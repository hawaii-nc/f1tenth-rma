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

## Results so far

| Question | Answer | Evidence |
|---|---|---|
| Does grip limit the car? | Yes. Crashes go up as grip goes down | E0, sim, N = 40 |
| Does adapting help? | Partly. φ closes 44% of the gap between the grip-blind and oracle controllers at μ = 0.4 | E1/E2, sim, N = 100 |
| Is the margin steadier? | 1.25–1.27× lower cross-grip ρ variance than the blind controller. The target I set beforehand was 10×, so this is a partial result | E2, N = 20/40/100 |
| Is the behaviour caused by the grip estimate? | Partly. Restoring φ moves behaviour 25% of the way back toward the safe side | E4, sim |
| Does it carry over to the real car? | Changing the tires changes the policy's steering (p = 0.0001) and yaw rate (p = 0.009), bare vs electrical tape, 81 trials | Real car |
| Can you read grip directly out of ẑ? | Only weakly (R² ≈ 0.08) | E5, needs a re-run |

Details and caveats are in [docs/RESULTS.md](docs/RESULTS.md).

The simulation numbers above came from the lab code in July. While putting this repo together I found bugs in that pipeline, most importantly that the mid-episode grip drop never reached the simulator's physics. I also found that f110_gym's tire model never saturates. Both are fixed or documented in [docs/BUGS_AND_LESSONS.md](docs/BUGS_AND_LESSONS.md) and [docs/SIM_FIDELITY.md](docs/SIM_FIDELITY.md), and the sim experiments need to be re-run with this code before the numbers go in a paper: `bash tools/retrain_fixed.sh` does the retraining and the re-runs in one go. A saturating (friction-circle) tire model is now available with `--tire-model friction_circle`.

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
