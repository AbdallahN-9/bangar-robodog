#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import math

class WheelNode(Node):
    def __init__(self):
        super().__init__('wheel_node')
        self.publisher = self.create_publisher(JointState, 'joint_states', 10)
        self.timer = self.create_timer(0.02, self.publish_joints)  # 50Hz
        self.wheel_angle = 0.0
        self.speed = 0.05  # radians per tick, increase for faster

    def publish_joints(self):
        self.wheel_angle += self.speed

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()

        msg.name = [
            'front_left_wheel_joint',
            'back_left_wheel_joint',
            'front_right_wheel_joint',
            'back_right_wheel_joint',
        ]

        msg.position = [
            self.wheel_angle,
            self.wheel_angle,
            self.wheel_angle,
            self.wheel_angle,
        ]

        self.publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(WheelNode())

if __name__ == '__main__':
    main()
