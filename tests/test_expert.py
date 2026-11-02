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


def test_corner_speed_profile_slows_for_tight_corners_and_low_grip():
    """High-speed expert: v ≤ √(v_c² + 2·a_b·d), v_c = √(f·μ·g·R) over the preview window."""
    import numpy as np
    from f1tenth_research.experts import PurePursuitExpert
    th = np.linspace(0, 2 * np.pi, 600, endpoint=False)
    wide = np.c_[10 * np.cos(th), 10 * np.sin(th)]        # R = 10 m
    tight = np.c_[1 * np.cos(th), 1 * np.sin(th)]         # R = 1 m
    cfg = {'corner_speed': True, 'nominal_speed': 5.0, 'max_speed': 5.0, 'lookahead_distance_base': 0.5,
           'grip_speed_scale': {1.0: 1.0}, 'grip_steering_scale': {1.0: 1.0}}
    def speed(wp, grip):
        ex = PurePursuitExpert(config=cfg, waypoints=wp)
        thr = ex.compute_action({'position': tuple(wp[0]), 'yaw': np.pi / 2, 'velocity': 3.0}, {'grip_factor': grip})[1]
        return (thr + 1) / 2 * 5.0
    mu = 1.0489
    assert speed(tight, 1.0) == pytest.approx(np.sqrt(0.6 * mu * 9.81 * 1.0), rel=0.05)
    assert speed(tight, 0.4) == pytest.approx(np.sqrt(0.6 * 0.4 * mu * 9.81 * 1.0), rel=0.05)
    assert speed(wide, 1.0) == pytest.approx(5.0)                      # capped by nominal speed
    # defaults unchanged: no corner logic, constant nominal speed
    ex = PurePursuitExpert(config={'lookahead_distance_base': 0.5}, waypoints=tight)
    thr = ex.compute_action({'position': tuple(tight[0]), 'yaw': np.pi / 2, 'velocity': 2.0}, {'grip_factor': 1.0})[1]
    assert (thr + 1) / 2 * 3.0 == pytest.approx(2.0)
