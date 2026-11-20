#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64, String

TOPICS = [
    '/cmd/front_left_shoulder',  '/cmd/front_left_knee',
    '/cmd/back_left_shoulder',   '/cmd/back_left_knee',
    '/cmd/front_right_shoulder', '/cmd/front_right_knee',
    '/cmd/back_right_shoulder',  '/cmd/back_right_knee',
    '/cmd/front_left_wheel',     '/cmd/back_left_wheel',
    '/cmd/front_right_wheel',    '/cmd/back_right_wheel',
]

KN_STANCE  = 0.75   # left knees: -KN_STANCE, right knees: +KN_STANCE
WHEEL_FWD  = 1.5    # left wheels: +WHEEL_FWD, right wheels: -WHEEL_FWD
GAIT_FREQ  = 0.6
AMP_SH     = 0.25
AMP_KN     = 0.12

class BangarController(Node):
    def __init__(self):
        super().__init__('bangar_controller')
        self._pubs = {t: self.create_publisher(Float64, t, 10) for t in TOPICS}
        self.create_subscription(String, '/bangar/mode', self._mode_cb, 10)
        self.mode = 'stop'
        self.t = 0.0
        self._turn_t = 0.0
        self.dt = 0.02
        self.create_timer(self.dt, self._update)
        self.get_logger().info('Bangar Controller Started. Mode: STOP')

    def _mode_cb(self, msg: String):
        raw = msg.data.strip().lower().replace("'", "").replace('"', "")
        self.get_logger().info(f'Received: "{raw}"')
        if raw != self.mode:
            self.get_logger().info(f'TRANSITION: {self.mode} -> {raw}')
            self.mode = raw
            self.t = 0.0
            self._turn_t = 0.0

    def _update(self):
        self.t += self.dt
        if   self.mode == 'walk':       self._walk()
        elif self.mode == 'turn_left':  self._turn(left=True)
        elif self.mode == 'turn_right': self._turn(left=False)
        elif self.mode == 'sit':        self._sit()
        else:                           self._stop()

    def _walk(self):
        phi = 2.0 * math.pi * GAIT_FREQ * self.t

        # Diagonal trot: FL+BR in phase, FR+BL antiphase
        fl_br = math.sin(phi)
        fr_bl = math.sin(phi + math.pi)

        # Left shoulders: +X axis → positive = forward swing
        # Right shoulders: -X axis → negative = forward swing (physically same direction)
        self._send({
            'fl_sh':  AMP_SH * fl_br,
            'bl_sh':  AMP_SH * fl_br,
            'fr_sh': -AMP_SH * fr_bl,   # flip sign for -X axis
            'br_sh': -AMP_SH * fr_bl,

            # Left knees: -X axis, stance is -KN_STANCE, lift reduces magnitude
            'fl_kn': -KN_STANCE + AMP_KN * fl_br,
            'bl_kn': -KN_STANCE + AMP_KN * fl_br,
            # Right knees: +X axis, stance is +KN_STANCE, lift reduces magnitude
            'fr_kn':  KN_STANCE - AMP_KN * fr_bl,
            'br_kn':  KN_STANCE - AMP_KN * fr_bl,

            # All wheels forward: left=+, right=-
            'fl_wh':  WHEEL_FWD, 'bl_wh':  WHEEL_FWD,
            'fr_wh': -WHEEL_FWD, 'br_wh': -WHEEL_FWD,
        })

    def _turn(self, left: bool):
        # Spin in place: one side forward, other backward
        # left turn: left wheels backward, right wheels backward in their frame = forward
        if left:
            self._send({
                'fl_wh': -WHEEL_FWD, 'bl_wh': -WHEEL_FWD,
                'fr_wh': -WHEEL_FWD, 'br_wh': -WHEEL_FWD,
            })
        else:
            self._send({
                'fl_wh':  WHEEL_FWD, 'bl_wh':  WHEEL_FWD,
                'fr_wh':  WHEEL_FWD, 'br_wh':  WHEEL_FWD,
            })

    def _sit(self):
        self._send({
            'fl_sh': 0.0, 'fl_kn': -KN_STANCE * 1.6,
            'bl_sh': 0.0, 'bl_kn': -KN_STANCE * 1.6,
            'fr_sh': 0.0, 'fr_kn':  KN_STANCE * 1.6,
            'br_sh': 0.0, 'br_kn':  KN_STANCE * 1.6,
            'fl_wh': 0.0, 'bl_wh': 0.0,
            'fr_wh': 0.0, 'br_wh': 0.0,
        })

    def _stop(self):
        self._send({
            'fl_sh': 0.0, 'fl_kn': -KN_STANCE,
            'bl_sh': 0.0, 'bl_kn': -KN_STANCE,
            'fr_sh': 0.0, 'fr_kn':  KN_STANCE,
            'br_sh': 0.0, 'br_kn':  KN_STANCE,
            'fl_wh': 0.0, 'bl_wh': 0.0,
            'fr_wh': 0.0, 'br_wh': 0.0,
        })

    def _send(self, j: dict):
        defaults = {
            'fl_sh': 0.0, 'fl_kn': -KN_STANCE,
            'bl_sh': 0.0, 'bl_kn': -KN_STANCE,
            'fr_sh': 0.0, 'fr_kn':  KN_STANCE,
            'br_sh': 0.0, 'br_kn':  KN_STANCE,
            'fl_wh': 0.0, 'bl_wh': 0.0,
            'fr_wh': 0.0, 'br_wh': 0.0,
        }
        defaults.update(j)
        mapping = {
            '/cmd/front_left_shoulder':  defaults['fl_sh'],
            '/cmd/front_left_knee':      defaults['fl_kn'],
            '/cmd/back_left_shoulder':   defaults['bl_sh'],
            '/cmd/back_left_knee':       defaults['bl_kn'],
            '/cmd/front_right_shoulder': defaults['fr_sh'],
            '/cmd/front_right_knee':     defaults['fr_kn'],
            '/cmd/back_right_shoulder':  defaults['br_sh'],
            '/cmd/back_right_knee':      defaults['br_kn'],
            '/cmd/front_left_wheel':     defaults['fl_wh'],
            '/cmd/back_left_wheel':      defaults['bl_wh'],
            '/cmd/front_right_wheel':   -float(defaults['fr_wh']), 
            '/cmd/back_right_wheel':    -float(defaults['br_wh']),
        }
        for topic, val in mapping.items():
            m = Float64()
            m.data = val
            self._pubs[topic].publish(m)

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(BangarController())
    rclpy.shutdown()

if __name__ == '__main__':
    main()