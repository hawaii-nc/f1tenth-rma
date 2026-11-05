#!/usr/bin/env python3
"""
Paper figures from results/retrain_nov2026 (no new runs). Writes PDF + PNG to paper/figures/.

  fig1_crash_vs_grip   crash rate vs grip, Oracle / phi / Blind, ideal sensors (Q) and car sensors (R),
                       mean over 3 training seeds, min-max band
  fig2_frontier        speed on full grip vs crash at grip 0.4: phi vs a fixed speed limit (Q, seed 0)
  fig3_readability     grip R2 of phi's estimate (E5) by configuration
  fig4_slip            crash at grip 0.4 under five wheel-slip models: phi_R, phi_DR, Blind (seed 0)

    python tools/make_figures.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
RES = REPO / 'results/retrain_nov2026'
OUT = REPO / 'paper/figures'
# Categorical slots 1-4 of the reference palette (validated: tools in the dataviz skill), fixed order:
# Oracle, phi, Blind, capped Blind. Two sit below 3:1 contrast, so every series is direct-labeled
# and has its own marker.
C = {'oracle': '#2a78d6', 'phi': '#eb6834', 'blind': '#1baf7a', 'capped': '#eda100'}
M = {'oracle': 's', 'phi': 'o', 'blind': '^', 'capped': 'D'}
NAME = {'oracle': 'Oracle (true grip)', 'phi': 'φ (adaptive)', 'blind': 'Blind (no grip info)'}
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.edgecolor': INK2, 'axes.labelcolor': INK,
    'xtick.color': INK2, 'ytick.color': INK2, 'axes.linewidth': 0.6, 'axes.grid': True,
    'grid.color': GRID, 'grid.linewidth': 0.5, 'axes.spines.top': False, 'axes.spines.right': False,
    'legend.frameon': False, 'figure.dpi': 200, 'savefig.bbox': 'tight', 'pdf.fonttype': 42})


def summary(run):
    return {(r['controller'], r['grip']): r for r in json.load(open(run / 'summary.json'))['summary']}


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ('pdf', 'png'):
        fig.savefig(OUT / f'{name}.{ext}')
    plt.close(fig)
    print('wrote', OUT / f'{name}.pdf')


def fig1():
    grips = [1.0, 0.8, 0.6, 0.4]
    configs = [
        ('Ideal sensors + probe (Q)', [RES / f'probe/seed{s}/e1_e2/run' for s in range(3)]),
        ('Car sensors + braking probe,\nracing expert (R)', [RES / f'real/seed{s}/e1_e2/run' for s in range(3)]),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.5), sharey=True)
    for ax, (title, runs) in zip(axes, configs):
        S = [summary(r) for r in runs]
        ends = {c: np.mean([s[(c, 0.4)]['crash_rate'] for s in S]) for c in ('oracle', 'phi', 'blind')}
        if abs(ends['phi'] - ends['oracle']) < 0.06:      # keep the two end labels apart
            hi, lo = ('phi', 'oracle') if ends['phi'] >= ends['oracle'] else ('oracle', 'phi')
            ends[hi] = max(ends[hi], ends[lo] + 0.06)
        for c in ('oracle', 'phi', 'blind'):
            y = np.array([[s[(c, g)]['crash_rate'] for g in grips] for s in S])
            ax.fill_between(grips, y.min(0), y.max(0), color=C[c], alpha=0.15, linewidth=0)
            ax.plot(grips, y.mean(0), color=C[c], lw=1.5, marker=M[c], ms=4.5,
                    markeredgecolor='white', markeredgewidth=0.6, label=NAME[c])
            ax.annotate(NAME[c].split(' (')[0], (0.4, ends[c]), xytext=(4, 0), textcoords='offset points',
                        va='center', fontsize=7, color=INK)
        ax.set_title(title, fontsize=8, color=INK, loc='left')
        ax.set_xlim(1.03, 0.33)
        ax.set_xticks(grips)
        ax.set_xlabel('grip (friction factor)')
    axes[0].set_ylabel('crash rate')
    axes[0].set_ylim(-0.02, 1.0)
    axes[1].legend(loc='upper left', fontsize=7)
    save(fig, 'fig1_crash_vs_grip')


def fig2():
    s0 = summary(RES / 'probe/seed0/e1_e2/run')
    pts = [('φ (adaptive)', s0[('phi', 1.0)]['mean_speed'], s0[('phi', 0.4)]['crash_rate'], 'phi'),
           ('Oracle', s0[('oracle', 1.0)]['mean_speed'], s0[('oracle', 0.4)]['crash_rate'], 'oracle'),
           ('Blind, no limit', s0[('blind', 1.0)]['mean_speed'], s0[('blind', 0.4)]['crash_rate'], 'blind')]
    caps = []
    for name, d in (('limit 1.3', 'cap_sweep_1.3'), ('limit 1.5', 'cap_sweep_1.5'), ('limit 1.7', 'cap_sweep_1.7'),
                    ('limit 1.93', 'speed_matched_measured')):
        s = summary(RES / f'probe/seed0/{d}/e1_e2/run')
        caps.append((name, s[('blind', 1.0)]['mean_speed'], s[('blind', 0.4)]['crash_rate']))
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    cx, cy = [c[1] for c in caps], [c[2] for c in caps]
    ax.plot(cx, cy, color=C['capped'], lw=1.5, marker=M['capped'], ms=4.5, markeredgecolor='white',
            markeredgewidth=0.6, label='Blind with a fixed speed limit')
    for name, x, y in caps:
        ax.annotate(name, (x, y), xytext=(-2, 8), textcoords='offset points', fontsize=6.5, color=INK2, ha='center')
    offs = {'phi': (0, -12, 'center'), 'oracle': (0, 7, 'center'), 'blind': (-6, 0, 'right')}
    for name, x, y, c in pts:
        ax.plot([x], [y], marker=M[c], color=C[c], ms=6, markeredgecolor='white', markeredgewidth=0.8, ls='none')
        dx, dy, ha = offs[c]
        ax.annotate(name, (x, y), xytext=(dx, dy), textcoords='offset points', fontsize=7, color=INK, ha=ha, va='center')
    ax.set_xlabel('mean speed on full grip (m/s)')
    ax.set_ylabel('crash rate at grip 0.4')
    ax.set_ylim(-0.04, 0.55)
    ax.set_xlim(1.35, 2.25)
    ax.legend(loc='upper left', fontsize=6.5)
    save(fig, 'fig2_frontier')


def fig3():
    def r2(path):
        return json.load(open(path / 'summary.json'))['r2']['phi']
    rows = [
        ('No probe, ideal sensors (P2)', np.mean([r2(RES / 'p2_friction_circle/e5/run')] +
                                                [r2(RES / f'robustness_fc/seed{s}/e5/run') for s in (1, 2)])),
        ('Probe, ideal sensors (Q)', np.mean([r2(RES / f'probe/seed{s}/e5/run') for s in range(3)])),
        ('Probe, car sensors (R)', np.mean([r2(RES / f'real/seed{s}/e5/run') for s in range(3)])),
        ('R, probe switched off', r2(RES / 'real/robustness/probe_off/e5/run')),
        ('Car sensors, slip-randomized (DR)', np.mean([r2(RES / f'real/slipdr/seed{s}/nominal/e5/run') for s in range(3)])),
        ('DR, wheels never slip', np.mean([r2(RES / f'real/slipdr/seed{s}/slip_none/e5/run') for s in range(3)])),
    ]
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    y = np.arange(len(rows))[::-1]
    vals = [max(v, 0.0) for _, v in rows]
    ax.barh(y, vals, height=0.6, color=C['phi'], edgecolor='white', linewidth=1.0)
    for yi, (name, v) in zip(y, rows):
        ax.text(max(v, 0) + 0.02, yi, f'{max(v, 0.0):.2f}', va='center', fontsize=7, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels([n for n, _ in rows], fontsize=7)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel('grip R² of φ\'s estimate (E5)')
    ax.grid(axis='y', visible=False)
    save(fig, 'fig3_readability')


def fig4():
    variants = [('default', 'nominal', None), ('slow spin-up', 'slip_slow', 'slip_slow'),
                ('fast spin-up', 'slip_fast', 'slip_fast'), ('slow recovery', 'slip_longrelax', 'slip_longrelax'),
                ('no slip', 'slip_none', 'slip_none')]
    rows = []
    for label, dr, rob in variants:
        d = summary(RES / f'real/slipdr/seed0/{dr}/e1_e2/run')
        r = summary(RES / ('real/seed0/e1_e2/run' if rob is None else f'real/robustness/{rob}/e1_e2/run'))
        rows.append((label, r[('phi', 0.4)]['crash_rate'], d[('phi', 0.4)]['crash_rate'], d[('blind', 0.4)]['crash_rate']))
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    x = np.arange(len(rows))
    series = [('φ trained on one slip model', 1, '#9a9893', 'v'), ('φ, slip model randomized', 2, C['phi'], 'o'),
              ('Blind', 3, C['blind'], '^')]
    for name, k, col, mk in series:
        ax.plot(x, [r[k] for r in rows], ls='none', marker=mk, ms=6, color=col, markeredgecolor='white',
                markeredgewidth=0.8, label=name)
    for xi, r in zip(x, rows):
        ax.plot([xi, xi], [r[1], r[2]], color=INK2, lw=0.6, zorder=0)
    ax.set_xticks(x)
    ax.set_xticklabels([r[0] for r in rows], fontsize=7, rotation=20, ha='right')
    ax.set_ylabel('crash rate at grip 0.4')
    ax.set_ylim(0, 1.0)
    ax.legend(loc='lower left', fontsize=6.5)
    ax.set_xlabel('wheel-slip model at test time')
    save(fig, 'fig4_slip')


if __name__ == '__main__':
    fig1(); fig2(); fig3(); fig4()
