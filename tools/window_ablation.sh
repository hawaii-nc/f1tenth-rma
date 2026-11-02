#!/bin/bash
# Amendment 4 (W): phi with a 200-step history on the P2 base policy, plus the speed-matched control.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
NPROC=${NPROC:-$(nproc --all)}
R=results/retrain_nov2026/window_k200
P1=runs/phase1_fc/final.pt; P2=runs/phase2_fc_k200/final.pt
C=configs/retrain_phase2_fc_onpolicy_k200.yaml
X=(--tire-model friction_circle)
mkdir -p $R
if [[ ! -f $P2 ]]; then
  TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint $P1 \
    --config $C --device cpu --num_envs "$NPROC" --log_dir runs/phase2_fc_k200 --checkpoint_dir runs/phase2_fc_k200
fi
e12() {  # out extra-args...
  local out=$1; shift
  [[ -f $out/run/summary.json ]] && return 0
  mkdir -p "$out"; local pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n 100 --grips $g --phase1 $P1 --phase2 $P2 --config $C "${X[@]}" "$@" \
      --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
}
e12 $R/e1_e2
pids=()
[[ -f $R/e5/run/summary.json ]] || { python3 experiments/e5_signal.py -n 200 --phase1 $P1 --phase2 $P2 --config $C "${X[@]}" --out $R/e5/run > $R/e5.log 2>&1 & pids+=($!); }
[[ -f $R/e3/run/summary.json ]] || { python3 experiments/e3_transient.py -n 40 --phase1 $P1 --phase2 $P2 --config $C "${X[@]}" --out $R/e3/run > $R/e3.log 2>&1 & pids+=($!); }
for p in "${pids[@]}"; do wait "$p"; done
# Caps fixed by rule (amendment 4): phi_k200's own mean speed at mu = 1.0 and at mu = 0.4
read CAP_HI CAP_LO < <(python3 -c "
import json; s = json.load(open('$R/e1_e2/run/summary.json'))['summary']
v = {r['grip']: r['mean_speed'] for r in s if r['controller'] == 'phi'}
print(round(v[1.0], 2), round(v[0.4], 2))")
echo "speed-matched caps: $CAP_HI (phi at mu=1.0), $CAP_LO (phi at mu=0.4)"
e12 $R/speed_matched_hi/e1_e2 --controllers blind --speed-cap $CAP_HI
e12 $R/speed_matched_lo/e1_e2 --controllers blind --speed-cap $CAP_LO
python3 tools/stats.py $R/e1_e2/run --out $R/stats.md
echo WINDOW_ABLATION_DONE
