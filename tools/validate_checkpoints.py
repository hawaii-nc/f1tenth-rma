#!/usr/bin/env python3
"""
Closed-loop validation of Phase 1 checkpoints (deterministic policy, oracle
intrinsics): every track from the start line at several grip levels, no
LiDAR noise. Appends one JSON line per checkpoint to <run>/validation.jsonl
and skips checkpoints already there. Used to pick the base policy.

    python tools/validate_checkpoints.py runs/phase1_retrain            # all checkpoints so far
    python tools/validate_checkpoints.py runs/phase1_retrain --watch    # keep validating new ones
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import torch
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src' / 'f1tenth_research'))

from f1tenth_research.envs import F1TenthRMAEnv  # noqa: E402
from f1tenth_research.models import load_actor_critic  # noqa: E402


def validate(ck: Path, cfg, grips, max_steps):
    ac, _ = load_actor_critic(str(ck), torch.device('cpu'))
    env = F1TenthRMAEnv(config=cfg)
    out = {}
    for g in grips:
        crashes, speeds, steps = [], [], []
        for tr in cfg['environment']['tracks']:
            obs, info = env.reset(seed=0, options={'training': False, 'track': tr, 'physics_params': {'grip_factor': g},
                                                   'obs_noise': False, 'disturbance_step': -1})
            z = ac.get_intrinsics(torch.as_tensor(info['physics_vector']))
            vs = []
            for n in range(1, max_steps + 1):
                with torch.no_grad():
                    a = ac.policy(torch.as_tensor(obs), z)[0].numpy()
                obs, _, term, _, info = env.step(a)
                vs.append(info['velocity'])
                if term:
                    break
            crashes.append(bool(info['collision']))
            speeds.append(float(np.mean(vs)))
            steps.append(n)
        out[str(g)] = {'crash_rate': float(np.mean(crashes)), 'mean_speed': float(np.mean(speeds)),
                       'mean_steps': float(np.mean(steps))}
    env.close()
    return out


def epoch_of(p: Path):
    m = re.search(r'epoch_(\d+)', p.name)
    return int(m.group(1)) if m else -1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run', type=Path)
    ap.add_argument('--config', default=str(REPO / 'configs' / 'retrain_phase2.yaml'))
    ap.add_argument('--grips', type=float, nargs='*', default=[1.0, 0.6, 0.4])
    ap.add_argument('--every', type=int, default=50, help='validate checkpoint_epoch_N for N % every == 0')
    ap.add_argument('--max-steps', type=int, default=2500)
    ap.add_argument('--watch', action='store_true')
    a = ap.parse_args()
    torch.set_num_threads(1)
    cfg = yaml.safe_load(open(a.config))
    log = a.run / 'validation.jsonl'
    while True:
        done = {json.loads(l)['checkpoint'] for l in log.read_text().splitlines()} if log.exists() else set()
        cands = [a.run / 'dagger.pt'] + sorted(a.run.glob('checkpoint_epoch_*.pt'), key=epoch_of) + [a.run / 'final.pt']
        cands = [c for c in cands if c.exists() and c.name not in done and
                 (not c.name.startswith('checkpoint_epoch_') or epoch_of(c) % a.every == 0)]
        for c in cands:
            res = validate(c, cfg, a.grips, a.max_steps)
            row = {'checkpoint': c.name, 'epoch': epoch_of(c), 'results': res,
                   'mean_crash_rate': float(np.mean([r['crash_rate'] for r in res.values()]))}
            with open(log, 'a') as f:
                f.write(json.dumps(row) + '\n')
            print(json.dumps(row), flush=True)
        if not a.watch or (a.run / 'final.pt').name in done | {c.name for c in cands}:
            break
        time.sleep(60)


if __name__ == '__main__':
    main()
