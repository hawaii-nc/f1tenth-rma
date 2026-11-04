### results/retrain_nov2026/real/robustness/slip_fast/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.54 [0.44, 0.63] | 2.56 | 0.550 [0.530, 0.572] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.32 | 0.688 [0.652, 0.725] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.53 | 0.466 [0.461, 0.473] |
| oracle | 0.4 | 100 | 0.03 [0.01, 0.08] | 2.36 | 0.506 [0.498, 0.514] |
| phi | 0.6 | 100 | 0.01 [0.00, 0.05] | 2.53 | 0.472 [0.464, 0.482] |
| phi | 0.4 | 100 | 0.43 [0.34, 0.53] | 2.39 | 0.592 [0.568, 0.620] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 93% [87%, 98%] | 0.01 / 0.54 / 0.00 | 4.4e-16 | 1e-17 |
| 0.4 | 53% [41%, 63%] | 0.43 / 0.86 / 0.03 | 2.3e-13 | 8.9e-10 |

Cross-grip ρ variance, Blind/φ: 1.32× [0.78, 2.07]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
