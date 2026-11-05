### results/retrain_nov2026/real/slipdr/seed2/nominal/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.33 [0.25, 0.43] | 2.58 | 0.525 [0.508, 0.542] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.33 | 0.681 [0.646, 0.718] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.54 | 0.465 [0.460, 0.471] |
| oracle | 0.4 | 100 | 0.09 [0.05, 0.16] | 2.48 | 0.517 [0.509, 0.526] |
| phi | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.52 | 0.464 [0.457, 0.472] |
| phi | 0.4 | 100 | 0.33 [0.25, 0.43] | 2.38 | 0.598 [0.571, 0.629] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 97% [91%, 100%] | 0.00 / 0.33 / 0.00 | 2.3e-10 | 9.1e-18 |
| 0.4 | 50% [39%, 62%] | 0.33 / 0.86 / 0.09 | 4.4e-16 | 9e-13 |

Cross-grip ρ variance, Blind/φ: 1.34× [0.92, 1.90]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
