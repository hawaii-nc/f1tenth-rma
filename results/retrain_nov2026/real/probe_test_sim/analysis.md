# Probe test: results/retrain_nov2026/real/probe_test_sim/sim_probe_trials.csv

| metric | grip_1.0 | grip_0.7 | grip_0.4 | Kruskal-Wallis p | MWU p (first > last) | pass |
|---|---|---|---|---|---|---|
| imu_decel | 9.51 [9.43, 9.59] (n=20) | 7.24 [7.18, 7.30] (n=20) | 4.17 [4.09, 4.26] (n=20) | 4.1e-12 | 3.4e-08 | **PASS** |
| odom_drop | 0.66 [0.59, 0.74] (n=20) | 0.57 [0.53, 0.63] (n=20) | 0.45 [0.39, 0.47] (n=20) | 4.3e-08 | 2.3e-07 | **PASS** |
| odom_drop_frac | 0.67 [0.57, 0.75] (n=20) | 0.62 [0.58, 0.68] (n=20) | 0.43 [0.37, 0.48] (n=20) | 2.5e-08 | 5.3e-08 | **PASS** |
| lidar_drop | -0.24 [-1.37, 1.29] (n=20) | 0.87 [-0.10, 1.61] (n=20) | -0.09 [-0.85, 0.91] (n=20) | 0.23 | 0.67 | FAIL |

Cells: median [IQR]. imu_decel in m/s², drops in m/s.
Overall: the probe's response **separates** the surfaces on at least one metric.
