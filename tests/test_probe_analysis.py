"""Stage 1 analysis (tools/real_car/analyze_probe_trials.py) on the committed simulated trials."""
import csv
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / 'tools/real_car/analyze_probe_trials.py'
SIM = REPO / 'results/retrain_nov2026/real/probe_test_sim/sim_probe_trials.csv'
ORDER = ['grip_1.0', 'grip_0.7', 'grip_0.4']


def run(path):
    return subprocess.run([sys.executable, str(TOOL), str(path), '--order', *ORDER],
                          capture_output=True, text=True, check=True).stdout


def test_simulated_trials_separate_and_show_wheel_slip():
    out = run(SIM)
    assert '**separates**' in out
    row = next(line for line in out.splitlines() if line.startswith('| odom_drop |'))
    assert row.rstrip().endswith('**PASS** |')
    assert 'dip minus drop after recovery' in out


def test_survives_what_a_real_session_produces(tmp_path):
    """No IMU, no wall in LiDAR range, no VESC current, one aborted trial."""
    rows = list(csv.DictReader(open(SIM)))
    for r in rows:
        r['imu_ax'] = ''
        r['front_range'] = 'inf'
        r['motor_current'] = ''
    rows = [r for r in rows if not (r['surface'] == 'grip_0.7' and r['trial'] == '3' and r['phase'] != 'cruise')]
    p = tmp_path / 'trials.csv'
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    out = run(p)
    assert '| imu_decel | n=0 | n=0 | n=0 |' in out and 'not logged' in out
    assert '(n=19)' in out and '**separates**' in out
