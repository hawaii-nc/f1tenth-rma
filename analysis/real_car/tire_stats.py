#!/usr/bin/env python3
"""
Real-car tire experiment: per-trial statistics and Mann–Whitney U tests.

Setup (July 2026): Traxxas Slash 4×4 F1TENTH car "Vader", frozen φ-RMA
checkpoint, single 90° corner bounded by cardboard on polished concrete.
Grip changed by wrapping the tires: bare (control), foil, duct tape,
electrical tape: 19–21 trials each, 81 total.

Inputs per tire condition <name> (written on the car by deploy/trial_helpers.sh):
    rma_data_<name>.csv        per-step log from rma_deployment_node (ROS ns clock)
    rma_trial_log_<name>.csv   start_time,end_time,direction,trial,result (unix s)

Per trial, over samples with |v| > --min-speed:
    yaw_rate   mean |yaw rate| (rad/s)
    steer      mean |steer_action| (rad): the policy's own command
    phi_sd     within-trial sd of φ's ẑ, averaged over the 8 dims ("φ activity")

Then each condition is compared with the control by two-sided Mann–Whitney U.

Poster values (bare vs electrical tape): yaw p = 0.009, steering p = 0.0001;
φ activity 12× higher on tape than bare rubber. The exact aggregation used
for the poster was not preserved; this script's definitions are stated
above: re-derive the poster numbers with it before quoting them.

    python analysis/real_car/tire_stats.py --data-dir ~/vader_logs \
        --conditions bare foil duct electrical --control bare
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu


def load_trials(path: Path):
    with open(path) as f:
        return [dict(r, start_time=float(r['start_time']), end_time=float(r['end_time']))
                for r in csv.DictReader(f)]


def load_data(path: Path):
    cols = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get('lidar_received') in ('True', 'true', '1')]
    if not rows:
        return {}
    for key in ('time', 'velocity', 'yaw_rate', 'steer_action', 'phi_active'):
        cols[key] = np.array([float(r[key]) if r[key] != '' else np.nan for r in rows])
    cols['time'] = cols['time'] / 1e9  # ROS ns -> unix s
    phi = np.array([[float(r[f'phi_{i}']) if r.get(f'phi_{i}', '') != '' else np.nan for i in range(8)]
                    for r in rows])
    cols['phi'] = phi
    return cols


def trial_stats(data, trial, min_speed):
    m = (data['time'] >= trial['start_time']) & (data['time'] <= trial['end_time'])
    m &= np.abs(data['velocity']) > min_speed
    if not m.any():
        return None
    phi = data['phi'][m]
    phi = phi[~np.isnan(phi).any(axis=1)]
    return {
        'trial': trial['trial'],
        'result': trial['result'],
        'samples': int(m.sum()),
        'yaw_rate': float(np.nanmean(np.abs(data['yaw_rate'][m]))),
        'steer': float(np.nanmean(np.abs(data['steer_action'][m]))),
        'phi_sd': float(phi.std(axis=0).mean()) if len(phi) > 1 else float('nan'),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data-dir', type=Path, required=True)
    ap.add_argument('--conditions', nargs='+', required=True)
    ap.add_argument('--control', required=True)
    ap.add_argument('--min-speed', type=float, default=0.1)
    ap.add_argument('--passed-only', action='store_true', help='drop trials whose result is not pass')
    ap.add_argument('--out', type=Path, default=Path('results/real_car'))
    args = ap.parse_args()

    per_cond = {}
    for name in args.conditions:
        data = load_data(args.data_dir / f'rma_data_{name}.csv')
        trials = load_trials(args.data_dir / f'rma_trial_log_{name}.csv')
        stats = [s for t in trials if (s := trial_stats(data, t, args.min_speed))]
        if args.passed_only:
            stats = [s for s in stats if s['result'].lower().startswith('pass')]
        per_cond[name] = stats

    report = {'conditions': {}, 'tests': {}}
    print(f"{'condition':12s} {'n':>3s} {'pass':>4s} {'yaw (rad/s)':>12s} {'steer (rad)':>12s} {'φ sd':>8s}")
    for name, stats in per_cond.items():
        agg = {k: float(np.nanmean([s[k] for s in stats])) for k in ('yaw_rate', 'steer', 'phi_sd')} if stats else {}
        n_pass = sum(s['result'].lower().startswith('pass') for s in stats)
        report['conditions'][name] = {'n': len(stats), 'pass': n_pass, **agg}
        if stats:
            print(f"{name:12s} {len(stats):3d} {n_pass:4d} {agg['yaw_rate']:12.3f} {agg['steer']:12.3f} {agg['phi_sd']:8.4f}")

    ctrl = per_cond[args.control]
    for name, stats in per_cond.items():
        if name == args.control or not stats or not ctrl:
            continue
        tests = {}
        for metric in ('yaw_rate', 'steer', 'phi_sd'):
            a = [s[metric] for s in ctrl if np.isfinite(s[metric])]
            b = [s[metric] for s in stats if np.isfinite(s[metric])]
            if len(a) > 1 and len(b) > 1:
                res = mannwhitneyu(a, b, alternative='two-sided')
                tests[metric] = {'U': float(res.statistic), 'p': float(res.pvalue)}
        report['tests'][f'{args.control}_vs_{name}'] = tests
        print(f"{args.control} vs {name}: " + ', '.join(f"{m} p={t['p']:.4g}" for m, t in tests.items()))

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'tire_stats.json').write_text(json.dumps({'args': {k: str(v) for k, v in vars(args).items()},
                                                          'per_trial': per_cond, **report}, indent=2))
    print(f'-> {args.out / "tire_stats.json"}')


if __name__ == '__main__':
    main()
