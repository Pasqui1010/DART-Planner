"""
SE(3) MPC Configuration for Quadrotor Dynamics

Contains the SE3MPCConfig dataclass with all tunable parameters for the SE(3) Model Predictive Controller.
"""

import numpy as np
from dataclasses import dataclass

@dataclass(frozen=True)
class SE3MPCConfig:
    """Configuration for SE(3) MPC designed for quadrotor dynamics"""

    # Prediction horizon - optimized for real-time performance
    prediction_horizon: int = 6  # Minimal horizon for real-time (750ms lookahead)
    dt: float = 0.125  # 125ms time steps - will be overridden by timing alignment

    # Physical constraints specific to quadrotors
    max_velocity: float = 10.0  # m/s - reasonable for aggressive maneuvers
    max_acceleration: float = 15.0  # m/s^2 - considering gravity compensation
    max_jerk: float = 20.0  # m/s^3 - for dynamic feasibility
    max_thrust: float = 25.0  # N - 2.5x nominal hover thrust (4kg drone)
    min_thrust: float = 2.0  # N - minimum controllable thrust

    # SE(3) specific parameters
    max_tilt_angle: float = np.pi / 4  # 45 degrees maximum tilt
    max_angular_velocity: float = 4.0  # rad/s

    # Cost function weights - tuned for quadrotor performance
    position_weight: float = 100.0  # Strong position tracking
    velocity_weight: float = 10.0  # Velocity regulation
    acceleration_weight: float = 1.0  # Smooth accelerations
    thrust_weight: float = 0.1  # Control effort minimization
    angular_weight: float = 10.0  # Attitude regulation

    # Obstacle avoidance
    obstacle_weight: float = 1000.0  # High penalty for collisions
    safety_margin: float = 1.5  # meters

    # Optimization parameters - optimized for speed
    max_iterations: int = 15  # Minimal iterations for real-time
    convergence_tolerance: float = 5e-2  # Very relaxed for speed 