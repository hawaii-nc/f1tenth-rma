# Results: retrained pipeline (November 2026)

All numbers come from the rebuilt, bug-fixed pipeline on the real f1tenth_gym (commit 4fdb9c7). How it was trained: [RETRAINING.md](RETRAINING.md). What was predicted before each run: [PREREGISTRATION_NOV2026.md](PREREGISTRATION_NOV2026.md) (original plan, addendum for P1/P2, amendment 2 for the evaluation protocol). Raw outputs: `results/retrain_nov2026/`. Every run has `episodes.csv`, `summary.json` and `provenance.json` (git commit, library versions, f110_gym commit, checkpoint hashes). Statistics: `tools/stats.py` (Wilson CIs for crash rates, episode-bootstrap CIs, exact McNemar and Wilcoxon signed-rank tests on paired episodes, Holm-corrected across the 4 grip levels).

**Evaluation protocol (amendment 2).** Every episode starts at a point along the lap drawn from its seed; all controllers get the same start for the same seed. An earlier version of this page, like the July poster, used start-line episodes. Those turned out to be deterministic replays: N = 100 was really 13 distinct episodes per cell, so their CIs and p-values were invalid. Those runs are kept under `*_startline/` and are superseded by the numbers below. The conclusions did not change.

**Not comparable one-to-one with the July poster**: different tracks (drivable scale), base-policy training (DAgger), checkpoints, evaluation protocol, and seven pipeline bugs fixed (C16–C22).

## Summary

| Configuration | φ crash at μ = 0.4 (Blind / Oracle) | ρ gap closed at μ = 0.4 | Variance ratio Blind/φ | φ speed μ = 1.0 → 0.4 (Oracle 1.98 → 1.19) | φ grip R² (E5) | Pre-registered G1 / H2 / H3 |
|---|---|---|---|---|---|---|
| **Original** (linear tire, φ on oracle data) | 0.39 (0.32 / 0.00) | **−16%** [−24, −7] | 0.83× | 2.13 → 2.11 | −0.02 | FAIL / FAIL / FAIL |
| Original, evaluated on friction-circle tire (T1) | 0.65 (0.55 / 0.00) | −13% [−22, −7] | 0.87× | 2.13 → 2.02 | n/a | FAIL / FAIL / FAIL |
| **P1** (linear tire, on-policy φ), post hoc | **0.07** (0.32 / 0.00) | 47% [40, 54] | 2.45× | **1.54 → 1.53** (constant) | 0.00 | PASS / FAIL / FAIL |
| **P2** (friction-circle tire, on-policy φ), post hoc | **0.07** (0.44 / 0.05) | **85%** [76, 91] | **14.7×** [8.0, 31.2] | 1.28 → 1.14 | **0.26** | **PASS / PASS / PASS** |

**The finding in one paragraph.** The base policy uses a correct grip belief perfectly: Oracle has ≈ 0 crashes at every grip and slows from 1.98 to 1.19 m/s, and injecting a false low-grip belief slows it by exactly that much (E4). Whether the adaptation module φ can *supply* that belief depends on the simulator. In f1tenth_gym's stock linear tire, grip does not measurably change the car's motion at these speeds (history R² ≈ 0), and φ cannot estimate it. Trained the July way (on oracle-driven data), φ is **worse than not adapting at all**. Trained on its own rollouts (P1), it becomes safe only by driving uniformly slowly. With a saturating friction-circle tire (P2), grip becomes partly observable (R² ≈ 0.25), and φ passes all three pre-registered checks against Blind (crash 0.07 vs 0.44 at μ = 0.4). It also beats a robust policy trained without grip information (0.07 vs 0.16, p = 0.012), but that policy drives 25% faster. **The decisive control (amendment 3) is Blind with its speed capped at φ's own speed. It is just as safe (0.05–0.06 vs 0.07 at μ = 0.4).** So φ's safety benefit is explained by driving slower, not by estimating grip. Its grip-dependent speed modulation is real but small (~18% of the Oracle's). The defensible claims are: (1) a grip-aware base policy is safe *given* the grip; (2) in the stock F1TENTH simulator, grip is not observable from proprioception at these speeds, so RMA-style adaptation cannot work there, and the July-style training makes it actively harmful (action leakage); (3) a saturating tire makes grip partly observable, but at a 3 m/s cap the benefit of adapting is matched by simply slowing down. Showing a benefit *of adaptation* needs a regime where slowing down everywhere is costly (higher speed caps, a lap-time objective) or more informative histories. That is the next experiment.

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
- **E3 (transient)**: after a μ 1.0 → 0.4 step, φ's decoded grip settles within ±0.1 in a median of **38 steps (0.76 s)**, 39/39 episodes. Unlike the linear configuration, this is a real detection, and it passes H-transient (< 100 steps).
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

### R1 / R3

*Running: replicate training seeds 1 and 2 of the P2 configuration; held-out tracks.*
