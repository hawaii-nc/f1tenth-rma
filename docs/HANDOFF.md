# Hand-off notes

These notes are for the student continuing the experiments. Last updated November 20, 2026.

## Current state

The July 2026 pipeline had seven bugs (C16–C24 in [BUGS_AND_LESSONS.md](BUGS_AND_LESSONS.md)). With them fixed, passive grip adaptation turned out to be impossible in this simulator: below the friction limit, the car's motion carries no information about grip. A short active probe, a speed or braking pulse on straights, makes grip readable, and the adaptive controller then beats any fixed speed limit at low grip. The controller was retrained with the car's actual sensing (wheel odometry, no gyro, 40 Hz LiDAR) and a racing expert, and made robust to the unknown wheel-slip behaviour. The summary at the top of [RESULTS_NOV2026.md](RESULTS_NOV2026.md) is the best place to start.

| | |
|---|---|
| Paper | `paper/latex/main.pdf` (4 pages, IEEE format) and `paper/workshop_draft.md` (longer text version). Figures: `python tools/make_figures.py` |
| Pre-registration | Every experiment's prediction was committed before it ran ([PREREGISTRATION_NOV2026.md](PREREGISTRATION_NOV2026.md), amendments 1–13). Please keep doing this |
| Models for the car | `runs/real_phase1_seedN/final.pt` (policy) with `runs/real_phase2_slipdr_seedN/final.pt` (φ), N = 0, 1 or 2; see [runs/README.md](../runs/README.md) and [SIM_TO_REAL.md](SIM_TO_REAL.md) |
| Target venue | An IEEE IV 2027 workshop paper (advisor's recommendation, Oct 5). IV 2027 is June 15–18, 2027, in Perth; workshop papers are due Feb 1, 2027 ([call](https://ieee-iv.org/2027/contributions/call-for-workshop-and-tutorials-proposals/)). Workshops are announced after Dec 1, 2026 |

## Getting started

1. Read the summary of [RESULTS_NOV2026.md](RESULTS_NOV2026.md), then [SIM_TO_REAL.md](SIM_TO_REAL.md) and [REAL_CAR_PROBE_PLAN.md](REAL_CAR_PROBE_PLAN.md).
2. Install and run the tests: `pip install -r requirements-dev.txt && pytest -q tests`. There are 83 tests; one is skipped if f1tenth_gym is not on the path.
3. Set up the simulator as described in [REPRODUCE.md](REPRODUCE.md) (f1tenth_gym at commit 4fdb9c7, then `python tools/prepare_tracks.py`). Section 2 of that page reruns one published result as a check.
4. Run Stage 1 of the real-car plan, using [STAGE1_RUN_SHEET.md](STAGE1_RUN_SHEET.md) in the lab. It needs no learned policy and one session, and it answers the main open question: does the real car's wheel response to a braking pulse reveal grip, as the simulator assumes?
5. Then deploy the controller with `~/start_rma.sh` (or `ros2 launch rma_deploy_pkg veh_launch.py checkpoint:=... adaptation:=... probe:=1`). The node's defaults match the car models: 100 Hz, a −1.0 m/s braking probe, and the cautious start. It has not run on hardware in this form, so put the car on a stand first.
6. Ask Prof. Modekurthy for lab-machine access and Ederic Oytas for time with the car.

## Priorities before Feb 1, 2027

| # | Task | Reason |
|---|---|---|
| 1 | Stage 1 probe test on VADER ([REAL_CAR_PROBE_PLAN.md](REAL_CAR_PROBE_PLAN.md)) | Every probe result is from simulation; this checks the assumption the method rests on |
| 2 | Check whether VADER's VESC publishes IMU data (`ros2 topic list`) | An IMU would measure the probe directly (simulated peak deceleration 9.5 / 7.2 / 4.2 m/s² at grip 1.0 / 0.7 / 0.4) |
| 3 | Re-center the slip randomization on what Stage 1 measures and retrain φ (`tools/slipdr_suite.sh`, about 1.5 h per seed on 4 cores) | φ works best when the training slip model matches the car |
| 4 | Closed-loop trials on the car: π with φ and the probe against the non-adaptive policy, on the July tire wraps | This is the real-car result the paper is missing |
| 5 | The remaining gap at μ = 0.4 | See below |
| 6 | Choose the workshop; advisor review of the draft | |

On item 5: with the cautious start, φ crashes in 22% of episodes at μ = 0.4 against 4% for the oracle (pooled over seeds). A small pessimistic margin on φ's grip estimate brings this to 7%, at a cost of 0.03–0.11 m/s at full grip; its registered cost criterion failed narrowly, and it has not yet been compared with a fixed speed limit at equal speed (RESULTS §11). Longer memory, faster probing and retraining with the cautious start did not help (§9, §12). The next steps are that equal-speed comparison and a check of the margin under the other slip models.

## Not in this repository

Ask Nathan for these.

| Item | Location | Use |
|---|---|---|
| July lab training code | Lab training machine, `/research_ws/src/f1tenth_research/` | Comparing against the rebuilt parts listed in [RECONSTRUCTION.md](RECONSTRUCTION.md) |
| Raw E0–E5 results from July | Lab training machine | The reported numbers in the July RESULTS page (branch `archive/full-record-nov2026`) |
| 100-step φ checkpoint | Lab training machine | E3 window ablation |
| On-car logs (`rma_data_*.csv`, `rma_trial_log_*.csv`) | VADER home directory | Re-deriving the real-car table with `analysis/real_car/tire_stats.py` |
| Poster (PDF and slides) | Nathan's Google Drive | Figures and wording |
| IEEE-format draft sent to the advisor on Sep 20, 2026 | Nathan's email | Earlier version of the paper |
| Full methodology notes and reward history | Nathan's Google Drive | Condensed in [EXPERIMENTS.md](EXPERIMENTS.md); the reward history is on `archive/full-record-nov2026` |

## Constraints

- φ never sees map-specific inputs: no racing line, pose or waypoints. The policy observes 5 motion signals and 108 LiDAR ranges; φ sees observations and actions.
- The raceline files' `psi` column is 90° off. Compute headings with `arctan2`.
- Do not use gymnasium's `AsyncVectorEnv` with f110_gym in Docker. Use `training/env_pool.py` with `OMP_NUM_THREADS=1`; default PyTorch threading made parallel runs about 60 times slower.
- f110_gym keeps one map per process (bug C22). Keep the scan-simulator snapshot logic in `envs/real_env.py`.
- After any change to the deployment node or the environment, `tests/test_node_sim_consistency.py` must still pass.
- Do not commit per-epoch checkpoints; only curated ones in `runs/` and `checkpoints/`.
- f110_gym's stock tire never saturates, so it does not penalize speed. Use `tire_model: friction_circle` where that matters ([SIM_FIDELITY.md](SIM_FIDELITY.md)).
- Run anything longer than about 10 minutes in tmux. On a cloud container, a restart will still kill it; the suites resume from their last finished step.
- Before a long training run, check the sign of each reward term at small scale (`eval/sanity_check_rollout.py`) and that expert actions are being produced (`tests/test_training_smoke.py`).
- On the car, start with the wheels off the ground. Hold R2 to engage; release R2 or hold L1 to take manual control.

## Working habits that helped

- Judge driving by crash rate and centerline deviation, not by reward totals.
- Write the prediction into the pre-registration and commit it before running an experiment.
- Report failed checks in the results with the same prominence as passing ones.

## People and access

- Advisor: Prof. Venkata Prashant Modekurthy (UNLV Computer Science). He wants another student to be able to run the experiments from this repository.
- Lab and hardware support: Ederic Oytas, TBE B150. He handles software installs on VADER (it has no internet access on campus) and can help with scp, slam_toolbox and the F1TENTH particle filter.
- Lab machines: the training machine (Docker and noVNC) and the Dell in TBE B150. Leave a note when training is running, and switch the power strip off otherwise.
- Hardware: a Jetson Orin AGX was ordered in July in place of the Orin NX (12-week lead time). The power board (AE170_PDU_02.04, 19 V at 4 A, 76 W) was checked against the Orin NX's 10–25 W; it needs to be checked against the AGX's power modes before the swap.

## If you have one week

Run Stage 1 on the car and analyze it with `tools/real_car/analyze_probe_trials.py`, then compare with the simulated prediction in `results/retrain_nov2026/real/probe_test_sim/analysis.md`. Whichever way it comes out, the result decides the next step and belongs in the paper.
