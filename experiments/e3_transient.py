#!/usr/bin/env python3
"""
E3: Transient response: how fast does φ notice a sudden grip change?

Each episode starts at grip_before and switches to grip_after at a fixed
step (default step 500 = 10 s at 50 Hz): the simulator's μ really changes
(the July pipeline only changed the label; see docs/BUGS_AND_LESSONS.md).

A linear probe ẑ → grip is fit on separate steady-grip calibration
episodes (grip ∈ {1.0, 0.8, 0.6, 0.4, 0.2}), then applied to φ's ẑ along
the step-change episodes. Reported:
  * decoded-grip trajectory (mean ± sd across episodes), CSV
  * settle time: first step after the change at which the decoded grip
    stays within ±band of its post-change steady value for `hold` steps
  * speed trajectory, for the behavioural response

φ's memory length limits how fast it can react; the 50-step φ needs at
least 1 s. A 100-step φ was being trained for this test in July (not in
the repo). Target from the project record: ~50 steps (1 s).

    python experiments/e3_transient.py -n 40
"""
import csv

import numpy as np
from _common import base_parser, eval_tracks, load_config, out_dir, track_for

from f1tenth_research.eval.harness import Phi, load_policy_pair, make_env, run_episode, write_outputs
from f1tenth_research.metrics import fit_ridge


def settle_step(decoded, change, band, hold):
    post = decoded[change:]
    if len(post) < hold * 2:
        return None
    target = np.median(post[-hold:])
    ok = np.abs(post - target) <= band
    for i in range(len(ok) - hold):
        if ok[i:i + hold].all():
            return i
    return None


def main():
    ap = base_parser(__doc__, n_default=40)
    ap.add_argument('--grip-before', type=float, default=1.0)
    ap.add_argument('--grip-after', type=float, default=0.4)
    ap.add_argument('--change-step', type=int, default=500)
    ap.add_argument('--calib-episodes', type=int, default=10, help='per calibration grip level')
    ap.add_argument('--band', type=float, default=0.1)
    ap.add_argument('--hold', type=int, default=25)
    args = ap.parse_args()

    cfg = load_config(args.config)
    ac, phi, _ = load_policy_pair(args.phase1, args.phase2, args.device)
    env = make_env(cfg, args.max_steps)
    tracks = eval_tracks(args, cfg)
    ctrl = Phi(ac, phi, args.device)

    # 1) probe ẑ -> grip on steady-grip episodes
    Z, y = [], []
    for grip in (1.0, 0.8, 0.6, 0.4, 0.2):
        for i in range(args.calib_episodes):
            r = run_episode(env, ac, ctrl, grip, seed=10_000 + args.seed + i, track=track_for(i, tracks),
                            keep_trace=True, device=args.device)
            zs = np.asarray(r.trace['z'])[phi.history_window:]
            Z.append(zs)
            y.append(np.full(len(zs), grip))
    probe = fit_ridge(np.concatenate(Z), np.concatenate(y))

    # 2) step-change episodes
    decoded, speeds, settles, results = [], [], [], []
    for i in range(args.episodes):
        r = run_episode(env, ac, ctrl, args.grip_before, seed=args.seed + i, track=track_for(i, tracks),
                        disturbance_step=args.change_step, disturbance_grip=args.grip_after,
                        keep_trace=True, device=args.device)
        results.append(r)
        if r.steps <= args.change_step:
            continue  # crashed before the change
        d = probe.predict(np.asarray(r.trace['z']))
        decoded.append(d)
        speeds.append(np.asarray(r.trace['v']))
        settles.append(settle_step(d, args.change_step, args.band, args.hold))

    out = out_dir(args, 'e3')
    T = min((len(d) for d in decoded), default=0)
    if T:
        D = np.stack([d[:T] for d in decoded])
        V = np.stack([v[:T] for v in speeds])
        out.mkdir(parents=True, exist_ok=True)
        with open(out / 'trajectory.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['step', 'decoded_grip_mean', 'decoded_grip_sd', 'speed_mean', 'speed_sd'])
            for t in range(T):
                w.writerow([t + 1, D[:, t].mean(), D[:, t].std(), V[:, t].mean(), V[:, t].std()])
    valid = [s for s in settles if s is not None]
    extra = {
        'args': vars(args),
        'episodes_reaching_change': len(decoded),
        'settled_fraction': len(valid) / len(settles) if settles else 0.0,
        'settle_steps_median': float(np.median(valid)) if valid else None,
        'settle_seconds_median': float(np.median(valid)) / 50.0 if valid else None,
        'phi_history_window': phi.history_window,
    }
    write_outputs(out, results, [], extra)
    print({k: v for k, v in extra.items() if k != 'args'})
    print(f'-> {out}')


if __name__ == '__main__':
    main()
