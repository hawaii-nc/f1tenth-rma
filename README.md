# F1TENTH-RMA

Rapid Motor Adaptation for a 1/10-scale race car. The car estimates its tire grip from its own motion (no friction sensor, no map) and adjusts how hard it drives.

Nathan Chong, advised by Prof. Venkata Prashant Modekurthy. NSF REU Site: Smart Cities (Award #2349616), University of Nevada, Las Vegas, Summer 2026.

This repo has everything from the project in one place: training code, the final checkpoints, the E0–E5 evaluation scripts, the ROS 2 code that runs on the car, the real-car analysis, and the notes needed to keep going. It replaces my earlier [`research_ws`](https://github.com/hawaii-nc/research_ws) and [`f1tenth-vader-deployment`](https://github.com/hawaii-nc/f1tenth-vader-deployment) repos.

**If you are picking this project up, start with [docs/HANDOFF.md](docs/HANDOFF.md).**

## How it works

RMA ([Kumar et al., RSS 2021](https://arxiv.org/abs/2107.04034)) trains in two phases. I followed the quadcopter version from [Zhang et al. (IEEE T-RO 2025)](https://arxiv.org/abs/2409.12949).

1. **Phase 1.** A PPO policy π(x, z) is trained in simulation with imitation from a Pure Pursuit expert. It gets the true physics `e` (grip, mass, inertia, motor gains, actuator delays), compressed by an encoder into an 8-D vector `z = μ(e)`.
2. **Phase 2.** A small 1-D CNN φ learns to predict `z` from the last 50 state–action pairs. On the car, `ẑ = φ(history)` replaces `μ(e)`, so the car works out its own condition from how it has been driving.

The policy only sees 5 motion signals and 108 LiDAR ranges (113 numbers). It gets no map, pose or racing line, so it runs on any track.

The safety question: when grip drops, does the car keep a steady safety margin instead of a steady speed? I measure that with friction-circle utilization, ρ = √(a_lat² + a_long²) / (μg), the fraction of the available grip the car is using.

## Results (November 2026, branch `retrain-fixed-and-tire-model`)

| Question | Answer | Where |
|---|---|---|
| Can the car read grip from normal driving? | **No**, not in this simulator: with its actions independent of grip, its motion history carries no grip information (R² ≈ 0, three tire models). July's weak estimate was leakage from the expert's own driving | RESULTS_NOV2026 §4 |
| What fixes it? | A short **active probe** (speed or braking pulse on straights) that asks the tires for more than low grip can give. Grip R² 0.89–0.93 | §4 |
| Does adapting beat driving slower? | **Yes, with the probe.** At grip 0.4: 2–8% crashes vs 33–47% for a non-adaptive car matched to the same speed, 3 seeds; no fixed speed limit matches both its speed and safety | §4, Fig. 2 |
| With the car's real sensors and racing speeds? | Grip R² 0.84–0.87; at equal speed, 0–5% vs 33–56% crashes at grip 0.6 and 28–39% vs 84–86% at grip 0.4 | §6 |
| Robust to the unknown wheel slip? | With slip randomized in training: beats the non-adaptive car in all 30 conditions; misses the pre-registered margin on one seed in the two hardest | §7–8 |
| Real car? | July pilot only (earlier pipeline). The one-session probe test is ready: `tools/real_car/`, docs/REAL_CAR_PROBE_PLAN.md | |

Paper: `paper/latex/main.pdf`. Everything was pre-registered first: docs/PREREGISTRATION_NOV2026.md. The July numbers (44% gap closure etc., [docs/RESULTS.md](docs/RESULTS.md)) came from a pipeline with bugs and are superseded.

## Layout

```
src/f1tenth_research/   training package: envs, models, PPO+IL and φ training, experts,
                        metrics (ρ, probes), safety shield, evaluation harness
src/rma_deploy_pkg/     ROS 2 node that drives the real car (VADER) or Gazebo
checkpoints/final/      phase1_v42.pt (policy) + phase2_crashtol_clean.pt (φ, 50-step history)
checkpoints/archive/    older policies, see checkpoints/README.md
configs/                training configs, exported from the checkpoints themselves
experiments/            E0–E5 scripts and run_all.sh
analysis/               real-car tire statistics, plots for the paper
deploy/                 scripts for the car, joystick trial logger, install checklist
maps/                   AUT/ESP/GBR/MCO; tools/prepare_tracks.py builds all 14 tight tracks
tools/                  checkpoint inspector, track builder
docker/                 ROS 2 Foxy + f110_gym + PyTorch image
docs/                   results, protocol, setup, hand-off, bug log
paper/                  workshop paper draft and BibTeX
tests/                  pytest suite; CI also runs every experiment on a small fake simulator
```

## Quick start

```bash
pip install -r requirements-dev.txt
pytest -q tests
python tools/inspect_checkpoint.py checkpoints/final/phase1_v42.pt
```

The experiments need f110_gym, which requires Python 3.8, gym 0.19 and numpy ≤ 1.22. The Docker image handles that:

```bash
docker build -t f1tenth-rma -f docker/Dockerfile .
docker run --rm -it -v $PWD:/f1tenth-rma f1tenth-rma
python tools/prepare_tracks.py
python experiments/e1_e2_calibration.py -n 100
python analysis/plot_results.py results/
```

Training, deploying to the car, and the real-car trial workflow are in [docs/REPRODUCE.md](docs/REPRODUCE.md).

## Docs

- [HANDOFF.md](docs/HANDOFF.md): where things stand, what to do next, who to ask
- [RESULTS.md](docs/RESULTS.md): every number and where it came from
- [EXPERIMENTS.md](docs/EXPERIMENTS.md): E0–E5 protocol and pre-registered hypotheses
- [REPRODUCE.md](docs/REPRODUCE.md): setup, training, evaluation, deployment
- [BUGS_AND_LESSONS.md](docs/BUGS_AND_LESSONS.md): bugs found so far and how they were fixed
- [SIM_FIDELITY.md](docs/SIM_FIDELITY.md): what the simulator's tire model can and can't show
- [RECONSTRUCTION.md](docs/RECONSTRUCTION.md): which parts are the original lab code and which were rebuilt
- [REWARD_HISTORY.md](docs/REWARD_HISTORY.md): how the reward changed and why
- [HARDWARE.md](docs/HARDWARE.md): the car, its software, the test tracks

## Citing

See [CITATION.cff](CITATION.cff). References are in [paper/references.bib](paper/references.bib).

## Acknowledgements

Thanks to Prof. Modekurthy for advising this work, to Ederic Oytas for help with the lab and the VADER car, and to the UNLV Smart Cities REU. Supported by NSF Award #2349616.

## License

Code is MIT ([LICENSE](LICENSE)). The AUT/ESP/GBR/MCO maps are from [BDEvan5/f1tenth_benchmarks](https://github.com/BDEvan5/f1tenth_benchmarks) (Apache-2.0). The other ten tracks come from [f1tenth/f1tenth_racetracks](https://github.com/f1tenth/f1tenth_racetracks) (GPL-3.0) and are downloaded by `tools/prepare_tracks.py`, not stored here.
