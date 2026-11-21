#!/usr/bin/env python3
"""
Amendment 13 readouts from results/retrain_nov2026/real/amendment13.

  --arm B   bias/seed*/g*/episodes.csv: oracle, phi_cs, blind_cs, phi_b15_cs, phi_b30_cs
            on the same episodes (pessimistic grip margin, no retraining)
  --arm T   train_cs/seed*/g*/episodes.csv: phi_cs of the phi retrained with the cautious
            start, compared with amendment 12's phi_cs on the same episodes

    python tools/amendment13_stats.py --arm B [--out bias_stats.md]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cold_start_stats import crash_vec, load, speed  # noqa: E402
from stats import holm, mcnemar  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'results/retrain_nov2026/real/amendment13'
A12 = REPO / 'results/retrain_nov2026/real/amendment12'
EPS = 1e-9


def load_seed(d: Path):
    data = {}
    for run in sorted(d.glob('g*')):
        if (run / 'episodes.csv').exists():
            data.update(load(run / 'episodes.csv'))
    return data


def compare(ref, new, ref_name, new_name, grips, drop_min, speed_tol):
    """ref/new: {seed: data}. Readouts of new_name (in new) against ref_name (in ref)."""
    seeds = sorted(set(ref) & set(new))
    per, pool_a, pool_b = {}, [], []
    for s in seeds:
        per[s] = {}
        for g in grips:
            if (new_name, g) not in new[s] or (ref_name, g) not in ref[s]:
                continue
            keys = sorted(set(ref[s][(ref_name, g)]) & set(new[s][(new_name, g)]))
            a, b = crash_vec(ref[s], ref_name, g, keys), crash_vec(new[s], new_name, g, keys)
            per[s][g] = {'n': len(keys), 'ref_crash': float(a.mean()), 'new_crash': float(b.mean()),
                         'ref_speed': speed(ref[s], ref_name, g), 'new_speed': speed(new[s], new_name, g),
                         'p': mcnemar(b, a)}
            if g == 0.4:
                pool_a.append(a)
                pool_b.append(b)
    out = {'seeds': seeds, 'per_seed': per, 'complete': all(set(per[s]) == set(grips) for s in seeds) and len(seeds) == 3}
    if pool_a:
        a, b = np.concatenate(pool_a), np.concatenate(pool_b)
        worst = max(per[s][0.4]['new_crash'] - per[s][0.4]['ref_crash'] for s in seeds if 0.4 in per[s])
        out['pooled'] = {'n': int(a.size), 'ref': float(a.mean()), 'new': float(b.mean()),
                         'drop': float(a.mean() - b.mean()), 'p': mcnemar(b, a), 'worst_seed_change': float(worst)}
        out['cost_pass'] = all(
            per[s][g]['new_crash'] <= per[s][g]['ref_crash'] + 0.03 + EPS for s in seeds for g in (1.0, 0.6) if g in per[s]
        ) and all(per[s][1.0]['new_speed'] >= per[s][1.0]['ref_speed'] - speed_tol - EPS for s in seeds if 1.0 in per[s])
        if speed_tol <= 0.05 + EPS:   # arm T: the speed criterion also applies at mu 0.6
            out['cost_pass'] = out['cost_pass'] and all(
                per[s][0.6]['new_speed'] >= per[s][0.6]['ref_speed'] - speed_tol - EPS for s in seeds if 0.6 in per[s])
        out['drop_min'] = drop_min
    return out


def table(res, label):
    lines = [f'| seed | μ | crash reference / {label} | speed reference / {label} (m/s) | p |', '|---:|---:|---|---|---:|']
    for s in res['seeds']:
        for g, r in sorted(res['per_seed'][s].items(), reverse=True):
            lines.append(f"| {s} | {g} | {r['ref_crash']:.2f} / **{r['new_crash']:.2f}** | "
                         f"{r['ref_speed']:.2f} / {r['new_speed']:.2f} | {r['p']:.2g} |")
    return lines


def arm_b(root):
    data = {int(p.name[4:]): load_seed(p) for p in sorted((root / 'bias').glob('seed*'))}
    a12 = {int(p.name[4:]): load_seed(p) for p in sorted(A12.glob('seed*'))}
    res = {'arm': 'B', 'betas': {}}
    grips = (1.0, 0.6, 0.4)
    for name in ('phi_b15_cs', 'phi_b30_cs'):
        res['betas'][name] = compare(data, data, 'phi_cs', name, grips, 0.05, 0.10)
    ps = holm([res['betas'][n]['pooled']['p'] for n in res['betas']])
    for n, p in zip(res['betas'], ps):
        q = res['betas'][n]
        q['pooled']['p_holm'] = float(p)
        q['B1_pass'] = bool(q['pooled']['drop'] >= 0.05 - EPS and p < 0.05 and q['pooled']['worst_seed_change'] <= 0.02 + EPS)
        q['B2_pass'] = bool(q['cost_pass'])
    # reproducibility of phi_cs against amendment 12, and the other controllers for context
    diff = 0
    ctx = {}
    for s, d in data.items():
        ctx[s] = {}
        for g in grips:
            if ('phi_cs', g) not in d:
                continue
            keys = sorted(d[('phi_cs', g)])
            if s in a12 and ('phi_cs', g) in a12[s]:
                diff += int((crash_vec(d, 'phi_cs', g, keys) != crash_vec(a12[s], 'phi_cs', g, keys)).sum())
            ctx[s][g] = {c: float(crash_vec(d, c, g, keys).mean()) for c in ('oracle', 'blind_cs')}
            ctx[s][g]['speed_oracle'] = speed(d, 'oracle', g)
    res['phi_cs_episodes_differing_from_amendment12'] = diff
    res['context'] = ctx
    return res


def md_b(res):
    out = ['### Amendment 13, arm B: pessimistic grip margin (reference: φ_DR + cautious start)', '']
    for n, q in res['betas'].items():
        beta = int(n.split('_b')[1].split('_')[0]) / 100
        out += [f'**β = {beta:.2f}** (`{n}`)', ''] + table(q, f'β = {beta:.2f}')
        p = q['pooled']
        out += ['', f"Pooled μ = 0.4 (N = {p['n']}): {p['ref']:.3f} → {p['new']:.3f} (drop {p['drop']:.3f}, exact McNemar "
                f"p = {p['p']:.2g}, Holm {p['p_holm']:.2g}); worst per-seed change {p['worst_seed_change']:+.2f}.",
                f"- B1: {'**PASS**' if q['B1_pass'] else '**FAIL**'}   B2 (cost): {'**PASS**' if q['B2_pass'] else '**FAIL**'}", '']
    out.append('Oracle / Blind + cautious start crash, per seed and μ: ' + '; '.join(
        f"seed {s} μ {g}: {v['oracle']:.2f} / {v['blind_cs']:.2f}" for s, d in res['context'].items() for g, v in d.items()))
    out.append(f"`phi_cs` episodes whose crash outcome differs from amendment 12: {res['phi_cs_episodes_differing_from_amendment12']}.")
    return '\n'.join(out)


def arm_t(root):
    new = {int(p.name[4:]): load_seed(p) for p in sorted((root / 'train_cs').glob('seed*'))}
    new = {s: d for s, d in new.items() if d}
    ref = {int(p.name[4:]): load_seed(p) for p in sorted(A12.glob('seed*'))}
    res = compare(ref, new, 'phi_cs', 'phi_cs', (1.0, 0.6, 0.4), 0.05, 0.05)
    res['arm'] = 'T'
    if 'pooled' in res:
        p = res['pooled']
        res['T1_pass'] = bool(res['complete'] and p['drop'] >= 0.05 - EPS and p['p'] < 0.05 and p['worst_seed_change'] <= 0.02 + EPS)
        res['T2_pass'] = bool(res['complete'] and res['cost_pass'])
    res['e5_phi_r2'] = {}
    for s in new:
        f = root / f'train_cs/seed{s}/e5/summary.json'
        if f.exists():
            res['e5_phi_r2'][s] = json.loads(f.read_text())['r2']['phi']
    return res


def md_t(res):
    out = ['### Amendment 13, arm T: φ retrained with the cautious start (reference: amendment 12 φ_DR + cautious start)', '']
    out += table(res, 'retrained')
    if 'pooled' in res:
        p = res['pooled']
        out += ['', f"Pooled μ = 0.4 (N = {p['n']}, seeds {res['seeds']}): {p['ref']:.3f} → {p['new']:.3f} (drop {p['drop']:.3f}, "
                f"exact McNemar p = {p['p']:.2g}); worst per-seed change {p['worst_seed_change']:+.2f}.",
                'E5 grip R² of the retrained φ: ' + ', '.join(f'seed {s}: {v:.2f}' for s, v in sorted(res['e5_phi_r2'].items())) + '.',
                '']
        if res['complete']:
            out += [f"- T1: {'**PASS**' if res['T1_pass'] else '**FAIL**'}", f"- T2: {'**PASS**' if res['T2_pass'] else '**FAIL**'}"]
        else:
            out.append('- incomplete: verdicts need all three seeds and grips')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--arm', choices=['B', 'T'], required=True)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--out', type=Path, default=None)
    args = ap.parse_args()
    res = arm_b(args.root) if args.arm == 'B' else arm_t(args.root)
    text = md_b(res) if args.arm == 'B' else md_t(res)
    print(text)
    if args.out:
        args.out.write_text(text + '\n')
        args.out.with_suffix('.json').write_text(json.dumps(res, indent=1, default=float))


if __name__ == '__main__':
    main()
