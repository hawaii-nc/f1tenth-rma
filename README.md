# F1TENTH-RMA: active probing makes tire grip observable for rapid motor adaptation

Code, trained models and raw results for the paper **`paper/latex/main.pdf`** (IEEE workshop format, 4 pages).

Nathan Chong, advised by Prof. Venkata Prashant Modekurthy. NSF REU Site: Smart Cities (Award #2349616), University of Nevada, Las Vegas, 2026.

**Picking this project up? Start with [docs/HANDOFF.md](docs/HANDOFF.md).**

## The paper in five lines

1. **Passive grip adaptation cannot work in F1TENTH simulation.** With the car's actions independent of grip, 0.5 s of motion history predicts grip with R² ≈ 0 (friction-circle and Fiala brush tires). Adaptation modules that seem to work are reading their own actions or just driving slowly.
2. **A brief active probe fixes it.** A 0.1 s speed pulse on straights asks the tires for more than low grip can give; grip R² rises to 0.89–0.93.
3. **With the probe, adaptation beats any fixed speed limit.** At grip 0.4 the adaptive car crashes 2–8% vs 33–47% for a non-adaptive car matched to its measured speed, on 3 training seeds, and it transfers to unseen tracks.
4. **It survives the car's real sensors at racing speed** (wheel-odometry speed with slip, kinematic yaw rate, 40 Hz LiDAR, braking probe): grip R² 0.84–0.87; 28–39% vs 84–86% crashes at grip 0.4.
5. **It depends on the wheel-slip model;** randomizing that model in training beats the non-adaptive car in all 30 slip-model × seed × grip comparisons. Real-car probe results are not shown yet: the one-session test is ready (docs/REAL_CAR_PROBE_PLAN.md).

Every hypothesis and threshold was registered before its runs ([docs/PREREGISTRATION_NOV2026.md](docs/PREREGISTRATION_NOV2026.md)). Failed checks are reported, not dropped.

## Where each result in the paper comes from

| Paper | Data (`results/retrain_nov2026/`) | Made by |
|---|---|---|
| §IV-A: grip not observable without excitation | numbers in [RESULTS_NOV2026 §4](docs/RESULTS_NOV2026.md) | `tools/phi_diagnostic.py` |
| §IV-A: standard RMA fails (original, P2, capped Blind) | `linear/`, `p2_friction_circle/`, `robustness_fc/` | `tools/retrain_all.sh`, `tools/remedies_suite.sh`, `tools/robustness_suite.sh` |
| Table I, Fig. 1 left: configuration Q | `probe/seed{0,1,2}/` | `tools/probe_suite.sh` |
| Fig. 2: speed-limit frontier | `probe/seed0/cap_sweep_*`, `speed_matched_measured/` | `tools/cap_sweep.sh`, `tools/speed_matched_test.py` |
| Fig. 1 right: configuration R (car sensors) | `real/seed{0,1,2}/` | `tools/real_suite.sh` |
| Fig. 4: wheel-slip robustness | `real/robustness/slip_*`, `real/slipdr/` | `tools/real_robustness.sh`, `tools/slipdr_suite.sh` |
| Fig. 3: grip R² by configuration | `*/e5/` of the above | `experiments/e5_signal.py` |
| §V: memory and probe-rate tests | `real/amendment11/` | `tools/amendment11_suite.sh` |
| Probe-test prediction | `real/probe_test_sim/` | `tools/real_car/simulate_probe_trials.py` |
| §IV-E: July real-car pilot | July trial CSVs (lab machine) | `analysis/real_car/tire_stats.py` |

Figures: `python tools/make_figures.py` (reads only `results/`). Paper: `cd paper/latex && pdflatex main && bibtex main && pdflatex main && pdflatex main`. Statistics: `tools/stats.py` (Wilson CIs, bootstrap, exact McNemar, Holm). Every run directory has `episodes.csv`, `summary.json` and `provenance.json` (git commit, library versions, checkpoint SHA-256).

## Trained models

All in `runs/`; [runs/README.md](runs/README.md) lists what each one is.

**For the car:** `runs/real_phase1_seedN/final.pt` (base policy) + `runs/real_phase2_slipdr_seedN/final.pt` (adaptation module, slip model randomized), N = 0, 1, 2. Run the node at 100 Hz with the probe on (`--probe 1`); see [docs/SIM_TO_REAL.md](docs/SIM_TO_REAL.md).

## Method

RMA ([Kumar et al., RSS 2021](https://arxiv.org/abs/2107.04034)) in two phases. **Phase 1:** a policy π(x, z) learns by DAgger from a grip-aware Pure Pursuit expert, with the true physics compressed to an 8-D vector z = μ(e). **Phase 2:** a 1-D CNN φ learns to predict z from the last 50 steps (0.5 s) of observations and actions. On the car, φ replaces μ. The policy sees 5 motion signals and 108 LiDAR ranges: no map, pose or racing line. Simulation: f1tenth_gym at 100 Hz with an added friction-circle tire.

## Layout

```
paper/                  LaTeX source + PDF, figures, BibTeX, text draft
results/retrain_nov2026/ raw results behind every number in the paper
runs/                   trained models (final.pt per run)
src/f1tenth_research/   environment, tire models, randomization, sensor model, probe,
                        DAgger and φ training, metrics, evaluation harness
src/rma_deploy_pkg/     ROS 2 node for the real car (100 Hz, probe, safety shield)
experiments/            E0-E5 evaluation scripts
tools/                  suites that produced the results, figures, statistics, real-car test
configs/                training and evaluation configs
docs/                   results, pre-registration, sim-to-real, real-car test plan, hand-off
checkpoints/final/      July 2026 checkpoint used in the real-car pilot (see checkpoints/README.md)
analysis/, deploy/      real-car pilot analysis; car scripts and install checklist
docker/, tests/         reproducible environment; pytest suite (CI runs it)
```

## Reproduce

```bash
pip install -r requirements-dev.txt && pytest -q tests        # no simulator needed
docker build -t f1tenth-rma -f docker/Dockerfile .           # f1tenth_gym needs Python 3.8
python tools/prepare_tracks.py                               # the 13 scaled tracks
```

Full training and evaluation: [docs/REPRODUCE.md](docs/REPRODUCE.md) and [docs/RETRAINING.md](docs/RETRAINING.md). Everything ran on a 4-core CPU.

## Docs

- [RESULTS_NOV2026.md](docs/RESULTS_NOV2026.md): every result, starting with the final claims
- [PREREGISTRATION_NOV2026.md](docs/PREREGISTRATION_NOV2026.md): hypotheses and amendments, written before each run
- [SIM_TO_REAL.md](docs/SIM_TO_REAL.md) and [REAL_CAR_PROBE_PLAN.md](docs/REAL_CAR_PROBE_PLAN.md): what transfers to the car and how to test it
- [BUGS_AND_LESSONS.md](docs/BUGS_AND_LESSONS.md): bugs found and fixed (including why the July results are superseded)
- [HANDOFF.md](docs/HANDOFF.md), [REPRODUCE.md](docs/REPRODUCE.md), [RETRAINING.md](docs/RETRAINING.md), [EXPERIMENTS.md](docs/EXPERIMENTS.md), [SIM_FIDELITY.md](docs/SIM_FIDELITY.md), [RECONSTRUCTION.md](docs/RECONSTRUCTION.md), [HARDWARE.md](docs/HARDWARE.md)

## Archive

Earlier work is kept on two branches and is not part of the paper:

- **`archive/july-2026-pipeline`**: the July 2026 summer pipeline (poster results, July checkpoints), as imported and bug-fixed in October.
- **`archive/full-record-nov2026`**: the complete November record before this cleanup, including superseded start-line evaluations, June/July checkpoints, the July results page and the Gazebo node.

The July poster numbers (e.g. 44% gap closure) came from a pipeline with an untrained encoder and other bugs (docs/BUGS_AND_LESSONS.md, C21) and should not be cited. The older repositories [`research_ws`](https://github.com/hawaii-nc/research_ws) and [`f1tenth-vader-deployment`](https://github.com/hawaii-nc/f1tenth-vader-deployment) are superseded by this one.

## Citing, acknowledgements, license

See [CITATION.cff](CITATION.cff); references are in [paper/references.bib](paper/references.bib). Thanks to Prof. Modekurthy for advising this work, to Ederic Oytas for help with the lab and the VADER car, and to the UNLV Smart Cities REU (NSF Award #2349616).

Code is MIT ([LICENSE](LICENSE)). The AUT/ESP/GBR/MCO maps are from [BDEvan5/f1tenth_benchmarks](https://github.com/BDEvan5/f1tenth_benchmarks) (Apache-2.0). The other tracks come from [f1tenth/f1tenth_racetracks](https://github.com/f1tenth/f1tenth_racetracks) (GPL-3.0) and are downloaded by `tools/prepare_tracks.py`, not stored here.
