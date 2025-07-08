import asyncio
import time
import logging
import numpy as np
import csv
from typing import Optional

from dart_planner.common.di_container_v2 import get_container
from dart_planner.common.timing_alignment import get_timing_manager, TimingConfig
from dart_planner.common.types import DroneState
from dart_planner.control.geometric_controller import GeometricController, GeometricControllerConfig
from dart_planner.control.trajectory_smoother import TrajectorySmoother
from dart_planner.communication.zmq_client import ZmqClient
from dart_planner.utils.drone_simulator import DroneSimulator
from dart_planner.common.logging_config import get_logger


async def main_improved(duration: Optional[float] = 30.0):
    """
    Improved edge node main loop implementing proper distributed architecture.

    This implementation follows the hybrid architecture principles:
    - High-frequency geometric control (1kHz) for attitude and thrust
    - Smooth trajectory following with proper interpolation
    - Robust communication handling with failsafes
    - Clean separation between planning (cloud) and control (edge)
    - Proper real-time timing using TimingManager
    """
    logger = get_logger(__name__)
    logger.info("=== Improved Distributed Edge Controller ===")

    # Initialize timing manager for real-time control
    from dart_planner.common.timing_alignment import TimingMode
    timing_config = TimingConfig(
        control_frequency=1000.0,  # 1kHz control loop
        planning_frequency=10.0,   # 10Hz communication
        mode=TimingMode.CONTROLLER_DRIVEN
    )
    timing_manager = get_timing_manager(timing_config)

    # Initialize components with proper configuration
    controller_config = GeometricControllerConfig(
        kp_pos=np.array([5.0, 5.0, 6.0]),  # Slightly higher Z gain
        kd_pos=np.array([3.0, 3.0, 4.0]),
        kp_att=np.array([8.0, 8.0, 4.0]),
        kd_att=np.array([2.5, 2.5, 1.0]),
        mass=1.0,
        gravity=9.81,
    )

    from dart_planner.control.geometric_controller import GeometricController
    from dart_planner.control.trajectory_smoother import TrajectorySmoother
    from dart_planner.communication.zmq_client import ZmqClient
    
    geometric_controller = get_container().resolve(GeometricController)
    trajectory_smoother = get_container().resolve(TrajectorySmoother)
    zmq_client = get_container().resolve(ZmqClient)
    drone_simulator = DroneSimulator()

    # Control loop timing from timing manager
    control_dt = timing_manager.control_dt  # 1kHz control loop
    comm_dt = 1.0 / timing_config.planning_frequency  # 10Hz communication with cloud

    # Initialize state
    current_state = DroneState(timestamp=time.time())
    geometric_controller.reset()

    # Logging for analysis
    log_data = []

    # Timing management
    last_comm_time = 0.0
    loop_count = 0

    try:
        logger.info(f"Starting improved edge controller for {duration}s")
        logger.info(f"Control frequency: {timing_config.control_frequency}Hz, Communication: {timing_config.planning_frequency}Hz")

        sim_start_time = time.time()

        while True:
            loop_start_time = time.time()
            current_time = loop_start_time
            current_state.timestamp = current_time

            # Check exit condition
            if duration and (current_time - sim_start_time) > duration:
                logger.info("Simulation duration reached.")
                break

            # === COMMUNICATION WITH CLOUD (10Hz) ===
            if current_time - last_comm_time >= comm_dt:
                logger.info(f"\n--- Communication Cycle {loop_count//100} ---")

                # Send state and receive trajectory from cloud
                request_data = {
                    "type": "state_update",
                    "state": current_state,
                    "timestamp": current_state.timestamp
                }
                response = zmq_client.send_request(request_data)
                new_trajectory = response.get("trajectory") if response else None

                if new_trajectory:
                    # Update trajectory smoother with new cloud trajectory
                    trajectory_smoother.update_trajectory(new_trajectory, current_state)
                    logger.info(
                        f"Received trajectory: {len(new_trajectory.positions)} waypoints"
                    )
                else:
                    logger.warning("Communication failed - using trajectory smoother failsafe")

                last_comm_time = current_time

                # Status logging
                smoother_status = trajectory_smoother.get_status()
                logger.info(f"Smoother status: {smoother_status}")

            # === HIGH-FREQUENCY CONTROL (1kHz) ===

            # Get desired state from trajectory smoother
            (
                desired_pos,
                desired_vel,
                desired_acc,
            ) = trajectory_smoother.get_desired_state(current_time, current_state)

            # Compute control command using geometric controller
            control_command = geometric_controller.compute_control(
                current_state=current_state,
                desired_pos=desired_pos,
                desired_vel=desired_vel,
                desired_acc=desired_acc,
                desired_yaw=0.0,  # Keep yaw at 0 for simplicity
                desired_yaw_rate=0.0,
            )

            # Simulate drone dynamics
            current_state = drone_simulator.step(
                current_state, control_command, control_dt
            )

            # === LOGGING ===
            log_data.append(
                [
                    current_state.timestamp,
                    *current_state.position,
                    *desired_pos,
                    *current_state.velocity,
                    *desired_vel,
                    control_command.thrust,
                    np.linalg.norm(control_command.torque),
                    geometric_controller.failsafe_active,
                ]
            )

            # Status updates every 100 cycles (0.1s)
            if loop_count % 100 == 0:
                pos_error = np.linalg.norm(current_state.position - desired_pos)
                vel_error = np.linalg.norm(current_state.velocity - desired_vel)
                logger.info(
                    f"State @ {current_time:.2f}s: "
                    f"Pos={np.round(current_state.position, 2)}, "
                    f"PosErr={pos_error:.3f}, VelErr={vel_error:.3f}"
                )

            # === TIMING CONTROL ===
            elapsed_time = time.time() - loop_start_time
            sleep_time = control_dt - elapsed_time

            if sleep_time > 0:
                # Use asyncio.sleep for non-blocking behavior
                await asyncio.sleep(sleep_time)
            elif elapsed_time > control_dt * 1.5:
                logger.warning(f"Warning: Control loop overrun: {elapsed_time*1000:.1f}ms")

            loop_count += 1

    except KeyboardInterrupt:
        logger.info("\nShutting down improved edge controller.")

    finally:
        # === SAVE RESULTS ===
        log_filename = f"improved_trajectory_log_{int(time.time())}.csv"
        with open(log_filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "actual_x",
                    "actual_y",
                    "actual_z",
                    "desired_x",
                    "desired_y",
                    "desired_z",
                    "actual_vx",
                    "actual_vy",
                    "actual_vz",
                    "desired_vx",
                    "desired_vy",
                    "desired_vz",
                    "thrust",
                    "torque_norm",
                    "failsafe_active",
                ]
            )
            writer.writerows(log_data)

        logger.info(f"Improved log data saved to {log_filename}")

        # Performance summary
        total_time = time.time() - sim_start_time
        actual_frequency = loop_count / total_time
        logger.info(f"\nPerformance Summary:")
        logger.info(f"Total runtime: {total_time:.2f}s")
        logger.info(f"Control loops: {loop_count}")
        logger.info(f"Actual frequency: {actual_frequency:.1f}Hz (target: {timing_config.control_frequency}Hz)")
        logger.info(
            f"Geometric controller failsafe activations: {sum(row[-1] for row in log_data)}"
        )

        # Cleanup
        zmq_client.close()


if __name__ == "__main__":
    asyncio.run(main_improved())
