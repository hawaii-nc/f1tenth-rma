"""
On-car launch. Examples:

  # Phase 1 only (Blind / nominal intrinsics)
  ros2 launch rma_deploy_pkg veh_launch.py checkpoint:=$CKPT/phase1_v42.pt

  # Phase 1 + φ (history window is read from the φ checkpoint)
  ros2 launch rma_deploy_pkg veh_launch.py checkpoint:=$CKPT/phase1_v42.pt \
      adaptation:=$CKPT/phase2_crashtol_clean.pt
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
            '--scan_topic', '/scan',
            '--drive_topic', '/drive',
        ],
    )

    return LaunchDescription(args + [rma_node])
