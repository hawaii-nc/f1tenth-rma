# What is original and what was reconstructed

The final training code ran in the lab training container and was never pushed. The public `research_ws` repo is a **mid-June snapshot**: 36/41/43-D observations, 8 m/s, single track. This repo rebuilds the final pipeline from three sources:

1. **The checkpoints themselves.** Every `.pt` file embeds its full training config (`tools/inspect_checkpoint.py`). That gives exact hyperparameters, tracks, observation settings and network shapes.
2. **The on-car deployment code** (`f1tenth-vader-deployment`, July 28), which pins down the deployed observation pipeline exactly.
3. **The project documents** (project record, IEEE draft, Paper 2 methodology, slides, poster).

## Inventory

| Component | Status | Confidence | Notes |
|---|---|---|---|
| Networks π, V, μ, φ (`models/`) | Original | High | All 8 checkpoints load unchanged |
| Final hyperparameters (`configs/final_*.yaml`) | Original | High | Exported verbatim from the checkpoints. `tests/test_checkpoints.py` checks they match |
| Deployed observation (`rma_deploy_pkg`) | Original, with bug fixes | High | Behaviour at default flags is unchanged (C12–C14 aside) |
| Env observation (113-D, max_velocity, LiDAR clip and normalise) | Updated | High | Matches the deployment node exactly. Test: `test_scan_preprocessing_matches_training` |
| Multi-track sampling (`environment.tracks`) | Rebuilt | High | Uniform per episode, plus a `set_track_weights()` hook |
| LiDAR noise (`lidar_noise_std`) and dropout (`lidar_dropout_prob`) | Rebuilt | Medium | Gaussian noise in *normalised* units; dropped beams read max range. The units of the original are unknown |
| `drift_spawn_prob` | Rebuilt | **Low** | Implemented as a ±0.35 rad spawn-heading perturbation. The original semantics are unknown |
| Mid-episode disturbance (`disturbance_friction_scale`, timing window) | Rebuilt **and fixed** | Medium | One drop per episode that really reaches the simulator (C1/C2) |
| Centerline-error reward term (`weight_centerline_error`) | Rebuilt | Medium | Named in the final config and the IEEE draft (§III-F) but absent from the June code |
| Track-reweighting curriculum (`track_reweight_interval`, `reweight_eval_episodes`, `track_weight_floor`) | **Not rebuilt** | n/a | The env exposes `set_track_weights()`; the training-loop logic is not written |
| Phase 2 auxiliary loss (`aux_loss_weight`, `aux_param_weights`) | Rebuilt | **Low** | A linear head ẑ → e with per-parameter weights (grip 3×). The real crashtol checkpoint has no aux-head weights, so the original may differ |
| "crashtol" Phase 2 data collection | **Unknown** | n/a | The name suggests episodes are kept after a crash. Ask before relying on it |
| 100-step φ (E3) | **Missing** | n/a | Was training on July 21. Not in any repo |
| TUMFTM racelines for the tight tracks | Rebuilt | Medium | `tools/prepare_tracks.py` scales the racetrack database's racelines. The lab's own optimizer outputs are not in the repo |
| E0–E5 scripts | Rebuilt from the methodology doc, slides and poster | Medium–High | The definitions follow the pre-registered protocol. The poster's 44% and 1.28× ratio are reproduced from its table by `tests/test_metrics.py` |
| Real-car tire statistics | Rebuilt | Medium | Mann–Whitney U on per-trial means. The exact poster aggregation was not preserved |
| Safety shield (ACDA + grip-adaptive speed) | New | n/a | Designed in project record §9.7 but never built |

## Recovering the originals

If you have access to the lab machine, copy these out and diff them against this repo:

- `/research_ws/src/f1tenth_research/f1tenth_research/` (the final training package)
- the Phase 2 crashtol collection script, and the 100-step φ checkpoint
- `/research_ws/maps/` (tight maps, centerlines, `racelines/`)
- E0–E5 result directories, which back the *reported* numbers in RESULTS.md
- on-car logs `~/rma_data_*.csv` and `~/rma_trial_log_*.csv` from VADER

Where the originals differ from the reconstruction, prefer the original *unless* the difference is one of the bugs C1–C15 in [BUGS_AND_LESSONS.md](BUGS_AND_LESSONS.md).
