# Checkpoints

All files load with `torch.load(..., weights_only=True)`. Each embeds its full training config:
`python tools/inspect_checkpoint.py <file>`.

| File | Contents | Obs | φ window | Steps | Notes |
|---|---|---:|---:|---:|---|
| `final/phase1_v42.pt` | π, V, μ | 113 | n/a | 16.0M | July 2026 base policy: the poster and the real-car pilot (paper §IV-E). Its encoder μ was never trained (bug C21, docs/BUGS_AND_LESSONS.md) |
| `final/phase2_crashtol_clean.pt` | φ | 115 in | 50 | 781k updates | July 2026 adaptation module, paired with v42 |

**These are not the paper's models.** The paper's models are in `runs/` ([runs/README.md](../runs/README.md)). The two files above stay because the real-car pilot used them the November configs inherit their settings (`configs/final_*.yaml`), and `tests/test_checkpoints.py` loads them. Older June/July checkpoints (v27, v28, v30, the June 36-beam baseline) are on the branch `archive/full-record-nov2026`.

Networks: π and V are 3-layer MLPs (256 hidden) on [obs, z]. μ is 7 → 128 → 128 → 8. φ is a Conv1d stack (115 → 32 → 32 → 8 channels, kernel 5, same padding) → FC (8k → 128 → 8).

The optimizer state is included, so training can resume from any of these.
