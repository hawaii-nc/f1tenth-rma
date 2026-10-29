# Checkpoints

All files load with `torch.load(..., weights_only=True)`. Each embeds its full training config:
`python tools/inspect_checkpoint.py <file>`.

| File | Contents | Obs | φ window | Steps | Notes |
|---|---|---:|---:|---:|---|
| `final/phase1_v42.pt` | π, V, μ | 113 | n/a | 16.0M | **Final base policy**: 14 × tight tracks, 3 m/s. Used for the poster and the real car |
| `final/phase2_crashtol_clean.pt` | φ | 115 in | 50 | 781k updates | **Final adaptation module**, paired with v42 |
| `archive/phase1_v27.pt` | π, V, μ | 113 | n/a | 10.0M | 4 tight tracks |
| `archive/phase1_v28.pt` | π, V, μ | 113 | n/a | 40.0M | 14 tight tracks; first real-car test policy |
| `archive/phase1_v30.pt` | π, V, μ | 113 | n/a | 40.0M | Config sets a 100-step φ window |
| `archive/phase2_v27.pt` | φ | 43 in | 10 | 391k | **Input is 43-D**, so it is *not* compatible with the 113-D policies; it pairs with an older 41-D policy |
| `archive/phase2_v28.pt` | φ | 115 in | 10 | 281k | Pairs with v28 |
| `archive/paper1_june_phase1_lidar36.pt` | π, V, μ | 41 | n/a | 2.0M | June multi-map baseline (36 beams, 8 m/s, AUT only) |

Networks: π and V are 3-layer MLPs (256 hidden) on [obs, z]. μ is 7 → 128 → 128 → 8. φ is a Conv1d stack (115 → 32 → 32 → 8 channels, kernel 5, same padding) → FC (8k → 128 → 8).

The optimizer state is included, so training can resume from any of these.
