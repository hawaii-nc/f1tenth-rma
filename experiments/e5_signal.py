#!/usr/bin/env python3
"""
E5: Signal diagnostic: where is the grip signal lost between physics and φ?

Rolls out the φ-RMA controller at grips drawn uniformly from [0.2, 1.0]
(other physics nominal unless --randomize-others), and at every
`--stride`-th step records three representations of the same moment:

  encoder   z = μ(e_true)                          (what Phase 1 was trained on)
  history   mean and sd of each channel over φ's k-step window
                                                   (is grip visible in behaviour at all?)
  φ output  ẑ = φ(window)                          (the live estimate)

and fits a linear probe → true grip for each, with 5-fold cross-validation
grouped by episode (samples from one episode never straddle a split).

July 2026 (BEFORE the physics-injection fix: must be re-run):
  encoder R² ≈ 0.98, history R² ≈ 0.36, φ R² ≈ 0.08.
Pre-registered H1: φ R² ≥ 0.7.

    python experiments/e5_signal.py -n 200
"""
from collections import deque

import numpy as np
import torch
from _common import base_parser, eval_tracks, load_config, out_dir, track_for

from f1tenth_research.eval.harness import make_env, load_policy_pair, physics_for, write_outputs
from f1tenth_research.envs.randomization import PhysicsRandomizer, PARAM_KEYS
from f1tenth_research.metrics import cv_r2


def main():
    ap = base_parser(__doc__, n_default=200)
    ap.add_argument('--grip-range', type=float, nargs=2, default=[0.2, 1.0])
    ap.add_argument('--stride', type=int, default=10)
    ap.add_argument('--randomize-others', action='store_true',
                    help='sample mass/inertia/motor/delay from the training range too')
    args = ap.parse_args()

    cfg = load_config(args.config)
    ac, phi, _ = load_policy_pair(args.phase1, args.phase2, args.device)
    env = make_env(cfg, args.max_steps)
    tracks = eval_tracks(args, cfg)
    k = phi.history_window
    rng = np.random.default_rng(args.seed)
    randomizer = PhysicsRandomizer(cfg['environment'].get('randomization', {}))

    enc, hist, est, y, groups = [], [], [], [], []
    with torch.no_grad():
        for ep in range(args.episodes):
            grip = float(rng.uniform(*args.grip_range))
            others = None
            if args.randomize_others:
                np.random.seed(args.seed + ep)
                s = randomizer.sample_training()
                others = {key: s[key] for key in PARAM_KEYS if key != 'grip_factor'}
            obs, info = env.reset(seed=args.seed + ep, options={
                'training': False, 'obs_noise': False, 'disturbance_step': -1,
                'physics_params': physics_for(grip, others), 'track': track_for(ep, tracks)})
            e = torch.as_tensor(info['physics_vector'])
            z_true = ac.get_intrinsics(e)
            window = deque(maxlen=k)
            for t in range(args.max_steps):
                if len(window) == k:
                    W = np.asarray(window, dtype=np.float32)
                    z_hat = phi(torch.as_tensor(W).unsqueeze(0)).squeeze(0)
                    if t % args.stride == 0:
                        enc.append(z_true.numpy())
                        hist.append(np.concatenate([W.mean(0), W.std(0)]))
                        est.append(z_hat.numpy())
                        y.append(grip)
                        groups.append(ep)
                    z = z_hat
                else:
                    z = ac.get_intrinsics(torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0]))
                mean, _ = ac.policy(torch.as_tensor(obs, dtype=torch.float32), z)
                action = mean.numpy()
                window.append(np.concatenate([obs, action]))
                obs, _, terminated, truncated, info = env.step(action)
                if terminated or truncated or info.get('collision'):
                    break

    y, groups = np.asarray(y), np.asarray(groups)
    r2 = {
        'encoder': cv_r2(np.asarray(enc), y, groups=groups),
        'history': cv_r2(np.asarray(hist), y, groups=groups),
        'phi': cv_r2(np.asarray(est), y, groups=groups),
    }
    extra = {'args': vars(args), 'r2': r2, 'samples': int(len(y)), 'H1_pass': r2['phi'] >= 0.7}
    out = out_dir(args, 'e5')
    write_outputs(out, [], [], extra)
    print(f"R² → grip   encoder {r2['encoder']:.3f}   history {r2['history']:.3f}   φ {r2['phi']:.3f}"
          f"   (n={len(y)}, H1 {'PASS' if extra['H1_pass'] else 'FAIL'})")
    print(f'-> {out}')


if __name__ == '__main__':
    main()
