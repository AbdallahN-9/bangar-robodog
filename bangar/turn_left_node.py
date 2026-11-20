#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

class TurnLeftNode(Node):
    def __init__(self):
        super().__init__('turn_left_node')
        self.publisher = self.create_publisher(JointState, 'joint_states', 10)
        self.timer = self.create_timer(0.02, self.publish_joints)
        self.angle = 0.0
        self.speed = 0.05

    def publish_joints(self):
        self.angle += self.speed
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = [
            'front_left_wheel_joint',
            'back_left_wheel_joint',
            'front_right_wheel_joint',
            'back_right_wheel_joint',
        ]
        # Left wheels backward, right wheels forward
        msg.position = [
            -self.angle,  # front_left
            -self.angle,  # back_left
             self.angle,  # front_right
             self.angle,  # back_right
        ]
        self.publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(TurnLeftNode())

if __name__ == '__main__':
    main()
