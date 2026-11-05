#!/bin/bash
# Amendment 11: memory (M) and probe-rate (F) arms for the mu-0.4 gap; robustness of phi_DR. Seed 0. Resumable.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
NPROC=${NPROC:-$(nproc --all)}
X=(--tire-model friction_circle)
P1=runs/real_phase1_seed0/final.pt; PDR=runs/real_phase2_slipdr_seed0/final.pt
ROOT=results/retrain_nov2026/real/amendment11; mkdir -p $ROOT
HOLD=(mco_tight silverstone_tight budapest_tight)
e12() {  # p1 p2 config out grips extra...
  local p1=$1 p2=$2 c=$3 out=$4 grips=$5; shift 5
  [[ -f $out/run/summary.json ]] && return 0
  mkdir -p "$out"; local pids=()
  for g in $grips; do
    python3 experiments/e1_e2_calibration.py -n 100 --grips $g --phase1 "$p1" --phase2 "$p2" --config "$c" "${X[@]}" "$@" \
      --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
}
train_phi() {  # p1 config dir
  [[ -f $3/final.pt ]] && return 0
  TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint "$1" \
    --config "$2" --device cpu --num_envs "$NPROC" --seed 12345 --log_dir "$3" --checkpoint_dir "$3"
}
echo "== A1-DR probe off + A3-DR grip step ($(date -u +%H:%M))"
R=$ROOT/robustness; mkdir -p $R
[[ -f $R/probe_off_e5/run/summary.json ]] || python3 experiments/e5_signal.py -n 200 --phase1 $P1 --phase2 $PDR \
  --config configs/real_eval_slipdr_probe_off.yaml "${X[@]}" --out $R/probe_off_e5/run > $R/probe_off_e5.log 2>&1 &
[[ -f $R/e3/run/summary.json ]] || python3 experiments/e3_transient.py -n 40 --phase1 $P1 --phase2 $PDR \
  --config configs/real_phase2_probe_slipdr.yaml "${X[@]}" --out $R/e3/run > $R/e3.log 2>&1 &
wait
grep "R²" $R/probe_off_e5.log || true; grep -i settle $R/e3.log | tail -1 || true
for arm in mem2s probe25; do
  echo "== arm $arm: training ($(date -u +%H:%M))"
  D=runs/real_phase2_slipdr_${arm}_seed0
  train_phi $P1 configs/real_phase2_slipdr_$arm.yaml $D
  NONE=configs/real_eval_slip_none.yaml; [[ $arm == probe25 ]] && NONE=configs/real_eval_slip_none_probe25.yaml
  echo "== arm $arm: evaluation ($(date -u +%H:%M))"
  e12 $P1 $D/final.pt configs/real_phase2_slipdr_$arm.yaml $ROOT/$arm/default/e1_e2 "1.0 0.6 0.4" &
  e12 $P1 $D/final.pt $NONE $ROOT/$arm/slip_none/e1_e2 "0.6 0.4" &
  wait
  for v in default slip_none; do
    python3 tools/stats.py $ROOT/$arm/$v/e1_e2/run --out $ROOT/$arm/$v/stats.md > /dev/null
    echo "-- $arm $v"; grep -E "^\| (phi|blind|oracle) \| (1.0|0.6|0.4)" $ROOT/$arm/$v/stats.md || true
  done
done
echo "== A2-DR held-out ($(date -u +%H:%M))"
DH=runs/real_phase2_slipdr_holdout
train_phi runs/real_phase1_holdout/final.pt configs/real_phase2_probe_slipdr_holdout.yaml $DH
e12 runs/real_phase1_holdout/final.pt $DH/final.pt configs/real_phase2_probe_slipdr.yaml $R/holdout_model/e1_e2 "1.0 0.8 0.6 0.4" --tracks "${HOLD[@]}"
e12 $P1 $PDR configs/real_phase2_probe_slipdr.yaml $R/main_model_on_holdout/e1_e2 "1.0 0.8 0.6 0.4" --tracks "${HOLD[@]}"
python3 tools/stats.py $R/holdout_model/e1_e2/run $R/main_model_on_holdout/e1_e2/run --labels holdout_model main_model --out $R/holdout_stats.md > /dev/null
grep -E "^### |^\| 0\.4" $R/holdout_stats.md || true
python3 tools/provenance.py $ROOT
echo AMENDMENT11_DONE
