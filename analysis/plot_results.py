#!/usr/bin/env python3
"""
Make the paper figures from experiment output folders.

Looks for the newest run of each experiment under a results root
(results/<exp>/<timestamp>/) and writes PNG + PDF figures to --out:

  e0_crash_vs_grip      E0 crash rate vs grip (Blind)
  e1_crash_vs_grip      E1 crash rate vs grip, one line per controller
  e2_rho_vs_grip        E2 mean rho vs grip with SEM bars (headline figure)
  e3_transient          E3 decoded grip and speed through the grip drop
  e4_interventions      E4 crash rate and mean speed per intervention

    python analysis/plot_results.py results/ --out figures/
"""
import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

COLORS = {'oracle': '#1b7837', 'phi': '#2166ac', 'blind': '#b2182b'}
LABELS = {'oracle': 'Oracle', 'phi': 'φ-RMA', 'blind': 'Blind'}


def latest(root: Path, exp: str):
    runs = sorted((root / exp).glob('*/summary.json')) if (root / exp).is_dir() else []
    return runs[-1].parent if runs else None


def load_summary(run: Path):
    return json.loads((run / 'summary.json').read_text())


def save(fig, out: Path, name: str):
    out.mkdir(parents=True, exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(out / f'{name}.{ext}', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'wrote {out / name}.png/.pdf')


def by_controller(rows):
    out = {}
    for r in rows:
        out.setdefault(r['controller'], []).append(r)
    for c in out:
        out[c].sort(key=lambda r: r['grip'], reverse=True)
    return out


def plot_e0(run, out):
    rows = sorted(load_summary(run)['summary'], key=lambda r: r['grip'], reverse=True)
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    ax.plot([r['grip'] for r in rows], [r['crash_rate'] for r in rows], 'o-', color=COLORS['blind'])
    ax.set_xlabel('grip μ (× nominal)')
    ax.set_ylabel('crash rate')
    ax.invert_xaxis()
    ax.grid(alpha=0.3)
    save(fig, out, 'e0_crash_vs_grip')


def plot_e1_e2(run, out):
    groups = by_controller(load_summary(run)['summary'])
    for metric, ylabel, name, err in (('crash_rate', 'crash rate', 'e1_crash_vs_grip', None),
                                      ('mean_rho', 'mean ρ (friction-circle use)', 'e2_rho_vs_grip', 'rho_sem')):
        fig, ax = plt.subplots(figsize=(3.4, 2.6))
        for c, rows in groups.items():
            ax.errorbar([r['grip'] for r in rows], [r[metric] for r in rows],
                        yerr=[r[err] for r in rows] if err else None, marker='o', capsize=2,
                        color=COLORS.get(c), label=LABELS.get(c, c))
        ax.set_xlabel('grip μ (× nominal)')
        ax.set_ylabel(ylabel)
        ax.invert_xaxis()
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=8)
        save(fig, out, name)


def plot_e3(run, out):
    path = run / 'trajectory.csv'
    if not path.exists():
        return
    with open(path) as f:
        rows = list(csv.DictReader(f))
    step = [int(r['step']) for r in rows]
    change = load_summary(run).get('args', {}).get('change_step')
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(3.6, 3.6), sharex=True)
    for ax, key, label in ((a1, 'decoded_grip', 'decoded grip'), (a2, 'speed', 'speed (m/s)')):
        m = [float(r[f'{key}_mean']) for r in rows]
        s = [float(r[f'{key}_sd']) for r in rows]
        ax.plot(step, m, color=COLORS['phi'])
        ax.fill_between(step, [a - b for a, b in zip(m, s)], [a + b for a, b in zip(m, s)],
                        color=COLORS['phi'], alpha=0.2, linewidth=0)
        if change:
            ax.axvline(change, color='0.4', linestyle='--', linewidth=1)
        ax.set_ylabel(label)
        ax.grid(alpha=0.3)
    a2.set_xlabel('step (50 Hz)')
    save(fig, out, 'e3_transient')


def plot_e4(run, out):
    rows = {r['controller']: r for r in load_summary(run)['summary']}
    order = [c for c in ('blindfold', 'restore', 'phi', 'oracle', 'hallucinate', 'phi_high') if c in rows]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.0, 2.4))
    a1.bar(order, [rows[c]['crash_rate'] for c in order], color='0.45')
    a1.set_ylabel('crash rate')
    a2.bar(order, [rows[c]['mean_speed'] for c in order], color='0.45')
    a2.set_ylabel('mean speed (m/s)')
    for ax in (a1, a2):
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=0.3)
    save(fig, out, 'e4_interventions')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root', type=Path, help='results root containing e0/, e1_e2/, e3/, e4/')
    ap.add_argument('--out', type=Path, default=Path('figures'))
    args = ap.parse_args()

    for exp, fn in (('e0', plot_e0), ('e1_e2', plot_e1_e2), ('e3', plot_e3), ('e4', plot_e4)):
        run = latest(args.root, exp)
        if run is None:
            print(f'no {exp} results under {args.root}, skipping')
            continue
        fn(run, args.out)


if __name__ == '__main__':
    main()
