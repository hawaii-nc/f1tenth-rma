# Bugs and lessons

Two lists:

1. **Found while consolidating this repo (October 2026).** These were in the code published as `research_ws` (the June snapshot) and/or in the July car deployment. All are fixed here, and most have a regression test.
2. **Found and fixed during the summer.** From the July 1 project record, kept so nobody has to rediscover them.

## 1. Found during consolidation

| # | Where | Bug | Effect | Fix / test |
|---|---|---|---|---|
| C1 | `envs/randomization.py`, `add_mid_episode_disturbance` | The "wet patch" disturbance only edited the Python dict. The simulator's μ was set at reset and never changed again | The encoder μ and the Phase 2 labels were told grip dropped while the physics stayed the same. This matches the "physics-injection bug" flagged on the E5 slide, and taught φ to associate *unchanged* motion with a *changed* label | `RealF110Wrapper.set_grip()` pushes μ into f110_gym via `update_params`. Test: `test_forced_disturbance_reaches_simulator` |
| C2 | same | The 30% chance was re-rolled on **every step** inside the 30–90% window, and grip was multiplied by 0.7 each time | Grip in the dict compounded toward 0 within about a second; the label ended near grip ≈ 0 | One drop per episode, decided at reset (30% of episodes), at a uniform time in the window. Test: `test_disturbance_is_one_shot_and_non_mutating`, `test_sampled_disturbance_fires_at_most_once` |
| C3 | `envs/real_env.py` | `motor_steering_scale` and `motor_drive_scale` were sampled and fed to μ but **never applied** to the car | Two of the seven "physics" inputs were pure noise to the encoder | Applied to the steering and velocity commands |
| C4 | `envs/f1tenth_env.py` | `v_des` was hard-coded to `(thr+1)/2 × 8.0`, while the final config and the car use a 3.0 m/s cap | The training observation and the deployment observation disagreed on `v_des` (index 2) unless the lab code had been patched | Uses `environment.max_velocity`. Test: `test_observation_matches_final_checkpoint` |
| C5 | `training/phase1_ppo_il.py` | The IL expert's state was built from the **observation**: position = (v, steering), yaw = v_des, velocity = steer_des | Pure Pursuit steered toward waypoints from a meaningless "pose" | The pose comes from `info` (privileged, never in the observation), with one expert per track. Test: `test_phase1_runs_and_expert_is_active` |
| C6 | `experts/__init__.py` | A partial config replaced the defaults instead of merging, so `config['grip_aware']` raised `KeyError`, which the rollout's bare `except` turned into "no expert action" | With the final config, imitation learning silently had **no signal** | Configs merge over defaults. Test: `test_partial_config_keeps_defaults` |
| C7 | `experts/__init__.py` | The expert emitted throttle = 0.5 × speed error (a P-controller *delta*), but the env reads throttle as an *absolute* setpoint | Expert "hold speed" meant "drive at v_max/2" | Emits the setpoint for the target speed. Test: `test_throttle_is_absolute_velocity_setpoint` |
| C8 | `training/phase2_adaptation.py` buffer | A `deque(maxlen)` of histories next to an unbounded list of labels | Once the buffer filled, histories and labels drifted apart (wrong label for every window) | An episode-structured buffer. Test: `test_eviction_keeps_alignment` |
| C9 | same | Windows were cut from one flat stream | A window could straddle two episodes with different physics | Windows are cut inside one episode. Test: `test_windows_never_cross_episodes_and_labels_align` |
| C10 | `training/phase2_adaptation.py` | Built `RMAActorCritic()` with the default `obs_dim=5` | Could not load any LiDAR checkpoint | `load_actor_critic()` sizes the model from the checkpoint |
| C11 | `f1tenth_research/setup.py` | `packages=[package_name]` installs only the top-level package | `colcon build` dropped `envs/`, `models/` and the rest; the car needed a `PYTHONPATH` workaround | `find_packages()` |
| C12 | `rma_deploy_pkg/launch/veh_launch.py` + node | The launch file passes `--adaptation ''`, and the node then called `torch.load('')`. The node's `--history_window` defaulted to 10 | Phase 2 could not launch from the launch file; the 50-step φ cannot load with k = 10 | Empty string means "no φ". k is read from the checkpoint |
| C13 | deploy node | `torch.load(..., weights_only=False)` | Loading an emailed or scp'd checkpoint could execute arbitrary code | `weights_only=True` everywhere |
| C14 | deploy node | The CSV log path was hard-coded to `/home/<user>/rma_data.csv`, and the "no LiDAR yet" rows had 14 columns instead of 15 | Broke for any other user; columns misaligned at startup | `--log_path`; rows padded to the header |
| C15 | `envs/reward.py`, `experts`, `randomization` | Partial YAML blocks replaced the defaults | `KeyError`s, or silently disabled terms | All three merge over defaults |

Found in November 2026, when the pipeline was first run end to end on the real f110_gym (not the CI fake simulator):

| # | Where | Bug | Effect | Fix / test |
|---|---|---|---|---|
| C16 | `envs/real_env.py`, `spawn_pose_from_centerline` | Found the centerline point nearest (0.7, 0) but returned **(0.7, 0) itself** as the spawn position | On the 10 racetrack-DB tracks (0.7, 0) is up to 0.7 m off the centerline, while the half-width is 0.38 m: the car started inside or outside the walls. Even the expert crashed in 1–30 steps | Spawn at the centerline point. Test: `test_spawn_is_on_the_centerline` |
| C17 | `tools/prepare_tracks.py` | Uniform 35% scale | Corners tighter than the car can turn (min turning radius 0.74 m; aut_tight has a 0.24 m hairpin). The Pure Pursuit expert crashed on 13 of 14 tracks even after C16 | Per-track scale: the smallest of 0.35, 0.40, … at which the expert laps (`TIGHT_SCALE`). Zandvoort crashes the expert at the same spot at every scale (map defect) and is left out |
| C18 | `tools/prepare_tracks.py` racelines | Racelines were scaled with the track, but the car is not | A scaled raceline passes within the car's half-width of the wall (9 cm on ims_tight); the IL expert crashed within ~50 steps on every DB track | No raceline for `*_tight`; the expert follows the centerline, which laps all 13 tracks |
| C19 | `training/phase1_ppo_il.py` rollout with `num_envs > 1` | (a) GAE ran over env-interleaved steps as one trajectory; (b) env 0's expert action was the IL label for every env; (c) env 0's physics fed μ for every env (gymnasium's vector-info format); (d) every rollout reset the env | Parallel training was silently wrong, so the July runs had to use `num_envs: 1` (≈ 250 steps/s) | `training/env_pool.py`: per-env GAE, labels and physics; episodes continue across rollouts; `--resume`. Tests: `tests/test_phase1_pool.py` |
| C21 | `training/phase1_ppo_il.py` update | The rollout stored μ(e) as numbers and the update reused them | The intrinsics encoder μ **never received a gradient**: z was a fixed random projection of e | Store e, recompute μ(e) inside the loss. Test: `test_ppo_update_trains_the_encoder` |
| C22 | `envs/real_env.py` + f110_gym | f110_gym's LiDAR/map simulator is **one per process** (`RaceCar.scan_simulator` is a class attribute). The env caches one `F110Env` per track, and building a new one replaces the map for all of them | Once every track had been visited, **every track ray-cast and iTTC-collided against the last-loaded map**: the car drove one track's geometry while seeing another's walls. This invalidated multi-track training and every multi-track experiment run in one process. It may also have affected the lab pipeline if it cached envs the same way | Each wrapper snapshots the scan simulator after loading its map and restores it when it becomes active. Test: `tests/test_real_sim.py` (needs f110_gym; fails without the fix) |
| C20 | `training/phase1_ppo_il.py` IL loss | A missing expert action dropped IL for the **whole rollout** (length check) | Same silent-IL failure class as C6 | Per-transition mask; an all-missing rollout raises. Test: `test_missing_expert_signal_is_loud` |

**The July checkpoints cannot drive the rebuilt environment.** At nominal grip with no noise, `phase1_v42.pt` crashes within about 100 steps on every track, including the IMS oval (min radius 4.8 m), while the expert laps it. None of these variants fixed it: flipped LiDAR, the deployment footprint margin, a 50 Hz policy, the June `v_des` scaling, or `ttc_thresh` 0.005. The lab environment differed in ways that were never saved (RECONSTRUCTION.md lists the low-confidence parts). So the whole pipeline was retrained: see [RETRAINING.md](RETRAINING.md).

**Consequence for results.** All July sim numbers (E0, E1/E2, E4, E5) come from a pipeline with some subset of C1–C9. The lab copy may have fixed some of these: the July 21 slides say a physics-injection fix landed before E3. That is why [RESULTS.md](RESULTS.md) marks them *pre-fix* and [HANDOFF.md](HANDOFF.md) puts the re-runs first.

## 2. Found and fixed during the summer (project record, July 1)

| Bug | Symptom | Fix / lesson |
|---|---|---|
| Softmax PPO on continuous actions | Policy collapsed to a constant action; reward worse than random (runs 1–3) | Gaussian actor (mean + log_std), real PPO ratio + clip, masked GAE |
| Placeholder expert waypoints | A degenerate 2-point waypoint file made the expert useless; a 150-epoch run was corrupted with no error | Load the real raceline. **Always check expert behaviour before a long run** |
| Config nesting | All YAML reward and randomization settings were silently ignored for 4+ runs | The env reads `config['environment']`. Silent config-wiring bugs are the most dangerous class (C6 and C15 are the same class) |
| `max_yaw_rate_error = 1.0` | The yaw-rate reward term was always saturated | 4.0 (term later removed) |
| IL decay scale | Zhang's constants assume ~100M steps; at 2M steps IL vanished too fast | Rescale `il_weight_decay`; plateau-triggered IL rescue |
| Velocity-tracking reward exploit | The policy commanded v_des ≈ 0, stood still, and scored 999.5/1000 | Progress = arc length along the centerline, capped per step |
| Raceline `psi` column is 90° off | Cars spawned facing walls in Gazebo | Heading = arctan2 of neighbouring centerline points |
| AsyncVectorEnv + f110_gym in Docker | Shared-memory crashes | Sequential envs (`num_envs: 1`) |
| Corrupted sim state | LiDAR readings near 0 m | Restart the container |
| Container restarts wipe `sim.yaml` edits | Config changes vanished | Edit the installed copy |
| `git push` 408 timeout | Pushing 98 checkpoints (165 MB) failed | Commit only curated checkpoints; `.gitignore` per-epoch files |
| `nohup … &` dies with `docker exec` | Overnight training died silently | Run long jobs in **tmux** |
| Broken `quadprog` wheel | The TUMFTM raceline optimizer failed to import | `pip install --no-binary quadprog --force-reinstall --no-deps quadprog` |
| nano over SSH | Tab/space corruption | Edit remotely with `cat <<'EOF'` heredocs |

## Lessons that generalise

1. **Verify that a randomized parameter reaches the physics,** not just the logs. Print the simulator's actual μ, not the dict's. C1 and C3 survived all summer because every log line looked right.
2. **Never wrap an imitation or reward signal in `except Exception: pass`.** A missing signal must be loud.
3. **The expert is the most critical upstream dependency.** Assert the expert's action distribution (and that it exists) before every long run.
4. **Trust driving metrics over reward totals.** A reward near zero once turned out to be a scaling artifact.
5. **Rescale hyperparameters to your training budget.** Paper decay constants assume 10–100× more steps.
6. **Know your simulator's physics** before claiming a safety result. See [SIM_FIDELITY.md](SIM_FIDELITY.md).
