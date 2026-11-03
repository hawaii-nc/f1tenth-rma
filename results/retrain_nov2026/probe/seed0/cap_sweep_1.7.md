phi: results/retrain_nov2026/probe/seed0/e1_e2/run  vs  capped Blind: results/retrain_nov2026/probe/seed0/cap_sweep_1.7/e1_e2/run

| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |
|---:|---:|---:|---|---:|---|
| 1.0 | 100 | 0.09 | 0.09 [0.05, 0.16] | 1 | 2.02 / 1.82 |
| 0.8 | 100 | 0.07 | 0.09 [0.05, 0.16] | 0.5 | 1.85 / 1.82 |
| 0.6 | 100 | 0.02 | 0.09 [0.05, 0.16] | 0.016 | 1.57 / 1.79 |
| 0.4 | 100 | 0.07 | 0.12 [0.07, 0.20] | 0.062 | 1.28 / 1.74 |

- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **FAIL**
