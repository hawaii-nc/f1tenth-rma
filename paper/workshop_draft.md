# You Cannot See Grip Without Using It: Active Probing for Rapid Motor Adaptation in Autonomous Racing

*Workshop-paper draft (rewrite of Nov 3, 2026), target IEEE IV 2027 Workshops (papers due Feb 1, 2027).*
*All simulation numbers come from `results/retrain_nov2026/` (see `docs/RESULTS_NOV2026.md`); every prediction was registered first in `docs/PREREGISTRATION_NOV2026.md`. Citation keys refer to `references.bib`.*

**Nathan Chong** (University of Hawaiʻi at Mānoa; NSF REU at UNLV) and **Venkata Prashant Modekurthy** (UNLV)

---

**Abstract.** Tire–road friction sets a race car's safe operating envelope, changes with surface, wear and payload, and is not measured by any onboard sensor. Rapid Motor Adaptation (RMA) [kumar2021rma, zhang2025extreme] promises to infer such hidden conditions from the robot's recent motion. We apply it to grip on the F1TENTH platform [okelly2020f1tenth] and find that, done the standard way, it cannot work: with the car's actions decoupled from grip, its 0.5 s motion history carries no information about grip (R² −0.02), for three tire models, because the car is close to neutral steer and drives well inside the friction circle. An adaptation module trained the standard way instead reads grip off the expert's own driving (action leakage) and becomes *less* safe than not adapting at all; a module trained on its own rollouts is safe only because it drives uniformly slowly, and a speed-capped non-adaptive car matches it. We then add an **active probe**: a brief speed pulse on straights that asks the tires for more than low grip can give. With a proprioceptive adaptation module, grip becomes readable (R² 0.89–0.93), the car drives within 0.1 m/s of an oracle's speed at every grip, and at μ = 0.4 it crashes in 0.02–0.07 of episodes vs 0.33–0.47 for a non-adaptive car matched to its speed (p < 10⁻⁷), on all three training seeds, and no fixed speed limit matches it on both speed and safety. Retrained for transfer to a real car (wheel-odometry speed with slip, kinematic yaw rate, commanded steering, 40 Hz LiDAR, a braking probe and a racing expert at up to 3 m/s), the controller still reads grip (R² 0.84–0.87) and, at the same average speed, crashes in 0.00–0.05 of episodes at μ = 0.6 vs 0.33–0.56 without adaptation, and in 0.28–0.39 vs 0.84–0.86 at μ = 0.4.

## I. Introduction

- Grip governs the limits of safe control, and it changes: rain, tire wear, dust, payload. A controller tuned for nominal grip is either conservative everywhere or unsafe when grip falls.
- RMA [kumar2021rma] trains a base policy on privileged physics, then an adaptation module that recovers those physics from recent states and actions. It works for legged robots and quadcopters [zhang2025extreme], whose dynamics expose the hidden parameters all the time.
- A car's grip is different: below the limit, the tires deliver whatever force is asked of them, at any grip. Grip shows only near the limit, which a cautious controller never visits. This is the familiar excitation requirement of tire–road friction estimation [acosta2017friction, khaleghian2017survey].
- **Question.** Can an RMA controller on F1TENTH infer grip from its own motion, and does adapting to it beat simply driving slower?

**Contributions:**

1. **A leakage-free observability test.** Rolling out the policy with a *random* grip belief, independent of the true grip, removes the information that the controller's own actions carry. Under it, the motion history contains no grip information for the linear, friction-circle and Fiala brush tires, which explains why standard RMA fails here and why apparent successes are leakage.
2. **Active grip probing for RMA.** A 0.1 s speed pulse every 0.5 s on straights, applied identically to all controllers, plus a proprioception-only adaptation module, makes grip readable and yields oracle-like speed modulation.
3. **A speed-matched control.** Comparing against a non-adaptive car capped at the adaptive car's own speed separates *adaptation* from *slowness*. Without the probe, slowness explains all of the safety gain; with it, adaptation does not.
4. **Methodology**: pre-registered hypotheses and amendments, paired episodes from seeded random starts (fixing a pseudo-replication flaw in our earlier protocol), three training seeds and held-out tracks.

## II. Related work

- **RMA.** Base policy plus an adaptation module regressed on privileged encodings [kumar2021rma]; joint PPO+IL with a decaying imitation weight for quadcopters [zhang2025extreme]. RMA's adaptation module is trained on its own rollouts to avoid distribution shift; we show a second reason it matters, action leakage.
- **Learning on F1TENTH.** LiDAR-only deep RL [hell2024lidar, evans2023trajectory], imitation-learning benchmarks [sun2023ilbenchmark], and the survey and benchmarks in [evans2024unifying]. None estimates vehicle physics online.
- **Domain randomization** gives robustness [tobin2017dr]; RMA turns it into adaptation by conditioning on the sampled physics.
- **Tire–road friction estimation** needs excitation: slip-based estimators need high tyre utilization (up to 80–90% on low-μ surfaces in the studies reviewed by [acosta2017friction]; 54–94% for a brush-model estimator in [prokes2016excitation]) and fail in steady driving [khaleghian2017survey]. We bring this requirement to learned adaptation and meet it with a deliberate excitation, the probe.
- **Sim-to-real for F1TENTH racing.** RL racing policies have been deployed zero-shot on F1TENTH cars using domain randomization and actuator modeling [czechmanowski2025racing] and with disturbances and observation preprocessing [budai2025endtoend]. History-dependent policies provably help domain-randomized transfer [chen2022understanding], which supports RMA's history-based adaptation module.
- **Friction circle / g-g diagram** [milliken1995rcvd].

## III. Method

**A. Platform and observation.** f1tenth_gym [okelly2020f1tenth] single-track model at 100 Hz, with a friction-circle tire we add: each axle's lateral force is capped at √((μF_z)² − F_x²) and acceleration at μg (the stock model never saturates). x_t ∈ ℝ¹¹³: speed, steering, the previous speed and steering commands, yaw rate, and 108 LiDAR beams (clipped at 10 m, normalized). The action is (steering ∈ [−0.42, 0.42] rad, speed command ∈ [0, 3] m/s). No map or pose enters the controller.

**B. Randomization.** Per episode e ∈ ℝ⁷: grip ∈ [0.4, 1.0] (μ = 1.0489·grip); mass, inertia, steering and drive gains ±20%; steering and drive delays 0–50 ms; then ±20% noise. 30% of training episodes get one mid-episode grip drop (×0.7). LiDAR noise σ = 0.02 and 5% dropout.

**C. Phase 1 (base policy).** π(x, z) (MLP 3×256) and encoder z = μ(e) ∈ ℝ⁸ (7→128→128→8), trained by DAgger (6 × 100k steps, β halving from 1) from a grip-aware Pure Pursuit expert [coulter1992purepursuit] on 13 circuits [betz2022racing], each scaled to the tightest size the expert can lap (0.35–0.70). PPO fine-tuning lowered closed-loop validation, so we use the DAgger policy.

**D. Phase 2 (adaptation module).** φ: Conv1d stack (32-32-8, kernel 5) and FC (→128→8), mapping the last k = 50 steps (0.5 s) to ẑ. MSE to μ(e), plus an auxiliary physics head (grip weighted 3×). Data: 800 episodes driven by the true z, then **3 on-policy rounds** (250 episodes each, driven by φ's own ẑ, labelled with the true z) [kumar2021rma].

**E. Active grip probe.** Every 50 steps, for 10 steps (0.1 s), add 2.0 m/s to the speed command while |steer| < 0.15 rad. The speed controller then requests ~9.5 m/s², which the tire caps at μg, so the achieved acceleration measures grip. The probe runs identically for every controller, in training and evaluation. With the probe, φ takes only the 7 proprioceptive channels (speed, steering, the two previous commands, yaw rate, and the action); the 108 LiDAR channels swamp the signal (offline R² 0.15 vs 0.67).

**F. Controllers.** One frozen π with three sources of z: **Oracle** μ(e_true), **φ** φ(history), **Blind** μ(e_nominal). **Speed-matched Blind:** Blind with its speed command capped at φ's own mean speed at μ = 1.0.

**G. Leakage-free observability test.** Roll out π with z = μ(e) where the grip entry of e is drawn uniformly from [0.2, 1.0] independently of the true grip, so the actions carry no grip information. Fit (i) a ridge probe on physical window features (peak acceleration and braking, lateral acceleration, yaw rate vs kinematic yaw rate, speed error) and (ii) φ's architecture, both scored by grouped cross-validation over episodes.

## IV. Experiments

Forced μ ∈ {1.0, 0.8, 0.6, 0.4}, N = 100 episodes per cell, each starting at a seeded random point on the lap, the same for every controller (paired). Statistics: Wilson CIs, exact McNemar on paired crashes, Wilcoxon on ρ, Holm across grips, episode bootstrap.

- **E1/E2:** crash rate, speed and friction-circle utilization ρ = √(a_lat² + a_long²)/(μg).
- **E5:** grip R² of ẑ (ridge, cross-validated by episode, N = 200 episodes, grip uniform in [0.2, 1.0]).
- **Speed-matched control (Q3):** at μ = 0.4, does capped Blind crash ≥ 0.10 more than φ (McNemar p < 0.05)?
- Configurations: **P2** (friction-circle tire, on-policy φ, no probe) and **Q** (P2 + probe + proprioceptive φ), three training seeds each; held-out tracks (mco, silverstone, budapest never seen in training).

## V. Results

**A. Without excitation, grip is not observable.** Leakage-free test, 240 episodes per condition:

| driving | tire | grip R² (physical features, 0.5 s) |
|---|---|---|
| random belief | friction circle | **−0.02** |
| random belief | Fiala brush | −0.03 |
| oracle belief | friction circle | 0.97 (leakage) |
| φ's belief | friction circle | 0.68 (leakage) |
| random belief **+ probe** | friction circle | **0.84** (0.997 per episode) |

Below the limit, grip barely changes the yaw response (steady cornering, μ 0.4 vs 1.0: −3% at 1.5 m/s, −5% at 2 m/s), and the policy's 99th-percentile acceleration (3–3.7 m/s²) and lateral acceleration (~2 m/s²) stay under even low-grip μg (3.9 m/s² at μ = 0.4). With the probe, peak acceleration tracks μg: 3.1 / 5.1 / 7.3 / 8.6 m/s² for grip bins 0.2–0.4 … 0.8–1.0.

**B. Standard RMA fails, in two different ways.** Linear tire, φ trained on oracle-driven data: φ drives *faster* than the oracle at every grip (2.13 m/s), crashes more than Blind at μ = 0.4 (0.39 vs 0.32), and decodes no grip (R² −0.02): action leakage. On-policy φ removes the leakage but learns a constant 1.53 m/s. With the friction-circle tire (P2, 3 seeds), φ is far safer than Blind (crash 0.04 ± 0.03 vs 0.44 at μ = 0.4) but slows only 0.10–0.19 m/s with grip (Oracle 0.79), R² 0.28 ± 0.05, and **Blind capped at φ's speed is as safe on every seed** (0.06 / 0.07 / 0.01 vs φ 0.07 / 0.05 / 0.01).

**C. With the probe, adaptation beats slowness.** Table I (Q, per training seed):

| | seed 0 | seed 1 | seed 2 |
|---|---|---|---|
| φ speed μ = 1.0 → 0.4 (m/s) | 2.02 → 1.28 | 2.06 → 1.29 | 2.00 → 1.28 |
| Oracle speed μ = 1.0 → 0.4 | 2.12 → 1.27 | 2.11 → 1.27 | 2.11 → 1.26 |
| crash at μ = 0.4: φ / Blind / Oracle | 0.07 / 0.46 / 0.06 | 0.02 / 0.47 / 0.00 | 0.08 / 0.43 / 0.06 |
| Blind matched on measured speed: crash at μ = 0.4 (McNemar p) | 0.37 (2×10⁻⁹) | 0.47 (6×10⁻¹⁴) | 0.33 (6×10⁻⁸) |
| E5 φ grip R² | 0.90 | 0.93 | 0.89 |
| ρ gap closed at μ = 0.4 | 87% | 82% | 83% |

The probe adds speed on top of a cap, so the Blind cap is set to match φ's *measured* speed at μ = 1.0 (within 0.01–0.05 m/s). **Fixed-limit frontier** (seed 0): capped at 1.7 / 1.5 / 1.3 m/s, Blind drives 1.82 / 1.63 / 1.43 m/s at μ = 1.0 and crashes 0.12 / 0.07 / 0.07 at μ = 0.4. Matching φ's safety (0.07) with a fixed limit costs 0.4–0.6 m/s (19–29%) on high grip; matching its speed costs 5× the crashes.

**The probe is necessary.** Evaluating the same seed-0 φ with the probe off, it falls back to a constant ~1.2 m/s (1.20 → 1.16 m/s) with grip R² 0.24, the P2 behaviour. **Detection speed:** after a grip step from 1.0 to 0.4, φ's decoded grip settles within ±0.1 in a median of 0.77 s (39/39 episodes). **Held-out tracks:** a φ trained without three circuits closes 80% [73, 86] of the gap on them at μ = 0.4 (crash 0.03 vs Blind 0.56), vs 87% for the model that trained on them.

**Cost of the probe.** Same base policies, seeds and starts, without → with the probe, three seeds: crash rates change by at most 0.02 for Blind and the Oracle at every grip (e.g. Blind at μ = 0.4: 0.44 → 0.46, 0.46 → 0.47, 0.41 → 0.43), and the pulses raise mean speed by 0.07–0.15 m/s. Tire wear, energy and smoothness are not measured.

**C2. Under realistic car sensors and racing speeds (configuration R).** We retrain the base policy and φ with the observation built as the car's node builds it from the standard F1TENTH stack: speed from VESC wheel odometry (the wheel spins up or locks when the tire is traction-limited; ±5% ERPM gain error; noise; 50 Hz), yaw rate computed as v·tan(δ_cmd)/L (no gyro), the commanded steering, and 40 Hz LiDAR with the node's 0.10 m margin. The probe becomes a 0.1 s *braking* pulse of 1 m/s (an accelerating pulse at racing speed asked for 5 m/s before corners), φ also sees the 10 front LiDAR beams, and the expert races: full 3 m/s on straights, corners at √(0.6·μ·g·R), braking at 0.5·μ·g. The new base policies are faster and safer in validation (0/39, 0/39, 2/39 crashes at ~2.5 m/s, vs 3/39 at 1.2–2.0 m/s).

| R, per seed | seed 0 | seed 1 | seed 2 |
|---|---|---|---|
| E5 φ grip R² | 0.86 | 0.84 | 0.87 |
| speed at μ = 1.0 → 0.4: φ / Oracle | 2.55 → 2.39 / 2.56 → 2.29 | 2.55 → 2.40 / 2.56 → 2.43 | 2.54 → 2.35 / 2.55 → 2.48 |
| crash at μ = 0.6: φ / Blind / Oracle | 0.01 / 0.56 / 0.00 | 0.05 / 0.43 / 0.00 | 0.00 / 0.33 / 0.00 |
| crash at μ = 0.4: φ / Blind / Oracle | 0.39 / 0.86 / 0.02 | 0.28 / 0.84 / 0.00 | 0.37 / 0.86 / 0.09 |
| Blind matched on measured speed, crash at μ = 0.4 (p) | 0.85 (3×10⁻¹⁴) | 0.84 (3×10⁻¹⁷) | 0.86 (4×10⁻¹⁵) |

All pre-registered checks except H3 pass on every seed. Here adaptation is *where* to slow, not how fast: the three controllers average the same speed, and a fixed cap that leaves Blind 0.4 m/s slower than φ still crashes 0.77–0.78 at μ = 0.4. μ = 0.6 is essentially solved; at μ = 0.4 φ closes 49–58% of the gap (82–87% with ideal sensors), plausibly because an estimate that needs a probe on a straight arrives late for the next corner at racing speed.

**C3. Robustness to the wheel-slip model.** The R controller read grip from the specific wheel-slip pattern of the simulated odometry: evaluated with no slip (odometry equal to true speed) it was blind (seed 0, μ = 0.4: 0.86 crash vs 0.86 for Blind). Re-training φ with the slip model randomized per episode (spin-up 10–150 m/s², recovery 0.01–0.15 s, no slip in 25% of episodes) removes this failure without cost under the default model (μ = 0.4: 0.41 / 0.25 / 0.33 vs 0.39 / 0.28 / 0.37 before). Across five slip models and three seeds, φ beats Blind in all 30 comparisons (μ = 0.6: ≤ 0.07 vs 0.29–0.56; μ = 0.4: 0.21–0.67 vs 0.84–0.86); with no slip it still reads grip (R² 0.59–0.63). The pre-registered margin at μ = 0.4 (0.30) is missed on one seed for the two weakest-signal models (0.19, 0.22). The probe's effect also holds on three held-out tracks (gap closed 41% vs 39% for a model trained on them) and the estimate settles within 0.22 s after a grip drop.

**D. A pre-registered check that failed.** H3 (cross-grip variance of ρ, Blind/φ ≥ 10×) fails with the probe (3.7×, 3.3×, 3.2×), but the Oracle itself reaches only 5.4–5.6×: each pulse loads the tires near the limit at every grip, which changes what ρ measures. Without the probe the check passed (16×) for the wrong reason, a uniformly slow φ.

**E. Real-car pilot (July 2026, earlier pipeline).** A Traxxas Slash 4×4 F1TENTH build ran the July checkpoint (linear tire, no probe) through one 90° corner on polished concrete with four tire wraps, 81 trials:

| Tires | n | pass | yaw (rad/s) | steer (rad) |
|---|---|---|---|---|
| bare | 20 | 19 | 0.678 | 0.133 |
| foil | 21 | 21 | 0.645 | 0.128 |
| duct | 21 | 21 | 0.663 | 0.129 |
| electrical | 19 | 18 | 0.661 | 0.128 |

Bare vs electrical tape: yaw p = 0.009, steering p = 0.0001 (Mann–Whitney U). This shows that the policy's commands respond to a real tire change; it does not test the probe or the retrained pipeline.

## VI. Discussion and limitations

- **The probe changes the method.** The controller no longer adapts passively: it spends a small, fixed amount of driving on measuring grip. This is a design choice with a cost (speed fluctuations, tire wear, energy) that we fix rather than optimize; a learned, risk-aware probing policy is future work.
- **Slip-model dependence.** Even with randomization, the controller is strongest when the wheel-slip signature is present; how VADER's wheels actually slip under a braking pulse is measured by the Stage 1 test, and the randomization range should then be centered on it.
- **Simulation idealizations.** Configuration R models the car's sensors (wheel-odometry speed with slip, kinematic yaw rate, commanded steering, LiDAR rate), but the wheel-slip model itself (spin-up to the command at 40 m/s², 30 ms relaxation) is an assumption; it decides how much the odometry reveals during a braking pulse, and must be measured on the car. The friction-circle tire caps force cleanly; real tires spin up and lock progressively.
- **Control rate.** The real-car node runs at 50 Hz but training is at 100 Hz (bug C23); the July trials ran with this mismatch, and it must be fixed before probe trials.
- **Regime.** Speeds ≤ 3 m/s on narrow (0.63–0.76 m) scaled tracks; our expert cannot lap them above ~3.5 m/s, so high-speed results are open.
- **Uniform grip.** Grip is constant over the track (plus one drop); real surfaces vary patch to patch.
- **Real car.** No probe trials and no measured μ per surface yet. The next experiment: probe pulses on 2–3 surfaces, logging wheel speed, IMU and commands, to test whether the achieved acceleration separates the surfaces as in simulation.

## VII. Conclusion

On F1TENTH, RMA cannot infer grip from passive driving: the information is not in the motion, and models that appear to succeed are reading their own actions or simply driving slowly. A brief, deliberate speed pulse makes grip observable; an RMA controller with that probe matches an oracle's speed at every grip and beats a speed-matched non-adaptive car on safety at low grip, across training seeds. Retrained with the car's real sensing and at racing speeds, it keeps most of that benefit. The deployment node now matches training, and the remaining question, whether the real car's wheel slip during a braking pulse reveals grip as the model assumes, is a one-session experiment that we describe.

**Acknowledgment.** Supported by NSF REU Site Award #2349616 (UNLV Smart Cities). Thanks to Ederic Oytas for hardware support.
