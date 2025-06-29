import time
from typing import Optional

from communication.zmq_client import ZmqClient
from control.onboard_controller import OnboardController
from common.types import DroneState
from utils.drone_simulator import DroneSimulator
from control.control_config import default_control_config


def main(duration: Optional[float] = 30.0):
    """
    Main loop for the edge node (drone).
    - Initializes components using a centralized configuration.
    - Runs a closed-loop simulation for a given duration, communicates with the cloud,
      and logs data for analysis.
    """
    # Initialization using the imported configuration
    onboard_controller = OnboardController(config=default_control_config)
    zmq_client = ZmqClient(host="localhost")
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
        print(
            f"Edge node starting. Running for {duration} seconds. Press Ctrl+C to stop early."
        )
        sim_start_time = time.time()
        while True:
            # Check for exit condition
            if duration and (time.time() - sim_start_time) > duration:
                print("Simulation duration reached.")
                break

            loop_start_time = time.time()

            if comm_counter % comm_frequency == 0:
                print(f"\n--- Timestep {comm_counter}: Communicating with Cloud ---")
                new_trajectory = zmq_client.send_state_and_receive_trajectory(
                    current_state
                )
                if new_trajectory:
                    trajectory = new_trajectory
                    print(
                        f"Received new trajectory. Target center: {trajectory.positions[0]}"
                    )
                else:
                    print(
                        "Communication failed. Continuing with old trajectory or fallback."
                    )

            control_command, target_pos = onboard_controller.compute_control_command(
                current_state, trajectory
            )
            current_state = drone_simulator.step(current_state, control_command, dt)

            # Log data for analysis
            log_data.append(
                [current_state.timestamp, *current_state.position, *target_pos]
            )

            if comm_counter % 100 == 0:
                print(
                    f"State @ {current_state.timestamp:.2f}: Pos={np.round(current_state.position, 2)}"
                )

            elapsed_time = time.time() - loop_start_time
            sleep_time = dt - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)

            comm_counter += 1

    except KeyboardInterrupt:
        print("Shutting down edge client.")
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
        print(f"Log data saved to {log_filename}")
        zmq_client.close()


if __name__ == "__main__":
    main()
