"""
Tiny stand-in for RealF110Wrapper so CI can run the env and every
experiment script end-to-end without f110_gym (which pins gym 0.19 /
numpy ≤ 1.22 / Python 3.8).

A kinematic bicycle on a circular corridor (radius 2 m, width 0.8 m) with a
saturating friction cap: yaw rate is limited to μg/v, so lower grip makes
the car run wide and hit the outer wall. This is for testing plumbing,
NOT for producing results.
"""
import numpy as np

G = 9.81
R = 2.0


class FakeSim:
    timestep = 0.01
    half_width = 0.4  # raise to keep episodes alive long enough for φ (k = 50)

    def __init__(self, track='fake'):
        self.track = track
        self.mu = 1.0489

    def set_grip(self, grip):
        self.mu = 1.0489 * grip

    def reset(self, physics_params=None, heading_offset=0.0):
        p = physics_params or {}
        self.set_grip(p.get('grip_factor', 1.0))
        self.x, self.y, self.th = R, 0.0, np.pi / 2 + heading_offset
        self.v, self.steer, self.yaw_rate = 0.0, 0.0, 0.0
        return self._vec(), self._obs(False)

    def step(self, action):
        steer, v_cmd = float(action[0]), float(action[1])
        self.steer = np.clip(steer, -0.4189, 0.4189)
        self.v += np.clip(v_cmd - self.v, -9.51 * self.timestep, 9.51 * self.timestep)
        yaw = self.v * np.tan(self.steer) / 0.33
        if self.v > 0.1:
            cap = self.mu * G / self.v
            yaw = np.clip(yaw, -cap, cap)
        self.yaw_rate = yaw
        self.th += yaw * self.timestep
        self.x += self.v * np.cos(self.th) * self.timestep
        self.y += self.v * np.sin(self.th) * self.timestep
        crash = abs(np.hypot(self.x, self.y) - R) > self.half_width
        return self._vec(), self._obs(crash), crash, {}

    def close(self):
        pass

    def _vec(self):
        return np.array([self.v, self.steer, self.yaw_rate], dtype=np.float32)

    def _obs(self, crash):
        err = np.hypot(self.x, self.y) - R
        scans = np.full(1080, 1.0, dtype=np.float32)
        scans[:540] = self.half_width + err        # right side ≈ outer wall when driving CCW
        scans[540:] = self.half_width - err
        return {
            'scans': [np.clip(scans, 0.0, 30.0)],
            'poses_x': [self.x], 'poses_y': [self.y], 'poses_theta': [self.th],
            'linear_vels_x': [self.v], 'ang_vels_z': [self.yaw_rate],
            'collisions': [float(crash)], 'lap_counts': [0],
        }
