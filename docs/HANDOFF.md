# Hand-off: continuing the project

For the student taking over the experiments, and for Nathan when he picks this back up.

## Where things stand (October 2026)

- **Code:** complete and tested for the full pipeline: train Phase 1 → train φ → evaluate E0–E5 → deploy on VADER → analyse real-car trials. `pytest tests` passes, and CI also runs every experiment script on a fake simulator.
- **Results:** the July results are promising but **partial**, and they came from a pipeline with the physics-injection bugs in [BUGS_AND_LESSONS.md](BUGS_AND_LESSONS.md) §1. Treat them as pilot data.
- **Target venue:** an IEEE IV 2027 **workshop** paper (advisor's recommendation, Oct 5 2026). He judged the work not yet novel enough for a full paper and said more experiments are needed.
  - IV 2027 runs **June 15–18, 2027, in Perth, Australia**. Workshop papers are due **Feb 1, 2027**, notification March 1, camera-ready March 15 ([IV 2027 call for workshops](https://ieee-iv.org/2027/contributions/call-for-workshop-and-tutorials-proposals/)).
  - Specific workshops are announced after the Dec 1, 2026 proposal deadline. Pick one about learning, safety, or racing / small-scale platforms once the list is out.

## Day one

1. Read this file, then [RESULTS.md](RESULTS.md) and [BUGS_AND_LESSONS.md](BUGS_AND_LESSONS.md) (30 min).
2. `pip install -r requirements-dev.txt && pytest -q tests`. Everything should pass on any laptop.
3. Build the Docker image and run `python tools/prepare_tracks.py` ([REPRODUCE.md](REPRODUCE.md) §0–1).
4. Run `python experiments/e0_grip_gate.py -n 5`, then `python analysis/plot_results.py results/`. If you get a figure, the whole pipeline works.
5. Ask Prof. Modekurthy for lab-machine access and Ederic Oytas for time with the car.

## Not in this repo (ask Nathan)

| Item | Where it is | Why you might need it |
|---|---|---|
| Final lab training code (July) | Lab training machine, `/research_ws/src/f1tenth_research/` | Compare with the rebuilt parts listed in [RECONSTRUCTION.md](RECONSTRUCTION.md) |
| Raw E0–E5 results from July | Lab training machine | The *reported* numbers in RESULTS.md |
| 100-step φ checkpoint | Lab training machine (was training on July 21) | E3 window ablation |
| On-car logs (`rma_data_*.csv`, `rma_trial_log_*.csv`) | VADER home directory | Re-deriving the real-car table with `analysis/real_car/tire_stats.py` |
| Poster (PDF and source slides) | Nathan's Google Drive | Figures and wording for the paper |
| Camera-ready paper draft (IEEE format, sent to the advisor Sep 20, 2026) | Nathan's email / Overleaf | Starting point for the workshop submission; `paper/workshop_draft.md` is a text version |
| Paper 2 methodology, project record, reward history (full versions) | Nathan's Google Drive | Condensed into docs/EXPERIMENTS.md, docs/REWARD_HISTORY.md |

## Priority order to Feb 1, 2027

Ordered by value per hour. Items 1–4 make the existing claims trustworthy, 5–7 make the paper stronger, and 8+ are stretch goals.

| # | Task | Why | Effort |
|---|---|---|---|
| 1–3 | **One command:** `bash tools/retrain_fixed.sh` (in tmux, in Docker; try `QUICK=1` first). It runs `pytest` and `tools/check_physics_injection.py` (confirms μ reaches the real f110_gym), retrains φ with the fixed disturbance + buffer (C1, C2, C8, C9) against `phase1_v42.pt`, then runs E0–E5 with the new φ and the July φ side by side into `results/<tag>/{new,old}/` | φ's labels were wrong in the old pipeline, so this is the most likely place for a real improvement over R² ≈ 0.08. It also turns "pre-fix" numbers into citable ones, with the old φ kept as an ablation | 2–3 days compute |
| 4 | **E3** with the new φ (k = 50; `retrain_fixed.sh` already runs this) and a k = 100 φ | The only experiment with no result yet; a window-length ablation is cheap and makes a good figure | 1–2 days |
| 5 | **Raise the speed cap** (`max_velocity` 3 → 5–6 on full-scale tracks) and retrain Phase 1 | At ρ ≈ 0.2 the car is never near the limit, so no safety claim is possible. The poster names this as the first open item | 2–3 days compute |
| 6 | **Saturating-tire robustness check**: the tire model is now implemented (`--tire-model friction_circle`, see [SIM_FIDELITY.md](SIM_FIDELITY.md)). Run `TIRE_MODEL=friction_circle bash tools/retrain_fixed.sh`, or just the experiments with the existing checkpoints | Pre-empts the obvious reviewer objection to a linear tire model, and is the first step toward the advisor's "learn on the fly on the real car" full-paper idea | 1–2 days compute |
| 7 | **Real car: no-adaptation baseline on the same four tire wraps, plus measured μ per wrap** (inclined plane or skidpad) | The poster's two named open items. Hallucination on the real car (E4, pure software) is the cheapest strong real-world result | 1–2 lab days |
| 8 | Safety shield on vs off (E1/E2 with `--shield`); "learned vs enforced rules" | A publishable question named in the project record | 2 days |
| 9 | Gazebo Tier 2 (E1, E2, E4 only) | Independent physics engine | 1 week |
| 10 | Track-reweighting curriculum, Phase 1 retrain | Only if Phase 1 is being retrained anyway | 1 day |

## Standing constraints (do not break these)

- **φ never sees map-specific inputs.** No raceline, no pose, no waypoints. The policy observation is 5 + 108 LiDAR, and φ's input is observation + action.
- **Do not trust the raceline `psi` column.** It is 90° off; compute headings with arctan2.
- **Do not use AsyncVectorEnv with f110_gym in Docker.** Use `num_envs: 1`.
- **Do not commit per-epoch checkpoints.** Curate into `checkpoints/`.
- **Do not assume the simulator punishes speed.** f110_gym's stock tires never saturate. Use `tire_model: friction_circle` when that matters (see SIM_FIDELITY.md).
- **Run anything longer than ~10 min in tmux**, not with `nohup &`.
- **Before any long run:** check per-term reward signs at small scale (`eval/sanity_check_rollout.py`), and check that `expert_actions` is non-empty (`tests/test_training_smoke.py` shows how).
- **The real car:** secure it (wheels off the ground) for first tests. Hold R2 to engage; release R2, or hold L1, for manual override.

## Working style that worked

- Edit in VS Code → push → pull on the lab machine → run in tmux → `grep "Avg Reward" train.log`.
- Judge driving by crash rate and centerline deviation, never by reward totals.
- For every experiment, write the pre-registered prediction down *before* running it (methodology Part G).

## People and access

- **Advisor:** Prof. Venkata Prashant Modekurthy (UNLV CS). He wants the code on GitHub so another student can run the experiments.
- **Lab and hardware support:** Ederic Oytas, TBE B150. He handles VADER software installs (the car has no internet on campus) and can help with scp, slam_toolbox, and the F1TENTH particle filter (its dependencies are already on the car).
- **Lab machines:** the lab training machine (Docker + noVNC) and the Dell in TBE B150. Leave a sticky note when you leave training running, and switch the power strip off otherwise.
- **Hardware upgrade:** a Jetson Orin AGX was ordered in July (the Orin NX had a 12-week wait). The power board (AE170_PDU_02.04, 19 V / 4 A = 76 W) was checked against the Orin NX's 10–25 W; **re-check it against the AGX's power envelope** before swapping.

## If you only have one week

Run `bash tools/retrain_fixed.sh` (items 1–3). That turns the existing poster story (44% gap closure, 1.25× steadier margin, real-car p-values) into numbers produced by a pipeline without known bugs. Whether they go up or down, that is the honest version of the paper.
