### results/retrain_nov2026/real/slipdr/seed2/slip_none/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.30 [0.22, 0.40] | 2.59 | 0.518 [0.504, 0.534] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.38 | 0.669 [0.635, 0.704] |
| oracle | 0.6 | 100 | 0.01 [0.00, 0.05] | 2.53 | 0.465 [0.460, 0.470] |
| oracle | 0.4 | 100 | 0.10 [0.06, 0.17] | 2.48 | 0.517 [0.510, 0.525] |
| phi | 0.6 | 100 | 0.04 [0.02, 0.10] | 2.57 | 0.484 [0.476, 0.493] |
| phi | 0.4 | 100 | 0.54 [0.44, 0.63] | 2.41 | 0.617 [0.589, 0.648] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 64% [55%, 72%] | 0.04 / 0.30 / 0.01 | 2.2e-07 | 5.9e-16 |
| 0.4 | 34% [22%, 46%] | 0.54 / 0.86 / 0.10 | 9.3e-10 | 2.5e-05 |

Cross-grip ρ variance, Blind/φ: 1.28× [0.89, 1.79]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
