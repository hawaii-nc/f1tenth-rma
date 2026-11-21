#!/usr/bin/env python3
"""
Compare two evaluation runs episode by episode (evaluation is deterministic, so a
rerun with the same code, checkpoints and simulator commit should be identical).

    python tools/compare_runs.py <rerun dir> <published run dir>

Each directory holds an episodes.csv. Only the cells (controller, grip) present
in both are compared. Exit status 1 if any shared episode differs in outcome.
"""
import argparse
import csv
import sys
from pathlib import Path


def load(run: Path):
    with open(run / 'episodes.csv') as f:
        return {(r['controller'], float(r['grip']), r['track'], int(r['seed'])): r for r in csv.DictReader(f)}


def compare(a: Path, b: Path):
    A, B = load(a), load(b)
    shared = sorted(set(A) & set(B))
    outcome = [k for k in shared if (A[k]['crashed'], A[k]['steps']) != (B[k]['crashed'], B[k]['steps'])]
    exact = sum(A[k] == B[k] for k in shared)
    cells = {}
    for k in shared:
        c = cells.setdefault(k[:2], [0, 0, 0])
        c[0] += 1
        c[1] += A[k]['crashed'] == 'True'
        c[2] += B[k]['crashed'] == 'True'
    return shared, outcome, exact, cells


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rerun', type=Path)
    ap.add_argument('published', type=Path)
    args = ap.parse_args()
    shared, outcome, exact, cells = compare(args.rerun, args.published)
    if not shared:
        sys.exit('no shared (controller, grip, track, seed) episodes')
    print('| controller | μ | n | crashes (rerun) | crashes (published) |')
    print('|---|---:|---:|---:|---:|')
    for (c, g), (n, x, y) in sorted(cells.items(), key=lambda t: (-t[0][1], t[0][0])):
        print(f'| {c} | {g} | {n} | {x} | {y} |')
    print(f'\n{len(shared)} shared episodes: {len(shared) - len(outcome)} with the same outcome and length, '
          f'{exact} identical in every column.')
    if outcome:
        print(f'{len(outcome)} DIFFER, e.g. {outcome[:3]}')
        sys.exit(1)


if __name__ == '__main__':
    main()
