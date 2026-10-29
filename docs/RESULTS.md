# Results

Every number below says where it came from. **Trust levels:**

- **Measured.** Produced by a run with a stored artifact or log in this repo.
- **Reported.** From the July 2026 slides, poster or project record. The run artifacts stayed on the lab machine and are not in this repo.
- **Pre-fix.** Produced before the physics-injection fixes in [BUGS_AND_LESSONS.md](BUGS_AND_LESSONS.md). Re-run before publishing.

All final sim results use `checkpoints/final/phase1_v42.pt` with `checkpoints/final/phase2_crashtol_clean.pt`, at a 3.0 m/s speed cap, on the 35%-scale "tight" tracks.

---

## 1. Simulation: risk calibration (E1/E2), the headline result

*Reported, pre-fix.* f1tenth_gym single-track model, forced grip sweep, N = 100 episodes per cell, paired seeds (same start pose and physics draw for all three controllers), the identical base policy for all three, and per-episode mean ρ averaged per condition.

| μ (grip) | Oracle | φ-RMA | Blind | φ gap | Blind gap |
|---:|---:|---:|---:|---:|---:|
| 1.0 | 0.102 | 0.094 | 0.102 | 0.008 | 0.000 |
| 0.8 | 0.119 | 0.116 | 0.126 | 0.003 | 0.007 |
| 0.6 | 0.142 | 0.154 | 0.166 | 0.012 | 0.024 |
| 0.4 | 0.185 | 0.215 | 0.239 | 0.030 | 0.054 |

- **Gap closed at μ = 0.4:** 1 − 0.030/0.054 = **44%**. Reproduced from the table by `tests/test_metrics.py`.
- **Cross-grip ρ variance, Blind/φ:** 1.25–1.27× at N = 20, 40 and 100. The rounded N = 100 table gives 1.28×, which is the "20–21% lower" figure in the overview README. This falls short of the pre-registered order-of-magnitude target (H3), so it is reported as a *partial* calibration effect.
- **Caveat:** ρ ≈ 0.1–0.24 throughout, so the car never approaches the friction limit and the safety payoff cannot yet be demonstrated. Raise the speed cap until ρ reaches 0.6–0.8 (poster, "what is still open"). See also [SIM_FIDELITY.md](SIM_FIDELITY.md): f110_gym's tire model does not saturate.

## 2. Simulation: the other E-series experiments

| Exp | Status (Jul 2026) | Result | Trust |
|---|---|---|---|
| E0: grip gate | **PASS** | Fixed-belief (Blind) controller crashes more as grip drops. N = 40 per grip, aut_tight | Reported, pre-fix |
| E3: transient | In progress | A longer-memory φ (100-step) was training. No result | n/a |
| E4: causal | Done | Hallucinate 0.30 crash / 1.99 m/s; blindfold 0.50 / 2.22; restore 0.45 / 2.15 → **25% gap closure**. Injected beliefs were > 4 SD from φ's usual outputs | Reported, pre-fix |
| E5: signal | **Needs re-check** | Grip R²: encoder 0.98 → history 0.36 → φ 0.08 | Reported, **pre-fix (flagged at the time)** |

Interpretation from the poster: grip need not be estimated precisely to be useful. φ decodes grip weakly (R² ≈ 0.08) yet still improves calibration, so the contribution is behavioural, not perceptual. The Paper 2 methodology treats E5 as supporting, not gating.

## 3. Real car: tire experiment

*Reported.* Setup: Traxxas Slash 4×4 F1TENTH car "VADER" (Jetson, ROS 2 Foxy) running the same frozen checkpoint as in simulation at a 3.0 m/s cap. The course is one 90° corner bounded by cardboard walls on polished concrete. Grip was changed by wrapping the tires. LiDAR (108 beams) and odometry only. 81 trials.

| Tires | n | pass | yaw rate (rad/s) | steer (rad) |
|---|---:|---:|---:|---:|
| bare (control) | 20 | 19 | 0.678 | 0.133 |
| foil | 21 | 21 | 0.645 | 0.128 |
| duct tape | 21 | 21 | 0.663 | 0.129 |
| electrical tape | 19 | 18 | 0.661 | 0.128 |

- Bare vs electrical tape: **yaw p = 0.009, steering p = 0.0001** (Mann–Whitney U).
- Within-trial variability of the grip estimate: **12× more active** on tape than on bare rubber.
- **Open items (poster):** run a matched no-adaptation baseline on the same four tire conditions, and *measure* each wrap's friction (inclined-plane or skidpad protocol) instead of assuming it.

The on-car logs (`rma_data_<tire>.csv`, `rma_trial_log_<tire>.csv`) are not in this repo. Re-derive the table with `analysis/real_car/tire_stats.py`, whose metric definitions are written down in its docstring; the exact aggregation behind the poster numbers was not preserved.

## 4. Phase 1 training history

*Reported* (project record, July 1).

| Run | Track(s) | obs | Config | Outcome |
|---|---|---:|---|---|
| 1–3 | example_map | 5 | Softmax "PPO" on continuous actions, no LiDAR | Policy collapsed to a constant action, ~8.5 reward/episode (worse than random). Invalid |
| 4 | example_map | 5 | Gaussian actor, real PPO clip, masked GAE | 999.5/1000: first working run |
| 5 | AUT | 5 | Dynamics only | ~0.91 reward/step |
| 6 | AUT | 41 | + 36-beam LiDAR, fixed reward, domain randomization | 999.7 on AUT; 998.8 zero-shot on example_map |
| Paper 1 | AUT/ESP/GBR/MCO | 43 | + raceline lookahead, 8 m/s | 634 steps avg, 0.199 m centerline deviation |
| Paper 2 (wall) | AUT/ESP/GBR/MCO | 43 | + wall proximity 0.2 | 769 steps, 286.3 reward, 0.195 m deviation |
| v27 | 4 × tight (AUT/ESP/GBR/MCO) | 113 | Map-agnostic (no raceline), 3 m/s, 108 beams | 10.0M steps (`checkpoints/archive`) |
| v28 / v30 | 14 × tight | 113 | Same; v30's config sets a 100-step φ window | 40.0M steps (`checkpoints/archive`) |
| **v42** | **14 × tight** | **113** | **Final**: `configs/final_phase1_v42.yaml` | **16.0M steps** (`checkpoints/final`) |

v27–v42 step counts and configs are *measured*, read from the checkpoints with `tools/inspect_checkpoint.py`. Per-run outcome metrics for v27–v42 were not preserved.

**June multi-map zero-shot evaluation** (*measured*, `docs/eval_results_multimap.txt`, 36-beam policy trained on AUT only): every track hit the 1000-step cap, and centerline deviation was 2.3–13.6 cm vs 23.5–28.0 cm for a random policy.

**Paper 2 reward-shaping finding** (*reported*): wall-proximity shaping improved precision and consistency but *not* speed regulation. The policy held about 8 m/s into hard turns, and the simulator did not punish it for doing so. That led to the Stage 0 / E0 gate.

## 5. What these results can and cannot support

- Supported: φ-RMA sits between Oracle and Blind at every degraded grip level, reproducibly across three sample sizes. The real car's own commands change with tire condition.
- Not yet supported: that the car is *safer* when it adapts. The car never approaches the grip limit (ρ ≤ 0.24), and the simulator's linear tire model cannot produce loss-of-traction events (see [SIM_FIDELITY.md](SIM_FIDELITY.md)).
- Pending re-runs after the physics fixes: E0, E1/E2, E4, E5. Also pending: E3, Gazebo (Tier 2), the real-car no-adaptation baseline, and measured tire friction.
