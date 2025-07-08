import csv
from dart_planner.common.di_container_v2 import get_container
import time
from typing import Optional

import numpy as np
import asyncio

from ..common.types import DroneState

from dart_planner.control.onboard_controller import OnboardController
from dart_planner.communication.zmq_client import ZmqClient
from dart_planner.utils.drone_simulator import DroneSimulator

import logging
from dart_planner.common.logging_config import get_logger
logger = get_logger(__name__)


def main(duration: Optional[float] = 30.0) -> None:
    """
    Main loop for the edge node (drone).
    - Initializes components using a centralized configuration.
    - Runs a closed-loop simulation for a given duration, communicates with the cloud,
      and logs data for analysis.
    """
    # Initialization using the imported configuration
    onboard_controller = OnboardController()
    from dart_planner.communication.zmq_client import ZmqClient
    zmq_client = get_container().resolve(ZmqClient)
    drone_simulator = DroneSimulator()
    dt = 0.01  # 100 Hz loop
    current_state = DroneState(timestamp=time.time())
    onboard_controller.reset()

    # Logging
    log_data = []

    # Communication
    comm_counter = 0
    comm_frequency = 100  # Communicate at 1Hz (100Hz loop / 100)
    trajectory = None

    try:
        logger.info(
            f"Edge node starting. Running for {duration} seconds. Press Ctrl+C to stop early."
        )
        sim_start_time = time.time()
        while True:
            # Check for exit condition
            if duration and (time.time() - sim_start_time) > duration:
                logger.info("Simulation duration reached.")
                break

            loop_start_time = time.time()

            if comm_counter % comm_frequency == 0:
                logger.info(f"\n--- Timestep {comm_counter}: Communicating with Cloud ---")
                # Send current state and request trajectory
                request_data = {
                    "type": "state_update",
                    "state": current_state,
                    "timestamp": current_state.timestamp
                }
                response = zmq_client.send_request(request_data)
                if response and "trajectory" in response:
                    trajectory = response["trajectory"]
                    logger.info(
                        f"Received new trajectory. Target center: {trajectory.positions[0]}"
                    )
                else:
                    logger.warning(
                        "Communication failed. Continuing with old trajectory or fallback."
                    )

            # Only compute control if we have a valid trajectory
            if trajectory is not None:
                control_command, target_pos = onboard_controller.compute_control_command(
                    current_state, trajectory
                )
            else:
                # Use fallback command if no trajectory
                control_command = onboard_controller.get_fallback_command(current_state)
                target_pos = current_state.position
            current_state = drone_simulator.step(current_state, control_command, dt)

            # Log data for analysis
            log_data.append(
                [current_state.timestamp, *current_state.position, *target_pos]
            )

            if comm_counter % 100 == 0:
                logger.info(
                    f"State @ {current_state.timestamp:.2f}: Pos={np.round(current_state.position, 2)}"
                )

            elapsed_time = time.time() - loop_start_time
            sleep_time = dt - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)

            comm_counter += 1

    except KeyboardInterrupt:
        logger.info("Shutting down edge client.")
    finally:
        # Save the log file
        log_filename = f"trajectory_log_{int(time.time())}.csv"
        with open(log_filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "actual_x",
                    "actual_y",
                    "actual_z",
                    "target_x",
                    "target_y",
                    "target_z",
                ]
            )
            writer.writerows(log_data)
        logger.info(f"Log data saved to {log_filename}")
        zmq_client.close()


if __name__ == "__main__":
    main()
