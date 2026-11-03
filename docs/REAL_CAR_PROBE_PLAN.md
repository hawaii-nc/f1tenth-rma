# Real-car test plan: does the grip probe work on the F1TENTH car?

**Goal.** Check, on the real car, the simulation finding behind amendment 6: a short speed pulse asks the tires for more than low grip can give, so the car's achieved acceleration reveals the grip. This is the first step toward Dr. Modekurthy's "learn on the fly in the real world" suggestion (Oct 31 email). Stage 1 needs no learned policy and can be run in one lab session.

## Stage 1: open-loop probe on different surfaces (no learned policy)

**Setup.** A straight of at least 4 m. Test 3 grip conditions, using the July tire wraps where possible, since those are known to change the car's behaviour:

1. bare tires on polished concrete (high grip)
2. electrical-tape-wrapped tires on polished concrete (lowest grip in July)
3. one more: duct-tape wraps, or bare tires on a dusty or low-grip surface

**Maneuver.** A simple script publishes `AckermannDriveStamped` commands:
- cruise straight at 1.5 m/s for 1 s;
- **pulse**: command 1.5 + 2.0 = 3.5 m/s for 0.1 s (the simulation probe: +2.0 m/s for 10 steps at 100 Hz);
- back to 1.5 m/s for 1 s;
- stop.

Repeat 20 times per condition, alternating direction. The simulation also used pulse sizes of +1.0 and +3.0 m/s; trying them on a few runs shows whether the motor, rather than the tires, limits acceleration.

**Log (rosbag, everything at full rate):**
- the drive commands sent
- odometry speed. On most F1TENTH builds this comes from VESC wheel speed (ERPM), which reads **high** during wheelspin
- IMU linear acceleration (x) and yaw rate, from the VESC's IMU or a separate IMU, whichever the car has
- VESC motor current and duty cycle, if published (`/sensors/core` on the standard stack)

Topic names differ between builds: check `ros2 topic list` on the car first.

**Analysis (one script, per pulse):**
- peak IMU longitudinal acceleration during the pulse
- wheel slip: wheel speed minus the IMU-integrated speed over the pulse
- whether the motor hit its current limit

**Pass criterion (set before running).** Peak acceleration differs across the 3 conditions (Kruskal–Wallis p < 0.05), and is lower for tape than for bare tires (Mann–Whitney, one-sided). If the motor current limit is hit at every condition, the pulse is motor-limited: reduce the cruise speed or raise the current limit before concluding anything.

**Expected (from simulation).** Achieved acceleration roughly tracks μg until the motor limit (sim: 3–9 m/s² over grip 0.3–0.9). Wheel slip during the pulse should be the clearest real-car signal, and it does not exist in the simulator.

**Safety.** The pulse adds at most ~0.8 m/s in 0.1 s on a straight; braking back down at low grip takes ~0.3 s. Keep walls at least 1 m beyond the end of the straight, and keep the e-stop in hand.

## Stage 2: closed-loop (after Stage 1 passes)

0. **Match the control rate (bug C23).** Training runs at 100 Hz (0.01 s per step), but `rma_deployment_node.py` defaults to 50 Hz. Run the node at 100 Hz if the LiDAR and odometry rates allow it, or retrain at 50 Hz. Otherwise φ's 50-step window spans 1 s instead of 0.5 s, and the probe's 50-step period and 10-step pulse double in length.

1. **Fix the speed input.** In simulation φ sees the true vehicle speed. On the car, that should be an IMU-fused speed, not raw wheel speed (which jumps during slip). Retrain φ_Q in simulation with that observation model (wheel speed plus IMU acceleration, with noise) before deploying.
2. Deploy π + φ_Q with the probe enabled in `rma_deployment_node.py` (to be added: the same `period_steps / duration_steps / amplitude / max_steer` logic as `envs/f1tenth_env.py`, after the speed command).
3. Compare φ_Q vs Blind on the July corner setup across tire wraps: speed and pass rate, as in the July Table II.

## What not to claim from Stage 1

Stage 1 shows that the *signal* exists on the real car, not that the learned controller works there. The paper should report it as such.
