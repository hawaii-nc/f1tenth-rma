### results/retrain_nov2026/real/slipdr/seed0/slip_fast/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.54 [0.44, 0.63] | 2.56 | 0.550 [0.530, 0.572] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.32 | 0.688 [0.652, 0.725] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.53 | 0.466 [0.461, 0.473] |
| oracle | 0.4 | 100 | 0.03 [0.01, 0.08] | 2.36 | 0.506 [0.498, 0.514] |
| phi | 0.6 | 100 | 0.01 [0.00, 0.05] | 2.51 | 0.465 [0.457, 0.475] |
| phi | 0.4 | 100 | 0.36 [0.27, 0.46] | 2.38 | 0.599 [0.572, 0.629] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 98% [93%, 100%] | 0.01 / 0.54 / 0.00 | 4.4e-16 | 1.1e-17 |
| 0.4 | 49% [37%, 60%] | 0.36 / 0.86 / 0.03 | 1.8e-15 | 5.3e-10 |

Cross-grip ρ variance, Blind/φ: 1.05× [0.61, 1.66]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
