# Stage 1 run sheet: braking-probe test on VADER

One page to take to the lab. Background and pass criterion: [REAL_CAR_PROBE_PLAN.md](REAL_CAR_PROBE_PLAN.md). One session, about 2 hours, no learned policy. The maneuver node has never run on hardware: do section 2 with the wheels off the ground first.

**Question.** When the speed command drops by 1 m/s for 0.1 s, does the car's response differ between high-grip and low-grip tires, and do the wheels slip the way the simulator assumes?

## 1. Bring and set up

- Tire wraps: none (bare), duct tape, electrical tape. Tape measure, floor tape, laptop with this repo, charged battery and a spare.
- A straight on polished concrete ending at a **flat wall**. Mark a start line **6–8 m from the wall**. The car travels about 4 m and must stop at least 1 m short; the wall gives the LiDAR a true-speed reference (it only counts walls closer than 9.5 m).
- Copy to the car: `scp tools/real_car/probe_maneuver_node.py <user>@vader:~/`

## 2. Checks before the first trial

| Check | Command | Write down |
|---|---|---|
| Car stack up | `ros2 launch f1tenth_unlv_veh stack_aeb_launch.py` | |
| Topics | `ros2 topic list` | names of the drive, odometry and scan topics (defaults `/drive`, `/odom`, `/scan`) |
| **IMU?** | `ros2 topic list \| grep -i imu` | topic name, or "none" (hand-off priority 2) |
| Motor current? | `ros2 topic list \| grep sensors/core` | yes / no |
| Odometry rate | `ros2 topic hz /odom` | Hz (the simulator assumes 50) |
| LiDAR rate and view | `ros2 topic hz /scan`; `ros2 topic echo /scan --once \| head -8` | Hz (assumed 40); `angle_min`, `angle_max` (assumed ±135°) |
| Bench run, **wheels off the ground** | `python3 ~/probe_maneuver_node.py --surface bench --trial 0 --out ~/bench.csv` | wheels spin ~1.5 s, dip briefly, spin 1 s, stop |
| Dead-man | does `/drive` move the car only while R2 is held? | yes / no |
| AEB | does the stack's emergency brake trigger when the car approaches the wall? | distance at which it triggers |

If the wheels do not turn in the bench run, the drive topic or the dead-man is the cause, not the node. If AEB triggers during a trial, move the start line back.

## 3. Trials

Order of surfaces: **bare → duct → electrical** (so tape residue does not affect the bare runs). 20 trials each. Start every trial from standstill on the start line, pointing at the wall.

```bash
python3 ~/probe_maneuver_node.py --surface bare --trial 1 --out ~/probe_trials.csv
```

Add `--imu_topic <name>` if an IMU topic exists; add `--drive_topic`, `--odom_topic`, `--scan_topic` if the names differ. Increase `--trial` each run; change `--surface` when the tires change. Everything appends to the one CSV.

- Hold R2 for the whole run if the dead-man requires it. Release it if anything looks wrong: the pulse only ever slows the car.
- A trial is void if the car hits something, veers more than about 0.3 m, or AEB fires: note the trial number and repeat it with the next number.
- After the first 3 bare trials, copy the CSV to the laptop and run the analysis (section 4) once to see that numbers come out. Then continue.

Note per surface: time, battery voltage if shown, anything odd (wheel hop, tape peeling).

## 4. Analysis (laptop)

```bash
scp <user>@vader:~/probe_trials.csv .
python tools/real_car/analyze_probe_trials.py probe_trials.csv --order bare duct electrical --out probe_report.md
```

Reading the report:

| What you see | What it means | Next |
|---|---|---|
| A metric **PASS**es (differs across surfaces, lower on electrical tape) | The probe reveals grip on the real car | Closed-loop trials (Stage 2) |
| `slip_excess` clearly above 0, larger on low grip | The wheels slip as the simulator assumes | Use φ_DR as is |
| `slip_excess` near 0 everywhere but `odom_drop` or `imu_decel` passes | No wheel slip; the signal is the true deceleration | φ_DR covers this case less well (RESULTS section 8): re-center the slip randomization toward "no slip" and retrain |
| Nothing passes, motor current equal on all surfaces | The pulse is motor-limited, not tire-limited | Repeat with `--amplitude -1.5` or `--cruise 2.0` (needs a longer straight) |
| Nothing passes, current differs | The wraps may not change grip enough on this floor | Measure grip directly (inclined plane, HARDWARE.md) before concluding |

Simulated prediction to compare against (`results/retrain_nov2026/real/probe_test_sim/analysis.md`): odometry drop 0.66 / 0.57 / 0.45 m/s and slip excess 0.33 / 0.41 / 0.59 m/s at grip 1.0 / 0.7 / 0.4.

## 5. Afterwards

- Keep the raw CSV and the notes (the CSV is not committed; archive it with the July logs).
- Add the report and the section-2 answers to RESULTS and the paper, **whichever way it comes out**.
- Tell Nathan / Prof. Modekurthy the outcome before starting Stage 2.
