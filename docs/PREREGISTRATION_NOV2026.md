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
