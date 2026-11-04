# Results: retrained pipeline (November 2026)

All numbers come from the rebuilt, bug-fixed pipeline on the real f1tenth_gym (commit 4fdb9c7). How it was trained: [RETRAINING.md](RETRAINING.md). What was predicted before each run: [PREREGISTRATION_NOV2026.md](PREREGISTRATION_NOV2026.md) (original plan, addendum for P1/P2, amendment 2 for the evaluation protocol). Raw outputs: `results/retrain_nov2026/`. Every run has `episodes.csv`, `summary.json` and `provenance.json` (git commit, library versions, f110_gym commit, checkpoint hashes). Statistics: `tools/stats.py` (Wilson CIs for crash rates, episode-bootstrap CIs, exact McNemar and Wilcoxon signed-rank tests on paired episodes, Holm-corrected across the 4 grip levels).

**Evaluation protocol (amendment 2).** Every episode starts at a point along the lap drawn from its seed; all controllers get the same start for the same seed. An earlier version of this page, like the July poster, used start-line episodes. Those turned out to be deterministic replays: N = 100 was really 13 distinct episodes per cell, so their CIs and p-values were invalid. Those runs are kept under `*_startline/` and are superseded by the numbers below. The conclusions did not change.

**Not comparable one-to-one with the July poster**: different tracks (drivable scale), base-policy training (DAgger), checkpoints, evaluation protocol, and seven pipeline bugs fixed (C16–C22).

## Summary

| Configuration | φ crash at μ = 0.4 (Blind / Oracle) | ρ gap closed at μ = 0.4 | Variance ratio Blind/φ | φ speed μ = 1.0 → 0.4 (Oracle 1.98 → 1.19) | φ grip R² (E5) | G1 / H2 / H3 |
|---|---|---|---|---|---|---|
| **Original** (linear tire, φ on oracle data) | 0.39 (0.32 / 0.00) | **−16%** [−24, −7] | 0.83× | 2.13 → 2.11 | −0.02 | FAIL / FAIL / FAIL |
| Original, evaluated on friction-circle tire (T1) | 0.65 (0.55 / 0.00) | −13% [−22, −7] | 0.87× | 2.13 → 2.02 | n/a | FAIL / FAIL / FAIL |
| **P1** (linear tire, on-policy φ), post hoc | 0.07 (0.32 / 0.00) | 47% [40, 54] | 2.45× | **1.54 → 1.53** (constant) | 0.00 | PASS / FAIL / FAIL |
| **P2** (friction-circle tire, on-policy φ), post hoc: 3 seeds | **0.04 ± 0.03** (0.44 / ~0.03) | **83% ± 7** | **16.2× ± 5.9** | ~1.35 → ~1.19 | **0.28 ± 0.05** | **PASS / PASS / PASS** (all seeds) |
| P2, held-out tracks (never trained on) | 0.02 (0.49 / 0.00) | 89% [84, 93] | 15.9× | 1.28 → 1.18 | n/a | PASS / PASS / PASS |
| **Q: P2 + active grip probe + proprioceptive φ** (amendment 6): 3 seeds | **0.06 ± 0.03** (0.45 / 0.04) | **84% ± 3** | 3.4× (Oracle 5.5×) | **~2.03 → 1.28** | **0.91 ± 0.02** | **PASS / PASS / FAIL** (all seeds); beats a speed-matched Blind on every seed (section 4) |
| **R: realistic car sensors + braking probe + racing expert** (amendment 8): 3 seeds, base policy retrained | **0.35 ± 0.06** (0.85 / 0.04) | **55% ± 5** | 2.0× | **2.55 → 2.38** (Oracle 2.56 → 2.40) | **0.86 ± 0.02** | **PASS / PASS / FAIL**; beats speed-matched Blind on every seed; at μ = 0.6: 0.02 vs 0.44 (section 6) |
| W: P2 with a 2 s window | 0.08 (0.44 / 0.05) | 65% [52, 80] | 3.4× | 1.17 → 1.15 (constant) | 0.02 | PASS / PASS / FAIL |
| **Controls (P2 setup)** | | | | | | |
| Robust baseline (no grip info) | 0.16 | n/a | n/a | 1.60 → 1.59 | n/a | φ safer, p = 0.012, but 25% slower |
| **Blind capped at φ's speed** (3 seeds) | **0.06 / 0.07 / 0.01** (φ: 0.07 / 0.05 / 0.01) | n/a | n/a | = φ's | n/a | **as safe as φ, every seed** |

**The finding in one paragraph.** The base policy uses a correct grip belief perfectly: Oracle has ≈ 0 crashes at every grip and slows from 1.98 to 1.19 m/s, and injecting a false low-grip belief slows it by exactly that much (E4). Whether the adaptation module φ can *supply* that belief depends on the simulator. In f1tenth_gym's stock linear tire, grip does not measurably change the car's motion at these speeds (history R² ≈ 0), and φ cannot estimate it. Trained the July way (on oracle-driven data), φ is **worse than not adapting at all**; trained on its own rollouts, it becomes safe only by driving uniformly slowly. With a saturating friction-circle tire, grip becomes partly observable (R² 0.28 ± 0.05 over 3 seeds). φ then passes all three pre-registered checks against Blind on every seed (crash 0.04 vs 0.44 at μ = 0.4) and transfers to unseen tracks (89% gap closed). **But on every seed, Blind capped at φ's own top speed is just as safe.** φ's safety comes from driving at a safe speed (which it does learn, with some grip-dependent modulation), not from grip estimation adding safety beyond that.

**Defensible claims for the paper.**

1. A grip-aware RMA base policy is safe *given* the grip, and its caution is causally driven by its grip belief (Oracle, E4).
2. In the stock F1TENTH simulator, grip is not observable from proprioception at these speeds, so RMA-style grip adaptation cannot work there. July-style training makes it actively harmful (action leakage), which explains the July E5 result.
3. A saturating tire makes grip partly observable. φ then learns a safe, mildly grip-modulated speed that replicates across seeds and transfers to unseen tracks.
4. **Limitation:** at a 3 m/s cap on these tracks, a fixed speed cap matches φ's safety. A benefit *of adaptation itself* would need a regime where uniform slowness is costly (higher speeds, a lap-time objective) and better grip estimates (R² 0.28 now), or measurements on the real car. That is the advisor's suggested direction (learning online on the real car).

## 1. Pre-registered experiments, original configuration

Linear tire. Base policy: DAgger checkpoint. φ: k = 50, trained on oracle-driven rollouts (as in July). N = 100 paired episodes per cell, 13 tracks round-robin, random starts.

| controller | μ = 1.0 | 0.8 | 0.6 | 0.4 |
|---|---|---|---|---|
| **Crash rate** [95% CI] | | | | |
| Oracle | 0.00 [0.00, 0.04] | 0.02 | 0.01 | 0.00 [0.00, 0.04] |
| φ-RMA | 0.06 [0.03, 0.12] | 0.11 | 0.16 | 0.39 [0.30, 0.49] |
| Blind | 0.00 [0.00, 0.04] | 0.02 | 0.10 | 0.32 [0.24, 0.42] |
| **Mean speed** (m/s) | | | | |
| Oracle | 1.98 | 1.78 | 1.52 | 1.19 |
| φ-RMA | 2.13 | 2.13 | 2.12 | 2.11 |
| Blind | 1.98 | 1.98 | 1.98 | 1.97 |

| Hypothesis | Result | Verdict |
|---|---|---|
| G0: grip is load-bearing (E0, Blind, aut_tight, N = 40) | Crash rate 0.03, 0.03, **0.53, 0.68, 1.00** at μ = 1.0, 0.8, 0.6, 0.4, 0.2 | **PASS** |
| G1: φ closes ≥ 30% of the ρ gap at μ = 0.4 | **−16%** [−24%, −7%]: φ is further from the Oracle than Blind is | **FAIL** |
| H2: φ crash ≤ Blind − 0.30 at μ = 0.4 | 0.39 vs 0.32, the wrong direction (McNemar, Holm p = 0.047) | **FAIL** |
| H3: cross-grip ρ variance Blind/φ ≥ 10× | 0.83× [0.71, 1.02] | **FAIL** |
| H4: belief causes caution (E4, N = 100) | Hallucinating μ = 0.4 at true μ = 1.0: 2.13 → **1.19 m/s** (= Oracle's μ = 0.4 speed), 0 crashes. Blindfold crash 0.32 = Blind's 0.32. Restore = φ (0.39) | Hallucination arm **PASS**; restore uninformative (φ ≈ constant) |
| H-transient (E3) | "Settles" in 0 steps, but φ's decoded grip is ≈ constant, so it sits trivially inside the band | **Uninformative** |
| H1: φ decodes grip, R² ≥ 0.7 (E5) | Encoder z 0.9999; history −0.02; φ −0.02 | **FAIL** |
| T1: Blind ≥ φ ≥ Oracle at μ = 0.4 on the friction-circle tire (N = 40) | Blind 0.55, **φ 0.65**, Oracle 0.00 | **FAIL** |

**Why it fails** (diagnosed before the post-hoc runs; see the addendum):

1. *Observability.* In f110_gym's linear single-track model, μ only enters the understeer gradient (K ≈ 0.0088/μ s²/m). At 2 m/s, the steady-state yaw gain at μ = 0.4 differs from μ = 1.0 by ~5%, which is less than the ±20% steering-scale randomization. The E5 history probe (R² −0.02; 0.04 in the start-line run) confirms grip is invisible in 0.5 s of motion.
2. *Action leakage.* φ trained on oracle-driven rollouts can read grip from the oracle's own slower driving. That cue is gone when φ drives, leaving a fixed point at "high-grip" behaviour: φ's 2.13 m/s is faster than the Oracle at *any* grip.

This is the same signature as July's E5 (φ R² 0.08).

## 2. Post-hoc remedies (registered before running)

### P1: on-policy φ (linear tire, same base policy)

φ was trained with the oracle round, then 3 on-policy rounds (250 episodes and 10k gradient steps each), in which the car drives on φ's own estimate as at deployment.

| μ | crash φ / Blind / Oracle | speed φ / Blind / Oracle (m/s) | gap closed (ρ) [95% CI] | McNemar p (Holm) |
|---:|---|---|---|---:|
| 1.0 | 0.00 / 0.00 / 0.00 | **1.54** / 1.98 / 1.98 | n/a | 1 |
| 0.8 | 0.00 / 0.02 / 0.02 | 1.53 / 1.98 / 1.78 | 61% [51%, 72%] | 1 |
| 0.6 | 0.01 / 0.10 / 0.01 | 1.53 / 1.98 / 1.52 | 63% [57%, 68%] | 0.012 |
| 0.4 | **0.07** / 0.32 / 0.00 | 1.53 / 1.97 / 1.19 | 47% [40%, 54%] | 2.4e-7 |

Variance ratio Blind/φ 2.45× [1.89, 3.30]. G1 passes, H2 fails (a 0.25 reduction vs the 0.30 threshold), and H3 fails. **The mechanism is not adaptation.** φ drives at a constant ~1.53 m/s at every grip and decodes nothing about grip (R² 0.00). Removing action leakage turned φ from over-confident into uniformly cautious: it learned the speed that is safest on average over the training grips, at a 22% speed cost at μ = 1.0. On the linear tire, the honest comparison for φ is therefore a robust policy, not Blind.

### P2: friction-circle tire (observability)

Everything retrained and evaluated under the saturating friction-circle tire: Phase 1 DAgger base policy (validation: 1/13 tracks crash at every grip, aut_tight, Oracle included), then φ with the oracle round plus 3 on-policy rounds.

| μ | crash φ / Blind / Oracle | speed φ / Blind / Oracle (m/s) | gap closed (ρ) [95% CI] | McNemar p (Holm) |
|---:|---|---|---|---:|
| 1.0 | **0.00** / 0.11 / 0.11 | 1.28 / 1.97 / 1.97 | n/a | 0.002 |
| 0.8 | 0.03 / 0.11 / 0.09 | 1.23 / 1.97 / 1.78 | −9% [−27%, 10%] | 0.008 |
| 0.6 | 0.00 / 0.13 / 0.07 | 1.18 / 1.97 / 1.52 | 85% [78%, 91%] | 7.3e-4 |
| 0.4 | **0.07** / 0.44 / 0.05 | 1.14 / 1.92 / 1.19 | 85% [76%, 91%] | 5.8e-11 |

Variance ratio Blind/φ **14.7×** [8.0, 31.2]. E5 grip R²: encoder 0.998, **history 0.23**, **φ 0.26** (linear tire: −0.02 and −0.02). The start-line E5 gave 0.37 and 0.36.

- **G1, H2 and H3 pass** (post hoc). φ's crash rate at μ = 0.4 matches the Oracle's (0.07 vs 0.05) against Blind's 0.44.
- P2 predictions: φ R² > P1's **held** (0.26 vs 0.00). History R² > 0.3 **failed** on the corrected protocol (0.23; it passed at 0.37 on the superseded start-line run). H1 (R² ≥ 0.7) fails.
- **E3 (transient)**: after a μ 1.0 → 0.4 step, φ's decoded grip settles within ±0.1 in a median of **38 steps (0.38 s at 100 Hz; first reported as 0.76 s, bug C23)**, 39/39 episodes. Unlike the linear configuration, this is a real detection, and it passes H-transient (< 100 steps).
- **Partial adaptation plus caution.** φ's speed falls with grip (1.28 → 1.14 m/s), about 18% of the Oracle's 1.98 → 1.19 swing. It is still 35% slower than the Oracle at μ = 1.0. Part of the gap closed is uniform caution.
- **E0** for this base policy on aut_tight: crash rate 0.68, 0.68, 0.85, 0.98, 1.00, monotone (PASS), but high even at μ = 1.0, because aut_tight is the track this base policy fails. A post-hoc E0 on three other tracks is in section 3.

**Interpretation.** With a tire that saturates, grip becomes partly observable from 0.5 s of motion (R² ≈ 0.25), and the adaptation module uses it, which is the mechanism the July story assumed. In the stock f1tenth_gym tire it is essentially absent. This supports the advisor's point (Oct 31) that the tire model decides whether the method can work at all, and that adapting online on the real car may be necessary.

## 3. Controls and robustness (friction-circle configuration)

### R2: robust baseline (B1)

Same DAgger recipe and tire, but μ only ever sees the nominal physics vector, so the policy gets no grip information. Paired with P2's φ episodes (same seeds and starts):

| μ | crash φ / robust | McNemar p | speed φ / robust (m/s) |
|---:|---|---:|---|
| 1.0 | 0.00 / 0.01 | 1 | 1.28 / 1.60 |
| 0.8 | 0.03 / 0.01 | 0.62 | 1.23 / 1.60 |
| 0.6 | 0.00 / 0.05 | 0.062 | 1.18 / 1.59 |
| 0.4 | **0.07 / 0.16** | **0.012** | 1.14 / 1.59 |

B1 **passes** on its crash criterion. But the robust policy is 25% faster at every grip: neither is better on both speed and safety.

### B2: speed-matched Blind (amendment 3, the decisive control)

The P2 base policy as Blind, with its commanded speed capped at φ's own speeds:

| μ | crash φ | Blind capped at 1.15 m/s | Blind capped at 1.28 m/s |
|---:|---:|---:|---:|
| 1.0 | 0.00 | 0.00 | 0.01 |
| 0.8 | 0.03 | 0.00 | 0.01 |
| 0.6 | 0.00 | 0.00 | 0.06 (p = 0.031 vs φ) |
| 0.4 | 0.07 | **0.05** (p = 0.5) | **0.06** (p = 1) |

Pre-registered readout: at μ = 0.4, Blind capped at 1.15 m/s is within 0.05 of φ, so **φ's low-grip safety is explained by its speed**. φ's only measurable edge over the faster (1.28 m/s) cap is at μ = 0.6 (0.00 vs 0.06). The adaptation claim is therefore limited to *grip-dependent speed modulation* (1.28 → 1.14 m/s, ~18% of the Oracle's), with no safety benefit beyond what a fixed slower speed gives at this speed cap. This matches the amendment-3 prediction.

### Post-hoc E0 on more tracks (friction-circle base policy, Blind, N = 40, random starts)

| track | μ = 1.0 | 0.8 | 0.6 | 0.4 | 0.2 | G0 |
|---|---:|---:|---:|---:|---:|---|
| sochi_tight | 0.00 | 0.00 | 0.00 | 0.30 | 1.00 | PASS |
| sepang_tight | 0.00 | 0.00 | 0.25 | 0.28 | 1.00 | PASS |
| ims_tight (oval) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | not met: no corner needs the grip |

Whether grip is load-bearing depends on the track's tightest corners, so E0 should be reported across tracks, not only aut_tight.

### W: 2-second history window (amendment 4)

The P2 base policy, with φ retrained exactly as in P2 but with k = 200 steps (2 s) instead of 50. It replaces the high-speed test, which was infeasible: the expert could not lap the narrow tracks above ~3.5 m/s.

| μ | crash φ_k200 / Blind / Oracle | speed φ_k200 (φ_k50) | Blind capped at 1.17 m/s: crash (McNemar p vs φ_k200) |
|---:|---|---|---|
| 1.0 | 0.01 / 0.11 / 0.11 | **1.17** (1.28) | 0.00 (1) |
| 0.8 | 0.01 / 0.11 / 0.09 | 1.16 (1.23) | 0.00 (1) |
| 0.6 | 0.01 / 0.13 / 0.07 | 1.16 (1.18) | 0.00 (1) |
| 0.4 | 0.08 / 0.44 / 0.05 | 1.15 (1.14) | 0.05 (0.55) |

E5 grip R²: φ_k200 **0.02** (φ_k50 0.26); history probe −0.07. E3: "settles" in 0 steps, which is trivial because the estimate is constant. Gap closed at μ = 0.4: 65% [52, 80]. Variance ratio 3.4×.

| Prediction | Result |
|---|---|
| W1: φ R² > 0.26 | **FAIL** (0.02) |
| W2: faster at μ = 1.0 than φ_k50, crash at μ = 0.4 ≤ 0.10 | **FAIL** (1.17 < 1.28 m/s) |
| W3: Blind capped at φ's μ = 1.0 speed crashes ≥ 0.10 more than φ at μ = 0.4 | **FAIL** (0.05 vs 0.08) |

With the longer window, φ learned essentially nothing about grip and fell back to one cautious speed (~1.16 m/s) everywhere. That is safe against Blind but no better than simply capping Blind's speed. The most likely reason is optimization: a 4× larger input (200 × 115) with the same data and gradient budget. Either way, a longer window by itself is not a fix.

### R1: replicate training seeds (P2 configuration)

Seeds 1 and 2 retrain everything from scratch (Phase 1 DAgger base policy, then φ with the oracle round plus 3 on-policy rounds), with the same E1/E2 (N = 100, random starts) and E5 (N = 200) protocol. Base-policy validation crash rate: seed 1 2.6%, seed 2 5.1% (seed 0 7.7%).

| | seed 0 | seed 1 | seed 2 | mean ± SD |
|---|---|---|---|---|
| φ crash at μ = 0.4 | 0.07 | 0.05 | 0.01 | **0.04 ± 0.03** |
| Blind crash at μ = 0.4 | 0.44 | 0.46 | 0.41 | 0.44 ± 0.03 |
| McNemar p (Holm), μ = 0.4 | 6×10⁻¹¹ | 4×10⁻¹² | 7×10⁻¹² | |
| Gap closed at μ = 0.4 | 85% | 76% | 89% | **83% ± 7** |
| Gap closed at μ = 0.6 | 85% | 84% | 79% | 83% ± 3 |
| Variance ratio Blind/φ | 14.7× | 11.2× | 22.7× | 16.2× ± 5.9 |
| φ speed μ = 1.0 → 0.4 (m/s) | 1.28 → 1.14 | 1.48 → 1.29 | 1.29 → 1.14 | |
| E5 φ grip R² | 0.26 | 0.34 | 0.24 | 0.28 ± 0.05 |
| G1 / H2 / H3 | PASS ×3 | PASS ×3 | PASS ×3 | |

**R1 (G1 and H2 hold for all three seeds): PASS.** The P2 effect against Blind is not a single-seed artifact, and the partial grip decoding (R² ≈ 0.28) replicates. Speeds differ between seeds: seed 1's φ is faster on good grip and slows more (0.19 m/s), while seeds 0 and 2 are slower and flatter. Whether any seed's φ beats a speed-matched Blind is tested by amendment 5 (below). Gap closed at μ = 0.8 is unstable across seeds (−21% to +53%), because the Blind–Oracle ρ gap there is small.

### R3: held-out tracks (G-hold)

Phase 1 and φ retrained without mco_tight, silverstone_tight and budapest_tight (10 training tracks), then evaluated only on those 3 tracks. The main model, which trained on them, is evaluated on the same episodes for comparison. Base-policy validation of the held-out model: **0/39 crashes** at grip 1.0/0.6/0.4 on all 13 tracks, including the 3 unseen ones.

| μ = 0.4, 3 unseen tracks | held-out model | main model (trained on them) |
|---|---|---|
| crash φ / Blind / Oracle | **0.02** / 0.49 / 0.00 | 0.02 / 0.46 / 0.00 |
| McNemar p (Holm) φ vs Blind | 6×10⁻¹⁴ | 5×10⁻¹³ |
| gap closed [95% CI] | **89%** [84, 93] | 88% [81, 92] |
| variance ratio Blind/φ | 15.9× | 11.4× |
| φ speed μ = 1.0 → 0.4 | 1.28 → 1.18 | 1.25 → 1.14 |

**G-hold: PASS.** The held-out model closes 101% as much of the gap on unseen tracks as the main model does on tracks it trained on (threshold ≥ 50%). The policy and φ use only LiDAR and motion, never the map, and they transfer to new circuits.

### Amendment 5: speed-matched control for seeds 1 and 2

Each seed's base policy as Blind, capped at that seed's φ speed at μ = 1.0, paired with φ's episodes:

| μ = 0.4 | φ crash | capped-Blind crash | McNemar p | speed φ / capped (m/s) |
|---|---:|---:|---:|---|
| seed 0 (amendment 3, cap 1.28) | 0.07 | 0.06 | 1 | 1.14 / 1.26 |
| seed 1 (cap 1.48) | 0.05 | 0.07 | 0.69 | 1.29 / 1.46 |
| seed 2 (cap 1.29) | 0.01 | 0.01 | 1 | 1.14 / 1.28 |

**Readout: not met for any seed** (needed capped Blind ≥ 0.10 worse than φ, p < 0.05). Across all three seeds, a non-adaptive car that never exceeds φ's own top speed is as safe as φ at every grip level. The grip-related crash cliff for this base policy lies between ~1.5 and ~1.9 m/s, so any speed cap below it removes most of the risk. φ's grip-dependent slowing (0.10–0.19 m/s, roughly 13–24% of the Oracle's 0.79 m/s swing) adds no measurable safety on top.


## 4. Why φ could not read grip, and the active-probe fix (amendments 6, 6b; post hoc, registered before running)

### Diagnosis: without excitation, grip is not in the motion history

`tools/phi_diagnostic.py` drives the P2 base policy (friction-circle tire, true grip uniform 0.2–1.0, other physics from the training range) with a *random* grip belief, independent of the true grip, so the car's own actions carry no grip information. A ridge probe on physical features of each 0.5 s window, cross-validated by episode, 240 episodes per row:

| driving | tire | grip R² |
|---|---|---|
| random belief | friction circle | **−0.02** |
| random belief | Fiala brush (`tire_model: brush`) | −0.03 |
| oracle belief | friction circle | 0.97 (action leakage) |
| φ's belief | friction circle | 0.68 (action leakage) |
| random belief + probe | friction circle | **0.84** (0.997 per episode) |

Why: the car is close to neutral steer, so below the limit grip barely changes the yaw response (steady cornering, μ 0.4 vs 1.0: −3% at 1.5 m/s and −5% at 2 m/s for the linear and friction-circle tires; ≤ 1% at 2 m/s for the brush tire). And the policy stays well inside the friction circle: 99th-percentile acceleration 3–3.7 m/s², lateral ~2 m/s², vs μg = 3.9 m/s² at μ = 0.4. **This explains every earlier φ result**: the original φ read the oracle's speed (leakage); P1 and the k = 200 φ settled on one cautious speed; P2's R² ≈ 0.28 came from leakage and from the lowest grips.

### Fix: active grip probe + proprioceptive φ (Q)

Every 50 steps (0.5 s), for 10 steps (0.1 s), the commanded speed gets +2.0 m/s while |steer| < 0.15 rad. f110's speed controller then requests ~9.5 m/s², which the tire caps at μg. The probe runs for **every** controller, in training and evaluation. φ_Q takes only the 7 proprioceptive channels (offline R² 0.67 vs 0.15 with all 115). Everything else as in P2, including the base policies of seeds 0–2. Config `configs/retrain_phase2_fc_probe.yaml`, script `tools/probe_suite.sh`, results `results/retrain_nov2026/probe/seed{0,1,2}/`.

**E1/E2** (N = 100 paired episodes per cell; crash rate / mean speed in m/s):

| seed | controller | μ = 1.0 | 0.8 | 0.6 | 0.4 |
|---|---|---|---|---|---|
| 0 | Oracle | 0.11 / 2.12 | 0.08 / 1.92 | 0.08 / 1.63 | 0.06 / 1.27 |
| 0 | **φ_Q** | 0.09 / 2.02 | 0.07 / 1.85 | 0.02 / 1.57 | **0.07** / 1.28 |
| 0 | Blind | 0.11 / 2.12 | 0.12 / 2.11 | 0.14 / 2.08 | 0.46 / 1.99 |
| 1 | Oracle | 0.10 / 2.11 | 0.09 / 1.92 | 0.02 / 1.63 | 0.00 / 1.27 |
| 1 | **φ_Q** | 0.10 / 2.06 | 0.07 / 1.91 | 0.04 / 1.63 | **0.02** / 1.29 |
| 1 | Blind | 0.10 / 2.11 | 0.11 / 2.11 | 0.17 / 2.07 | 0.47 / 1.99 |
| 2 | Oracle | 0.02 / 2.11 | 0.08 / 1.91 | 0.08 / 1.62 | 0.06 / 1.26 |
| 2 | **φ_Q** | 0.02 / 2.00 | 0.04 / 1.87 | 0.08 / 1.60 | **0.08** / 1.28 |
| 2 | Blind | 0.02 / 2.11 | 0.09 / 2.11 | 0.11 / 2.08 | 0.43 / 1.99 |

**Pre-registered readouts** (amendment 6; the claim needs all three seeds):

| | seed 0 | seed 1 | seed 2 | verdict |
|---|---|---|---|---|
| Q1: E5 φ grip R² ≥ 0.5 | 0.90 | 0.93 | 0.89 | **PASS** (P2: 0.28 ± 0.05) |
| Q2: φ speed drop μ 1.0 → 0.4 ≥ 0.40 m/s | 0.74 | 0.77 | 0.72 | **PASS** (Oracle 0.84–0.85; P2 0.10–0.19) |
| Q3: Blind capped at φ's μ = 1.0 speed crashes ≥ 0.10 more at μ = 0.4, p < 0.05 | 0.46 vs 0.07, p = 4×10⁻¹² | 0.47 vs 0.02, p = 6×10⁻¹⁴ | 0.43 vs 0.08, p = 6×10⁻¹¹ | **PASS** |
| G1: ρ gap closed at μ = 0.4 [95% CI] | 87% [81, 91] | 82% [76, 87] | 83% [76, 89] | **PASS** |
| H2: φ crash ≤ Blind − 0.30 at μ = 0.4 (Holm p) | 0.07 vs 0.46 (1.5×10⁻¹¹) | 0.02 vs 0.47 (< 10⁻¹²) | 0.08 vs 0.43 (2×10⁻¹⁰) | **PASS** |
| H3: cross-grip ρ variance Blind/φ ≥ 10× | 3.7× | 3.3× | 3.2× | **FAIL** |

**On H3.** With the probe, even the Oracle reaches only 5.4–5.6× (seeds 0–1): each pulse loads the tires near the limit at every grip, which changes what ρ measures. φ_Q gets ~65% of the Oracle's ratio. P2 passed H3 (14.7×) because its φ drove uniformly slowly. Reported as a failure; the threshold is not changed.

### Amendment 6b: speed matched on *measured* speed, and a cap sweep

The probe adds on top of the cap, so the Q3 "capped" Blind drove faster than φ_Q (seed 0: 2.12 vs 2.02 m/s at μ = 1.0). Rerun with the cap lowered by that excess:

| μ = 0.4 | φ_Q crash | matched Blind crash | McNemar p | speed at μ = 1.0, φ_Q / Blind |
|---|---:|---:|---:|---|
| seed 0 (cap 1.93) | 0.07 | 0.37 | 2×10⁻⁹ | 2.02 / 2.05 |
| seed 1 (cap 2.01) | 0.02 | 0.47 | 6×10⁻¹⁴ | 2.06 / 2.11 |
| seed 2 (cap 1.89) | 0.08 | 0.33 | 6×10⁻⁸ | 2.00 / 2.01 |

**Q3m: PASS on every seed.** Seed 1's cap did not bind (Blind's own commands stay below 2.01), so its match is 0.05 m/s off; seed 2's is within 0.01 m/s.

**Frontier of a fixed speed limit** (seed 0, Blind with the probe):

| | speed at μ = 1.0 | crash at μ = 0.4 |
|---|---:|---:|
| **φ_Q** | **2.02** | **0.07** |
| Blind, cap 1.93 | 2.05 | 0.37 |
| Blind, cap 1.7 | 1.82 | 0.12 |
| Blind, cap 1.5 | 1.63 | 0.07 |
| Blind, cap 1.3 | 1.43 | 0.07 |

**φ_Q dominates** (registered rule: no cap gets both speed ≥ 1.97 m/s and crash ≤ 0.12). A fixed limit that is as safe at low grip costs 0.4–0.6 m/s (19–29%) on high grip.

### Cost of the probe (descriptive)

Same base policies, seeds and starts, without (P2 runs) → with the probe (Q runs):

| seed | Blind crash μ = 1.0 | Blind crash μ = 0.4 | Oracle crash μ = 0.4 | mean speed change |
|---|---|---|---|---|
| 0 | 0.11 → 0.11 | 0.44 → 0.46 | 0.05 → 0.06 | +0.07 to +0.15 m/s |
| 1 | 0.09 → 0.10 | 0.46 → 0.47 | 0.00 → 0.00 | +0.07 to +0.14 m/s |
| 2 | 0.02 → 0.02 | 0.41 → 0.43 | 0.06 → 0.06 | +0.07 to +0.14 m/s |

Crash rates move by at most 0.02; the pulses add speed, and distance covered per episode rises 4–8%. Not measured: tire wear, energy, ride smoothness, which matter on the real car.

## 5. Robustness of the probe arm (amendment 7)

| ID | Result | Verdict |
|---|---|---|
| A1: probe **off** at test time (seed-0 φ_Q, all controllers, E1/E2 N = 100, E5 N = 200) | φ_Q falls back to a constant ~1.2 m/s (1.20 → 1.16, a 0.04 m/s drop) and its grip R² falls to 0.24 (history probe 0.03). It stays safe (crash 0.00–0.07) by driving slowly, exactly like P2 | **PASS** (R² < 0.3, drop < 0.2 m/s): φ_Q's adaptation comes from the probe |
| A3: E3 grip step 1.0 → 0.4 with the probe (seed 0, N = 40) | Decoded grip settles within ±0.1 in a median of **77 steps (0.77 s)**, 39/39 episodes | **PASS** (< 100 steps) |
| A2: held-out tracks: φ_Q trained on the P2 held-out base policy without mco/silverstone/budapest, evaluated only on those 3 (E1/E2 N = 100, with the probe) | Crash at μ = 0.4: φ 0.03 vs Blind 0.56 vs Oracle 0.00 (Holm p < 10⁻¹⁴); speed 2.04 → 1.31 m/s; gap closed **80%** [73, 86] vs **87%** [82, 92] for the seed-0 main model, which trained on those tracks | **PASS** (92% of the main model's gap, ≥ 50%; speed drop 0.73 ≥ 0.40 m/s) |

(A1 is also a clean replication of the diagnosis: same φ, same policy, and only the probe differs.)

### What this changes in the claims

Claims 1–3 above stand. Claim 4 (the limitation) is resolved in simulation: **with an active probe, grip adaptation adds safety beyond what any fixed speed limit gives at the same speed**, on all three seeds. New claims:

5. Passive proprioceptive grip estimation is not possible in this simulator below the limit (leakage-free R² ≈ 0 for three tire models). Apparent grip estimation in RMA-style training can be action leakage; a random-belief rollout is a simple test for it.
6. A brief speed pulse on straights makes grip observable (R² 0.89–0.93). φ_Q then drives within 0.1 m/s of the Oracle at every grip, beats a speed-matched fixed limit at μ = 0.4 (0.02–0.08 vs 0.33–0.47 crashes), and no fixed limit matches it on both speed and safety. Turning the probe off removes the adaptation.

**Caveats.** The probe changes the method: the car spends some driving on measurement. φ sees the true vehicle speed; on the car, wheel speed rises during wheelspin, so the signal must come from the IMU or wheel-vs-IMU slip. The real-car node runs at 50 Hz while training is at 100 Hz (bug C23). See docs/REAL_CAR_PROBE_PLAN.md.

## 6. Sim-to-real configuration R: realistic car sensors, braking probe, racing expert (amendments 8, 8b)

Everything above uses the simulator's true speed and gyro yaw rate, and an expert that drives 2.0 m/s × grip factor. R makes training match the car (docs/SIM_TO_REAL.md): speed from VESC wheel odometry (wheel spin and lock when traction-limited, ERPM gain error, noise, 50 Hz), yaw rate computed from odometry and the steering command, commanded steering, 40 Hz LiDAR with the node's 0.10 m margin, a **braking** probe (−1.0 m/s for 0.1 s every 0.5 s on straights), and a racing expert (full 3 m/s on straights, corner speed √(0.6·μ·g·R), braking 0.5·μ·g). Phase 1 *and* φ retrained for seeds 0–2. Config `configs/real_phase{1,2_probe}.yaml`, script `tools/real_suite.sh`, results `results/retrain_nov2026/real/`. A first attempt with the accelerating probe was stopped in Phase 1 (amendment 8b).

**Base policies** (validation, 13 tracks, true grip): crashes 0/39, 0/39, 2/39; speed at grip 1.0 / 0.6 / 0.4 ≈ 2.57 / 2.55 / 2.40–2.51 m/s (P2/Q base policies: 3/39 crashes at 1.98 / 1.52 / 1.20 m/s). **Faster and safer**, with noisier sensors.

**E1/E2** (N = 100 paired episodes per cell; crash rate / mean speed in m/s):

| seed | controller | μ = 1.0 | 0.8 | 0.6 | 0.4 |
|---|---|---|---|---|---|
| 0 | Oracle | 0.02 / 2.56 | 0.00 / 2.55 | 0.00 / 2.52 | 0.02 / 2.29 |
| 0 | **φ_R** | 0.00 / 2.55 | 0.01 / 2.55 | **0.01** / 2.53 | **0.39** / 2.39 |
| 0 | Blind | 0.02 / 2.56 | 0.01 / 2.58 | 0.56 / 2.56 | 0.86 / 2.32 |
| 1 | Oracle | 0.00 / 2.56 | 0.00 / 2.55 | 0.00 / 2.51 | 0.00 / 2.43 |
| 1 | **φ_R** | 0.00 / 2.55 | 0.01 / 2.55 | **0.05** / 2.54 | **0.28** / 2.40 |
| 1 | Blind | 0.00 / 2.56 | 0.07 / 2.57 | 0.43 / 2.58 | 0.84 / 2.35 |
| 2 | Oracle | 0.00 / 2.55 | 0.00 / 2.55 | 0.00 / 2.54 | 0.09 / 2.48 |
| 2 | **φ_R** | 0.01 / 2.54 | 0.03 / 2.55 | **0.00** / 2.53 | **0.37** / 2.35 |
| 2 | Blind | 0.00 / 2.55 | 0.01 / 2.56 | 0.33 / 2.58 | 0.86 / 2.33 |

**Pre-registered readouts** (amendment 8; all three seeds needed):

| | seed 0 | seed 1 | seed 2 | verdict |
|---|---|---|---|---|
| R1: E5 φ grip R² ≥ 0.4 | 0.86 | 0.84 | 0.87 | **PASS** |
| R2: φ speed drop ≥ 50% of the Oracle's | 0.16 vs 0.27 (59%) | 0.15 vs 0.13 (115%) | 0.19 vs 0.07 (271%) | **PASS** |
| R3: Blind matched on measured speed crashes ≥ 0.10 more at μ = 0.4, p < 0.05 | 0.85 vs 0.39, p = 3×10⁻¹⁴ | 0.84 vs 0.28, p = 3×10⁻¹⁷ | 0.86 vs 0.37, p = 4×10⁻¹⁵ | **PASS** |
| R4: G1, ρ gap closed at μ = 0.4 [95% CI] | 49% [38, 60] | 57% [45, 68] | 58% [47, 70] | **PASS** |
| R4: H2, φ ≤ Blind − 0.30 at μ = 0.4 (Holm p) | 0.39 vs 0.86 (4×10⁻¹⁴) | 0.28 vs 0.84 (10⁻¹⁶) | 0.37 vs 0.86 (10⁻¹⁴) | **PASS** |
| H3 (variance ratio ≥ 10) | 1.9× | 2.0× | 2.0× | FAIL |

Matched Blind's speed at μ = 1.0: 2.51 / 2.51 / 2.50 m/s vs φ 2.55 / 2.55 / 2.54 (within 0.05). Blind capped at φ's speed by the Q3 rule drives *slower* than φ (2.12–2.15 m/s, the cap only binds on straights) and still crashes 0.77–0.78 at μ = 0.4.

**What R shows.**

1. **Adaptation is where to slow, not how fast.** All three controllers drive at about the same average speed; the Oracle and φ slow in corners on low grip, which a speed cap cannot do. A speed limit 0.4 m/s *below* φ's speed crashes twice as often at μ = 0.4.
2. **μ = 0.6 is solved** (φ 0.00–0.05 vs Blind 0.33–0.56, Oracle 0.00).
3. **μ = 0.4 is half solved:** φ 0.28–0.39 vs Blind 0.84–0.86 vs Oracle 0.00–0.09, gap closed 49–58% (Q, ideal sensors: 82–87%). Grip reading (R² 0.84–0.87) is good, so the remaining gap is likely latency: φ's estimate needs a probe on a straight, and at 2.4–2.5 m/s the car reaches the next corner before the estimate has settled. Not tested; a faster probe schedule or longer history at corner entry are candidates.

**Caveats.** The wheel-slip model (spin-up to the command at 40 m/s², 30 ms relaxation) is an assumption that decides how much the odometry reveals; Stage 1 of `docs/REAL_CAR_PROBE_PLAN.md` measures it. Seed 2's base policy crashed 2/13 validation tracks at grip 0.4 (seeds 0–1: 0/13). The Oracle's speed drop with grip is small here (0.07–0.27 m/s), so R2's percentage is noisy.
