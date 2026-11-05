### results/retrain_nov2026/real/slipdr/seed2/slip_longrelax/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.31 [0.23, 0.41] | 2.59 | 0.518 [0.503, 0.535] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.32 | 0.687 [0.651, 0.724] |
| oracle | 0.6 | 100 | 0.01 [0.00, 0.05] | 2.54 | 0.465 [0.459, 0.471] |
| oracle | 0.4 | 100 | 0.09 [0.05, 0.16] | 2.47 | 0.517 [0.509, 0.525] |
| phi | 0.6 | 100 | 0.02 [0.01, 0.07] | 2.54 | 0.475 [0.466, 0.485] |
| phi | 0.4 | 100 | 0.52 [0.42, 0.62] | 2.38 | 0.626 [0.597, 0.656] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 82% [70%, 90%] | 0.02 / 0.31 / 0.01 | 3e-08 | 1.6e-16 |
| 0.4 | 36% [24%, 47%] | 0.52 / 0.86 / 0.09 | 2.3e-10 | 3e-06 |

Cross-grip ρ variance, Blind/φ: 1.25× [0.86, 1.74]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
