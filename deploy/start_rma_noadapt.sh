#!/bin/bash
source /opt/ros/foxy/setup.bash
source ~/ws/install/local_setup.bash
source ~/rma_deploy_ws/install/local_setup.bash
export LD_LIBRARY_PATH=~/local_libs:$LD_LIBRARY_PATH
export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/liblapack.so.3
export PYTHONPATH=$PYTHONPATH:~
export ROS_DOMAIN_ID=20
exec ~/rma_deploy_ws/install/rma_deploy_pkg/bin/rma_deployment_node \
    --actor_critic ~/rma_deploy_ws/src/rma_deploy_pkg/checkpoints/phase1_v42.pt \
    --history_window 50 \
    --odom_topic /odom
