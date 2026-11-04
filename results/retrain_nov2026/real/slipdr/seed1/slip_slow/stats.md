### results/retrain_nov2026/real/slipdr/seed1/slip_slow/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.45 [0.36, 0.55] | 2.58 | 0.538 [0.518, 0.561] |
| blind | 0.4 | 100 | 0.84 [0.76, 0.90] | 2.34 | 0.681 [0.645, 0.718] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.51 | 0.463 [0.458, 0.467] |
| oracle | 0.4 | 100 | 0.01 [0.00, 0.05] | 2.42 | 0.508 [0.501, 0.515] |
| phi | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.50 | 0.462 [0.456, 0.470] |
| phi | 0.4 | 100 | 0.28 [0.20, 0.37] | 2.38 | 0.587 [0.562, 0.614] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 99% [93%, 100%] | 0.00 / 0.45 / 0.00 | 5.7e-14 | 2.5e-17 |
| 0.4 | 54% [42%, 65%] | 0.28 / 0.84 / 0.01 | 5.6e-17 | 8.8e-12 |

Cross-grip ρ variance, Blind/φ: 1.30× [0.73, 2.09]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
