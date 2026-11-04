### results/retrain_nov2026/real/robustness/slip_none/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.56 [0.46, 0.65] | 2.56 | 0.548 [0.528, 0.569] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.37 | 0.676 [0.642, 0.711] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.53 | 0.468 [0.462, 0.474] |
| oracle | 0.4 | 100 | 0.00 [0.00, 0.04] | 2.20 | 0.507 [0.500, 0.514] |
| phi | 0.6 | 100 | 0.52 [0.42, 0.62] | 2.55 | 0.549 [0.530, 0.570] |
| phi | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.34 | 0.682 [0.647, 0.717] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | -1% [-11%, 8%] | 0.52 / 0.56 / 0.00 | 0.96 | 0.47 |
| 0.4 | -3% [-12%, 4%] | 0.86 / 0.86 / 0.00 | 1 | 0.12 |

Cross-grip ρ variance, Blind/φ: 0.94× [0.73, 1.20]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **FAIL**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **FAIL**
- H3 (cross-grip variance ratio >= 10): **FAIL**
