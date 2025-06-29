import time
import asyncio
import numpy as np
from communication.zmq_server import ZmqServer
from planning.cloud_planner import CloudPlanner
from common.types import Trajectory # For creating a dummy trajectory on error

async def main():
    """
    Main loop for the cloud node.
    - Initializes the planner and communication server.
    - Continuously waits for drone state, plans a trajectory, and sends it back.
    """
    cloud_planner = CloudPlanner()
    zmq_server = ZmqServer()

    # Define a goal position for the drone
    goal_position = np.array([10.0, 10.0, 5.0])

    try:
        while True:
            print("\nWaiting for drone state...")
            drone_state = zmq_server.receive_state()

            if drone_state:
                print(f"Received state from drone: {drone_state}")

                # Plan a new trajectory
                trajectory = cloud_planner.plan_trajectory(drone_state, goal_position)

                # Send the trajectory back to the drone
                print(f"Sending trajectory: {trajectory.positions.shape[0]} waypoints")
                zmq_server.send_trajectory(trajectory)
            else:
                print("Failed to receive state, sending a fallback trajectory.")
                # Create a simple hover trajectory if state receive fails
                fallback_traj = Trajectory(timestamps=np.array([time.time()]), positions=np.array([[0,0,1]]))
                zmq_server.send_trajectory(fallback_traj)

    except KeyboardInterrupt:
        print("Shutting down cloud server.")
    finally:
        zmq_server.close()

if __name__ == "__main__":
    asyncio.run(main()) 