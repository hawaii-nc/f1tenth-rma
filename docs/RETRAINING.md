# Retraining the full pipeline (November 2026)

The lab machine is no longer available, so everything was retrained from this repo in a 4-core CPU container (no GPU) on the **real f110_gym** (commit 4fdb9c7), not the CI fake simulator. This page records why everything was retrained, what changed, and how to reproduce it. Results are in [RESULTS_NOV2026.md](RESULTS_NOV2026.md).

## Why not just retrain φ?

The plan was to keep `phase1_v42.pt` and retrain only φ with the fixed disturbance. Running the pipeline on the real simulator for the first time showed that this wasn't possible:

1. **The July policy cannot drive the rebuilt environment.** At nominal grip with no noise, `phase1_v42.pt` crashes within about 100 steps (≈ 2 m) on every track, including the IMS oval, which the expert laps. Testing the obvious mismatches (flipped LiDAR, the car's 10 cm footprint margin, a 50 Hz policy, the June `v_des` scaling, a looser `ttc_thresh`) didn't fix it. The lab environment differed in ways that were never saved (see RECONSTRUCTION.md: tracks, spawn, noise and drift semantics are all reconstructions).
2. **The rebuilt environment itself had bugs** that no CI test could catch, because the fake simulator has no tracks: C16–C21 in [BUGS_AND_LESSONS.md](BUGS_AND_LESSONS.md). The spawn put cars inside walls. A uniform 35% scale made corners tighter than the car's turning circle. Scaled racelines ran inside the car's half-width of the wall. The parallel trainer mixed up environments, and the encoder μ never received a gradient.

So Phase 1 (π, μ, V), Phase 2 (φ) and every experiment were rerun on the fixed environment. **Numbers from this pipeline are not comparable one-to-one with the July poster**: different tracks (scale), training procedure (DAgger pre-training) and checkpoints. They are internally consistent and come from code with no known bugs.

## What changed relative to the July v42 recipe

| Item | July v42 | Retrained | Why |
|---|---|---|---|
| Tracks | 14 × 35% scale | 13 tracks, each at the smallest scale (0.35–0.70) at which Pure Pursuit laps it; Zandvoort dropped | At 35%, aut has a 0.24 m-radius hairpin vs the car's 0.74 m minimum turning radius; the expert crashed on 13/14 tracks. Zandvoort crashes the expert at the same point at every scale (map defect) |
| Expert waypoints | TUMFTM racelines (scaled) | Centerline | Scaled racelines pass within 9 cm of the wall; the car's half-width is 15.5 cm |
| Spawn | (0.7, 0) | Training: random point along the lap (+ drift heading); evaluation: start line | Fixed spawns meant the policy only ever saw the first metres of each track |
| Training | PPO + IL loss, 1 env | DAgger (6 × 100k steps, β = 1, ½, ¼, …), then PPO + IL (same schedule as v42), 4 envs. **Base policy = the checkpoint with the lowest closed-loop validation crash rate, which was the DAgger checkpoint** | PPO + IL from scratch never left the first metres (crash rate 0.99 after 1M steps). Plain behaviour cloning drifts; DAgger is the standard fix. DAgger alone: 0/39 validation crashes at grip 1.0/0.6/0.4. PPO fine-tuning raised training reward but also validation crashes (0.26 by epoch 50), so it was stopped there |
| Encoder μ | Never received a gradient (C21) | Trained by DAgger and by PPO/IL | |
| `max_episode_steps` (Phase 1) | 34,000 | 5,000 | The grip drop fires at 30–90% of the episode, so with 34k it almost never happened |
| Everything else | | Unchanged: networks, 113-D observation, rewards, randomization ranges, PPO hyperparameters, 16M PPO steps, Phase 2 config (k = 50, 800 episodes, 100 epochs, aux loss) | |

`configs/retrain_phase1.yaml` and `configs/retrain_phase2.yaml` hold the exact settings. Their headers list the differences from the July configs.

## How to reproduce

```bash
# simulator: f1tenth_gym @ 4fdb9c7 (Docker image, or PYTHONPATH=<checkout>/gym with gym 0.26 + numba)
python tools/prepare_tracks.py            # 13 drivable *_tight tracks (per-track scale)
tmux new -s retrain 'bash tools/retrain_all.sh 2>&1 | tee runs/retrain_all.log'
QUICK=1 bash tools/retrain_all.sh         # minutes-long smoke run of every stage
```

`tools/retrain_all.sh` is resumable (each stage is skipped if its output exists):

0. `pytest` + `tools/check_physics_injection.py` (μ reaches the simulated car; the right tire model is active)
1. Phase 1 → `runs/phase1_retrain/` (`--resume` continues from `latest.pt`), then `tools/validate_checkpoints.py` picks the base policy (lowest closed-loop crash rate on all tracks at grip 1.0/0.6/0.4; override with `PHASE1_CKPT=`)
2. Phase 2 → `runs/phase2_retrain/final.pt` (parallel data collection)
3. E0–E5 (E1/E2 split by grip across cores, merged with `tools/merge_e1_e2.py`) → `results/retrain_nov2026/linear/`
4. Tire robustness: E0 + E1/E2 under the friction-circle tire with the same checkpoints → `results/retrain_nov2026/friction_circle/`

On 4 CPU cores DAgger takes about 30 min (the full 16M PPO steps would add about 4 h), Phase 2 about 2–3 h, and the experiments about 3 h.

## Checks that made the difference (do these before any long run)

- Drive the **expert** on every track and require a full lap (`tools/prepare_tracks.py` docstring). If the expert can't lap a track, no policy will learn it.
- Evaluate the **deterministic policy** closed-loop after a few epochs, not just the training crash rate.
- Fit the IL labels **offline**: R² of the expert's steering from the observation. Low R² on expert-visited states means the labels and observations don't match. High R² there but bad closed-loop driving means you need DAgger.
