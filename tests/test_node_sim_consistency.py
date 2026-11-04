"""
Closed loop: the on-car node and the training env must agree step by step.

The env (sensors.model = car, braking probe) drives a fake car. At every step the
node gets exactly the messages the car's stack would publish from that state
(odometry speed and yaw rate, raw LiDAR scan), runs its real control_loop()
with the R checkpoints, and we check that:
  1. the node's observation equals the env's observation,
  2. the speed and steering the node publishes equal what the env applies for
     the same action (probe included), and
  3. φ sees the same history in both.
ROS 2 is not installed in CI, so rclpy and the message packages are stubbed.
"""
import sys
import types
from pathlib import Path

import numpy as np
import pytest
import torch

REPO = Path(__file__).resolve().parents[1]
P1 = REPO / 'runs/real_phase1_seed0/final.pt'
P2 = REPO / 'runs/real_phase2_seed0/final.pt'


class _NS(types.SimpleNamespace):
    pass


def _msg():
    return _NS(header=_NS(stamp=None), drive=_NS(steering_angle=0.0, speed=0.0))


class _Node:
    def __init__(self, name):
        self.published = []

    def get_logger(self):
        return _NS(info=lambda *a, **k: None, warn=lambda *a, **k: None)

    def create_subscription(self, *a, **k):
        return None

    def create_publisher(self, *a, **k):
        return _NS(publish=self.published.append)

    def create_timer(self, *a, **k):
        return None

    def get_clock(self):
        return _NS(now=lambda: _NS(nanoseconds=0, to_msg=lambda: None))

    def destroy_node(self):
        pass


@pytest.fixture(scope='module')
def node_module():
    stubs = {}
    for name in ('rclpy', 'rclpy.node', 'sensor_msgs', 'sensor_msgs.msg', 'nav_msgs', 'nav_msgs.msg',
                 'ackermann_msgs', 'ackermann_msgs.msg'):
        if name not in sys.modules:
            stubs[name] = sys.modules[name] = types.ModuleType(name)
    sys.modules['rclpy.node'].Node = _Node
    sys.modules['sensor_msgs.msg'].LaserScan = object
    sys.modules['nav_msgs.msg'].Odometry = object
    sys.modules['ackermann_msgs.msg'].AckermannDriveStamped = _msg
    import importlib
    import rma_deploy_pkg
    sys.modules.pop('rma_deploy_pkg.rma_deployment_node', None)
    if hasattr(rma_deploy_pkg, 'rma_deployment_node'):
        delattr(rma_deploy_pkg, 'rma_deployment_node')   # another test may have imported it with other stubs
    rma_deployment_node = importlib.import_module('rma_deploy_pkg.rma_deployment_node')
    yield rma_deployment_node
    sys.modules.pop('rma_deploy_pkg.rma_deployment_node', None)
    for name in stubs:
        sys.modules.pop(name, None)


@pytest.mark.skipif(not (P1.exists() and P2.exists()), reason='R checkpoints not present')
def test_node_matches_env_closed_loop(node_module, tmp_path):
    import yaml
    from fake_sim import FakeSim
    from f1tenth_research.envs import F1TenthRMAEnv
    cfg = yaml.safe_load((REPO / 'configs/real_phase2_probe.yaml').read_text())
    env_cfg = cfg['environment']
    env_cfg['tracks'] = ['aut']
    env_cfg['sensors'] = {'model': 'car', 'speed_noise': 0.0}
    env_cfg['observation']['lidar_noise_std'] = 0.0
    env_cfg['observation']['lidar_dropout_prob'] = 0.0
    pr = env_cfg['probe']
    pr['max_steer'] = 1.0   # the fake corridor is a tight circle: let the probe fire there too
    F1TenthRMAEnv.wrapper_factory = staticmethod(FakeSim)
    old_hw = FakeSim.half_width
    FakeSim.half_width = 50.0   # this is a plumbing test: keep the fake car alive past φ's window
    try:
        env = F1TenthRMAEnv(config=cfg)
        node = node_module.RMADeploymentNode(
            str(P1), str(P2), control_freq=100.0, log_path=str(tmp_path / 'log.csv'),
            footprint_margin=env.sensor_cfg['footprint_margin'], probe=True,
            probe_period=pr['period_steps'], probe_duration=pr['duration_steps'],
            probe_amplitude=pr['amplitude'], probe_max_steer=pr['max_steer'])
        obs, info = env.reset(seed=3, options={'training': False, 'track': 'aut', 'obs_noise': False})
        env_hist = []
        built = []
        orig_build = node._build_obs
        node._build_obs = lambda: built.append(orig_build()) or built[-1]
        n_probe = 0
        for t in range(120):
            # What the car's stack would publish for the env's current state
            node.odom_callback(_NS(twist=_NS(twist=_NS(linear=_NS(x=float(obs[0])), angular=_NS(z=float(obs[4])))),
                                   pose=_NS(pose=_NS(position=_NS(x=0.0, y=0.0)))))
            node.lidar_callback(_NS(ranges=env._scan_hold.tolist()))
            node.control_loop()
            node_obs = built[-1]
            np.testing.assert_allclose(node_obs, obs, rtol=1e-5, atol=1e-5, err_msg=f'obs differ at step {t}')
            action = node.history[-1][-2:].copy()            # the raw action the node acted on
            env_hist.append(np.concatenate([obs, action]))
            msg = node.published[-1]
            obs, _, term, trunc, info = env.step(action)
            assert msg.drive.speed == pytest.approx(info['velocity_cmd'], abs=1e-5), f'speed differs at step {t}'
            assert msg.drive.steering_angle == pytest.approx(float(np.clip(action[0], -0.4189, 0.4189)), abs=1e-6)
            n_probe += bool(info['probing'])
            if term:
                break
        assert t > 60, 'fake car crashed too early to test φ'
        assert n_probe > 0, 'no probe pulse happened'
        # φ's history in the node equals the (obs, action) history the env produced
        k = node.history_window
        np.testing.assert_allclose(np.asarray(node.history)[-k:], np.asarray(env_hist)[-k:], rtol=1e-5, atol=1e-5)
    finally:
        F1TenthRMAEnv.wrapper_factory = None
        FakeSim.half_width = old_hw
