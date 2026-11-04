### results/retrain_nov2026/real/slipdr/seed0/slip_none/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.56 [0.46, 0.65] | 2.56 | 0.548 [0.528, 0.569] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.37 | 0.676 [0.642, 0.711] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.53 | 0.468 [0.462, 0.474] |
| oracle | 0.4 | 100 | 0.00 [0.00, 0.04] | 2.20 | 0.507 [0.500, 0.514] |
| phi | 0.6 | 100 | 0.07 [0.03, 0.14] | 2.56 | 0.491 [0.480, 0.503] |
| phi | 0.4 | 100 | 0.64 [0.54, 0.73] | 2.36 | 0.643 [0.611, 0.678] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 71% [62%, 79%] | 0.07 / 0.56 / 0.00 | 6.4e-13 | 1.4e-15 |
| 0.4 | 20% [7%, 32%] | 0.64 / 0.86 / 0.00 | 4.8e-07 | 0.034 |

Cross-grip ρ variance, Blind/φ: 0.72× [0.42, 1.08]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **FAIL**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **FAIL**
- H3 (cross-grip variance ratio >= 10): **FAIL**
