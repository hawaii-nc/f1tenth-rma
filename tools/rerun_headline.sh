#!/bin/bash
# Rerun the headline experiments with seeded random start points (PREREGISTRATION
# amendment 2). Old start-line results are moved to <dir>_startline/ first.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
R=results/retrain_nov2026
L1=runs/phase1_retrain/selected.pt; L2=runs/phase2_retrain/final.pt; LC=configs/retrain_phase2.yaml
O2=runs/phase2_onpolicy/final.pt
F1=runs/phase1_fc/final.pt; F2=runs/phase2_fc/final.pt; FC=configs/retrain_phase2_fc_onpolicy.yaml

for d in linear friction_circle p1_onpolicy p2_friction_circle; do
  [[ -d $R/$d && ! -d $R/${d}_startline ]] && mv "$R/$d" "$R/${d}_startline"
done

e12() {  # p1 p2 cfg tire n out
  [[ -f $6/run/summary.json ]] && return 0
  mkdir -p "$6"; local pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n "$5" --grips $g --phase1 "$1" --phase2 "$2" --config "$3" \
      --tire-model "$4" --out "$6/_shards/g$g" > "$6.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$6"/_shards/g* --out "$6/run"
}
one() {  # script n p1 p2 cfg tire out
  [[ -f $7/run/summary.json ]] || python3 experiments/$1 -n "$2" --phase1 "$3" --phase2 "$4" --config "$5" --tire-model "$6" --out "$7/run" > "$7.log" 2>&1
}
mkdir -p $R/linear $R/friction_circle $R/p1_onpolicy $R/p2_friction_circle

echo "== E1/E2"
e12 $F1 $F2 $FC friction_circle 100 $R/p2_friction_circle/e1_e2
e12 $L1 $L2 $LC linear 100 $R/linear/e1_e2
e12 $L1 $O2 $LC linear 100 $R/p1_onpolicy/e1_e2
e12 $L1 $L2 $LC friction_circle 40 $R/friction_circle/e1_e2

echo "== E0 / E3 / E4 / E5"
pids=()
one e0_grip_gate.py 40 $F1 $F2 $FC friction_circle $R/p2_friction_circle/e0 & pids+=($!)
one e0_grip_gate.py 40 $L1 $L2 $LC linear $R/linear/e0 & pids+=($!)
one e5_signal.py 200 $F1 $F2 $FC friction_circle $R/p2_friction_circle/e5 & pids+=($!)
one e5_signal.py 200 $L1 $L2 $LC linear $R/linear/e5 & pids+=($!)
for p in "${pids[@]}"; do wait "$p"; done
pids=()
one e3_transient.py 40 $F1 $F2 $FC friction_circle $R/p2_friction_circle/e3 & pids+=($!)
one e3_transient.py 40 $L1 $L2 $LC linear $R/linear/e3 & pids+=($!)
one e4_causal.py 100 $L1 $L2 $LC linear $R/linear/e4 & pids+=($!)
one e5_signal.py 200 $L1 $O2 $LC linear $R/p1_onpolicy/e5 & pids+=($!)
for p in "${pids[@]}"; do wait "$p"; done

echo "== statistics"
python3 tools/provenance.py $R
for d in linear friction_circle p1_onpolicy p2_friction_circle; do
  python3 tools/stats.py $R/$d/e1_e2/run --out $R/stats_$d.md
done
echo "RERUN_DONE"
