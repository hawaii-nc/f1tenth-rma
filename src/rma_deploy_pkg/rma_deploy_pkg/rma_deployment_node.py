"""
RMA Deployment Node -- Real Car / Gazebo Sim Compatible
=========================================================
Loads a trained Phase 1 (+ optional Phase 2) RMA policy and drives the car.
LiDAR + odometry only -- no map/raceline dependency, works on any track shape.

Topic parameters (set via launch file or CLI):
  odom_topic   : '/ego_racecar/odom' (sim) or '/odom' (real car)
  scan_topic   : '/scan' (same for both)
  drive_topic  : '/drive' (same for both)

Modes:
  Phase 1 only (no --adaptation): the policy receives μ(nominal physics) as
      its intrinsics: this is the "Blind" controller.
  Phase 2 (--adaptation PATH): ẑ = φ(last k state-action pairs) once k steps
      of history exist; nominal intrinsics until then. k is read from the
      checkpoint (phase2_crashtol_clean.pt uses 50).

Per-step CSV log (--log_path, default ~/rma_data.csv): same columns as the
July 2026 hardware trials, consumed by analysis/real_car/tire_stats.py.

Changes vs. the July 28 on-car version (behaviour at defaults is unchanged):
  * checkpoints load with weights_only=True and are sized from their weights
  * --adaptation '' (what veh_launch.py passes by default) means "none"
    instead of crashing on torch.load('')
  * history window inferred from the φ checkpoint (was a CLI default of 10,
    which cannot load the 50-step φ)
  * log path, steering limit and footprint margin are CLI arguments
  * optional --shield: grip-adaptive ACDA / curvature speed shield (off by default)
"""

import argparse
import csv
import os
from collections import deque
from typing import Optional

import numpy as np
import torch
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from ackermann_msgs.msg import AckermannDriveStamped

OBS_DIM = 113          # 5 base signals + 108 LiDAR beams (matches v27+ training config)
LIDAR_BEAMS = 108
LIDAR_MAX_RANGE = 10.0
ACTION_DIM = 2
MAX_VELOCITY = 3.0      # m/s -- matches tight-track training config
NOMINAL_PHYSICS = [1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0]
STATIONARY_VEL_THRESHOLD = 0.10
STATIONARY_TIMEOUT_TICKS = 150  # 3s at 50Hz


def preprocess_scan(ranges, beams=LIDAR_BEAMS, max_range=LIDAR_MAX_RANGE, footprint_margin=0.10):
    """
    1080 raw ranges -> `beams` evenly spaced, minus a virtual footprint
    margin (the car "sees" walls this much closer than reality), clipped and
    normalized to [0, 1] exactly as in training.
    """
    r = np.asarray(ranges, dtype=np.float32)
    r = np.where(np.isfinite(r), r, max_range)
    idx = np.linspace(0, len(r) - 1, beams).astype(int)
    r = np.clip(r[idx] - footprint_margin, 0.0, max_range)
    return r / max_range


class RMADeploymentNode(Node):
    def __init__(
        self,
        actor_critic_checkpoint: str,
        adaptation_checkpoint: Optional[str] = None,
        control_freq: float = 50.0,
        odom_topic: str = '/ego_racecar/odom',
        scan_topic: str = '/scan',
        drive_topic: str = '/drive',
        history_window: Optional[int] = None,
        log_path: str = '~/rma_data.csv',
        max_steer: float = 0.436,
        footprint_margin: float = 0.10,
        shield: bool = False,
        shield_mu: float = 1.0,
    ):
        super().__init__('rma_deployment')
        self.control_freq = control_freq
        self.max_steer = max_steer
        self.footprint_margin = footprint_margin
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.get_logger().info(f"Using device: {self.device}")
        self.get_logger().info(f"Subscribing to odom: {odom_topic}, scan: {scan_topic}")
        self.get_logger().info(f"Publishing to drive: {drive_topic}")

        from f1tenth_research.models import load_actor_critic, load_adaptation

        # --- Load actor-critic (Phase 1) ---
        self.actor_critic, _ = load_actor_critic(actor_critic_checkpoint, self.device)
        obs_dim = self.actor_critic.policy.obs_dim
        if obs_dim != OBS_DIM:
            raise ValueError(f"{actor_critic_checkpoint} expects obs_dim={obs_dim}; this node builds {OBS_DIM}")
        self.get_logger().info(f"Actor-critic loaded from {actor_critic_checkpoint} (obs_dim={OBS_DIM})")
        with torch.no_grad():
            self.nominal_intrinsics = self.actor_critic.get_intrinsics(
                torch.tensor([NOMINAL_PHYSICS], device=self.device))

        # --- Load adaptation module (Phase 2, optional) ---
        self.adaptation = None
        self.use_adaptation = False
        self.history_window = history_window or 1
        if adaptation_checkpoint:
            self.adaptation, _ = load_adaptation(adaptation_checkpoint, self.device)
            if history_window and history_window != self.adaptation.history_window:
                self.get_logger().warn(
                    f"--history_window {history_window} ignored; checkpoint was trained "
                    f"with {self.adaptation.history_window}")
            self.history_window = self.adaptation.history_window
            self.use_adaptation = True
            self.get_logger().info(
                f"Adaptation module loaded (Phase 2 mode, history={self.history_window})")
        else:
            self.get_logger().info(
                "No adaptation checkpoint provided -- running Phase 1 mode "
                "(nominal intrinsics).")

        self.shield = None
        if shield:
            from f1tenth_research.safety import shield_velocity
            self.shield = shield_velocity
            self.shield_mu = shield_mu
            self.get_logger().info(f"Safety shield ON (μ={shield_mu})")

        # --- State tracking ---
        self.current_velocity = 0.0
        self.current_steering = 0.0
        self.current_yaw_rate = 0.0
        self.pose_x = ''
        self.pose_y = ''
        self.lidar_obs = np.ones(LIDAR_BEAMS, dtype=np.float32)
        self.lidar_raw = None
        self.lidar_received = False
        self.prev_action = np.zeros(ACTION_DIM, dtype=np.float32)
        self.smoothed_action = np.zeros(ACTION_DIM, dtype=np.float32)
        self.action_smoothing_alpha = 1.0  # 1.0 = no smoothing, matches training
        self.history = deque(maxlen=self.history_window)
        self._stationary_ticks = 0
        self._ticks = 0
        self._last_phi = None

        log_path = os.path.expanduser(log_path)
        self._csv_file = open(log_path, 'w', newline='')
        self._csv = csv.writer(self._csv_file)
        self._csv.writerow(
            ['time', 'lidar_received', 'velocity', 'yaw_rate', 'pose_x', 'pose_y',
             'lidar_min', 'lidar_mean', 'v_des', 'steer_des', 'phi_active',
             'raw_steer', 'raw_throttle', 'steer_action', 'throttle_action']
            + [f'phi_{i}' for i in range(8)] + [f'lidar_{i}' for i in range(LIDAR_BEAMS)])
        self.get_logger().info(f"Logging to {log_path}")

        self.odom_sub = self.create_subscription(Odometry, odom_topic, self.odom_callback, 10)
        self.lidar_sub = self.create_subscription(LaserScan, scan_topic, self.lidar_callback, 10)
        self.drive_pub = self.create_publisher(AckermannDriveStamped, drive_topic, 10)
        self.timer = self.create_timer(1.0 / control_freq, self.control_loop)
        self.get_logger().info(f"RMA deployment node ready at {control_freq} Hz")

    def odom_callback(self, msg: Odometry):
        self.current_velocity = float(msg.twist.twist.linear.x)
        self.current_yaw_rate = float(msg.twist.twist.angular.z)
        self.pose_x = float(msg.pose.pose.position.x)
        self.pose_y = float(msg.pose.pose.position.y)

    def lidar_callback(self, msg: LaserScan):
        self.lidar_raw = np.asarray(msg.ranges, dtype=np.float32)
        self.lidar_obs = preprocess_scan(self.lidar_raw, footprint_margin=self.footprint_margin)
        self.lidar_received = True

    def _build_obs(self) -> np.ndarray:
        v_des = (float(self.prev_action[1]) + 1.0) / 2.0 * MAX_VELOCITY
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

    def _now(self):
        return self.get_clock().now().nanoseconds

    def control_loop(self):
        self._ticks += 1
        if not self.lidar_received:
            self._csv.writerow([self._now(), False, self.current_velocity, self.current_yaw_rate,
                                self.pose_x, self.pose_y] + [''] * 9 + [''] * 8 + [''] * LIDAR_BEAMS)
            self._csv_file.flush()
            return

        obs = self._build_obs()
        obs_tensor = torch.from_numpy(obs).unsqueeze(0).to(self.device)

        phi_active = self.use_adaptation and len(self.history) >= self.history_window
        with torch.no_grad():
            if phi_active:
                hist = torch.from_numpy(np.asarray(self.history, dtype=np.float32)).unsqueeze(0).to(self.device)
                intrinsics = self.adaptation(hist)
                self._last_phi = intrinsics.cpu().numpy().flatten().tolist()
            else:
                intrinsics = self.nominal_intrinsics
            mean, _ = self.actor_critic.policy(obs_tensor, intrinsics)
            raw_action = mean.cpu().numpy().squeeze(0)

        alpha = self.action_smoothing_alpha
        self.smoothed_action = alpha * raw_action + (1 - alpha) * self.smoothed_action
        action_np = self.smoothed_action.astype(np.float32)

        self.history.append(np.concatenate([obs, action_np]))
        self.prev_action = action_np.copy()
        self.current_steering = float(action_np[0])
        # Pure RMA: policy output -> command, no hand-coded logic in between
        # (unless --shield, which can only lower the speed).
        steer_cmd = float(np.clip(action_np[0], -self.max_steer, self.max_steer))
        throttle_cmd = float(np.clip(action_np[1], -1.0, 1.0))
        velocity_cmd = (throttle_cmd + 1.0) / 2.0 * MAX_VELOCITY
        if self.shield is not None and self.lidar_raw is not None:
            velocity_cmd, _ = self.shield(velocity_cmd, steer_cmd, self.lidar_raw, self.shield_mu)

        msg = AckermannDriveStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.drive.steering_angle = steer_cmd
        msg.drive.speed = velocity_cmd
        self.drive_pub.publish(msg)

        # Stationary timeout: stop logging once the car has been idle 3+ s
        # (end-of-trial / dead time between runs).
        if abs(self.current_velocity) < STATIONARY_VEL_THRESHOLD:
            self._stationary_ticks += 1
        else:
            self._stationary_ticks = 0
        if self._stationary_ticks < STATIONARY_TIMEOUT_TICKS:
            lidar_m = self.lidar_obs * LIDAR_MAX_RANGE
            self._csv.writerow(
                [self._now(), True, self.current_velocity, self.current_yaw_rate,
                 self.pose_x, self.pose_y, float(lidar_m.min()), float(lidar_m.mean()),
                 self._last_v_des, self._last_steer_des, int(phi_active),
                 float(raw_action[0]), float(raw_action[1]),
                 float(action_np[0]), float(action_np[1])]
                + (self._last_phi if phi_active else [''] * 8)
                + lidar_m.tolist())
        self._csv_file.flush()

        if self._ticks % 50 == 0:
            lidar_m = self.lidar_obs * LIDAR_MAX_RANGE
            self.get_logger().info(
                f"[DIAG] vel={self.current_velocity:.2f} yaw_rate={self.current_yaw_rate:.2f} "
                f"lidar_min={lidar_m.min():.2f} lidar_mean={lidar_m.mean():.2f} "
                f"raw_action=[{raw_action[0]:.3f},{raw_action[1]:.3f}] "
                f"steer_cmd={steer_cmd:.3f} vel_cmd={velocity_cmd:.3f} phi={int(phi_active)}")

    def destroy_node(self):
        self._csv_file.close()
        super().destroy_node()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--actor_critic', type=str, required=True)
    parser.add_argument('--adaptation', type=str, default='')
    parser.add_argument('--control_freq', type=float, default=50.0)
    parser.add_argument('--odom_topic', type=str, default='/ego_racecar/odom')
    parser.add_argument('--scan_topic', type=str, default='/scan')
    parser.add_argument('--drive_topic', type=str, default='/drive')
    parser.add_argument('--history_window', type=int, default=0,
                        help='Ignored when it disagrees with the φ checkpoint (kept for old scripts)')
    parser.add_argument('--log_path', type=str, default='~/rma_data.csv')
    parser.add_argument('--max_steer', type=float, default=0.436,
                        help='0.436 rad was used in the July 2026 hardware trials; training clipped at 0.4189')
    parser.add_argument('--footprint_margin', type=float, default=0.10)
    parser.add_argument('--shield', action='store_true')
    parser.add_argument('--shield_mu', type=float, default=1.0)
    args, _ = parser.parse_known_args()

    rclpy.init()
    node = RMADeploymentNode(
        actor_critic_checkpoint=args.actor_critic,
        adaptation_checkpoint=args.adaptation or None,
        control_freq=args.control_freq,
        odom_topic=args.odom_topic,
        scan_topic=args.scan_topic,
        drive_topic=args.drive_topic,
        history_window=args.history_window or None,
        log_path=args.log_path,
        max_steer=args.max_steer,
        footprint_margin=args.footprint_margin,
        shield=args.shield,
        shield_mu=args.shield_mu,
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
