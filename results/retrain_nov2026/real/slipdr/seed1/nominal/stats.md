### results/retrain_nov2026/real/slipdr/seed1/nominal/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.43 [0.34, 0.53] | 2.58 | 0.539 [0.518, 0.562] |
| blind | 0.4 | 100 | 0.84 [0.76, 0.90] | 2.35 | 0.675 [0.641, 0.711] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.51 | 0.462 [0.457, 0.466] |
| oracle | 0.4 | 100 | 0.00 [0.00, 0.04] | 2.43 | 0.507 [0.501, 0.514] |
| phi | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.50 | 0.461 [0.454, 0.469] |
| phi | 0.4 | 100 | 0.25 [0.18, 0.34] | 2.39 | 0.580 [0.557, 0.606] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 99% [93%, 100%] | 0.00 / 0.43 / 0.00 | 2.3e-13 | 4.3e-17 |
| 0.4 | 57% [45%, 67%] | 0.25 / 0.84 / 0.00 | 6.9e-18 | 6.7e-13 |

Cross-grip ρ variance, Blind/φ: 1.30× [0.75, 2.11]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
