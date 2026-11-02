"""
Expert Controller Module for F1Tenth RMA
=========================================

Implements expert controllers (IL target) that take ground-truth randomized physics
parameters as input and adapt their control law accordingly.

This mirrors Zhang et al. (2025) PD* expert, which had access to ground-truth
model parameters of each sampled quadcopter. For F1Tenth, we implement:
- Pure Pursuit with grip-aware speed modulation
- Future: MPCC (Model Predictive Contouring Control)

Reference: Zhang et al. (2025) Section II-B - Expert Policy PD*
"""

import numpy as np
from typing import Dict, Tuple
import warnings


class F1TenthExpertController:
    """
    Base class for F1Tenth expert controllers.
    
    Takes ground-truth physics parameters et and adapts control law.
    Outputs: expert action a_exp = [steering_cmd, throttle_cmd]
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize expert controller.
        
        Args:
            config: Dictionary with controller hyperparameters
        """
        # merge over defaults so a partial YAML block keeps every key (bug C6)
        self.config = {**self._default_config(), **(config or {})}
    
    def _default_config(self) -> Dict:
        """Default configuration - override in subclasses."""
        return {}
    
    def compute_action(
        self,
        state: Dict,
        physics_params: Dict,
    ) -> np.ndarray:
        """
        Compute expert action given state and physics parameters.
        
        Args:
            state: Current state dict containing:
              - 'position': (x, y) coordinates
              - 'yaw': heading angle (rad)
              - 'velocity': longitudinal velocity (m/s)
              - 'yaw_rate': angular velocity (rad/s)
            physics_params: Randomized physics parameters et containing:
              - 'grip_factor': tire friction scaling
              - 'mass_scale': chassis mass scaling
              - 'motor_steering_scale': steering effectiveness
              - 'motor_drive_scale': drive motor effectiveness
              - etc.
              
        Returns:
            Expert action [steering_cmd, throttle_cmd]
        """
        raise NotImplementedError("Subclasses must implement compute_action()")


class PurePursuitExpert(F1TenthExpertController):
    """
    Pure Pursuit expert controller with grip-aware speed modulation.
    
    Extends standard Pure Pursuit with adaptation to grip_factor:
    - Higher grip (c closer to 1.0): enable aggressive steering, maintain higher speed
    - Lower grip (c closer to 0.4): reduce speed, use gentler steering to maintain traction
    
    Reference: Pure Pursuit control law (Coulter, 1992) + Zhang et al. adaptation
    """
    
    def __init__(self, config: Dict = None, waypoints: np.ndarray = None):
        """
        Initialize Pure Pursuit expert.
        
        Args:
            config: Controller config dict
            waypoints: Nx2 array of reference waypoints (x, y)
        """
        super().__init__(config)
        self.waypoints = waypoints if waypoints is not None else np.array([])
        
        if len(self.waypoints) == 0:
            warnings.warn("PurePursuitExpert initialized without waypoints")
        elif self.config.get('corner_speed', False):
            self._precompute_corner_profile()

    # ----------------------------------------------------- corner speed profile
    def _precompute_corner_profile(self):
        """Arc length and local turning radius (3-point circle over ~0.5 m) per waypoint."""
        xy = np.asarray(self.waypoints, dtype=float)[:, :2]
        n = len(xy)
        seg = np.hypot(*np.diff(np.vstack([xy, xy[:1]]), axis=0).T)
        self._ds = float(np.median(seg))
        self._arc = np.concatenate([[0.0], np.cumsum(seg[:-1])])
        k = max(1, int(round(0.25 / max(self._ds, 1e-6))))
        a, b, c = xy[(np.arange(n) - k) % n], xy, xy[(np.arange(n) + k) % n]
        ab, bc, ca = np.hypot(*(b - a).T), np.hypot(*(c - b).T), np.hypot(*(a - c).T)
        area = np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])) / 2
        self._radius = np.where(area > 1e-12, ab * bc * ca / np.maximum(4 * area, 1e-12), np.inf)

    def _corner_speed_limit(self, closest_idx: int, grip_factor: float) -> float:
        """
        Highest speed from which the car can still take every corner within
        corner_preview_m: v ≤ √(v_c² + 2·a_b·d), v_c = √(f·μ·g·R), a_b = f_b·μ·g.
        μ is the true friction (privileged, like the rest of the expert's inputs).
        """
        mu = float(self.config.get('mu_nominal', 1.0489)) * float(grip_factor)
        g = 9.81
        f_lat = float(self.config.get('lat_accel_frac', 0.6))
        f_brk = float(self.config.get('brake_accel_frac', 0.5))
        n = len(self._radius)
        # Look far enough ahead to brake from top speed: max(preview, v_max²/(2·a_b) + 0.5 m)
        a_b = f_brk * mu * g
        preview = max(float(self.config.get('corner_preview_m', 3.0)),
                      float(self.config.get('max_speed', 3.0)) ** 2 / (2 * max(a_b, 1e-6)) + 0.5)
        m = min(n, int(preview / max(self._ds, 1e-6)) + 1)
        idx = (closest_idx + np.arange(m)) % n
        d = np.arange(m) * self._ds
        v_c = np.sqrt(f_lat * mu * g * self._radius[idx])
        return float(np.min(np.sqrt(v_c ** 2 + 2 * f_brk * mu * g * d)))
    
    def _default_config(self) -> Dict:
        """Default Pure Pursuit parameters."""
        return {
            'wheelbase': 0.33,              # F1Tenth wheelbase (meters)
            'lookahead_distance_base': 1.5, # Base lookahead distance (meters)
            'nominal_speed': 2.0,           # Nominal cruising speed (m/s)
            'max_speed': 3.0,               # = env max_velocity; throttle +1 maps here
            'max_steering': 0.4189,         # Max steering angle (rad)
            'min_speed': 0.5,               # Minimum speed (m/s)
            
            # Grip-aware modulation
            'grip_aware': True,
            'grip_speed_scale': {
                # grip_factor -> speed multiplier
                # At grip_factor=1.0: full nominal speed
                # At grip_factor=0.4: reduced speed for traction
                0.4: 0.6,   # Low grip: 60% nominal speed
                0.7: 0.85,  # Medium grip: 85% nominal speed
                1.0: 1.0,   # High grip: 100% nominal speed
            },
            'grip_steering_scale': {
                # grip_factor -> steering angle multiplier
                # Gentler steering on low grip to avoid skidding
                0.4: 0.7,
                0.7: 0.85,
                1.0: 1.0,
            },
        }
    
    def compute_action(
        self,
        state: Dict,
        physics_params: Dict,
    ) -> np.ndarray:
        """
        Compute Pure Pursuit action with grip-aware modulation.
        
        Args:
            state: Current state {position, yaw, velocity, yaw_rate, ...}
            physics_params: Physics params including grip_factor
            
        Returns:
            [steering_cmd, throttle_cmd]
        """
        if len(self.waypoints) == 0:
            # Fallback: no waypoints, return neutral action
            return np.array([0.0, 0.0], dtype=np.float32)
        
        # Extract state
        x, y = state.get('position', (0, 0))
        yaw = state.get('yaw', 0.0)
        current_velocity = state.get('velocity', 0.0)
        
        # Find lookahead point
        target = self._find_lookahead_point(x, y, current_velocity)
        
        # Compute steering command via Pure Pursuit
        steering = self._compute_pure_pursuit_steering(
            x, y, yaw, target, current_velocity
        )
        
        # Adapt for grip factor
        grip_factor = physics_params.get('grip_factor', 1.0)
        
        if self.config['grip_aware']:
            # Scale steering angle based on grip
            steering_scale = self._interpolate_grip_scale(
                grip_factor, self.config['grip_steering_scale']
            )
            steering *= steering_scale
            
            # Compute speed command based on grip
            speed_scale = self._interpolate_grip_scale(
                grip_factor, self.config['grip_speed_scale']
            )
            desired_speed = self.config['nominal_speed'] * speed_scale
        else:
            desired_speed = self.config['nominal_speed']

        if self.config.get('corner_speed', False) and len(self.waypoints):
            closest = int(np.argmin(np.hypot(self.waypoints[:, 0] - x, self.waypoints[:, 1] - y)))
            desired_speed = min(desired_speed, self._corner_speed_limit(closest, grip_factor))
        
        # Clamp steering to physical limits
        steering = np.clip(steering, -self.config['max_steering'], self.config['max_steering'])
        
        desired_speed = float(np.clip(desired_speed, self.config['min_speed'], self.config['max_speed']))

        # env maps throttle to an absolute setpoint: v = (thr + 1)/2 * v_max (bug C7)
        throttle = float(np.clip(2.0 * desired_speed / self.config['max_speed'] - 1.0, -1.0, 1.0))
        
        return np.array([steering, throttle], dtype=np.float32)
    
    def _find_lookahead_point(self, x: float, y: float, velocity: float = 0.0) -> Tuple[float, float]:
        """
        Find the lookahead point on the reference trajectory.
        
        Searches forward along waypoints to find one at lookahead_distance.
        
        Args:
            x, y: Current position
            
        Returns:
            (target_x, target_y) coordinates
        """
        lookahead = self.config['lookahead_distance_base'] + \
            float(self.config.get('lookahead_speed_gain', 0.0)) * max(0.0, float(velocity))
        
        # Compute distances to all waypoints
        dx = self.waypoints[:, 0] - x
        dy = self.waypoints[:, 1] - y
        distances = np.sqrt(dx**2 + dy**2)
        
        # Find closest waypoint
        closest_idx = np.argmin(distances)
        
        # Search forward to find one at lookahead distance
        n = len(self.waypoints)
        for i in range(n):
            idx = (closest_idx + i) % n
            if distances[idx] >= lookahead:
                return tuple(self.waypoints[idx])
        
        # Fallback: return closest
        return tuple(self.waypoints[closest_idx])
    
    def _compute_pure_pursuit_steering(
        self,
        x: float,
        y: float,
        yaw: float,
        target: Tuple[float, float],
        velocity: float = 0.0,
    ) -> float:
        """
        Compute steering command via Pure Pursuit control law.
        
        ψ = atan2(2 * L * sin(α) / ℓ)
        where:
          L: wheelbase
          α: angle to target relative to heading
          ℓ: lookahead distance
        
        Args:
            x, y: Current position
            yaw: Current heading (rad)
            target: Target point (tx, ty)
            
        Returns:
            Steering angle command (rad)
        """
        tx, ty = target
        
        # Angle to target in world frame
        angle_to_target = np.arctan2(ty - y, tx - x)
        
        # Angle relative to current heading
        alpha = angle_to_target - yaw
        
        # Normalize to [-π, π]
        while alpha > np.pi:
            alpha -= 2 * np.pi
        while alpha < -np.pi:
            alpha += 2 * np.pi
        
        # Pure Pursuit formula
        wheelbase = self.config['wheelbase']
        lookahead = self.config['lookahead_distance_base'] + \
            float(self.config.get('lookahead_speed_gain', 0.0)) * max(0.0, float(velocity))
        
        steering = np.arctan2(2.0 * wheelbase * np.sin(alpha), lookahead)
        return steering
    
    def _interpolate_grip_scale(
        self,
        grip_factor: float,
        scale_table: Dict[float, float],
    ) -> float:
        """
        Interpolate speed/steering scale factor based on grip_factor.
        
        Linear interpolation between defined points.
        
        Args:
            grip_factor: Current grip factor (typically 0.4-1.0)
            scale_table: {grip_value: scale_factor} mapping
            
        Returns:
            Interpolated scale factor
        """
        # Sort table by grip factor
        sorted_grips = sorted(scale_table.keys())
        
        # Clamp to range
        if grip_factor <= sorted_grips[0]:
            return scale_table[sorted_grips[0]]
        if grip_factor >= sorted_grips[-1]:
            return scale_table[sorted_grips[-1]]
        
        # Find bracketing points
        for i in range(len(sorted_grips) - 1):
            g1, g2 = sorted_grips[i], sorted_grips[i+1]
            if g1 <= grip_factor <= g2:
                # Linear interpolation
                frac = (grip_factor - g1) / (g2 - g1)
                scale1 = scale_table[g1]
                scale2 = scale_table[g2]
                return scale1 + frac * (scale2 - scale1)
        
        # Shouldn't reach here
        return 1.0


class MPCCExpert(F1TenthExpertController):
    """
    MPCC (Model Predictive Contouring Control) expert.
    
    More advanced than Pure Pursuit: uses explicit model of vehicle dynamics
    and solves finite-horizon optimal control problem.
    
    TODO: Implement full MPC formulation with:
    - Kinematic bicycle model
    - QP-based trajectory optimization
    - Grip-aware cost function weights
    
    For now, placeholder that falls back to Pure Pursuit.
    """
    
    def __init__(self, config: Dict = None, waypoints: np.ndarray = None):
        super().__init__(config)
        self.waypoints = waypoints
        self._pure_pursuit_fallback = PurePursuitExpert(config, waypoints)
    
    def compute_action(
        self,
        state: Dict,
        physics_params: Dict,
    ) -> np.ndarray:
        """Fallback to Pure Pursuit for now."""
        return self._pure_pursuit_fallback.compute_action(state, physics_params)


__all__ = [
    'F1TenthExpertController',
    'PurePursuitExpert',
    'MPCCExpert',
]
