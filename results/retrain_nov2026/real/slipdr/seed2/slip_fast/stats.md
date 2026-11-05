### results/retrain_nov2026/real/slipdr/seed2/slip_fast/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.33 [0.25, 0.43] | 2.58 | 0.525 [0.508, 0.543] |
| blind | 0.4 | 100 | 0.85 [0.77, 0.91] | 2.33 | 0.682 [0.647, 0.718] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.54 | 0.465 [0.460, 0.471] |
| oracle | 0.4 | 100 | 0.09 [0.05, 0.16] | 2.48 | 0.517 [0.509, 0.525] |
| phi | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.51 | 0.461 [0.454, 0.469] |
| phi | 0.4 | 100 | 0.35 [0.26, 0.45] | 2.37 | 0.598 [0.570, 0.629] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 92% [86%, 99%] | 0.00 / 0.33 / 0.00 | 2.3e-10 | 8e-18 |
| 0.4 | 51% [39%, 63%] | 0.35 / 0.85 / 0.09 | 3.6e-15 | 2.1e-13 |

Cross-grip ρ variance, Blind/φ: 1.30× [0.87, 1.85]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
