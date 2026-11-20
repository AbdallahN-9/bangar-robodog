#!/usr/bin/env python3
import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_bangar = get_package_share_directory('bangar')
    pkg_ros_gz = get_package_share_directory('ros_gz_sim')

    urdf_path  = os.path.join(pkg_bangar, 'urdf', 'bangar_gazebo.urdf')
    world_path = os.path.join(pkg_bangar, 'worlds', 'warehouse_world.sdf')

    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    return LaunchDescription([

        # 1. Gazebo server
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_ros_gz, 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments={
                'gz_args': f'{world_path} -r -s',
                'on_exit_shutdown': 'true',
            }.items()
        ),

        # 2. Robot state publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': True,
            }],
            output='screen'
        ),

        # 3. Spawn Bangar — delayed 5s to let Gazebo fully load
        TimerAction(period=5.0, actions=[
            Node(
                package='ros_gz_sim',
                executable='create',
                arguments=[
                    '-name', 'bangar',
                    '-file', urdf_path,
                    '-x', '0.0',
                    '-y', '0.0',
                    '-z', '0.4',
                    '-R', '1.5708',  # π/2 radians - rotate to stand upright
                    '-P', '0.0',
                    '-Y', '0.0',
                ],
                output='screen'
            ),
        ]),

        # 4. Bridge Gazebo <-> ROS2
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
                '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
                '/bangar/us/front_left@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
                '/bangar/us/front_right@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
                '/bangar/us/diag_left@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
                '/bangar/us/diag_right@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
                '/bangar/us/rear@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
                # Joint position command bridges
                '/cmd/front_left_shoulder@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/front_left_knee@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/back_left_shoulder@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/back_left_knee@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/front_right_shoulder@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/front_right_knee@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/back_right_shoulder@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/back_right_knee@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/front_left_wheel@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/back_left_wheel@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/front_right_wheel@std_msgs/msg/Float64]gz.msgs.Double',
                '/cmd/back_right_wheel@std_msgs/msg/Float64]gz.msgs.Double',
            ],
            output='screen'
        ),

        # 5. Walk node
        Node(
            package='bangar',
            executable='walk_node.py',
            parameters=[{'use_sim_time': True}],
            output='screen'
        ),
    ])
