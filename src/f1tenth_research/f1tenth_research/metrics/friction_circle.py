"""
Friction-circle utilization ρ: the project's safety-calibration metric.

    ρ = sqrt(a_lat² + a_long²) / (μ g)

Fraction of the tire friction circle (Milliken & Milliken, Race Car Vehicle
Dynamics, 1995) the car is spending: 0 = coasting, 1 = at the physical limit.
A calibrated driver holds ρ roughly constant as grip changes: a steady
margin, not a steady speed.

a_lat is computed as v · yaw_rate (steady-state lateral acceleration of a
point mass on a circular path); a_long as the finite difference of v.

Simulator caveat: f110_gym's tire model is linear in slip with no saturation,
so ρ > 1 is reachable without loss of control. ρ in simulation therefore
measures *how much grip the policy chose to ask for*, not proximity to an
actual loss-of-traction event. See docs/SIM_FIDELITY.md.
"""

from typing import Dict, Iterable

import numpy as np

G = 9.81
NOMINAL_MU = 1.0489  # f110_gym default μ; grip_factor 1.0 ↔ this value


def utilization(velocity, yaw_rate, accel_long, mu) -> np.ndarray:
    """Per-step ρ. All arguments broadcast; mu is the absolute friction coefficient."""
    v = np.asarray(velocity, dtype=np.float64)
    a_lat = v * np.asarray(yaw_rate, dtype=np.float64)
    a_long = np.asarray(accel_long, dtype=np.float64)
    return np.hypot(a_lat, a_long) / (np.asarray(mu, dtype=np.float64) * G)


def utilization_from_grip(velocity, yaw_rate, accel_long, grip_factor) -> np.ndarray:
    return utilization(velocity, yaw_rate, accel_long, NOMINAL_MU * np.asarray(grip_factor))


def episode_mean_rho(rho_steps: Iterable[float], min_speed_mask=None) -> float:
    """
    Mean ρ over an episode: the per-episode statistic used in the poster
    (mean per episode, then averaged per condition).
    """
    r = np.asarray(list(rho_steps), dtype=np.float64)
    if min_speed_mask is not None:
        r = r[np.asarray(min_speed_mask, dtype=bool)]
    return float(np.mean(r)) if r.size else float('nan')


def calibration_gaps(rho_by_grip: Dict[str, Dict[float, float]]) -> Dict[str, Dict[float, float]]:
    """
    Gap of each controller's mean ρ to the Oracle at each grip level, and the
    fraction of the Blind→Oracle gap closed by φ.

    rho_by_grip: {'oracle': {μ: ρ}, 'phi': {μ: ρ}, 'blind': {μ: ρ}}
    Returns {'phi_gap': {μ: ..}, 'blind_gap': {μ: ..}, 'gap_closed': {μ: ..}}
    """
    out = {'phi_gap': {}, 'blind_gap': {}, 'gap_closed': {}}
    for mu, r_or in rho_by_grip['oracle'].items():
        phi_gap = abs(rho_by_grip['phi'][mu] - r_or)
        blind_gap = abs(rho_by_grip['blind'][mu] - r_or)
        out['phi_gap'][mu] = phi_gap
        out['blind_gap'][mu] = blind_gap
        out['gap_closed'][mu] = (1.0 - phi_gap / blind_gap) if blind_gap > 1e-12 else float('nan')
    return out


def cross_grip_swing(rho_by_grip: Dict[float, float], grips: Iterable[float]) -> float:
    """Variance of a controller's mean ρ across grip levels (lower = steadier margin)."""
    return float(np.var([rho_by_grip[g] for g in grips]))


def bootstrap_calibration(rho_episodes: Dict[str, Dict[float, np.ndarray]], grips: Iterable[float],
                          n_boot: int = 2000, ci: float = 0.95, seed: int = 0) -> Dict:
    """
    Paired bootstrap CIs for the E1/E2 headline numbers.

    rho_episodes: {'oracle'|'phi'|'blind': {μ: per-episode mean ρ, ordered by seed}}.
    Episode i used the same seed (start pose, track, physics draw) for every
    controller and grip, so one resampled set of episode indices is applied to
    all cells. That keeps the pairing, which is what makes the CIs tight.

    Returns {'gap_closed': {μ: (lo, hi)}, 'blind_over_phi_variance_ratio': (lo, hi),
             'n_boot': n_boot, 'ci': ci}. A CI is (nan, nan) where the statistic
    is undefined in most resamples (e.g. μ = 1.0, where Blind equals Oracle).
    """
    grips = list(grips)
    ctrls = ('oracle', 'phi', 'blind')
    arr = {c: {g: np.asarray(rho_episodes[c][g], dtype=np.float64) for g in grips} for c in ctrls}
    n = {len(arr[c][g]) for c in ctrls for g in grips}
    if len(n) != 1:
        raise ValueError(f'paired bootstrap needs the same episode count in every cell, got {sorted(n)}')
    n = n.pop()
    rng = np.random.default_rng(seed)
    gap = {g: np.empty(n_boot) for g in grips}
    ratio = np.empty(n_boot)
    with np.errstate(invalid='ignore', divide='ignore'):
        for b in range(n_boot):
            idx = rng.integers(0, n, size=n)
            means = {c: {g: np.nanmean(arr[c][g][idx]) for g in grips} for c in ctrls}
            for g in grips:
                blind_gap = abs(means['blind'][g] - means['oracle'][g])
                phi_gap = abs(means['phi'][g] - means['oracle'][g])
                gap[g][b] = 1.0 - phi_gap / blind_gap if blind_gap > 1e-12 else np.nan
            v_phi = cross_grip_swing(means['phi'], grips)
            v_blind = cross_grip_swing(means['blind'], grips)
            ratio[b] = v_blind / v_phi if v_phi > 0 else np.nan

    q = [100 * (1 - ci) / 2, 100 * (1 + ci) / 2]

    def interval(x):
        x = x[np.isfinite(x)]
        if x.size < 0.5 * n_boot:
            return (float('nan'), float('nan'))
        lo, hi = np.percentile(x, q)
        return (float(lo), float(hi))

    return {'gap_closed': {g: interval(gap[g]) for g in grips},
            'blind_over_phi_variance_ratio': interval(ratio),
            'n_boot': n_boot, 'ci': ci}
