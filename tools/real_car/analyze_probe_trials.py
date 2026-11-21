#!/usr/bin/env python3
"""
Stage 1 analysis (docs/REAL_CAR_PROBE_PLAN.md): does the braking probe's response
separate surfaces of different grip?

Input: CSV from probe_maneuver_node.py (real car) or simulate_probe_trials.py
(simulator, known grip). Per trial, around the pulse:
  imu_decel      peak deceleration from the IMU (50 ms moving average), m/s^2
                 (only if imu_ax was logged). Physics: capped at mu*g.
  odom_drop      odometry speed just before the pulse minus odometry 60-120 ms after
                 it ends, m/s. While the wheel is locked, odometry reads the wheel,
                 not the car; once it rolls again it reads the car, which slowed by
                 about mu*g*pulse length.
  odom_drop_frac odom_drop / (pre-pulse odometry - pulse command): the car cannot
                 brake below the command, so this removes the cruise-speed confound
  lidar_drop     same speed drop, but from the front LiDAR range rate (true motion,
                 no wheel slip). Needs a wall ahead within range.
Also reported, descriptively: wheel_dip and slip_excess (does the wheel slip under the
pulse, as the simulator's slip model assumes?) and the peak motor current.
Pre-registered pass criterion (REAL_CAR_PROBE_PLAN.md): a metric differs across
surfaces (Kruskal-Wallis p < 0.05) and is lower for the lowest-grip surface than the
highest (one-sided Mann-Whitney p < 0.05). Surfaces are ordered by --order
(highest grip first).

    python tools/real_car/analyze_probe_trials.py probe_trials.csv --order bare duct electrical
"""
import argparse
import csv
from collections import defaultdict

import numpy as np
from scipy import stats as st


def per_trial(rows, pulse_s):
    t = np.array([float(r['t']) for r in rows])
    phase = np.array([r['phase'] for r in rows])
    if not (phase == 'pulse').any():
        return None
    t0 = t[phase == 'pulse'][0]
    t1 = t0 + pulse_s
    v = np.array([float(r['odom_speed']) for r in rows])
    out = {}
    pre = (t > t0 - 0.2) & (t < t0)
    post = (t > t1 + 0.06) & (t < t1 + 0.12)
    if pre.any() and post.any():
        out['odom_drop'] = float(np.nanmean(v[pre]) - np.nanmean(v[post]))
        # The car cannot brake below the pulse command, so normalize by the drop available
        cmd_pulse = float(rows[int(np.argmax(phase == 'pulse'))]['cmd_speed'])
        avail = np.nanmean(v[pre]) - cmd_pulse
        if avail > 0.2:
            out['odom_drop_frac'] = float(out['odom_drop'] / avail)
    # Wheel-slip signature (descriptive): how far the odometry (wheel) speed dips during the pulse,
    # and how much of that dip is gone once the wheel rolls again. No slip: dip = drop. A wheel
    # that locks towards the command: dip close to the full command step, well above the drop.
    during = (t >= t0) & (t <= t1 + 0.05)
    if pre.any() and during.any() and 'odom_drop' in out:
        out['wheel_dip'] = float(np.nanmean(v[pre]) - np.nanmin(v[during]))
        out['slip_excess'] = float(out['wheel_dip'] - out['odom_drop'])
    cur = np.array([float(r['motor_current']) if r.get('motor_current') not in (None, '', 'nan') else np.nan for r in rows])
    if np.isfinite(cur[during]).sum() > 2:
        out['brake_current'] = float(np.nanmax(np.abs(cur[during])))
    ax = np.array([float(r['imu_ax']) if r.get('imu_ax') not in (None, '', 'nan') else np.nan for r in rows])
    if np.isfinite(ax).sum() > 10:
        dt = np.median(np.diff(t))
        k = max(1, int(round(0.05 / dt)))
        sm = np.convolve(np.nan_to_num(ax), np.ones(k) / k, mode='same')
        win = (t >= t0) & (t <= t1 + 0.1)
        out['imu_decel'] = float(-sm[win].min())
    fr = np.array([float(r['front_range']) if r.get('front_range') not in (None, '', 'nan') else np.nan for r in rows])

    def lidar_speed(mask):
        m = mask & np.isfinite(fr) & (fr < 9.5)
        if m.sum() < 5:
            return np.nan
        return -np.polyfit(t[m], fr[m], 1)[0]
    vb = lidar_speed((t > t0 - 0.3) & (t < t0))
    va = lidar_speed((t > t1 + 0.05) & (t < t1 + 0.35))
    if np.isfinite(vb) and np.isfinite(va):
        out['lidar_drop'] = float(vb - va)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('csv')
    ap.add_argument('--order', nargs='+', help='surface labels, highest grip first (default: as they appear)')
    ap.add_argument('--pulse_s', type=float, default=0.1)
    ap.add_argument('--out', help='write the report here too (markdown)')
    a = ap.parse_args()
    trials = defaultdict(list)
    for r in csv.DictReader(open(a.csv)):
        trials[(r['surface'], r['trial'])].append(r)
    surfaces = a.order or list(dict.fromkeys(s for s, _ in trials))
    vals = {s: defaultdict(list) for s in surfaces}
    for (s, _), rows in trials.items():
        if s not in vals:
            continue
        m = per_trial(rows, a.pulse_s)
        for k, v in (m or {}).items():
            if np.isfinite(v):
                vals[s][k].append(v)
    lines = [f'# Probe test: {a.csv}', '', '| metric | ' + ' | '.join(surfaces) + ' | Kruskal-Wallis p | MWU p (first > last) | pass |',
             '|---|' + '---|' * (len(surfaces) + 3)]
    any_pass = False
    for metric in ('imu_decel', 'odom_drop', 'odom_drop_frac', 'lidar_drop'):
        groups = [vals[s][metric] for s in surfaces]
        if any(len(g) < 3 for g in groups):
            lines.append(f'| {metric} | ' + ' | '.join(f'n={len(g)}' for g in groups) + ' | – | – | not enough data |')
            continue
        kw = st.kruskal(*groups).pvalue
        mw = st.mannwhitneyu(groups[0], groups[-1], alternative='greater').pvalue
        ok = kw < 0.05 and mw < 0.05
        any_pass |= ok
        cells = ' | '.join(f'{np.median(g):.2f} [{np.percentile(g, 25):.2f}, {np.percentile(g, 75):.2f}] (n={len(g)})' for g in groups)
        lines.append(f'| {metric} | {cells} | {kw:.2g} | {mw:.2g} | {"**PASS**" if ok else "FAIL"} |')
    lines += ['', 'Cells: median [IQR]. imu_decel in m/s², drops in m/s.', '',
              'Descriptive (not part of the pass criterion):', '',
              '| quantity | ' + ' | '.join(surfaces) + ' |', '|---|' + '---|' * len(surfaces)]
    for metric, what in (('wheel_dip', 'odometry dip during the pulse (m/s)'),
                         ('slip_excess', 'dip minus drop after recovery (m/s); > 0 means the wheel slipped'),
                         ('brake_current', 'peak motor current during the pulse (A)')):
        cells = ' | '.join((f'{np.median(g):.2f} [{np.percentile(g, 25):.2f}, {np.percentile(g, 75):.2f}] (n={len(g)})'
                            if len(g) else 'not logged') for g in (vals[s_][metric] for s_ in surfaces))
        lines.append(f'| {what} | {cells} |')
    lines += ['', 'If slip_excess is near 0 on every surface, the wheels do not slip under the pulse: the grip signal '
              'is then only in odom_drop (true deceleration), which is the "no slip" model of RESULTS section 8.',
              'If brake_current is the same on every surface and odom_drop does not separate them, the pulse is '
              'motor-limited rather than tire-limited: use a larger --amplitude or a higher --cruise.',
              f"Overall: the probe's response {'**separates**' if any_pass else 'does **not** separate'} the surfaces on at least one metric."]
    text = '\n'.join(lines) + '\n'
    print(text)
    if a.out:
        open(a.out, 'w').write(text)


if __name__ == '__main__':
    main()
