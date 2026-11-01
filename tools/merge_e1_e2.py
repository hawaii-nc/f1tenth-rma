#!/usr/bin/env python3
"""
Merge E1/E2 runs that were split by grip level (one process per grip, to use
every core) into one result directory, with the same summary.json as a
single run, so analysis/plot_results.py works unchanged.

    python experiments/e1_e2_calibration.py --grips 1.0 --out res/e1_e2/g10 &
    python experiments/e1_e2_calibration.py --grips 0.8 --out res/e1_e2/g08 &  ...
    python tools/merge_e1_e2.py res/e1_e2/g10 res/e1_e2/g08 ... --out res/e1_e2/run
"""
import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src' / 'f1tenth_research'))

from f1tenth_research.eval.harness import EpisodeResult, markdown_table, summarize, write_outputs  # noqa: E402
from f1tenth_research.metrics import calibration_gaps, cross_grip_swing  # noqa: E402


def load(d: Path):
    out = []
    with open(d / 'episodes.csv') as f:
        for r in csv.DictReader(f):
            out.append(EpisodeResult(
                controller=r['controller'], grip=float(r['grip']), track=r['track'], seed=int(r['seed']),
                steps=int(r['steps']), crashed=r['crashed'] == 'True', completed=r['completed'] == 'True',
                mean_speed=float(r['mean_speed']), mean_rho=float(r['mean_rho']),
                max_rho=float(r['max_rho']), progress_m=float(r['progress_m'])))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('shards', nargs='+', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()

    results = [r for d in a.shards for r in load(d)]
    args0 = json.loads((a.shards[0] / 'summary.json').read_text()).get('args', {})
    grips = sorted({r.grip for r in results}, reverse=True)
    summary = summarize(results)
    extra = {'args': dict(args0, grips=grips, merged_from=[str(d) for d in a.shards])}
    ctrls = {r.controller for r in results}
    if {'oracle', 'phi', 'blind'} <= ctrls:
        rho = {c: {r['grip']: r['mean_rho'] for r in summary if r['controller'] == c}
               for c in ('oracle', 'phi', 'blind')}
        gaps = calibration_gaps(rho)
        swing = {c: cross_grip_swing(rho[c], grips) for c in rho}
        extra.update({
            'gaps': gaps,
            'cross_grip_variance': swing,
            'blind_over_phi_variance_ratio': swing['blind'] / swing['phi'] if swing['phi'] > 0 else float('nan'),
        })
        print('gap closed by φ:', {g: f'{v:.0%}' for g, v in gaps['gap_closed'].items()})
        print(f"cross-grip ρ variance, Blind/φ = {extra['blind_over_phi_variance_ratio']:.2f}×")
    write_outputs(a.out, results, summary, extra)
    print(markdown_table(summary, ['controller', 'grip', 'n', 'crash_rate', 'completion_rate', 'mean_speed', 'mean_rho']))
    print(f'-> {a.out}')


if __name__ == '__main__':
    main()
