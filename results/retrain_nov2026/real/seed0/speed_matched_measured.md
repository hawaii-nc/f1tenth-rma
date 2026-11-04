phi: results/retrain_nov2026/real/seed0/e1_e2/run  vs  capped Blind: results/retrain_nov2026/real/seed0/speed_matched_measured/e1_e2/run

| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |
|---:|---:|---:|---|---:|---|
| 1.0 | 100 | 0.00 | 0.01 [0.00, 0.05] | 1 | 2.55 / 2.51 |
| 0.8 | 100 | 0.01 | 0.00 [0.00, 0.04] | 1 | 2.55 / 2.52 |
| 0.6 | 100 | 0.01 | 0.50 [0.40, 0.60] | 3.6e-15 | 2.53 / 2.52 |
| 0.4 | 100 | 0.39 | 0.85 [0.77, 0.91] | 2.8e-14 | 2.39 / 2.29 |

- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **PASS**
