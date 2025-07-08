import asyncio
from dart_planner.common.di_container_v2 import get_container
import time

import numpy as np

from dart_planner.common.types import Trajectory
from dart_planner.communication.zmq_server import ZmqServer
from dart_planner.planning.se3_mpc_planner import SE3MPCConfig, SE3MPCPlanner

import logging
from dart_planner.common.logging_config import get_logger
logger = get_logger(__name__)


def main_improved():
    """
    Improved cloud node main loop implementing the **SE(3) MPC** planner that
    replaced the original DIAL-MPC in the edge-first architecture.

    Highlights
    - Uses a domain-appropriate SE(3) MPC for quadrotor dynamics
    - Runs at ~10 Hz on the cloud side (non-critical)
    - Generates smooth, dynamically-feasible trajectories
    - Includes proper error handling and fall-backs
    """
    logger.info("=== Improved Distributed Cloud Planner ===")

    # Initialize SE(3) MPC planner with tuned configuration
    planner_config = SE3MPCConfig(
        prediction_horizon=8,  # 0.8 s look-ahead at 100 ms steps
        dt=0.1,
        max_velocity=10.0,
        max_acceleration=15.0,
        position_weight=100.0,
        velocity_weight=10.0,
        obstacle_weight=1000.0,
        safety_margin=1.5,
    )

    se3_mpc_planner = SE3MPCPlanner(planner_config)
    from dart_planner.communication.zmq_server import ZmqServer
    zmq_server = get_container().resolve(ZmqServer)

    # Define mission goal
    goal_position = np.array([10.0, 10.0, 5.0])
    logger.info(f"Mission goal: {goal_position}")

    # Add some example obstacles for testing
    se3_mpc_planner.add_obstacle(np.array([5.0, 5.0, 2.5]), 1.0)
    se3_mpc_planner.add_obstacle(np.array([7.5, 7.5, 3.0]), 0.8)

    planning_count = 0

    def handle_state_update(data: dict):
        """Handle state update requests from the edge."""
        nonlocal planning_count
        try:
            drone_state = data.get("state")
            if drone_state:
                logger.info(f"\n--- Planning Cycle {planning_count} ---")
                logger.info(
                    f"Received state: pos={np.round(drone_state.position, 2)}, "
                    f"vel={np.round(drone_state.velocity, 2)}"
                )

                # Plan optimal trajectory using SE(3) MPC
                start_time = time.time()
                trajectory = se3_mpc_planner.plan_trajectory(drone_state, goal_position)
                planning_time = time.time() - start_time

                logger.info(f"SE(3) MPC planning completed in {planning_time*1000:.1f}ms")
                logger.info(f"Generated trajectory: {len(trajectory.positions)} waypoints")

                # Performance logging
                if planning_count % 10 == 0 and planning_count > 0:
                    logger.info(f"\nSE(3) MPC Performance Stats:")
                    logger.info(f"  Planning cycle: {planning_count}")
                    logger.info(f"  Recent planning time: {planning_time*1000:.1f}ms")

                # Check if goal reached
                goal_distance = np.linalg.norm(drone_state.position - goal_position)
                if goal_distance < 1.0:
                    logger.info(f"\n🎯 Goal reached! Distance: {goal_distance:.2f}m")

                planning_count += 1
                return {"trajectory": trajectory}
            else:
                logger.warning("No state received, sending fallback trajectory")
                # Create fallback hover trajectory
                fallback_traj = Trajectory(
                    timestamps=np.array([time.time()]),
                    positions=np.array([[0, 0, 1]]),
                    velocities=np.array([[0, 0, 0]]),
                    accelerations=np.array([[0, 0, 0]]),
                )
                return {"trajectory": fallback_traj}
        except Exception as e:
            logger.error(f"Error in planning: {e}")
            # Return fallback trajectory on error
            fallback_traj = Trajectory(
                timestamps=np.array([time.time()]),
                positions=np.array([[0, 0, 1]]),
                velocities=np.array([[0, 0, 0]]),
                accelerations=np.array([[0, 0, 0]]),
            )
            return {"trajectory": fallback_traj}

    # Add the handler to the server
    zmq_server.add_handler("state_update", handle_state_update)

    try:
        logger.info("Cloud planner ready. Starting ZMQ server...")
        zmq_server.start()
        logger.info("Server running. Press Ctrl+C to stop.")

        # Keep the server running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\nShutting down cloud planner.")

    finally:
        # Final performance summary
        if planning_count > 0:
            logger.info(f"\nFinal SE(3) MPC Performance Summary:")
            logger.info(f"  Total planning cycles: {planning_count}")

        zmq_server.stop()
        logger.info("Cloud planner shutdown complete.")


if __name__ == "__main__":
    main_improved()
