from common.types import DroneState, Trajectory
import numpy as np
import time


class CloudPlanner:
    """
    High-level planner running in the cloud.
    Uses computationally intensive methods (like DIAL-MPC) and a neural scene
    representation to generate optimal trajectories.
    """

    def __init__(self):
        # Placeholder for planner models (e.g., scene representation, dynamics model)
        print("Cloud Planner initialized.")
        self.plan_count = 0
        # self.dial_mpc = ContinuousDIALMPC(...) # Example
        pass

    def plan_trajectory(
        self, current_state: DroneState, goal_position: np.ndarray
    ) -> Trajectory:
        """
        Generates an optimal trajectory from the current state to a goal.
        For this version, it generates a circular path around a goal point.
        """
        print(f"Cloud planner received state. Planning a path near {goal_position}...")

        # --- Generate a Circular Trajectory ---
        # This is a placeholder for a real planner like DIAL-MPC.
        # It creates a circular path to demonstrate trajectory tracking.
        radius = 5.0
        angular_speed = 0.5  # rad/s
        num_waypoints = 50
        total_time = (2 * np.pi) / angular_speed  # Time for one full circle

        # Start the circle from an angle based on the current drone position
        # to make the transition smoother, but for this demo, we start at a fixed point.
        start_angle = np.arctan2(
            current_state.position[1] - goal_position[1],
            current_state.position[0] - goal_position[0],
        )

        angles = np.linspace(start_angle, start_angle + 2 * np.pi, num_waypoints)

        timestamps = np.linspace(time.time(), time.time() + total_time, num_waypoints)

        # Create waypoints for the circle in the XY plane, at the goal's Z height
        positions_x = goal_position[0] + radius * np.cos(angles)
        positions_y = goal_position[1] + radius * np.sin(angles)
        positions_z = np.full(num_waypoints, goal_position[2])

        positions = np.vstack([positions_x, positions_y, positions_z]).T

        # Calculate tangential velocities (optional but good for advanced control)
        velocities_x = -radius * angular_speed * np.sin(angles)
        velocities_y = radius * angular_speed * np.cos(angles)
        velocities_z = np.zeros(num_waypoints)
        velocities = np.vstack([velocities_x, velocities_y, velocities_z]).T

        print("Circular trajectory planned successfully.")
        self.plan_count += 1
        return Trajectory(
            timestamps=timestamps,
            positions=positions,
            velocities=velocities,
            attitudes=None,
        )
