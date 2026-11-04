### results/retrain_nov2026/real/slipdr/seed1/slip_none/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 0.6 | 100 | 0.41 [0.32, 0.51] | 2.58 | 0.537 [0.516, 0.560] |
| blind | 0.4 | 100 | 0.84 [0.76, 0.90] | 2.34 | 0.677 [0.643, 0.713] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 2.50 | 0.464 [0.459, 0.469] |
| oracle | 0.4 | 100 | 0.00 [0.00, 0.04] | 2.33 | 0.506 [0.498, 0.513] |
| phi | 0.6 | 100 | 0.03 [0.01, 0.08] | 2.52 | 0.474 [0.467, 0.481] |
| phi | 0.4 | 100 | 0.38 [0.29, 0.48] | 2.35 | 0.592 [0.568, 0.617] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 0.6 | 87% [80%, 92%] | 0.03 / 0.41 / 0.00 | 7.3e-12 | 5.5e-16 |
| 0.4 | 50% [39%, 60%] | 0.38 / 0.84 / 0.00 | 5.7e-14 | 4e-10 |

Cross-grip ρ variance, Blind/φ: 1.41× [0.82, 2.22]

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
