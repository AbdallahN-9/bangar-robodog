#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseWithCovarianceStamped
from cv_bridge import CvBridge
import cv2
import cv2.aruco as aruco
import numpy as np

# DroidCam stream URL
DROIDCAM_URL = "http://192.168.1.1:4747/video"

# ArUco marker physical size in meters (measure your printed markers)
MARKER_SIZE = 0.05  # 5cm

# Map each marker ID to its known position in the map (x, y) in meters
MARKER_MAP = {
    0:  (0.5, 0.5),
    1:  (1.5, 0.5),
    2:  (0.5, 2.0),
    3:  (1.5, 2.0),
    4:  (1.0, 1.0),  # center
}

# Basic camera calibration (replace with yours if you calibrate)
# These are approximate values for a phone camera at 640x480
CAM_MATRIX = np.array([
    [600,   0, 320],
    [  0, 600, 240],
    [  0,   0,   1]
], dtype=np.float32)

DIST_COEFFS = np.zeros((4, 1), dtype=np.float32)

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        # Publishers
        self.image_pub  = self.create_publisher(Image, '/bangar/camera/image', 10)
        self.pose_pub   = self.create_publisher(PoseWithCovarianceStamped, '/bangar/pose_estimate', 10)

        self.bridge = CvBridge()
        self.aruco_dict   = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        self.aruco_params = aruco.DetectorParameters()
        self.detector     = aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        self.cap = cv2.VideoCapture(DROIDCAM_URL)
        if not self.cap.isOpened():
            self.get_logger().error(f'Cannot open DroidCam stream at {DROIDCAM_URL}')
        else:
            self.get_logger().info('DroidCam connected.')

        self.timer = self.create_timer(0.033, self.update)  # ~30Hz

    def update(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn('No frame from DroidCam')
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)

        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)
            self._estimate_pose(frame, corners, ids)

        # Publish image
        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        self.image_pub.publish(msg)

    def _estimate_pose(self, frame, corners, ids):
        positions = []

        for i, marker_id in enumerate(ids.flatten()):
            if marker_id not in MARKER_MAP:
                continue

            # Estimate marker pose relative to camera
            rvec, tvec, _ = aruco.estimatePoseSingleMarkers(
                [corners[i]], MARKER_SIZE, CAM_MATRIX, DIST_COEFFS)

            cv2.drawFrameAxes(frame, CAM_MATRIX, DIST_COEFFS,
                              rvec[0], tvec[0], MARKER_SIZE * 0.5)

            # Known marker world position
            mx, my = MARKER_MAP[marker_id]

            # Camera is offset from marker by tvec (in camera frame)
            # Simple 2D estimate: subtract x,z translation from marker world pos
            cam_x = mx - float(tvec[0][0][0])
            cam_y = my - float(tvec[0][0][2])

            positions.append((cam_x, cam_y))

            self.get_logger().info(
                f'Marker {marker_id}: estimated pos ({cam_x:.2f}, {cam_y:.2f})')

        if not positions:
            return

        # Average position from all visible markers
        est_x = float(np.mean([p[0] for p in positions]))
        est_y = float(np.mean([p[1] for p in positions]))

        # Publish pose estimate
        pose_msg = PoseWithCovarianceStamped()
        pose_msg.header.stamp = self.get_clock().now().to_msg()
        pose_msg.header.frame_id = 'map'
        pose_msg.pose.pose.position.x = est_x
        pose_msg.pose.pose.position.y = est_y
        pose_msg.pose.pose.position.z = 0.0
        pose_msg.pose.pose.orientation.w = 1.0

        # Covariance: low confidence single marker, higher with multiple
        cov = 0.1 if len(positions) == 1 else 0.05
        pose_msg.pose.covariance[0]  = cov  # x variance
        pose_msg.pose.covariance[7]  = cov  # y variance
        pose_msg.pose.covariance[35] = 0.2  # yaw variance

        self.pose_pub.publish(pose_msg)

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
