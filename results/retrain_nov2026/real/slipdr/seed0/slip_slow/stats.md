### results/retrain_nov2026/real/slipdr/seed0/slip_slow/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.53 [0.43, 0.62] | 2.57 | 0.546 [0.527, 0.568] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.32 | 0.687 [0.651, 0.724] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.52 | 0.467 [0.461, 0.473] |
| oracle | 0.4 | 100 | 0.02 [0.01, 0.07] | 2.20 | 0.494 [0.484, 0.504] |
| phi | 0.6 | 100 | 0.01 [0.00, 0.05] | 2.51 | 0.469 [0.461, 0.479] |
| phi | 0.4 | 100 | 0.48 [0.38, 0.58] | 2.35 | 0.616 [0.588, 0.647] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 98% [92%, 100%] | 0.01 / 0.53 / 0.00 | 8.9e-16 | 9.1e-18 |
| 0.4 | 37% [25%, 48%] | 0.48 / 0.86 / 0.02 | 7.3e-12 | 1.5e-06 |

Cross-grip ρ variance, Blind/φ: 0.92× [0.54, 1.43]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
