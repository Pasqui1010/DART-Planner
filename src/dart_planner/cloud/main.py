import asyncio
from dart_planner.common.di_container_v2 import get_container
import time

import numpy as np

from dart_planner.common.types import Trajectory  # For creating a dummy trajectory on error
from dart_planner.communication.zmq_server import ZmqServer
from dart_planner.planning.cloud_planner import CloudPlanner

import logging
from dart_planner.common.logging_config import get_logger
logger = get_logger(__name__)


async def main() -> None:
    """
    Main loop for the cloud node.
    - Initializes the planner and communication server.
    - Uses handler-based approach to process requests.
    """
    cloud_planner = CloudPlanner()
    from dart_planner.communication.zmq_server import ZmqServer
    zmq_server = get_container().resolve(ZmqServer)

    # Define a goal position for the drone
    goal_position = np.array([10.0, 10.0, 5.0])

    def handle_state_update(data: dict) -> dict:
        """Handle state update requests from the drone."""
        try:
            drone_state = data.get("state")
            if drone_state:
                logger.info(f"Received state from drone: {drone_state}")
                
                # Plan a new trajectory
                trajectory = cloud_planner.plan_trajectory(drone_state, goal_position)
                
                logger.info(f"Planned trajectory: {trajectory.positions.shape[0]} waypoints")
                return {"trajectory": trajectory}
            else:
                logger.warning("No state received, sending fallback trajectory.")
                # Create a simple hover trajectory if state receive fails
                fallback_traj = Trajectory(
                    timestamps=np.array([time.time()]), positions=np.array([[0, 0, 1]])
                )
                return {"trajectory": fallback_traj}
        except Exception as e:
            logger.error(f"Error handling state update: {e}")
            # Return fallback trajectory on error
            fallback_traj = Trajectory(
                timestamps=np.array([time.time()]), positions=np.array([[0, 0, 1]])
            )
            return {"trajectory": fallback_traj}

    # Add the handler to the server
    zmq_server.add_handler("state_update", handle_state_update)
    
    try:
        logger.info("Starting ZMQ server...")
        zmq_server.start()
        logger.info("Server running. Press Ctrl+C to stop.")
        
        # Keep the server running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down cloud server.")
    finally:
        zmq_server.stop()


if __name__ == "__main__":
    asyncio.run(main())
