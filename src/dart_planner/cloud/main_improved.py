import asyncio
from dart_planner.common.di_container import get_container
import time

import numpy as np

from dart_planner.common.types import Trajectory
from dart_planner.communication.zmq_server import ZmqServer
from dart_planner.planning.se3_mpc_planner import SE3MPCConfig, SE3MPCPlanner


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
    print("=== Improved Distributed Cloud Planner ===")

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
    zmq_server = get_container().create_communication_container().get_zmq_server()

    # Define mission goal
    goal_position = np.array([10.0, 10.0, 5.0])
    print(f"Mission goal: {goal_position}")

    # Add some example obstacles for testing
    se3_mpc_planner.add_obstacle(np.array([5.0, 5.0, 2.5]), 1.0)
    se3_mpc_planner.add_obstacle(np.array([7.5, 7.5, 3.0]), 0.8)

    planning_count = 0

    try:
        print("Cloud planner ready. Waiting for edge connections...")

        while True:
            print(f"\n--- Planning Cycle {planning_count} ---")
            print("Waiting for drone state...")

            # Receive state from edge
            drone_state = zmq_server.receive_state()

            if drone_state:
                print(
                    f"Received state: pos={np.round(drone_state.position, 2)}, "
                    f"vel={np.round(drone_state.velocity, 2)}"
                )

                # Plan optimal trajectory using SE(3) MPC
                start_time = time.time()
                trajectory = se3_mpc_planner.plan_trajectory(drone_state, goal_position)
                planning_time = time.time() - start_time

                print(f"SE(3) MPC planning completed in {planning_time*1000:.1f}ms")
                print(f"Generated trajectory: {len(trajectory.positions)} waypoints")

                # Send trajectory back to edge
                zmq_server.send_trajectory(trajectory)
                print("Trajectory sent to edge")

                # Performance logging
                if planning_count % 10 == 0 and planning_count > 0:
                    stats = se3_mpc_planner.get_performance_stats()
                    print(f"\nSE(3) MPC Performance Stats:")
                    print(f"  Average planning time: {stats['avg_time_ms']:.1f}ms")
                    print(f"  Max planning time: {stats['max_time_ms']:.1f}ms")
                    print(f"  Total plans: {stats['plan_count']}")
                    print(f"  Recent average: {stats['recent_avg_ms']:.1f}ms")

                # Check if goal reached
                goal_distance = np.linalg.norm(drone_state.position - goal_position)
                if goal_distance < 1.0:
                    print(f"\n🎯 Goal reached! Distance: {goal_distance:.2f}m")
                    # Could update goal here for multi-waypoint missions

                planning_count += 1

            else:
                print("Failed to receive state from edge")
                # Create fallback hover trajectory
                fallback_traj = Trajectory(
                    timestamps=np.array([time.time()]),
                    positions=np.array([[0, 0, 1]]),
                    velocities=np.array([[0, 0, 0]]),
                    accelerations=np.array([[0, 0, 0]]),
                )
                zmq_server.send_trajectory(fallback_traj)
                print("Sent fallback hover trajectory")

    except KeyboardInterrupt:
        print("\nShutting down cloud planner.")

    finally:
        # Final performance summary
        if planning_count > 0:
            stats = se3_mpc_planner.get_performance_stats()
            print(f"\nFinal SE(3) MPC Performance Summary:")
            print(f"  Total planning cycles: {planning_count}")
            print(f"  Average planning time: {stats['avg_time_ms']:.1f}ms")
            print(f"  Max planning time: {stats['max_time_ms']:.1f}ms")
            if stats["avg_time_ms"]:
                print(
                    f"  Planning frequency achieved: {1000/stats['avg_time_ms']:.1f}Hz"
                )

        zmq_server.close()
        print("Cloud planner shutdown complete.")


if __name__ == "__main__":
    main_improved()
