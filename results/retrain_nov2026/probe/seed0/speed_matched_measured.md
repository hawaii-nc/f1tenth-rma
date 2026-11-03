phi: results/retrain_nov2026/probe/seed0/e1_e2/run  vs  capped Blind: results/retrain_nov2026/probe/seed0/speed_matched_measured/e1_e2/run

| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |
|---:|---:|---:|---|---:|---|
| 1.0 | 100 | 0.09 | 0.10 [0.06, 0.17] | 1 | 2.02 / 2.05 |
| 0.8 | 100 | 0.07 | 0.11 [0.06, 0.19] | 0.12 | 1.85 / 2.05 |
| 0.6 | 100 | 0.02 | 0.11 [0.06, 0.19] | 0.0039 | 1.57 / 2.02 |
| 0.4 | 100 | 0.07 | 0.37 [0.28, 0.47] | 1.9e-09 | 1.28 / 1.95 |

- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **PASS**
