import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import argparse

def visualize_trajectory(log_file):
    """
    Reads a trajectory log file and plots the actual vs. target paths in 3D.

    Args:
        log_file (str): The path to the CSV log file.
    """
    # Read the data
    try:
        data = pd.read_csv(log_file)
    except FileNotFoundError:
        print(f"Error: Log file not found at {log_file}")
        return

    # Create the 3D plot
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot actual trajectory
    ax.plot(data['actual_x'], data['actual_y'], data['actual_z'], label='Actual Trajectory', color='b')
    
    # Plot target trajectory
    ax.plot(data['target_x'], data['target_y'], data['target_z'], label='Target Trajectory', color='r', linestyle='--')

    # Mark start and end points
    ax.scatter(data['actual_x'].iloc[0], data['actual_y'].iloc[0], data['actual_z'].iloc[0], color='green', s=100, label='Start')
    ax.scatter(data['actual_x'].iloc[-1], data['actual_y'].iloc[-1], data['actual_z'].iloc[-1], color='purple', s=100, label='End')

    # Formatting
    ax.set_xlabel('X Position (m)')
    ax.set_ylabel('Y Position (m)')
    ax.set_zlabel('Z Position (m)')
    ax.set_title('Drone Trajectory Tracking Performance')
    ax.legend()
    ax.grid(True)
    
    # Set aspect ratio to be equal
    max_range = max(data['actual_x'].max()-data['actual_x'].min(), 
                    data['actual_y'].max()-data['actual_y'].min(), 
                    data['actual_z'].max()-data['actual_z'].min())
    mid_x = (data['actual_x'].max()+data['actual_x'].min()) * 0.5
    mid_y = (data['actual_y'].max()+data['actual_y'].min()) * 0.5
    mid_z = (data['actual_z'].max()+data['actual_z'].min()) * 0.5
    ax.set_xlim(mid_x - max_range * 0.5, mid_x + max_range * 0.5)
    ax.set_ylim(mid_y - max_range * 0.5, mid_y + max_range * 0.5)
    ax.set_zlim(mid_z - max_range * 0.5, mid_z + max_range * 0.5)

    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize drone trajectory from a log file.")
    parser.add_argument("log_file", type=str, help="Path to the trajectory_log.csv file.")
    args = parser.parse_args()
    
    visualize_trajectory(args.log_file) 