### results/retrain_nov2026/real/robustness/slip_longrelax/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.56 [0.46, 0.65] | 2.56 | 0.550 [0.530, 0.573] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.32 | 0.687 [0.651, 0.724] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.53 | 0.467 [0.461, 0.473] |
| oracle | 0.4 | 100 | 0.04 [0.02, 0.10] | 2.27 | 0.494 [0.485, 0.503] |
| phi | 0.6 | 100 | 0.04 [0.02, 0.10] | 2.58 | 0.492 [0.481, 0.504] |
| phi | 0.4 | 100 | 0.79 [0.70, 0.86] | 2.36 | 0.644 [0.614, 0.676] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 70% [61%, 77%] | 0.04 / 0.56 / 0.00 | 8.9e-16 | 4.7e-15 |
| 0.4 | 22% [12%, 32%] | 0.79 / 0.86 / 0.04 | 0.016 | 0.0032 |

Cross-grip ρ variance, Blind/φ: 0.80× [0.51, 1.18]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **FAIL**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **FAIL**
- H3 (cross-grip variance ratio >= 10): **FAIL**
