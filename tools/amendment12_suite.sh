#!/bin/bash
# Amendment 12: cold start. phi_DR with and without a cautious start (no retraining), seeds 0-2,
# mu 1.0 / 0.6 / 0.4, N = 100 paired episodes, five controllers on the same episodes. Resumable.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
NPROC=${NPROC:-$(nproc --all)}
ROOT=results/retrain_nov2026/real/amendment12
N=${N:-100}
jobs_running() { jobs -rp | wc -l; }
for s in ${SEEDS:-0 1 2}; do
  for g in ${GRIPS:-0.4 0.6 1.0}; do
    out=$ROOT/seed$s/g$g
    [[ -f $out/summary.json ]] && continue
    mkdir -p "$ROOT/seed$s"
    while (( $(jobs_running) >= NPROC )); do sleep 5; done
    python3 experiments/e1_e2_calibration.py -n "$N" --grips "$g" --n-boot 0 \
      --controllers oracle phi blind phi_cs blind_cs \
      --phase1 runs/real_phase1_seed$s/final.pt --phase2 runs/real_phase2_slipdr_seed$s/final.pt \
      --config configs/real_phase2_probe.yaml --tire-model friction_circle \
      --out "$out" > "$ROOT/seed$s/g$g.log" 2>&1 &
  done
done
wait
python3 tools/provenance.py $ROOT
python3 tools/cold_start_stats.py --out $ROOT/stats.md
echo AMENDMENT12_DONE
