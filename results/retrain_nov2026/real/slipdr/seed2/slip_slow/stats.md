### results/retrain_nov2026/real/slipdr/seed2/slip_slow/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.29 [0.21, 0.39] | 2.58 | 0.523 [0.507, 0.542] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.33 | 0.679 [0.644, 0.715] |
| oracle | 0.6 | 100 | 0.01 [0.00, 0.05] | 2.53 | 0.465 [0.460, 0.471] |
| oracle | 0.4 | 100 | 0.09 [0.05, 0.16] | 2.48 | 0.518 [0.510, 0.526] |
| phi | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.52 | 0.465 [0.458, 0.473] |
| phi | 0.4 | 100 | 0.37 [0.28, 0.47] | 2.40 | 0.594 [0.569, 0.622] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 99% [94%, 100%] | 0.00 / 0.29 / 0.01 | 3.7e-09 | 1.1e-17 |
| 0.4 | 52% [41%, 64%] | 0.37 / 0.86 / 0.09 | 7.1e-15 | 1.4e-11 |

Cross-grip ρ variance, Blind/φ: 1.43× [0.97, 2.09]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
