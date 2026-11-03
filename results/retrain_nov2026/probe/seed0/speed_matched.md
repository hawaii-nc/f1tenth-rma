phi: results/retrain_nov2026/probe/seed0/e1_e2/run  vs  capped Blind: results/retrain_nov2026/probe/seed0/speed_matched/e1_e2/run

| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |
|---:|---:|---:|---|---:|---|
| 1.0 | 100 | 0.09 | 0.11 [0.06, 0.19] | 0.5 | 2.02 / 2.12 |
| 0.8 | 100 | 0.07 | 0.12 [0.07, 0.20] | 0.062 | 1.85 / 2.11 |
| 0.6 | 100 | 0.02 | 0.14 [0.09, 0.22] | 0.00049 | 1.57 / 2.08 |
| 0.4 | 100 | 0.07 | 0.46 [0.37, 0.56] | 3.6e-12 | 1.28 / 1.99 |

- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **PASS**
