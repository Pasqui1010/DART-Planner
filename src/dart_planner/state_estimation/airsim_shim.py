import time
import numpy as np
from typing import Optional
from dart_planner.common.types import EstimatedState, Pose, Twist, Accel

class AirSimStateEstimator:
    """
    State estimator for AirSim simulation.
    Adds configurable Gaussian noise to ground-truth state to mimic real-world estimation.
    Outputs EstimatedState for use by controllers/planners.
    """
    def __init__(self, airsim_client, noise_std=None):
        self.airsim_client = airsim_client
        self.noise_std = noise_std or {
            'position': 0.02,   # meters
            'orientation': 0.01, # radians
            'linear': 0.05,     # m/s
            'angular': 0.01,    # rad/s
        }
        self._latest: Optional[EstimatedState] = None

    def update(self):
        """Poll AirSim for ground-truth state, add noise, and update the estimate."""
        now = time.time()
        pose = Pose()
        twist = Twist()
        accel = Accel()
        cov = None
        source = "AirSim"
        # Get ground-truth state
        state = self.airsim_client.getMultirotorState()
        # Position (NED)
        pos = np.array([
            state.kinematics_estimated.position.x_val,
            state.kinematics_estimated.position.y_val,
            state.kinematics_estimated.position.z_val
        ])
        pos += np.random.normal(0, self.noise_std['position'], 3)
        pose.position = pos
        # Orientation (convert quaternion to rpy)
        q = state.kinematics_estimated.orientation
        # AirSim: w, x, y, z
        w, x, y, z = q.w_val, q.x_val, q.y_val, q.z_val
        roll = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
        pitch = np.arcsin(2*(w*y - z*x))
        yaw = np.arctan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
        rpy = np.array([roll, pitch, yaw])
        rpy += np.random.normal(0, self.noise_std['orientation'], 3)
        pose.orientation = rpy
        # Linear velocity
        lin_vel = np.array([
            state.kinematics_estimated.linear_velocity.x_val,
            state.kinematics_estimated.linear_velocity.y_val,
            state.kinematics_estimated.linear_velocity.z_val
        ])
        lin_vel += np.random.normal(0, self.noise_std['linear'], 3)
        twist.linear = lin_vel
        # Angular velocity
        ang_vel = np.array([
            state.kinematics_estimated.angular_velocity.x_val,
            state.kinematics_estimated.angular_velocity.y_val,
            state.kinematics_estimated.angular_velocity.z_val
        ])
        ang_vel += np.random.normal(0, self.noise_std['angular'], 3)
        twist.angular = ang_vel
        # (Optional) Acceleration: not directly available, could be estimated by finite difference
        # For now, leave as zeros
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
