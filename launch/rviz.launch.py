#!/usr/bin/env python3
import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_bangar = get_package_share_directory('bangar')
    urdf_path = os.path.join(pkg_bangar, 'urdf', 'bangar.urdf')

    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': False,
            }],
            output='screen'
        ),
        Node(
            package='bangar',
            executable='walk_node.py',
            parameters=[{'use_sim_time': False}],
            output='screen'
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            output='screen'
        ),
    ])
