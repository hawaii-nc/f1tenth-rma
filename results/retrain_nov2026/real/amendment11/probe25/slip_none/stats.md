### results/retrain_nov2026/real/amendment11/probe25/slip_none/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.36 [0.27, 0.46] | 2.32 | 0.674 [0.664, 0.686] |
| blind | 0.4 | 100 | 0.84 [0.76, 0.90] | 2.17 | 0.879 [0.867, 0.892] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.22 | 0.615 [0.613, 0.617] |
| oracle | 0.4 | 100 | 0.01 [0.00, 0.05] | 1.86 | 0.754 [0.746, 0.761] |
| phi | 0.6 | 100 | 0.18 [0.12, 0.27] | 2.29 | 0.646 [0.642, 0.652] |
| phi | 0.4 | 100 | 0.82 [0.73, 0.88] | 2.18 | 0.862 [0.853, 0.873] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 47% [39%, 55%] | 0.18 / 0.36 / 0.00 | 0.00024 | 6.2e-15 |
| 0.4 | 13% [6%, 20%] | 0.82 / 0.84 / 0.01 | 0.5 | 2.7e-05 |

Cross-grip ρ variance, Blind/φ: 0.90× [0.79, 1.02]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **FAIL**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **FAIL**
- H3 (cross-grip variance ratio >= 10): **FAIL**
