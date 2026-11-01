#!/usr/bin/env python3
"""
E4: Causal intervention: is the car's caution caused by its belief about grip?

Same checkpoint, swapped intrinsics at test time (project record §9.6;
Paper 2 methodology Part C/D):

  at LOW true grip (default 0.4):
    blindfold     z = μ(grip = 1.0)  : told grip is fine when it is not
    restore       starts blindfolded, then φ takes over once it has k steps
                  of real history (self-correction)
    phi, oracle   references
  at HIGH true grip (default 1.0):
    hallucinate   z = μ(grip = 0.4)  : told grip is bad when it is fine;
                  any caution can only come from ẑ (the cleanest test)
    phi_high      reference: φ at the same high grip

Predictions (H-causal): blindfold ≈ Blind crash rate; hallucinate is slower
than phi_high; restore recovers toward the safe side.
  hallucination slowdown = speed(phi_high) − speed(hallucinate)
  gap closure (as on the July slide)
      = (crash_blindfold − crash_restore) / (crash_blindfold − crash_hallucinate)

Also reports how out-of-distribution each injected belief is relative to
φ's own outputs (max per-dimension |z − mean| / sd). July 2026: injected
beliefs were > 4 SD from φ's typical output: a caveat on interpreting
"restore", reported rather than hidden.

July 2026 result: hallucinate 0.30 crash / 1.99 m/s, blindfold 0.50 / 2.22,
restore 0.45 / 2.15 → 25% gap closure.

    python experiments/e4_causal.py -n 100
"""
import numpy as np
import torch
from _common import base_parser, eval_tracks, load_config, out_dir, track_for

from f1tenth_research.eval.harness import (
    Belief, Oracle, Phi, load_policy_pair, make_env, markdown_table, run_episode, summarize, write_outputs,
)


def main():
    ap = base_parser(__doc__)
    ap.add_argument('--true-grip', type=float, default=0.4, help='true grip for blindfold/restore')
    ap.add_argument('--blindfold-grip', type=float, default=1.0, help='belief injected when blindfolded')
    ap.add_argument('--high-grip', type=float, default=1.0, help='true grip for the hallucination arm')
    ap.add_argument('--hallucinate-grip', type=float, default=0.4, help='belief injected when hallucinating')
    args = ap.parse_args()

    cfg = load_config(args.config, args.tire_model)
    ac, phi, _ = load_policy_pair(args.phase1, args.phase2, args.device)
    env = make_env(cfg, args.max_steps)
    tracks = eval_tracks(args, cfg)

    blindfold = Belief(ac, args.blindfold_grip, args.device, name='blindfold')
    hallucinate = Belief(ac, args.hallucinate_grip, args.device, name='hallucinate')
    restore = Phi(ac, phi, args.device, warmup=Belief(ac, args.blindfold_grip, args.device))
    restore.name = 'restore'
    phi_ctrl = Phi(ac, phi, args.device)
    phi_high = Phi(ac, phi, args.device)
    phi_high.name = 'phi_high'
    arms = [(blindfold, args.true_grip), (restore, args.true_grip), (phi_ctrl, args.true_grip),
            (Oracle(ac, args.device), args.true_grip), (hallucinate, args.high_grip), (phi_high, args.high_grip)]

    results, phi_z = [], []
    for i in range(args.episodes):
        track = track_for(i, tracks)
        for ctrl, grip in arms:
            keep = ctrl is phi_ctrl
            r = run_episode(env, ac, ctrl, grip, seed=args.seed + i, track=track,
                            keep_trace=keep, device=args.device)
            if keep:
                phi_z.extend(r.trace['z'][phi.history_window:])
                r.trace = {}
            results.append(r)

    summary = summarize(results, keys=('controller',))
    by = {r['controller']: r for r in summary}
    denom = by['blindfold']['crash_rate'] - by['hallucinate']['crash_rate']
    gap = (by['blindfold']['crash_rate'] - by['restore']['crash_rate']) / denom if abs(denom) > 1e-9 else float('nan')

    ood = {}
    if phi_z:
        Z = np.asarray(phi_z)
        mu, sd = Z.mean(0), Z.std(0) + 1e-8
        with torch.no_grad():
            for ctrl in (blindfold, hallucinate):
                z = ctrl.intrinsics({}, []).cpu().numpy()
                ood[ctrl.name] = float(np.max(np.abs(z - mu) / sd))

    slowdown = by['phi_high']['mean_speed'] - by['hallucinate']['mean_speed']
    extra = {'args': vars(args), 'gap_closure': gap, 'hallucination_slowdown_mps': slowdown, 'ood_max_sd': ood}
    out = out_dir(args, 'e4')
    write_outputs(out, results, summary, extra)
    print(markdown_table(summary, ['controller', 'n', 'crash_rate', 'mean_speed', 'mean_rho']))
    print(f'hallucination slowdown: {slowdown:+.3f} m/s   gap closure (restore): {gap:.0%}')
    print(f'OOD (max SD of injected beliefs from φ outputs): {ood}')
    print(f'-> {out}')


if __name__ == '__main__':
    main()
