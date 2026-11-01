"""
Real f110_gym wrapper for RMA F1Tenth env.
Maps f110_gym's (params-dict, [steer,vel]-action, dict-obs) API
to the Gymnasium-style interface expected by f1tenth_env.py.

Also implements actuator delay (Zhang Section II-E "motor effectiveness" analog):
commanded actions are buffered in a FIFO queue and applied N steps later,
where N = round(delay_seconds / timestep). delay_steering and delay_drive
come from PhysicsRandomizer.sample() (typical F1Tenth servo/ESC latencies
~10-50ms, per literature).

Every one of the 7 randomized parameters now reaches the physics:
  grip_factor          -> params['mu']   (live-updatable via set_grip)
  mass_scale           -> params['m']
  inertia_scale        -> params['I']
  motor_steering_scale -> scales the steering command
  motor_drive_scale    -> scales the velocity command
  delay_steering/drive -> FIFO queues
NOTE on fidelity: f110_gym's stock single-track model uses a *linear* tire
model. μ scales cornering stiffness; there is no friction-circle saturation,
so the car cannot physically "exceed grip". Pass tire_model='friction_circle'
(config: environment.tire_model) for a tire that saturates at μF_z.
See envs/tire_models.py and docs/SIM_FIDELITY.md.
"""
import numpy as np
from collections import deque
from f110_gym.envs.f110_env import F110Env

from ..paths import centerline_path
from . import tire_models

# f110_gym keeps ONE LiDAR/map simulator per process (RaceCar.scan_simulator is
# a class attribute). Building an F110Env for another track replaces the map
# for every car in the process, so with one cached env per track all tracks
# ray-cast (and iTTC-collide) against whichever map was loaded last (bug C22).
# Each wrapper snapshots the scan simulator after loading its own map and
# restores it whenever it becomes the active one.
_ACTIVE = {'wrapper': None}


def _scan_simulator():
    from f110_gym.envs.base_classes import RaceCar
    return RaceCar.scan_simulator

NOMINAL_VEHICLE_PARAMS = {
    'mu': 1.0489, 'C_Sf': 4.718, 'C_Sr': 5.4562,
    'lf': 0.15875, 'lr': 0.17145, 'h': 0.074, 'm': 3.74,
    'I': 0.04712, 's_min': -0.4189, 's_max': 0.4189,
    'sv_min': -3.2, 'sv_max': 3.2, 'v_switch': 7.319,
    'a_max': 9.51, 'v_min': -5.0, 'v_max': 20.0,
    'width': 0.31, 'length': 0.58,
}


def vehicle_params_from_physics(physics_params):
    params = dict(NOMINAL_VEHICLE_PARAMS)
    p = physics_params or {}
    if 'grip_factor' in p:
        params['mu'] = NOMINAL_VEHICLE_PARAMS['mu'] * float(p['grip_factor'])
    if 'mass_scale' in p:
        params['m'] = NOMINAL_VEHICLE_PARAMS['m'] * float(p['mass_scale'])
    if 'inertia_scale' in p:
        params['I'] = NOMINAL_VEHICLE_PARAMS['I'] * float(p['inertia_scale'])
    return params


def spawn_pose_from_centerline(centerline_xy, spawn_xy=(0.7, 0.0), spawn_frac=None):
    """
    Pose at the centerline point nearest spawn_xy, heading along the track.

    Heading comes from arctan2 of neighbouring centerline points: the psi
    column in the TUMFTM raceline CSVs is 90° off and must not be used.
    """
    xy = np.asarray(centerline_xy)[:, 0:2]
    if spawn_frac is not None:
        # Training: anywhere along the lap, so the policy sees every corner
        idx = int(spawn_frac * len(xy)) % len(xy)
    else:
        d = np.hypot(xy[:, 0] - spawn_xy[0], xy[:, 1] - spawn_xy[1])
        idx = int(np.argmin(d))
    ip = max(0, idx - 2)
    inn = min(len(xy) - 1, idx + 2)
    heading = float(np.arctan2(xy[inn, 1] - xy[ip, 1], xy[inn, 0] - xy[ip, 0]))
    # Spawn ON the centerline (bug C16). Returning spawn_xy itself put the car
    # up to 0.7 m off the centerline (half-width 0.38 m) on the racetrack-DB
    # tight tracks, i.e. inside or outside the walls.
    return float(xy[idx, 0]), float(xy[idx, 1]), heading


class RealF110Wrapper:
    supports_spawn_frac = True
    """
    Single-agent wrapper around F110Env.
    reset(physics_params) -> obs_vec
    step(action) -> obs_vec, raw_obs_dict, done, info
    """
    def __init__(self, map_name="/f1tenth_gym/examples/example_map", timestep=0.01,
                 track="example_map", ttc_thresh=0.05, tire_model="linear"):
        if tire_model not in tire_models.TIRE_MODELS:
            raise ValueError(f"Unknown tire_model {tire_model!r}; choose from {tire_models.TIRE_MODELS}")
        self.map_name = map_name
        self.tire_model = tire_model
        self.timestep = timestep
        self.track = track
        self.ttc_thresh = ttc_thresh
        self.env = None
        self.vehicle_params = dict(NOMINAL_VEHICLE_PARAMS)
        self.last_steer = 0.0
        self.last_vel = 0.0
        self.steer_scale = 1.0
        self.drive_scale = 1.0
        self.steer_queue = deque([0.0])
        self.drive_queue = deque([0.0])
        self._centerline = None
        cl_path = centerline_path(track)
        if cl_path.exists():
            self._centerline = np.loadtxt(cl_path, delimiter=',')

    def _build_env(self, physics_params):
        self.vehicle_params = vehicle_params_from_physics(physics_params)
        if self.env is None:
            self.env = F110Env(map=self.map_name, map_ext=".png",
                               params=self.vehicle_params, num_agents=1,
                               timestep=self.timestep)
            self._scan_state = dict(_scan_simulator().__dict__)
            _ACTIVE['wrapper'] = self
        else:
            # Reusing the env avoids re-loading the map PNG every episode.
            self.env.update_params(self.vehicle_params)
        # Increase iTTC threshold for more realistic collision detection.
        # Default 0.005s triggers at 4cm at 8m/s -- too lenient, allows wall grazing.
        # 0.05s triggers at 40cm -- within car half-width, stops wall phasing.
        for agent in self.env.sim.agents:
            agent.ttc_thresh = self.ttc_thresh

    def _activate_map(self):
        """Make f110_gym's process-wide scan simulator use this track's map."""
        if _ACTIVE['wrapper'] is not self:
            _scan_simulator().__dict__.update(self._scan_state)
            _ACTIVE['wrapper'] = self

    def set_grip(self, grip_factor: float):
        """Change tire friction mid-episode (wet patch / E3 step change)."""
        self.vehicle_params['mu'] = NOMINAL_VEHICLE_PARAMS['mu'] * float(grip_factor)
        self.env.update_params(self.vehicle_params)

    def _setup_delay_queues(self, physics_params):
        """Initialize FIFO delay buffers. Queue length N means an action
        issued now is applied N steps from now (N=0 -> applied immediately)."""
        p = physics_params or {}
        delay_steer_s = float(p.get('delay_steering', 0.0))
        delay_drive_s = float(p.get('delay_drive', 0.0))
        n_steer = max(0, round(delay_steer_s / self.timestep))
        n_drive = max(0, round(delay_drive_s / self.timestep))
        # queue holds N pending zero-actions; popleft() on step gives delayed value
        self.steer_queue = deque([0.0] * n_steer)
        self.drive_queue = deque([0.0] * n_drive)
        self.n_steer = n_steer
        self.n_drive = n_drive

    def reset(self, physics_params=None, heading_offset=0.0, spawn_frac=None):
        # Process-wide switch; re-applied every episode so wrappers with
        # different tire models can share one process (e.g. experiments).
        tire_models.install(self.tire_model)
        self._build_env(physics_params)
        self._activate_map()
        self._setup_delay_queues(physics_params)
        p = physics_params or {}
        self.steer_scale = float(p.get('motor_steering_scale', 1.0))
        self.drive_scale = float(p.get('motor_drive_scale', 1.0))

        if self._centerline is not None:
            x, y, heading = spawn_pose_from_centerline(self._centerline, spawn_frac=spawn_frac)
        else:
            x, y, heading = 0.7, 0.0, 1.37079632679  # example_map default (pi/2 - 0.20)
        poses = np.array([[x, y, heading + heading_offset]])
        obs, _, _, _ = self.env.reset(poses)
        self.last_steer = 0.0
        self.last_vel = float(obs['linear_vels_x'][0])
        return self._to_vec(obs), obs

    def close(self):
        """Close the f110_gym environment."""
        if self.env is not None:
            try:
                self.env.close()
            except Exception:
                pass
            self.env = None

    def _apply_delay(self, queue, n, new_value):
        """Push new_value, return the delayed value to actually apply."""
        if n == 0:
            return new_value
        queue.append(new_value)
        return queue.popleft()

    def step(self, action):
        # action: [steer_angle_cmd, velocity_cmd] (already mapped to m/s by the env)
        steer_cmd = float(action[0]) * self.steer_scale
        velocity_cmd = float(action[1]) * self.drive_scale

        # Apply actuator delay (Zhang Section II-E analog: motor effectiveness/latency)
        delayed_steer = self._apply_delay(self.steer_queue, self.n_steer, steer_cmd)
        delayed_velocity = self._apply_delay(self.drive_queue, self.n_drive, velocity_cmd)

        ctrl = np.array([[delayed_steer, delayed_velocity]])
        self._activate_map()
        obs, _, done, info = self.env.step(ctrl)
        self.last_steer = delayed_steer
        self.last_vel = float(obs['linear_vels_x'][0])
        done = bool(done) or bool(obs['collisions'][0])
        return self._to_vec(obs), obs, done, info

    def _to_vec(self, obs):
        # xt = [current_velocity, current_steering(proxy), yaw_rate]
        return np.array([
            obs['linear_vels_x'][0],
            self.last_steer,
            obs['ang_vels_z'][0],
        ], dtype=np.float32)
