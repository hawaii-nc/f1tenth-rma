#!/usr/bin/env python3
"""
E0: Grip load-bearing gate (project record Stage 0).

Question: does surface grip physically constrain the car in this simulator?
Method:   Blind controller (always believes nominal grip), forced grip sweep,
          N episodes per level on one track (default aut_tight).
Pass:     crash rate does not decrease as grip drops, and is strictly higher
          at the lowest grip than at nominal. If it fails, grip_factor is not
          reaching the tire model and nothing downstream is meaningful.

July 2026 result (pre physics-injection fix): PASS, N=40, aut_tight.

    python experiments/e0_grip_gate.py -n 40
"""
from _common import base_parser, load_config, out_dir

from f1tenth_research.eval.harness import (
    Blind, load_policy_pair, make_env, markdown_table, run_episode, summarize, write_outputs,
)


def main():
    ap = base_parser(__doc__, n_default=40)
    ap.add_argument('--grips', type=float, nargs='*', default=[1.0, 0.8, 0.6, 0.4, 0.2])
    ap.add_argument('--track', default='aut_tight')
    args = ap.parse_args()

    cfg = load_config(args.config)
    ac, _, _ = load_policy_pair(args.phase1, None, args.device)
    env = make_env(cfg, args.max_steps)
    ctrl = Blind(ac, args.device)

    results = []
    for grip in args.grips:
        for i in range(args.episodes):
            results.append(run_episode(env, ac, ctrl, grip, seed=args.seed + i,
                                       track=args.track, device=args.device))
        print(f'grip={grip}: done')
    summary = summarize(results)
    by_grip = {r['grip']: r['crash_rate'] for r in summary}
    ordered = [by_grip[g] for g in sorted(by_grip, reverse=True)]  # nominal → lowest
    monotone = all(b >= a for a, b in zip(ordered, ordered[1:]))
    passed = monotone and ordered[-1] > ordered[0]

    out = out_dir(args, 'e0')
    write_outputs(out, results, summary, {'pass': passed, 'monotone': monotone, 'args': vars(args)})
    print(markdown_table(summary, ['grip', 'n', 'crash_rate', 'mean_speed', 'mean_rho']))
    print(f"E0 {'PASS' if passed else 'FAIL'} (monotone={monotone}) -> {out}")


if __name__ == '__main__':
    main()
