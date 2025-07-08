#!/usr/bin/env python3
"""
Improved Edge Controller with Quartic Scheduler

This version uses the quartic cooperative real-time scheduler to replace
asyncio.sleep(dt) for hard real-time tasks like 400 Hz control loops.

Features:
- Quartic scheduler for precise timing
- Jitter analysis and performance monitoring
- Thread-safe state buffer integration
- Real-time control with deadline monitoring
"""

import asyncio
import csv
import time
import numpy as np
from typing import Optional
from pathlib import Path
import matplotlib.pyplot as plt

from dart_planner.common.config import get_config
from dart_planner.common.di_container_v2 import get_container
from dart_planner.common.types import DroneState
from dart_planner.common.logging_config import get_logger
from dart_planner.utils.drone_simulator import DroneSimulator
from dart_planner.common.quartic_scheduler import (
    QuarticScheduler, create_control_task, create_planning_task,
    quartic_scheduler_context
)
from dart_planner.common.real_time_config import TaskPriority


async def main_quartic_improved(duration: Optional[float] = 30.0):
    """
    Main function for improved edge controller with quartic scheduler.
    
    This version uses the quartic cooperative real-time scheduler to provide
    precise timing for hard real-time tasks like 400 Hz control loops.
    """
    logger = get_logger(__name__)

    # === CONFIGURATION ===
    config = get_config()
    timing_config = config.timing
    timing_manager = get_container().resolve("timing_manager")

    # Initialize components
    from dart_planner.control.geometric_controller import GeometricController
    from dart_planner.control.trajectory_smoother import TrajectorySmoother
    from dart_planner.communication.zmq_client import ZmqClient
    
    geometric_controller = get_container().resolve(GeometricController)
    trajectory_smoother = get_container().resolve(TrajectorySmoother)
    zmq_client = get_container().resolve(ZmqClient)
    drone_simulator = DroneSimulator()

    # Control loop timing
    control_frequency = timing_config.control_frequency  # 400 Hz
    planning_frequency = timing_config.planning_frequency  # 50 Hz

    # Initialize thread-safe state buffer
    from dart_planner.common.state_buffer import create_drone_state_buffer
    state_buffer = create_drone_state_buffer(buffer_size=10)
    
    # Initialize state
    current_state = DroneState(timestamp=time.time())
    state_buffer.update_state(current_state, "initialization")
    geometric_controller.reset()

    # Logging for analysis
    log_data = []
    sim_start_time = time.time()

    # === QUARTIC SCHEDULER SETUP ===
    logger.info(f"Starting quartic scheduler improved edge controller for {duration}s")
    logger.info(f"Control frequency: {control_frequency}Hz, Planning: {planning_frequency}Hz")

    async with quartic_scheduler_context(enable_monitoring=True, max_jitter_ms=1.0) as scheduler:
        
        # === CONTROL TASK (400 Hz) ===
        def control_step():
            """High-frequency control step."""
            nonlocal current_state, log_data
            
            current_time = time.time()
            current_state.timestamp = current_time

            # Get desired state from trajectory smoother
            (
                desired_pos,
                desired_vel,
                desired_acc,
            ) = trajectory_smoother.get_desired_state(current_time, current_state)

            # Convert numpy arrays to Quantity types for geometric controller
            from dart_planner.common.units import Q_
            desired_pos_q = Q_(desired_pos, 'm')
            desired_vel_q = Q_(desired_vel, 'm/s')
            desired_acc_q = Q_(desired_acc, 'm/s^2')

            # Compute control command using geometric controller
            control_command = geometric_controller.compute_control(
                current_state=current_state,
                desired_pos=desired_pos_q,
                desired_vel=desired_vel_q,
                desired_acc=desired_acc_q,
                desired_yaw=0.0,  # Keep yaw at 0 for simplicity
                desired_yaw_rate=0.0,
            )

            # Simulate drone dynamics
            control_dt = 1.0 / control_frequency
            current_state = drone_simulator.step(
                current_state, control_command, control_dt
            )
            
            # Update thread-safe state buffer
            state_buffer.update_state(current_state, "control")

            # Logging
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

            # Status updates every 400 cycles (1 second at 400Hz)
            if len(log_data) % 400 == 0:
                pos_error = np.linalg.norm(current_state.position - desired_pos)
                vel_error = np.linalg.norm(current_state.velocity - desired_vel)
                logger.info(
                    f"Control @ {current_time:.2f}s: "
                    f"Pos={np.round(current_state.position, 2)}, "
                    f"PosErr={pos_error:.3f}, VelErr={vel_error:.3f}"
                )

        # === PLANNING TASK (50 Hz) ===
        def planning_step():
            """Medium-frequency planning step."""
            nonlocal current_state
            
            current_time = time.time()
            
            logger.info(f"\n--- Planning Cycle @ {current_time:.2f}s ---")

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

            # Status logging
            smoother_status = trajectory_smoother.get_status()
            logger.info(f"Smoother status: {smoother_status}")

        # Create and add tasks to scheduler
        control_task = create_control_task(
            control_step, 
            frequency_hz=control_frequency, 
            name="control_loop"
        )
        
        planning_task = create_planning_task(
            planning_step,
            frequency_hz=planning_frequency,
            name="planning_loop"
        )
        
        scheduler.add_task(control_task)
        scheduler.add_task(planning_task)
        
        # Run for specified duration
        try:
            await asyncio.sleep(duration)
        except KeyboardInterrupt:
            logger.info("\nShutting down quartic scheduler improved edge controller.")

    # === SAVE RESULTS ===
    log_filename = f"quartic_improved_trajectory_log_{int(time.time())}.csv"
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

    logger.info(f"Quartic improved log data saved to {log_filename}")

    # === PERFORMANCE SUMMARY ===
    total_time = time.time() - sim_start_time
    logger.info(f"\nQuartic Scheduler Performance Summary:")
    logger.info(f"Total runtime: {total_time:.2f}s")
    logger.info(f"Control loops: {len(log_data)}")
    logger.info(f"Actual frequency: {len(log_data)/total_time:.1f}Hz (target: {control_frequency}Hz)")
    logger.info(
        f"Geometric controller failsafe activations: {sum(row[-1] for row in log_data)}"
    )

    # Generate jitter analysis
    results_dir = Path("results/quartic_improved")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Note: We can't access the scheduler here since it's closed, but we can
    # analyze the log data for timing patterns
    if len(log_data) > 1:
        timestamps = [row[0] for row in log_data]
        intervals = np.diff(timestamps)
        expected_interval = 1.0 / control_frequency
        
        jitter_ms = (intervals - expected_interval) * 1000.0
        
        logger.info(f"\nTiming Analysis:")
        logger.info(f"Mean interval: {np.mean(intervals)*1000:.3f}ms (expected: {expected_interval*1000:.3f}ms)")
        logger.info(f"Mean jitter: {np.mean(jitter_ms):.3f}ms")
        logger.info(f"Max jitter: {np.max(jitter_ms):.3f}ms")
        logger.info(f"Min jitter: {np.min(jitter_ms):.3f}ms")
        logger.info(f"Std jitter: {np.std(jitter_ms):.3f}ms")
        
        # Create jitter histogram
        plt.figure(figsize=(10, 6))
        plt.hist(jitter_ms, bins=50, alpha=0.7, edgecolor='black')
        plt.axvline(np.mean(jitter_ms), color='red', linestyle='--', 
                   label=f'Mean: {np.mean(jitter_ms):.3f}ms')
        plt.xlabel('Jitter (ms)')
        plt.ylabel('Frequency')
        plt.title('Control Loop Jitter Distribution')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(str(results_dir / "control_jitter_histogram.png"), dpi=300, bbox_inches='tight')
        logger.info(f"Jitter histogram saved to: {results_dir / 'control_jitter_histogram.png'}")

    # Cleanup
    zmq_client.close()


if __name__ == "__main__":
    asyncio.run(main_quartic_improved()) 