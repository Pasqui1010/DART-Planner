from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from ..common.types import ControlCommand, DroneState

# -----------------------------------------------------------------------------
# Simulator configuration helper
# -----------------------------------------------------------------------------


@dataclass
class SimulatorConfig:
    """Configuration parameters for :class:`DroneSimulator`.  Only a subset
    is actually used by the simple physics model; the rest are placeholders so
    that unit-tests and future extensions can pass richer settings without
    breaking the interface.

    The defaults mirror the values hard-coded in older experiment scripts so
    that behaviour stays unchanged if callers omit the config.
    """

    # Core physical parameters
    mass: float = 1.0
    gravity: float = 9.81

    # Simple disturbance / environment parameters (currently unused)
    wind_mean: float = 0.0
    wind_std: float = 0.0
    sensor_noise_std: float = 0.0
    drag_coefficient: float = 0.0


class DroneSimulator:
    """
    A simple physics simulator for a quadrotor drone.
    """

    def __init__(self, wind: Optional[np.ndarray] = None, max_thrust: float = 20.0, max_torque: float = 10.0) -> None:
        if wind is None:
            self.wind = np.zeros(3)
        else:
            self.wind = np.array(wind)
        self.max_thrust = max_thrust
        self.max_torque = max_torque
        self.mass = 1.5  # kg
        self.gravity = 9.81
        self.inertia = np.diag([0.1, 0.1, 0.2])

    def step(self, state: DroneState, command: ControlCommand, dt: float) -> DroneState:
        # Apply actuator saturation
        thrust = np.clip(command.thrust, 0, self.max_thrust)
        torque = np.clip(command.torque, -self.max_torque, self.max_torque)
        # Add wind disturbance to acceleration
        wind_accel = self.wind / self.mass
        # Simple translational dynamics
        acc = np.array([0, 0, -self.gravity]) + np.array([0, 0, thrust / self.mass]) + wind_accel
        new_velocity = state.velocity + acc * dt
        new_position = state.position + new_velocity * dt
        # Simple rotational dynamics
        angular_accel = np.linalg.solve(self.inertia, torque)
        new_angular_velocity = state.angular_velocity + angular_accel * dt
        new_attitude = state.attitude + new_angular_velocity * dt
        return DroneState(
            timestamp=state.timestamp + dt,
            position=new_position,
            velocity=new_velocity,
            attitude=new_attitude,
            angular_velocity=new_angular_velocity,
        )

    def _euler_to_rotation_matrix(self, att: np.ndarray) -> NDArray[np.float64]:
        """Converts Euler angles (roll, pitch, yaw) to a rotation matrix."""
        roll, pitch, yaw = att
        R_x = np.array(
            [
                [1, 0, 0],
                [0, np.cos(roll), -np.sin(roll)],
                [0, np.sin(roll), np.cos(roll)],
            ]
        )
        R_y = np.array(
            [
                [np.cos(pitch), 0, np.sin(pitch)],
                [0, 1, 0],
                [-np.sin(pitch), 0, np.cos(pitch)],
            ]
        )
        R_z = np.array(
            [[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]]
        )
        return (R_z @ R_y @ R_x).astype(np.float64)  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Compatibility shims expected by some tests/legacy code
    # ------------------------------------------------------------------
