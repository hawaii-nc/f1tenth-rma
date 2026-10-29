# Reproducing the work

## 0. Environment

f110_gym 0.2.1 pins `gym==0.19`, `numpy<=1.22` and Python 3.8, the same Python as the car's JetPack 5. The simplest route is the Docker image:

```bash
docker build -t f1tenth-rma -f docker/Dockerfile .
docker run --rm -it -v $PWD:/f1tenth-rma f1tenth-rma          # add --gpus all if you have CUDA
pytest -q tests                                              # sanity check
```

Without Docker, use a Python 3.8 virtualenv: `pip install "setuptools==65.5.0" "wheel<0.40"`, then `pip install -e <f1tenth_gym checkout>` (commit 4fdb9c7), then `pip install -r requirements-dev.txt`.

Code runs from the repo with `PYTHONPATH=src/f1tenth_research`. The Docker image sets this, and the experiment scripts add it themselves.

## 1. Tracks

```bash
python tools/prepare_tracks.py          # 4 benchmark maps + 10 racetrack-DB circuits → 14 × *_tight (35%)
```

Maps are read from `$F1TENTH_MAPS_DIR` (default: `maps/`).

## 2. Train Phase 1 (π, μ, V)

```bash
cd src/f1tenth_research
tmux new -s p1 'python3 -u -m f1tenth_research.training.phase1_ppo_il \
    --config ../../configs/final_phase1_v42.yaml --device auto \
    --log_dir ../../runs/phase1 --checkpoint_dir ../../runs/phase1 2>&1 | tee ../../runs/phase1.log'
grep "Avg Reward" ../../runs/phase1.log       # monitor
tensorboard --logdir ../../runs/phase1 --port 6007 --host 0.0.0.0
```

Final config: 16M steps, 34,000-step rollouts, PPO (clip 0.2, γ 0.99, λ 0.95, lr 3e-4), and IL weight from 1.0 decaying at 0.0035 toward 0.01, with up to 8 plateau rescues. The v42 run took 16.0M steps.

**Before any long run:** run `--debug` (100k steps). Check that the per-step reward breakdown has sensible signs (`[REWARD DEBUG]` lines), and that expert actions are produced (`tests/test_training_smoke.py::test_phase1_runs_and_expert_is_active`).

## 3. Train Phase 2 (φ)

```bash
python3 -u -m f1tenth_research.training.phase2_adaptation \
    --phase1_checkpoint ../../checkpoints/final/phase1_v42.pt \
    --config ../../configs/final_phase2_crashtol.yaml \
    --log_dir ../../runs/phase2 --checkpoint_dir ../../runs/phase2
```

Final config: k = 50 history window, 800 collection episodes, a 2M-transition buffer, 100 epochs, lr 5e-4, and an auxiliary physics loss with grip weighted 3× ([RECONSTRUCTION.md](RECONSTRUCTION.md) explains why the aux head is a reconstruction). For the E3 ablation, set `networks.adaptation.history_window: 100`.

## 4. Evaluate (E0–E5)

```bash
python experiments/e0_grip_gate.py -n 40
python experiments/e1_e2_calibration.py -n 100 --phase2 runs/phase2/final.pt
python experiments/e3_transient.py -n 40
python experiments/e4_causal.py -n 100
python experiments/e5_signal.py -n 200
# or: tmux new -s exps 'bash experiments/run_all.sh'
```

Every script takes `--phase1`, `--phase2`, `--config`, `-n`, `--tracks`, `--seed` and `--out`. See [EXPERIMENTS.md](EXPERIMENTS.md) for the protocol.

## 5. Deploy on the car (VADER: Jetson, L4T R35.4.1 = JetPack 5.1.2, ROS 2 Foxy)

PyTorch for the Jetson comes from NVIDIA's JetPack 5.1.x / Python 3.8 wheel (installed on VADER: torch 2.1.0). See `deploy/TA_INSTALL_CHECKLIST.md`.

```bash
# from your laptop
scp -r src/rma_deploy_pkg src/f1tenth_research <user>@vader:~/rma_deploy_ws/src/
scp checkpoints/final/*.pt <user>@vader:~/rma_deploy_ws/src/rma_deploy_pkg/checkpoints/
scp deploy/*.sh deploy/joy_manager.py <user>@vader:~/

# on the car
cd ~/rma_deploy_ws && colcon build --packages-select f1tenth_research rma_deploy_pkg
source install/local_setup.bash
ros2 launch f1tenth_unlv_veh stack_aeb_launch.py        # car stack (terminal 1)
~/start_rma.sh                                           # φ-RMA   (terminal 2)
~/start_rma_noadapt.sh                                   # Blind baseline
```

**Safety:** secure the car (wheels off the ground) for first tests. Hold R2 to engage; release R2, or hold L1, for manual override. The policy caps speed at 3.0 m/s. `--shield` adds the ACDA / grip-adaptive speed shield (off by default; it can only lower speed).

## 6. Real-car trials and analysis

```bash
source ~/trial_helpers.sh
new_material                       # fresh log for this tire condition
~/start_rma.sh &                   # node writes ~/rma_data.csv
start_trial; ...; end_trial cw 1 pass
finish_material electrical         # → rma_data_electrical.csv, rma_trial_log_electrical.csv
```

`joy_manager.py` logs TRIAL_START / PASS / FAIL from the controller buttons (Circle / Triangle / X).

Back on a laptop:

```bash
python analysis/real_car/tire_stats.py --data-dir ~/vader_logs \
    --conditions bare foil duct electrical --control bare
```

On-car logs are git-ignored; archive them separately.
