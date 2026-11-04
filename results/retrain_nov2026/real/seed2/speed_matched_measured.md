phi: results/retrain_nov2026/real/seed2/e1_e2/run  vs  capped Blind: results/retrain_nov2026/real/seed2/speed_matched_measured/e1_e2/run

| μ | n | crash φ | crash capped Blind [95% CI] | McNemar p | speed φ / capped (m/s) |
|---:|---:|---:|---|---:|---|
| 1.0 | 100 | 0.01 | 0.01 [0.00, 0.05] | 1 | 2.54 / 2.50 |
| 0.8 | 100 | 0.03 | 0.01 [0.00, 0.05] | 0.62 | 2.55 / 2.52 |
| 0.6 | 100 | 0.00 | 0.28 [0.20, 0.37] | 7.5e-09 | 2.53 / 2.55 |
| 0.4 | 100 | 0.37 | 0.86 [0.78, 0.91] | 3.6e-15 | 2.35 / 2.30 |

- Adaptation beats speed (capped Blind ≥ φ + 0.10 at μ = 0.4, p < 0.05): **PASS**
