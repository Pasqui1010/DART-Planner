import logging
from typing import Optional, Tuple

import numpy as np

from dart_planner.common.types import ControlCommand, DroneState, Trajectory
from dart_planner.control.control_config import ControllerTuningProfile
from dart_planner.utils.pid_controller import PIDController
from dart_planner.common.logging_config import get_logger


# def _create_pid(gains: PIDGains) -> PIDController:
#     return PIDController(
#         gains.Kp, gains.Ki, gains.Kd, integral_limit=gains.integral_limit
#     )


class OnboardController:
    """
    High-frequency controller running on the drone.
    Uses a cascaded PID structure to convert a desired trajectory and
    current state into low-level motor commands.
    """

    def __init__(self, mass: float = 1.0, g: float = 9.81) -> None:
        self.mass = mass
        self.g = g

        # Create simple PID controllers with default gains
        self.pos_x_pid = PIDController(10.0, 1.0, 5.0, integral_limit=2.0)
        self.pos_y_pid = PIDController(10.0, 1.0, 5.0, integral_limit=2.0)
        self.pos_z_pid = PIDController(12.0, 1.5, 6.0, integral_limit=2.0)
        self.roll_pid = PIDController(8.0, 0.0, 2.0, integral_limit=1.0)
        self.pitch_pid = PIDController(8.0, 0.0, 2.0, integral_limit=1.0)
        self.yaw_rate_pid = PIDController(4.0, 0.0, 1.0, integral_limit=0.5)

        self.last_time = None
        
        # Setup logging
        self.logger = get_logger(__name__)
        self.logger.info("Onboard Controller upgraded to Feedforward+Feedback architecture.")

    def _interpolate_trajectory(
        self, current_time: float, trajectory: Trajectory
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Finds the target state by interpolating the trajectory.
        Returns target position, velocity, and acceleration.
        """
        idx = np.searchsorted(trajectory.timestamps, current_time)

        if idx == 0:
            vel = (
                trajectory.velocities[0]
                if trajectory.velocities is not None
                else np.zeros(3)
            )
            accel = (
                trajectory.accelerations[0]
                if trajectory.accelerations is not None
                else np.zeros(3)
            )
            return trajectory.positions[0], vel, accel
        if idx >= len(trajectory.timestamps):
            vel = (
                trajectory.velocities[-1]
                if trajectory.velocities is not None
                else np.zeros(3)
            )
            accel = (
                trajectory.accelerations[-1]
                if trajectory.accelerations is not None
                else np.zeros(3)
            )
            return trajectory.positions[-1], vel, accel

        t1, t2 = trajectory.timestamps[idx - 1], trajectory.timestamps[idx]
        p1, p2 = trajectory.positions[idx - 1], trajectory.positions[idx]

        interp_factor = (current_time - t1) / (t2 - t1)
        target_pos = p1 + interp_factor * (p2 - p1)

        target_vel = np.zeros(3)
        if trajectory.velocities is not None:
            v1, v2 = trajectory.velocities[idx - 1], trajectory.velocities[idx]
            target_vel = v1 + interp_factor * (v2 - v1)

        target_accel = np.zeros(3)
        if trajectory.accelerations is not None:
            a1, a2 = trajectory.accelerations[idx - 1], trajectory.accelerations[idx]
            target_accel = a1 + interp_factor * (a2 - a1)

        return target_pos, target_vel, target_accel

    def _compute_desired_attitude_and_thrust(
        self, desired_accel: np.ndarray, current_yaw: float
    ) -> Tuple[float, float, float]:
        """Converts desired acceleration into desired thrust, roll, and pitch."""

        thrust = self.mass * (desired_accel[2] + self.g)
        thrust = max(0.0, thrust)

        # Simplified inversion of dynamics, assumes small angles
        desired_roll = (1 / self.g) * (
            desired_accel[0] * np.sin(current_yaw)
            - desired_accel[1] * np.cos(current_yaw)
        )
        desired_pitch = (1 / self.g) * (
            desired_accel[0] * np.cos(current_yaw)
            + desired_accel[1] * np.sin(current_yaw)
        )

        return desired_roll, desired_pitch, thrust

    def _compute_torque(
        self,
        desired_roll: float,
        desired_pitch: float,
        target_yaw_rate: float,
        current_state: DroneState,
        dt: float,
    ) -> np.ndarray:
        """Computes the required torque using the inner-loop PID controllers."""

        self.roll_pid.setpoint = desired_roll
        roll_torque = self.roll_pid.update(current_state.attitude[0], dt)

        self.pitch_pid.setpoint = desired_pitch
        pitch_torque = self.pitch_pid.update(current_state.attitude[1], dt)

        self.yaw_rate_pid.setpoint = target_yaw_rate
        yaw_torque = self.yaw_rate_pid.update(current_state.angular_velocity[2], dt)

        return np.array([roll_torque, pitch_torque, yaw_torque])

    def sense(self, current_state: DroneState, trajectory: Trajectory) -> Tuple[float, np.ndarray, np.ndarray, np.ndarray]:
        """Extracts current time, dt, and interpolates trajectory targets."""
        current_time = current_state.timestamp
        dt = current_time - self.last_time if self.last_time is not None else 0.01
        self.last_time = current_time
        target_pos, target_vel, target_accel = self._interpolate_trajectory(current_time, trajectory)
        return dt, target_pos, target_vel, target_accel

    def plan(self, current_state: DroneState, target_pos: np.ndarray, target_accel: np.ndarray, dt: float) -> Tuple[float, float, float]:
        """Computes corrective acceleration and desired attitude/thrust."""
        # Feedback Control (PID)
        self.pos_x_pid.setpoint = target_pos[0]
        corrective_accel_x = self.pos_x_pid.update(current_state.position[0], dt)
        self.pos_y_pid.setpoint = target_pos[1]
        corrective_accel_y = self.pos_y_pid.update(current_state.position[1], dt)
        self.pos_z_pid.setpoint = target_pos[2]
        corrective_accel_z = self.pos_z_pid.update(current_state.position[2], dt)
        corrective_acceleration = np.array([
            corrective_accel_x, corrective_accel_y, corrective_accel_z
        ])
        # Feedforward + Feedback
        desired_accel = target_accel + corrective_acceleration
        desired_roll, desired_pitch, thrust = self._compute_desired_attitude_and_thrust(
            desired_accel, current_state.attitude[2]
        )
        return desired_roll, desired_pitch, thrust

    def act(self, current_state: DroneState, desired_roll: float, desired_pitch: float, thrust: float, dt: float) -> ControlCommand:
        """Computes torque and returns the final control command."""
        target_yaw_rate = 0.0  # Not commanding yaw changes for now
        torque = self._compute_torque(
            desired_roll, desired_pitch, target_yaw_rate, current_state, dt
        )
        command = ControlCommand(thrust=thrust, torque=torque)
        return command

    def compute_control_command(
        self, current_state: DroneState, trajectory: Trajectory
    ) -> Tuple[ControlCommand, np.ndarray]:
        dt, target_pos, target_vel, target_accel = self.sense(current_state, trajectory)
        if dt <= 0:
            return ControlCommand(thrust=0, torque=np.zeros(3)), np.zeros(3)
        desired_roll, desired_pitch, thrust = self.plan(current_state, target_pos, target_accel, dt)
        command = self.act(current_state, desired_roll, desired_pitch, thrust, dt)
        return command, target_pos

    def get_fallback_command(self, current_state: DroneState) -> ControlCommand:
        """Returns a safe control command (hover)."""
        return ControlCommand(thrust=self.mass * self.g, torque=np.zeros(3))

    def reset(self) -> None:
        self.pos_x_pid.reset()
        self.pos_y_pid.reset()
        self.pos_z_pid.reset()
        self.roll_pid.reset()
        self.pitch_pid.reset()
        self.yaw_rate_pid.reset()
        self.last_time = None
