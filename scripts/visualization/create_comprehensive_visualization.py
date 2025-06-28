import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import glob
import os

def create_comprehensive_visualization(improved_log_file, original_log_files=None):
    """
    Create comprehensive visualizations showing system improvements
    """
    # Read improved data
    print(f"Reading improved log: {improved_log_file}")
    try:
        improved_data = pd.read_csv(improved_log_file)
    except FileNotFoundError:
        print(f"Error: Improved log file not found: {improved_log_file}")
        return
    
    # Check which format we have
    has_desired = 'desired_x' in improved_data.columns
    has_target = 'target_x' in improved_data.columns
    has_velocity = 'actual_vx' in improved_data.columns
    has_control = 'thrust' in improved_data.columns
    
    if has_desired:
        target_x, target_y, target_z = 'desired_x', 'desired_y', 'desired_z'
    elif has_target:
        target_x, target_y, target_z = 'target_x', 'target_y', 'target_z'
    else:
        print("Error: No target/desired position columns found")
        return
    
    print(f"Log format: {'Enhanced' if has_velocity else 'Basic'} - Columns: {list(improved_data.columns)}")
    
    # Create figure with multiple subplots - adjust layout based on available data
    rows, cols = (3, 3) if has_velocity and has_control else (2, 3)
    fig = plt.figure(figsize=(24, 8*rows))
    
    # 1. 3D Trajectory Plot
    ax1 = fig.add_subplot(rows, cols, 1, projection='3d')
    ax1.plot(improved_data['actual_x'], improved_data['actual_y'], improved_data['actual_z'], 
             label='Actual Trajectory', color='blue', linewidth=2)
    ax1.plot(improved_data[target_x], improved_data[target_y], improved_data[target_z], 
             label='Target/Desired Trajectory', color='red', linestyle='--', linewidth=2)
    
    # Mark start and end points
    ax1.scatter([improved_data['actual_x'].iloc[0]], [improved_data['actual_y'].iloc[0]], 
               [improved_data['actual_z'].iloc[0]], color='green', s=100, label='Start')
    ax1.scatter([improved_data['actual_x'].iloc[-1]], [improved_data['actual_y'].iloc[-1]], 
               [improved_data['actual_z'].iloc[-1]], color='purple', s=100, label='End')
    
    ax1.set_xlabel('X Position (m)')
    ax1.set_ylabel('Y Position (m)')
    ax1.set_zlabel('Z Position (m)')
    ax1.set_title('3D Trajectory Tracking - Improved System')
    ax1.legend()
    ax1.grid(True)
    
    # 2. Position Error Over Time
    ax2 = fig.add_subplot(rows, cols, 2)
    
    # Calculate position errors
    pos_error_x = improved_data['actual_x'] - improved_data[target_x]
    pos_error_y = improved_data['actual_y'] - improved_data[target_y] 
    pos_error_z = improved_data['actual_z'] - improved_data[target_z]
    total_pos_error = np.sqrt(pos_error_x**2 + pos_error_y**2 + pos_error_z**2)
    
    time_rel = improved_data['timestamp'] - improved_data['timestamp'].iloc[0]
    
    ax2.plot(time_rel, total_pos_error, label='Total Position Error', color='red', linewidth=2)
    ax2.plot(time_rel, np.abs(pos_error_x), label='X Error', alpha=0.7)
    ax2.plot(time_rel, np.abs(pos_error_y), label='Y Error', alpha=0.7)
    ax2.plot(time_rel, np.abs(pos_error_z), label='Z Error', alpha=0.7)
    
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Position Error (m)')
    ax2.set_title('Position Tracking Error Over Time')
    ax2.legend()
    ax2.grid(True)
    
    # 3. Velocity Profiles
    ax3 = fig.add_subplot(rows, cols, 3)
    
    if has_velocity:
        # Use actual velocity data from log
        vel_x = improved_data['actual_vx']
        vel_y = improved_data['actual_vy']
        vel_z = improved_data['actual_vz']
        vel_magnitude = np.sqrt(vel_x**2 + vel_y**2 + vel_z**2)
        
        ax3.plot(time_rel, vel_magnitude, label='Speed', color='purple', linewidth=2)
        ax3.plot(time_rel, vel_x, label='Vx', alpha=0.7)
        ax3.plot(time_rel, vel_y, label='Vy', alpha=0.7)
        ax3.plot(time_rel, vel_z, label='Vz', alpha=0.7)
        
        if 'desired_vx' in improved_data.columns:
            desired_vel_mag = np.sqrt(improved_data['desired_vx']**2 + 
                                    improved_data['desired_vy']**2 + 
                                    improved_data['desired_vz']**2)
            ax3.plot(time_rel, desired_vel_mag, label='Desired Speed', 
                    color='red', linestyle='--', linewidth=2)
    else:
        # Calculate velocities from positions (numerical differentiation)
        dt = np.diff(improved_data['timestamp'])
        vel_x = np.diff(improved_data['actual_x']) / dt
        vel_y = np.diff(improved_data['actual_y']) / dt
        vel_z = np.diff(improved_data['actual_z']) / dt
        vel_magnitude = np.sqrt(vel_x**2 + vel_y**2 + vel_z**2)
        
        time_vel = time_rel[1:]  # One less point due to diff
        
        ax3.plot(time_vel, vel_magnitude, label='Speed', color='purple', linewidth=2)
        ax3.plot(time_vel, vel_x, label='Vx', alpha=0.7)
        ax3.plot(time_vel, vel_y, label='Vy', alpha=0.7)
        ax3.plot(time_vel, vel_z, label='Vz', alpha=0.7)
    
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Velocity (m/s)')
    ax3.set_title('Velocity Profiles - Smooth Motion')
    ax3.legend()
    ax3.grid(True)
    
    # 4. Position Components Over Time
    ax4 = fig.add_subplot(rows, cols, 4)
    
    ax4.plot(time_rel, improved_data['actual_x'], label='Actual X', color='blue')
    ax4.plot(time_rel, improved_data[target_x], label='Target X', color='blue', linestyle='--')
    ax4.plot(time_rel, improved_data['actual_y'], label='Actual Y', color='green')
    ax4.plot(time_rel, improved_data[target_y], label='Target Y', color='green', linestyle='--')
    ax4.plot(time_rel, improved_data['actual_z'], label='Actual Z', color='red')
    ax4.plot(time_rel, improved_data[target_z], label='Target Z', color='red', linestyle='--')
    
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Position (m)')
    ax4.set_title('Position Components vs Target')
    ax4.legend()
    ax4.grid(True)
    
    # 5. Error Statistics
    ax5 = fig.add_subplot(rows, cols, 5)
    
    # Create error statistics
    error_stats = {
        'Mean Error': [np.mean(np.abs(pos_error_x)), np.mean(np.abs(pos_error_y)), 
                      np.mean(np.abs(pos_error_z)), np.mean(total_pos_error)],
        'Max Error': [np.max(np.abs(pos_error_x)), np.max(np.abs(pos_error_y)), 
                     np.max(np.abs(pos_error_z)), np.max(total_pos_error)],
        'RMS Error': [np.sqrt(np.mean(pos_error_x**2)), np.sqrt(np.mean(pos_error_y**2)), 
                     np.sqrt(np.mean(pos_error_z**2)), np.sqrt(np.mean(total_pos_error**2))]
    }
    
    x_pos = np.arange(4)
    width = 0.25
    
    ax5.bar(x_pos - width, error_stats['Mean Error'], width, label='Mean Error', alpha=0.8)
    ax5.bar(x_pos, error_stats['Max Error'], width, label='Max Error', alpha=0.8)
    ax5.bar(x_pos + width, error_stats['RMS Error'], width, label='RMS Error', alpha=0.8)
    
    ax5.set_xlabel('Error Component')
    ax5.set_ylabel('Error Magnitude (m)')
    ax5.set_title('Position Error Statistics')
    ax5.set_xticks(x_pos)
    ax5.set_xticklabels(['X', 'Y', 'Z', 'Total'])
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # 6. Control Performance Metrics
    ax6 = fig.add_subplot(rows, cols, 6)
    
    # Calculate actual control frequency
    control_dt = np.diff(improved_data['timestamp'])
    control_freq = 1.0 / control_dt
    
    # Remove outliers for better visualization
    freq_percentile_95 = np.percentile(control_freq, 95)
    freq_clean = control_freq[control_freq <= freq_percentile_95]
    
    ax6.hist(freq_clean, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
    ax6.axvline(float(np.mean(freq_clean)), color='red', linestyle='--', linewidth=2, 
               label=f'Mean: {np.mean(freq_clean):.1f} Hz')
    ax6.axvline(1000, color='green', linestyle='--', linewidth=2, label='Target: 1000 Hz')
    
    ax6.set_xlabel('Control Frequency (Hz)')
    ax6.set_ylabel('Count')
    ax6.set_title('Control Loop Frequency Distribution')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    # Additional plots for enhanced data
    if has_control and rows > 2:
        # 7. Control Inputs Over Time
        ax7 = fig.add_subplot(rows, cols, 7)
        
        ax7.plot(time_rel, improved_data['thrust'], label='Thrust', color='blue', linewidth=2)
        ax7_twin = ax7.twinx()
        ax7_twin.plot(time_rel, improved_data['torque_norm'], label='Torque Norm', 
                     color='red', linewidth=2)
        
        ax7.set_xlabel('Time (s)')
        ax7.set_ylabel('Thrust (N)', color='blue')
        ax7_twin.set_ylabel('Torque Norm (N⋅m)', color='red')
        ax7.set_title('Control Inputs Over Time')
        ax7.grid(True, alpha=0.3)
        
        # Combine legends
        lines1, labels1 = ax7.get_legend_handles_labels()
        lines2, labels2 = ax7_twin.get_legend_handles_labels()
        ax7.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        # 8. Velocity Tracking (if available)
        if has_velocity:
            ax8 = fig.add_subplot(rows, cols, 8)
            
            # Velocity errors
            vel_error_x = improved_data['actual_vx'] - improved_data['desired_vx']
            vel_error_y = improved_data['actual_vy'] - improved_data['desired_vy']
            vel_error_z = improved_data['actual_vz'] - improved_data['desired_vz']
            total_vel_error = np.sqrt(vel_error_x**2 + vel_error_y**2 + vel_error_z**2)
            
            ax8.plot(time_rel, total_vel_error, label='Total Velocity Error', 
                    color='red', linewidth=2)
            ax8.plot(time_rel, np.abs(vel_error_x), label='Vx Error', alpha=0.7)
            ax8.plot(time_rel, np.abs(vel_error_y), label='Vy Error', alpha=0.7)
            ax8.plot(time_rel, np.abs(vel_error_z), label='Vz Error', alpha=0.7)
            
            ax8.set_xlabel('Time (s)')
            ax8.set_ylabel('Velocity Error (m/s)')
            ax8.set_title('Velocity Tracking Error')
            ax8.legend()
            ax8.grid(True)
        
        # 9. Failsafe Status
        if 'failsafe_active' in improved_data.columns:
            ax9 = fig.add_subplot(rows, cols, 9)
            
            failsafe_values = improved_data['failsafe_active'].astype(int)
            ax9.plot(time_rel, failsafe_values, label='Failsafe Active', 
                    color='red', linewidth=3, marker='o', markersize=2)
            ax9.fill_between(time_rel, 0, failsafe_values, alpha=0.3, color='red')
            
            ax9.set_xlabel('Time (s)')
            ax9.set_ylabel('Failsafe Status')
            ax9.set_title('Safety System Status')
            ax9.set_ylim(-0.1, 1.1)
            ax9.set_yticks([0, 1])
            ax9.set_yticklabels(['Safe', 'Failsafe'])
            ax9.legend()
            ax9.grid(True, alpha=0.3)
            
            # Add summary text
            failsafe_count = np.sum(failsafe_values)
            failsafe_pct = 100 * failsafe_count / len(failsafe_values)
            ax9.text(0.02, 0.98, f'Failsafe activations: {failsafe_count} ({failsafe_pct:.1f}%)', 
                    transform=ax9.transAxes, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout(pad=3.0)
    
    # Save the comprehensive plot
    output_filename = 'improved_system_comprehensive_analysis.png'
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    print(f"Comprehensive analysis saved to: {output_filename}")
    
    # Display performance summary
    print("\n" + "="*80)
    print("🚁 IMPROVED DRONE CONTROL SYSTEM PERFORMANCE SUMMARY")
    print("="*80)
    
    print(f"📊 Trajectory Tracking Performance:")
    print(f"   • Total simulation time: {time_rel.iloc[-1]:.2f} seconds")
    print(f"   • Data points collected: {len(improved_data)}")
    print(f"   • Average control frequency: {np.mean(control_freq):.1f} Hz")
    print(f"   • Control frequency std: {np.std(control_freq):.1f} Hz")
    print(f"   • Actual frequency range: {np.min(control_freq):.1f} - {np.max(control_freq):.1f} Hz")
    
    print(f"\n📏 Position Tracking Accuracy:")
    print(f"   • Mean position error: {np.mean(total_pos_error):.4f} m")
    print(f"   • Max position error: {np.max(total_pos_error):.4f} m")
    print(f"   • RMS position error: {np.sqrt(np.mean(total_pos_error**2)):.4f} m")
    print(f"   • Final position error: {total_pos_error.iloc[-1]:.4f} m")
    
    print(f"\n🎯 Component-wise Accuracy:")
    print(f"   • X-axis RMS error: {np.sqrt(np.mean(pos_error_x**2)):.4f} m")
    print(f"   • Y-axis RMS error: {np.sqrt(np.mean(pos_error_y**2)):.4f} m") 
    print(f"   • Z-axis RMS error: {np.sqrt(np.mean(pos_error_z**2)):.4f} m")
    
    # Velocity analysis if available
    if has_velocity:
        vel_x = improved_data['actual_vx']
        vel_y = improved_data['actual_vy']
        vel_z = improved_data['actual_vz']
        vel_magnitude = np.sqrt(vel_x**2 + vel_y**2 + vel_z**2)
        
        print(f"\n🚀 Motion Characteristics:")
        print(f"   • Average speed: {np.mean(vel_magnitude):.2f} m/s")
        print(f"   • Max speed: {np.max(vel_magnitude):.2f} m/s")
        print(f"   • Speed standard deviation: {np.std(vel_magnitude):.2f} m/s")
        
        if 'desired_vx' in improved_data.columns:
            vel_error_x = improved_data['actual_vx'] - improved_data['desired_vx']
            vel_error_y = improved_data['actual_vy'] - improved_data['desired_vy']
            vel_error_z = improved_data['actual_vz'] - improved_data['desired_vz']  
            total_vel_error = np.sqrt(vel_error_x**2 + vel_error_y**2 + vel_error_z**2)
            
            print(f"\n🎯 Velocity Tracking Accuracy:")
            print(f"   • Mean velocity error: {np.mean(total_vel_error):.4f} m/s")
            print(f"   • Max velocity error: {np.max(total_vel_error):.4f} m/s")
            print(f"   • RMS velocity error: {np.sqrt(np.mean(total_vel_error**2)):.4f} m/s")
    
    # Control analysis if available
    if has_control:
        print(f"\n⚙️ Control System Performance:")
        print(f"   • Average thrust: {np.mean(improved_data['thrust']):.2f} N")
        print(f"   • Thrust range: {np.min(improved_data['thrust']):.2f} - {np.max(improved_data['thrust']):.2f} N")
        print(f"   • Average torque norm: {np.mean(improved_data['torque_norm']):.4f} N⋅m")
        print(f"   • Max torque norm: {np.max(improved_data['torque_norm']):.4f} N⋅m")
        
        if 'failsafe_active' in improved_data.columns:
            failsafe_count = np.sum(improved_data['failsafe_active'].astype(int))
            failsafe_pct = 100 * failsafe_count / len(improved_data)
            print(f"\n🛡️ Safety System:")
            print(f"   • Failsafe activations: {failsafe_count} times ({failsafe_pct:.2f}%)")
            print(f"   • System stability: {'EXCELLENT' if failsafe_count == 0 else 'NEEDS ATTENTION'}")
    
    # Compare with original if provided
    if original_log_files:
        print(f"\n📈 COMPARISON WITH ORIGINAL SYSTEM:")
        try:
            # Find latest original log
            latest_original = max(original_log_files, key=os.path.getctime)
            original_data = pd.read_csv(latest_original)
            
            # Determine original format
            orig_target_x = 'target_x' if 'target_x' in original_data.columns else 'desired_x'
            orig_target_y = 'target_y' if 'target_y' in original_data.columns else 'desired_y'
            orig_target_z = 'target_z' if 'target_z' in original_data.columns else 'desired_z'
            
            # Calculate original errors
            orig_pos_error_x = original_data['actual_x'] - original_data[orig_target_x]
            orig_pos_error_y = original_data['actual_y'] - original_data[orig_target_y]
            orig_pos_error_z = original_data['actual_z'] - original_data[orig_target_z]
            orig_total_pos_error = np.sqrt(orig_pos_error_x**2 + orig_pos_error_y**2 + orig_pos_error_z**2)
            
            improvement_factor = np.mean(orig_total_pos_error) / np.mean(total_pos_error)
            print(f"   • Original mean error: {np.mean(orig_total_pos_error):.2f} m")
            print(f"   • Improved mean error: {np.mean(total_pos_error):.4f} m")
            print(f"   • Improvement factor: {improvement_factor:.1f}x better! 🎉")
            
            # Control frequency comparison
            orig_dt = np.diff(original_data['timestamp'])
            orig_freq = 1.0 / orig_dt
            freq_improvement = np.mean(control_freq) / np.mean(orig_freq)
            print(f"   • Original avg frequency: {np.mean(orig_freq):.1f} Hz")
            print(f"   • Improved avg frequency: {np.mean(control_freq):.1f} Hz")
            print(f"   • Frequency improvement: {freq_improvement:.1f}x")
            
        except Exception as e:
            print(f"   • Could not load original data for comparison: {e}")
    
    plt.show()
    
    return {
        'mean_error': np.mean(total_pos_error),
        'max_error': np.max(total_pos_error),
        'rms_error': np.sqrt(np.mean(total_pos_error**2)),
        'avg_frequency': np.mean(control_freq),
        'simulation_time': time_rel.iloc[-1],
        'has_enhanced_data': has_velocity and has_control
    }

def compare_with_original_logs():
    """
    Create a comparison visualization between improved and original systems
    """
    # Find log files
    improved_files = glob.glob('improved_trajectory_log_*.csv')
    original_files = glob.glob('trajectory_log_*.csv')
    original_files = [f for f in original_files if not f.startswith('improved_')]
    
    if not improved_files:
        print("No improved log files found!")
        return
    
    if not original_files:
        print("No original log files found for comparison!")
        original_files = None
    
    # Get latest files
    latest_improved = max(improved_files, key=os.path.getctime)
    
    if original_files:
        latest_original = max(original_files, key=os.path.getctime)
        print(f"Comparing:")
        print(f"📊 Improved: {latest_improved}")
        print(f"📊 Original: {latest_original}")
    else:
        print(f"Analyzing improved system: {latest_improved}")
    
    # Create comprehensive analysis
    return create_comprehensive_visualization(latest_improved, original_files)

if __name__ == "__main__":
    compare_with_original_logs() 