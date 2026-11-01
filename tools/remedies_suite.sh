#!/bin/bash
# Post-hoc remedy runs P1 and P2 (docs/PREREGISTRATION_NOV2026.md, addendum).
#   P1  on-policy φ (linear tire), same base policy
#   P2  friction-circle tire: Phase 1 DAgger + on-policy φ, evaluated under friction_circle
# Resumable. tmux new -s remedies 'bash tools/remedies_suite.sh 2>&1 | tee runs/remedies.log'
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
NPROC=${NPROC:-$(nproc)}
RES=${RES:-results/retrain_nov2026}
BASE=${BASE:-runs/phase1_retrain/selected.pt}

e12() {  # p1 p2 config tire out
  local p1=$1 p2=$2 cfg=$3 tire=$4 out=$5
  [[ -f $out/run/summary.json ]] && return 0
  local pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n 100 --grips $g --phase1 "$p1" --phase2 "$p2" --config "$cfg" \
      --tire-model "$tire" --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
}
e5() { [[ -f $5/run/summary.json ]] || python3 experiments/e5_signal.py -n 200 --phase1 "$1" --phase2 "$2" --config "$3" --tire-model "$4" --out "$5/run"; }
e0() { [[ -f $5/run/summary.json ]] || python3 experiments/e0_grip_gate.py -n 40 --phase1 "$1" --phase2 "$2" --config "$3" --tire-model "$4" --out "$5/run"; }

echo "== P1 on-policy phi (linear)"
if [[ ! -f runs/phase2_onpolicy/final.pt ]]; then
  TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint "$BASE" \
    --config configs/retrain_phase2_onpolicy.yaml --device cpu --num_envs "$NPROC" --log_dir runs/phase2_onpolicy --checkpoint_dir runs/phase2_onpolicy
fi
O=$RES/p1_onpolicy; mkdir -p "$O/e1_e2" "$O/e5"
e12 "$BASE" runs/phase2_onpolicy/final.pt configs/retrain_phase2.yaml linear "$O/e1_e2"
e5 "$BASE" runs/phase2_onpolicy/final.pt configs/retrain_phase2.yaml linear "$O/e5" > "$O/e5.log" 2>&1

echo "== P2 friction-circle tire"
if [[ ! -f runs/phase1_fc/final.pt ]]; then
  python3 -u -m f1tenth_research.training.phase1_ppo_il --config configs/retrain_phase1_fc.yaml --device cpu \
    --num_envs "$NPROC" --seed 0 --total_timesteps 0 --log_dir runs/phase1_fc --checkpoint_dir runs/phase1_fc
  python3 tools/validate_checkpoints.py runs/phase1_fc --config configs/retrain_phase2_fc_onpolicy.yaml
fi
if [[ ! -f runs/phase2_fc/final.pt ]]; then
  TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint runs/phase1_fc/final.pt \
    --config configs/retrain_phase2_fc_onpolicy.yaml --device cpu --num_envs "$NPROC" --log_dir runs/phase2_fc --checkpoint_dir runs/phase2_fc
fi
O=$RES/p2_friction_circle; mkdir -p "$O/e1_e2" "$O/e5" "$O/e0"
e0 runs/phase1_fc/final.pt runs/phase2_fc/final.pt configs/retrain_phase2_fc_onpolicy.yaml friction_circle "$O/e0" > "$O/e0.log" 2>&1 &
e12 runs/phase1_fc/final.pt runs/phase2_fc/final.pt configs/retrain_phase2_fc_onpolicy.yaml friction_circle "$O/e1_e2"
wait
e5 runs/phase1_fc/final.pt runs/phase2_fc/final.pt configs/retrain_phase2_fc_onpolicy.yaml friction_circle "$O/e5" > "$O/e5.log" 2>&1

echo "== statistics"
python3 tools/provenance.py "$RES"
python3 tools/stats.py "$RES/linear/e1_e2/run" "$RES/p1_onpolicy/e1_e2/run" --labels original p1_onpolicy --out "$RES/stats_p1.md"
python3 tools/stats.py "$RES/friction_circle/e1_e2/run" "$RES/p2_friction_circle/e1_e2/run" --labels linear_trained_on_fc p2_fc_trained --out "$RES/stats_p2.md"
echo "REMEDIES_DONE"
