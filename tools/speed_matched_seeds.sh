#!/bin/bash
# Amendment 5: speed-matched Blind for replicate seeds (cap = phi_s's own mean speed at mu = 1.0).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
R=results/retrain_nov2026/robustness_fc
C=configs/retrain_phase2_fc_onpolicy.yaml
for s in 1 2; do
  [[ -f $R/seed$s/e1_e2/run/summary.json ]] || continue
  out=$R/seed$s/speed_matched/e1_e2
  [[ -f $out/run/summary.json ]] && continue
  cap=$(python3 -c "
import json; s = json.load(open('$R/seed$s/e1_e2/run/summary.json'))['summary']
print(round([r['mean_speed'] for r in s if r['controller'] == 'phi' and r['grip'] == 1.0][0], 2))")
  echo "seed $s cap $cap"
  mkdir -p "$out"; pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n 100 --grips $g --controllers blind --speed-cap $cap \
      --phase1 runs/phase1_fc_seed$s/final.pt --phase2 runs/phase2_fc_seed$s/final.pt --config $C \
      --tire-model friction_circle --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
done
echo SPEED_MATCHED_SEEDS_DONE
