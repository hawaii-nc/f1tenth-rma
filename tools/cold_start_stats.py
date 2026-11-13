#!/usr/bin/env python3
"""
Amendment 12 (cold start): readouts C0-C3 from results/retrain_nov2026/real/amendment12.

Each seed*/g*/episodes.csv holds five controllers on the same episodes:
oracle, phi, blind, phi_cs and blind_cs (the last two start with a low-grip
belief until the first probe pulse at speed has ended; eval/harness.py).

    python tools/cold_start_stats.py [--out stats.md]

Also usable on any e1_e2 run to count early crashes:
    python tools/cold_start_stats.py --early results/.../e1_e2/run
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats import mcnemar, wilson  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'results/retrain_nov2026/real/amendment12'
PUBLISHED = REPO / 'results/retrain_nov2026/real/slipdr'
EARLY_STEPS = 200   # 2 s at 100 Hz


def load(path: Path):
    """{(controller, grip): {(track, seed): row}} with typed fields."""
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            row = {'crashed': r['crashed'] == 'True', 'steps': int(r['steps']),
                   'speed': float(r['mean_speed']), 'rho': float(r['mean_rho'])}
            out.setdefault((r['controller'], float(r['grip'])), {})[(r['track'], int(r['seed']))] = row
    return out


def cell(data, ctrl, grip):
    rows = data[(ctrl, grip)]
    keys = sorted(rows)
    return keys, rows


def crash_vec(data, ctrl, grip, keys=None):
    k, rows = cell(data, ctrl, grip)
    keys = keys or k
    return np.array([rows[i]['crashed'] for i in keys])


def rate(data, ctrl, grip):
    return float(crash_vec(data, ctrl, grip).mean())


def speed(data, ctrl, grip):
    _, rows = cell(data, ctrl, grip)
    return float(np.mean([r['speed'] for r in rows.values()]))


def early(data, ctrl, grip, steps=EARLY_STEPS):
    _, rows = cell(data, ctrl, grip)
    return sum(r['crashed'] and r['steps'] < steps for r in rows.values())


def early_table(run: Path):
    data = load(run / 'episodes.csv')
    lines = ['| controller | μ | crashes | first 1 s | first 2 s |', '|---|---:|---:|---:|---:|']
    for (c, g) in sorted(data, key=lambda t: (-t[1], t[0])):
        n = int(crash_vec(data, c, g).sum())
        lines.append(f'| {c} | {g} | {n} | {early(data, c, g, 100)} | {early(data, c, g, 200)} |')
    return '\n'.join(lines)


def analyse(root: Path = ROOT, published: Path = PUBLISHED):
    seeds = sorted(int(p.name[4:]) for p in root.glob('seed*') if p.is_dir())
    res = {'seeds': seeds, 'per_seed': {}, 'C0_mismatches': []}
    pooled = {'phi': [], 'phi_cs': []}
    for s in seeds:
        data = {}
        for run in sorted((root / f'seed{s}').glob('g*')):
            if (run / 'episodes.csv').exists():
                data.update(load(run / 'episodes.csv'))
        grips = sorted({g for _, g in data}, reverse=True)
        per = {}
        # C0: reruns against the published cells (section 8: grips 0.6 and 0.4)
        pub_csv = published / f'seed{s}/nominal/e1_e2/run/episodes.csv'
        pub = load(pub_csv) if pub_csv.exists() else {}
        for g in grips:
            for c in ('oracle', 'phi', 'blind'):
                if (c, g) in pub:
                    keys, _ = cell(data, c, g)
                    a, b = crash_vec(data, c, g, keys), crash_vec(pub, c, g, keys)
                    if int((a != b).sum()):
                        res['C0_mismatches'].append(
                            {'seed': s, 'grip': g, 'controller': c, 'rerun': int(a.sum()),
                             'published': int(b.sum()), 'episodes_differing': int((a != b).sum())})
        for g in grips:
            keys, _ = cell(data, 'phi', g)
            v = {c: crash_vec(data, c, g, keys) for c in ('oracle', 'phi', 'blind', 'phi_cs', 'blind_cs')}
            n = len(keys)
            per[g] = {
                'n': n,
                'crash': {c: float(x.mean()) for c, x in v.items()},
                'crash_ci_phi_cs': wilson(int(v['phi_cs'].sum()), n),
                'speed': {c: speed(data, c, g) for c in v},
                'early_2s': {c: early(data, c, g) for c in v},
                'p_phi_cs_vs_phi': mcnemar(v['phi_cs'], v['phi']),
                'p_phi_cs_vs_blind_cs': mcnemar(v['phi_cs'], v['blind_cs']),
            }
            if g == 0.4:
                pooled['phi'].append(v['phi'])
                pooled['phi_cs'].append(v['phi_cs'])
                gap = per[g]['crash']['phi'] - per[g]['crash']['oracle']
                per[g]['crash_gap_removed'] = ((per[g]['crash']['phi'] - per[g]['crash']['phi_cs']) / gap
                                               if gap > 0 else float('nan'))
        res['per_seed'][s] = per

    a, b = np.concatenate(pooled['phi']), np.concatenate(pooled['phi_cs'])
    drop = float(a.mean() - b.mean())
    p = mcnemar(b, a)
    worst = max(res['per_seed'][s][0.4]['crash']['phi_cs'] - res['per_seed'][s][0.4]['crash']['phi'] for s in seeds)
    res['pooled_mu0.4'] = {'n': int(a.size), 'phi': float(a.mean()), 'phi_cs': float(b.mean()),
                           'drop': drop, 'p': p, 'worst_seed_change': float(worst)}
    eps = 1e-9
    res['C0_pass'] = not res['C0_mismatches']
    res['C1_pass'] = bool(drop >= 0.07 - eps and p < 0.05 and worst <= 0.02 + eps)
    res['C2_pass'] = all(
        res['per_seed'][s][g]['crash']['phi_cs'] <= res['per_seed'][s][g]['crash']['phi'] + 0.03 + eps
        and res['per_seed'][s][g]['speed']['phi_cs'] >= res['per_seed'][s][g]['speed']['phi'] - 0.05 - eps
        for s in seeds for g in (1.0, 0.6) if g in res['per_seed'][s])
    res['C3_pass'] = all(
        res['per_seed'][s][0.4]['crash']['phi_cs'] <= res['per_seed'][s][0.4]['crash']['blind_cs'] - 0.30 + eps
        and res['per_seed'][s][0.4]['p_phi_cs_vs_blind_cs'] < 0.05 for s in seeds)
    return res


def md(res):
    out = ['### Amendment 12: cold start (φ_DR, default slip model)', '',
           '| seed | μ | crash Oracle / φ / φ+cautious start / Blind / Blind+cautious start | '
           'speed φ / φ+cs (m/s) | crashes in first 2 s: φ / φ+cs | p (φ+cs vs φ) | p (φ+cs vs Blind+cs) |',
           '|---:|---:|---|---|---|---:|---:|']
    for s in res['seeds']:
        for g, r in res['per_seed'][s].items():
            c, sp, e = r['crash'], r['speed'], r['early_2s']
            out.append(f"| {s} | {g} | {c['oracle']:.2f} / {c['phi']:.2f} / **{c['phi_cs']:.2f}** / "
                       f"{c['blind']:.2f} / {c['blind_cs']:.2f} | {sp['phi']:.2f} / {sp['phi_cs']:.2f} | "
                       f"{e['phi']} / {e['phi_cs']} | {r['p_phi_cs_vs_phi']:.2g} | {r['p_phi_cs_vs_blind_cs']:.2g} |")
    q = res['pooled_mu0.4']
    out += ['',
            f"Pooled μ = 0.4 (N = {q['n']}): φ {q['phi']:.3f} → φ + cautious start {q['phi_cs']:.3f} "
            f"(drop {q['drop']:.3f}, exact McNemar p = {q['p']:.2g}); worst per-seed change {q['worst_seed_change']:+.2f}.",
            'Share of the φ–Oracle crash gap removed at μ = 0.4, per seed: '
            + ', '.join(f"{res['per_seed'][s][0.4]['crash_gap_removed']:.0%}" for s in res['seeds']) + '.',
            '']
    v = lambda k: '**PASS**' if res[k] else '**FAIL**'  # noqa: E731
    out += [f"- C0 (reruns reproduce the published cells): {v('C0_pass')}"
            + ('' if res['C0_pass'] else f" ({len(res['C0_mismatches'])} cells differ; see stats.json)"),
            f"- C1 (pooled drop ≥ 0.07, p < 0.05, no seed worse by > 0.02): {v('C1_pass')}",
            f"- C2 (μ 1.0 and 0.6: crash ≤ φ + 0.03, speed ≥ φ − 0.05 m/s, every seed): {v('C2_pass')}",
            f"- C3 (μ 0.4: φ+cs ≤ Blind+cs − 0.30, p < 0.05, every seed): {v('C3_pass')}"]
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--out', type=Path, default=None, help='write the markdown here (and stats.json beside it)')
    ap.add_argument('--early', type=Path, default=None, help='only print the early-crash table of one e1_e2 run')
    args = ap.parse_args()
    if args.early:
        print(early_table(args.early))
        return
    res = analyse(args.root)
    text = md(res)
    print(text)
    if args.out:
        args.out.write_text(text + '\n')
        args.out.with_suffix('.json').write_text(json.dumps(res, indent=1, default=float))


if __name__ == '__main__':
    main()
