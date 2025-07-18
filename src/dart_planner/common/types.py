from dataclasses import dataclass, field
from typing import List, Optional, Union, TypeAlias

import os
import numpy as np
from pint import Quantity
from dart_planner.common.units import Q_, ensure_units

@dataclass
class Pose:
    """Represents position and orientation (in radians, as roll/pitch/yaw or quaternion)."""
    position: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'm'))
    orientation: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'rad'))  # roll, pitch, yaw

@dataclass
class Twist:
    """Represents linear and angular velocity."""
    linear: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'm/s'))
    angular: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'rad/s'))

@dataclass
class Accel:
    """Represents linear and angular acceleration."""
    linear: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'm/s^2'))
    angular: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'rad/s^2'))

@dataclass
class FastDroneState:
    """
    Unit-stripped drone state for high-frequency control loops.
    
    All fields are numpy arrays in base SI units (no pint overhead):
    - position: meters (m)
    - velocity: m/s
    - attitude: radians (rad)
    - angular_velocity: rad/s
    - timestamp: seconds (s)
    """
    timestamp: float
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))      # meters
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))      # m/s
    attitude: np.ndarray = field(default_factory=lambda: np.zeros(3))      # rad
    angular_velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))  # rad/s
    
    @classmethod
    def from_drone_state(cls, state: 'DroneState') -> 'FastDroneState':
        """Convert DroneState to FastDroneState, stripping units."""
        return cls(
            timestamp=state.timestamp,
            position=state.position.to('m').magnitude,
            velocity=state.velocity.to('m/s').magnitude,
            attitude=state.attitude.to('rad').magnitude,
            angular_velocity=state.angular_velocity.to('rad/s').magnitude,
        )

# ---------------------------------------------------------------------------
# Type aliases to improve static type-checking clarity.
# ---------------------------------------------------------------------------

QuantityVector: TypeAlias = Quantity  # 1-D vector quantity (e.g. m, m/s, rad)

@dataclass
class DroneState:
    """Represents the complete state of the drone at a single point in time.

    All fields use pint.Quantity for units safety.
    - position: meters
    - velocity: m/s
    - attitude: radians (roll, pitch, yaw)
    - angular_velocity: rad/s
    - motor_rpms: RPM (unitless for now)
    """
    timestamp: float
    position: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'm'))
    velocity: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'm/s'))
    attitude: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'rad'))
    angular_velocity: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'rad/s'))
    motor_rpms: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(4))

    def __post_init__(self):
        # ------------------------------------------------------------------
        # Development-mode guard: reject raw np.ndarray to enforce unit safety
        # ------------------------------------------------------------------
        if os.getenv("DART_DEV_MODE", "0") == "1":
            for fname in ("position", "velocity", "attitude", "angular_velocity"):
                val = getattr(self, fname)
                if isinstance(val, np.ndarray):
                    raise TypeError(
                        f"{fname} received raw ndarray in DroneState; use pint.Quantity or FastDroneState."
                    )

        self.position = ensure_units(self.position, 'm', 'DroneState.position')
        self.velocity = ensure_units(self.velocity, 'm/s', 'DroneState.velocity')
        self.attitude = ensure_units(self.attitude, 'rad', 'DroneState.attitude')
        self.angular_velocity = ensure_units(self.angular_velocity, 'rad/s', 'DroneState.angular_velocity')
        
    def to_fast_state(self) -> FastDroneState:
        """Convert to FastDroneState for high-frequency control loops."""
        return FastDroneState.from_drone_state(self)

@dataclass
class ControlCommand:
    """Represents the output of the low-level controller, sent to the motors.
    - thrust: Newtons (N)
    - torque: Nm (roll, pitch, yaw moments)
    """
    thrust: Quantity = field(default_factory=lambda: Q_(0.0, 'N'))
    torque: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'N*m'))

    def __post_init__(self):
        self.thrust = ensure_units(self.thrust, 'N', 'ControlCommand.thrust')
        self.torque = ensure_units(self.torque, 'N*m', 'ControlCommand.torque')

@dataclass
class BodyRateCommand:
    """Represents body-rate control command for PX4 compatibility.
    - thrust: Normalized (0-1, unitless)
    - body_rates: rad/s (roll, pitch, yaw rates)
    """
    thrust: float  # Normalized thrust (0-1)
    body_rates: Quantity = field(default_factory=lambda: Q_(np.zeros(3), 'rad/s'))

    def __post_init__(self):
        self.body_rates = ensure_units(self.body_rates, 'rad/s', 'BodyRateCommand.body_rates')

@dataclass
class Trajectory:
    """Represents a time-indexed sequence of desired states, generated by the planner.
    All arrays are expected to be pint.Quantity with appropriate units.
    """
    timestamps: np.ndarray
    positions: Quantity
    velocities: Optional[Quantity] = None
    accelerations: Optional[Quantity] = None
    attitudes: Optional[Quantity] = None  # Roll, Pitch, Yaw (rad)
    body_rates: Optional[Quantity] = None  # Roll, Pitch, Yaw rates (rad/s)
    thrusts: Optional[Quantity] = None  # Thrust magnitudes (N)
    yaws: Optional[Quantity] = None
    yaw_rates: Optional[Quantity] = None

@dataclass
class EstimatedState:
    """Standardized output of a state estimator (EKF2, AirSim, etc)."""
    timestamp: float
    pose: Pose = field(default_factory=Pose)
    twist: Twist = field(default_factory=Twist)
    accel: Accel = field(default_factory=Accel)
    covariance: Optional[np.ndarray] = None  # 9x9 or 15x15 covariance matrix, if available
    source: str = "unknown"  # e.g., 'PX4_EKF2', 'AirSim', etc.
