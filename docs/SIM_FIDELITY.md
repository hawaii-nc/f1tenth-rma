# Simulator fidelity: what f110_gym can and cannot show about grip

Read this before interpreting any grip or ρ result from simulation.

## The tire model is linear, with no friction-circle saturation

f110_gym 0.2.1 (`gym/f110_gym/envs/dynamic_models.py`, `vehicle_dynamics_st`) uses the CommonRoad single-track model:

- **Below 0.5 m/s** it switches to the kinematic model, where μ has no effect at all.
- **Above 0.5 m/s** the yaw-rate and slip-angle equations are linear in slip angle. μ multiplies the cornering-stiffness terms (`mu * C_Sf * ...`, `mu * C_Sr * ...`).
- There is **no saturation**: lateral tire force grows without bound as slip angle grows. Longitudinal acceleration is limited by `a_max` and `v_switch`, neither of which depends on μ.

What this means:

1. **Lowering μ makes the car understeer. It does not make it lose grip.** At low μ the same steering produces less yaw, so the car runs wide and hits the outer wall. That is how E0 passes: crashes do rise as grip drops. But there is no "limit" to exceed, and no spin or slide.
2. **ρ can exceed 1 with no consequence.** ρ = √(a_lat² + a_long²)/(μg) is still a well-defined measure of *how much grip the policy chose to ask for*. In f110_gym, though, ρ is not a distance to a loss-of-control event. The July poster's ρ ≈ 0.10–0.24 is far from 1 anyway, which leads to the poster's own recommendation to raise the speed cap until ρ reaches 0.6–0.8.
3. **The safety story needs a simulator where the limit is real.** A policy can only learn to "respect the friction circle" if crossing it costs something.

## Options, from cheapest to most work

| Option | What it buys | Cost |
|---|---|---|
| Raise `max_velocity` (3 → 5–6 m/s on full-scale tracks) | ρ moves toward the regime where understeer crashes dominate | Retrain Phase 1 and Phase 2. Still no saturation |
| Add a saturating tire to f110_gym: clip lateral force to √((μF_z)² − F_x²), or swap in a Pacejka Magic Formula lateral tire | A real friction limit. Exceeding it produces slides | Local fork of `dynamic_models.py` (numba). Parameters need identification at 1/10 scale |
| Use a fork with these models already built: [Gym-Khana](https://gym-khana.readthedocs.io/) has STP (single-track + lateral Pacejka) and PAC2002-based models | Same as above, with less code | Its docs say the best parameters are for a full-scale vehicle. Needs porting of the env wrapper |
| Gazebo (Tier 2 in the methodology) with surface friction set per surface (`<mu>/<mu2>`) | Independent rigid-body physics, so the result can't be an artifact of the bicycle model | 10–100× slower. Needs a skidpad calibration of μ_eff per surface |
| Real car with measured μ_eff (skidpad or inclined plane) | Ground truth that matters | Hardware time |

## Implemented: `tire_model: friction_circle` (November 2026)

`envs/tire_models.py` adds a saturating tire that f110_gym integrates in place of its stock `vehicle_dynamics_st` (same signature, swapped in by `RealF110Wrapper`).

- Below the limit it matches the stock linear model term for term (`tests/test_tire_models.py` checks this against a transcription of f110_gym's equations).
- Each axle's lateral force is capped at its share of the friction circle, √((μF_z)² − F_x²). F_x is split front/rear in proportion to load (the car is 4×4).
- Longitudinal acceleration is capped at μg, so low grip also lengthens braking.
- Not modelled: a force peak followed by fall-off (Pacejka), left/right load transfer, or tire relaxation.

Same inputs at 3 m/s with 0.35 rad of steer:

| grip | stock linear: a_lat, body slip | friction circle: body slip |
|---:|---|---|
| 1.0 | 8.9 m/s² (μg = 10.3), 0.6° | 0.6° (identical) |
| 0.6 | 8.5 m/s² (μg = 6.2, *impossible*), −5° | −75°: the car spins |
| 0.4 | 8.0 m/s² (μg = 4.1, *impossible*), −12° | −91°: the car spins |

How to use it:

```bash
python tools/check_physics_injection.py --track aut_tight --tire-model friction_circle   # pre-flight
python experiments/e1_e2_calibration.py --tire-model friction_circle ...                # evaluate existing checkpoints
python -m f1tenth_research.training.phase2_adaptation --tire_model friction_circle ...   # retrain φ
TIRE_MODEL=friction_circle bash tools/retrain_fixed.sh                                  # all of the above
```

Or set `environment.tire_model: friction_circle` in a config. Every experiment's `summary.json` records the tire model it used.

Two ways to use it in the paper:

1. **Robustness check (cheap).** Evaluate the existing policy and φ, trained on the linear tire, under the friction-circle tire. Does φ-RMA still sit between Oracle and Blind, and does Blind now crash (spin) more at low grip?
2. **Train on it (stronger).** Retrain Phase 1 and φ with `friction_circle`, ideally with the speed cap raised (HANDOFF item 5), so that exceeding the limit actually costs something during training.

The advisor's suggestion (Oct 31, 2026): if no sim tire model is representative enough, *learning on the fly on the real car* to avoid losing grip could be a novel full-paper contribution. Train on this model first; how far its predictions diverge from VADER's behaviour is evidence for that argument.

**Recommendation for the Feb 2027 workshop paper:**

- State the linear-tire limitation explicitly. Reviewers who know vehicle dynamics will ask about it.
- Present E1/E2 as "the policy asks for less grip when it believes grip is low" (behavioural calibration), which the linear model *can* show.
- Run the friction-circle robustness check above (no retraining needed for option 1).

## Other modelling notes

- `grip_factor` maps to μ = 1.0489 × grip_factor (1.0489 is f110_gym's default).
- `mass_scale` and `inertia_scale` change `m` and `I`. Both enter the single-track yaw dynamics.
- `motor_steering_scale` and `motor_drive_scale` now scale the steering and velocity commands. The June code sampled them but never applied them.
- Actuator delays are FIFO queues at the 100 Hz sim timestep (0.01 s), while the policy runs at 50 Hz.
- The f110_gym `ttc_thresh` is raised to 0.05 s, so the sim stops the car about 40 cm from walls instead of letting it graze them.

Sources: [f1tenth_gym](https://github.com/f1tenth/f1tenth_gym) source (`dynamic_models.py`, commit 4fdb9c7); [Gym-Khana dynamic models](https://gym-khana.readthedocs.io/en/latest/api/dynamic_models.html); Milliken & Milliken, *Race Car Vehicle Dynamics* (SAE, 1995), g-g diagram / friction circle.
