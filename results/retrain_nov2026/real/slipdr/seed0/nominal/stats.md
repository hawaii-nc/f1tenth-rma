### results/retrain_nov2026/real/slipdr/seed0/nominal/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.56 [0.46, 0.65] | 2.56 | 0.549 [0.528, 0.571] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.32 | 0.689 [0.653, 0.725] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.52 | 0.466 [0.461, 0.473] |
| oracle | 0.4 | 100 | 0.02 [0.01, 0.07] | 2.29 | 0.498 [0.488, 0.507] |
| phi | 0.6 | 100 | 0.01 [0.00, 0.05] | 2.51 | 0.466 [0.458, 0.475] |
| phi | 0.4 | 100 | 0.41 [0.32, 0.51] | 2.36 | 0.602 [0.575, 0.632] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 99% [94%, 100%] | 0.01 / 0.56 / 0.00 | 1.1e-16 | 8.5e-18 |
| 0.4 | 45% [34%, 56%] | 0.41 / 0.86 / 0.02 | 5.7e-14 | 1.4e-09 |

Cross-grip ρ variance, Blind/φ: 1.05× [0.61, 1.62]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
