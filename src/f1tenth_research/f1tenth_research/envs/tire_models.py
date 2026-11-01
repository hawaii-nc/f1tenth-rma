"""
Tire models for f110_gym's single-track vehicle dynamics.

f110_gym 0.2.1 integrates ``vehicle_dynamics_st`` (CommonRoad single-track),
whose lateral tire force is *linear* in slip angle with no limit (see
docs/SIM_FIDELITY.md). Lowering μ there only makes the car understeer; it
can never slide or spin.

This module provides drop-in replacements with the exact same signature, so
``RealF110Wrapper`` can swap them into ``f110_gym.envs.base_classes``:

``linear``           f110_gym's stock model, unchanged.
``friction_circle``  Same linear cornering stiffness at small slip, but each
                     axle's lateral force is capped by its share of the
                     friction circle, |F_y| ≤ √((μF_z)² − F_x²), and
                     longitudinal acceleration is capped at μg. Below the
                     limit it matches the stock model term for term (except
                     the μg traction cap). Above it the front axle washes
                     out (plough) or the rear axle lets go (slide / spin).

Force formulation (it reproduces the stock linear equations exactly):

    F_zf = m(g·l_r − a·h)/L          F_zr = m(g·l_f + a·h)/L
    α_f  = δ − β − l_f·ψ̇/v           α_r  = −β + l_r·ψ̇/v
    F_yf = μ·C_Sf·F_zf·α_f           F_yr = μ·C_Sr·F_zr·α_r
    ψ̈   = (l_f·F_yf − l_r·F_yr)/I
    β̇   = (F_yf + F_yr)/(m·v) − ψ̇

The drive is treated as all-wheel (the Traxxas Slash 4×4), so F_x splits
between the axles in proportion to F_z. Each axle then has the same usable
lateral fraction, √(1 − (a/μg)²).

Not modelled: a force peak followed by fall-off (Pacejka), load transfer
between left and right wheels, and relaxation length. Gym-Khana's
STP/PAC2002 models cover those (docs/SIM_FIDELITY.md).
"""
import numpy as np

try:  # f110_gym depends on numba; tests run without it.
    from numba import njit
except ImportError:  # pragma: no cover - exercised only without numba
    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda f: f

G = 9.81
TIRE_MODELS = ('linear', 'friction_circle')


@njit(cache=True)
def _steering_constraint(steering_angle, steering_velocity, s_min, s_max, sv_min, sv_max):
    # Same as f110_gym.envs.dynamic_models.steering_constraint
    if (steering_angle <= s_min and steering_velocity <= 0) or \
            (steering_angle >= s_max and steering_velocity >= 0):
        steering_velocity = 0.
    elif steering_velocity <= sv_min:
        steering_velocity = sv_min
    elif steering_velocity >= sv_max:
        steering_velocity = sv_max
    return steering_velocity


@njit(cache=True)
def _accl_constraints(vel, accl, v_switch, a_max, v_min, v_max):
    # Same as f110_gym.envs.dynamic_models.accl_constraints
    if vel > v_switch:
        pos_limit = a_max * v_switch / vel
    else:
        pos_limit = a_max
    if (vel <= v_min and accl <= 0) or (vel >= v_max and accl >= 0):
        accl = 0.
    elif accl <= -a_max:
        accl = -a_max
    elif accl >= pos_limit:
        accl = pos_limit
    return accl


@njit(cache=True)
def vehicle_dynamics_st_friction_circle(x, u_init, mu, C_Sf, C_Sr, lf, lr, h, m, I,
                                        s_min, s_max, sv_min, sv_max, v_switch, a_max,
                                        v_min, v_max):
    """
    Single-track dynamics with a friction-circle-limited tire.
    Signature and state layout identical to f110_gym's vehicle_dynamics_st:
    x = [x, y, steer, v, yaw, yaw_rate, slip_angle], u = [steer_vel, accel].
    """
    sv = _steering_constraint(x[2], u_init[0], s_min, s_max, sv_min, sv_max)
    a = _accl_constraints(x[3], u_init[1], v_switch, a_max, v_min, v_max)
    # Traction limit: the tires cannot push or brake harder than μg.
    a_lim = mu * G
    if a > a_lim:
        a = a_lim
    elif a < -a_lim:
        a = -a_lim

    lwb = lf + lr
    f = np.zeros(7)
    if abs(x[3]) < 0.5:
        # Kinematic model at low speed, as in f110_gym.
        f[0] = x[3] * np.cos(x[4])
        f[1] = x[3] * np.sin(x[4])
        f[2] = sv
        f[3] = a
        f[4] = x[3] / lwb * np.tan(x[2])
        f[5] = a / lwb * np.tan(x[2]) + x[3] / (lwb * np.cos(x[2]) ** 2) * sv
        f[6] = 0.
        return f

    v = x[3]
    Fzf = m * (G * lr - a * h) / lwb
    Fzr = m * (G * lf + a * h) / lwb
    if Fzf < 0.:
        Fzf = 0.
    if Fzr < 0.:
        Fzr = 0.

    alpha_f = x[2] - x[6] - lf * x[5] / v
    alpha_r = -x[6] + lr * x[5] / v
    Fyf = mu * C_Sf * Fzf * alpha_f
    Fyr = mu * C_Sr * Fzr * alpha_r

    # Combined slip, AWD: the share of μF_z left for cornering.
    r = a / a_lim if a_lim > 0. else 0.
    lat_frac = np.sqrt(max(0., 1. - r * r))
    Fyf_max = mu * Fzf * lat_frac
    Fyr_max = mu * Fzr * lat_frac
    if Fyf > Fyf_max:
        Fyf = Fyf_max
    elif Fyf < -Fyf_max:
        Fyf = -Fyf_max
    if Fyr > Fyr_max:
        Fyr = Fyr_max
    elif Fyr < -Fyr_max:
        Fyr = -Fyr_max

    f[0] = v * np.cos(x[6] + x[4])
    f[1] = v * np.sin(x[6] + x[4])
    f[2] = sv
    f[3] = a
    f[4] = x[5]
    f[5] = (lf * Fyf - lr * Fyr) / I
    f[6] = (Fyf + Fyr) / (m * v) - x[5]
    return f


def axle_utilization(x, a, mu, C_Sf, C_Sr, lf, lr, h, m, **_):
    """
    (front, rear) unsaturated lateral demand / friction-circle capacity for
    state x and longitudinal acceleration a. Values ≥ 1 mean that axle is at
    its limit under the friction_circle model. For diagnostics and tests.
    """
    lwb = lf + lr
    v = x[3]
    Fzf = max(0., m * (G * lr - a * h) / lwb)
    Fzr = max(0., m * (G * lf + a * h) / lwb)
    alpha_f = x[2] - x[6] - lf * x[5] / v
    alpha_r = -x[6] + lr * x[5] / v
    r = min(1., abs(a) / (mu * G))
    frac = np.sqrt(1. - r * r)
    cap_f = mu * Fzf * frac
    cap_r = mu * Fzr * frac
    uf = abs(mu * C_Sf * Fzf * alpha_f) / cap_f if cap_f > 0 else np.inf
    ur = abs(mu * C_Sr * Fzr * alpha_r) / cap_r if cap_r > 0 else np.inf
    return uf, ur


def install(tire_model: str):
    """
    Point f110_gym's RaceCar integrator at the requested tire model.

    RaceCar.update_pose looks up ``vehicle_dynamics_st`` in
    f110_gym.envs.base_classes at call time, so rebinding that module
    attribute switches every car in this process. Idempotent; call it before
    each episode so environments with different models can share a process.
    """
    if tire_model not in TIRE_MODELS:
        raise ValueError(f"Unknown tire_model {tire_model!r}; choose from {TIRE_MODELS}")
    import f110_gym.envs.base_classes as bc
    import f110_gym.envs.dynamic_models as dm
    bc.vehicle_dynamics_st = (dm.vehicle_dynamics_st if tire_model == 'linear'
                              else vehicle_dynamics_st_friction_circle)
