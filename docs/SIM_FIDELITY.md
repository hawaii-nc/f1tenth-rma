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

**Recommendation for the Feb 2027 workshop paper:**

- State the linear-tire limitation explicitly. Reviewers who know vehicle dynamics will ask about it.
- Present E1/E2 as "the policy asks for less grip when it believes grip is low" (behavioural calibration), which the linear model *can* show.
- If time allows, add the saturating-tire fork as a robustness check. The change is local to one numba function.

## Other modelling notes

- `grip_factor` maps to μ = 1.0489 × grip_factor (1.0489 is f110_gym's default).
- `mass_scale` and `inertia_scale` change `m` and `I`. Both enter the single-track yaw dynamics.
- `motor_steering_scale` and `motor_drive_scale` now scale the steering and velocity commands. The June code sampled them but never applied them.
- Actuator delays are FIFO queues at the 100 Hz sim timestep (0.01 s), while the policy runs at 50 Hz.
- The f110_gym `ttc_thresh` is raised to 0.05 s, so the sim stops the car about 40 cm from walls instead of letting it graze them.

Sources: [f1tenth_gym](https://github.com/f1tenth/f1tenth_gym) source (`dynamic_models.py`, commit 4fdb9c7); [Gym-Khana dynamic models](https://gym-khana.readthedocs.io/en/latest/api/dynamic_models.html); Milliken & Milliken, *Race Car Vehicle Dynamics* (SAE, 1995), g-g diagram / friction circle.
