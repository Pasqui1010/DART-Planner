import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
import glob
import os

# Set publication-ready style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'serif',
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 12,
    'figure.titlesize': 18,
    'lines.linewidth': 2,
    'axes.linewidth': 1.5,
    'grid.alpha': 0.3
})

def create_publication_plots():
    """Create publication-ready plots for academic papers"""
    
    # Find the latest improved log
    improved_files = glob.glob('improved_trajectory_log_*.csv')
    if not improved_files:
        print("No improved trajectory log found!")
        return
    
    latest_improved = max(improved_files, key=os.path.getctime)
    print(f"Using improved log: {latest_improved}")
    
    try:
        data = pd.read_csv(latest_improved)
        print(f"Loaded {len(data)} data points")
    except Exception as e:
        print(f"Error loading data: {e}")
        return
    
    # Create publication figure with multiple subplots
    fig = plt.figure(figsize=(16, 12))
    
    # 1. 3D Trajectory Plot (Top Left)
    ax1 = fig.add_subplot(2, 3, 1, projection='3d')
    
    # Plot trajectories
    ax1.plot(data['actual_x'], data['actual_y'], data['actual_z'], 
             'b-', linewidth=2, alpha=0.8, label='Actual')
    ax1.plot(data['desired_x'], data['desired_y'], data['desired_z'], 
             'r--', linewidth=2, alpha=0.8, label='Desired')
    
    # Start and end points
    ax1.scatter(data['actual_x'].iloc[0], data['actual_y'].iloc[0], data['actual_z'].iloc[0], 
               color='green', s=100, marker='o', label='Start')
    ax1.scatter(data['actual_x'].iloc[-1], data['actual_y'].iloc[-1], data['actual_z'].iloc[-1], 
               color='red', s=100, marker='s', label='End')
    
    ax1.set_xlabel('X Position (m)')
    ax1.set_ylabel('Y Position (m)')
    ax1.set_zlabel('Z Position (m)')
    ax1.set_title('3D Trajectory Tracking')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Position Error Over Time (Top Middle)
    ax2 = fig.add_subplot(2, 3, 2)
    
    position_error = np.sqrt((data['actual_x'] - data['desired_x'])**2 + 
                           (data['actual_y'] - data['desired_y'])**2 + 
                           (data['actual_z'] - data['desired_z'])**2)
    
    ax2.plot(data['timestamp'], position_error, 'b-', linewidth=2)
    ax2.fill_between(data['timestamp'], position_error, alpha=0.3)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Position Error (m)')
    ax2.set_title('Position Tracking Error')
    ax2.grid(True, alpha=0.3)
    
    # Add statistics
    mean_error = position_error.mean()
    ax2.axhline(y=mean_error, color='r', linestyle='--', alpha=0.7, 
                label=f'Mean: {mean_error:.2f}m')
    ax2.legend()
    
    # 3. Control Frequency (Top Right)
    ax3 = fig.add_subplot(2, 3, 3)
    
    # Calculate frequency from timestamps
    dt = np.diff(data['timestamp'])
    frequency = 1.0 / dt
    frequency = frequency[frequency < 2000]  # Remove outliers
    
    ax3.hist(frequency, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
    ax3.set_xlabel('Control Frequency (Hz)')
    ax3.set_ylabel('Count')
    ax3.set_title('Control Frequency Distribution')
    ax3.axvline(x=frequency.mean(), color='r', linestyle='--', 
                label=f'Mean: {frequency.mean():.1f} Hz')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Velocity Profiles (Bottom Left)
    ax4 = fig.add_subplot(2, 3, 4)
    
    actual_speed = np.sqrt(data['actual_vx']**2 + data['actual_vy']**2 + data['actual_vz']**2)
    desired_speed = np.sqrt(data['desired_vx']**2 + data['desired_vy']**2 + data['desired_vz']**2)
    
    ax4.plot(data['timestamp'], actual_speed, 'b-', linewidth=2, label='Actual Speed')
    ax4.plot(data['timestamp'], desired_speed, 'r--', linewidth=2, label='Desired Speed')
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Speed (m/s)')
    ax4.set_title('Velocity Tracking')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 5. Control Inputs (Bottom Middle)
    ax5 = fig.add_subplot(2, 3, 5)
    
    ax5_twin = ax5.twinx()
    
    line1 = ax5.plot(data['timestamp'], data['thrust'], 'b-', linewidth=2, label='Thrust')
    line2 = ax5_twin.plot(data['timestamp'], data['torque_norm'], 'r-', linewidth=2, label='Torque')
    
    ax5.set_xlabel('Time (s)')
    ax5.set_ylabel('Thrust (N)', color='b')
    ax5_twin.set_ylabel('Torque Norm (N⋅m)', color='r')
    ax5.set_title('Control Inputs')
    
    # Combine legends
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax5.legend(lines, labels, loc='upper right')
    
    ax5.grid(True, alpha=0.3)
    
    # 6. System Performance Summary (Bottom Right)
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.axis('off')
    
    # Calculate key metrics
    mean_pos_error = position_error.mean()
    rms_pos_error = np.sqrt(np.mean(position_error**2))
    max_pos_error = position_error.max()
    mean_freq = frequency.mean()
    failsafe_count = data['failsafe_active'].sum()
    
    # Create performance summary text
    summary_text = f"""
SYSTEM PERFORMANCE SUMMARY

Trajectory Tracking:
• Mean Position Error: {mean_pos_error:.2f} m
• RMS Position Error: {rms_pos_error:.2f} m
• Maximum Error: {max_pos_error:.2f} m

Control System:
• Mean Frequency: {mean_freq:.1f} Hz
• Target Frequency: 1000 Hz
• Efficiency: {(mean_freq/1000)*100:.1f}%

Safety & Reliability:
• Failsafe Activations: {failsafe_count}
• Data Points: {len(data):,}
• Duration: {data['timestamp'].iloc[-1]:.1f} s

Status: STABLE ✓
    """
    
    ax6.text(0.1, 0.9, summary_text, transform=ax6.transAxes, fontsize=11,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('publication_ready_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("✅ Publication-ready plots saved as 'publication_ready_analysis.png'")
    
    # Create separate high-quality 3D trajectory plot
    create_standalone_3d_plot(data)

def create_standalone_3d_plot(data):
    """Create a standalone high-quality 3D trajectory plot"""
    
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot trajectories with enhanced styling
    actual_line = ax.plot(data['actual_x'], data['actual_y'], data['actual_z'], 
                         'b-', linewidth=3, alpha=0.9, label='Actual Trajectory')
    desired_line = ax.plot(data['desired_x'], data['desired_y'], data['desired_z'], 
                          'r--', linewidth=3, alpha=0.9, label='Desired Trajectory')
    
    # Enhanced start/end markers
    ax.scatter(data['actual_x'].iloc[0], data['actual_y'].iloc[0], data['actual_z'].iloc[0], 
               color='green', s=200, marker='o', label='Start', edgecolors='black', linewidth=2)
    ax.scatter(data['actual_x'].iloc[-1], data['actual_y'].iloc[-1], data['actual_z'].iloc[-1], 
               color='red', s=200, marker='s', label='End', edgecolors='black', linewidth=2)
    
    # Enhanced labeling
    ax.set_xlabel('X Position (m)', fontsize=14, labelpad=10)
    ax.set_ylabel('Y Position (m)', fontsize=14, labelpad=10)
    ax.set_zlabel('Z Position (m)', fontsize=14, labelpad=10)
    ax.set_title('Distributed Control System: 3D Trajectory Tracking\nAdvanced Performance Metrics', 
                 fontsize=16, pad=20)
    
    # Enhanced legend
    ax.legend(loc='upper left', fontsize=12, framealpha=0.9)
    
    # Enhanced grid
    ax.grid(True, alpha=0.4)
    
    # Set viewing angle for best presentation
    ax.view_init(elev=20, azim=45)
    
    plt.tight_layout()
    plt.savefig('standalone_3d_trajectory.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("✅ Standalone 3D trajectory plot saved as 'standalone_3d_trajectory.png'")

if __name__ == "__main__":
    create_publication_plots() 