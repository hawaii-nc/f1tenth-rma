import numpy as np
import pytest

from f1tenth_research.experts import PurePursuitExpert


def expert(**cfg):
    wp = np.column_stack([np.linspace(0, 10, 200), np.zeros(200)])
    return PurePursuitExpert(config={'lookahead_distance_base': 0.5, 'max_speed': 3.0, 'min_speed': 0.5, **cfg},
                             waypoints=wp)


def test_partial_config_keeps_defaults():
    e = expert()
    assert e.config['grip_aware'] is True        # used to KeyError -> silently no expert


def test_throttle_is_absolute_velocity_setpoint():
    e = expert(grip_aware=False, nominal_speed=1.5)
    a = e.compute_action({'position': (0.0, 0.0), 'yaw': 0.0, 'velocity': 1.5}, {'grip_factor': 1.0})
    v_cmd = (a[1] + 1) / 2 * 3.0
    assert v_cmd == pytest.approx(1.5)            # env commands exactly the expert's target speed


def test_low_grip_slows_expert():
    e = expert(nominal_speed=3.0)
    state = {'position': (0.0, 0.0), 'yaw': 0.0, 'velocity': 2.0}
    hi = e.compute_action(state, {'grip_factor': 1.0})
    lo = e.compute_action(state, {'grip_factor': 0.4})
    assert lo[1] < hi[1]


def test_steers_toward_path():
    e = expert(grip_aware=False)
    left_of_path = e.compute_action({'position': (0.0, 0.5), 'yaw': 0.0, 'velocity': 1.0}, {})
    assert left_of_path[0] < 0                    # path is to the right -> steer right (negative)
