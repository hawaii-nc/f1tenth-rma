#!/bin/bash
# Full retraining of the RMA pipeline in the rebuilt environment, then every
# experiment (docs/RETRAINING.md). This is what produced results/retrain_nov2026/.
#
#   python tools/prepare_tracks.py                         # once: 13 drivable *_tight tracks
#   tmux new -s retrain 'bash tools/retrain_all.sh 2>&1 | tee runs/retrain_all.log'
#
# Stages (each skipped if its output already exists, so the script is resumable):
#   0. pytest + real-simulator physics pre-flight
#   1. Phase 1: π, μ, V with PPO + imitation   -> runs/phase1_retrain/final.pt   (~6 h on 4 cores)
#   2. Phase 2: φ                               -> runs/phase2_retrain/final.pt   (~2-3 h)
#   3. E0-E5 with the retrained pair            -> $RES/linear/
#   4. Tire robustness: E0 + E1/E2 under the friction-circle tire, same checkpoints -> $RES/friction_circle/
#
# Env: NPROC (parallel processes, default nproc), RES (results dir), QUICK=1 (tiny smoke run).
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
export PYTHONPATH="$REPO/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
NPROC=${NPROC:-$(nproc)}
RES=${RES:-results/retrain_nov2026}
P1DIR=runs/phase1_retrain
P2DIR=runs/phase2_retrain
C1=configs/retrain_phase1.yaml
C2=configs/retrain_phase2.yaml
mkdir -p runs "$RES"

if [[ "${QUICK:-0}" == 1 ]]; then
  P1DIR=runs/quick_phase1; P2DIR=runs/quick_phase2; RES=results/quick
  N0=2; N12=2; N3=2; N4=2; N5=4; NT=2; STEPS=300; E3_EXTRA=(--calib-episodes 1 --change-step 100)
  for c in 1 2; do
    python3 - "configs/retrain_phase$c.yaml" "runs/quick_phase$c.yaml" <<'EOF'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1]))
c['phase1_training'].update(total_timesteps=8000, rollout_steps=4000)
c['phase2_training'].update(num_eval_episodes=4, num_epochs=2)
yaml.safe_dump(c, open(sys.argv[2], 'w'))
EOF
  done
  C1=runs/quick_phase1.yaml; C2=runs/quick_phase2.yaml
else
  N0=40; N12=100; N3=40; N4=100; N5=200; NT=40; STEPS=2500; E3_EXTRA=()
fi

echo "== 0. pre-flight"
python3 -m pytest -q tests
python3 tools/check_physics_injection.py --track aut_tight --tire-model linear
python3 tools/check_physics_injection.py --track aut_tight --tire-model friction_circle

echo "== 1. Phase 1"
if [[ ! -f $P1DIR/final.pt ]]; then
  (cd src/f1tenth_research && python3 -u -m f1tenth_research.training.phase1_ppo_il \
     --config "$REPO/$C1" --device cpu --num_envs "$NPROC" \
     --log_dir "$REPO/$P1DIR" --checkpoint_dir "$REPO/$P1DIR" --resume)
fi
# Base policy = the checkpoint with the lowest closed-loop validation crash rate
# (tools/validate_checkpoints.py; ties go to the earliest). In Nov 2026 that was
# the DAgger checkpoint: PPO fine-tuning raised validation crashes 0.00 -> 0.26 by
# epoch 50, so the run was stopped there. Override with PHASE1_CKPT=<path>.
python3 tools/validate_checkpoints.py "$P1DIR" --every 50
P1=${PHASE1_CKPT:-$(python3 -c "
import json, sys
rows = [json.loads(l) for l in open('$P1DIR/validation.jsonl')]
print('$P1DIR/' + min(rows, key=lambda r: (r['mean_crash_rate'], r['epoch']))['checkpoint'])")}
echo "Phase 1 base policy: $P1"

echo "== 2. Phase 2"
if [[ ! -f $P2DIR/final.pt ]]; then
  python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint "$P1" \
     --config "$C2" --device cpu --num_envs "$NPROC" --log_dir "$P2DIR" --checkpoint_dir "$P2DIR"
fi
P2=$P2DIR/final.pt

run_suite() {  # $1 = tire model, $2 = output root, $3 = which experiments
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
  [[ -f $out/e0/run/summary.json ]] || \
    python3 experiments/e0_grip_gate.py -n "$N0" "${c[@]}" --out "$out/e0/run" > "$out.e0.log" 2>&1 &
  pids+=($!)
  for p in "${pids[@]}"; do wait "$p"; done
  [[ -f $out/e1_e2/run/summary.json ]] || python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/e1_e2/run"
  if [[ $which == all ]]; then
    pids=()
    [[ -f $out/e3/run/summary.json ]] || python3 experiments/e3_transient.py -n "$N3" "${c[@]}" "${E3_EXTRA[@]}" --out "$out/e3/run" > "$out.e3.log" 2>&1 & pids+=($!)
    [[ -f $out/e4/run/summary.json ]] || python3 experiments/e4_causal.py -n "$N4" "${c[@]}" --out "$out/e4/run" > "$out.e4.log" 2>&1 & pids+=($!)
    [[ -f $out/e5/run/summary.json ]] || python3 experiments/e5_signal.py -n "$N5" "${c[@]}" --out "$out/e5/run" > "$out.e5.log" 2>&1 & pids+=($!)
    for p in "${pids[@]}"; do wait "$p"; done
  fi
  python3 analysis/plot_results.py "$out" --out "$out/figures"
}

echo "== 3. experiments (linear tire)"
run_suite linear "$RES/linear" all
echo "== 4. tire robustness (friction-circle tire, same checkpoints)"
run_suite friction_circle "$RES/friction_circle" tire
echo "done: $RES"
