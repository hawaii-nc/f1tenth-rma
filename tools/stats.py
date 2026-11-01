#!/usr/bin/env python3
"""
Statistics for E1/E2 runs, as fixed in docs/PREREGISTRATION_NOV2026.md.

Per (controller, grip): crash rate with a Wilson 95% CI, mean speed, and mean ρ
with an episode-bootstrap 95% CI. Per grip, φ vs Blind on paired episodes
(same seed, track and grip): exact McNemar on crashes and Wilcoxon signed-rank
on ρ, Holm-corrected across grips. Gap closed and the cross-grip variance
ratio get bootstrap CIs, resampling episode indices jointly across
controllers (they are paired). With several run dirs (training seeds), it
also reports the mean ± SD of the headline numbers across seeds.

    python tools/stats.py results/.../e1_e2/run                         # one run
    python tools/stats.py runA runB runC --labels s0 s1 s2 --out stats.md  # seeds
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats as st

B = 10_000
RNG = np.random.default_rng(0)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float('nan'),) * 2
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def load(run: Path):
    rows = list(csv.DictReader(open(run / 'episodes.csv')))
    data = {}
    for r in rows:
        key = (r['controller'], float(r['grip']))
        data.setdefault(key, {})[(int(r['seed']), r['track'])] = {
            'crash': r['crashed'] == 'True', 'speed': float(r['mean_speed']), 'rho': float(r['mean_rho'])}
    return data


def paired(data, grip, ctrls=('oracle', 'phi', 'blind')):
    """Arrays over the episodes present for every controller at this grip."""
    keys = set.intersection(*[set(data.get((c, grip), {})) for c in ctrls])
    keys = sorted(keys)
    out = {}
    for c in ctrls:
        d = data[(c, grip)]
        out[c] = {m: np.array([d[k][m] for k in keys], float) for m in ('crash', 'speed', 'rho')}
    return out, len(keys)


def gap(o, p, b):
    den = abs(np.nanmean(b) - np.nanmean(o))
    return 1 - abs(np.nanmean(p) - np.nanmean(o)) / den if den > 0 else float('nan')


def boot(fn, n):
    vals = []
    for _ in range(B):
        idx = RNG.integers(0, n, n)
        vals.append(fn(idx))
    vals = np.array(vals, float)
    vals = vals[np.isfinite(vals)]
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if len(vals) else (float('nan'),) * 2


def mcnemar(a, b):
    """Exact McNemar: a, b boolean arrays (paired)."""
    n01 = int(np.sum(a & ~b))
    n10 = int(np.sum(~a & b))
    if n01 + n10 == 0:
        return 1.0
    return float(st.binomtest(min(n01, n10), n01 + n10, 0.5).pvalue)


def wilcoxon(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 5 or np.allclose(a[m], b[m]):
        return float('nan')
    return float(st.wilcoxon(a[m], b[m]).pvalue)


def holm(ps):
    order = np.argsort(ps)
    adj = np.empty(len(ps))
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = running
    return adj.tolist()


def analyse(run: Path):
    data = load(run)
    grips = sorted({g for _, g in data}, reverse=True)
    ctrls = sorted({c for c, _ in data})
    res = {'run': str(run), 'cells': [], 'grips': {}}
    for c in ctrls:
        for g in grips:
            d = data.get((c, g))
            if not d:
                continue
            cr = np.array([v['crash'] for v in d.values()])
            rho = np.array([v['rho'] for v in d.values()])
            spd = np.array([v['speed'] for v in d.values()])
            lo, hi = wilson(int(cr.sum()), len(cr))
            rl, rh = boot(lambda i: np.nanmean(rho[i]), len(rho))
            res['cells'].append({'controller': c, 'grip': g, 'n': len(cr), 'crash_rate': float(cr.mean()),
                                 'crash_ci': [lo, hi], 'mean_speed': float(spd.mean()),
                                 'mean_rho': float(np.nanmean(rho)), 'rho_ci': [rl, rh]})
    if not {'oracle', 'phi', 'blind'} <= set(ctrls):
        return res
    p_crash, p_rho = [], []
    per_grip = {}
    for g in grips:
        P, n = paired(data, g)
        o, p, b = P['oracle'], P['phi'], P['blind']
        gl, gh = boot(lambda i: gap(o['rho'][i], p['rho'][i], b['rho'][i]), n)
        per_grip[g] = {'n_paired': n, 'gap_closed': gap(o['rho'], p['rho'], b['rho']), 'gap_ci': [gl, gh],
                       'phi_crash': float(p['crash'].mean()), 'blind_crash': float(b['crash'].mean()),
                       'oracle_crash': float(o['crash'].mean()),
                       'phi_speed': float(p['speed'].mean()), 'blind_speed': float(b['speed'].mean()),
                       'oracle_speed': float(o['speed'].mean())}
        p_crash.append(mcnemar(p['crash'].astype(bool), b['crash'].astype(bool)))
        p_rho.append(wilcoxon(p['rho'], b['rho']))
    pc_adj = holm(np.array(p_crash))
    pr = np.array([x if np.isfinite(x) else 1.0 for x in p_rho])
    pr_adj = holm(pr)
    for i, g in enumerate(grips):
        per_grip[g].update({'mcnemar_p': p_crash[i], 'mcnemar_p_holm': pc_adj[i],
                            'wilcoxon_rho_p': p_rho[i], 'wilcoxon_rho_p_holm': pr_adj[i]})
    res['grips'] = per_grip

    # cross-grip variance of per-grip mean ρ, Blind / φ, bootstrap over episodes
    Ps = {g: paired(data, g) for g in grips}

    def var_ratio(idx_by_g):
        mb = [np.nanmean(Ps[g][0]['blind']['rho'][idx_by_g[g]]) for g in grips]
        mp = [np.nanmean(Ps[g][0]['phi']['rho'][idx_by_g[g]]) for g in grips]
        vp = np.var(mp)
        return np.var(mb) / vp if vp > 0 else float('nan')
    full = {g: np.arange(Ps[g][1]) for g in grips}
    vals = [var_ratio({g: RNG.integers(0, Ps[g][1], Ps[g][1]) for g in grips}) for _ in range(2000)]
    vals = np.array(vals)[np.isfinite(vals)]
    res['variance_ratio_blind_over_phi'] = float(var_ratio(full))
    res['variance_ratio_ci'] = [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if len(vals) else None

    g4 = per_grip.get(0.4)
    if g4:
        res['hypotheses'] = {
            'G1 (gap closed >= 30% at 0.4, CI excludes 0)': bool(g4['gap_closed'] >= 0.30 and g4['gap_ci'][0] > 0),
            'H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05)':
                bool(g4['phi_crash'] <= g4['blind_crash'] - 0.30 and g4['mcnemar_p_holm'] < 0.05),
            'H3 (cross-grip variance ratio >= 10)': bool(res['variance_ratio_blind_over_phi'] >= 10),
        }
    return res


def md(res):
    out = [f"### {res['run']}\n", '| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |',
           '|---|---:|---:|---|---:|---|']
    for c in res['cells']:
        out.append(f"| {c['controller']} | {c['grip']:.1f} | {c['n']} | {c['crash_rate']:.2f} "
                   f"[{c['crash_ci'][0]:.2f}, {c['crash_ci'][1]:.2f}] | {c['mean_speed']:.2f} | "
                   f"{c['mean_rho']:.3f} [{c['rho_ci'][0]:.3f}, {c['rho_ci'][1]:.3f}] |")
    if res['grips']:
        out += ['', '| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |',
                '|---:|---|---|---:|---:|']
        for g, v in res['grips'].items():
            out.append(f"| {g:.1f} | {v['gap_closed']:.0%} [{v['gap_ci'][0]:.0%}, {v['gap_ci'][1]:.0%}] | "
                       f"{v['phi_crash']:.2f} / {v['blind_crash']:.2f} / {v['oracle_crash']:.2f} | "
                       f"{v['mcnemar_p_holm']:.2g} | {v['wilcoxon_rho_p_holm']:.2g} |")
        ci = res.get('variance_ratio_ci')
        out.append(f"\nCross-grip ρ variance, Blind/φ: {res['variance_ratio_blind_over_phi']:.2f}×"
                   + (f" [{ci[0]:.2f}, {ci[1]:.2f}]" if ci else ''))
    if res.get('hypotheses'):
        out += [''] + [f"- {k}: **{'PASS' if v else 'FAIL'}**" for k, v in res['hypotheses'].items()]
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('runs', nargs='+', type=Path)
    ap.add_argument('--labels', nargs='*')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    results = [analyse(r) for r in a.runs]
    text = ''.join(md(r) for r in results)
    if len(results) > 1:
        labels = a.labels or [str(r) for r in a.runs]
        text += '\n### Across training seeds\n\n| metric | ' + ' | '.join(labels) + ' | mean ± SD |\n|---|' + '---|' * (len(labels) + 1) + '\n'
        for g in sorted({g for r in results for g in r['grips']}, reverse=True):
            for m in ('gap_closed', 'phi_crash', 'blind_crash'):
                vals = [r['grips'].get(g, {}).get(m, float('nan')) for r in results]
                text += f"| {m} @ μ={g:.1f} | " + ' | '.join(f'{v:.2f}' for v in vals) + \
                        f" | {np.nanmean(vals):.2f} ± {np.nanstd(vals, ddof=1) if len(vals) > 1 else 0:.2f} |\n"
        vals = [r.get('variance_ratio_blind_over_phi', float('nan')) for r in results]
        text += '| variance ratio Blind/φ | ' + ' | '.join(f'{v:.2f}' for v in vals) + \
                f" | {np.nanmean(vals):.2f} ± {np.nanstd(vals, ddof=1):.2f} |\n"
    print(text)
    if a.out:
        a.out.write_text(text)
        a.out.with_suffix('.json').write_text(json.dumps(results, indent=2, default=float))


if __name__ == '__main__':
    main()
