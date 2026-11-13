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


def test_probe_defaults_match_the_deployable_model(node_module):
    """The node's and the launch file's default probe must be the one the car models
    (runs/real_*) were trained with: a braking pulse. The default used to be +2.0 m/s,
    the ideal-sensor configuration's accelerating pulse."""
    import inspect
    import re
    import yaml
    pr = yaml.safe_load((REPO / 'configs/real_phase2_probe.yaml').read_text())['environment']['probe']
    sig = inspect.signature(node_module.RMADeploymentNode.__init__).parameters
    assert sig['probe_amplitude'].default == pr['amplitude'] < 0
    assert sig['probe_period'].default == pr['period_steps']
    assert sig['probe_duration'].default == pr['duration_steps']
    assert sig['probe_max_steer'].default == pr['max_steer']
    src = (REPO / 'src/rma_deploy_pkg/rma_deploy_pkg/rma_deployment_node.py').read_text()
    cli = re.search(r"'--probe_amplitude', type=float, default=(-?[\d.]+)", src)
    assert cli and float(cli.group(1)) == pr['amplitude']
    launch = (REPO / 'src/rma_deploy_pkg/launch/veh_launch.py').read_text()
    arg = re.search(r"DeclareLaunchArgument\('probe_amplitude', default_value='(-?[\d.]+)'\)", launch)
    assert arg and float(arg.group(1)) == pr['amplitude']
    assert "'--probe_amplitude', LaunchConfiguration('probe_amplitude')" in launch
