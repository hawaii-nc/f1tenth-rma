# Rapid Motor Adaptation for Real-Time Grip Calibration in Autonomous Racing

*Workshop-paper draft, target IEEE IV 2027 Workshops (papers due Feb 1, 2027).*
*Builds on the July 13 IEEE draft and the poster. Every **[RE-RUN]** marks a number to be regenerated with this repo (see docs/HANDOFF.md). Citation keys refer to `references.bib`.*

**Nathan Chong** (University of Hawaiʻi at Mānoa; NSF REU at UNLV) and **Venkata Prashant Modekurthy** (UNLV)

---

**Abstract.** A race car's safe operating envelope is set by tire–road friction, which changes with surface, wear and payload, and which no onboard sensor measures directly. We ask whether a learned controller can infer its available grip from its own motion and spend a *steady fraction* of it. We adapt the two-phase Rapid Motor Adaptation (RMA) framework [kumar2021rma, zhang2025extreme] to the F1TENTH platform [okelly2020f1tenth].

- **Phase 1** trains a PPO policy, with imitation from a grip-aware Pure Pursuit expert, conditioned on a latent encoding of seven randomized physics parameters.
- **Phase 2** trains a 1-D CNN to reproduce that latent from the last 50 state–action pairs.

The deployed controller is map-agnostic: it observes 108 LiDAR ranges and 5 motion signals, with no map, pose or raceline. We measure safety by friction-circle utilization ρ, the fraction of available grip in use.

In simulation, the adaptation module closes **44%** of the gap between a grip-blind and an oracle controller at μ = 0.4, with **1.25×** lower cross-grip ρ variance **[RE-RUN]**. On a 1/10-scale car, wrapping the tires to lower grip significantly changes the frozen policy's own steering (p = 0.0001) and yaw rate (p = 0.009) across 81 trials. We also report a limitation that shapes the interpretation: the standard F1TENTH simulator's linear tire model never saturates.

## I. Introduction

- Grip governs the limits of safe control, and it changes: rain, tire wear, dust, payload. A controller tuned for nominal conditions is either conservative everywhere or unsafe when conditions degrade.
- Human drivers infer grip from how the car responds and leave a margin. We want a car that does the same: a steady **margin**, not a steady **speed**.
- RMA formalizes "infer the condition from behaviour", but it has been shown on legged robots [kumar2021rma] and quadcopters [zhang2025extreme], not on ground racing, where one condition-dependent constraint (friction) dominates.

**Contributions:**

1. To our knowledge, the first latent-intrinsics RMA on F1TENTH ground racing, end to end from simulation to a real car.
2. A fully map-agnostic observation (LiDAR + proprioception) for both the policy and the adaptation module.
3. A safety evaluation built on friction-circle utilization, with paired Oracle / φ-RMA / Blind controllers sharing one policy, plus causal belief-injection tests.
4. A real-car tire-wrap experiment.
5. An analysis of what the simulator's tire model can and cannot show.

## II. Related work

- **RMA.** Base policy plus an adaptation module trained by regression on privileged encodings [kumar2021rma]. The quadcopter extension adds joint PPO+IL with a decaying imitation weight [zhang2025extreme].
- **Learning on F1TENTH.** LiDAR-only deep RL [hell2024lidar, evans2023trajectory], imitation-learning benchmarks [sun2023ilbenchmark], and the survey and benchmarks in [evans2024unifying]. None estimates vehicle physics online.
- **Domain randomization** gives robustness [tobin2017dr]. RMA turns this into *adaptation* by conditioning on the sampled physics.
- **Safety framing.** The friction circle / g-g diagram [milliken1995rcvd]. Rules-as-constraints [shalevshwartz2017rss, achiam2017cpo].

## III. Method

**A. Observation and action.** x_t ∈ ℝ¹¹³:

- v, applied steering, previous v and steering commands, and yaw rate;
- 108 LiDAR beams, evenly subsampled from 1080, clipped at 10 m and normalized.

The action is (steering δ ∈ [−0.4189, 0.4189] rad, throttle ∈ [−1, 1] ↦ v_cmd ∈ [0, 3.0] m/s). No map-specific signal enters π or φ.

**B. Randomization.** Per episode we sample e ∈ ℝ⁷:

- grip ∈ [0.4, 1.0] (μ = 1.0489·grip);
- mass, inertia (correlated), and steering and drive gains, each ±20%;
- steering and drive delays of 0–50 ms;

followed by ±20% multiplicative noise. In 30% of episodes, one mid-episode grip drop (×0.7) is applied at a uniform time in [30%, 90%] of the episode. During training, LiDAR gets noise (σ = 0.02) and 5% beam dropout.

**C. Phase 1.** Networks:

- the policy π(x, z): an MLP, 3×256;
- the value V(x, z);
- the encoder z = μ(e) ∈ ℝ⁸, 7→128→128→8.

They are trained jointly with PPO (clip 0.2, γ 0.99, λ 0.95, lr 3·10⁻⁴) plus an imitation loss toward a grip-aware Pure Pursuit expert [coulter1992purepursuit] on minimum-curvature racelines [heilmeier2020mincurv]. The IL weight decays from 1.0 toward 0.01, with plateau-triggered rescues. The policy trains on 14 circuits [betz2022racing] at 35% scale (matching a 2–3 ft physical track), for 16M steps.

Reward: 5.0 × centerline progress, 0.05 smoothness, 0.01 alive, −1 collision, 0.5 speed–turn coupling, 0.1 centerline error.

**D. Phase 2.** φ is a Conv1d stack (115→32→32→8, kernel 5) followed by an FC layer (400→128→8). It maps the last k = 50 (x, a) pairs to ẑ and is trained by MSE against μ(e) on Phase 1 rollouts, plus an auxiliary physics loss with grip weighted 3×.

**E. Controllers.** One frozen π, three intrinsics sources:

- **Oracle:** μ(e_true);
- **φ-RMA:** φ(history);
- **Blind:** μ(e_nominal).

**F. Safety metric.** ρ = √(a_lat² + a_long²)/(μg), with a_lat = vω and a_long = dv/dt. A calibrated driver holds ρ roughly constant as μ changes.

## IV. Experiments

**Simulation** (f1tenth_gym [okelly2020f1tenth]): forced μ ∈ {1.0, 0.8, 0.6, 0.4}, N = 100 episodes per cell, paired seeds, tracks round-robin.

- **E0:** grip gate.
- **E1/E2:** crash rate and ρ.
- **E3:** step change in grip.
- **E4:** belief injection. Blindfold = believe 1.0 at true 0.4; hallucinate = believe 0.4 at true 1.0; restore = blindfold, then φ.
- **E5:** linear probes ẑ → μ.

**Real car:** a Traxxas Slash 4×4 F1TENTH build with Jetson and ROS 2, running the same frozen checkpoint. One 90° corner with cardboard walls on polished concrete. Four tire conditions (bare, foil, duct tape, electrical tape), 19–21 trials each, 81 total.

## V. Results **[RE-RUN all simulation numbers]**

**Table I. Mean ρ by grip** (July 2026 pilot, N = 100):

| μ | Oracle | φ-RMA | Blind |
|---|---|---|---|
| 1.0 | 0.102 | 0.094 | 0.102 |
| 0.8 | 0.119 | 0.116 | 0.126 |
| 0.6 | 0.142 | 0.154 | 0.166 |
| 0.4 | 0.185 | 0.215 | 0.239 |

- **E0:** crash rate rises as grip falls, so grip is load-bearing.
- **E1/E2:** φ-RMA sits between Oracle and Blind at every degraded grip. It closes 44% of Blind's gap at μ = 0.4, with 1.25–1.27× lower cross-grip ρ variance at N = 20, 40 and 100. This is below our pre-registered 10× target, so it is a partial effect.
- **E4:** restoring φ after a blindfold moves behaviour 25% of the way toward the safe side. Caveat: the injected beliefs were > 4 SD outside φ's typical outputs.
- **E5:** ẑ decodes grip weakly (R² ≈ 0.08), yet calibration improves. The adaptation is behavioural rather than a clean grip readout.

**Table II. Real car** (frozen checkpoint, 81 trials):

| Tires | n | pass | yaw (rad/s) | steer (rad) |
|---|---|---|---|---|
| bare | 20 | 19 | 0.678 | 0.133 |
| foil | 21 | 21 | 0.645 | 0.128 |
| duct | 21 | 21 | 0.663 | 0.129 |
| electrical | 19 | 18 | 0.661 | 0.128 |

Bare vs electrical tape: yaw p = 0.009, steering p = 0.0001 (Mann–Whitney U). φ's estimate is 12× more variable on tape than on bare rubber.

## VI. Discussion and limitations

- **Linear tires.** f1tenth_gym's single-track model scales cornering stiffness by μ but never saturates. Low grip produces understeer, not loss of traction, and ρ > 1 has no consequence. Our ρ results therefore show that the policy *asks for less grip when it believes grip is low*, not that it avoids slides. **[ADD: saturating-tire robustness check if done]**
- **Margin.** With ρ ≤ 0.24 the car never nears the limit. **[ADD: higher speed-cap results]**
- **Real car.** No measured μ per tire wrap and no matched no-adaptation baseline yet. **[ADD]**
- **Pipeline.** A bug in the July pipeline meant mid-episode grip drops changed the labels but not the simulated physics. All simulation numbers here are regenerated with the fix. **[confirm after re-run]**

## VII. Conclusion

A two-phase RMA controller can run on a 1/10-scale race car from LiDAR and motion alone. It shifts its operating point toward an oracle's as grip falls, and its own commands respond to a real tire change. The effect is real but partial. The next steps are a saturating tire model, a speed regime that approaches the limit, and measured real-world friction.

**Acknowledgment.** Supported by NSF REU Site Award #2349616 (UNLV Smart Cities). Thanks to Ederic Oytas for hardware support.
