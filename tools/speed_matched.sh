#!/bin/bash
# Amendment 3 (B2): P2 base policy as Blind with its speed capped at phi's speeds.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
R=${RES:-results/retrain_nov2026/robustness_fc}
for cap in 1.15 1.28; do
  out=$R/speed_matched_$cap/e1_e2
  [[ -f $out/run/summary.json ]] && continue
  mkdir -p "$out"; pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n 100 --grips $g --controllers blind --speed-cap $cap \
      --phase1 runs/phase1_fc/final.pt --phase2 runs/phase2_fc/final.pt --config configs/retrain_phase2_fc_onpolicy.yaml \
      --tire-model friction_circle --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
done
echo SPEED_MATCHED_DONE
