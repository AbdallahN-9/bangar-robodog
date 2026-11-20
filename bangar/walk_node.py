#!/usr/bin/env python3
"""
walk_node.py - corrected gait for Bangar

ROOT CAUSE OF PREVIOUS BUGS:
  The knee logic was inverted. The FK shows that for FL knee (axis=-X):
    - walk_node publishes -kn_a
    - kn_sent = -kn_a (negative = extends leg DOWN toward ground)
    - So LARGE kn_a = leg extended to ground (STANCE)
    - SMALL kn_a = leg retracted upward (SWING lifted)

  Previous code had knee_stance=0.20 (small = leg UP in stance!)
  and applied knee_lift as ADDITION during swing (making it even lower = leg DOWN in swing!)
  This put the leg UP when it should grip and DOWN when it should clear.

FIX:
  kn_stance = 0.85  (large = leg pushed down, wheels grip ground)
  kn_air    = 0.10  (small = leg pulled up, wheel clears ground)
  During SWING: kn dips from kn_stance down to kn_air at mid-swing, then back
  During STANCE: kn held at kn_stance (firm ground contact)
"""

import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

TOPICS = [
    '/cmd/front_left_shoulder',  '/cmd/front_left_knee',
    '/cmd/back_left_shoulder',   '/cmd/back_left_knee',
    '/cmd/front_right_shoulder', '/cmd/front_right_knee',
    '/cmd/back_right_shoulder',  '/cmd/back_right_knee',
    '/cmd/front_left_wheel',     '/cmd/back_left_wheel',
    '/cmd/front_right_wheel',    '/cmd/back_right_wheel',
]

class WalkNode(Node):
    def __init__(self):
        super().__init__('walk_node')
        self._pubs = {t: self.create_publisher(Float64, t, 10) for t in TOPICS}
        self.create_timer(0.02, self._update)

        self.t  = 0.0
        self.dt = 0.02

        self.freq      = 0.6    # Hz — original speed, gait is now correct so this is fine
        self.stride    = 0.25   # shoulder sweep ±rad — matches joint limit headroom

        # Knee values (what walk_node computes before negation):
        #   kn_stance = large -> sent to joint as -kn_stance (negative) -> leg extends DOWN
        #   kn_air    = small -> sent as -kn_air (near zero)             -> leg retracts UP
        self.kn_stance = 0.85
        self.kn_air    = 0.10

        self.get_logger().info('Walk node started — corrected knee direction')

    def _pub(self, topic, val):
        m = Float64()
        m.data = float(val)
        self._pubs[topic].publish(m)

    def _leg(self, phi):
        """
        Returns (shoulder_angle, kn_val) for gait phase phi in [0, 2*pi).

        The caller publishes -kn_val to left knees (axis=-X) and +kn_val to right knees (axis=+X).
        Large kn_val -> sent as negative to joint -> leg extends to ground.
        Small kn_val -> leg retracts upward for clearance.

        SWING phase (phi in [0, pi)):
          - shoulder sweeps +stride -> -stride  (rear to front, foot steps forward)
          - kn dips from kn_stance to kn_air at mid-swing then back (lifts foot)

        STANCE phase (phi in [pi, 2*pi)):
          - shoulder sweeps -stride -> +stride  (front to rear, pushes body forward)
          - kn held at kn_stance (wheels pressed firmly onto ground)
        """
        phi = phi % (2.0 * math.pi)
        if phi < math.pi:
            # SWING: lift and step forward
            p  = phi / math.pi
            sh = self.stride * (0.5 - p)
            # kn dips from kn_stance to kn_air and back — sin arch subtracted
            kn = self.kn_stance - (self.kn_stance - self.kn_air) * math.sin(math.pi * p)
        else:
            # STANCE: push body forward, hold knee firm on ground
            p  = (phi - math.pi) / math.pi
            sh = self.stride * (-0.5 + p)
            kn = self.kn_stance

        sh = max(-self.stride, min(self.stride, sh))
        kn = max(0.0, min(1.1, kn))
        return sh, kn

    def _update(self):
        self.t += self.dt
        phi = (2.0 * math.pi * self.freq * self.t) % (2.0 * math.pi)

        # Diagonal trot: FL+BR in phase A, FR+BL in phase B (offset by pi)
        sh_a, kn_a = self._leg(phi)
        sh_b, kn_b = self._leg((phi + math.pi) % (2.0 * math.pi))

        # Left shoulders:  axis=+X — positive sh = foot swings forward. Direct.
        # Right shoulders: axis=-X — negate sh to get same world-space motion.
        # Left knees:  axis=-X — publish -kn (negative sent = leg extends down).
        # Right knees: axis=+X — publish +kn (positive sent = same leg-down motion).
        self._pub('/cmd/front_left_shoulder',   sh_a)
        self._pub('/cmd/front_left_knee',      -kn_a)
        self._pub('/cmd/back_left_shoulder',    sh_b)
        self._pub('/cmd/back_left_knee',       -kn_b)
        self._pub('/cmd/front_right_shoulder', -sh_b)
        self._pub('/cmd/front_right_knee',      kn_b)
        self._pub('/cmd/back_right_shoulder',  -sh_a)
        self._pub('/cmd/back_right_knee',       kn_a)

        # Wheels are passive — velocity controllers removed from URDF
        self._pub('/cmd/front_left_wheel',  0.0)
        self._pub('/cmd/back_left_wheel',   0.0)
        self._pub('/cmd/front_right_wheel', 0.0)
        self._pub('/cmd/back_right_wheel',  0.0)

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(WalkNode())

if __name__ == '__main__':
    main()
