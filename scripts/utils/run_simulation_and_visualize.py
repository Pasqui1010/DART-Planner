import threading
import time
import glob
import os
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from src.cloud.main_improved import main_improved as cloud_main
from src.edge.main_improved import main_improved as edge_main

def run_simulation_and_visualize():
    """
    Orchestrates the full simulation and visualization pipeline:
    1. Starts the cloud server in a background thread.
    2. Runs the edge client for a fixed duration to generate a log.
    3. Finds the latest log file.
    4. Generates and displays the trajectory plot.
    """
    print("--- Starting Full System Test & Visualization ---")

    # 1. Start cloud server in the background
    print("Starting cloud server in background...")
    server_thread = threading.Thread(target=cloud_main, daemon=True)
    server_thread.start()
    time.sleep(2) # Give server time to initialize

    # 2. Run edge simulation to generate the log
    print("Running edge simulation for 20 seconds...")
    edge_main(duration=20.0)

    # 3. Find the latest log file
    try:
        list_of_files = glob.glob('trajectory_log_*.csv')
        if not list_of_files:
            print("Error: No log files found. Did the edge node run correctly?")
            return
        latest_file = max(list_of_files, key=os.path.getctime)
        print(f"Found log file: {latest_file}")
    except Exception as e:
        print(f"Error finding log file: {e}")
        return

    # 4. Visualize the results
    print("Generating trajectory visualization...")
    try:
        data = pd.read_csv(latest_file)
        
        # Create 3D plot
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot actual trajectory
        ax.plot(data['actual_x'], data['actual_y'], data['actual_z'], 
                label='Actual Trajectory', color='b', linewidth=2)
        
        # Plot target/desired trajectory (check which column exists)
        if 'target_x' in data.columns:
            ax.plot(data['target_x'], data['target_y'], data['target_z'], 
                    label='Target Trajectory', color='r', linestyle='--', linewidth=2)
        elif 'desired_x' in data.columns:
            ax.plot(data['desired_x'], data['desired_y'], data['desired_z'], 
                    label='Desired Trajectory', color='r', linestyle='--', linewidth=2)
        
        # Mark start and end
        ax.scatter(data['actual_x'].iloc[0], data['actual_y'].iloc[0], data['actual_z'].iloc[0], 
                   color='green', s=100, label='Start')
        ax.scatter(data['actual_x'].iloc[-1], data['actual_y'].iloc[-1], data['actual_z'].iloc[-1], 
                   color='purple', s=150, label='End')
        
        ax.set_xlabel('X Position (m)')
        ax.set_ylabel('Y Position (m)')
        ax.set_zlabel('Z Position (m)')
        ax.set_title('Drone Trajectory - System Test Results')
        ax.legend()
        ax.grid(True)
        
        plt.show()
        print(f"Visualization complete for {len(data)} data points")
        
    except Exception as e:
        print(f"Error creating visualization: {e}")
    
    print("--- Test & Visualization Complete ---")

if __name__ == "__main__":
    run_simulation_and_visualize() 