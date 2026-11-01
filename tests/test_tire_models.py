"""Saturating tire model (envs/tire_models.py) vs f110_gym's stock linear model."""
import sys
import types

import numpy as np
import pytest

from f1tenth_research.envs import tire_models as tm

# f110_gym defaults (same as envs/real_env.py NOMINAL_VEHICLE_PARAMS, which
# can't be imported here without f110_gym installed)
P = {
    'mu': 1.0489, 'C_Sf': 4.718, 'C_Sr': 5.4562,
    'lf': 0.15875, 'lr': 0.17145, 'h': 0.074, 'm': 3.74,
    'I': 0.04712, 's_min': -0.4189, 's_max': 0.4189,
    'sv_min': -3.2, 'sv_max': 3.2, 'v_switch': 7.319,
    'a_max': 9.51, 'v_min': -5.0, 'v_max': 20.0,
}

ARGS = ('mu', 'C_Sf', 'C_Sr', 'lf', 'lr', 'h', 'm', 'I', 's_min', 's_max',
        'sv_min', 'sv_max', 'v_switch', 'a_max', 'v_min', 'v_max')
G = 9.81


def args(**over):
    p = dict(P, **over)
    return tuple(p[k] for k in ARGS)


def stock_st(x, u, mu, C_Sf, C_Sr, lf, lr, h, m, I, *_):
    """f110_gym 0.2.1 vehicle_dynamics_st, dynamic branch (|v| ≥ 0.5), transcribed."""
    a = u[1]
    return np.array([
        x[3] * np.cos(x[6] + x[4]),
        x[3] * np.sin(x[6] + x[4]),
        u[0],
        a,
        x[5],
        -mu * m / (x[3] * I * (lr + lf)) * (lf**2 * C_Sf * (G * lr - a * h) + lr**2 * C_Sr * (G * lf + a * h)) * x[5]
        + mu * m / (I * (lr + lf)) * (lr * C_Sr * (G * lf + a * h) - lf * C_Sf * (G * lr - a * h)) * x[6]
        + mu * m / (I * (lr + lf)) * lf * C_Sf * (G * lr - a * h) * x[2],
        (mu / (x[3]**2 * (lr + lf)) * (C_Sr * (G * lf + a * h) * lr - C_Sf * (G * lr - a * h) * lf) - 1) * x[5]
        - mu / (x[3] * (lr + lf)) * (C_Sr * (G * lf + a * h) + C_Sf * (G * lr - a * h)) * x[6]
        + mu / (x[3] * (lr + lf)) * (C_Sf * (G * lr - a * h)) * x[2],
    ])


@pytest.mark.parametrize('grip', [1.0, 0.6, 0.4])
def test_matches_stock_model_below_the_limit(grip):
    mu = P['mu'] * grip
    rng = np.random.default_rng(0)
    for _ in range(50):
        # small slip, moderate speed, accel well inside μg
        x = np.array([0., 0., rng.uniform(-0.03, 0.03), rng.uniform(1.0, 3.0), 0.,
                      rng.uniform(-0.2, 0.2), rng.uniform(-0.01, 0.01)])
        u = np.array([0.1, rng.uniform(-1.0, 1.0)])
        uf, ur = tm.axle_utilization(x, u[1], **dict(P, mu=mu))
        if max(uf, ur) >= 1.0:
            continue
        got = tm.vehicle_dynamics_st_friction_circle(x, u, *args(mu=mu))
        np.testing.assert_allclose(got, stock_st(x, u, *args(mu=mu)), rtol=1e-9, atol=1e-9)


def test_lateral_force_is_capped_at_mu_fz():
    mu = P['mu'] * 0.4
    # Hard steer at speed: the linear model demands far more than μF_z.
    x = np.array([0., 0., 0.4, 3.0, 0., 0., 0.])
    u = np.array([0., 0.])
    uf, _ = tm.axle_utilization(x, 0.0, **dict(P, mu=mu))
    assert uf > 1.0
    lin = stock_st(x, u, *args(mu=mu))
    sat = tm.vehicle_dynamics_st_friction_circle(x, u, *args(mu=mu))
    assert abs(sat[5]) < abs(lin[5])
    # With β = ψ̇ = 0, ψ̈ = l_f·F_yf/I and the front force is exactly μ·F_zf.
    Fzf = P['m'] * G * P['lr'] / (P['lf'] + P['lr'])
    assert sat[5] == pytest.approx(P['lf'] * mu * Fzf / P['I'])
    # Total lateral acceleration (F_yf + F_yr)/m can never exceed μg.
    a_lat = (sat[6] + x[5]) * x[3]
    assert abs(a_lat) <= mu * G + 1e-9


def test_traction_limit_caps_longitudinal_accel():
    mu = P['mu'] * 0.4
    x = np.array([0., 0., 0., 2.0, 0., 0., 0.])
    sat = tm.vehicle_dynamics_st_friction_circle(x, np.array([0., 9.0]), *args(mu=mu))
    assert sat[3] == pytest.approx(mu * G)
    sat = tm.vehicle_dynamics_st_friction_circle(x, np.array([0., -9.0]), *args(mu=mu))
    assert sat[3] == pytest.approx(-mu * G)
    # Full grip: a_max (9.51) is below μg (10.29), so nothing changes.
    full = tm.vehicle_dynamics_st_friction_circle(x, np.array([0., 9.0]), *args())
    assert full[3] == pytest.approx(9.0)


def _simulate(fn, mu, steer, v0, T=2.0, dt=0.01, accel=0.0):
    x = np.array([0., 0., steer, v0, 0., 0., 0.])
    u = np.array([0., accel])
    out = []
    for _ in range(int(T / dt)):
        x = x + dt * fn(x, u, *args(mu=mu))
        out.append(x.copy())
    return np.array(out)


def test_low_grip_hard_corner_slides_instead_of_tracking():
    """Linear model: the car settles into a steady turn at any μ.
    Friction circle: same inputs at low grip give a large body slip angle."""
    mu = P['mu'] * 0.4
    lin = _simulate(stock_st, mu, steer=0.35, v0=3.0)
    sat = _simulate(tm.vehicle_dynamics_st_friction_circle, mu, steer=0.35, v0=3.0)
    assert np.all(np.isfinite(sat))
    # yaw rate stays within the friction-limited bound μg/v (+ transient slack)
    assert np.max(np.abs(sat[:, 5])) < np.max(np.abs(lin[:, 5]))
    # lateral acceleration v(ψ̇ + β̇) bounded by μg in the saturating model
    beta_dot = np.diff(sat[:, 6]) / 0.01
    a_lat = sat[1:, 3] * (sat[1:, 5] + beta_dot)
    assert np.max(np.abs(a_lat)) <= mu * G * 1.05


def test_rear_saturation_under_braking_can_spin():
    """Braking in a corner unloads the rear axle: with the friction circle
    the rear lets go and the body slip angle grows (oversteer). The linear
    model has no such mode."""
    mu = P['mu'] * 0.5
    x0 = dict(steer=0.25, v0=3.0, T=1.0, accel=-4.0)
    lin = _simulate(stock_st, mu, **x0)
    sat = _simulate(tm.vehicle_dynamics_st_friction_circle, mu, **x0)
    keep = sat[:, 3] >= 0.5
    assert np.max(np.abs(sat[keep, 6])) > 1.5 * np.max(np.abs(lin[keep, 6]))


def test_kinematic_branch_unchanged_at_low_speed():
    x = np.array([0., 0., 0.2, 0.3, 0.1, 0., 0.])
    u = np.array([0.5, 1.0])
    f = tm.vehicle_dynamics_st_friction_circle(x, u, *args())
    lwb = P['lf'] + P['lr']
    assert f[4] == pytest.approx(0.3 / lwb * np.tan(0.2))
    assert f[6] == 0.0


def test_install_swaps_f110_gym_integrator(monkeypatch):
    """install() rebinds base_classes.vehicle_dynamics_st, which RaceCar
    looks up at call time; 'linear' restores the stock function."""
    stock = object()
    bc = types.ModuleType('f110_gym.envs.base_classes')
    dm = types.ModuleType('f110_gym.envs.dynamic_models')
    bc.vehicle_dynamics_st = stock
    dm.vehicle_dynamics_st = stock
    envs = types.ModuleType('f110_gym.envs')
    envs.base_classes, envs.dynamic_models = bc, dm
    pkg = types.ModuleType('f110_gym')
    pkg.envs = envs
    for name, mod in [('f110_gym', pkg), ('f110_gym.envs', envs),
                      ('f110_gym.envs.base_classes', bc), ('f110_gym.envs.dynamic_models', dm)]:
        monkeypatch.setitem(sys.modules, name, mod)

    tm.install('friction_circle')
    assert bc.vehicle_dynamics_st is tm.vehicle_dynamics_st_friction_circle
    tm.install('linear')
    assert bc.vehicle_dynamics_st is stock
    with pytest.raises(ValueError):
        tm.install('pacejka')


def test_env_rejects_unknown_tire_model():
    from f1tenth_research.envs import F1TenthRMAEnv
    with pytest.raises(ValueError):
        F1TenthRMAEnv(config={'environment': {'tire_model': 'friction-circle'}})
