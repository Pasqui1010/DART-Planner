import time
import numpy as np
from src.communication.zmq_server import ZmqServer
from src.planning.dial_mpc_planner import DIALMPCPlanner, DIALMPCConfig
from src.common.types import Trajectory

def main_improved():
    """
    Improved cloud node main loop implementing proper DIAL-MPC planning.
    
    This implementation:
    - Uses DIAL-MPC for optimal trajectory generation
    - Runs at appropriate cloud frequency (~10Hz)
    - Generates smooth, dynamically feasible trajectories
    - Includes proper error handling and fallbacks
    """
    print("=== Improved Distributed Cloud Planner ===")
    
    # Initialize DIAL-MPC planner with appropriate configuration
    planner_config = DIALMPCConfig(
        prediction_horizon=20,  # 2 second horizon at 100ms steps
        dt=0.1,  # 100ms planning resolution
        max_velocity=8.0,
        max_acceleration=4.0,
        max_jerk=8.0,
        position_weight=10.0,
        velocity_weight=1.0,
        acceleration_weight=0.1,
        jerk_weight=0.01,
        smoothness_weight=1.0
    )
    
    dial_mpc_planner = DIALMPCPlanner(planner_config)
    zmq_server = ZmqServer()
    
    # Define mission goal
    goal_position = np.array([10.0, 10.0, 5.0])
    print(f"Mission goal: {goal_position}")
    
    # Add some example obstacles for testing
    dial_mpc_planner.add_obstacle(np.array([5.0, 5.0, 2.5]), 1.0)
    dial_mpc_planner.add_obstacle(np.array([7.5, 7.5, 3.0]), 0.8)
    
    planning_count = 0
    
    try:
        print("Cloud planner ready. Waiting for edge connections...")
        
        while True:
            print(f"\n--- Planning Cycle {planning_count} ---")
            print("Waiting for drone state...")
            
            # Receive state from edge
            drone_state = zmq_server.receive_state()
            
            if drone_state:
                print(f"Received state: pos={np.round(drone_state.position, 2)}, "
                      f"vel={np.round(drone_state.velocity, 2)}")
                
                # Plan optimal trajectory using DIAL-MPC
                start_time = time.time()
                trajectory = dial_mpc_planner.plan_trajectory(drone_state, goal_position)
                planning_time = time.time() - start_time
                
                print(f"DIAL-MPC planning completed in {planning_time*1000:.1f}ms")
                print(f"Generated trajectory: {len(trajectory.positions)} waypoints")
                
                # Send trajectory back to edge
                zmq_server.send_trajectory(trajectory)
                print("Trajectory sent to edge")
                
                # Performance logging
                if planning_count % 10 == 0 and planning_count > 0:
                    stats = dial_mpc_planner.get_planning_stats()
                    print(f"\nDIAL-MPC Performance Stats:")
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
                    accelerations=np.array([[0, 0, 0]])
                )
                zmq_server.send_trajectory(fallback_traj)
                print("Sent fallback hover trajectory")
    
    except KeyboardInterrupt:
        print("\nShutting down cloud planner.")
    
    finally:
        # Final performance summary
        if planning_count > 0:
            stats = dial_mpc_planner.get_planning_stats()
            print(f"\nFinal DIAL-MPC Performance Summary:")
            print(f"  Total planning cycles: {planning_count}")
            print(f"  Average planning time: {stats['avg_time_ms']:.1f}ms")
            print(f"  Max planning time: {stats['max_time_ms']:.1f}ms")
            print(f"  Planning frequency achieved: {1000/stats['avg_time_ms']:.1f}Hz")
        
        zmq_server.close()
        print("Cloud planner shutdown complete.")

if __name__ == "__main__":
    main_improved() 