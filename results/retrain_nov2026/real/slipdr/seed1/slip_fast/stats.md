### results/retrain_nov2026/real/slipdr/seed1/slip_fast/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.44 [0.35, 0.54] | 2.58 | 0.539 [0.519, 0.562] |
| blind | 0.4 | 100 | 0.84 [0.76, 0.90] | 2.35 | 0.674 [0.640, 0.710] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.51 | 0.461 [0.457, 0.466] |
| oracle | 0.4 | 100 | 0.00 [0.00, 0.04] | 2.43 | 0.507 [0.500, 0.514] |
| phi | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.50 | 0.460 [0.454, 0.468] |
| phi | 0.4 | 100 | 0.21 [0.14, 0.30] | 2.40 | 0.579 [0.555, 0.606] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 99% [93%, 100%] | 0.00 / 0.44 / 0.00 | 1.1e-13 | 4.7e-17 |
| 0.4 | 57% [45%, 68%] | 0.21 / 0.84 / 0.00 | 4.3e-19 | 7.8e-13 |

Cross-grip ρ variance, Blind/φ: 1.28× [0.74, 2.06]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
