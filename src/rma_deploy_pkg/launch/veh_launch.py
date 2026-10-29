from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    checkpoint_arg = DeclareLaunchArgument('checkpoint', default_value='phase1_v28.pt')
    adaptation_arg = DeclareLaunchArgument('adaptation', default_value='')

    rma_node = Node(
        package='rma_deploy_pkg',
        executable='rma_deployment_node',
        name='rma_deployment',
        output='screen',
        arguments=[
            '--actor_critic', LaunchConfiguration('checkpoint'),
            '--adaptation', LaunchConfiguration('adaptation'),
            '--odom_topic', '/odom',
            '--scan_topic', '/scan',
            '--drive_topic', '/drive',
        ],
    )

    return LaunchDescription([checkpoint_arg, adaptation_arg, rma_node])
