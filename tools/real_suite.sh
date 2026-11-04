#!/bin/bash
# Amendment 8 (R): sim-to-real configuration - car sensors, probe, racing expert. Seeds 0-2.
# Resumable. tmux new -s real 'bash tools/real_suite.sh 2>&1 | tee runs/real.log'
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
NPROC=${NPROC:-$(nproc --all)}
C1=configs/real_phase1.yaml; C2=configs/real_phase2_probe.yaml
X=(--tire-model friction_circle)
ROOT=results/retrain_nov2026/real
SEEDS=${SEEDS:-0 1 2}
e12() {  # p1 p2 out extra-args...
  local p1=$1 p2=$2 out=$3; shift 3
  [[ -f $out/run/summary.json ]] && return 0
  mkdir -p "$out"; local pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n 100 --grips $g --phase1 "$p1" --phase2 "$p2" --config $C2 "${X[@]}" "$@" \
      --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
}
speed() { python3 -c "
import json; s = json.load(open('$1/run/summary.json'))['summary']
print([r['mean_speed'] for r in s if r['controller'] == '$2' and r['grip'] == 1.0][0])"; }
for s in $SEEDS; do
  P1D=runs/real_phase1_seed$s; P2D=runs/real_phase2_seed$s; R=$ROOT/seed$s
  mkdir -p $R
  echo "== seed $s: Phase 1 ($(date -u +%H:%M))"
  if [[ ! -f $P1D/final.pt ]]; then
    python3 -u -m f1tenth_research.training.phase1_ppo_il --config $C1 --device cpu --num_envs "$NPROC" --seed $s \
      --total_timesteps 0 --log_dir $P1D --checkpoint_dir $P1D
    python3 tools/validate_checkpoints.py $P1D --config $C2 || true
  fi
  echo "== seed $s: Phase 2 ($(date -u +%H:%M))"
  if [[ ! -f $P2D/final.pt ]]; then
    TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint $P1D/final.pt \
      --config $C2 --device cpu --num_envs "$NPROC" --seed $((12345 + s)) --log_dir $P2D --checkpoint_dir $P2D
  fi
  echo "== seed $s: E1/E2 + E5 ($(date -u +%H:%M))"
  e12 $P1D/final.pt $P2D/final.pt $R/e1_e2
  [[ -f $R/e5/run/summary.json ]] || python3 experiments/e5_signal.py -n 200 --phase1 $P1D/final.pt --phase2 $P2D/final.pt \
    --config $C2 "${X[@]}" --out $R/e5/run > $R/e5.log 2>&1 &
  CAP=$(python3 -c "print(round($(speed $R/e1_e2 phi), 2))")
  echo "== seed $s: speed-matched Blind, cap $CAP ($(date -u +%H:%M))"
  e12 $P1D/final.pt $P2D/final.pt $R/speed_matched/e1_e2 --controllers blind --speed-cap "$CAP"
  CAP2=$(python3 -c "print(round($(speed $R/e1_e2 phi) - ($(speed $R/speed_matched/e1_e2 blind) - $(speed $R/e1_e2 phi)), 2))")
  echo "== seed $s: measured-speed-matched Blind, cap $CAP2"
  e12 $P1D/final.pt $P2D/final.pt $R/speed_matched_measured/e1_e2 --controllers blind --speed-cap "$CAP2"
  wait
  python3 tools/stats.py $R/e1_e2/run --out $R/stats.md
  python3 tools/speed_matched_test.py $R/e1_e2/run $R/speed_matched_measured/e1_e2/run --out $R/speed_matched_measured.md
  grep "R²" $R/e5.log || true
done
python3 tools/provenance.py $ROOT
echo REAL_SUITE_DONE
