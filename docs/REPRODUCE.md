# Reproducing the work

This page covers the paper's pipeline (November 2026). The July 2026 recipe (PPO + IL with `configs/final_phase1_v42.yaml`, the `checkpoints/final/` models) is on the branch `archive/july-2026-pipeline`; its numbers are superseded (BUGS_AND_LESSONS.md).

## 0. Environment

Two routes. Every result in `results/retrain_nov2026/` was produced with the first (see any `provenance.json`).

**A. Current Python, simulator on `PYTHONPATH`** (used for all November results; Python 3.13, numpy 2.5, torch 2.15, numba 0.68):

```bash
pip install -r requirements-dev.txt numba "gym==0.26.2" pillow pyglet
git clone https://github.com/f1tenth/f1tenth_gym.git ../f1tenth_gym && git -C ../f1tenth_gym checkout 4fdb9c7
export PYTHONPATH=$PWD/../f1tenth_gym/gym:$PWD/src/f1tenth_research
python -m pytest -q tests          # 80 tests; without the simulator on PYTHONPATH one is skipped
```

**B. Docker image** (ROS 2 Foxy, Python 3.8, as on the car's Jetson):

```bash
docker build -t f1tenth-rma -f docker/Dockerfile .
docker run --rm -it -v $PWD:/f1tenth-rma f1tenth-rma
```

The tests alone need no simulator (`tests/fake_sim.py`); CI runs them that way.

## 1. Tracks

```bash
python tools/prepare_tracks.py     # 13 drivable *_tight tracks, each at its own scale (0.35–0.70)
```

Four maps are in `maps/`; the others are downloaded from f1tenth_racetracks. Maps are read from `$F1TENTH_MAPS_DIR` (default `maps/`).

## 2. Check that your setup reproduces a published number

Evaluation is deterministic: the same code, checkpoints and simulator commit give the same episodes. This reruns one published cell (φ_DR, seed 0, μ = 0.4; about 10 minutes on one core) and compares it with the committed result:

```bash
export OMP_NUM_THREADS=1
python experiments/e1_e2_calibration.py -n 100 --grips 0.4 --n-boot 0 \
    --phase1 runs/real_phase1_seed0/final.pt --phase2 runs/real_phase2_slipdr_seed0/final.pt \
    --config configs/real_phase2_probe.yaml --tire-model friction_circle --out /tmp/repro
python tools/compare_runs.py /tmp/repro results/retrain_nov2026/real/slipdr/seed0/nominal/e1_e2/run
```

Expected: crash counts Oracle 2, φ 41, Blind 86 of 100, and all 300 episodes identical (checked Nov 13, 2026).

## 3. Train

Each suite trains what it needs if the checkpoint is missing, then evaluates; all are resumable. Run them in tmux. With the committed `runs/` they skip training and only evaluate.

| Paper configuration | Script | Trains | Time on 4 cores |
|---|---|---|---|
| Original, P1, P2 (§IV-A) | `tools/retrain_all.sh`, `tools/remedies_suite.sh`, `tools/robustness_suite.sh` | base policy (DAgger) and φ, linear and friction-circle tires | DAgger ~30 min, φ 2–3 h, experiments ~3 h |
| Q: ideal sensors + probe | `tools/probe_suite.sh`, `tools/cap_sweep.sh`, `tools/speed_matched_seeds.sh` | φ_Q, seeds 0–2 | |
| R: car sensors, braking probe, racing expert | `tools/real_suite.sh`, `tools/real_robustness.sh` | base policy and φ_R, seeds 0–2 | |
| R with slip randomization (deployable) | `tools/slipdr_suite.sh` | φ_DR, seeds 0–2 | ~1.5 h per seed |
| Memory and probe-rate arms | `tools/amendment11_suite.sh` | two φ variants | |
| Cold start | `tools/amendment12_suite.sh` | nothing (evaluation only) | ~1.5 h |

`QUICK=1 bash tools/retrain_all.sh` is a minutes-long smoke run of every stage. Details and the checks to do before a long run: [RETRAINING.md](RETRAINING.md). Configs: `configs/real_*.yaml` (R), `configs/retrain_*.yaml` (original, P1, P2, Q).

## 4. Evaluate, figures, paper

```bash
python experiments/e1_e2_calibration.py -n 100 --phase1 <policy> --phase2 <phi> --config <config> --tire-model friction_circle
python experiments/e5_signal.py -n 200 ...        # grip R² of φ's estimate
python tools/stats.py <run dir> --out stats.md    # Wilson CIs, bootstrap, exact McNemar, Holm
python tools/make_figures.py                      # paper/figures/ from results/ only
cd paper/latex && pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Every experiment script takes `--phase1`, `--phase2`, `--config`, `-n`, `--tracks`, `--seed`, `--out`, `--tire-model`. Protocol: [EXPERIMENTS.md](EXPERIMENTS.md). Write the prediction into [PREREGISTRATION_NOV2026.md](PREREGISTRATION_NOV2026.md) and commit it before running anything new.

## 5. Deploy on the car (VADER: Jetson, L4T R35.4.1 = JetPack 5.1.2, ROS 2 Foxy)

PyTorch for the Jetson comes from NVIDIA's JetPack 5.1.x / Python 3.8 wheel (installed on VADER: torch 2.1.0). Full steps: `deploy/TA_INSTALL_CHECKLIST.md`.

```bash
# from your laptop
scp -r src/rma_deploy_pkg src/f1tenth_research <user>@vader:~/rma_deploy_ws/src/
ssh <user>@vader mkdir -p ~/rma_deploy_ws/runs
scp -r runs/real_phase1_seed0 runs/real_phase2_slipdr_seed0 <user>@vader:~/rma_deploy_ws/runs/
scp deploy/*.sh deploy/joy_manager.py <user>@vader:~/

# on the car
cd ~/rma_deploy_ws && colcon build --packages-select f1tenth_research rma_deploy_pkg
source install/local_setup.bash
ros2 launch f1tenth_unlv_veh stack_aeb_launch.py        # car stack (terminal 1)
~/start_rma_noadapt.sh                                   # non-adaptive baseline, probe on
~/start_rma.sh                                           # adaptive: policy + φ_DR, probe on
```

The node defaults match the car models: 100 Hz, braking probe of −1.0 m/s (`--probe 1` turns it on; the start scripts do). **The node has not run on hardware in this form.** Do Stage 1 of [REAL_CAR_PROBE_PLAN.md](REAL_CAR_PROBE_PLAN.md) first.

**Safety:** secure the car (wheels off the ground) for first tests. Hold R2 to engage; release R2, or hold L1, for manual override. The policy caps speed at 3.0 m/s. `--shield` adds the ACDA / grip-adaptive speed shield (off by default; it can only lower speed).

## 6. Real-car trials and analysis

```bash
source ~/trial_helpers.sh
new_material                       # fresh log for this tire condition
~/start_rma.sh &                   # node writes ~/rma_data.csv
start_trial; ...; end_trial cw 1 pass
finish_material electrical         # → rma_data_electrical.csv, rma_trial_log_electrical.csv
```

`joy_manager.py` logs TRIAL_START / PASS / FAIL from the controller buttons (Circle / Triangle / X).

Back on a laptop:

```bash
python analysis/real_car/tire_stats.py --data-dir ~/vader_logs \
    --conditions bare foil duct electrical --control bare
```

On-car logs are git-ignored; archive them separately.
