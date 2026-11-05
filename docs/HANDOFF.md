# Hand-off: continuing the project

For the student taking over the experiments, and for Nathan when he picks this back up.

## Where things stand (November 5, 2026)

All work for the paper is on `main`; earlier work is on the branches `archive/july-2026-pipeline` and `archive/full-record-nov2026` (README, Archive). In one paragraph: the July pipeline had seven bugs (C16–C24 in [BUGS_AND_LESSONS.md](BUGS_AND_LESSONS.md)). Once fixed, passive grip adaptation turned out to be **impossible in this simulator**: the car's motion carries no grip information below the limit. A short **active probe** (a speed or braking pulse on straights) fixes that, and the adaptive controller then beats any fixed speed limit at low grip. It was retrained with realistic car sensing (wheel odometry, no gyro, 40 Hz LiDAR) and a racing expert, and made robust to the unknown wheel-slip behaviour. Start with the **"Read this first"** section of [RESULTS_NOV2026.md](RESULTS_NOV2026.md).

- **Paper:** `paper/latex/main.pdf` (4 pages, IEEE format, compiled) and `paper/workshop_draft.md` (longer text version). Figures: `python tools/make_figures.py`.
- **Pre-registration:** every experiment's prediction was committed before it ran ([PREREGISTRATION_NOV2026.md](PREREGISTRATION_NOV2026.md), amendments 1–11). Keep doing this.
- **Models for the car:** `runs/real_phase1_seedN/final.pt` (policy) + `runs/real_phase2_slipdr_seedN/final.pt` (φ), N = 0, 1 or 2. See [runs/README.md](../runs/README.md) and [SIM_TO_REAL.md](SIM_TO_REAL.md).
- **Target venue:** an IEEE IV 2027 **workshop** paper (advisor's recommendation, Oct 5 2026). IV 2027 runs **June 15–18, 2027, in Perth**; workshop papers are due **Feb 1, 2027** ([call](https://ieee-iv.org/2027/contributions/call-for-workshop-and-tutorials-proposals/)). Workshops are announced after Dec 1, 2026.

## Day one (November 2026 onward)

1. Read the "Read this first" section of [RESULTS_NOV2026.md](RESULTS_NOV2026.md), then [SIM_TO_REAL.md](SIM_TO_REAL.md) and [REAL_CAR_PROBE_PLAN.md](REAL_CAR_PROBE_PLAN.md).
2. `pip install -r requirements-dev.txt && pytest -q tests` (77 tests; the closed-loop node test needs the committed `runs/real_*` checkpoints).
3. Simulator setup: [RETRAINING.md](RETRAINING.md) (f1tenth_gym 0.2.1 at commit 4fdb9c7, `python tools/prepare_tracks.py`).
4. **The first real-car task is Stage 1 of [REAL_CAR_PROBE_PLAN.md](REAL_CAR_PROBE_PLAN.md):** run `tools/real_car/probe_maneuver_node.py` on 3 tire wraps, then `tools/real_car/analyze_probe_trials.py`. It needs no learned policy, takes one session, and answers the main open question: does the real car's wheel slip during a braking pulse reveal grip, as the simulator assumes?
5. Then deploy: `ros2 launch rma_deploy_pkg veh_launch.py checkpoint:=... adaptation:=... probe:=1` (the node now defaults to 100 Hz, matching training; it was 50 Hz in July). The node is untested on hardware: secure the car first.
6. Ask Prof. Modekurthy for lab-machine access and Ederic Oytas for time with the car.

## Priority order to Feb 1, 2027 (updated Nov 5)

| # | Task | Why |
|---|---|---|
| 1 | **Stage 1 probe test on VADER** ([REAL_CAR_PROBE_PLAN.md](REAL_CAR_PROBE_PLAN.md)) | Every probe result is simulation-only; this checks the one assumption the method rests on |
| 2 | Check whether VADER's VESC publishes IMU data (`ros2 topic list`) | An IMU acceleration channel would measure the probe directly (simulated: 9.5 / 7.2 / 4.2 m/s² at grip 1.0 / 0.7 / 0.4) |
| 3 | Re-center the slip randomization on what Stage 1 measures, retrain φ (`tools/slipdr_suite.sh`, ~1.5 h per seed on 4 CPU cores) | φ is strongest when the training slip model matches the car |
| 4 | Closed-loop car trials: π + φ with the probe vs Blind, same tire wraps as July | The paper's missing real-car result |
| 5 | Close the μ = 0.4 gap | Not timing (amendment 11: longer memory and faster probe both fail). Untested candidate: the base policy itself at low grip |
| 6 | Choose the workshop; advisor review | |

## Not in this repo (ask Nathan)

| Item | Where it is | Why you might need it |
|---|---|---|
| Final lab training code (July) | Lab training machine, `/research_ws/src/f1tenth_research/` | Compare with the rebuilt parts listed in [RECONSTRUCTION.md](RECONSTRUCTION.md) |
| Raw E0–E5 results from July | Lab training machine | The *reported* numbers in the July docs/RESULTS.md (branch `archive/full-record-nov2026`) |
| 100-step φ checkpoint | Lab training machine (was training on July 21) | E3 window ablation |
| On-car logs (`rma_data_*.csv`, `rma_trial_log_*.csv`) | VADER home directory | Re-deriving the real-car table with `analysis/real_car/tire_stats.py` |
| Poster (PDF and source slides) | Nathan's Google Drive | Figures and wording for the paper |
| Camera-ready paper draft (IEEE format, sent to the advisor Sep 20, 2026) | Nathan's email / Overleaf | Starting point for the workshop submission; `paper/workshop_draft.md` is a text version |
| Paper 2 methodology, project record, reward history (full versions) | Nathan's Google Drive | Condensed into docs/EXPERIMENTS.md and docs/REWARD_HISTORY.md (the latter now on the branch `archive/full-record-nov2026`) |

## Standing constraints (do not break these)

- **φ never sees map-specific inputs.** No raceline, no pose, no waypoints. The policy observation is 5 + 108 LiDAR, and φ's input is observation + action.
- **Do not trust the raceline `psi` column.** It is 90° off; compute headings with arctan2.
- **Do not use AsyncVectorEnv with f110_gym in Docker.** Use `training/env_pool.py` (spawn-context workers), with `OMP_NUM_THREADS=1`: default PyTorch threading made parallel runs ~60× slower.
- **One f110_gym map per process** (bug C22): keep the scan-simulator snapshot logic in `envs/real_env.py`.
- **Keep the node and the env in step:** `tests/test_node_sim_consistency.py` must pass after any change to either.
- **Do not commit per-epoch checkpoints.** Curate into `checkpoints/`.
- **Do not assume the simulator punishes speed.** f110_gym's stock tires never saturate. Use `tire_model: friction_circle` when that matters (see SIM_FIDELITY.md).
- **Run anything longer than ~10 min in tmux**, not with `nohup &`.
- **Before any long run:** check per-term reward signs at small scale (`eval/sanity_check_rollout.py`), and check that `expert_actions` is non-empty (`tests/test_training_smoke.py` shows how).
- **The real car:** secure it (wheels off the ground) for first tests. Hold R2 to engage; release R2, or hold L1, for manual override.

## Working style that worked

- Edit in VS Code → push → pull on the lab machine → run in tmux → `grep "Avg Reward" train.log`.
- Judge driving by crash rate and centerline deviation, never by reward totals.
- For every experiment, write the pre-registered prediction down *before* running it (methodology Part G).

## People and access

- **Advisor:** Prof. Venkata Prashant Modekurthy (UNLV CS). He wants the code on GitHub so another student can run the experiments.
- **Lab and hardware support:** Ederic Oytas, TBE B150. He handles VADER software installs (the car has no internet on campus) and can help with scp, slam_toolbox, and the F1TENTH particle filter (its dependencies are already on the car).
- **Lab machines:** the lab training machine (Docker + noVNC) and the Dell in TBE B150. Leave a sticky note when you leave training running, and switch the power strip off otherwise.
- **Hardware upgrade:** a Jetson Orin AGX was ordered in July (the Orin NX had a 12-week wait). The power board (AE170_PDU_02.04, 19 V / 4 A = 76 W) was checked against the Orin NX's 10–25 W; **re-check it against the AGX's power envelope** before swapping.

## If you only have one week

Run Stage 1 of [REAL_CAR_PROBE_PLAN.md](REAL_CAR_PROBE_PLAN.md) on the car and analyse it with `tools/real_car/analyze_probe_trials.py`. Compare against the simulated prediction in `results/retrain_nov2026/real/probe_test_sim/analysis.md`. Whether it separates the surfaces or not, that result decides the next step and goes in the paper.
