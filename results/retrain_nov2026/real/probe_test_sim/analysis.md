# Probe test: results/retrain_nov2026/real/probe_test_sim/sim_probe_trials.csv

| metric | grip_1.0 | grip_0.7 | grip_0.4 | Kruskal-Wallis p | MWU p (first > last) | pass |
|---|---|---|---|---|---|---|
| imu_decel | 9.51 [9.43, 9.59] (n=20) | 7.24 [7.18, 7.30] (n=20) | 4.17 [4.09, 4.26] (n=20) | 4.1e-12 | 3.4e-08 | **PASS** |
| odom_drop | 0.66 [0.59, 0.74] (n=20) | 0.57 [0.53, 0.63] (n=20) | 0.45 [0.39, 0.47] (n=20) | 4.3e-08 | 2.3e-07 | **PASS** |
| odom_drop_frac | 0.67 [0.57, 0.75] (n=20) | 0.62 [0.58, 0.68] (n=20) | 0.43 [0.37, 0.48] (n=20) | 2.5e-08 | 5.3e-08 | **PASS** |
| lidar_drop | -0.24 [-1.37, 1.29] (n=20) | 0.87 [-0.10, 1.61] (n=20) | -0.09 [-0.85, 0.91] (n=20) | 0.23 | 0.67 | FAIL |

Cells: median [IQR]. imu_decel in m/s², drops in m/s.

Descriptive (not part of the pass criterion):

| quantity | grip_1.0 | grip_0.7 | grip_0.4 |
|---|---|---|---|
| odometry dip during the pulse (m/s) | 1.00 [0.83, 1.23] (n=20) | 0.98 [0.89, 1.19] (n=20) | 1.07 [1.01, 1.12] (n=20) |
| dip minus drop after recovery (m/s); > 0 means the wheel slipped | 0.33 [0.23, 0.47] (n=20) | 0.41 [0.35, 0.48] (n=20) | 0.59 [0.54, 0.71] (n=20) |
| peak motor current during the pulse (A) | not logged | not logged | not logged |

If slip_excess is near 0 on every surface, the wheels do not slip under the pulse: the grip signal is then only in odom_drop (true deceleration), which is the "no slip" model of RESULTS section 8.
If brake_current is the same on every surface and odom_drop does not separate them, the pulse is motor-limited rather than tire-limited: use a larger --amplitude or a higher --cruise.
Overall: the probe's response **separates** the surfaces on at least one metric.
