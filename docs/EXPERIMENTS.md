# Experiment protocol (E0–E5)

Condensed from the Paper 2 Safety Evaluation Methodology (July 2026). Scripts are in `experiments/`, and they share `src/f1tenth_research/f1tenth_research/eval/harness.py`.

**Claim under test:** the policy perceives a safety-relevant change (a grip drop) and responds by holding its *margin* roughly constant rather than its *speed*.

The claim is **behavioural and causal, not representational**. Success means behaviour tracks the true risk, and that dependence is mediated by ẑ. Whether ẑ correlates with the grip number is supporting evidence only.

## Controllers: one policy, three ways to supply z

| Controller | z | Role |
|---|---|---|
| Oracle | μ(e_true) | Upper bound (simulation only) |
| φ-RMA | φ(last k state–action pairs) | System under test |
| Blind | μ(e_nominal) | No-adaptation baseline (what the car runs without φ) |
| Belief(g) | μ(e with grip = g) | Causal interventions (E4) |

Episodes are **paired**: episode *i* uses the same seed and track for every controller. Actions are the policy mean. LiDAR noise and spawn drift are off.

## Metric: friction-circle utilization

ρ = √(a_lat² + a_long²) / (μg), with a_lat = v·ω and a_long = dv/dt, averaged over steps with v > 0.5 m/s, then per episode, then per condition. A calibrated controller keeps ρ roughly constant across grip levels. "Cross-grip swing" is the variance of a controller's per-grip mean ρ.

## Experiments

| Exp | Question | Script | Default protocol |
|---|---|---|---|
| E0 | Is grip load-bearing in this simulator? (gate) | `e0_grip_gate.py` | Blind; μ ∈ {1.0, 0.8, 0.6, 0.4, 0.2}; N = 40; aut_tight. Pass if crash rate is non-decreasing as μ drops and higher at the lowest μ |
| E1 | Does adapting recover performance? | `e1_e2_calibration.py` | Oracle / φ / Blind; μ ∈ {1.0, 0.8, 0.6, 0.4}; N = 100; 14 tracks round-robin |
| E2 | Is risk calibrated across grip? | same runs | Mean ρ per cell; gap closed; cross-grip variance ratio |
| E3 | How fast does φ notice a sudden change? | `e3_transient.py` | μ 1.0 → 0.4 at step 500; linear probe ẑ → grip fit on steady-grip episodes; settle time within ±0.1 for 25 steps |
| E4 | Is caution caused by the belief? | `e4_causal.py` | At μ = 0.4: blindfold (believe 1.0), restore (blindfold → φ), φ, Oracle. At μ = 1.0: hallucinate (believe 0.4), φ. Reports how far out of distribution each injected belief is |
| E5 | Where is the grip signal lost? | `e5_signal.py` | μ ~ U[0.2, 1.0]; probe R² for encoder z, history statistics, and φ's ẑ; 5-fold CV grouped by episode |

All scripts write `results/<exp>/<timestamp>/{episodes.csv, summary.csv, summary.json}`. `experiments/run_all.sh` runs the full set at the July sample sizes.

## Pre-registered hypotheses

| ID | Statement | Test | Type | July status |
|---|---|---|---|---|
| G0 | The crash boundary moves with grip | E0 | Gate | Pass (pre-fix) |
| G1 | φ closes ≥ X% of the Blind→Oracle gap (set X before running!) | E1 | Gate | 44% of the ρ gap at μ = 0.4 |
| H-safety (H3) | φ's cross-grip ρ variance is ≥ 10× below Blind's | E2 | Primary | **Not met** (1.25–1.27×) |
| H2 | φ's crash rate at μ = 0.4 is ≤ 2× its μ = 1.0 rate, while Blind's is ≥ 5× | E1 | Primary | Not reported |
| H-transient | φ's transient survival ≫ Blind's, with bounded latency | E3 | Primary | Pending |
| H-causal (H4) | Hallucination slows the car on good grip; blindfold ≈ Blind; restore recovers | E4 | Primary | Partial (25% gap closure) |
| H-perception (H1) | ẑ decodes grip, R² ≥ 0.7 (reported regardless) | E5 | Supporting | 0.08 (pre-fix) |

**Falsifiers.** If φ's cross-grip variance ≈ Blind's, the calibration claim fails. If hallucination doesn't induce caution, causal mediation fails. If G0 or G1 fails, the problem is upstream (physics or adaptation), and no metric tuning can fix it. A low H1 alongside passing primaries is a *mechanism finding*, not a failure.

**Fix these before running:** sweep points, N, X%, the E3 band and hold, and the number of drop events.

## Three venues

| Tier | Venue | Ground truth | Role | Runs |
|---|---|---|---|---|
| 1 | f110_gym | True μ, full control of ẑ | Establishes the claim | E0–E5 |
| 2 | Gazebo (ROS 2 Foxy) | Friction settable per surface (`<mu>/<mu2>`); μ_eff from a skidpad | Independent physics | E1, E2, E3, E4 |
| 3 | Real VADER car | No true μ, only imposed conditions | Sim-to-real existence proof | ρ per condition, ẑ response, **E4 hallucination** (pure software) |

**Skidpad calibration (Tiers 2–3).** Drive steady circles and tighten the radius until commanded and actual yaw rate diverge. The peak sustained a_lat equals μ_eff·g.

## Suggested figure set

1. E0: crash rate (or crash boundary) vs grip.
2. E1: completion and crash rate vs grip, three controllers.
3. E2: ρ distributions per grip, plus a cross-grip variance bar (the headline).
4. E3: decoded grip and ρ through a grip drop, with a window-length inset.
5. E4: bars for blindfold / hallucinate / restore.
6. E5: ẑ cluster plot coloured by grip, with probe R².
7. Real car: tire table, plus decoded grip over a run onto a slippery patch.
