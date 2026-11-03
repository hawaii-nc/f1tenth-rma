#!/bin/bash
# Amendment 6 (Q): active grip probe + proprioceptive φ, on the P2 base policies
# (friction-circle tire), for training seeds 0, 1 and 2. Per seed: φ_Q training
# (oracle round + 3 on-policy rounds, as P2), E1/E2 (N = 100 per grip, Oracle / φ /
# Blind, all with the probe), E5 (N = 200), then the speed-matched control: Blind
# with the probe, capped at φ_Q's own mean speed at μ = 1.0 (rule of amendment 4).
# Resumable. tmux new -s probe 'bash tools/probe_suite.sh 2>&1 | tee runs/probe.log'
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
NPROC=${NPROC:-$(nproc --all)}
C=configs/retrain_phase2_fc_probe.yaml
X=(--tire-model friction_circle)
ROOT=results/retrain_nov2026/probe
SEEDS=${SEEDS:-0 1 2}

e12() {  # p1 p2 out extra-args...
  local p1=$1 p2=$2 out=$3; shift 3
  [[ -f $out/run/summary.json ]] && return 0
  mkdir -p "$out"; local pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n 100 --grips $g --phase1 "$p1" --phase2 "$p2" --config $C "${X[@]}" "$@" \
      --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
}

for s in $SEEDS; do
  if [[ $s == 0 ]]; then P1=runs/phase1_fc/final.pt; else P1=runs/phase1_fc_seed$s/final.pt; fi
  D=runs/phase2_fc_probe_seed$s; R=$ROOT/seed$s
  mkdir -p "$R"
  echo "== seed $s: phi_Q training ($(date -u +%H:%M))"
  if [[ ! -f $D/final.pt ]]; then
    TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint $P1 \
      --config $C --device cpu --num_envs "$NPROC" --seed $((12345 + s)) --log_dir $D --checkpoint_dir $D
  fi
  echo "== seed $s: E1/E2 ($(date -u +%H:%M))"
  e12 $P1 $D/final.pt $R/e1_e2
  [[ -f $R/e5/run/summary.json ]] || python3 experiments/e5_signal.py -n 200 --phase1 $P1 --phase2 $D/final.pt \
    --config $C "${X[@]}" --out $R/e5/run > $R/e5.log 2>&1 &
  CAP=$(python3 -c "
import json; s = json.load(open('$R/e1_e2/run/summary.json'))['summary']
print(round([r['mean_speed'] for r in s if r['controller'] == 'phi' and r['grip'] == 1.0][0], 2))")
  echo "== seed $s: speed-matched Blind, cap $CAP m/s ($(date -u +%H:%M))"
  e12 $P1 $D/final.pt $R/speed_matched/e1_e2 --controllers blind --speed-cap "$CAP"
  wait
  python3 tools/stats.py $R/e1_e2/run --out $R/stats.md
  python3 tools/speed_matched_test.py $R/e1_e2/run $R/speed_matched/e1_e2/run --out $R/speed_matched.md
done
python3 tools/provenance.py $ROOT
echo PROBE_SUITE_DONE
