import time
import numpy as np
from typing import Optional
from dart_planner.common.types import EstimatedState, Pose, Twist, Accel
from dart_planner.common.units import Q_, ensure_units

class PX4EKF2StateEstimator:
    """
    State estimator that wraps PX4 EKF2 outputs via MAVLink.
    Consumes ATTITUDE, GLOBAL_POSITION_INT, and (optionally) EKF_STATUS_REPORT/ODOMETRY.
    Outputs EstimatedState for use by controllers/planners.
    
    All sensor data is converted to proper units:
    - Position: meters (from lat/lon/alt or x/y/z)
    - Velocity: m/s (from vx/vy/vz)
    - Attitude: radians (from roll/pitch/yaw)
    - Angular velocity: rad/s (from roll/pitch/yaw rates)
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
                # Convert attitude from degrees to radians
                pose.orientation = ensure_units(Q_(np.array([msg.roll, msg.pitch, msg.yaw]), 'deg'), 'rad', 'ATTITUDE.orientation')
                # Convert angular velocities from deg/s to rad/s
                twist.angular = ensure_units(Q_(np.array([msg.rollspeed, msg.pitchspeed, msg.yawspeed]), 'deg/s'), 'rad/s', 'ATTITUDE.angular')
            elif msg_type == "GLOBAL_POSITION_INT":
                # Convert lat/lon from 1e7 scaling to degrees, then to meters (approximate)
                # Convert alt from mm to meters
                lat_deg = msg.lat / 1e7
                lon_deg = msg.lon / 1e7
                alt_m = msg.alt / 1e3
                
                # Simple conversion to local meters (approximate)
                # In practice, you'd use proper geodetic to local conversion
                pose.position = Q_(np.array([lat_deg * 111320, lon_deg * 111320, alt_m]), 'm')
                
                # Convert velocities from cm/s to m/s
                twist.linear = Q_(np.array([msg.vx / 100.0, msg.vy / 100.0, msg.vz / 100.0]), 'm/s')
            elif msg_type == "ODOMETRY":
                # If available, use ODOMETRY for pose/twist/covariance
                # (PX4 1.13+) - already in meters and radians
                pose.position = Q_(np.array([msg.x, msg.y, msg.z]), 'm')
                pose.orientation = Q_(np.array([msg.roll, msg.pitch, msg.yaw]), 'rad')
                twist.linear = Q_(np.array([msg.vx, msg.vy, msg.vz]), 'm/s')
                twist.angular = Q_(np.array([msg.rollspeed, msg.pitchspeed, msg.yawspeed]), 'rad/s')
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
