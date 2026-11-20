#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import math

class SitNode(Node):
    def __init__(self):
        super().__init__('sit_node')
        self.publisher = self.create_publisher(JointState, 'joint_states', 10)
        self.timer = self.create_timer(0.02, self.publish_joints)  # 50Hz
        self.t = 0.0
        self.duration = 2.0  # seconds to complete sit motion

    def publish_joints(self):
        # Clamp t to [0, duration] so it holds the final pose
        self.t = min(self.t + 0.02, self.duration)

        # Smooth interpolation using cosine easing
        alpha = (1 - math.cos(math.pi * self.t / self.duration)) / 2.0

        # Target sit positions
        back_shoulder_target = 0.7   # rear shoulders swing back
        back_knee_target     = 1.0   # rear knees bend deep

        # Front stays at rest (0)
        back_shoulder = alpha * back_shoulder_target
        back_knee     = alpha * back_knee_target

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()

        msg.name = [
            'front_left_shoulder_joint',
            'front_left_knee_joint',
            'back_left_shoulder_joint',
            'back_left_knee_joint',
            'front_right_shoulder_joint',
            'front_right_knee_joint',
            'back_right_shoulder_joint',
            'back_right_knee_joint',
            'front_left_wheel_joint',
            'back_left_wheel_joint',
            'front_right_wheel_joint',
            'back_right_wheel_joint',
        ]

        msg.position = [
            0.0,             # front_left_shoulder  (stay)
            0.0,             # front_left_knee      (stay)
           -back_shoulder,   # back_left_shoulder   (axis: 1 so negate)
            back_knee,       # back_left_knee       (axis: -1)
            0.0,             # front_right_shoulder (stay)
            0.0,             # front_right_knee     (stay)
            back_shoulder,   # back_right_shoulder  (axis: -1)
            back_knee,       # back_right_knee      (axis: 1)
            0.0, 0.0, 0.0, 0.0,  # wheels locked
        ]

        self.publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(SitNode())

if __name__ == '__main__':
    main()
