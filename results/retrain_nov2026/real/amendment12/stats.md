### Amendment 12: cold start (φ_DR, default slip model)

| seed | μ | crash Oracle / φ / φ+cautious start / Blind / Blind+cautious start | speed φ / φ+cs (m/s) | crashes in first 2 s: φ / φ+cs | p (φ+cs vs φ) | p (φ+cs vs Blind+cs) |
|---:|---:|---|---|---|---:|---:|
| 0 | 1.0 | 0.02 / 0.00 / **0.01** / 0.02 / 0.02 | 2.53 / 2.48 | 0 / 0 | 1 | 1 |
| 0 | 0.6 | 0.00 / 0.01 / **0.00** / 0.56 / 0.51 | 2.51 / 2.49 | 1 / 0 | 1 | 8.9e-16 |
| 0 | 0.4 | 0.02 / 0.41 / **0.27** / 0.86 / 0.85 | 2.36 / 2.49 | 15 / 1 | 0.0013 | 6.9e-18 |
| 1 | 1.0 | 0.00 / 0.00 / **0.00** / 0.00 / 0.00 | 2.52 / 2.50 | 0 / 0 | 1 | 1 |
| 1 | 0.6 | 0.00 / 0.00 / **0.00** / 0.43 / 0.39 | 2.50 / 2.48 | 0 / 0 | 1 | 3.6e-12 |
| 1 | 0.4 | 0.00 / 0.25 / **0.18** / 0.84 / 0.82 | 2.39 / 2.48 | 11 / 0 | 0.17 | 1.1e-19 |
| 2 | 1.0 | 0.00 / 0.00 / **0.01** / 0.00 / 0.00 | 2.54 / 2.52 | 0 / 0 | 1 | 1 |
| 2 | 0.6 | 0.00 / 0.00 / **0.00** / 0.33 / 0.32 | 2.52 / 2.50 | 0 / 0 | 1 | 4.7e-10 |
| 2 | 0.4 | 0.09 / 0.33 / **0.22** / 0.86 / 0.84 | 2.38 / 2.50 | 14 / 0 | 0.019 | 4.3e-19 |

Pooled μ = 0.4 (N = 300): φ 0.330 → φ + cautious start 0.223 (drop 0.107, exact McNemar p = 2.1e-05); worst per-seed change -0.07.
Share of the φ–Oracle crash gap removed at μ = 0.4, per seed: 36%, 28%, 46%.

- C0 (reruns reproduce the published cells): **PASS**
- C1 (pooled drop ≥ 0.07, p < 0.05, no seed worse by > 0.02): **PASS**
- C2 (μ 1.0 and 0.6: crash ≤ φ + 0.03, speed ≥ φ − 0.05 m/s, every seed): **PASS**
- C3 (μ 0.4: φ+cs ≤ Blind+cs − 0.30, p < 0.05, every seed): **PASS**
