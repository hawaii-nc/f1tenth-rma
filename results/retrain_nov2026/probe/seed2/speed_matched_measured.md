phi: results/retrain_nov2026/probe/seed2/e1_e2/run  vs  capped Blind: results/retrain_nov2026/probe/seed2/speed_matched_measured/e1_e2/run

| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |
|---:|---:|---:|---|---:|---|
| 1.0 | 100 | 0.02 | 0.02 [0.01, 0.07] | 1 | 2.00 / 2.01 |
| 0.8 | 100 | 0.04 | 0.02 [0.01, 0.07] | 0.5 | 1.87 / 2.01 |
| 0.6 | 100 | 0.08 | 0.09 [0.05, 0.16] | 1 | 1.60 / 1.98 |
| 0.4 | 100 | 0.08 | 0.33 [0.25, 0.43] | 6e-08 | 1.28 / 1.91 |

- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **PASS**
