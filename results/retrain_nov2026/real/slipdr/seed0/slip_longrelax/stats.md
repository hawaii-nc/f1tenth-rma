### results/retrain_nov2026/real/slipdr/seed0/slip_longrelax/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.56 [0.46, 0.65] | 2.56 | 0.550 [0.530, 0.573] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.32 | 0.687 [0.651, 0.724] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.53 | 0.467 [0.461, 0.473] |
| oracle | 0.4 | 100 | 0.04 [0.02, 0.10] | 2.27 | 0.494 [0.485, 0.503] |
| phi | 0.6 | 100 | 0.02 [0.01, 0.07] | 2.53 | 0.474 [0.466, 0.485] |
| phi | 0.4 | 100 | 0.67 [0.57, 0.75] | 2.36 | 0.630 [0.601, 0.661] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 91% [85%, 96%] | 0.02 / 0.56 / 0.00 | 2.2e-16 | 2.1e-17 |
| 0.4 | 30% [19%, 40%] | 0.67 / 0.86 / 0.04 | 3.8e-06 | 0.00025 |

Cross-grip ρ variance, Blind/φ: 0.77× [0.46, 1.17]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **FAIL**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **FAIL**
- H3 (cross-grip variance ratio >= 10): **FAIL**
