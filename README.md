# You Cannot See Grip Without Using It: Active Probing for Rapid Motor Adaptation in Autonomous Racing

Code, trained models and raw results for the workshop paper in [`paper/latex/main.pdf`](paper/latex/main.pdf).

Nathan Chong (University of Hawaiʻi at Mānoa) and Venkata Prashant Modekurthy (University of Nevada, Las Vegas). This work was done through the NSF REU Site in Smart Cities at UNLV (Award #2349616), summer and fall 2026.

New to the project? Start with [docs/HANDOFF.md](docs/HANDOFF.md).

## Overview

Rapid Motor Adaptation (RMA) infers hidden physical parameters, such as tire grip, from a robot's recent motion. We find that on the F1TENTH platform this does not work as usually trained. When the car's actions are kept independent of grip, half a second of motion history carries no information about grip (R² ≈ 0 for linear, friction-circle and brush tire models), because the car drives well inside its friction limit. Adaptation modules that appear to work are reading the expert's own driving or simply driving slowly; a non-adaptive car with a speed limit matches them.

A brief active probe fixes this. A 0.1 s speed pulse on straights asks the tires for more than low grip can deliver, and grip becomes readable (R² 0.89–0.93). With the probe, the adaptive controller tracks an oracle's speed at every grip level and beats any fixed speed limit at low grip. The result holds with the car's actual sensing (wheel-odometry speed, kinematic yaw rate, 40 Hz LiDAR) and a braking probe, and after randomizing the wheel-slip model in training.

All results are from simulation. The real-car test of the probe has not been run yet; the protocol is in [docs/REAL_CAR_PROBE_PLAN.md](docs/REAL_CAR_PROBE_PLAN.md). Every hypothesis and threshold was registered before its runs in [docs/PREREGISTRATION_NOV2026.md](docs/PREREGISTRATION_NOV2026.md), and failed checks are reported alongside the ones that passed.

## Results

Crash rate at grip μ = 0.4, 100 paired episodes per cell, three training seeds. "Matched Blind" is the non-adaptive policy with a speed limit set so that its measured speed equals the adaptive controller's.

| Configuration | Adaptive (φ) | Matched Blind | Oracle | Grip R² of φ |
|---|---|---|---|---|
| Ideal sensors, speed probe (Q) | 0.02–0.08 | 0.33–0.47 | 0.00–0.06 | 0.89–0.93 |
| Car sensors, braking probe, racing expert (R) | 0.28–0.39 | 0.84–0.86 | 0.00–0.09 | 0.84–0.87 |
| R with wheel-slip randomization and a cautious start | 0.18–0.27 | — | 0.00–0.09 | 0.79–0.84 |

Further results (slip-model robustness, held-out tracks, the memory, probe-rate and cold-start tests) are in [docs/RESULTS_NOV2026.md](docs/RESULTS_NOV2026.md). Each table there links to its raw data in `results/retrain_nov2026/`.

| Paper element | Data in `results/retrain_nov2026/` | Produced by |
|---|---|---|
| §IV-A, no grip information without excitation | see RESULTS §4 | `tools/phi_diagnostic.py` |
| §IV-A, standard RMA fails | `linear/`, `p2_friction_circle/`, `robustness_fc/` | `tools/retrain_all.sh`, `tools/remedies_suite.sh`, `tools/robustness_suite.sh` |
| Table I and Fig. 1 (left), configuration Q | `probe/seed{0,1,2}/` | `tools/probe_suite.sh` |
| Fig. 2, speed-limit frontier | `probe/seed0/cap_sweep_*`, `probe/seed*/speed_matched_measured/` | `tools/cap_sweep.sh`, `tools/speed_matched_test.py` |
| Fig. 1 (right), configuration R | `real/seed{0,1,2}/` | `tools/real_suite.sh` |
| Fig. 4, wheel-slip robustness | `real/robustness/slip_*`, `real/slipdr/` | `tools/real_robustness.sh`, `tools/slipdr_suite.sh` |
| Fig. 3, grip R² by configuration | `*/e5/` of the runs above | `experiments/e5_signal.py` |
| §V, memory and probe-rate tests | `real/amendment11/` | `tools/amendment11_suite.sh` |
| §V, cold start | `real/amendment12/` | `tools/amendment12_suite.sh` |
| Grip margin and retraining tests (not in the paper) | `real/amendment13/` | `tools/amendment13_suite.sh` |
| Real-car probe test, simulated prediction | `real/probe_test_sim/` | `tools/real_car/simulate_probe_trials.py` |
| §IV-E, July 2026 real-car pilot | trial logs on the lab machine | `analysis/real_car/tire_stats.py` |

Every run directory contains `episodes.csv`, `summary.json` and `provenance.json` (git commit, library versions, SHA-256 of the checkpoints). Statistics come from `tools/stats.py`: Wilson intervals, episode bootstrap, exact McNemar tests on paired episodes, and Holm correction.

## Requirements

```bash
pip install -r requirements-dev.txt numba "gym==0.26.2" pillow pyglet
git clone https://github.com/f1tenth/f1tenth_gym.git ../f1tenth_gym
git -C ../f1tenth_gym checkout 4fdb9c7
export PYTHONPATH=$PWD/../f1tenth_gym/gym:$PWD/src/f1tenth_research
python tools/prepare_tracks.py        # builds the 13 scaled tracks
python -m pytest -q tests             # 83 tests
```

A Docker image matching the car's Python 3.8 environment is in `docker/Dockerfile`. The tests run without the simulator using `tests/fake_sim.py`, which is how CI runs them.

## Training and evaluation

Each suite in `tools/` trains whatever checkpoint is missing, evaluates it, and resumes where it stopped; with the committed `runs/` it only evaluates. Training a base policy takes about 30 minutes and an adaptation module about 1.5 hours on a 4-core CPU. A single evaluation cell (100 paired episodes at one grip level):

```bash
python experiments/e1_e2_calibration.py -n 100 --grips 0.4 \
    --phase1 runs/real_phase1_seed0/final.pt --phase2 runs/real_phase2_slipdr_seed0/final.pt \
    --config configs/real_phase2_probe.yaml --tire-model friction_circle --out /tmp/check
python tools/compare_runs.py /tmp/check results/retrain_nov2026/real/slipdr/seed0/nominal/e1_e2/run
```

Evaluation is deterministic, so the second command should report all 300 episodes identical to the published run. Full instructions: [docs/REPRODUCE.md](docs/REPRODUCE.md) and [docs/RETRAINING.md](docs/RETRAINING.md). Figures: `python tools/make_figures.py`. Paper: `cd paper/latex && pdflatex main && bibtex main && pdflatex main && pdflatex main`.

## Trained models

All checkpoints the results cite are in `runs/` ([runs/README.md](runs/README.md) describes each one). For the car, use `runs/real_phase1_seedN/final.pt` (base policy) with `runs/real_phase2_slipdr_seedN/final.pt` (adaptation module), N = 0, 1 or 2. The ROS 2 node in `src/rma_deploy_pkg/` runs them at 100 Hz with the braking probe; see [docs/SIM_TO_REAL.md](docs/SIM_TO_REAL.md) and `deploy/`.

## Method

RMA ([Kumar et al., RSS 2021](https://arxiv.org/abs/2107.04034)) in two phases. In phase 1, a policy π(x, z) learns by DAgger from a grip-aware Pure Pursuit expert, with the true physics compressed into an 8-D vector z by an encoder. In phase 2, a 1-D CNN φ learns to predict z from the last 50 steps (0.5 s) of observations and actions; on the car, φ replaces the encoder. The policy sees 5 motion signals and 108 LiDAR ranges, with no map, pose or racing line. Simulation uses f1tenth_gym at 100 Hz with an added friction-circle tire model.

## Repository layout

```
paper/                    LaTeX source and PDF, figures, BibTeX, longer text version
results/retrain_nov2026/  raw results behind every number in the paper
runs/                     trained models (final.pt per run)
src/f1tenth_research/     environment, tire models, randomization, sensor model, probe,
                          DAgger and phase-2 training, metrics, evaluation harness
src/rma_deploy_pkg/       ROS 2 node for the car (100 Hz, probe, safety shield)
experiments/              evaluation scripts E0–E5
tools/                    experiment suites, figures, statistics, real-car test tools
configs/                  training and evaluation configs
docs/                     results, pre-registration, sim-to-real notes, test plans, hand-off
checkpoints/final/        July 2026 checkpoint used in the real-car pilot
analysis/, deploy/        real-car pilot analysis; scripts and install checklist for the car
docker/, tests/           container definition; test suite run by CI
```

## Earlier work

The July 2026 pipeline is on the branch `archive/july-2026-pipeline`, and the full record before the November reorganization is on `archive/full-record-nov2026`. The July poster figures (for example, 44% of the oracle gap closed) came from a pipeline with an untrained encoder and other bugs, described in [docs/BUGS_AND_LESSONS.md](docs/BUGS_AND_LESSONS.md); they should not be cited. The repositories [`research_ws`](https://github.com/hawaii-nc/research_ws) and [`f1tenth-vader-deployment`](https://github.com/hawaii-nc/f1tenth-vader-deployment) are superseded by this one.

## Citation

See [CITATION.cff](CITATION.cff). References are in [paper/references.bib](paper/references.bib).

## Acknowledgments

Thanks to Prof. Modekurthy for advising this work, to Ederic Oytas for help with the lab and the VADER car, and to the UNLV Smart Cities REU (NSF Award #2349616).

## License

The code is MIT-licensed ([LICENSE](LICENSE)). The AUT, ESP, GBR and MCO maps are from [BDEvan5/f1tenth_benchmarks](https://github.com/BDEvan5/f1tenth_benchmarks) (Apache-2.0). The other tracks come from [f1tenth/f1tenth_racetracks](https://github.com/f1tenth/f1tenth_racetracks) (GPL-3.0) and are downloaded by `tools/prepare_tracks.py` rather than stored here.
