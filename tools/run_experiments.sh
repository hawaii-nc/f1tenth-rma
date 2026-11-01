#!/bin/bash
# Experiments only (stages 3-4 of tools/retrain_all.sh) for given checkpoints:
# E0-E5 under the linear tire, then E0 + E1/E2 under the friction-circle tire.
# This is what produced results/retrain_nov2026/{linear,friction_circle}.
#
#   P1=runs/phase1_retrain/selected.pt P2=runs/phase2_retrain/final.pt bash tools/run_experiments.sh
#
# Resumable (finished experiments are skipped). OMP_NUM_THREADS=1 matters: with
# PyTorch's default threading, 5 parallel experiment processes on 4 cores ran
# ~60x slower (8 vs ~500 steps/s per process).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
P1=${P1:?set P1=<phase 1 checkpoint>}
P2=${P2:?set P2=<phase 2 checkpoint>}
C2=${C2:-configs/retrain_phase2.yaml}
RES=${RES:-results/retrain_nov2026}
N0=40; N12=100; N3=40; N4=100; N5=200; NT=40; STEPS=2500

run_suite() {  # $1 = tire model, $2 = output root, $3 = all | tire
  local tire=$1 out=$2 which=$3
  local c=(--phase1 "$P1" --phase2 "$P2" --config "$C2" --tire-model "$tire" --max-steps "$STEPS")
  local n12=$N12; [[ $which == tire ]] && n12=$NT
  local pids=()
  mkdir -p "$out"
  if [[ ! -f $out/e1_e2/run/summary.json ]]; then
    for g in 1.0 0.8 0.6 0.4; do
      python3 experiments/e1_e2_calibration.py -n "$n12" --grips $g "${c[@]}" --out "$out/_shards/g$g" > "$out.e12_$g.log" 2>&1 &
      pids+=($!)
    done
  fi
  if [[ ! -f $out/e0/run/summary.json ]]; then
    python3 experiments/e0_grip_gate.py -n "$N0" "${c[@]}" --out "$out/e0/run" > "$out.e0.log" 2>&1 &
    pids+=($!)
  fi
  for p in "${pids[@]}"; do wait "$p"; done
  [[ -f $out/e1_e2/run/summary.json ]] || python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/e1_e2/run"
  if [[ $which == all ]]; then
    pids=()
    if [[ ! -f $out/e3/run/summary.json ]]; then python3 experiments/e3_transient.py -n "$N3" "${c[@]}" --out "$out/e3/run" > "$out.e3.log" 2>&1 & pids+=($!); fi
    if [[ ! -f $out/e4/run/summary.json ]]; then python3 experiments/e4_causal.py -n "$N4" "${c[@]}" --out "$out/e4/run" > "$out.e4.log" 2>&1 & pids+=($!); fi
    if [[ ! -f $out/e5/run/summary.json ]]; then python3 experiments/e5_signal.py -n "$N5" "${c[@]}" --out "$out/e5/run" > "$out.e5.log" 2>&1 & pids+=($!); fi
    for p in "${pids[@]}"; do wait "$p"; done
  fi
  python3 analysis/plot_results.py "$out" --out "$out/figures"
}

echo "== experiments (linear tire)"
run_suite linear "$RES/linear" all
echo "== tire robustness (friction-circle tire, same checkpoints)"
run_suite friction_circle "$RES/friction_circle" tire
echo "== statistics"
python3 tools/provenance.py "$RES"
python3 tools/stats.py "$RES/linear/e1_e2/run" --out "$RES/stats_linear.md"
python3 tools/stats.py "$RES/friction_circle/e1_e2/run" --out "$RES/stats_friction_circle.md"
echo "done: $RES"
