"""
On-car launch. Examples:

  # Phase 1 only (Blind / nominal intrinsics)
  ros2 launch rma_deploy_pkg veh_launch.py checkpoint:=$CKPT/phase1_v42.pt

  # Phase 1 + φ (history window is read from the φ checkpoint)
  ros2 launch rma_deploy_pkg veh_launch.py checkpoint:=$CKPT/phase1_v42.pt \
      adaptation:=$CKPT/phase2_crashtol_clean.pt

  # November 2026 deployable model (amendments 8-10): braking probe on, 100 Hz (defaults)
  ros2 launch rma_deploy_pkg veh_launch.py checkpoint:=$RUNS/real_phase1_seed0/final.pt \
      adaptation:=$RUNS/real_phase2_slipdr_seed0/final.pt probe:=1

probe_amplitude must match the phi checkpoint: -1.0 m/s (braking, the default) for the
runs/real_* models; +2.0 only for the ideal-sensor configuration Q, which is not for the car.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    args = [
        DeclareLaunchArgument('checkpoint', default_value='phase1_v42.pt'),
        DeclareLaunchArgument('adaptation', default_value=''),
        DeclareLaunchArgument('log_path', default_value='~/rma_data.csv'),
        DeclareLaunchArgument('odom_topic', default_value='/odom'),
        DeclareLaunchArgument('control_freq', default_value='100.0'),
        DeclareLaunchArgument('probe', default_value='0'),
        DeclareLaunchArgument('probe_amplitude', default_value='-1.0'),
    ]

    rma_node = Node(
        package='rma_deploy_pkg',
        executable='rma_deployment_node',
        name='rma_deployment',
        output='screen',
        arguments=[
            '--actor_critic', LaunchConfiguration('checkpoint'),
            '--adaptation', LaunchConfiguration('adaptation'),
            '--log_path', LaunchConfiguration('log_path'),
            '--odom_topic', LaunchConfiguration('odom_topic'),
            '--control_freq', LaunchConfiguration('control_freq'),
            '--probe', LaunchConfiguration('probe'),
            '--probe_amplitude', LaunchConfiguration('probe_amplitude'),
            '--scan_topic', '/scan',
            '--drive_topic', '/drive',
        ],
    )

    return LaunchDescription(args + [rma_node])
