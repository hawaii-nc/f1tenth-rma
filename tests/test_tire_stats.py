"""analysis/real_car/tire_stats.py on synthetic on-car logs with a known effect."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
HEADER = (['time', 'lidar_received', 'velocity', 'yaw_rate', 'pose_x', 'pose_y', 'lidar_min', 'lidar_mean',
           'v_des', 'steer_des', 'phi_active', 'raw_steer', 'raw_throttle', 'steer_action', 'throttle_action']
          + [f'phi_{i}' for i in range(8)] + [f'lidar_{i}' for i in range(108)])


def write_condition(d: Path, name: str, yaw: float, steer: float, phi_sd: float, rng, trials=12):
    t0 = 1_783_000_000.0
    with open(d / f'rma_trial_log_{name}.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['start_time', 'end_time', 'direction', 'trial', 'result'])
        for k in range(trials):
            w.writerow([t0 + 10 * k, t0 + 10 * k + 5, 'cw', k + 1, 'pass'])
    with open(d / f'rma_data_{name}.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for k in range(trials):
            for s in range(250):
                t = t0 + 10 * k + s * 0.02
                row = [int(t * 1e9), True, 1.5, yaw + rng.normal(0, 0.02), '', '', 1, 2, 1.5, steer, 1,
                       steer, 0, steer + rng.normal(0, 0.005), 0]
                row += list(rng.normal(0, phi_sd, 8)) + [3.0] * 108
                w.writerow(row)


def test_detects_known_difference(tmp_path):
    rng = np.random.default_rng(0)
    write_condition(tmp_path, 'bare', yaw=0.68, steer=0.133, phi_sd=0.01, rng=rng)
    write_condition(tmp_path, 'tape', yaw=0.64, steer=0.128, phi_sd=0.12, rng=rng)
    out = tmp_path / 'out'
    subprocess.run([sys.executable, str(REPO / 'analysis/real_car/tire_stats.py'), '--data-dir', str(tmp_path),
                    '--conditions', 'bare', 'tape', '--control', 'bare', '--out', str(out)],
                   check=True, capture_output=True)
    report = json.loads((out / 'tire_stats.json').read_text())
    assert report['conditions']['bare']['n'] == 12
    tests = report['tests']['bare_vs_tape']
    assert tests['yaw_rate']['p'] < 0.01 and tests['steer']['p'] < 0.01 and tests['phi_sd']['p'] < 0.01
    ratio = report['conditions']['tape']['phi_sd'] / report['conditions']['bare']['phi_sd']
    assert 8 < ratio < 16
