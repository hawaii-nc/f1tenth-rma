#!/usr/bin/env python3
"""
Stage 1 of docs/REAL_CAR_PROBE_PLAN.md: the open-loop braking-probe maneuver on
the real car, logged to CSV for tools/real_car/analyze_probe_trials.py.

UNTESTED ON HARDWARE (written without ROS 2 or the car). Check topic names with
`ros2 topic list` first, keep the car on a straight of >= 4 m, e-stop in hand.

Each trial, driven straight (steering 0):
  cruise  --cruise m/s for --cruise_s s     (let the speed settle)
  pulse   --cruise + --amplitude for --pulse_s s   (amplitude < 0: braking probe;
          the R configuration uses -1.0 m/s for 0.1 s)
  recover --cruise for --recover_s s
  stop    0 m/s
logged at --rate Hz (100 = training rate): t, phase, commanded speed, odometry
speed and yaw rate, front LiDAR range (median of beams within +-5 deg of straight
ahead: true motion, independent of wheel slip), IMU longitudinal acceleration
if --imu_topic is given (VESC IMU), VESC motor current if /sensors/core exists.

    ros2 run ... probe_maneuver_node.py --surface bare --trial 1 --out ~/probe_trials.csv
"""
import argparse
import csv
import math
import os
import time

import rclpy
from rclpy.node import Node
from ackermann_msgs.msg import AckermannDriveStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan, Imu


class ProbeManeuver(Node):
    def __init__(self, a):
        super().__init__('probe_maneuver')
        self.a = a
        self.pub = self.create_publisher(AckermannDriveStamped, a.drive_topic, 10)
        self.create_subscription(Odometry, a.odom_topic, self._odom, 10)
        self.create_subscription(LaserScan, a.scan_topic, self._scan, 10)
        if a.imu_topic:
            self.create_subscription(Imu, a.imu_topic, self._imu, 10)
        try:   # VESC state (motor current) if the vesc_msgs package is present
            from vesc_msgs.msg import VescStateStamped
            self.create_subscription(VescStateStamped, '/sensors/core', self._core, 10)
        except ImportError:
            pass
        self.v_odom = self.yaw = self.front = self.ax = self.current = float('nan')
        new = not os.path.exists(os.path.expanduser(a.out))
        self.f = open(os.path.expanduser(a.out), 'a', newline='')
        self.w = csv.writer(self.f)
        if new:
            self.w.writerow(['t', 'surface', 'trial', 'phase', 'cmd_speed', 'odom_speed', 'odom_yaw_rate',
                             'front_range', 'imu_ax', 'motor_current'])
        self.t0 = time.monotonic()
        self.timer = self.create_timer(1.0 / a.rate, self._tick)

    def _odom(self, m):
        self.v_odom = m.twist.twist.linear.x
        self.yaw = m.twist.twist.angular.z

    def _scan(self, m):
        n = len(m.ranges)
        c = int(round((0.0 - m.angle_min) / m.angle_increment))      # beam pointing straight ahead
        half = int(round(math.radians(5.0) / m.angle_increment))
        vals = [r for r in m.ranges[max(0, c - half):min(n, c + half + 1)] if math.isfinite(r)]
        self.front = sorted(vals)[len(vals) // 2] if vals else float('nan')

    def _imu(self, m):
        self.ax = m.linear_acceleration.x

    def _core(self, m):
        self.current = m.state.current_motor

    def _tick(self):
        a, t = self.a, time.monotonic() - self.t0
        if t < a.cruise_s:
            phase, v = 'cruise', a.cruise
        elif t < a.cruise_s + a.pulse_s:
            phase, v = 'pulse', max(0.0, a.cruise + a.amplitude)
        elif t < a.cruise_s + a.pulse_s + a.recover_s:
            phase, v = 'recover', a.cruise
        else:
            phase, v = 'stop', 0.0
        msg = AckermannDriveStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.drive.speed = float(v)
        msg.drive.steering_angle = 0.0
        self.pub.publish(msg)
        self.w.writerow([f'{t:.4f}', a.surface, a.trial, phase, v, self.v_odom, self.yaw, self.front, self.ax, self.current])
        if phase == 'stop' and t > a.cruise_s + a.pulse_s + a.recover_s + 1.0:
            self.f.close()
            raise SystemExit


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--surface', required=True, help='label, e.g. bare / duct / electrical')
    ap.add_argument('--trial', type=int, required=True)
    ap.add_argument('--out', default='~/probe_trials.csv')
    ap.add_argument('--cruise', type=float, default=1.5)
    ap.add_argument('--amplitude', type=float, default=-1.0)
    ap.add_argument('--cruise_s', type=float, default=1.5)
    ap.add_argument('--pulse_s', type=float, default=0.1)
    ap.add_argument('--recover_s', type=float, default=1.0)
    ap.add_argument('--rate', type=float, default=100.0)
    ap.add_argument('--drive_topic', default='/drive')
    ap.add_argument('--odom_topic', default='/odom')
    ap.add_argument('--scan_topic', default='/scan')
    ap.add_argument('--imu_topic', default='', help='e.g. /sensors/imu/raw, if the VESC publishes it')
    a, _ = ap.parse_known_args()
    rclpy.init()
    node = ProbeManeuver(a)
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
