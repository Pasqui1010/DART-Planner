import time
import numpy as np
import csv
from typing import Optional
from src.communication.zmq_client import ZmqClient
from src.control.geometric_controller import GeometricController, GeometricControllerConfig
from src.control.trajectory_smoother import TrajectorySmoother
from src.common.types import DroneState
from src.utils.drone_simulator import DroneSimulator

def main_improved(duration: Optional[float] = 30.0):
    """
    Improved edge node main loop implementing proper distributed architecture.
    
    This implementation follows the hybrid architecture principles:
    - High-frequency geometric control (1kHz) for attitude and thrust
    - Smooth trajectory following with proper interpolation
    - Robust communication handling with failsafes
    - Clean separation between planning (cloud) and control (edge)
    """
    print("=== Improved Distributed Edge Controller ===")
    
    # Initialize components with proper configuration
    controller_config = GeometricControllerConfig(
        kp_pos=np.array([5.0, 5.0, 6.0]),  # Slightly higher Z gain
        kd_pos=np.array([3.0, 3.0, 4.0]),
        kp_att=np.array([8.0, 8.0, 4.0]),
        kd_att=np.array([2.5, 2.5, 1.0]),
        mass=1.0,
        gravity=9.81
    )
    
    geometric_controller = GeometricController(controller_config)
    trajectory_smoother = TrajectorySmoother(
        transition_time=0.5,  # 500ms smooth transitions
        max_velocity=8.0,
        max_acceleration=4.0
    )
    zmq_client = ZmqClient(host="localhost")
    drone_simulator = DroneSimulator()
    
    # Control loop timing
    control_dt = 0.001  # 1kHz control loop
    comm_dt = 0.1       # 10Hz communication with cloud
    
    # Initialize state
    current_state = DroneState(timestamp=time.time())
    geometric_controller.reset()
    
    # Logging for analysis
    log_data = []
    
    # Timing management
    last_comm_time = 0.0
    loop_count = 0
    
    try:
        print(f"Starting improved edge controller for {duration}s")
        print("Control frequency: 1000Hz, Communication: 10Hz")
        
        sim_start_time = time.time()
        
        while True:
            loop_start_time = time.time()
            current_time = loop_start_time
            current_state.timestamp = current_time
            
            # Check exit condition
            if duration and (current_time - sim_start_time) > duration:
                print("Simulation duration reached.")
                break
            
            # === COMMUNICATION WITH CLOUD (10Hz) ===
            if current_time - last_comm_time >= comm_dt:
                print(f"\n--- Communication Cycle {loop_count//100} ---")
                
                # Send state and receive trajectory from cloud
                new_trajectory = zmq_client.send_state_and_receive_trajectory(current_state)
                
                if new_trajectory:
                    # Update trajectory smoother with new cloud trajectory
                    trajectory_smoother.update_trajectory(new_trajectory, current_state)
                    print(f"Received trajectory: {len(new_trajectory.positions)} waypoints")
                else:
                    print("Communication failed - using trajectory smoother failsafe")
                
                last_comm_time = current_time
                
                # Status logging
                smoother_status = trajectory_smoother.get_status()
                print(f"Smoother status: {smoother_status}")
            
            # === HIGH-FREQUENCY CONTROL (1kHz) ===
            
            # Get desired state from trajectory smoother
            desired_pos, desired_vel, desired_acc = trajectory_smoother.get_desired_state(
                current_time, current_state)
            
            # Compute control command using geometric controller
            control_command = geometric_controller.compute_control(
                current_state=current_state,
                desired_pos=desired_pos,
                desired_vel=desired_vel,
                desired_acc=desired_acc,
                desired_yaw=0.0,  # Keep yaw at 0 for simplicity
                desired_yaw_rate=0.0
            )
            
            # Simulate drone dynamics
            current_state = drone_simulator.step(current_state, control_command, control_dt)
            
            # === LOGGING ===
            log_data.append([
                current_state.timestamp,
                *current_state.position,
                *desired_pos,
                *current_state.velocity,
                *desired_vel,
                control_command.thrust,
                np.linalg.norm(control_command.torque),
                geometric_controller.failsafe_active
            ])
            
            # Status updates every 100 cycles (0.1s)
            if loop_count % 100 == 0:
                pos_error = np.linalg.norm(current_state.position - desired_pos)
                vel_error = np.linalg.norm(current_state.velocity - desired_vel)
                print(f"State @ {current_time:.2f}s: "
                      f"Pos={np.round(current_state.position, 2)}, "
                      f"PosErr={pos_error:.3f}, VelErr={vel_error:.3f}")
            
            # === TIMING CONTROL ===
            elapsed_time = time.time() - loop_start_time
            sleep_time = control_dt - elapsed_time
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif elapsed_time > control_dt * 1.5:
                print(f"Warning: Control loop overrun: {elapsed_time*1000:.1f}ms")
            
            loop_count += 1
    
    except KeyboardInterrupt:
        print("\nShutting down improved edge controller.")
    
    finally:
        # === SAVE RESULTS ===
        log_filename = f"improved_trajectory_log_{int(time.time())}.csv"
        with open(log_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", 
                "actual_x", "actual_y", "actual_z",
                "desired_x", "desired_y", "desired_z",
                "actual_vx", "actual_vy", "actual_vz",
                "desired_vx", "desired_vy", "desired_vz",
                "thrust", "torque_norm", "failsafe_active"
            ])
            writer.writerows(log_data)
        
        print(f"Improved log data saved to {log_filename}")
        
        # Performance summary
        total_time = time.time() - sim_start_time
        actual_frequency = loop_count / total_time
        print(f"\nPerformance Summary:")
        print(f"Total runtime: {total_time:.2f}s")
        print(f"Control loops: {loop_count}")
        print(f"Actual frequency: {actual_frequency:.1f}Hz (target: 1000Hz)")
        print(f"Geometric controller failsafe activations: {sum(row[-1] for row in log_data)}")
        
        # Cleanup
        zmq_client.close()

if __name__ == "__main__":
    main_improved() 