#!/usr/bin/env python3
"""
Speed-matched control readout (amendments 3-6): φ's episodes vs Blind capped at
φ's speed, paired on (seed, track) per grip. Exact McNemar on crashes.
Pre-registered pass rule at μ = 0.4: capped Blind crashes ≥ 0.10 more than φ,
p < 0.05.

    python tools/speed_matched_test.py <phi run dir> <capped-blind run dir> [--out file.md]
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats import load, mcnemar, wilson  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('phi_run', type=Path)
    ap.add_argument('capped_run', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    P, B = load(a.phi_run), load(a.capped_run)
    lines = [f'phi: {a.phi_run}  vs  capped Blind: {a.capped_run}', '',
             '| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |',
             '|---:|---:|---:|---|---:|---|']
    verdict = None
    for g in sorted({g for _, g in P}, reverse=True):
        p, b = P.get(('phi', g), {}), B.get(('blind', g), {})
        keys = sorted(set(p) & set(b))
        if not keys:
            continue
        cp = np.array([p[k]['crash'] for k in keys]); cb = np.array([b[k]['crash'] for k in keys])
        sp = np.mean([p[k]['speed'] for k in keys]); sb = np.mean([b[k]['speed'] for k in keys])
        pv = mcnemar(cp, cb)
        lo, hi = wilson(int(cb.sum()), len(cb))
        lines.append(f'| {g:.1f} | {len(keys)} | {cp.mean():.2f} | {cb.mean():.2f} [{lo:.2f}, {hi:.2f}] | {pv:.2g} | {sp:.2f} / {sb:.2f} |')
        if g == 0.4:
            verdict = bool(cb.mean() - cp.mean() >= 0.10 and pv < 0.05)
    if verdict is not None:
        lines += ['', f"- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **{'PASS' if verdict else 'FAIL'}**"]
    text = '\n'.join(lines) + '\n'
    print(text)
    if a.out:
        a.out.write_text(text)


if __name__ == '__main__':
    main()
