### Amendment 13, arm T: φ retrained with the cautious start (reference: amendment 12 φ_DR + cautious start)

| seed | μ | crash reference / retrained | speed reference / retrained (m/s) | p |
|---:|---:|---|---|---:|
| 0 | 1.0 | 0.01 / **0.01** | 2.48 / 2.50 | 1 |
| 0 | 0.6 | 0.00 / **0.00** | 2.49 / 2.50 | 1 |
| 0 | 0.4 | 0.27 / **0.40** | 2.49 / 2.49 | 0.0072 |
| 1 | 1.0 | 0.00 / **0.00** | 2.50 / 2.51 | 1 |
| 1 | 0.6 | 0.00 / **0.00** | 2.48 / 2.49 | 1 |
| 1 | 0.4 | 0.18 / **0.23** | 2.48 / 2.48 | 0.33 |
| 2 | 1.0 | 0.01 / **0.00** | 2.52 / 2.52 | 1 |
| 2 | 0.6 | 0.00 / **0.01** | 2.50 / 2.50 | 1 |
| 2 | 0.4 | 0.22 / **0.26** | 2.50 / 2.51 | 0.57 |

Pooled μ = 0.4 (N = 300, seeds [0, 1, 2]): 0.223 → 0.297 (drop -0.073, exact McNemar p = 0.0092); worst per-seed change +0.13.
E5 grip R² of the retrained φ: seed 0: 0.81, seed 1: 0.82, seed 2: 0.82.

- T1: **FAIL**
- T2: **PASS**
