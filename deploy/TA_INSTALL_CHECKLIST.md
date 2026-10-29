# RMA Deployment: Install Checklist (VADER, L4T R35.4.1 = JetPack 5.1.2, Python 3.8)

## What this is
A trained reinforcement-learning policy that drives the car autonomously using only
LiDAR (108 beams) and odometry. It needs no map, GPS or raceline, so it works on any
track shape, including the cardboard track.

## 1. PyTorch (already done on VADER: torch 2.1.0, user install)
NVIDIA's JetPack 5.1.x / Python 3.8 wheel: https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048
    pip3 install torch-<version>-cp38-cp38-linux_aarch64.whl
    python3 -c "import torch; print(torch.__version__)"

## 2. numpy, slam_toolbox (already present on VADER)
    python3 -c "import numpy; print(numpy.__version__)"

## 3. Copy both packages + checkpoints (from a laptop with this repo)
    scp -r src/f1tenth_research src/rma_deploy_pkg USER@vader:~/rma_deploy_ws/src/
    ssh USER@vader mkdir -p ~/rma_deploy_ws/src/rma_deploy_pkg/checkpoints
    scp checkpoints/final/*.pt USER@vader:~/rma_deploy_ws/src/rma_deploy_pkg/checkpoints/
    scp deploy/start_rma.sh deploy/start_rma_noadapt.sh deploy/trial_helpers.sh deploy/joy_manager.py USER@vader:~/

## 4. Build (no PYTHONPATH workaround needed any more)
    cd ~/rma_deploy_ws
    colcon build --packages-select f1tenth_research rma_deploy_pkg
    source install/local_setup.bash

## 5. Test launch (SECURE THE CAR FIRST: wheels off the ground or held in place)
    ros2 launch f1tenth_unlv_veh stack_aeb_launch.py           # terminal 1
    ~/start_rma_noadapt.sh                                       # terminal 2: base policy only
Hold R2 to engage autonomous control. Release it (or hold L1) immediately if anything looks wrong.

## 6. With adaptation (φ)
    ~/start_rma.sh          # phase1_v42.pt + phase2_crashtol_clean.pt; history window read from the checkpoint

## Notes
- The policy caps speed at 3.0 m/s, which is safe for the tight cardboard track.
- Observation: 113-D (5 base signals + 108 LiDAR beams).
- Per-step log: ~/rma_data.csv (override with RMA_LOG=...). See deploy/trial_helpers.sh for the trial workflow.
- Check the L4T version with: cat /etc/nv_tegra_release
