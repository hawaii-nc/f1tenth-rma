#!/bin/bash
# Amendment 6b: speed-matched caps (measured speed = phi_Q's at mu = 1.0) for all seeds,
# plus a cap sweep on seed 0. Waits for tools/probe_suite.sh to finish. Resumable.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
C=configs/retrain_phase2_fc_probe.yaml
ROOT=results/retrain_nov2026/probe
while tmux has-session -t =probe 2>/dev/null; do sleep 60; done
e12b() {  # p1 p2 out cap
  local out=$3
  [[ -f $out/run/summary.json ]] && return 0
  mkdir -p "$out"; local pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n 100 --grips $g --controllers blind --speed-cap "$4" --phase1 "$1" \
      --phase2 "$2" --config $C --tire-model friction_circle --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
}
speed() { python3 -c "
import json; s = json.load(open('$1/run/summary.json'))['summary']
print([r['mean_speed'] for r in s if r['controller'] == '$2' and r['grip'] == 1.0][0])"; }
for s in 0 1 2; do
  if [[ $s == 0 ]]; then P1=runs/phase1_fc/final.pt; else P1=runs/phase1_fc_seed$s/final.pt; fi
  P2=runs/phase2_fc_probe_seed$s/final.pt; R=$ROOT/seed$s
  cap=$(python3 -c "print(round($(speed $R/e1_e2 phi) - ($(speed $R/speed_matched/e1_e2 blind) - $(speed $R/e1_e2 phi)), 2))")
  echo "== seed $s: matched cap $cap"
  e12b $P1 $P2 $R/speed_matched_measured/e1_e2 $cap
  python3 tools/speed_matched_test.py $R/e1_e2/run $R/speed_matched_measured/e1_e2/run --out $R/speed_matched_measured.md
  if [[ $s == 0 ]]; then
    for c in 1.3 1.5 1.7; do
      echo "== seed 0: sweep cap $c"
      e12b $P1 $P2 $R/cap_sweep_$c/e1_e2 $c
      python3 tools/speed_matched_test.py $R/e1_e2/run $R/cap_sweep_$c/e1_e2/run --out $R/cap_sweep_$c.md
    done
  fi
done
python3 tools/provenance.py $ROOT
echo CAP_SWEEP_DONE
