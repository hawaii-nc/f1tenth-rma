### results/retrain_nov2026/probe/robustness/holdout_model/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 1.0 | 100 | 0.00 [0.00, 0.04] | 2.10 | 0.316 [0.313, 0.319] |
| blind | 0.8 | 100 | 0.00 [0.00, 0.04] | 2.10 | 0.389 [0.385, 0.393] |
| blind | 0.6 | 100 | 0.02 [0.01, 0.07] | 2.07 | 0.454 [0.446, 0.462] |
| blind | 0.4 | 100 | 0.56 [0.46, 0.65] | 1.99 | 0.559 [0.538, 0.582] |
| oracle | 1.0 | 100 | 0.00 [0.00, 0.04] | 2.10 | 0.316 [0.313, 0.320] |
| oracle | 0.8 | 100 | 0.00 [0.00, 0.04] | 1.90 | 0.370 [0.368, 0.373] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 1.62 | 0.397 [0.393, 0.401] |
| oracle | 0.4 | 100 | 0.00 [0.00, 0.04] | 1.26 | 0.390 [0.386, 0.393] |
| phi | 1.0 | 100 | 0.00 [0.00, 0.04] | 2.04 | 0.305 [0.302, 0.309] |
| phi | 0.8 | 100 | 0.00 [0.00, 0.04] | 1.89 | 0.368 [0.363, 0.372] |
| phi | 0.6 | 100 | 0.00 [0.00, 0.04] | 1.63 | 0.399 [0.393, 0.407] |
| phi | 0.4 | 100 | 0.03 [0.01, 0.08] | 1.31 | 0.424 [0.412, 0.440] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 1.0 | nan% [nan%, nan%] | 0.00 / 0.00 / 0.00 | 1 | 1.8e-17 |
| 0.8 | 84% [69%, 98%] | 0.00 / 0.00 / 0.00 | 1 | 1.8e-17 |
| 0.6 | 96% [89%, 100%] | 0.00 / 0.02 / 0.00 | 1 | 1.6e-17 |
| 0.4 | 80% [73%, 86%] | 0.03 / 0.56 / 0.00 | 8.9e-16 | 1.6e-17 |

Cross-grip ρ variance, Blind/φ: 4.03× [3.38, 4.74]

**WARNING: pseudo-replication** in 12 cells, e.g. blind μ=1.0: only 99 distinct outcomes among 100 episodes (deterministic replays?): CIs and p-values treat them as independent

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**
### results/retrain_nov2026/probe/robustness/main_model_on_holdout/e1_e2/run

| controller | grip | n | crash rate [95% CI] | mean speed | mean ρ [95% CI] |
|---|---:|---:|---|---:|---|
| blind | 1.0 | 100 | 0.08 [0.04, 0.15] | 2.11 | 0.319 [0.316, 0.322] |
| blind | 0.8 | 100 | 0.10 [0.06, 0.17] | 2.10 | 0.391 [0.388, 0.396] |
| blind | 0.6 | 100 | 0.17 [0.11, 0.26] | 2.07 | 0.456 [0.448, 0.466] |
| blind | 0.4 | 100 | 0.51 [0.41, 0.61] | 1.99 | 0.539 [0.523, 0.558] |
| oracle | 1.0 | 100 | 0.08 [0.04, 0.15] | 2.11 | 0.319 [0.316, 0.323] |
| oracle | 0.8 | 100 | 0.00 [0.00, 0.04] | 1.91 | 0.374 [0.371, 0.376] |
| oracle | 0.6 | 100 | 0.00 [0.00, 0.04] | 1.63 | 0.400 [0.397, 0.404] |
| oracle | 0.4 | 100 | 0.00 [0.00, 0.04] | 1.27 | 0.392 [0.389, 0.396] |
| phi | 1.0 | 100 | 0.00 [0.00, 0.04] | 1.99 | 0.302 [0.299, 0.306] |
| phi | 0.8 | 100 | 0.00 [0.00, 0.04] | 1.83 | 0.361 [0.357, 0.365] |
| phi | 0.6 | 100 | 0.00 [0.00, 0.04] | 1.54 | 0.388 [0.381, 0.397] |
| phi | 0.4 | 100 | 0.02 [0.01, 0.07] | 1.27 | 0.411 [0.402, 0.422] |

| grip | gap closed [95% CI] | crash φ / Blind / Oracle | McNemar p (Holm) | Wilcoxon ρ p (Holm) |
|---:|---|---|---:|---:|
| 1.0 | nan% [nan%, nan%] | 0.00 / 0.08 / 0.08 | 0.0078 | 8.7e-17 |
| 0.8 | 27% [6%, 46%] | 0.00 / 0.10 / 0.00 | 0.0039 | 1.6e-17 |
| 0.6 | 78% [66%, 91%] | 0.00 / 0.17 / 0.00 | 4.6e-05 | 1.6e-17 |
| 0.4 | 87% [82%, 92%] | 0.02 / 0.51 / 0.00 | 1.4e-14 | 1.6e-17 |

Cross-grip ρ variance, Blind/φ: 3.99× [3.45, 4.60]

**WARNING: pseudo-replication** in 12 cells, e.g. blind μ=1.0: only 99 distinct outcomes among 100 episodes (deterministic replays?): CIs and p-values treat them as independent

- G1 (gap closed >= 30% at 0.4, CI excludes 0): **PASS**
- H2 (phi crash <= blind crash - 0.30 at 0.4, McNemar p < .05): **PASS**
- H3 (cross-grip variance ratio >= 10): **FAIL**

### Across training seeds

| metric | holdout_model | main_model | mean ± SD |
|---|---|---|---|
| gap_closed @ μ=1.0 | nan | nan | nan ± nan |
| phi_crash @ μ=1.0 | 0.00 | 0.00 | 0.00 ± 0.00 |
| blind_crash @ μ=1.0 | 0.00 | 0.08 | 0.04 ± 0.06 |
| gap_closed @ μ=0.8 | 0.84 | 0.27 | 0.56 ± 0.40 |
| phi_crash @ μ=0.8 | 0.00 | 0.00 | 0.00 ± 0.00 |
| blind_crash @ μ=0.8 | 0.00 | 0.10 | 0.05 ± 0.07 |
| gap_closed @ μ=0.6 | 0.96 | 0.78 | 0.87 ± 0.13 |
| phi_crash @ μ=0.6 | 0.00 | 0.00 | 0.00 ± 0.00 |
| blind_crash @ μ=0.6 | 0.02 | 0.17 | 0.10 ± 0.11 |
| gap_closed @ μ=0.4 | 0.80 | 0.87 | 0.83 ± 0.05 |
| phi_crash @ μ=0.4 | 0.03 | 0.02 | 0.03 ± 0.01 |
| blind_crash @ μ=0.4 | 0.56 | 0.51 | 0.54 ± 0.04 |
| variance ratio Blind/φ | 4.03 | 3.99 | 4.01 ± 0.02 |
