"""
Shared evaluation harness for the E-series experiments (E0–E5).

One frozen base policy π, three ways to supply its intrinsics z:

    Oracle  z = μ(e_true)            true physics every step   (upper bound, sim only)
    φ-RMA   z = φ(last k steps)      own motion history        (system under test)
    Blind   z = μ(e_nominal)         assumes nominal grip      (no-adaptation baseline)

plus fixed-belief controllers for the causal tests (E4):

    Belief(g)        z = μ(e with grip=g), regardless of the true grip
    Restore(g)       starts from Belief(g), switches to φ once its history is full

Episodes are paired across controllers: episode i of every controller uses
the same seed, track and physics draw. Actions are the policy mean
(deterministic). LiDAR noise and spawn-heading drift are off.
"""

import csv
import json
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import torch

from ..envs import F1TenthRMAEnv
from ..envs.randomization import NOMINAL_PARAMS, PARAM_KEYS
from ..metrics.friction_circle import utilization_from_grip
from ..models import load_actor_critic, load_adaptation

MOVING_SPEED = 0.5  # m/s; ρ is averaged over steps faster than this


# --------------------------------------------------------------------- controllers
class Controller:
    name = 'base'

    def reset(self):
        pass

    def intrinsics(self, info: Dict, history: Sequence[np.ndarray]) -> torch.Tensor:
        raise NotImplementedError


class _Base(Controller):
    def __init__(self, actor_critic, device='cpu'):
        self.ac = actor_critic
        self.device = device

    def encode(self, physics: Sequence[float]) -> torch.Tensor:
        e = torch.as_tensor(np.asarray(physics, dtype=np.float32), device=self.device)
        return self.ac.get_intrinsics(e)


class Oracle(_Base):
    name = 'oracle'

    def intrinsics(self, info, history):
        return self.encode(info['physics_vector'])


class Blind(_Base):
    name = 'blind'

    def intrinsics(self, info, history):
        return self.encode(NOMINAL_PARAMS)


class Belief(_Base):
    """Fixed belief about grip; every other physics parameter nominal."""

    def __init__(self, actor_critic, grip: float, device='cpu', name=None):
        super().__init__(actor_critic, device)
        self.grip = grip
        self.name = name or f'belief_{grip:g}'
        self._z = None

    def intrinsics(self, info, history):
        if self._z is None:
            e = list(NOMINAL_PARAMS)
            e[0] = self.grip
            self._z = self.encode(e)
        return self._z


class Phi(_Base):
    name = 'phi'

    def __init__(self, actor_critic, adaptation, device='cpu', warmup: Optional[Controller] = None):
        super().__init__(actor_critic, device)
        self.phi = adaptation
        self.k = adaptation.history_window
        self.warmup = warmup  # controller used until k steps of history exist (default: Blind)

    def intrinsics(self, info, history):
        if len(history) >= self.k:
            h = torch.as_tensor(np.asarray(list(history)[-self.k:], dtype=np.float32), device=self.device)
            return self.phi(h.unsqueeze(0)).squeeze(0)
        if self.warmup is not None:
            return self.warmup.intrinsics(info, history)
        return self.encode(NOMINAL_PARAMS)


def make_controllers(actor_critic, adaptation, names: Sequence[str], device='cpu') -> List[Controller]:
    out = []
    for n in names:
        if n == 'oracle':
            out.append(Oracle(actor_critic, device))
        elif n == 'blind':
            out.append(Blind(actor_critic, device))
        elif n == 'phi':
            out.append(Phi(actor_critic, adaptation, device))
        elif n.startswith('belief_'):
            out.append(Belief(actor_critic, float(n.split('_', 1)[1]), device))
        else:
            raise ValueError(f'unknown controller {n}')
    return out


# ------------------------------------------------------------------- episodes
@dataclass
class EpisodeResult:
    controller: str
    grip: float
    track: str
    seed: int
    steps: int
    crashed: bool
    completed: bool
    mean_speed: float
    mean_rho: float
    max_rho: float
    progress_m: float
    trace: Dict[str, list] = field(default_factory=dict, repr=False)

    def row(self) -> Dict:
        d = asdict(self)
        d.pop('trace')
        return d


def physics_for(grip: float, others: Optional[Dict] = None) -> Dict[str, float]:
    p = dict(zip(PARAM_KEYS, NOMINAL_PARAMS))
    if others:
        p.update(others)
    p['grip_factor'] = float(grip)
    return p


@torch.no_grad()
def run_episode(
    env: F1TenthRMAEnv,
    actor_critic,
    controller: Controller,
    grip: float,
    seed: int,
    track: Optional[str] = None,
    max_steps: Optional[int] = None,
    physics_others: Optional[Dict] = None,
    disturbance_step: int = -1,
    disturbance_grip: Optional[float] = None,
    keep_trace: bool = False,
    z_hook: Optional[Callable[[int, torch.Tensor], torch.Tensor]] = None,
    device='cpu',
) -> EpisodeResult:
    """
    Roll out one deterministic episode with forced physics.

    z_hook(step, z) may replace the intrinsics before the policy sees them
    (used by E4 to inject beliefs after warm-up).
    """
    opts = {
        'training': False,
        'obs_noise': False,
        'physics_params': physics_for(grip, physics_others),
        'disturbance_step': disturbance_step,
    }
    if disturbance_grip is not None:
        opts['disturbance_grip'] = disturbance_grip
    if track is not None:
        opts['track'] = track
    obs, info = env.reset(seed=seed, options=opts)
    controller.reset()

    k = getattr(controller, 'k', 1)
    history = deque(maxlen=max(k, 1))
    limit = max_steps or env.max_episode_steps
    speeds, rhos, trace = [], [], {k_: [] for k_ in ('v', 'yaw_rate', 'grip', 'rho', 'steer', 'throttle', 'z', 'x', 'y')}
    crashed = completed = False
    progress = 0.0
    steps = 0
    for steps in range(1, limit + 1):
        z = controller.intrinsics(info, history)
        if z_hook is not None:
            z = z_hook(steps, z)
        obs_t = torch.as_tensor(obs, dtype=torch.float32, device=device)
        mean, _ = actor_critic.policy(obs_t, z)
        action = mean.cpu().numpy()
        history.append(np.concatenate([obs, action]).astype(np.float32))

        obs, reward, terminated, truncated, info = env.step(action)
        g = info['physics_params']['grip_factor']
        rho = float(utilization_from_grip(info['velocity'], info['yaw_rate'], info['accel_long'], g))
        progress += info['reward_breakdown'].get('progress', 0.0) / max(
            env.reward_computer.config.get('weight_progress', 1.0), 1e-9)
        if info['velocity'] > MOVING_SPEED:
            rhos.append(rho)
        speeds.append(info['velocity'])
        if keep_trace:
            for key, val in (('v', info['velocity']), ('yaw_rate', info['yaw_rate']), ('grip', g),
                             ('rho', rho), ('steer', float(action[0])), ('throttle', float(action[1])),
                             ('z', z.cpu().numpy().tolist()),
                             ('x', info.get('poses_x')), ('y', info.get('poses_y'))):
                trace[key].append(val)
        if info.get('collision'):
            crashed = True
            break
        if info.get('lap_counts', 0) >= 1:
            completed = True
            break
        if terminated or truncated:
            completed = not terminated
            break

    return EpisodeResult(
        controller=controller.name, grip=float(grip), track=env.track, seed=seed, steps=steps,
        crashed=crashed, completed=completed,
        mean_speed=float(np.mean(speeds)) if speeds else 0.0,
        mean_rho=float(np.mean(rhos)) if rhos else float('nan'),
        max_rho=float(np.max(rhos)) if rhos else float('nan'),
        progress_m=float(progress),
        trace=trace if keep_trace else {},
    )


# ---------------------------------------------------------------------- setup
def load_policy_pair(phase1: str, phase2: Optional[str], device='cpu'):
    ac, cfg = load_actor_critic(phase1, device)
    phi = None
    if phase2:
        phi, _ = load_adaptation(phase2, device)
    return ac, phi, cfg


def make_env(cfg: Dict, max_steps: Optional[int] = None) -> F1TenthRMAEnv:
    return F1TenthRMAEnv(config=cfg, max_episode_steps=max_steps)


def summarize(results: List[EpisodeResult], keys=('controller', 'grip')) -> List[Dict]:
    groups: Dict[tuple, List[EpisodeResult]] = {}
    for r in results:
        groups.setdefault(tuple(getattr(r, k) for k in keys), []).append(r)
    rows = []
    for key, rs in sorted(groups.items(), key=lambda kv: (kv[0][0], -kv[0][1]) if len(kv[0]) == 2 else kv[0]):
        rhos = np.array([r.mean_rho for r in rs], dtype=float)
        rows.append({
            **dict(zip(keys, key)),
            'n': len(rs),
            'crash_rate': float(np.mean([r.crashed for r in rs])),
            'completion_rate': float(np.mean([r.completed for r in rs])),
            'mean_speed': float(np.mean([r.mean_speed for r in rs])),
            'mean_rho': float(np.nanmean(rhos)) if np.isfinite(rhos).any() else float('nan'),
            'rho_sem': float(np.nanstd(rhos) / np.sqrt(max(np.isfinite(rhos).sum(), 1))),
            'mean_progress_m': float(np.mean([r.progress_m for r in rs])),
        })
    return rows


def write_outputs(out_dir: Path, results: List[EpisodeResult], summary: List[Dict], extra: Optional[Dict] = None):
    out_dir.mkdir(parents=True, exist_ok=True)
    if results:
        with open(out_dir / 'episodes.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(results[0].row().keys()))
            w.writeheader()
            for r in results:
                w.writerow(r.row())
    if summary:
        with open(out_dir / 'summary.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
            w.writeheader()
            w.writerows(summary)
    with open(out_dir / 'summary.json', 'w') as f:
        json.dump({'summary': summary, **(extra or {})}, f, indent=2, default=float)


def markdown_table(rows: List[Dict], cols: Sequence[str], fmt: str = '{:.3f}') -> str:
    head = '| ' + ' | '.join(cols) + ' |\n|' + '---|' * len(cols) + '\n'
    body = ''
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c, '')
            cells.append(fmt.format(v) if isinstance(v, float) else str(v))
        body += '| ' + ' | '.join(cells) + ' |\n'
    return head + body
