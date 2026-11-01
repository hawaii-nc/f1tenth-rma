#!/bin/bash
# Robustness runs for the paper (docs/PREREGISTRATION_NOV2026.md), after tools/retrain_all.sh:
#   R1  replicate training seeds 1 and 2: Phase 1 (DAgger) + Phase 2 + E0, E1/E2, E5
#   R2  robust baseline: same DAgger recipe, no grip information (blind intrinsics) + E0, E1/E2
#   R3  held-out tracks: train without mco/silverstone/budapest; E1/E2 on those tracks,
#       for the held-out model and for the main model
#   R4  provenance.json for every result + statistics (tools/stats.py)
# Resumable: every stage is skipped if its output exists.
#   tmux new -s robust 'bash tools/robustness_suite.sh 2>&1 | tee runs/robustness.log'
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export PYTHONPATH="$REPO/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1   # several experiment processes share the cores
NPROC=${NPROC:-$(nproc --all)}  # --all: plain nproc obeys OMP_NUM_THREADS (=1 below)
RES=${RES:-results/retrain_nov2026}
MAIN_P1=${MAIN_P1:-runs/phase1_retrain/selected.pt}
MAIN_P2=${MAIN_P2:-runs/phase2_retrain/final.pt}
C2=configs/retrain_phase2.yaml
HOLD=(mco_tight silverstone_tight budapest_tight)
N12=${N12:-100}; N0=${N0:-40}; N5=${N5:-200}

phase1() {  # dir seed extra-args...
  local dir=$1 seed=$2; shift 2
  [[ -f $dir/final.pt ]] && return 0
  python3 -u -m f1tenth_research.training.phase1_ppo_il --config "${P1CFG:-configs/retrain_phase1.yaml}" --device cpu \
    --num_envs "$NPROC" --seed "$seed" --total_timesteps 0 --log_dir "$dir" --checkpoint_dir "$dir" "$@"
  python3 tools/validate_checkpoints.py "$dir"
}
phase2() {  # p1 dir seed config
  [[ -f $2/final.pt ]] && return 0
  TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint "$1" \
    --config "$4" --device cpu --num_envs "$NPROC" --seed "$3" --log_dir "$2" --checkpoint_dir "$2"
}
e12() {  # p1 p2 out extra-args...  (one process per grip, then merge)
  local p1=$1 p2=$2 out=$3; shift 3
  [[ -f $out/run/summary.json ]] && return 0
  local pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n "$N12" --grips $g --phase1 "$p1" --phase2 "$p2" --config "$C2" \
      "$@" --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
}
e0() { [[ -f $3/run/summary.json ]] || python3 experiments/e0_grip_gate.py -n "$N0" --phase1 "$1" --phase2 "$2" --config "$C2" --out "$3/run"; }
e5() { [[ -f $3/run/summary.json ]] || python3 experiments/e5_signal.py -n "$N5" --phase1 "$1" --phase2 "$2" --config "$C2" --out "$3/run"; }

mkdir -p "$RES" runs
echo "== R1 replicate seeds"
for s in 1 2; do
  phase1 runs/phase1_seed$s $s
  phase2 runs/phase1_seed$s/final.pt runs/phase2_seed$s $((12345 + s)) "$C2"
  P1=runs/phase1_seed$s/final.pt; P2=runs/phase2_seed$s/final.pt; O=$RES/seed$s
  mkdir -p "$O/e1_e2" "$O/e0" "$O/e5"
  e0 "$P1" "$P2" "$O/e0" > "$O/e0.log" 2>&1 &
  e12 "$P1" "$P2" "$O/e1_e2"
  wait
  e5 "$P1" "$P2" "$O/e5" > "$O/e5.log" 2>&1
done

echo "== R2 robust baseline (no grip information)"
phase1 runs/phase1_robust 0 --blind_intrinsics
O=$RES/robust; mkdir -p "$O/e1_e2" "$O/e0"
e0 runs/phase1_robust/final.pt "$MAIN_P2" "$O/e0" > "$O/e0.log" 2>&1 &
e12 runs/phase1_robust/final.pt "$MAIN_P2" "$O/e1_e2" --controllers blind
wait

echo "== R3 held-out tracks"
P1CFG=configs/retrain_phase1_holdout.yaml phase1 runs/phase1_holdout 0
phase2 runs/phase1_holdout/final.pt runs/phase2_holdout 12345 configs/retrain_phase2_holdout.yaml
mkdir -p "$RES/holdout/heldout_model/e1_e2" "$RES/holdout/main_model/e1_e2"
e12 runs/phase1_holdout/final.pt runs/phase2_holdout/final.pt "$RES/holdout/heldout_model/e1_e2" --tracks "${HOLD[@]}"
e12 "$MAIN_P1" "$MAIN_P2" "$RES/holdout/main_model/e1_e2" --tracks "${HOLD[@]}"

echo "== R4 provenance + statistics"
python3 tools/provenance.py "$RES"
python3 tools/stats.py "$RES/linear/e1_e2/run" "$RES/seed1/e1_e2/run" "$RES/seed2/e1_e2/run" \
  --labels seed0 seed1 seed2 --out "$RES/stats_seeds.md"
python3 tools/stats.py "$RES/friction_circle/e1_e2/run" --out "$RES/stats_friction_circle.md"
python3 tools/stats.py "$RES/holdout/heldout_model/e1_e2/run" "$RES/holdout/main_model/e1_e2/run" \
  --labels heldout_model main_model --out "$RES/stats_holdout.md"
python3 tools/stats.py "$RES/robust/e1_e2/run" --out "$RES/stats_robust.md"
echo "ROBUSTNESS_SUITE_DONE"
