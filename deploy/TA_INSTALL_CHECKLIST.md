# RMA Deployment - TA Install Checklist (Vader, JetPack 5.4.1, Python 3.8)

## What this is
A trained reinforcement learning policy that drives the car autonomously using
only LiDAR (108 beams) + odometry (velocity/steering feedback) -- no map or GPS required.
Works on any track shape, including our physical cardboard track.

## 1. PyTorch (the main blocker)
Download the JetPack 5.4.1 / Python 3.8 wheel from NVIDIA Jetson Zoo:
https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048

Then:
pip3 install torch-<version>-cp38-cp38-linux_aarch64.whl

Verify:
python3 -c "import torch; print(torch.version)"

## 2. numpy (should already be present with ROS 2, verify anyway)
python3 -c "import numpy; print(numpy.version)"
If missing: `pip3 install numpy`

## 3. Copy the deployment package + supporting library
scp -r rma_deploy_ws/src/rma_deploy_pkg USER@vader:~/ws/src/
scp f1tenth_research_for_car.tar.gz USER@vader:~/ws/src/
On the car:
cd ~/ws/src && tar xzf f1tenth_research_for_car.tar.gz

## 4. Set PYTHONPATH so the node can import f1tenth_research.models
Add to ~/.bashrc or run before launching:
export PYTHONPATH=$PYTHONPATH:~/ws/src

## 5. Build
cd ~/ws
colcon build --packages-select rma_deploy_pkg
source install/local_setup.bash

## 6. Test launch (SECURE THE CAR FIRST -- wheels off ground or held in place)
ros2 launch f1tenth_unlv_veh stack_aeb_launch.py
In new terminal:
ros2 launch rma_deploy_pkg veh_launch.py checkpoint:=/home/USER/ws/src/rma_deploy_pkg/checkpoints/phase1_v28.pt
Hold R2 to engage autonomous control. Release immediately if anything looks wrong.

## Notes
- Policy caps speed at 3.0 m/s -- safe for our tight cardboard track
- No map/raceline data needed -- policy drives from LiDAR + motion state alone
- Observation space: 113D (5 base signals + 108 LiDAR beams)
- If things go wrong, release R2 (or hold L1 for manual override) immediately

## Note on Phase 2 (adaptation)
For the first real-car test, launch WITHOUT the --adaptation flag (i.e., don't pass
checkpoint:=... for the adaptation parameter). The base policy (phase1_v28.pt) alone
is the most thoroughly validated option. Phase 2 support is included for future
testing once further validated.
