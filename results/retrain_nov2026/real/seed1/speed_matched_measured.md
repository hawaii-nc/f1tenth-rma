phi: results/retrain_nov2026/real/seed1/e1_e2/run  vs  capped Blind: results/retrain_nov2026/real/seed1/speed_matched_measured/e1_e2/run

| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |
|---:|---:|---:|---|---:|---|
| 1.0 | 100 | 0.00 | 0.00 [0.00, 0.04] | 1 | 2.55 / 2.51 |
| 0.8 | 100 | 0.01 | 0.03 [0.01, 0.08] | 0.5 | 2.55 / 2.53 |
| 0.6 | 100 | 0.05 | 0.40 [0.31, 0.50] | 5.8e-11 | 2.54 / 2.54 |
| 0.4 | 100 | 0.28 | 0.84 [0.76, 0.90] | 2.8e-17 | 2.40 / 2.33 |

- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **PASS**
