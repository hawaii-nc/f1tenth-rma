#!/bin/bash
# Amendment 7: robustness of the probe arm (Q). Waits for the Q suite and the cap sweep. Resumable.
#   A1 probe-off ablation (seed 0 phi_Q, every controller without the probe): E1/E2, E5
#   A2 held-out tracks: phi_Q trained on the P2 held-out base policy without mco/silverstone/budapest,
#      E1/E2 on those 3 tracks (with the probe), plus the seed-0 main phi_Q on the same episodes
#   A3 E3 transient (grip 1.0 -> 0.4 mid-episode) for seed 0 phi_Q, with the probe
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
NPROC=${NPROC:-$(nproc --all)}
while tmux has-session -t =probe 2>/dev/null || tmux has-session -t =capsweep 2>/dev/null; do sleep 60; done
X=(--tire-model friction_circle)
CQ=configs/retrain_phase2_fc_probe.yaml; CQH=configs/retrain_phase2_fc_probe_holdout.yaml
COFF=configs/retrain_phase2_fc_onpolicy.yaml   # same environment, no probe
P1=runs/phase1_fc/final.pt; P2=runs/phase2_fc_probe_seed0/final.pt
R=results/retrain_nov2026/probe/robustness; mkdir -p $R
HOLD=(mco_tight silverstone_tight budapest_tight)
e12() {  # p1 p2 config out extra...
  local p1=$1 p2=$2 c=$3 out=$4; shift 4
  [[ -f $out/run/summary.json ]] && return 0
  mkdir -p "$out"; local pids=()
  for g in 1.0 0.8 0.6 0.4; do
    python3 experiments/e1_e2_calibration.py -n 100 --grips $g --phase1 "$p1" --phase2 "$p2" --config "$c" "${X[@]}" "$@" \
      --out "$out/_shards/g$g" > "$out.g$g.log" 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  python3 tools/merge_e1_e2.py "$out"/_shards/g* --out "$out/run"
}
echo "== A1 probe off ($(date -u +%H:%M))"
e12 $P1 $P2 $COFF $R/probe_off/e1_e2
[[ -f $R/probe_off/e5/run/summary.json ]] || python3 experiments/e5_signal.py -n 200 --phase1 $P1 --phase2 $P2 --config $COFF "${X[@]}" --out $R/probe_off/e5/run > $R/probe_off.e5.log 2>&1
python3 tools/stats.py $R/probe_off/e1_e2/run --out $R/probe_off/stats.md
echo "== A3 E3 transient ($(date -u +%H:%M))"
[[ -f $R/e3/run/summary.json ]] || python3 experiments/e3_transient.py -n 40 --phase1 $P1 --phase2 $P2 --config $CQ "${X[@]}" --out $R/e3/run > $R/e3.log 2>&1
grep -i "settle\|median\|PASS\|FAIL" $R/e3.log | tail -3 || true
echo "== A2 held-out tracks ($(date -u +%H:%M))"
D=runs/phase2_fc_probe_holdout
if [[ ! -f $D/final.pt ]]; then
  TORCH_THREADS=$NPROC python3 -u -m f1tenth_research.training.phase2_adaptation --phase1_checkpoint runs/phase1_fc_holdout/final.pt \
    --config $CQH --device cpu --num_envs "$NPROC" --seed 12345 --log_dir $D --checkpoint_dir $D
fi
e12 runs/phase1_fc_holdout/final.pt $D/final.pt $CQ $R/holdout_model/e1_e2 --tracks "${HOLD[@]}"
e12 $P1 $P2 $CQ $R/main_model_on_holdout/e1_e2 --tracks "${HOLD[@]}"
python3 tools/stats.py $R/holdout_model/e1_e2/run $R/main_model_on_holdout/e1_e2/run --labels holdout_model main_model --out $R/holdout_stats.md
python3 tools/provenance.py $R
echo PROBE_ROBUSTNESS_DONE
