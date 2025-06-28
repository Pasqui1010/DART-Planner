import numpy as np
from src.common.types import DroneState, ControlCommand

class DroneSimulator:
    """
    A simple physics simulator for a quadrotor drone.
    """
    def __init__(self, mass=1.0, g=9.81, I=np.eye(3)):
        """
        Initializes the simulator with drone parameters.
        Args:
            mass (float): Mass of the drone in kg.
            g (float): Acceleration due to gravity in m/s^2.
            I (np.ndarray): 3x3 inertia matrix of the drone.
        """
        self.mass = mass
        self.g = g
        self.I = I
        self.inv_I = np.linalg.inv(I)
        print("Drone simulator initialized.")

    def step(self, current_state: DroneState, command: ControlCommand, dt: float) -> DroneState:
        """
        Advances the drone's state by one time step.
        Args:
            current_state: The current state of the drone.
            command: The control command (thrust and torque) to apply.
            dt: The time step duration in seconds.
        Returns:
            The new state of the drone after the time step.
        """
        # Unpack state
        pos = current_state.position
        vel = current_state.velocity
        att = current_state.attitude
        ang_vel = current_state.angular_velocity

        # Rotation matrix from body to world frame
        R = self._euler_to_rotation_matrix(att)

        # 1. Calculate forces and accelerations
        thrust_force = R @ np.array([0, 0, command.thrust])
        gravity_force = np.array([0, 0, -self.mass * self.g])
        total_force = thrust_force + gravity_force
        acceleration = total_force / self.mass

        # 2. Calculate angular acceleration
        angular_acceleration = self.inv_I @ (command.torque - np.cross(ang_vel, self.I @ ang_vel))

        # 3. Integrate to find new state (using simple Euler integration)
        new_vel = vel + acceleration * dt
        new_pos = pos + new_vel * dt
        new_ang_vel = ang_vel + angular_acceleration * dt
        new_att = att + new_ang_vel * dt

        return DroneState(
            timestamp=current_state.timestamp + dt,
            position=new_pos,
            velocity=new_vel,
            attitude=new_att,
            angular_velocity=new_ang_vel
        )

    def _euler_to_rotation_matrix(self, att: np.ndarray) -> np.ndarray:
        """Converts Euler angles (roll, pitch, yaw) to a rotation matrix."""
        roll, pitch, yaw = att
        R_x = np.array([[1, 0, 0],
                        [0, np.cos(roll), -np.sin(roll)],
                        [0, np.sin(roll), np.cos(roll)]])
        R_y = np.array([[np.cos(pitch), 0, np.sin(pitch)],
                        [0, 1, 0],
                        [-np.sin(pitch), 0, np.cos(pitch)]])
        R_z = np.array([[np.cos(yaw), -np.sin(yaw), 0],
                        [np.sin(yaw), np.cos(yaw), 0],
                        [0, 0, 1]])
        return R_z @ R_y @ R_x 