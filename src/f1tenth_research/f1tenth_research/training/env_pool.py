"""
Environment pool for Phase 1 rollouts.

Each slot owns one F1TenthRMAEnv and its own Pure Pursuit experts, and
auto-resets when an episode ends. After every reset/step a slot returns the
expert action *for the state it just returned*, so imitation labels always
belong to the right environment and the right state.

    pool = make_pool(config, n)        # n == 1: in-process; n > 1: one process per env
    obs, infos, experts = pool.reset()
    obs, rewards, dones, infos, experts, finished = pool.step(actions)

`finished` lists the stats of episodes that ended during this step.

Replaces gymnasium's AsyncVectorEnv here, whose vector-info format broke the
old rollout: the physics vector and the expert action of env 0 were used for
every env, and GAE ran across interleaved envs as if they were one trajectory.
"""
import multiprocessing as mp
from typing import Dict, Optional

import numpy as np

from ..envs import F1TenthRMAEnv
from ..experts import PurePursuitExpert
from ..paths import centerline_path, raceline_path


def create_experts(config: Dict) -> Optional[Dict[str, PurePursuitExpert]]:
    """One Pure Pursuit expert per training track (None if IL is off)."""
    tcfg = config.get('phase1_training', {})
    if not tcfg.get('il', {}).get('use_expert_actions', False):
        return None
    ecfg = config.get('expert', {})
    if ecfg.get('type', 'pure_pursuit') != 'pure_pursuit':
        return None
    env_cfg = config.get('environment', {})
    tracks = env_cfg.get('tracks') or [env_cfg.get('track', 'example_map')]
    experts = {}
    for track in tracks:
        if track == 'example_map':
            wpt = np.loadtxt('/f1tenth_gym/examples/example_waypoints.csv', delimiter=';', skiprows=3)
            waypoints = wpt[:, 1:3]
        else:
            # Raceline if one exists (full-scale tracks), else the centerline.
            # prepare_tracks.py writes no raceline for *_tight tracks: scaled
            # racelines pass within the car's half-width of the walls.
            rl = raceline_path(track)
            if rl.exists():
                waypoints = np.loadtxt(rl, delimiter=',', comments='#')[:, 1:3]
            else:
                waypoints = np.loadtxt(centerline_path(track), delimiter=',')[:, 0:2]
        experts[track] = PurePursuitExpert(config=ecfg.get('pure_pursuit', {}), waypoints=waypoints)
    return experts


def expert_action(experts, info: Dict) -> Optional[np.ndarray]:
    """Expert action from the privileged pose in info (never in the observation)."""
    if experts is None or 'poses_x' not in info:
        return None
    ex = experts.get(info.get('track'))
    if ex is None:
        return None
    state = {
        'position': (info['poses_x'], info['poses_y']),
        'yaw': info['pose_theta'],
        'velocity': info.get('velocity', 0.0),
        'yaw_rate': info.get('yaw_rate', 0.0),
    }
    return np.asarray(ex.compute_action(state, info.get('physics_params', {})), dtype=np.float32)


class _Slot:
    """One env + its experts + running episode stats."""

    def __init__(self, config: Dict, seed: int):
        np.random.seed(seed)
        env_cfg = config.get('environment', {})
        self.env = F1TenthRMAEnv(config=config, max_episode_steps=env_cfg.get('max_episode_steps', 1000))
        self.experts = create_experts(config)

    def _reset(self):
        obs, info = self.env.reset()
        self.ep_len, self.ep_ret = 0, 0.0
        return obs, info

    def reset(self):
        obs, info = self._reset()
        return obs, _slim(info), expert_action(self.experts, info)

    def step(self, action):
        obs, r, term, trunc, info = self.env.step(np.asarray(action, dtype=np.float32))
        self.ep_len += 1
        self.ep_ret += float(r)
        done = bool(term or trunc)
        finished = None
        if done:
            finished = {'track': info.get('track'), 'length': self.ep_len, 'return': self.ep_ret,
                        'crash': bool(info.get('collision', False)), 'truncated': bool(trunc and not term),
                        'grip': float(info['physics_params'].get('grip_factor', 1.0))}
            obs, info = self._reset()
        return obs, float(r), done, _slim(info), expert_action(self.experts, info), finished


def _slim(info: Dict) -> Dict:
    """Only what the trainer needs (keeps pipe traffic small)."""
    return {'physics_vector': np.asarray(info['physics_vector'], dtype=np.float32),
            'track': info.get('track')}


def _worker(conn, config, seed):
    slot = _Slot(config, seed)
    try:
        while True:
            cmd, arg = conn.recv()
            if cmd == 'reset':
                conn.send(slot.reset())
            elif cmd == 'step':
                conn.send(slot.step(arg))
            elif cmd == 'close':
                slot.env.close()
                conn.close()
                return
    except (EOFError, KeyboardInterrupt):
        return


class EnvPool:
    def __init__(self, config: Dict, n: int, seed: int = 0, inproc: bool = False):
        self.n = n
        if n == 1 or inproc:  # inproc: tests (fake simulator isn't visible to spawned workers)
            self._slots = [_Slot(config, seed + 1000 * i) for i in range(n)]
            self._conns = None
            return
        ctx = mp.get_context('spawn')  # never fork f110_gym / numba state
        self._conns, self._procs = [], []
        for i in range(n):
            parent, child = ctx.Pipe()
            p = ctx.Process(target=_worker, args=(child, config, seed + 1000 * i), daemon=True)
            p.start()
            child.close()
            self._conns.append(parent)
            self._procs.append(p)

    def _call(self, cmd, args=None):
        if self._conns is None:
            return [s.reset() if cmd == 'reset' else s.step(args[i]) for i, s in enumerate(self._slots)]
        for i, c in enumerate(self._conns):
            c.send((cmd, None if args is None else args[i]))
        return [c.recv() for c in self._conns]

    def reset(self):
        out = self._call('reset')
        obs = np.stack([o[0] for o in out]).astype(np.float32)
        return obs, [o[1] for o in out], [o[2] for o in out]

    def step(self, actions: np.ndarray):
        out = self._call('step', list(actions))
        obs = np.stack([o[0] for o in out]).astype(np.float32)
        rewards = np.array([o[1] for o in out], dtype=np.float32)
        dones = np.array([o[2] for o in out], dtype=np.float32)
        finished = [o[5] for o in out if o[5] is not None]
        return obs, rewards, dones, [o[3] for o in out], [o[4] for o in out], finished

    def close(self):
        if self._conns is None:
            for s in self._slots:
                s.env.close()
            return
        for c in self._conns:
            try:
                c.send(('close', None))
            except (BrokenPipeError, OSError):
                pass
        for p in self._procs:
            p.join(timeout=5)


def make_pool(config: Dict, n: int, seed: int = 0) -> EnvPool:
    return EnvPool(config, n, seed, inproc=bool(config.get('phase1_training', {}).get('inproc_envs', False)))
