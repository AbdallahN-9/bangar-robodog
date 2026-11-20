import os
import subprocess
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch.actions import (DeclareLaunchArgument, ExecuteProcess,
                            TimerAction, SetEnvironmentVariable)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # --- 1. Path Setup ---
    pkg_bangar     = get_package_share_directory('bangar')
    urdf_path      = os.path.join(pkg_bangar, 'urdf', 'bangar_gazebo.urdf')
    world_path     = os.path.join(pkg_bangar, 'worlds', 'warehouse_world.sdf')
    sdf_path       = '/tmp/bangar.sdf'
    
    # Resource path: We need the parent directory of the package so Gazebo can find 'bangar/meshes'
    install_dir = os.path.dirname(pkg_bangar)

    # --- 2. URDF to SDF Conversion ---
    # This ensures Gazebo Sim (Ignition) reads the robot correctly
    subprocess.run(
        ['gz', 'sdf', '-p', urdf_path],
        stdout=open(sdf_path, 'w'),
        stderr=subprocess.DEVNULL
    )

    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    controller_node = LaunchConfiguration('controller_node')

    return LaunchDescription([
        # --- 3. Arguments & Environment ---
        DeclareLaunchArgument(
            'controller_node',
            default_value='bangar_controller.py',
            description='Behavior node executable'
        ),

        # This tells Gazebo where to look for models and meshes
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', install_dir),
        
        # macOS specific: helps with discovery between server and GUI
        SetEnvironmentVariable('GZ_PARTITION', 'bangar_sim'),

        # --- 4. Gazebo Server (Physics) ---
        # Note: We launch WITHOUT the GUI (-s) for macOS stability
        ExecuteProcess(
            cmd=['gz', 'sim', '-r', '-s', world_path],
            output='screen'
        ),

        # --- 5. Robot State Publisher ---
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': True,
            }],
            output='screen'
        ),

        # --- 6. ROS-Gazebo Bridge ---
        # Bridges topics between ROS 2 and Gazebo Transport
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
                # Shoulder/Knee/Wheel Commands
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

        # --- 7. Spawn Robot ---
        # Wait 5 seconds for server to initialize
        TimerAction(period=5.0, actions=[
            Node(
                package='ros_gz_sim',
                executable='create',
                arguments=[
                    '-name', 'bangar',
                    '-file', sdf_path,
                    '-x', '0.0', '-y', '0.0', '-z', '0.24',
                    '-R', '1.5708', '-P', '0.0', '-Y', '0.0',
                ],
                output='screen'
            ),
        ]),

        # --- 8. Controller Node ---
        # Wait until robot is spawned before starting control logic
        TimerAction(period=8.0, actions=[
            Node(
                package='bangar',
                executable=controller_node,
                parameters=[{'use_sim_time': True}],
                output='screen'
            ),
        ]),
    ])