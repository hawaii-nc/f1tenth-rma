#!/bin/bash
# Amendment 9: robustness of configuration R (seed-0 models). Resumable.
#   S     slip-model sensitivity: 4 alternative wheel-slip models, mu 0.6 and 0.4
#   A1-R  probe off;  A3-R  E3 grip step;  A2-R  held-out tracks (retrains Phase 1 + phi)
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
NPROC=${NPROC:-$(nproc --all)}
X=(--tire-model friction_circle)
P1=runs/real_phase1_seed0/final.pt; P2=runs/real_phase2_seed0/final.pt
R=results/retrain_nov2026/real/robustness; mkdir -p $R
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
echo "== S: slip-model sensitivity ($(date -u +%H:%M))"
for v in slip_slow slip_fast slip_longrelax slip_none; do
  e12 $P1 $P2 configs/real_eval_$v.yaml $R/$v/e1_e2 "0.6 0.4" &
  sleep 2
  [[ $v == slip_fast || $v == slip_none ]] && wait   # two variants (4 processes) at a time
done
wait
for v in slip_slow slip_fast slip_longrelax slip_none; do
  python3 tools/stats.py $R/$v/e1_e2/run --out $R/$v/stats.md > /dev/null
  echo "-- $v"; grep -E "^\| (0.6|0.4) \|" $R/$v/stats.md | tail -2
done
echo "== A1-R probe off ($(date -u +%H:%M))"
e12 $P1 $P2 configs/real_eval_probe_off.yaml $R/probe_off/e1_e2 "1.0 0.8 0.6 0.4"
[[ -f $R/probe_off/e5/run/summary.json ]] || python3 experiments/e5_signal.py -n 200 --phase1 $P1 --phase2 $P2 \
  --config configs/real_eval_probe_off.yaml "${X[@]}" --out $R/probe_off/e5/run > $R/probe_off.e5.log 2>&1
python3 tools/stats.py $R/probe_off/e1_e2/run --out $R/probe_off/stats.md > /dev/null
grep "R²" $R/probe_off.e5.log || true
echo "== A3-R E3 ($(date -u +%H:%M))"
[[ -f $R/e3/run/summary.json ]] || python3 experiments/e3_transient.py -n 40 --phase1 $P1 --phase2 $P2 \
  --config configs/real_phase2_probe.yaml "${X[@]}" --out $R/e3/run > $R/e3.log 2>&1
grep -i "settle" $R/e3.log | tail -1 || true
echo "== A2-R held-out tracks ($(date -u +%H:%M))"
D1=runs/real_phase1_holdout; D2=runs/real_phase2_holdout
if [[ ! -f $D1/final.pt ]]; then
  python3 -u -m f1tenth_research.training.phase1_ppo_il --config configs/real_phase1_holdout.yaml --device cpu \
    --num_envs "$NPROC" --seed 0 --total_timesteps 0 --log_dir $D1 --checkpoint_dir $D1
  python3 tools/validate_checkpoints.py $D1 --config configs/real_phase2_probe.yaml || true
fi
if [[ ! -f $D2/final.pt ]]; then
  TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint $D1/final.pt \
    --config configs/real_phase2_probe_holdout.yaml --device cpu --num_envs "$NPROC" --seed 12345 --log_dir $D2 --checkpoint_dir $D2
fi
e12 $D1/final.pt $D2/final.pt configs/real_phase2_probe.yaml $R/holdout_model/e1_e2 "1.0 0.8 0.6 0.4" --tracks "${HOLD[@]}"
e12 $P1 $P2 configs/real_phase2_probe.yaml $R/main_model_on_holdout/e1_e2 "1.0 0.8 0.6 0.4" --tracks "${HOLD[@]}"
python3 tools/stats.py $R/holdout_model/e1_e2/run $R/main_model_on_holdout/e1_e2/run --labels holdout_model main_model --out $R/holdout_stats.md > /dev/null
python3 tools/provenance.py $R
echo REAL_ROBUSTNESS_DONE
