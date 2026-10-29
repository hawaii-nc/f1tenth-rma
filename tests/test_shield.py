import numpy as np

from f1tenth_research.safety import ShieldConfig, shield_velocity, acda_speed_limit, curvature_speed_limit


def scan(dist, n=1080):
    return np.full(n, dist)


def test_shield_never_raises_speed():
    rng = np.random.default_rng(0)
    for _ in range(200):
        v = rng.uniform(0, 3)
        out, _ = shield_velocity(v, rng.uniform(-0.4, 0.4), rng.uniform(0.1, 10, 1080), rng.uniform(0.2, 1.0))
        assert out <= v + 1e-12


def test_open_road_is_unchanged():
    out, d = shield_velocity(3.0, 0.0, scan(10.0), 1.0)
    assert out == 3.0 and not d['active']


def test_wall_ahead_stops_car():
    out, d = shield_velocity(3.0, 0.0, scan(0.25), 1.0)
    assert out == 0.0 and d['active']


def test_limits_shrink_with_grip():
    assert acda_speed_limit(2.0, 0.4) < acda_speed_limit(2.0, 1.0)
    assert curvature_speed_limit(0.3, 0.4) < curvature_speed_limit(0.3, 1.0)
    assert curvature_speed_limit(0.0, 1.0) == float('inf')


def test_curvature_limit_physics():
    cfg = ShieldConfig(lateral_margin=1.0, wheelbase=0.33)
    steer = 0.3
    v = curvature_speed_limit(steer, 1.0, cfg)
    kappa = np.tan(steer) / 0.33
    assert np.isclose(v ** 2 * kappa, 9.81)  # lateral accel at the limit = μg
