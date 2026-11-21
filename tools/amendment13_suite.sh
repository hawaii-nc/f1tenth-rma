#!/bin/bash
# Amendment 13: (B) pessimistic grip margin on phi_DR + cautious start, no retraining;
# (T) phi_DR retrained with the cautious start in the on-policy rounds. Seeds 0-2. Resumable.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
NPROC=${NPROC:-$(nproc --all)}
ROOT=results/retrain_nov2026/real/amendment13
N=${N:-100}
C=configs/real_phase2_probe.yaml
e12() {  # p1 p2 grip out controllers...
  local p1=$1 p2=$2 g=$3 out=$4; shift 4
  [[ -f $out/summary.json ]] && return 0
  mkdir -p "$(dirname "$out")"
  python3 experiments/e1_e2_calibration.py -n "$N" --grips "$g" --n-boot 0 --controllers "$@" \
    --phase1 "$p1" --phase2 "$p2" --config $C --tire-model friction_circle --out "$out" > "$out.log" 2>&1
}
throttle() { while (( $(jobs -rp | wc -l) >= NPROC )); do sleep 5; done; }

echo "== arm B ($(date -u +%H:%M))"
for s in ${SEEDS:-0 1 2}; do
  for g in 0.4 0.6 1.0; do
    throttle
    e12 runs/real_phase1_seed$s/final.pt runs/real_phase2_slipdr_seed$s/final.pt $g $ROOT/bias/seed$s/g$g \
      oracle phi_cs blind_cs phi_b15_cs phi_b30_cs &
  done
done
wait
python3 tools/amendment13_stats.py --arm B --out $ROOT/bias_stats.md || true

for s in ${SEEDS:-0 1 2}; do
  P1=runs/real_phase1_seed$s/final.pt; D=runs/real_phase2_slipdr_cs_seed$s
  echo "== arm T seed $s: training ($(date -u +%H:%M))"
  if [[ ! -f $D/final.pt ]]; then
    TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint $P1 \
      --config configs/real_phase2_probe_slipdr_cs.yaml --device cpu --num_envs "$NPROC" --seed $((12345 + s)) \
      --log_dir $D --checkpoint_dir $D > $D.log 2>&1
  fi
  echo "== arm T seed $s: evaluation ($(date -u +%H:%M))"
  for g in 0.4 0.6 1.0; do
    e12 $P1 $D/final.pt $g $ROOT/train_cs/seed$s/g$g phi_cs &
  done
  mkdir -p $ROOT/train_cs/seed$s
  [[ -f $ROOT/train_cs/seed$s/e5/summary.json ]] || python3 experiments/e5_signal.py -n 200 --phase1 $P1 --phase2 $D/final.pt \
    --config $C --tire-model friction_circle --out $ROOT/train_cs/seed$s/e5 > $ROOT/train_cs/seed$s/e5.log 2>&1 &
  wait
  python3 tools/amendment13_stats.py --arm T --out $ROOT/train_cs_stats.md || true
done
python3 tools/provenance.py $ROOT
echo AMENDMENT13_DONE
