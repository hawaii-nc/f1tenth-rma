"""
The on-car node must build exactly the observation the policy was trained on.
ROS 2 is not installed in CI, so rclpy & message packages are stubbed.
"""
import sys
import types
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def node_module():
    stubs = {}
    for name in ('rclpy', 'rclpy.node', 'sensor_msgs', 'sensor_msgs.msg', 'nav_msgs', 'nav_msgs.msg',
                 'ackermann_msgs', 'ackermann_msgs.msg'):
        if name not in sys.modules:
            stubs[name] = sys.modules[name] = types.ModuleType(name)
    sys.modules['rclpy.node'].Node = object
    sys.modules['sensor_msgs.msg'].LaserScan = object
    sys.modules['nav_msgs.msg'].Odometry = object
    sys.modules['ackermann_msgs.msg'].AckermannDriveStamped = object
    from rma_deploy_pkg import rma_deployment_node
    yield rma_deployment_node
    for name in stubs:
        sys.modules.pop(name, None)


def test_scan_preprocessing_matches_training(node_module):
    rng = np.random.default_rng(0)
    raw = rng.uniform(0.05, 12.0, 1080).astype(np.float32)
    raw[7] = np.inf
    # Training: evenly spaced 108 of 1080, clip [0, 10], /10 (f1tenth_env._process_observation)
    idx = np.linspace(0, 1079, 108).astype(int)
    train = np.clip(np.where(np.isfinite(raw), raw, 10.0)[idx], 0.0, 10.0) / 10.0
    deploy = node_module.preprocess_scan(raw, footprint_margin=0.0)
    np.testing.assert_allclose(deploy, train, rtol=1e-6)
    # Footprint margin only ever makes walls look closer
    assert (node_module.preprocess_scan(raw, footprint_margin=0.1) <= deploy + 1e-7).all()


def test_constants_match_final_checkpoint(node_module):
    import yaml
    cfg = yaml.safe_load((REPO / 'configs/final_phase1_v42.yaml').read_text())['environment']
    assert node_module.LIDAR_BEAMS == cfg['observation']['lidar_beams']
    assert node_module.LIDAR_MAX_RANGE == cfg['observation']['lidar_max_range']
    assert node_module.MAX_VELOCITY == cfg['max_velocity']
    assert node_module.OBS_DIM == 5 + node_module.LIDAR_BEAMS
