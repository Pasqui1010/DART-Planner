from common.types import Trajectory, DroneState
import numpy as np
from typing import Optional, Tuple
import time


class TrajectorySmoother:
    """
    Trajectory smoother for edge execution.

    This class handles smooth transitions between trajectories provided by the cloud
    planner, ensuring continuity in position, velocity, and acceleration commands
    to prevent control instabilities.

    Key features:
    - Smooth splicing of new trajectories with current motion
    - Minimum jerk trajectory generation for transitions
    - Failsafe trajectory generation when cloud communication fails
    """

    def __init__(
        self,
        transition_time: float = 0.5,
        max_velocity: float = 10.0,
        max_acceleration: float = 5.0,
    ):
        self.transition_time = transition_time
        self.max_velocity = max_velocity
        self.max_acceleration = max_acceleration

        # Current trajectory state
        self.current_trajectory: Optional[Trajectory] = None
        self.trajectory_start_time: float = 0.0
        self.last_cloud_update: float = 0.0

        # Smooth transition state
        self.in_transition = False
        self.transition_start_time: float = 0.0
        self.transition_start_pos: np.ndarray = np.zeros(3)
        self.transition_start_vel: np.ndarray = np.zeros(3)
        self.transition_target_pos: np.ndarray = np.zeros(3)
        self.transition_target_vel: np.ndarray = np.zeros(3)

        print("Trajectory Smoother initialized for edge execution")

    def update_trajectory(self, new_trajectory: Trajectory, current_state: DroneState):
        """
        Update with a new trajectory from the cloud planner.

        This method smoothly transitions from the current motion to the new trajectory
        to avoid discontinuities that cause control instabilities.
        """
        current_time = time.time()
        self.last_cloud_update = current_time

        if self.current_trajectory is None:
            # First trajectory - no transition needed
            self.current_trajectory = new_trajectory
            self.trajectory_start_time = current_time
            self.in_transition = False
            print("First trajectory received from cloud")
            return

        # Get current desired state from existing trajectory
        (
            current_des_pos,
            current_des_vel,
            current_des_acc,
        ) = self._interpolate_trajectory(
            current_time, self.current_trajectory, self.trajectory_start_time
        )

        # Get target state from new trajectory
        new_start_pos, new_start_vel, new_start_acc = self._interpolate_trajectory(
            current_time, new_trajectory, current_time
        )

        # Check if we need a transition (significant difference in commands)
        pos_diff = np.linalg.norm(new_start_pos - current_des_pos)
        vel_diff = np.linalg.norm(new_start_vel - current_des_vel)

        if pos_diff > 0.5 or vel_diff > 1.0:
            # Start smooth transition
            self.in_transition = True
            self.transition_start_time = current_time
            self.transition_start_pos = current_des_pos
            self.transition_start_vel = current_des_vel
            self.transition_target_pos = new_start_pos
            self.transition_target_vel = new_start_vel
            print(
                f"Starting smooth transition: pos_diff={pos_diff:.2f}, vel_diff={vel_diff:.2f}"
            )

        # Update trajectory
        self.current_trajectory = new_trajectory
        self.trajectory_start_time = current_time

    def get_desired_state(
        self, current_time: float, current_state: DroneState
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get desired position, velocity, and acceleration at the current time.

        Returns smooth, continuous commands that prevent control instabilities.
        """
        # Check for communication timeout (failsafe)
        if current_time - self.last_cloud_update > 2.0:
            return self._get_failsafe_trajectory(current_time, current_state)

        # Handle smooth transition
        if self.in_transition:
            transition_progress = (
                current_time - self.transition_start_time
            ) / self.transition_time

            if transition_progress >= 1.0:
                # Transition complete
                self.in_transition = False
            else:
                # Generate smooth transition using minimum jerk trajectory
                return self._generate_transition_state(transition_progress)

        # Normal trajectory following
        if self.current_trajectory is not None:
            return self._interpolate_trajectory(
                current_time, self.current_trajectory, self.trajectory_start_time
            )
        else:
            # No trajectory available - hover
            return current_state.position, np.zeros(3), np.zeros(3)

    def _interpolate_trajectory(
        self, current_time: float, trajectory: Trajectory, start_time: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Interpolate trajectory at given time."""
        trajectory_time = current_time - start_time

        if len(trajectory.timestamps) == 0:
            return np.zeros(3), np.zeros(3), np.zeros(3)

        # Adjust trajectory timestamps to start from trajectory_time = 0
        traj_times = trajectory.timestamps - trajectory.timestamps[0]

        # Find interpolation indices
        if trajectory_time <= traj_times[0]:
            idx = 0
            pos = trajectory.positions[0]
            vel = (
                trajectory.velocities[0]
                if trajectory.velocities is not None
                else np.zeros(3)
            )
            acc = (
                trajectory.accelerations[0]
                if trajectory.accelerations is not None
                else np.zeros(3)
            )
        elif trajectory_time >= traj_times[-1]:
            idx = len(traj_times) - 1
            pos = trajectory.positions[-1]
            vel = (
                trajectory.velocities[-1]
                if trajectory.velocities is not None
                else np.zeros(3)
            )
            acc = (
                trajectory.accelerations[-1]
                if trajectory.accelerations is not None
                else np.zeros(3)
            )
        else:
            # Linear interpolation
            idx = np.searchsorted(traj_times, trajectory_time) - 1
            t1, t2 = traj_times[idx], traj_times[idx + 1]
            alpha = (trajectory_time - t1) / (t2 - t1)

            pos = (1 - alpha) * trajectory.positions[
                idx
            ] + alpha * trajectory.positions[idx + 1]

            if trajectory.velocities is not None:
                vel = (1 - alpha) * trajectory.velocities[
                    idx
                ] + alpha * trajectory.velocities[idx + 1]
            else:
                vel = np.zeros(3)

            if trajectory.accelerations is not None:
                acc = (1 - alpha) * trajectory.accelerations[
                    idx
                ] + alpha * trajectory.accelerations[idx + 1]
            else:
                acc = np.zeros(3)

        return pos, vel, acc

    def _generate_transition_state(
        self, progress: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate smooth transition using minimum jerk trajectory."""
        # Quintic polynomial for smooth transition (minimum jerk)
        t = np.clip(progress, 0.0, 1.0)

        # Quintic polynomial coefficients for smooth interpolation
        s = 10 * t**3 - 15 * t**4 + 6 * t**5  # Position blend factor
        s_dot = (
            30 * t**2 - 60 * t**3 + 30 * t**4
        ) / self.transition_time  # Velocity blend factor
        s_ddot = (60 * t - 180 * t**2 + 120 * t**3) / (
            self.transition_time**2
        )  # Acceleration blend factor

        # Interpolated position
        pos = (1 - s) * self.transition_start_pos + s * self.transition_target_pos

        # Interpolated velocity
        pos_diff = self.transition_target_pos - self.transition_start_pos
        vel = (
            (1 - s) * self.transition_start_vel
            + s * self.transition_target_vel
            + s_dot * pos_diff
        )

        # Interpolated acceleration
        acc = s_ddot * pos_diff

        # Apply safety limits
        vel_norm = np.linalg.norm(vel)
        if vel_norm > self.max_velocity:
            vel = vel * (self.max_velocity / vel_norm)

        acc_norm = np.linalg.norm(acc)
        if acc_norm > self.max_acceleration:
            acc = acc * (self.max_acceleration / acc_norm)

        return pos, vel, acc

    def _get_failsafe_trajectory(
        self, current_time: float, current_state: DroneState
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate safe hover trajectory when cloud communication is lost."""
        # Gradually reduce velocity to zero and maintain current position
        target_pos = current_state.position

        # Exponential decay to zero velocity
        decay_rate = 2.0  # 1/s
        vel_decay = np.exp(
            -decay_rate * min(current_time - self.last_cloud_update - 2.0, 5.0)
        )
        target_vel = current_state.velocity * vel_decay

        # Acceleration to reduce velocity
        target_acc = -decay_rate * target_vel

        return target_pos, target_vel, target_acc

    def is_trajectory_valid(self) -> bool:
        """Check if current trajectory is valid and recent."""
        return (
            self.current_trajectory is not None
            and time.time() - self.last_cloud_update < 2.0
        )

    def get_status(self) -> dict:
        """Get current status for debugging."""
        return {
            "has_trajectory": self.current_trajectory is not None,
            "in_transition": self.in_transition,
            "last_update_age": time.time() - self.last_cloud_update,
            "trajectory_valid": self.is_trajectory_valid(),
        }
