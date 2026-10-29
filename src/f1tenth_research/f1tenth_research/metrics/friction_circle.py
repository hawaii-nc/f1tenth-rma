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
