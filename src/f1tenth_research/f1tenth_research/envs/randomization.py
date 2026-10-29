"""
Domain Randomization Module for F1Tenth RMA
============================================

Implements Zhang et al. (2025) Section II-A: domain randomization with size factor c.
Maps physical parameters (et) -> intrinsic parameters (zt) via μ encoder.

Key components:
- Grip factor c ∈ [0,1]: scales tire friction coefficient μ
- Motor effectiveness factors: independent scaling per actuator (steering, drive)
- Mass/inertia scaling: correlated chassis parameter variation
- External disturbances: mid-episode randomized perturbations

Training range (δ=0.5 reference) stored as config. Supports sampling at arbitrary δ.
"""

import warnings

import numpy as np
from typing import Dict, Tuple, Optional
from enum import Enum


# Order of the 7-D physics vector e fed to the intrinsics encoder μ.
# Must match training (checkpoints' encoder.network.0.weight is (128, 7)).
PARAM_KEYS = (
    'grip_factor', 'mass_scale', 'inertia_scale',
    'motor_steering_scale', 'motor_drive_scale',
    'delay_steering', 'delay_drive',
)

# Physics vector the deployment node feeds μ when no φ estimate is available
# ("Blind" controller in the E-series experiments).
NOMINAL_PARAMS = (1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0)


def params_to_vector(params: Dict[str, float]) -> np.ndarray:
    return np.array([float(params.get(k, 0.0)) for k in PARAM_KEYS], dtype=np.float32)


class SampleMode(Enum):
    """Sampling mode for physics parameters."""
    TRAIN = "train"           # Sample from δ=0.5 training range
    GENERALIZATION = "generalization"  # Sample at arbitrary δ


class PhysicsRandomizer:
    """
    Samples randomized physics parameters (et) for F1Tenth domain randomization.
    
    References: Zhang et al. (2025) Table I - quadcopter randomization ranges.
    Adapted for F1Tenth with analogous scaling factors.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize randomizer with training range (δ=0.5).
        
        Args:
            config: Dictionary with hyperparameters. If None, use defaults.
        """
        # Merge so a partial YAML block still gets every default key.
        self.config = {**self._default_config(), **(config or {})}
        
        # Training range (δ=0.5 reference) - normalized nominal values
        # These define what "1.0" scaling factor means
        self.nominal_params = {
            'grip_factor': 1.0,              # μ tire friction nominal
            'mass_scale': 1.0,               # chassis mass scaling
            'inertia_scale': 1.0,            # rotational inertia scaling
            'motor_steering_scale': 1.0,     # steering servo effectiveness
            'motor_drive_scale': 1.0,        # drive motor effectiveness
            'delay_steering': 0.0,           # steering command delay (seconds)
            'delay_drive': 0.0,              # drive command delay (seconds)
        }
        
        # Training range bounds (Zhang's δ=0.5 reference)
        self.train_range = {
            'grip_factor': (0.4, 1.0),                      # c ∈ [0.4, 1.0] 
            'mass_scale': (0.8, 1.2),                       # ±20%
            'inertia_scale': (0.8, 1.2),                    # ±20%
            'motor_steering_scale': (0.8, 1.2),             # ±20%
            'motor_drive_scale': (0.8, 1.2),                # ±20%
            'delay_steering': (0.0, 0.05),                  # 0-50ms jitter
            'delay_drive': (0.0, 0.05),                     # 0-50ms jitter
        }
        
        # Correlation: if mass scales up, inertia scales similarly
        # (preserves rotational dynamics)
        self.correlated_params = {
            'mass_inertia': True,  # mass and inertia scale together
        }
    
    def _default_config(self) -> Dict:
        """Default hyperparameters."""
        return {
            'apply_post_scale_noise': True,  # ±20% uniform noise after scaling
            'noise_fraction': 0.20,           # ±20% noise magnitude
            'mid_episode_disturbance': True,  # randomly timed friction change
            'disturbance_timing': (0.3, 0.9),  # when (frac of episode) disturbance occurs
            'disturbance_magnitude': 0.3,     # friction reduction magnitude
        }
    
    def sample_training(self) -> Dict[str, float]:
        """
        Sample physics parameters from training distribution (δ=0.5).
        
        Returns:
            Dictionary of sampled parameters et = {grip_factor, mass_scale, ...}
        """
        params = {}
        
        # Sample base parameters independently
        for key, (lo, hi) in self.train_range.items():
            params[key] = np.random.uniform(lo, hi)
        
        # Apply correlations: mass and inertia should scale together
        if self.correlated_params['mass_inertia']:
            # Use the sampled mass_scale for inertia_scale as well,
            # with slight decorrelation (±5%)
            base = params['mass_scale']
            params['inertia_scale'] = base * np.random.uniform(0.95, 1.05)
        
        # Apply post-sampling noise (±20% uniform)
        if self.config['apply_post_scale_noise']:
            noise_mag = self.config['noise_fraction']
            for key in params:
                noise = np.random.uniform(-noise_mag, noise_mag)
                params[key] *= (1.0 + noise)

        # Noise can push grip above nominal (μ > 1.0489 is unphysical for the
        # car's rubber on concrete) or delays negative; keep samples sane.
        params['grip_factor'] = float(np.clip(params['grip_factor'], 0.05, 1.0))
        params['delay_steering'] = max(0.0, params['delay_steering'])
        params['delay_drive'] = max(0.0, params['delay_drive'])

        return params
    
    def sample_at_generalization_level(self, delta: float) -> Dict[str, float]:
        """
        Sample physics parameters at generalization difficulty level δ.
        
        δ = 0: nominal (all parameters = 1.0)
        δ = 0.5: training range (default)
        δ = 1, 2, 4, 8: increasing generalization difficulty
        
        Maps: training range [min, max] -> extrapolated range at δ via linear scaling
        
        Args:
            delta: Generalization difficulty level (0 to 8+)
            
        Returns:
            Dictionary of sampled parameters at the given δ level
        """
        if delta == 0:
            # Nominal - no randomization
            return self.nominal_params.copy()
        
        params = {}
        
        # Linearly scale the training range bounds by δ relative to training (δ=0.5)
        # scaling_factor = δ / 0.5
        scale_factor = delta / 0.5
        
        for key, (train_lo, train_hi) in self.train_range.items():
            # Nominal value (typically in middle or at nominal)
            nominal = self.nominal_params[key]
            
            # Scaled bounds
            delta_lo = (train_lo - nominal) * scale_factor + nominal
            delta_hi = (train_hi - nominal) * scale_factor + nominal
            
            # Ensure no negative scales
            delta_lo = max(0.01, delta_lo)
            delta_hi = max(delta_lo + 0.01, delta_hi)
            
            params[key] = np.random.uniform(delta_lo, delta_hi)
        
        # Apply correlations
        if self.correlated_params['mass_inertia']:
            base = params['mass_scale']
            params['inertia_scale'] = base * np.random.uniform(0.95, 1.05)
        
        # Apply post-sampling noise
        if self.config['apply_post_scale_noise']:
            noise_mag = self.config['noise_fraction']
            for key in params:
                noise = np.random.uniform(-noise_mag, noise_mag)
                params[key] *= (1.0 + noise)

        # Generalization levels may push grip past nominal on purpose (δ>0.5),
        # but never to zero/negative friction or negative delay.
        params['grip_factor'] = max(0.05, params['grip_factor'])
        params['delay_steering'] = max(0.0, params['delay_steering'])
        params['delay_drive'] = max(0.0, params['delay_drive'])
        
        return params
    
    def sample(self, mode: SampleMode = SampleMode.TRAIN, delta: float = 0.5) -> Dict[str, float]:
        """
        Unified sampling interface.
        
        Args:
            mode: TRAIN or GENERALIZATION
            delta: For GENERALIZATION mode, the difficulty level (0-8+)
            
        Returns:
            Sampled physics parameters et
        """
        if mode == SampleMode.TRAIN:
            return self.sample_training()
        elif mode == SampleMode.GENERALIZATION:
            return self.sample_at_generalization_level(delta)
        else:
            raise ValueError(f"Unknown sample mode: {mode}")
    
    def sample_disturbance_time(self) -> Optional[float]:
        """
        Decide at reset whether this episode gets a mid-episode grip drop, and when.

        Returns the episode-progress fraction at which the drop fires, or None.
        30% of episodes get exactly one drop, uniformly timed inside
        disturbance_timing (default 30–90% of the episode).
        """
        if not self.config.get('mid_episode_disturbance', False):
            return None
        if np.random.rand() >= self.config.get('disturbance_prob', 0.3):
            return None
        timing_lo, timing_hi = self.config.get('disturbance_timing', (0.3, 0.9))
        return float(np.random.uniform(timing_lo, timing_hi))

    def apply_disturbance(self, params: Dict[str, float]) -> Dict[str, float]:
        """
        Return a copy of params with the one-shot grip drop applied
        (simulated wet patch). The caller must push the new grip into the
        simulator; editing this dict alone does not change the physics.
        """
        out = dict(params)
        scale = self.config.get(
            'disturbance_friction_scale',
            1.0 - self.config.get('disturbance_magnitude', 0.3),
        )
        out['grip_factor'] = float(params['grip_factor']) * float(scale)
        return out

    def add_mid_episode_disturbance(
        self,
        params: Dict[str, float],
        episode_progress: float
    ) -> Dict[str, float]:
        """
        Deprecated, do not use (bugs C1, C2). F1TenthRMAEnv uses
        sample_disturbance_time() + apply_disturbance() instead.
        """
        warnings.warn(
            "add_mid_episode_disturbance is deprecated; see docstring",
            DeprecationWarning,
        )
        return params
    
    def params_to_description(self, params: Dict[str, float]) -> str:
        """
        Human-readable description of sampled parameters.
        Useful for logging and debugging.
        """
        lines = [
            f"grip_factor={params['grip_factor']:.3f}",
            f"mass_scale={params['mass_scale']:.3f}",
            f"inertia_scale={params['inertia_scale']:.3f}",
            f"motor_steering_scale={params['motor_steering_scale']:.3f}",
            f"motor_drive_scale={params['motor_drive_scale']:.3f}",
            f"delay_steering={params['delay_steering']:.4f}s",
            f"delay_drive={params['delay_drive']:.4f}s",
        ]
        return ", ".join(lines)
