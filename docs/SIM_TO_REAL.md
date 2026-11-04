# Sim-to-real: what the training does to transfer to VADER, and what is still open

Written Nov 4, 2026, with amendment 8 (`docs/PREREGISTRATION_NOV2026.md`). It covers what the July pipeline already did, the mismatches found since, what is now modeled, and what only the real car can settle.

## 1. Already in the pipeline (July work, kept)

| Measure | Where | Values |
|---|---|---|
| Physics domain randomization | `envs/randomization.py` | grip 0.4–1.0; mass, inertia, steering and drive gain ±20%; steering and drive delay 0–50 ms; then ±20% noise; 30% of episodes get a mid-episode grip drop |
| Actuator delays | `envs/real_env.py` | FIFO queues at the 0.01 s sim step |
| LiDAR noise | `observation` config | Gaussian σ = 0.02 (normalized), 5% beam dropout |
| Map-agnostic observation | env + node | 108 LiDAR beams + 5 motion signals; no map, pose or raceline |
| Drift spawns | `drift_spawn_prob` | 30% of training episodes start with a heading error |
| Deployment safety margin | `rma_deployment_node.py` | walls seen 0.10 m closer; optional speed shield; R2 dead-man switch |

## 2. Mismatches between training and the car (found Nov 3–4)

| # | Training (before amendment 8) | Car (`rma_deployment_node.py`, standard F1TENTH stack) | Status |
|---|---|---|---|
| 1 | Control at 100 Hz | Node at 50 Hz (bug C23) | **Fixed:** node defaults to 100 Hz |
| 2 | Speed = true vehicle speed | `/odom` speed = VESC wheel speed: reads the wheel, which spins up or locks when the tire is traction-limited; calibration (ERPM gain) error | **Modeled** (sensors.model = car) |
| 3 | Yaw rate = true (gyro-like) | `/odom` angular rate from `vesc_to_odom` = v·tan(steering command)/L: kinematic, not measured | **Modeled** |
| 4 | Steering obs = delayed, scaled steering actually applied | Node has no servo feedback: steering obs = last command | **Modeled.** The old sim channel also leaked the steering gain and delay |
| 5 | LiDAR fresh every step, no footprint margin | Hokuyo at 40 Hz; node subtracts 0.10 m | **Modeled** (40 Hz hold, same margin) |
| 6 | Steering clip 0.4189 rad | Node clip 0.436 rad | **Fixed:** node default 0.4189 |
| 7 | Probe in sim only | — | **Fixed:** node `--probe 1` (same logic, after the speed command, before the shield) |
| 8 | Expert drives 2.0 m/s × grip factor everywhere (not a racing line speed) | — | **Changed:** physics-based corner/braking speed profile up to 3 m/s (section 3) |

Assumption to check on the car: the wheel-slip model. When f110's speed controller requests more than μg, the model lets the wheel spin up or lock towards the command at 40 m/s² and then roll back to the car's speed with a 30 ms time constant. Real VESC current limits and wheel inertia decide the true shape. Stage 1 of `docs/REAL_CAR_PROBE_PLAN.md` measures exactly this.

## 3. Driving fast but safe: what the policy is actually trained on

The base policy π is trained by **DAgger imitation** of a Pure Pursuit expert. The RL reward (`envs/reward.py`: 5.0 × progress, −1.0 collision, 0.05 smoothness, 0.01 alive, 0.5 speed–turn coupling, 0.1 centerline error) is defined but not what trains the selected policy: PPO fine-tuning lowered closed-loop validation (RETRAINING.md), so the DAgger checkpoint is used. **So "fast" is whatever the expert does.**

- **Before:** the expert drove a fixed 2.0 m/s scaled by grip (×0.6 at grip 0.4), the same on straights and in corners. Not a racing behaviour.
- **Amendment 8 expert:** speed = min(3.0 m/s, √(v_c² + 2·a_b·d)) over the next corners, with corner speed v_c = √(f·μ·g·R), f = 0.6 of the friction limit, braking a_b = 0.5·μ·g, true μ. Full speed on straights, braking into corners, slower corners on low grip. Lap check over 13 tracks × 2 starts: no crashes at grip 1.0 and 0.6 (mean 2.9 and 2.8 m/s) and 2/26 at grip 0.4 (2.6 m/s; aut and sepang hairpins). Cornering at 0.5 or 0.45 of the limit did not remove the grip-0.4 crashes (4/26, 2/26), so 0.6 is used.
- **Still open:** a lap-time objective (RL fine-tuning on progress with a crash penalty, as in [Evans 2023] and [Czechmanowski 2025]) could beat the expert; it failed to help in our July/Nov PPO runs.

## 4. What the literature does (searched Nov 4; arXiv full text was not reachable from this session, so details come from abstracts and summaries)

- **Czechmanowski, Węgrzynowski, Kicki, Walas, "On learning racing policies with reinforcement learning" (arXiv 2504.02420, 2025).** RL policy trained in simulation, deployed zero-shot on an F1TENTH car; studies domain randomization, **actuator dynamics modeling** and policy architecture; beat MPC and an expert human driver on a 17 m track. The closest published precedent. *To do: read the full paper (needs arxiv.org allowed in the session) and compare their actuator model and randomization ranges with ours.*
- **Budai et al., "End-to-end Reinforcement Learning for Autonomous Racing: Bridging the sim-to-real gap" (ACC 2025).** Domain randomization, training with disturbances, observation preprocessing; validated on an F1TENTH-type car.
- **Evans et al., "High-speed Autonomous Racing using Trajectory-aided Deep Reinforcement Learning" (RA-L 2023, arXiv 2306.07003).** LiDAR-only agents in the F1TENTH simulator learn a feasible speed profile by following a reference trajectory; notes that the single-track linear tire model is only accurate for small slip angles.
- **Chen et al., "Understanding Domain Randomization for Sim-to-real Transfer" (ICLR 2022).** Theory: with domain randomization, policies with memory (history) transfer better. Supports RMA's history-based φ.
- **Friction estimation needs excitation:** Acosta et al., Applied Sciences 2017 (review): slip-based estimators need high excitation; Prokeš et al. (Chalmers): the brush model needs 54–94% friction utilization for an accurate estimate. This is the observability finding of amendment 6 and the reason for the probe.
- **IMU + motor speed on F1TENTH** (arXiv 2408.15610): velocity estimation from IMU and motor speed with a learned model under large slip; relevant if VADER's VESC IMU can be used.

## 5. Still open (needs the car or a decision)

1. **IMU.** HARDWARE.md lists LiDAR + wheel odometry only. If VADER's VESC publishes IMU data, a longitudinal-acceleration channel would measure the probe directly instead of through wheel slip and LiDAR.
2. **Actuator identification.** Steering servo rate and motor response are f110 defaults (3.2 rad/s, 9.51 m/s²) plus ±20% randomization; measure them on VADER (step commands, rosbag) and center the randomization on the measured values.
3. **LiDAR beam count and field of view.** The node resamples whatever the scan has to 108 beams; check that VADER's scan is 270° like the simulated one.
4. **The probe's cost on the real car:** tire wear, battery, and whether the pulses upset the car on a real surface.
