#!/bin/bash
# Adaptive controller on the car: base policy + adaptation module (phi_DR) with the active grip probe.
# Models: copy runs/real_phase1_seedN/final.pt and runs/real_phase2_slipdr_seedN/final.pt from the
# repo to $RMA_RUNS_DIR on the car, keeping the directory names (deploy/TA_INSTALL_CHECKLIST.md).
# These were trained with the car's sensing, a 100 Hz loop and a -1.0 m/s braking probe; the node's
# defaults match. The probe must be on for every controller, the non-adaptive baseline included.
# Overrides: RMA_SEED (0, 1 or 2), RMA_POLICY, RMA_PHI, RMA_LOG, RMA_PROBE (0 = off).
# The July 2026 pilot instead ran checkpoints/final/phase1_v42.pt + phase2_crashtol_clean.pt at
# 50 Hz without a probe; to repeat it, set RMA_POLICY / RMA_PHI to those files, RMA_PROBE=0 and
# add --control_freq 50.
source /opt/ros/foxy/setup.bash
source ~/ws/install/local_setup.bash
source ~/rma_deploy_ws/install/local_setup.bash
export LD_LIBRARY_PATH=~/local_libs:$LD_LIBRARY_PATH
export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/liblapack.so.3
export PYTHONPATH=$PYTHONPATH:~
export ROS_DOMAIN_ID=20
RUNS=${RMA_RUNS_DIR:-~/rma_deploy_ws/runs}
SEED=${RMA_SEED:-0}
POLICY=${RMA_POLICY:-$RUNS/real_phase1_seed$SEED/final.pt}
PHI=${RMA_PHI:-$RUNS/real_phase2_slipdr_seed$SEED/final.pt}
[[ -f $POLICY ]] || { echo "missing policy checkpoint: $POLICY" >&2; exit 1; }
[[ -f $PHI ]] || { echo "missing adaptation checkpoint: $PHI" >&2; exit 1; }
exec ~/rma_deploy_ws/install/rma_deploy_pkg/bin/rma_deployment_node \
    --actor_critic "$POLICY" \
    --adaptation "$PHI" \
    --probe "${RMA_PROBE:-1}" \
    --odom_topic /odom \
    --log_path "${RMA_LOG:-~/rma_data.csv}" "$@"
