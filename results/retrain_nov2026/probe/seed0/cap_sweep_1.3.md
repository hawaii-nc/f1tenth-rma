phi: results/retrain_nov2026/probe/seed0/e1_e2/run  vs  capped Blind: results/retrain_nov2026/probe/seed0/cap_sweep_1.3/e1_e2/run

| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |
|---:|---:|---:|---|---:|---|
| 1.0 | 100 | 0.09 | 0.01 [0.00, 0.05] | 0.021 | 2.02 / 1.43 |
| 0.8 | 100 | 0.07 | 0.00 [0.00, 0.04] | 0.016 | 1.85 / 1.43 |
| 0.6 | 100 | 0.02 | 0.05 [0.02, 0.11] | 0.38 | 1.57 / 1.40 |
| 0.4 | 100 | 0.07 | 0.07 [0.03, 0.14] | 1 | 1.28 / 1.36 |

- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **FAIL**
