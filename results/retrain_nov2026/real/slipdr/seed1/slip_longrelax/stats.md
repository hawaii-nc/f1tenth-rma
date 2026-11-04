### results/retrain_nov2026/real/slipdr/seed1/slip_longrelax/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.44 [0.35, 0.54] | 2.58 | 0.537 [0.516, 0.561] |
| blind | 0.4 | 100 | 0.84 [0.76, 0.90] | 2.35 | 0.673 [0.639, 0.709] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.51 | 0.463 [0.458, 0.468] |
| oracle | 0.4 | 100 | 0.02 [0.01, 0.07] | 2.42 | 0.505 [0.499, 0.512] |
| phi | 0.6 | 100 | 0.03 [0.01, 0.08] | 2.52 | 0.469 [0.461, 0.478] |
| phi | 0.4 | 100 | 0.50 [0.40, 0.60] | 2.38 | 0.604 [0.578, 0.633] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 92% [84%, 97%] | 0.03 / 0.44 / 0.00 | 1.8e-12 | 5.8e-17 |
| 0.4 | 41% [29%, 52%] | 0.50 / 0.84 / 0.02 | 1.2e-10 | 1.1e-07 |

Cross-grip ρ variance, Blind/φ: 1.00× [0.58, 1.56]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
