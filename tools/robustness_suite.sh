#!/bin/bash
# Robustness runs (docs/PREREGISTRATION_NOV2026.md), on one configuration:
#   R0  post-hoc E0 on three more tracks (E0's aut_tight can be a track the base policy fails)
#   R2  robust baseline: same DAgger recipe, no grip information (blind intrinsics); E0 + E1/E2
#   R1  replicate training seeds 1 and 2: Phase 1 (DAgger) + Phase 2 + E1/E2, E5
#   R3  held-out tracks: train without mco/silverstone/budapest; E1/E2 on those tracks for the
#       held-out model and the main model
#   R4  provenance + statistics
# Configuration (defaults = original linear-tire setup; the friction-circle setup is
#   CONF=fc bash tools/robustness_suite.sh):
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
NPROC=${NPROC:-$(nproc --all)}  # --all: plain nproc obeys OMP_NUM_THREADS (=1 below)
export OMP_NUM_THREADS=1
CONF=${CONF:-linear}
if [[ $CONF == fc ]]; then
  TIRE=friction_circle; SUF=_fc
  P1CFG=configs/retrain_phase1_fc.yaml;  P1CFG_HOLD=configs/retrain_phase1_fc_holdout.yaml
  C2=configs/retrain_phase2_fc_onpolicy.yaml; C2_HOLD=configs/retrain_phase2_fc_onpolicy_holdout.yaml
  MAIN_P1=runs/phase1_fc/final.pt; MAIN_P2=runs/phase2_fc/final.pt
  RES=${RES:-results/retrain_nov2026/robustness_fc}
else
  TIRE=linear; SUF=
  P1CFG=configs/retrain_phase1.yaml;     P1CFG_HOLD=configs/retrain_phase1_holdout.yaml
  C2=configs/retrain_phase2.yaml;        C2_HOLD=configs/retrain_phase2_holdout.yaml
  MAIN_P1=runs/phase1_retrain/selected.pt; MAIN_P2=runs/phase2_retrain/final.pt
  RES=${RES:-results/retrain_nov2026/robustness_linear}
fi
HOLD=(mco_tight silverstone_tight budapest_tight)
N12=${N12:-100}; N0=${N0:-40}; N5=${N5:-200}
X=(--tire-model "$TIRE")

phase1() {  # dir seed config extra-args...
  local dir=$1 seed=$2 cfg=$3; shift 3
  [[ -f $dir/final.pt ]] && return 0
  python3 -u -m f1tenth_research.training.phase1_ppo_il --config "$cfg" --device cpu \
    --num_envs "$NPROC" --seed "$seed" --total_timesteps 0 --log_dir "$dir" --checkpoint_dir "$dir" "$@"
  python3 tools/validate_checkpoints.py "$dir" --config "$C2"
}
phase2() {  # p1 dir seed config
  [[ -f $2/final.pt ]] && return 0
  TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint "$1" \
    --config "$4" --device cpu --num_envs "$NPROC" --seed "$3" --log_dir "$2" --checkpoint_dir "$2"
}
e12() {  # p1 p2 out extra-args...
  local p1=$1 p2=$2 out=$3; shift 3
  [[ -f $out/run/summary.json ]] && return 0
  mkdir -p "$out"
  local pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n "$N12" --grips $g --phase1 "$p1" --phase2 "$p2" --config "$C2" \
      "${X[@]}" "$@" --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
}
e0() {  # p1 p2 out track
  [[ -f $3/run/summary.json ]] || python3 experiments/e0_grip_gate.py -n "$N0" --phase1 "$1" --phase2 "$2" --config "$C2" \
    "${X[@]}" --track "$4" --out "$3/run" > "$3.log" 2>&1
}
e5() { [[ -f $3/run/summary.json ]] || python3 experiments/e5_signal.py -n "$N5" --phase1 "$1" --phase2 "$2" --config "$C2" "${X[@]}" --out "$3/run" > "$3.log" 2>&1; }

mkdir -p "$RES" runs
echo "== R0 post-hoc E0 on more tracks ($CONF)"
pids=()
for t in ims_tight sochi_tight sepang_tight; do mkdir -p "$RES/e0_$t"; e0 "$MAIN_P1" "$MAIN_P2" "$RES/e0_$t" $t & pids+=($!); done
for p in "${pids[@]}"; do wait "$p"; done

echo "== R2 robust baseline (no grip information)"
phase1 runs/phase1_robust$SUF 0 "$P1CFG" --blind_intrinsics
e12 runs/phase1_robust$SUF/final.pt "$MAIN_P2" "$RES/robust/e1_e2" --controllers blind
python3 tools/stats.py "$RES/robust/e1_e2/run" --out "$RES/stats_robust.md" || true

echo "== R1 replicate seeds"
for s in 1 2; do
  phase1 runs/phase1${SUF}_seed$s $s "$P1CFG"
  phase2 runs/phase1${SUF}_seed$s/final.pt runs/phase2${SUF}_seed$s $((12345 + s)) "$C2"
  e12 runs/phase1${SUF}_seed$s/final.pt runs/phase2${SUF}_seed$s/final.pt "$RES/seed$s/e1_e2"
  mkdir -p "$RES/seed$s"
  e5 runs/phase1${SUF}_seed$s/final.pt runs/phase2${SUF}_seed$s/final.pt "$RES/seed$s/e5"
done

echo "== R3 held-out tracks"
phase1 runs/phase1${SUF}_holdout 0 "$P1CFG_HOLD"
phase2 runs/phase1${SUF}_holdout/final.pt runs/phase2${SUF}_holdout 12345 "$C2_HOLD"
e12 runs/phase1${SUF}_holdout/final.pt runs/phase2${SUF}_holdout/final.pt "$RES/holdout_model/e1_e2" --tracks "${HOLD[@]}"
e12 "$MAIN_P1" "$MAIN_P2" "$RES/main_model_on_holdout/e1_e2" --tracks "${HOLD[@]}"

echo "== R4 provenance + statistics"
python3 tools/provenance.py "$RES"
echo "ROBUSTNESS_SUITE_DONE"
