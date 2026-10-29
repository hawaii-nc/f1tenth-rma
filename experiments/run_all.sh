#!/bin/bash
# Full E-series at the sample sizes used in July 2026. Needs f110_gym (see docker/Dockerfile)
# and the 14 *_tight tracks (python tools/prepare_tracks.py). Run inside tmux: this takes hours.
#   tmux new -s exps 'bash experiments/run_all.sh 2>&1 | tee results/run_all.log'
set -euo pipefail
cd "$(dirname "$0")"
python3 e0_grip_gate.py -n 40
python3 e1_e2_calibration.py -n 100
python3 e3_transient.py -n 40
python3 e4_causal.py -n 100
python3 e5_signal.py -n 200
