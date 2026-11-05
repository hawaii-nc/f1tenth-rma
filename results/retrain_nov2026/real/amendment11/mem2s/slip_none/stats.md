### results/retrain_nov2026/real/amendment11/mem2s/slip_none/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.56 [0.46, 0.65] | 2.56 | 0.548 [0.528, 0.569] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.37 | 0.676 [0.642, 0.711] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.53 | 0.468 [0.462, 0.474] |
| oracle | 0.4 | 100 | 0.00 [0.00, 0.04] | 2.20 | 0.507 [0.500, 0.514] |
| phi | 0.6 | 100 | 0.05 [0.02, 0.11] | 2.49 | 0.486 [0.470, 0.505] |
| phi | 0.4 | 100 | 0.34 [0.25, 0.44] | 2.32 | 0.634 [0.598, 0.671] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 77% [62%, 93%] | 0.05 / 0.56 / 0.00 | 8.9e-16 | 1.9e-16 |
| 0.4 | 25% [18%, 34%] | 0.34 / 0.86 / 0.00 | 8.9e-16 | 1.6e-11 |

Cross-grip ρ variance, Blind/φ: 0.76× [0.56, 0.95]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **FAIL**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
