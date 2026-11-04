### results/retrain_nov2026/real/robustness/slip_slow/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.53 [0.43, 0.62] | 2.57 | 0.546 [0.527, 0.568] |
| blind | 0.4 | 100 | 0.86 [0.78, 0.91] | 2.32 | 0.687 [0.651, 0.724] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.52 | 0.467 [0.461, 0.473] |
| oracle | 0.4 | 100 | 0.02 [0.01, 0.07] | 2.20 | 0.494 [0.484, 0.504] |
| phi | 0.6 | 100 | 0.02 [0.01, 0.07] | 2.54 | 0.476 [0.468, 0.487] |
| phi | 0.4 | 100 | 0.59 [0.49, 0.68] | 2.36 | 0.616 [0.589, 0.646] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 88% [81%, 93%] | 0.02 / 0.53 / 0.00 | 1.8e-15 | 1.5e-17 |
| 0.4 | 37% [26%, 47%] | 0.59 / 0.86 / 0.02 | 1.5e-08 | 2.6e-06 |

Cross-grip ρ variance, Blind/φ: 1.01× [0.62, 1.52]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **FAIL**
- H3 (cross-grip variance ratio >= 10): **FAIL**
