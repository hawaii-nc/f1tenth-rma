#!/bin/bash
# Retrain φ on the fixed pipeline, then re-run the experiments with the new φ
# and the July φ side by side (HANDOFF.md priority items 1–4).
#
# Run on the lab machine, inside the Docker image, inside tmux:
#   mkdir -p runs && tmux new -s retrain 'bash tools/retrain_fixed.sh 2>&1 | tee runs/retrain_fixed.log'
#
# Options (environment variables):
#   TIRE_MODEL=friction_circle   saturating-tire variant (docs/SIM_FIDELITY.md); default linear
#   SKIP_TRAIN=1 PHI=<path>      skip retraining and evaluate an existing φ
#   QUICK=1                      tiny sample sizes, to check the script end to end first (~minutes)
#
# Output: runs/phase2_<tag>/{latest,final}.pt, results/<tag>/{new,old}/<exp>/<run>/,
#         figures in results/<tag>/{new,old}/figures/.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src/f1tenth_research${PYTHONPATH:+:$PYTHONPATH}"

TIRE=${TIRE_MODEL:-linear}
TAG=${TAG:-fixed_${TIRE}_$(date +%Y%m%d)}
P1=checkpoints/final/phase1_v42.pt
OLD_PHI=checkpoints/final/phase2_crashtol_clean.pt
CFG=configs/final_phase2_crashtol.yaml
RUN=runs/phase2_$TAG
RES=results/$TAG

if [[ "${QUICK:-0}" == 1 ]]; then
  N0=2; N12=2; N3=2; N4=2; N5=4; STEPS=300; E3_EXTRA=(--calib-episodes 1 --change-step 100)
  QCFG=$(mktemp --suffix=.yaml)
  python3 - "$CFG" "$QCFG" <<'EOF'
import sys, yaml
cfg = yaml.safe_load(open(sys.argv[1]))
cfg['phase2_training'].update(num_eval_episodes=3, num_epochs=2)
yaml.safe_dump(cfg, open(sys.argv[2], 'w'))
EOF
  CFG=$QCFG
else
  N0=40; N12=100; N3=40; N4=100; N5=200; STEPS=2500; E3_EXTRA=()
fi
mkdir -p "$RUN" "$RES"
echo "tag=$TAG tire_model=$TIRE config=$CFG"

echo "== 0. pre-flight: tests + μ reaches the real simulator"
python3 -m pytest -q tests
python3 tools/check_physics_injection.py --track aut_tight --tire-model "$TIRE"

if [[ "${SKIP_TRAIN:-0}" == 1 ]]; then
  NEW_PHI=${PHI:?set PHI=<path to φ checkpoint> with SKIP_TRAIN=1}
else
  echo "== 1. retrain φ against $P1"
  python3 -u -m f1tenth_research.training.phase2_adaptation \
      --phase1_checkpoint "$P1" --config "$CFG" --tire_model "$TIRE" \
      --log_dir "$RUN" --checkpoint_dir "$RUN"
  NEW_PHI=$RUN/final.pt
fi

echo "== 2. experiments: new φ ($NEW_PHI) vs July φ ($OLD_PHI)"
common=(--tire-model "$TIRE" --max-steps "$STEPS" --phase1 "$P1")
for label in new old; do
  if [[ $label == new ]]; then phi=$NEW_PHI; else phi=$OLD_PHI; fi
  out=$RES/$label
  python3 experiments/e1_e2_calibration.py -n $N12 --phase2 "$phi" "${common[@]}" --out "$out/e1_e2/run"
  python3 experiments/e4_causal.py         -n $N4  --phase2 "$phi" "${common[@]}" --out "$out/e4/run"
  python3 experiments/e5_signal.py         -n $N5  --phase2 "$phi" "${common[@]}" --out "$out/e5/run"
  python3 experiments/e3_transient.py      -n $N3  --phase2 "$phi" "${common[@]}" "${E3_EXTRA[@]}" --out "$out/e3/run"
done
# E0 tests the Blind controller only (no φ), so it runs once.
python3 experiments/e0_grip_gate.py -n $N0 "${common[@]}" --out "$RES/new/e0/run"
cp -r "$RES/new/e0" "$RES/old/e0"

for label in new old; do
  python3 analysis/plot_results.py "$RES/$label" --out "$RES/$label/figures"
done
echo "done: results in $RES (compare new/ vs old/)"
