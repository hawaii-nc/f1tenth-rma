# Pre-registration for the November 2026 retrained pipeline

Written and committed on 2026-11-01, **before** any E1–E5 result of the retrained pipeline was seen. The git history timestamps this file. What *had* been seen when writing it:

- Phase 1 validation of the DAgger base policy (oracle intrinsics): 0/39 crashes at grip 1.0/0.6/0.4 on the 13 tracks.
- A 10-episode E0 check on aut_tight: the Blind controller crashed 0% at grip 1.0/0.8 and 100% at grip 0.6/0.4/0.2.
- Phase 2 training loss and held-out latent L2 error (0.124).

Everything below is fixed now. Results that contradict it will be reported as such. Anything added after results come in will be labelled *post hoc*.

## Fixed protocol

| Item | Value |
|---|---|
| Base policy | DAgger checkpoint, selected by closed-loop validation (docs/RETRAINING.md) |
| Tracks | 13 `*_tight` tracks at per-track drivable scale; round-robin |
| Grip sweep (E1/E2) | μ ∈ {1.0, 0.8, 0.6, 0.4}, N = 100 per cell, paired seeds |
| E0 | Blind, μ ∈ {1.0, 0.8, 0.6, 0.4, 0.2}, N = 40, aut_tight |
| E3 | μ 1.0 → 0.4 at step 500, band ±0.1, hold 25 steps, N = 40 |
| E4 | July protocol (true grip 0.4 for blindfold/restore; 1.0 for hallucinate) |
| E5 | N = 200, μ ~ U[0.2, 1.0], 5-fold CV grouped by episode |
| Episode cap | 2,500 steps; speed cap 3.0 m/s |
| Training seeds | 0 (main), 1 and 2 (replicates); the replicates use E0 + E1/E2 + E5 |
| Statistics | Crash rates with Wilson 95% CIs; ρ and gap closed with episode-bootstrap 95% CIs (10,000 resamples); φ vs Blind paired tests per grip: exact McNemar (crash), Wilcoxon signed-rank (ρ); across seeds mean ± SD. α = 0.05; the 4 grip levels are Holm-corrected |

## Hypotheses and thresholds

| ID | Prediction | Pass if |
|---|---|---|
| G0 | Grip is load-bearing | E0 Blind crash rate is non-decreasing as μ falls and ≥ 0.5 at μ = 0.4 |
| G1 | φ closes the Blind → Oracle gap | **≥ 30%** of the ρ gap at μ = 0.4 (seed 0), and the bootstrap CI excludes 0 |
| H2 | φ prevents low-grip crashes | At μ = 0.4: φ crash rate ≤ Blind crash rate − 0.30, McNemar p < 0.05 |
| H3 | Calibration | φ's cross-grip ρ variance ≥ 10× below Blind's. (The July value was 1.25×, and it is kept at 10× so the target can't be moved.) |
| H-transient | φ notices a sudden grip drop | E3: median settle time < 100 steps (1 s), and φ's survival after the drop > Blind's |
| H4 | The caution is caused by the belief | E4: hallucination lowers speed at μ = 1.0; blindfold crash rate ≈ Blind's (within 0.1); restore recovers to within 0.1 of φ |
| H1 | φ decodes grip | E5 φ grip R² ≥ 0.7 (reported regardless; supporting, not gating) |
| R1 | The effect replicates across training seeds | G1 and H2 hold for all three seeds |
| B1 | Adaptation beats robustness | A domain-randomized policy trained without grip information (same DAgger recipe, intrinsics fixed to nominal) has a higher crash rate than φ at μ = 0.4, **or** is ≥ 10% slower than φ at μ = 1.0 |
| G-hold | Map-agnostic | A model trained without 3 tracks (mco, silverstone, budapest) closes ≥ 50% as much of the ρ gap on those tracks as the main model does in distribution, at μ = 0.4 |
| T1 | Saturating tire (robustness, not trained on) | Under `friction_circle`, the ordering Blind ≥ φ ≥ Oracle in crash rate at μ = 0.4 holds |

## Predictions (direction)

- G0, H2 and T1: pass (the 10-episode E0 check already suggests a sharp crash boundary near μ = 0.6).
- G1: pass. H3: likely fail at 10×, as in July. Report the actual ratio.
- H1: uncertain. The July R² was 0.08 on the buggy pipeline. Expected higher now that the grip drop reaches the physics and μ is trained.
- B1: pass via speed. A grip-blind robust policy should learn to drive slowly everywhere.
- G-hold: pass.

---

## Addendum, 2026-11-01 22:31 UTC (commit time): post-hoc runs (registered before they ran)

**What happened.** The seed-0 results failed G1, H2 and H3, and they are reported as such: φ crashed *more* than Blind at μ = 0.4 (0.39 vs 0.31) and drove at ~2.13 m/s regardless of grip. G0 passed, H4's hallucination arm passed (believing μ = 0.4 at true μ = 1.0 slowed the car to the Oracle's 1.19 m/s), and E5 gave grip R² of 0.9999 for the encoder, 0.04 for history statistics, and ≈ 0 for φ. The replicate-seed suite was paused: replicating a configuration whose mechanism is known to fail is low value.

**Diagnosis (before the runs below).**
1. *Observability.* In the linear single-track model, μ only enters the understeer gradient. With f110_gym's parameters, K ≈ 0.0088/μ s²/m, so at 2 m/s the steady-state yaw gain at μ = 0.4 differs from μ = 1.0 by ~5%, below the ±20% motor-steering randomization. Grip is nearly unobservable from a 0.5 s history at these speeds.
2. *Action leakage.* φ was trained on oracle-driven rollouts, where low grip is revealed by the oracle's *own* slower driving. Under φ that cue is absent: a fixed point at high-grip behaviour (φ's 2.13 m/s exceeds every oracle speed).

**Post-hoc runs, labelled post hoc in all write-ups:**

| ID | Change | Isolates | Prediction |
|---|---|---|---|
| P1 | Same base policy; φ trained with 3 on-policy rounds (250 episodes, 10k steps each) after the oracle round | Action leakage | φ's speed falls to ≤ the Blind/Oracle range at μ = 1.0, and its μ = 1.0 crash rate drops to ≈ Blind's. E5 φ R² stays < 0.3 (observability limit). G1 still fails |
| P2 | Friction-circle tire for training *and* evaluation: Phase 1 DAgger + φ with on-policy rounds | Observability (μ now caps acceleration at μg, and cornering saturates) | E5 history R² > 0.3 and φ R² > P1's. G1 (≥ 30% gap closed at μ = 0.4) passes. φ crash rate at μ = 0.4 < Blind's |

Same E1/E2 (N = 100) and E5 (N = 200) protocol and the same statistics (tools/stats.py). If P2 passes, the replicate seeds, robust baseline and held-out tracks (R1–R3) are run on the P2 configuration. Otherwise they are run on the original configuration, as planned.

---

## Amendment 2, 2026-11-02 (before the reruns below): evaluation episodes were replays

**Problem found.** With the evaluation protocol inherited from July (start line, fixed physics, no observation noise), every seed on a given track replays the *same* deterministic episode. In every E1/E2 run so far, each (controller, grip, track) group of ~8 episodes has exactly **one** distinct outcome. So "N = 100" was **13 distinct episodes per cell**. Point estimates are unaffected as averages over tracks, but every CI and p-value computed so far treats copies as independent and is **invalid**. E0 (one track) had effectively N = 1 per grip. The July protocol had the same property.

**Change.** Each evaluation episode starts at a point along the lap drawn from its seed (`eval/harness.py`, `spawn_frac_for`). Every controller gets the same start for the same seed, so paired tests stay valid, and different seeds give different episodes. `--spawn start` reproduces the old protocol. `tools/stats.py` now reports the number of distinct outcomes per cell and warns on replication.

**Reruns (same hypotheses, thresholds and N as fixed above):** original configuration (E0, E1/E2, E3, E4, E5); its friction-circle evaluation (T1, N = 40); P1 (E1/E2, E5); P2 (E0, E1/E2, E3, E5). Earlier start-line results are kept under `*_startline/` and reported as superseded. The robustness suite (R0–R4) runs afterwards with the new protocol.

---

## Amendment 3, 2026-11-02 (before running): speed-matched control (B2)

**Why.** P2's φ is safer than Blind at low grip, but it is also slower at every grip (1.28 → 1.14 m/s vs Blind's ~1.97), and the Oracle shows that ~1.2 m/s is safe at μ = 0.4. Its safety could therefore come from *driving slowly* rather than from estimating grip. The robust baseline (R2) does not settle this either, because it drives faster (~1.6 m/s in validation).

**Control (B2).** The P2 base policy as Blind (nominal grip belief), with its commanded velocity capped (`--speed-cap`) at **1.15 m/s** (≈ φ's speed at μ = 0.4) and at **1.28 m/s** (≈ φ's speed at μ = 1.0). Friction-circle tire, same E1/E2 protocol (N = 100 per grip, random starts, paired seeds).

**Pre-registered readout.**

| Outcome at μ = 0.4 | Conclusion |
|---|---|
| Capped Blind (1.28 m/s) crash rate ≥ φ's + 0.10, McNemar p < 0.05 | φ's low-grip safety is **not** explained by speed alone: grip adaptation contributes |
| Capped Blind (1.15 m/s) crash rate within 0.05 of φ's | φ's safety is explained by its speed. The adaptation claim is limited to "speed is modulated by inferred grip", ~18% of the Oracle's modulation |
| In between | Report as partially explained by speed |

**Prediction.** At 1.15 m/s, capped Blind will be about as safe as φ (the Oracle is safe at 1.19). At 1.28 m/s, capped Blind will crash somewhat more than φ. So φ's benefit is mostly speed, with a small adaptive part.

---

## Amendment 4, 2026-11-02 (before running): longer history window instead of the high-speed test

**High-speed test dropped (not run).** The planned 3 → 5 m/s test needed an expert that can drive the tracks at speed. With a physics-based corner and braking speed profile (`experts/__init__.py`, `corner_speed`, off by default), the expert still could not lap the 0.63–0.76 m-wide tracks reliably above ~3.5 m/s (4 m/s: 1 of 8 laps; IMS oval failed at full grip). Making it work needs a better high-speed controller or wider tracks, which is future work.

**Why a longer window.** The current setup already has headroom: the Oracle drives 1.98 m/s at μ = 1.0 and is safe at μ = 0.4, while P2's φ hedges at 1.28 m/s because its grip estimate is weak (E5 R² 0.26 from 0.5 s). A longer history (k = 200 steps = 2 s) is the most direct way to make grip more readable. This is also HANDOFF item 4 (window ablation).

**Run (W).** P2 base policy (`runs/phase1_fc/final.pt`), φ retrained exactly as in P2 but with k = 200. Then E1/E2 (N = 100), E3, E5, and the speed-matched Blind control with caps set by a rule fixed now: **the cap equals φ_k200's own mean speed at μ = 1.0, and separately at μ = 0.4**.

**Predictions.**

| ID | Prediction | Pass if |
|---|---|---|
| W1 | Longer window, more grip information | E5 φ R² > 0.26 (P2's k = 50) |
| W2 | Less hedging | φ_k200's speed at μ = 1.0 > φ_k50's (1.28 m/s), with crash at μ = 0.4 ≤ 0.10 |
| W3 | Adaptation beats speed (the key test) | At μ = 0.4, Blind capped at φ_k200's μ = 1.0 speed crashes ≥ 0.10 more than φ_k200, McNemar p < 0.05 |

Expected: W1 and W2 pass. W3 is uncertain: it needs φ to be both faster at high grip and safe at low grip.

---

## Amendment 5, 2026-11-02 (before running): speed-matched control for the replicate seeds

Seen before writing this: seed 1's E1/E2 (φ crash 0.05 vs Blind 0.46 at μ = 0.4; φ speed 1.48 → 1.29 m/s). Not yet seen: any speed-matched run for seeds 1 or 2.

**Run.** For each replicate seed s ∈ {1, 2}: that seed's base policy as Blind, capped at **φ_s's own mean speed at μ = 1.0** (the amendment-4 rule), same E1/E2 protocol, paired with φ_s's episodes.

**Readout (as W3).** Adaptation beats speed for seed s if, at μ = 0.4, the capped Blind crashes ≥ 0.10 more than φ_s, McNemar p < 0.05. Reported per seed, alongside seed 0 (amendment 3: not met).

---

## Amendment 6, 2026-11-03 (before running): why φ cannot read grip, and the active-probe arm (Q)

**Diagnostic (already run, reported here in full).** `tools/phi_diagnostic.py` rolls out the P2 base policy (friction-circle tire, true grip uniform 0.2–1.0, other physics from the training range) with three grip beliefs, 240 episodes each, same seeds: the true grip (oracle), φ's estimate, and a *random* grip independent of the true one (no action leakage). A ridge probe on physical features of each 0.5 s window (peak acceleration and braking, lateral acceleration, yaw rate vs the kinematic yaw rate, speed error), grouped CV by episode:

| data | grip R² |
|---|---|
| random belief (actions carry no grip information) | **−0.02** |
| oracle belief | 0.97 (action leakage: the oracle's own speed reveals the grip) |
| φ's belief | 0.68 (φ's own speed choice, same leakage) |

So with leakage removed, the motion history contains essentially **no** grip information. Why: (1) this car is close to neutral steer, so below the limit grip barely changes the yaw response (steady cornering, μ 0.4 vs 1.0: −3% at 1.5 m/s, −5% at 2 m/s for the linear and friction-circle models); (2) the policy drives well inside the friction circle (99th-percentile acceleration 3–3.7 m/s², lateral ~2 m/s², braking ~0.1 m/s², vs μg = 3.9 at μ = 0.4). A Fiala brush tire, where grip bends the force curve below the limit (added to `envs/tire_models.py` as `brush`), did **not** help (random-belief R² −0.03; steady-state yaw change ≤ 1% at 2 m/s), because the car is near neutral steer and the yaw response doesn't show it. The brush tire is not used further. This also explains P2's φ R² of 0.26–0.34 and amendment 4's failure: it is not a learning problem, the information is not there.

**Fix tested in the diagnostic.** An *active probe*, as in traction-control friction estimation: every 0.5 s, on straights only (|steer| < 0.15 rad), add 2.0 m/s to the commanded speed for 0.1 s. f110's speed controller then asks for ~9.5 m/s², which the tire caps at μg. Random-belief data with the probe: peak acceleration 3.1 / 5.1 / 7.3 / 8.6 m/s² for grip bins 0.2–0.4 / … / 0.8–1.0, physical-feature R² **0.84** per 0.5 s window (0.997 per episode), episode lengths unchanged. φ's CNN trained on that data for 3000 steps reaches held-out R² **0.67** with proprioceptive inputs only (v, steering, v_des, steering_des, yaw rate, 2 actions), but 0.15 with all 115 channels (the 108 LiDAR channels swamp it). These numbers were seen before writing this amendment.

**Run (Q).** For each training seed s ∈ {0, 1, 2}, all three run regardless of seed 0's outcome: P2's base policy for that seed (unchanged), φ_Q retrained exactly as in P2 (oracle round + 3 on-policy rounds, same budget) except:
- `environment.probe` on (period 50 steps, 10 steps, +2.0 m/s, |steer| < 0.15), in φ training and in **every** evaluation, for every controller (Oracle, φ, Blind, capped Blind), so all controllers drive with the same probe;
- `networks.adaptation.input_channels: proprio`, k = 50.

Config `configs/retrain_phase2_fc_probe.yaml`, script `tools/probe_suite.sh`. Evaluation: E1/E2 (N = 100 per grip, random starts, paired seeds), E5 (N = 200, with the probe), and the speed-matched control: Blind (with the probe) capped at φ_Q's own mean speed at μ = 1.0 (amendment 4 rule), tested with `tools/speed_matched_test.py`.

**Predictions and pass rules (per seed; the claim needs all three seeds).**

| ID | Prediction | Pass if |
|---|---|---|
| Q1 | φ reads grip | E5 φ R² ≥ 0.5 (P2: 0.28 ± 0.05) |
| Q2 | φ modulates speed like the Oracle | φ speed at μ = 1.0 minus at μ = 0.4 ≥ 0.40 m/s (Oracle ~0.8; P2 φ 0.10–0.19) |
| Q3 | **Adaptation beats speed** (the key test, as W3 / amendment 5) | At μ = 0.4, Blind capped at φ_Q's μ = 1.0 speed crashes ≥ 0.10 more than φ_Q, exact McNemar p < 0.05 |
| Q4 | Still safe vs Blind | G1, H2 and H3 (as fixed in the original plan) |

Also reported, no threshold: the probe's cost (Oracle and Blind speed and crash rate with the probe vs P2's runs without it, same seeds and starts).

**Expected.** Q1 and Q2 pass. Q3 is the open question: it passes only if φ_Q drives near the Oracle's speed on high grip while staying safe on low grip. If Q3 fails, the paper keeps the amendment-5 conclusion (safety comes from speed). Either way the diagnostic stands as a result: passive proprioceptive grip adaptation is not possible in this simulator below the limit; it needs excitation.

### Amendment 6b, 2026-11-03 (after Q seed 0's E1/E2 and Q3, before running): cap sweep

**Seen before writing this:** Q seed 0's E1/E2, E5 and Q3 (pass). **Problem:** the probe pulse is added on top of the speed cap, so Blind capped at φ_Q's μ = 1.0 speed (2.02 m/s) actually averaged 2.12 m/s at μ = 1.0, faster than φ_Q (2.02). Q3 followed the registered rule, but it is not a true speed match.

**Run (all seeds, after the Q suite).** Blind (with the probe) at caps chosen so its *measured* speed at μ = 1.0 equals φ_Q's: cap_matched = cap − (measured capped-Blind speed − φ_Q speed) at μ = 1.0, from the Q3 run (seed 0: 2.02 − 0.10 = 1.92). Plus, for seed 0 only, a sweep at caps 1.3, 1.5 and 1.7 m/s to trace the speed-vs-safety frontier of a fixed speed limit.

**Readouts.**
- Q3m (per seed, same rule as Q3): at μ = 0.4, Blind at cap_matched crashes ≥ 0.10 more than φ_Q, McNemar p < 0.05.
- Frontier (seed 0, descriptive): for each cap, (speed at μ = 1.0, crash at μ = 0.4). φ_Q **dominates** a fixed limit if no cap achieves both speed at μ = 1.0 ≥ φ_Q's − 0.05 m/s and crash at μ = 0.4 ≤ φ_Q's + 0.05.

## Amendment 7, 2026-11-03 (before running): robustness of the probe arm

**Seen before writing this:** Q seeds 0 and 1 (E1/E2, E5, Q3); not seed 2, the cap sweep, or anything below. Script `tools/probe_robustness.sh`, run after the Q suite and the cap sweep.

| ID | Run | Prediction | Pass if |
|---|---|---|---|
| A1 | **Probe off:** seed-0 φ_Q, all controllers evaluated *without* the probe (E1/E2 N = 100, E5 N = 200) | φ_Q's grip reading depends on the probe | E5 φ R² < 0.3 and φ's speed drop from μ = 1.0 to 0.4 < 0.2 m/s (with the probe: 0.90 and 0.74) |
| A2 | **Held-out tracks:** φ_Q trained on the P2 held-out base policy (`runs/phase1_fc_holdout`) without mco/silverstone/budapest; E1/E2 on those 3 tracks with the probe; seed-0 main φ_Q on the same episodes | Transfers to unseen tracks | Held-out model's gap closed at μ = 0.4 ≥ 50% of the main model's (G-hold rule), and its speed drop ≥ 0.40 m/s (Q2 rule) |
| A3 | **E3 transient** with the probe (seed 0, N = 40): grip 1.0 → 0.4 mid-episode | φ_Q detects the drop | Median settle time within ±0.1 < 100 steps (H-transient rule; P2: 38 steps, but with a weak estimate) |

**Probe cost (descriptive, no threshold, no new runs):** Oracle and Blind mean speed, crash rate and progress with the probe (Q runs) vs without it (P2 runs), same base policies, seeds and starts, all three seeds.

## Amendment 8, 2026-11-04 (before running): sim-to-real configuration R

**Why.** Training did not match the car (docs/SIM_TO_REAL.md): control rate (C23), speed from wheel odometry rather than true speed, kinematic rather than measured yaw rate, commanded rather than applied steering, 40 Hz LiDAR with a 0.10 m margin, steering clip. And the expert drove 2.0 m/s × grip factor everywhere, which is not racing.

**Seen before writing this:** the diagnostic below, and the racing-expert lap check. No R training has been run.

- Racing expert (corner/braking speed profile, f = 0.6, a_b = 0.5·μ·g, top speed 3 m/s): 13 tracks × 2 starts, crashes 0/26 (grip 1.0, mean 2.91 m/s), 0/26 (0.6, 2.79), 2/26 (0.4, 2.61). f = 0.5 and 0.45 gave 4/26 and 2/26 at grip 0.4.
- Leakage-free diagnostic (random belief, P2 base policy, car sensors), 240 episodes each: with the probe, φ's architecture reaches held-out grip R² 0.52 (proprio), 0.52 (proprio + 10 front beams), 0.29 (all 115 channels); physical features 0.39. Without the probe: R² ≈ 0 (−0.03 physical features).

**Run (R), seeds 0, 1, 2, all regardless of seed 0's outcome.** `tools/real_suite.sh`: Phase 1 DAgger with `configs/real_phase1.yaml` (car sensors, probe on, racing expert; everything else as P2), then φ with `configs/real_phase2_probe.yaml` (as Q, but car sensors and `input_channels: proprio_front`), then E1/E2 (N = 100 per grip, all controllers with car sensors and the probe), E5 (N = 200), and the speed-matched Blind: capped at φ's μ = 1.0 speed, then rerun with the cap lowered by the measured excess (amendment 6b rule).

| ID | Prediction | Pass if (per seed; the claim needs all three) |
|---|---|---|
| R1 | φ reads grip through realistic sensors | E5 φ R² ≥ 0.4 |
| R2 | φ adapts speed like the Oracle | φ's speed drop μ 1.0 → 0.4 ≥ 50% of the Oracle's drop (the racing expert's own drop is smaller than before: ~0.3 m/s) |
| R3 | Adaptation beats a speed limit | At μ = 0.4, Blind matched on measured μ = 1.0 speed crashes ≥ 0.10 more than φ, McNemar p < 0.05 |
| R4 | Safe vs Blind | G1 and H2 as in the original plan |

Also reported, no threshold: mean speeds vs Q (racing should be faster), the base policy's validation crash rate, H3.

**Expected.** R1 passes but lower than Q (0.89–0.93), because the realistic sensors carry less information. R2 and R3 are uncertain: the racing expert slows down mostly in corners, so the speed gap between grips, and thus the room for adaptation, is smaller than in Q.

### Amendment 8b, 2026-11-04 (before rerunning): braking probe

**What happened.** The first R run (log `runs/real_attempt1_accel_probe.log`) was stopped during seed 0's Phase 1, after DAgger rounds 0–4 showed training crash rates of 0.73, 0.76, 0.81, 0.83, 0.60. No checkpoint or result from it is used. **Cause:** the +2.0 m/s probe on top of the racing expert's 3 m/s straights asks for 5 m/s just before corners. Expert alone, 40 training-randomized episodes each (same seed): old 2 m/s expert 28% crashes (1.76 m/s); racing expert + accelerating probe 50% (2.77 m/s); racing, no probe 40% (2.65); **racing + braking probe (−1.0 m/s) 25% (2.36 m/s)**; with cornering at 0.45 instead of 0.6: 30% (2.40) with the braking probe, 33% (2.62) without.

**Change.** Probe amplitude −1.0 m/s (a 0.1 s braking pulse every 0.5 s on straights; f110's speed controller then asks for ~19 m/s², above μg at every grip). Same period, duration and steering gate. Everything else in amendment 8 is unchanged, including φ inputs (proprio + front beams), the expert (0.6 / 0.5), predictions R1–R4 and their thresholds.

**Seen before writing this:** leakage-free diagnostic with car sensors and the braking probe, φ architecture, held-out R² **0.73** (proprio) and **0.68** (proprio + front beams), vs 0.52 / 0.52 with the accelerating probe; physical-feature ridge 0.25 per window, 0.48 per episode.

## Amendment 9, 2026-11-04 (before running): robustness of configuration R

**Seen before writing this:** R E1/E2, E5 and speed-matched results for seeds 0–2 (section 6 of RESULTS). Nothing below. Script `tools/real_robustness.sh`; all evaluations use the seed-0 R models unless noted, N = 100 paired episodes per cell, Oracle / φ / Blind.

**S: slip-model sensitivity (evaluation only, no retraining).** The R models were trained with one wheel-slip model (wheel spins up or locks towards the command at 40 m/s², relaxes back in 30 ms). The car's real behaviour is unknown. Re-evaluate at μ ∈ {0.6, 0.4} with four alternatives: spin-up 15 m/s² (slow), 120 m/s² (fast), relaxation 0.1 s, and no slip (odometry = true speed).

| ID | Pass if (per variant) |
|---|---|
| S1 | At μ = 0.4, φ crash ≤ Blind − 0.30 (McNemar p < 0.05) |
| S2 | At μ = 0.6, φ crash ≤ Blind − 0.20 (McNemar p < 0.05) |

Prediction: both hold for every variant. Grip shows in odometry through slip (spin variants) or directly through the capped deceleration (no slip), and φ also sees the front LiDAR beams. The variant most likely to fail is slow spin-up, where the wheel signal is weakest.

**A-R: robustness checks of amendment 7, repeated for R.**

| ID | Run | Pass if |
|---|---|---|
| A1-R | Probe off at test time (all controllers), E1/E2 all grips + E5 N = 200 | E5 φ R² < 0.4 (below R1's threshold): the grip reading needs the probe |
| A2-R | Held-out tracks: Phase 1 and φ retrained under R without mco/silverstone/budapest (seed 0), E1/E2 on those 3 tracks; the main seed-0 R models on the same episodes | Held-out model's ρ gap closed at μ = 0.4 ≥ 50% of the main model's, and its H2 holds |
| A3-R | E3 grip step 1.0 → 0.4 (N = 40) | Median settle < 100 steps |
