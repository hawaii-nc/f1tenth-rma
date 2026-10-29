"""
Runtime safety shield: traffic-law speed rules enforced on the policy output.

Project record §9.7, mechanism (B): "rule as runtime shield", in the spirit of
Responsibility-Sensitive Safety (Shalev-Shwartz et al., 2017). No retraining:
the shield only ever lowers the commanded velocity.

Two rules, both grip-adaptive (μ is the estimated tire–road friction):

1. Assured Clear Distance Ahead (ACDA): "never drive faster than you can stop
   within the distance you can see":
       v ≤ sqrt(2 · μ g · max(d_forward − margin, 0))
   d_forward is the minimum LiDAR range in a forward cone.

2. Basic Speed Law: "speed reasonable for conditions" in a corner of
   curvature κ (lateral acceleration v²κ must fit in the friction circle):
       v ≤ sqrt(μ g / κ)
   κ is estimated from the commanded steering with the bicycle model,
   κ = tan(δ) / L, so the rule needs no map.

The sqrt in ACDA is steep as d → 0; v_min keeps the car able to creep out.
"""

from dataclasses import dataclass
from typing import Tuple

import numpy as np

G = 9.81


@dataclass
class ShieldConfig:
    wheelbase: float = 0.33
    forward_half_angle: float = np.deg2rad(15.0)  # forward cone for ACDA
    stop_margin: float = 0.30                     # m kept free after stopping
    braking_efficiency: float = 0.7               # fraction of μg usable for braking
    lateral_margin: float = 0.8                   # fraction of μg usable laterally
    v_min: float = 0.3                            # never command below this (m/s) unless blocked
    lidar_fov: float = np.deg2rad(270.0)          # Hokuyo UST-10LX field of view


def forward_distance(ranges: np.ndarray, cfg: ShieldConfig = ShieldConfig()) -> float:
    """Minimum range inside ±forward_half_angle of straight ahead."""
    ranges = np.asarray(ranges, dtype=np.float64)
    angles = np.linspace(-cfg.lidar_fov / 2, cfg.lidar_fov / 2, len(ranges))
    cone = np.abs(angles) <= cfg.forward_half_angle
    return float(np.min(ranges[cone])) if np.any(cone) else float(np.min(ranges))


def acda_speed_limit(d_forward: float, mu: float, cfg: ShieldConfig = ShieldConfig()) -> float:
    free = max(d_forward - cfg.stop_margin, 0.0)
    return float(np.sqrt(2.0 * cfg.braking_efficiency * mu * G * free))


def curvature_speed_limit(steer: float, mu: float, cfg: ShieldConfig = ShieldConfig()) -> float:
    kappa = abs(np.tan(steer)) / cfg.wheelbase
    if kappa < 1e-6:
        return float('inf')
    return float(np.sqrt(cfg.lateral_margin * mu * G / kappa))


def shield_velocity(
    v_cmd: float,
    steer_cmd: float,
    ranges: np.ndarray,
    mu: float,
    cfg: ShieldConfig = ShieldConfig(),
) -> Tuple[float, dict]:
    """
    Clip a commanded velocity to the tighter of the two rule limits.

    Args:
        v_cmd: policy velocity command (m/s)
        steer_cmd: policy steering command (rad)
        ranges: LiDAR ranges in metres, ordered right→left across the FOV
        mu: friction estimate (1.0 ≈ rubber on dry concrete)

    Returns:
        (shielded velocity, diagnostics dict)
    """
    d_fwd = forward_distance(ranges, cfg)
    v_acda = acda_speed_limit(d_fwd, mu, cfg)
    v_curve = curvature_speed_limit(steer_cmd, mu, cfg)
    v_limit = min(v_acda, v_curve)
    if d_fwd > cfg.stop_margin:
        v_limit = max(v_limit, cfg.v_min)
    v_out = float(min(v_cmd, v_limit))
    return v_out, {
        'd_forward': d_fwd,
        'v_acda': v_acda,
        'v_curve': v_curve,
        'active': v_out < v_cmd,
    }
