"""
F1Tenth Gymnasium Environment Wrapper for RMA
==============================================

Wraps f1tenth_gym simulator with domain randomization, reward function, and
state/action space specifications for Zhang et al. (2025) RMA training.

Observation space (xt), final (v42) configuration = 113-D:
  - current_velocity: longitudinal velocity (m/s)
  - current_steering_angle: last applied steering (rad)
  - desired_velocity: previous velocity command (m/s)
  - desired_steering_angle: previous steering command (rad)
  - yaw_rate: angular velocity around z-axis (rad/s)
  - 108 LiDAR beams, evenly subsampled from 1080, clipped to 10 m, /10

No map, waypoint, raceline or pose information is in the observation -
this is what makes the policy and φ map-agnostic.

Action space (at):
  - steering_angle_cmd: steering command (rad), |δ| ≤ 0.4189
  - throttle_cmd ∈ [-1, 1], mapped linearly to [0, max_velocity] m/s

Config keys honoured under config['environment'] (see configs/final_phase1_v42.yaml):
  max_velocity, tracks, track, max_episode_steps, drift_spawn_prob,
  tire_model ('linear' = stock f110_gym, default; 'friction_circle'),
  observation.{include_lidar, lidar_beams, lidar_max_range,
               lidar_noise_std, lidar_dropout_prob},
  randomization.*, reward.*

Reset options (all optional):
  training (bool)          sample physics from the training range (default True)
  delta (float)            generalization difficulty when training=False
  physics_params (dict)    override sampled physics (merged over nominal);
                           used by the E-series experiments to force μ
  disturbance_step (int)   force the grip drop at this step (E3); -1 disables
  disturbance_grip (float) grip_factor after the forced drop
  track (str)              force a specific track
  spawn_frac (float)       start at this fraction of the lap (default: random
                           when training and environment.random_spawn is
                           true (default), else the fixed start line)
  obs_noise (bool)         LiDAR noise/dropout on/off (default: on iff training)
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Tuple, Optional
import warnings

try:
    from .real_env import RealF110Wrapper
    F1TENTH_GYM_AVAILABLE = True
except ImportError:
    F1TENTH_GYM_AVAILABLE = False
    warnings.warn(
        "f110_gym not available - using mock environment."
    )

from .randomization import (
    PhysicsRandomizer, SampleMode, NOMINAL_PARAMS, PARAM_KEYS, params_to_vector,
)
from .reward import RewardComputer
from .tire_models import TIRE_MODELS
from ..paths import centerline_path, map_base

MAX_STEER = 0.4189
DRIFT_SPAWN_MAX_HEADING = 0.35  # rad; reconstruction, see docs/RECONSTRUCTION.md


class F1TenthRMAEnv(gym.Env):
    """
    F1Tenth Gymnasium environment for RMA training.

    Integrates:
    - Domain randomization (physics parameter sampling)
    - Composite reward function
    - State/action spaces
    - Episode termination logic

    Reference: Zhang et al. (2025) Section II - System Setup and Randomization
    """

    metadata = {'render_modes': [None, 'human']}

    # Optional callable track -> simulator wrapper (same interface as
    # RealF110Wrapper). Tests inject a lightweight fake simulator here.
    wrapper_factory = None

    def __init__(
        self,
        config: Dict = None,
        render_mode: str = None,
        track: str = None,
        max_episode_steps: int = None,
    ):
        """
        Initialize F1Tenth RMA environment.

        Args:
            config: Full YAML config dict (environment settings under 'environment')
            render_mode: Rendering mode ('human' or None)
            track: Track name; overrides config. If None, uses config 'tracks'
                   (sampled per episode) or config 'track'.
            max_episode_steps: Maximum steps per episode; overrides config.
        """
        super().__init__()

        # config is the full YAML; environment-specific settings (reward,
        # randomization, observation) live under config['environment'].
        full_config = config or {}
        self.config = full_config.get('environment', None) or self._default_config()
        self.render_mode = render_mode

        if track is not None:
            self.tracks = [track]
        else:
            self.tracks = list(self.config.get('tracks') or [self.config.get('track', 'aut')])
        self.track_weights = np.ones(len(self.tracks)) / len(self.tracks)
        self.track = self.tracks[0]
        self.max_episode_steps = max_episode_steps or self.config.get('max_episode_steps', 1000)
        # 8.0 for the old June checkpoints, 3.0 for v27 onward
        self.max_velocity = float(self.config.get('max_velocity', 8.0))
        self.drift_spawn_prob = float(self.config.get('drift_spawn_prob', 0.0))
        self.tire_model = str(self.config.get('tire_model', 'linear'))
        if self.tire_model not in TIRE_MODELS:
            # Checked here so a typo can never silently fall back to the mock env.
            raise ValueError(f"environment.tire_model={self.tire_model!r}; choose from {TIRE_MODELS}")

        # Initialize components
        self.randomizer = PhysicsRandomizer(self.config.get('randomization', {}))
        self.reward_computer = RewardComputer(self.config.get('reward', {}))

        self._centerlines: Dict[str, Optional[np.ndarray]] = {}
        self._wrappers: Dict[str, object] = {}
        self.base_env = None
        self._select_track(self.track)

        # State-action space definition
        self._setup_spaces()

        # Episode state
        self.current_physics_params = None
        self.prev_action = None
        self.current_state = None
        self.episode_step = 0
        self.total_episode_reward = 0.0
        self._disturbance_step = None
        self._disturbance_grip = None
        self._obs_noise = True
        self._prev_velocity = 0.0

    # ------------------------------------------------------------------ tracks
    def _load_centerline(self, track: str) -> Optional[np.ndarray]:
        if track not in self._centerlines:
            path = centerline_path(track)
            cl = None
            if path.exists():
                try:
                    cl = np.loadtxt(path, delimiter=',')[:, 0:2]
                except Exception:
                    cl = None
            self._centerlines[track] = cl
        return self._centerlines[track]

    def _resolve_map_name(self, track: str) -> str:
        """
        Map a track identifier to its f110_gym map path (no extension --
        F110Env appends .png/.yaml itself).

        'example_map' is special-cased to f1tenth_gym's bundled example,
        used for the original Phase 1 validation run.
        """
        if track == 'example_map':
            return '/f1tenth_gym/examples/example_map'
        return map_base(track)

    def _select_track(self, track: str):
        self.track = track
        cl = self._load_centerline(track)
        # None clears the previous track's centerline (progress reward -> 0)
        self.reward_computer.set_centerline(cl)
        if track not in self._wrappers:
            self._wrappers[track] = self._make_wrapper(track)
        self.base_env = self._wrappers[track]

    def _make_wrapper(self, track: str):
        """Simulator backend for one track; None -> mock (zeros) mode."""
        if self.wrapper_factory is not None:
            return self.wrapper_factory(track)
        if not F1TENTH_GYM_AVAILABLE:
            return None
        try:
            return RealF110Wrapper(map_name=self._resolve_map_name(track), timestep=0.01, track=track,
                                   tire_model=self.tire_model)
        except Exception as e:
            warnings.warn(f"Failed to initialize f110_gym wrapper for {track}: {e}")
            return None

    def set_track_weights(self, weights):
        """Curriculum hook: per-track sampling weights (track_reweight_interval)."""
        w = np.asarray(weights, dtype=np.float64)
        floor = float(self.config.get('track_weight_floor', 0.0))
        w = np.maximum(w, floor)
        self.track_weights = w / w.sum()

    def _default_config(self) -> Dict:
        """Default environment configuration."""
        return {
            'randomization': {},
            'reward': {},
            'observation': {
                'include_lidar': False,  # LiDAR observations (if available)
                'lidar_beams': 36,
                'include_imu': True,  # IMU (yaw rate)
                'normalize_obs': True,
            },
        }

    def _setup_spaces(self):
        """
        Define observation and action spaces.

        Observation (xt): [v_current, steering_current, v_desired, steering_desired, yaw_rate, ...]
        Action (at): [steering_cmd, throttle_cmd]
        """
        obs_config = self.config.get('observation', {})

        # Base observation dimension: 5 core signals
        obs_dim = 5  # v, steering, v_des, steering_des, yaw_rate

        # Add lidar if enabled
        if obs_config.get('include_lidar', False):
            obs_dim += obs_config.get('lidar_beams', 36)

        # Observation space: all continuous, unbounded (relative to nominal ranges)
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_dim,),
            dtype=np.float32
        )

        # Action space: steering angle + throttle/velocity command
        self.action_space = spaces.Box(
            low=np.array([-MAX_STEER, -1.0], dtype=np.float32),
            high=np.array([MAX_STEER, 1.0], dtype=np.float32),
            dtype=np.float32
        )

    def throttle_to_velocity(self, throttle: float) -> float:
        return (float(throttle) + 1.0) / 2.0 * self.max_velocity

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Dict = None,
    ) -> Tuple[np.ndarray, Dict]:
        """
        Reset environment to start of episode.

        Samples new randomized physics parameters (et) and resets base environment.
        See module docstring for supported options.
        """
        if seed is not None:
            np.random.seed(seed)
        options = options or {}

        # Track: forced, or sampled per episode from the (weighted) list
        track = options.get('track')
        if track is None:
            track = self.tracks[np.random.choice(len(self.tracks), p=self.track_weights)]
        self._select_track(track)

        # Sample new physics parameters (Zhang Section II-A)
        training = options.get('training', True)
        mode = SampleMode.TRAIN if training else SampleMode.GENERALIZATION
        delta = options.get('delta', 0.5)
        params = self.randomizer.sample(mode=mode, delta=delta)
        if 'physics_params' in options:
            params = dict(zip(PARAM_KEYS, NOMINAL_PARAMS))
            params.update(options['physics_params'])
        self.current_physics_params = params

        # Mid-episode grip drop: forced (E3) or sampled once per episode
        self._disturbance_step = None
        self._disturbance_grip = None
        if 'disturbance_step' in options:
            if options['disturbance_step'] >= 0:
                self._disturbance_step = int(options['disturbance_step'])
                self._disturbance_grip = options.get('disturbance_grip')
        elif 'physics_params' not in options:
            frac = self.randomizer.sample_disturbance_time()
            if frac is not None:
                self._disturbance_step = int(frac * self.max_episode_steps)

        self._obs_noise = bool(options.get('obs_noise', training))

        heading_offset = 0.0
        if training and np.random.rand() < self.drift_spawn_prob:
            heading_offset = float(np.random.uniform(-DRIFT_SPAWN_MAX_HEADING, DRIFT_SPAWN_MAX_HEADING))

        spawn_frac = options.get('spawn_frac')
        if spawn_frac is None and training and self.config.get('random_spawn', True):
            spawn_frac = float(np.random.rand())

        if self.base_env is None:
            raw_obs_vec = np.zeros(3, dtype=np.float32)
            raw_obs_dict = None
        elif spawn_frac is not None and getattr(self.base_env, 'supports_spawn_frac', False):
            raw_obs_vec, raw_obs_dict = self.base_env.reset(
                self.current_physics_params, heading_offset=heading_offset, spawn_frac=spawn_frac)
        else:
            raw_obs_vec, raw_obs_dict = self.base_env.reset(
                self.current_physics_params, heading_offset=heading_offset)

        # Reset episode state
        self.prev_action = np.zeros(2, dtype=np.float32)
        self.current_state = self._process_observation(raw_obs_vec, self.prev_action, raw_obs_dict)
        self.episode_step = 0
        self.total_episode_reward = 0.0
        self._prev_velocity = float(raw_obs_vec[0])
        self.reward_computer.reset_episode()

        info = {
            'physics_params': dict(self.current_physics_params),
            'physics_vector': params_to_vector(self.current_physics_params),
            'physics_params_description': self.randomizer.params_to_description(self.current_physics_params),
            'track': self.track,
            'disturbance_step': self._disturbance_step,
            'episode_num': 0,  # Updated by caller
        }
        if raw_obs_dict is not None:
            info['poses_x'] = float(raw_obs_dict['poses_x'][0])
            info['poses_y'] = float(raw_obs_dict['poses_y'][0])
            info['pose_theta'] = float(raw_obs_dict['poses_theta'][0])

        return self.current_state, info

    def _process_observation(self, raw_obs_vec: np.ndarray, last_action: np.ndarray,
                              raw_obs_dict: Dict = None) -> np.ndarray:
        """
        Build state vector xt = [v, steering, v_des, steering_des, yaw_rate, (lidar...)]
        from real_env's [v, steering_proxy, yaw_rate] and last commanded action.

        If observation.include_lidar is set, appends a downsampled, normalized
        LiDAR scan. f110_gym returns 1080 beams in raw_obs_dict['scans']; we
        subsample to observation.lidar_beams evenly-spaced indices, clip to
        observation.lidar_max_range meters (default 10.0), and normalize to
        [0, 1]. During training, Gaussian noise (lidar_noise_std, in
        normalized units) and beam dropout (lidar_dropout_prob, dropped beams
        read max range) are added.
        """
        v, steering, yaw_rate = float(raw_obs_vec[0]), float(raw_obs_vec[1]), float(raw_obs_vec[2])
        steering_des = float(last_action[0])
        v_des = self.throttle_to_velocity(last_action[1])
        base_obs = np.array([v, steering, v_des, steering_des, yaw_rate], dtype=np.float32)

        obs_config = self.config.get('observation', {})
        if not obs_config.get('include_lidar', False):
            return base_obs

        num_beams = obs_config.get('lidar_beams', 36)
        max_range = obs_config.get('lidar_max_range', 10.0)

        if raw_obs_dict is not None and 'scans' in raw_obs_dict:
            full_scan = np.asarray(raw_obs_dict['scans'][0], dtype=np.float32)
            indices = np.linspace(0, len(full_scan) - 1, num_beams).astype(int)
            lidar = full_scan[indices]
            lidar = np.clip(lidar, 0.0, max_range) / max_range
        else:
            lidar = np.zeros(num_beams, dtype=np.float32)

        if self._obs_noise:
            noise_std = obs_config.get('lidar_noise_std', 0.0)
            if noise_std > 0:
                lidar = lidar + np.random.normal(0.0, noise_std, size=lidar.shape)
            dropout = obs_config.get('lidar_dropout_prob', 0.0)
            if dropout > 0:
                lidar = np.where(np.random.rand(num_beams) < dropout, 1.0, lidar)
            lidar = np.clip(lidar, 0.0, 1.0)

        return np.concatenate([base_obs, lidar]).astype(np.float32)

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one step of environment.

        Returns (obs, reward, terminated, truncated, info). info carries the
        quantities needed for the friction-circle metric ρ: velocity,
        yaw_rate, accel_long, and the current physics params.
        """
        self.episode_step += 1

        # One-shot mid-episode grip drop, pushed into the simulator
        disturbance_fired = False
        if self._disturbance_step is not None and self.episode_step == self._disturbance_step:
            if self._disturbance_grip is not None:
                self.current_physics_params = dict(self.current_physics_params,
                                                   grip_factor=float(self._disturbance_grip))
            else:
                self.current_physics_params = self.randomizer.apply_disturbance(self.current_physics_params)
            if self.base_env is not None:
                self.base_env.set_grip(self.current_physics_params['grip_factor'])
            disturbance_fired = True

        # Clip action to bounds
        action = np.clip(action, self.action_space.low, self.action_space.high)

        # Map action -> f110_gym control input [steer_angle, velocity_cmd]
        steer_cmd = float(action[0])
        throttle_cmd = float(action[1])
        velocity_cmd = self.throttle_to_velocity(throttle_cmd)
        sim_action = np.array([steer_cmd, velocity_cmd], dtype=np.float32)

        # Step base environment
        if self.base_env is None:
            raw_obs_vec = np.zeros(3, dtype=np.float32)
            raw_obs_dict = None
            terminated = False
        else:
            raw_obs_vec, raw_obs_dict, done, _ = self.base_env.step(sim_action)
            # Terminate immediately on collision -- prevents wall-phasing exploit
            collision_flag = bool(raw_obs_dict['collisions'][0]) if raw_obs_dict is not None else False
            terminated = bool(done) or collision_flag
        truncated = False

        # Process observation -> xt
        obs = self._process_observation(raw_obs_vec, action, raw_obs_dict)

        current_velocity = float(raw_obs_vec[0])
        desired_velocity = velocity_cmd
        current_yaw_rate = float(raw_obs_vec[2])
        # Bicycle-model derivation: yaw_rate_des = v_des * tan(steer_des) / wheelbase
        # wheelbase = lf + lr = 0.15875 + 0.17145 = 0.3302 m (f110_gym default)
        wheelbase = 0.3302
        desired_yaw_rate = velocity_cmd * np.tan(steer_cmd) / wheelbase

        _poses_x = float(raw_obs_dict['poses_x'][0]) if raw_obs_dict is not None else None
        _poses_y = float(raw_obs_dict['poses_y'][0]) if raw_obs_dict is not None else None
        _collision = bool(raw_obs_dict['collisions'][0]) if raw_obs_dict is not None else False
        _lidar_obs = obs[5:] if len(obs) > 5 else None

        step_reward, reward_breakdown = self.reward_computer.compute_step_reward(
            action=action,
            prev_action=self.prev_action,
            current_velocity=current_velocity,
            desired_velocity=desired_velocity,
            current_yaw_rate=current_yaw_rate,
            desired_yaw_rate=desired_yaw_rate,
            poses_x=_poses_x,
            poses_y=_poses_y,
            lidar_obs=_lidar_obs,
            collision=_collision,
        )

        # Check termination conditions
        terminated_rma, termination_reason = self.reward_computer.compute_episode_termination(
            state={'velocity': current_velocity},
            track_error=None,
            lateral_accel=None,
        )
        terminated = terminated or terminated_rma

        # Check time limit
        truncated = truncated or (self.episode_step >= self.max_episode_steps)

        dt = self.base_env.timestep if self.base_env is not None else 0.01
        accel_long = (current_velocity - self._prev_velocity) / dt
        self._prev_velocity = current_velocity

        # Update state
        self.prev_action = action
        self.current_state = obs
        self.total_episode_reward += step_reward

        info = {
            'reward_breakdown': reward_breakdown,
            'episode_step': self.episode_step,
            'total_episode_reward': self.total_episode_reward,
            'physics_params': dict(self.current_physics_params),
            'physics_vector': params_to_vector(self.current_physics_params),
            'track': self.track,
            'collision': _collision,
            'velocity': current_velocity,
            'yaw_rate': current_yaw_rate,
            'accel_long': accel_long,
            'velocity_cmd': velocity_cmd,
            'disturbance_fired': disturbance_fired,
        }
        if raw_obs_dict is not None:
            # Privileged pose: for the Pure Pursuit expert and evaluation
            # only. It is never part of the policy/φ observation.
            info['poses_x'] = _poses_x
            info['poses_y'] = _poses_y
            info['pose_theta'] = float(raw_obs_dict['poses_theta'][0])
            info['lap_counts'] = int(raw_obs_dict['lap_counts'][0])
        if termination_reason is not None:
            info['termination_reason'] = termination_reason

        return obs, step_reward, terminated, truncated, info

    def render(self):
        """Render environment (delegate to base_env if available)."""
        if self.base_env is not None and self.render_mode == 'human':
            return self.base_env.env.render()
        return None

    def close(self):
        """Clean up environment."""
        for w in self._wrappers.values():
            if w is not None:
                w.close()

    def get_physics_params_description(self) -> str:
        """Get human-readable description of current physics parameters."""
        if self.current_physics_params is None:
            return "No physics parameters sampled yet"
        return self.randomizer.params_to_description(self.current_physics_params)
