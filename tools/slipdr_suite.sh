#!/bin/bash
# Amendment 10 (DR): phi retrained with a randomized wheel-slip model, seeds 0-2; evaluated under
# the nominal slip model and the 4 amendment-9 variants. Waits for tools/real_robustness.sh. Resumable.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
NPROC=${NPROC:-$(nproc --all)}
while tmux has-session -t =realrob 2>/dev/null; do sleep 60; done
X=(--tire-model friction_circle)
ROOT=results/retrain_nov2026/real/slipdr
e12() {  # p1 p2 config out
  local out=$4
  [[ -f $out/run/summary.json ]] && return 0
  mkdir -p "$out"; local pids=()
  for g in 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n 100 --grips $g --phase1 "$1" --phase2 "$2" --config "$3" "${X[@]}" \
      --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
}
for s in ${SEEDS:-0 1 2}; do
  P1=runs/real_phase1_seed$s/final.pt; D=runs/real_phase2_slipdr_seed$s; R=$ROOT/seed$s
  mkdir -p $R
  echo "== seed $s: phi_DR training ($(date -u +%H:%M))"
  if [[ ! -f $D/final.pt ]]; then
    TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint $P1 \
      --config configs/real_phase2_probe_slipdr.yaml --device cpu --num_envs "$NPROC" --seed $((12345 + s)) --log_dir $D --checkpoint_dir $D
  fi
  echo "== seed $s: evaluation ($(date -u +%H:%M))"
  e12 $P1 $D/final.pt configs/real_phase2_probe.yaml $R/nominal/e1_e2 &
  e12 $P1 $D/final.pt configs/real_eval_slip_none.yaml $R/slip_none/e1_e2 &
  wait
  e12 $P1 $D/final.pt configs/real_eval_slip_slow.yaml $R/slip_slow/e1_e2 &
  e12 $P1 $D/final.pt configs/real_eval_slip_fast.yaml $R/slip_fast/e1_e2 &
  wait
  e12 $P1 $D/final.pt configs/real_eval_slip_longrelax.yaml $R/slip_longrelax/e1_e2 &
  for v in nominal slip_none; do
    c=configs/real_phase2_probe.yaml; [[ $v == slip_none ]] && c=configs/real_eval_slip_none.yaml
    [[ -f $R/$v/e5/run/summary.json ]] || python3 experiments/e5_signal.py -n 200 --phase1 $P1 --phase2 $D/final.pt \
      --config $c "${X[@]}" --out $R/$v/e5/run > $R/$v.e5.log 2>&1 &
  done
  wait
  for v in nominal slip_slow slip_fast slip_longrelax slip_none; do
    python3 tools/stats.py $R/$v/e1_e2/run --out $R/$v/stats.md > /dev/null
    echo "-- seed $s $v"; grep -E "^\| (0.6|0.4) \|" $R/$v/stats.md | tail -2
  done
  grep "R²" $R/nominal.e5.log $R/slip_none.e5.log || true
done
python3 tools/provenance.py $ROOT
echo SLIPDR_DONE
