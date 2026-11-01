# Results: retrained pipeline (November 2026)

All numbers come from the rebuilt, bug-fixed pipeline on the real f1tenth_gym (commit 4fdb9c7). How it was trained: [RETRAINING.md](RETRAINING.md). What was predicted before running: [PREREGISTRATION_NOV2026.md](PREREGISTRATION_NOV2026.md). Raw outputs: `results/retrain_nov2026/` (every run has `episodes.csv`, `summary.json` and `provenance.json` with the git commit and checkpoint hashes). Statistics: `tools/stats.py`.

**These are not comparable one-to-one with the July poster**: different tracks (drivable scale), base-policy training (DAgger) and checkpoints, and seven pipeline bugs fixed (C16–C22). The July numbers came from a pipeline in which, among other things, every track used the last-loaded map (C22).

## 1. Pre-registered experiments, main configuration (seed 0)

Linear (stock) tire. Base policy: DAgger checkpoint. φ: k = 50, trained on oracle-driven rollouts (as in July). N = 100 paired episodes per cell, 13 tracks round-robin.

| controller | μ = 1.0 | 0.8 | 0.6 | 0.4 |
|---|---|---|---|---|
| **Crash rate** [95% CI] | | | | |
| Oracle | 0.00 [0.00, 0.04] | 0.00 | 0.00 | 0.00 [0.00, 0.04] |
| φ-RMA | 0.08 [0.04, 0.15] | 0.08 | 0.16 | 0.39 [0.30, 0.49] |
| Blind | 0.00 [0.00, 0.04] | 0.00 | 0.08 | 0.31 [0.23, 0.41] |
| **Mean speed** (m/s) | | | | |
| Oracle | 1.98 | 1.79 | 1.52 | 1.19 |
| φ-RMA | 2.13 | 2.13 | 2.13 | 2.12 |
| Blind | 1.98 | 1.98 | 1.98 | 1.98 |
| **Mean ρ** | | | | |
| Oracle | 0.067 | 0.064 | 0.057 | 0.050 |
| φ-RMA | 0.078 | 0.098 | 0.132 | 0.201 |
| Blind | 0.067 | 0.084 | 0.110 | 0.163 |

| Hypothesis | Result | Verdict |
|---|---|---|
| G0: grip is load-bearing (E0, Blind, aut_tight, N = 40) | Crash rate 0, 0, **1.0, 1.0, 1.0** at μ = 1.0, 0.8, 0.6, 0.4, 0.2 | **PASS** |
| G1: φ closes ≥ 30% of the ρ gap at μ = 0.4 | **−33%** [−36%, −29%]: φ is *further* from the Oracle than Blind is | **FAIL** |
| H2: φ crash ≤ Blind − 0.30 at μ = 0.4 | 0.39 vs 0.31 (McNemar, Holm p = 0.031, in the wrong direction) | **FAIL** |
| H3: cross-grip ρ variance Blind/φ ≥ 10× | 0.62× [0.57, 0.67] | **FAIL** |
| H4: belief causes caution (E4) | Hallucinating μ = 0.4 at true μ = 1.0 slows the car from 2.13 to **1.19 m/s** (= Oracle's μ = 0.4 speed), 0 crashes. Blindfold crash 0.31 = Blind's (0.31). "Restore" = φ (0.39) | Hallucination arm **PASS**; restore uninformative because φ ≈ constant |
| H-transient (E3) | "Settles" in 0 steps, but φ's decoded grip is ~constant (see H1), so this is trivially inside the band, not a detection | **Uninformative** |
| H1: φ decodes grip, R² ≥ 0.7 (E5, N = 200) | Encoder z: **0.9999**; history statistics: **0.04**; φ: **≈ 0** | **FAIL** |
| T1: Blind ≥ φ ≥ Oracle crash at μ = 0.4 under the friction-circle tire (same checkpoints, N = 40) | Blind 0.40, **φ 0.62**, Oracle 0.00 | **FAIL** |

**What this shows.**

1. **The base policy is grip-aware, and belief alone controls its caution.** With the true grip (Oracle) it never crashes at any μ and slows from 1.98 to 1.19 m/s as μ falls. Told the wrong grip (Blind), it crashes. Told a low grip at high true grip (hallucination), it slows down exactly as much as at a real low grip. E0, the Oracle row and E4 together make the case that *if* grip can be estimated, the policy will use it.
2. **φ cannot estimate grip in this configuration**, so φ-RMA is no better than Blind. It is slightly worse: φ settles on a latent that makes the car drive faster (2.13 m/s) than the Oracle does at *any* grip.
3. **Why** (diagnosed before the post-hoc runs, see the pre-registration addendum):
   - *Observability.* In f110_gym's linear single-track model, μ only enters the understeer gradient. With its parameters, the steady-state yaw gain at μ = 0.4 differs from μ = 1.0 by ~5% at 2 m/s, smaller than the ±20% steering-scale randomization. The E5 history probe (R² 0.04) confirms that grip is nearly invisible in 0.5 s of motion.
   - *Action leakage.* φ is trained on oracle-driven rollouts, in which the oracle's own slower driving reveals low grip. That cue disappears when φ drives, leaving a fixed point at "high-grip" behaviour.

   This is the same signature as the July E5 result (φ R² 0.08), now explained.

## 2. Post-hoc remedies (registered before running; labelled post hoc)

*Running. P1 = on-policy φ (removes action leakage). P2 = friction-circle tire for training and evaluation (makes grip observable through the μg acceleration cap and cornering saturation).* Results will be added here.

## 3. Robustness (replicate seeds, robust baseline, held-out tracks)

*Queued after section 2, on whichever configuration the pre-registration addendum selects.*
