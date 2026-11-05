#!/usr/bin/env python3
"""
E1 / E2: Performance recovery and risk calibration (the poster's headline result).

Three controllers share one frozen base policy (Oracle / φ-RMA / Blind; see
eval/harness.py). Forced grip sweep, paired seeds, tracks cycled round-robin
over the 14 evaluation circuits.

Metrics per (controller, grip):
  E1  crash rate, completion rate, mean speed
  E2  mean friction-circle utilization ρ (per-episode mean, then averaged)

Derived:
  gap closed at μ   1 − |ρ_φ − ρ_oracle| / |ρ_blind − ρ_oracle|
  cross-grip swing  variance of a controller's mean ρ across grip levels
                    (φ vs Blind ratio; lower = steadier margin)
  95% CIs           paired bootstrap over episodes for both (--n-boot)

July 2026 result (N=100, μ ∈ {1.0, 0.8, 0.6, 0.4}):
  ρ at μ=0.4: Oracle 0.185, φ 0.215, Blind 0.239 → 44% of the gap closed;
  cross-grip ρ variance 1.25–1.27× lower for φ than Blind (N = 20, 40, 100).
  Pre-registered H3 (order of magnitude) NOT met: a partial effect.

    python experiments/e1_e2_calibration.py -n 100
"""
from _common import base_parser, eval_tracks, load_config, out_dir, track_for

from f1tenth_research.eval.harness import (
    load_policy_pair, make_controllers, make_env, markdown_table, run_episode, summarize, write_outputs,
)
import numpy as np

from f1tenth_research.metrics import bootstrap_calibration, calibration_gaps, cross_grip_swing


def main():
    ap = base_parser(__doc__)
    ap.add_argument('--grips', type=float, nargs='*', default=[1.0, 0.8, 0.6, 0.4])
    ap.add_argument('--controllers', nargs='*', default=['oracle', 'phi', 'blind'])
    ap.add_argument('--n-boot', type=int, default=2000, help='bootstrap resamples for the CIs (0 = skip)')
    args = ap.parse_args()

    cfg = load_config(args.config, args.tire_model)
    ac, phi, _ = load_policy_pair(args.phase1, args.phase2, args.device)
    env = make_env(cfg, args.max_steps)
    tracks = eval_tracks(args, cfg)
    controllers = make_controllers(ac, phi, args.controllers, args.device)

    results = []
    for grip in args.grips:
        for i in range(args.episodes):
            track = track_for(i, tracks)
            for ctrl in controllers:
                results.append(run_episode(env, ac, ctrl, grip, seed=args.seed + i,
                                           track=track, device=args.device))
        print(f'grip={grip}: done')

    summary = summarize(results)
    extra = {'args': vars(args)}
    if {'oracle', 'phi', 'blind'} <= set(args.controllers):
        rho = {c: {r['grip']: r['mean_rho'] for r in summary if r['controller'] == c}
               for c in ('oracle', 'phi', 'blind')}
        gaps = calibration_gaps(rho)
        swing = {c: cross_grip_swing(rho[c], args.grips) for c in rho}
        extra.update({
            'gaps': gaps,
            'cross_grip_variance': swing,
            'blind_over_phi_variance_ratio': swing['blind'] / swing['phi'] if swing['phi'] > 0 else float('nan'),
        })
        print('gap closed by φ:', {g: f'{v:.0%}' for g, v in gaps['gap_closed'].items()})
        print(f"cross-grip ρ variance, Blind/φ = {extra['blind_over_phi_variance_ratio']:.2f}×")
        if args.n_boot > 0:
            eps = {c: {g: np.array([r.mean_rho for r in sorted(results, key=lambda r: r.seed)
                                    if r.controller == c and r.grip == g])
                       for g in args.grips} for c in ('oracle', 'phi', 'blind')}
            boot = bootstrap_calibration(eps, args.grips, n_boot=args.n_boot, seed=args.seed)
            extra['bootstrap'] = boot
            for g, (lo, hi) in boot['gap_closed'].items():
                print(f'  gap closed at μ={g}: 95% CI [{lo:.0%}, {hi:.0%}]')
            lo, hi = boot['blind_over_phi_variance_ratio']
            print(f'  Blind/φ variance ratio: 95% CI [{lo:.2f}×, {hi:.2f}×]')

    out = out_dir(args, 'e1_e2')
    write_outputs(out, results, summary, extra)
    print(markdown_table(summary, ['controller', 'grip', 'n', 'crash_rate', 'completion_rate', 'mean_speed', 'mean_rho']))
    print(f'-> {out}')


if __name__ == '__main__':
    main()
