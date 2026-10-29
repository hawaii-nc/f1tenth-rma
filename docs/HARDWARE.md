# Hardware and test setup

## VADER (the real car)

| Item | Detail |
|---|---|
| Chassis | Traxxas Slash 4×4, 1/10 scale (F1TENTH build) |
| Compute | NVIDIA Jetson, L4T R35.4.1 = **JetPack 5.1.2** (earlier notes say "JetPack 5.4.1", which does not exist; check with `cat /etc/nv_tegra_release`), Python 3.8 |
| Software | ROS 2 Foxy; PyTorch 2.1.0 (user install); numpy; slam_toolbox; F1TENTH particle_filter dependencies, including range_libc |
| Sensors used by the policy | 2-D LiDAR (1080 beams → 108 used) and wheel odometry (`/odom`). No IMU, map or pose in the observation |
| Car stack | `ros2 launch f1tenth_unlv_veh stack_aeb_launch.py` (UNLV vehicle package with AEB) |
| Teleop | PS controller: hold **R2** for autonomous; release R2 or hold **L1** for manual override |
| Network | No internet on campus; software installs go through lab staff. Copy models with `scp` |
| Power board | AE170_PDU_02.04: 19 V output rated 4 A (76 W) |

**Upgrade in progress (July 2026):** the Jetson Orin NX 16 GB was preferred for size and power, but it had a 12-week lead time, so a **Jetson Orin AGX** was ordered instead (July 10). Before installing it, re-check the 76 W PDU budget against the AGX module's power mode, and get an AGX-compatible carrier board.

## Physical test tracks

- **Tire experiment (July 2026):** a single 90° corner bounded by cardboard walls on polished concrete. The four tire conditions were bare (control), foil, duct tape and electrical tape, with 81 trials total.
- **Cardboard loop:** about 2–3 ft wide, with the car about 8–9 in wide. This is why training uses 35%-scale "tight" tracks and a 3.0 m/s cap.
- **Planned:** a 20 × 20 ft loop with a mix of sweepers and a tight hairpin.
- **Planned friction protocol:** inclined-plane friction measurement per surface/tire, plus fixed-behaviour trials. Or the skidpad procedure in [EXPERIMENTS.md](EXPERIMENTS.md).

## Lab compute

- The lab training machine runs Docker with a GPU training container and a noVNC container for GUIs. Long jobs run in **tmux**.
- The Dell in TBE B150 was also used for training. Leave a note on it when a job is running.
