# Real-car test plan: does the grip probe work on the F1TENTH car?

**Goal.** Check, on the real car, the simulation finding behind amendment 6: a short braking pulse asks the tires for more than low grip can give, so the car's achieved deceleration reveals the grip. This is the first step toward Dr. Modekurthy's "learn on the fly in the real world" suggestion (Oct 31 email). Stage 1 needs no learned policy and can be run in one lab session.

## Stage 1: open-loop braking probe on different surfaces (no learned policy)

**Step-by-step sheet for the lab session: [STAGE1_RUN_SHEET.md](STAGE1_RUN_SHEET.md).**

The probe used by the deployable models (configuration R, amendment 8b) is a **braking** pulse: the speed command drops by 1.0 m/s for 0.1 s. This replaces the accelerating pulse in earlier versions of this plan.

**Setup.** A straight of at least 4 m, ending at a flat wall 2–8 m beyond where the pulse happens (the front LiDAR then measures true speed, independent of wheel slip). Test 3 grip conditions, using the July tire wraps where possible, since those are known to change the car's behaviour:

1. bare tires on polished concrete (high grip)
2. duct-tape wraps
3. electrical-tape wraps (lowest grip in July)

**Maneuver and logging: `tools/real_car/probe_maneuver_node.py`** (ROS 2; untested on hardware, check topics with `ros2 topic list` first). One run per trial:
- cruise straight at 1.5 m/s for 1.5 s
- **pulse**: 0.5 m/s for 0.1 s
- back to 1.5 m/s for 1 s
- stop

It logs, at 100 Hz, to one CSV:
- the commanded speed
- odometry speed and yaw rate
- front LiDAR range (median of ±5° straight ahead)
- IMU longitudinal acceleration, if `--imu_topic` is given
- VESC motor current, if `/sensors/core` is available

```
python3 tools/real_car/probe_maneuver_node.py --surface bare --trial 1 --out ~/probe_trials.csv
```

Do 20 trials per surface, alternating direction.

**Analysis: `tools/real_car/analyze_probe_trials.py`**
```
python3 tools/real_car/analyze_probe_trials.py ~/probe_trials.csv --order bare duct electrical --out probe_report.md
```
It computes per trial:
- **imu_decel:** peak IMU deceleration
- **odom_drop:** the drop in odometry speed once the wheel rolls again after the pulse
- **odom_drop_frac:** odom_drop normalized by the drop available
- **lidar_drop:** the drop in speed from the front-range rate

**Pass criterion (set before running).** At least one metric differs across the 3 surfaces (Kruskal–Wallis p < 0.05) and is lower for electrical tape than for bare tires (one-sided Mann–Whitney p < 0.05). Also check `motor_current`: if the brake current saturates at every surface, the pulse is motor-limited rather than tire-limited.

**Prediction (simulation of the same test, `tools/real_car/simulate_probe_trials.py`; `results/retrain_nov2026/real/probe_test_sim/analysis.md`)**, 20 trials per grip:

| metric | grip 1.0 | grip 0.7 | grip 0.4 | separates? |
|---|---|---|---|---|
| IMU peak deceleration (m/s²) | 9.5 | 7.2 | 4.2 | yes, p = 4×10⁻¹² |
| odometry speed drop (m/s) | 0.66 | 0.57 | 0.45 | yes, p = 4×10⁻⁸ |
| LiDAR speed drop | — | — | — | no: the simulated straight has no wall ahead |

So **the probe should be detectable even without an IMU**, through wheel odometry alone, *if* the real wheel slips as the model assumes (spin-up or lock at 40 m/s² towards the command, 30 ms recovery). That assumption is exactly what this test checks; the slip-model sensitivity runs (amendment 9) show how much the trained controller depends on it.

**Safety.** The pulse only slows the car (by at most 1 m/s). Keep walls at least 1 m beyond the end of the straight, and keep the e-stop in hand.

## Stage 2: closed-loop (after Stage 1 passes)

The node already does what earlier versions of this plan listed as to-do: it runs at 100 Hz like training (bug C23 fixed), applies the probe (`--probe 1`, default amplitude −1.0 m/s, the braking pulse the car models were trained with), and the models were retrained on the car's sensing (wheel-odometry speed with slip, kinematic yaw rate, 40 Hz LiDAR; amendments 8–10). None of this has run on hardware.

1. **Re-center the slip model if Stage 1 says so.** If the measured wheel response differs from the default model (spin-up or lock at 40 m/s², 30 ms recovery), re-center the slip randomization on it and retrain φ (`tools/slipdr_suite.sh`, about 1.5 h per seed on 4 cores).
2. **Bench test.** Wheels off the ground: `~/start_rma_noadapt.sh`, then `~/start_rma.sh` (`deploy/`). Check the log for the 0.1 s speed dips every 0.5 s when steering is straight, and that the loop holds 100 Hz.
3. **Trials.** π + φ_DR (`runs/real_phase1_seedN` + `runs/real_phase2_slipdr_seedN`) against the non-adaptive baseline, both with the probe on, on the July corner setup across tire wraps: speed and pass rate, as in the July Table II. Register the prediction first (docs/PREREGISTRATION_NOV2026.md).

## What not to claim from Stage 1

Stage 1 shows that the *signal* exists on the real car, not that the learned controller works there. The paper should report it as such.
