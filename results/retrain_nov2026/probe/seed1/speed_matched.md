phi: results/retrain_nov2026/probe/seed1/e1_e2/run  vs  capped Blind: results/retrain_nov2026/probe/seed1/speed_matched/e1_e2/run

| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |
|---:|---:|---:|---|---:|---|
| 1.0 | 100 | 0.10 | 0.10 [0.06, 0.17] | 1 | 2.06 / 2.11 |
| 0.8 | 100 | 0.07 | 0.11 [0.06, 0.19] | 0.12 | 1.91 / 2.11 |
| 0.6 | 100 | 0.04 | 0.17 [0.11, 0.26] | 0.00024 | 1.63 / 2.07 |
| 0.4 | 100 | 0.02 | 0.47 [0.38, 0.57] | 5.7e-14 | 1.29 / 1.99 |

- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **PASS**
