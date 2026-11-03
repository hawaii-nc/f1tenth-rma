phi: results/retrain_nov2026/probe/seed2/e1_e2/run  vs  capped Blind: results/retrain_nov2026/probe/seed2/speed_matched/e1_e2/run

| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |
|---:|---:|---:|---|---:|---|
| 1.0 | 100 | 0.02 | 0.02 [0.01, 0.07] | 1 | 2.00 / 2.11 |
| 0.8 | 100 | 0.04 | 0.09 [0.05, 0.16] | 0.12 | 1.87 / 2.11 |
| 0.6 | 100 | 0.08 | 0.11 [0.06, 0.19] | 0.25 | 1.60 / 2.08 |
| 0.4 | 100 | 0.08 | 0.43 [0.34, 0.53] | 5.8e-11 | 1.28 / 1.99 |

- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **PASS**
