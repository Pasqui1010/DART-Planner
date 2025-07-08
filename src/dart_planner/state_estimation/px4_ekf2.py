import time
import numpy as np
from typing import Optional
from dart_planner.common.types import EstimatedState, Pose, Twist, Accel

class PX4EKF2StateEstimator:
    """
    State estimator that wraps PX4 EKF2 outputs via MAVLink.
    Consumes ATTITUDE, GLOBAL_POSITION_INT, and (optionally) EKF_STATUS_REPORT/ODOMETRY.
    Outputs EstimatedState for use by controllers/planners.
    """
    def __init__(self, mavlink_connection):
        self.mavlink_connection = mavlink_connection
        self._latest: Optional[EstimatedState] = None

    def update(self):
        """Poll MAVLink for new state messages and update the estimate."""
        now = time.time()
        pose = Pose()
        twist = Twist()
        accel = Accel()
        cov = None
        source = "PX4_EKF2"
        # Parse messages
        while True:
            msg = self.mavlink_connection.recv_match(
                type=["ATTITUDE", "GLOBAL_POSITION_INT", "EKF_STATUS_REPORT", "ODOMETRY"],
                blocking=False,
            )
            if not msg:
                break
            msg_type = msg.get_type()
            if msg_type == "ATTITUDE":
                pose.orientation = np.array([msg.roll, msg.pitch, msg.yaw])
                twist.angular = np.array([msg.rollspeed, msg.pitchspeed, msg.yawspeed])
            elif msg_type == "GLOBAL_POSITION_INT":
                pose.position = np.array([msg.lat / 1e7, msg.lon / 1e7, msg.alt / 1e3])
                twist.linear = np.array([msg.vx / 100.0, msg.vy / 100.0, msg.vz / 100.0])
            elif msg_type == "ODOMETRY":
                # If available, use ODOMETRY for pose/twist/covariance
                # (PX4 1.13+)
                pose.position = np.array([
                    msg.x, msg.y, msg.z
                ])
                pose.orientation = np.array([
                    msg.roll, msg.pitch, msg.yaw
                ])
                twist.linear = np.array([msg.vx, msg.vy, msg.vz])
                twist.angular = np.array([msg.rollspeed, msg.pitchspeed, msg.yawspeed])
                # Covariance parsing (if present)
                if hasattr(msg, "pose_covariance"):
                    cov = np.array(msg.pose_covariance).reshape((6, 6))
            elif msg_type == "EKF_STATUS_REPORT":
                # Optionally parse innovation/variance metrics
                pass
        self._latest = EstimatedState(
            timestamp=now,
            pose=pose,
            twist=twist,
            accel=accel,
            covariance=cov,
            source=source,
        )

    def get_latest(self) -> Optional[EstimatedState]:
        """Return the most recent state estimate."""
        return self._latest 
