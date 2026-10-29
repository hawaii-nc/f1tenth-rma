"""
RMA Deployment Node -- Real Car / Gazebo Sim Compatible
=========================================================
Loads a trained Phase 1 (+ optional Phase 2) RMA policy and drives the car.
LiDAR + odometry only -- no map/raceline dependency, works on any track shape.

Topic parameters (set via launch file or --ros-args -p):
  odom_topic   : '/ego_racecar/odom' (sim) or '/odom' (real car)
  scan_topic   : '/scan' (same for both)
  drive_topic  : '/drive' (same for both)
"""

import argparse
from collections import deque
from typing import Optional

import numpy as np
import torch
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from ackermann_msgs.msg import AckermannDriveStamped

OBS_DIM = 113          # 5 base signals + 108 LiDAR beams (matches v27 training config)
LIDAR_BEAMS = 108
LIDAR_MAX_RANGE = 10.0
ACTION_DIM = 2
INTRINSICS_DIM = 8
MAX_VELOCITY = 3.0      # m/s -- matches tight-track training config
MAX_STEER = 0.436       # rad -- matches real car ~25 deg


class RMADeploymentNode(Node):
    def __init__(
        self,
        actor_critic_checkpoint: str,
        adaptation_checkpoint: Optional[str] = None,
        control_freq: float = 50.0,
        odom_topic: str = '/ego_racecar/odom',
        scan_topic: str = '/scan',
        drive_topic: str = 'nav_vel',
        history_window: int = 10,
    ):
        super().__init__('rma_deployment')
        self.control_freq = control_freq
        self.history_window = history_window
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.get_logger().info(f"Using device: {self.device}")
        self.get_logger().info(f"Subscribing to odom: {odom_topic}, scan: {scan_topic}")
        self.get_logger().info(f"Publishing to drive: {drive_topic}")

        from f1tenth_research.models import RMAActorCritic, AdaptationModule

        # --- Load actor-critic (Phase 1) ---
        self.actor_critic = RMAActorCritic(
            obs_dim=OBS_DIM,
            action_dim=ACTION_DIM,
            intrinsics_dim=INTRINSICS_DIM,
            env_params_dim=7,
        ).to(self.device)
        ckpt = torch.load(actor_critic_checkpoint, map_location=self.device, weights_only=False)
        self.actor_critic.load_state_dict(ckpt['actor_critic'])
        self.actor_critic.eval()
        self.get_logger().info(
            f"Actor-critic loaded from {actor_critic_checkpoint} (obs_dim={OBS_DIM})"
        )

        # --- Load adaptation module (Phase 2, optional) ---
        self.adaptation = None
        self.use_adaptation = False
        if adaptation_checkpoint is not None:
            self.adaptation = AdaptationModule(
                state_action_dim=OBS_DIM + ACTION_DIM,
                history_window=self.history_window,
                intrinsics_dim=INTRINSICS_DIM,
            ).to(self.device)
            ckpt2 = torch.load(adaptation_checkpoint, map_location=self.device, weights_only=False)
            self.adaptation.load_state_dict(ckpt2['adaptation'])
            self.adaptation.eval()
            self.use_adaptation = True
            self.get_logger().info("Adaptation module loaded (Phase 2 mode)")
        else:
            self.get_logger().info(
                "No adaptation checkpoint provided -- running Phase 1 mode "
                "(nominal intrinsics)."
            )

        # --- State tracking ---
        self.current_velocity = 0.0
        self.current_steering = 0.0
        self.current_yaw_rate = 0.0
        self.lidar_obs = np.ones(LIDAR_BEAMS, dtype=np.float32)
        self.lidar_received = False
        self.prev_action = np.zeros(ACTION_DIM, dtype=np.float32)
        self.smoothed_action = np.zeros(ACTION_DIM, dtype=np.float32)
        self.action_smoothing_alpha = 1.0  # 1.0 = no smoothing, matches training
        self.history = deque(maxlen=self.history_window)

        # --- ROS subscriptions (parameterized topics) ---
        self.odom_sub = self.create_subscription(
            Odometry, odom_topic, self.odom_callback, 10
        )
        self.lidar_sub = self.create_subscription(
            LaserScan, scan_topic, self.lidar_callback, 10
        )
        # --- Publisher ---
        self.drive_pub = self.create_publisher(
            AckermannDriveStamped, drive_topic, 10
        )

        # --- Control loop timer ---
        self.timer = self.create_timer(1.0 / control_freq, self.control_loop)
        self.get_logger().info(f"RMA deployment node ready at {control_freq} Hz")

    def odom_callback(self, msg: Odometry):
        self.current_velocity = float(msg.twist.twist.linear.x)
        self.current_yaw_rate = float(msg.twist.twist.angular.z)
        self.pose_x = float(msg.pose.pose.position.x)
        self.pose_y = float(msg.pose.pose.position.y)

    def lidar_callback(self, msg: LaserScan):
        if not hasattr(self, '_lidar_cb_count'):
            self._lidar_cb_count = 0
        self._lidar_cb_count += 1
        if self._lidar_cb_count <= 3 or self._lidar_cb_count % 100 == 0:
            self.get_logger().info(f"[CALLBACK FIRED] count={self._lidar_cb_count} num_ranges={len(msg.ranges)}")
        ranges = np.array(msg.ranges, dtype=np.float32)
        ranges = np.where(np.isfinite(ranges), ranges, LIDAR_MAX_RANGE)
        indices = np.linspace(0, len(ranges) - 1, LIDAR_BEAMS).astype(int)
        downsampled = ranges[indices]
        VIRTUAL_FOOTPRINT_MARGIN = 0.10  # meters; car "sees" walls this much closer than reality
        downsampled_margined = np.clip(downsampled - VIRTUAL_FOOTPRINT_MARGIN, 0.0, LIDAR_MAX_RANGE)
        self.lidar_obs = np.clip(downsampled_margined, 0.0, LIDAR_MAX_RANGE) / LIDAR_MAX_RANGE
        self.lidar_received = True

    def _build_obs(self) -> np.ndarray:
        throttle_cmd = self.prev_action[1]
        v_des = (float(throttle_cmd) + 1.0) / 2.0 * MAX_VELOCITY
        steer_des = float(self.prev_action[0])
        self._last_v_des = v_des
        self._last_steer_des = steer_des
        base = np.array([
            self.current_velocity,
            self.current_steering,
            v_des,
            steer_des,
            self.current_yaw_rate,
        ], dtype=np.float32)
        return np.concatenate([base, self.lidar_obs]).astype(np.float32)

    def control_loop(self):
        import csv
        if not hasattr(self, '_csv_file'):
            self._csv_file = open('/home/ncchong/rma_data.csv', 'w', newline='')
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow(['time','lidar_received','velocity','yaw_rate','pose_x','pose_y','lidar_min','lidar_mean','v_des','steer_des','phi_active','raw_steer','raw_throttle','steer_action','throttle_action'] + [f'phi_{i}' for i in range(8)] + [f'lidar_{i}' for i in range(108)])
        if not hasattr(self, '_cl_ticks'):
            self._cl_ticks = 0
        self._cl_ticks += 1
        if self._cl_ticks <= 5 or self._cl_ticks % 100 == 0:
            self.get_logger().info(f"[TICK] control_loop called, tick={self._cl_ticks}, lidar_received={self.lidar_received}")

        if not self.lidar_received:
            self._csv_writer.writerow([self.get_clock().now().nanoseconds, False, self.current_velocity, self.current_yaw_rate, getattr(self,'pose_x',''), getattr(self,'pose_y',''), '', '', '', '', '', '', '', ''] + ['']*8 + ['']*108)
            self._csv_file.flush()
            return

        obs = self._build_obs()
        obs_tensor = torch.from_numpy(obs).float().unsqueeze(0).to(self.device)

        with torch.no_grad():
            if self.use_adaptation and len(self.history) >= self.history_window:
                history_array = np.array(list(self.history), dtype=np.float32)
                hist_tensor = torch.from_numpy(history_array).unsqueeze(0).float().to(self.device)
                intrinsics = self.adaptation(hist_tensor)
                self._last_phi_intrinsics = intrinsics.detach().cpu().numpy().flatten().tolist()
            else:
                nominal_params = torch.tensor(
                    [[1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0]],
                    device=self.device
                )
                intrinsics = self.actor_critic.get_intrinsics(nominal_params)
            mean, _ = self.actor_critic.policy(obs_tensor, intrinsics)
            raw_action = mean.cpu().numpy().squeeze(0)
        self._last_raw_action = raw_action.copy()

        alpha = self.action_smoothing_alpha
        self.smoothed_action = alpha * raw_action + (1 - alpha) * self.smoothed_action
        action_np = self.smoothed_action.copy()

        state_action = np.concatenate([obs, action_np])
        self.history.append(state_action)
        self.prev_action = action_np.copy()
        self.current_steering = float(action_np[0])
        # Pure RMA: policy output -> command, no hand-coded logic in between.
        steer_cmd = float(np.clip(action_np[0], -MAX_STEER, MAX_STEER))
        throttle_cmd = float(np.clip(action_np[1], -1.0, 1.0))
        velocity_cmd = (throttle_cmd + 1.0) / 2.0 * MAX_VELOCITY

        msg = AckermannDriveStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.drive.steering_angle = steer_cmd
        msg.drive.speed = velocity_cmd
        self.drive_pub.publish(msg)

        _ra = getattr(self, '_last_raw_action', None)
        _full_lidar = (self.lidar_obs * LIDAR_MAX_RANGE).tolist()
        _phi_active = 1 if (self.use_adaptation and len(self.history) >= self.history_window) else 0

        # --- Stationary-timeout: skip logging once car has been idle 3+ seconds ---
        # (treat as end-of-trial / no-data period, so a single-person operator
        # doesn't have to manually track dead time between runs)
        STATIONARY_VEL_THRESHOLD = 0.10
        STATIONARY_TIMEOUT_TICKS = 150  # 3s at 50Hz
        if not hasattr(self, '_stationary_ticks'):
            self._stationary_ticks = 0
        if abs(self.current_velocity) < STATIONARY_VEL_THRESHOLD:
            self._stationary_ticks += 1
        else:
            self._stationary_ticks = 0

        if self._stationary_ticks < STATIONARY_TIMEOUT_TICKS:
            self._csv_writer.writerow([self.get_clock().now().nanoseconds, True, self.current_velocity, self.current_yaw_rate, getattr(self,'pose_x',''), getattr(self,'pose_y',''), float(self.lidar_obs.min()*LIDAR_MAX_RANGE), float(self.lidar_obs.mean()*LIDAR_MAX_RANGE), getattr(self,'_last_v_des',''), getattr(self,'_last_steer_des',''), _phi_active, float(_ra[0]) if _ra is not None else '', float(_ra[1]) if _ra is not None else '', float(action_np[0]), float(action_np[1])] + (getattr(self, '_last_phi_intrinsics', None) or ['']*8) + _full_lidar)
        self._csv_file.flush()

        if not hasattr(self, '_diag_counter'):
            self._diag_counter = 0
        self._diag_counter += 1
        if self._diag_counter % 50 == 0:
            lidar_real = self.lidar_obs * LIDAR_MAX_RANGE
            self.get_logger().info(
                f"[DIAG] vel={self.current_velocity:.2f} yaw_rate={self.current_yaw_rate:.2f} "
                f"steer_state={self.current_steering:.2f} "
                f"lidar_min={lidar_real.min():.2f} lidar_max={lidar_real.max():.2f} lidar_mean={lidar_real.mean():.2f} "
                f"raw_action=[{raw_action[0]:.3f},{raw_action[1]:.3f}] "
                f"steer_cmd={steer_cmd:.3f} vel_cmd={velocity_cmd:.3f}"
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--actor_critic', type=str, required=True)
    parser.add_argument('--adaptation', type=str, default=None)
    parser.add_argument('--control_freq', type=float, default=50.0)
    parser.add_argument('--odom_topic', type=str, default='/ego_racecar/odom')
    parser.add_argument('--scan_topic', type=str, default='/scan')
    parser.add_argument('--drive_topic', type=str, default='/drive')
    parser.add_argument('--history_window', type=int, default=10)
    args, _ = parser.parse_known_args()

    rclpy.init()
    node = RMADeploymentNode(
        actor_critic_checkpoint=args.actor_critic,
        adaptation_checkpoint=args.adaptation,
        control_freq=args.control_freq,
        odom_topic=args.odom_topic,
        scan_topic=args.scan_topic,
        drive_topic=args.drive_topic,
        history_window=args.history_window,
    )
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
