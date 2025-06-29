import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D


def create_clean_trajectory_viz(log_file):
    """Create a clean, professional 3D trajectory visualization"""

    try:
        data = pd.read_csv(log_file)
        print(f"Loaded {len(data)} data points from {log_file}")
    except FileNotFoundError:
        print(f"Error: Log file not found: {log_file}")
        return

    # Determine column names
    has_desired = "desired_x" in data.columns
    target_x = "desired_x" if has_desired else "target_x"
    target_y = "desired_y" if has_desired else "target_y"
    target_z = "desired_z" if has_desired else "target_z"

    # Create figure
    fig = plt.figure(figsize=(15, 12))

    # Main 3D plot
    ax1 = fig.add_subplot(2, 2, (1, 3), projection="3d")

    # Plot trajectories
    actual_line = ax1.plot(
        data["actual_x"],
        data["actual_y"],
        data["actual_z"],
        label="Actual Trajectory",
        color="#2E86C1",
        linewidth=3,
        alpha=0.8,
    )
    desired_line = ax1.plot(
        data[target_x],
        data[target_y],
        data[target_z],
        label="Desired Trajectory",
        color="#E74C3C",
        linestyle="--",
        linewidth=2,
        alpha=0.9,
    )

    # Mark start and end points
    ax1.scatter(
        [data["actual_x"].iloc[0]],
        [data["actual_y"].iloc[0]],
        [data["actual_z"].iloc[0]],
        color="#27AE60",
        s=150,
        label="Start Position",
        marker="o",
        edgecolors="black",
        linewidth=2,
    )
    ax1.scatter(
        [data["actual_x"].iloc[-1]],
        [data["actual_y"].iloc[-1]],
        [data["actual_z"].iloc[-1]],
        color="#8E44AD",
        s=150,
        label="End Position",
        marker="s",
        edgecolors="black",
        linewidth=2,
    )

    # Set equal aspect ratio
    max_range = (
        max(
            data["actual_x"].max() - data["actual_x"].min(),
            data["actual_y"].max() - data["actual_y"].min(),
            data["actual_z"].max() - data["actual_z"].min(),
        )
        * 0.6
    )

    mid_x = (data["actual_x"].max() + data["actual_x"].min()) * 0.5
    mid_y = (data["actual_y"].max() + data["actual_y"].min()) * 0.5
    mid_z = (data["actual_z"].max() + data["actual_z"].min()) * 0.5

    ax1.set_xlim(mid_x - max_range, mid_x + max_range)
    ax1.set_ylim(mid_y - max_range, mid_y + max_range)
    ax1.set_zlim(mid_z - max_range, mid_z + max_range)

    # Labels and title
    ax1.set_xlabel("X Position (m)", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Y Position (m)", fontsize=12, fontweight="bold")
    ax1.set_zlabel("Z Position (m)", fontsize=12, fontweight="bold")
    ax1.set_title(
        "Drone Trajectory Tracking Performance\nImproved Distributed Control System",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax1.legend(loc="upper left", fontsize=11)
    ax1.grid(True, alpha=0.3)

    # Position error over time
    ax2 = fig.add_subplot(2, 2, 2)

    pos_error_x = data["actual_x"] - data[target_x]
    pos_error_y = data["actual_y"] - data[target_y]
    pos_error_z = data["actual_z"] - data[target_z]
    total_error = np.sqrt(pos_error_x**2 + pos_error_y**2 + pos_error_z**2)

    time_rel = data["timestamp"] - data["timestamp"].iloc[0]

    ax2.plot(
        time_rel, total_error, color="#E74C3C", linewidth=2, label="Position Error"
    )
    ax2.fill_between(time_rel, 0, total_error, alpha=0.3, color="#E74C3C")

    ax2.set_xlabel("Time (s)", fontsize=11)
    ax2.set_ylabel("Position Error (m)", fontsize=11)
    ax2.set_title("Position Tracking Error", fontsize=12, fontweight="bold")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Control frequency
    ax3 = fig.add_subplot(2, 2, 4)

    dt = np.diff(data["timestamp"])
    freq = 1.0 / dt
    freq_clean = freq[freq <= np.percentile(freq, 95)]  # Remove outliers

    ax3.hist(freq_clean, bins=30, alpha=0.7, color="#3498DB", edgecolor="black")
    ax3.axvline(
        np.mean(freq_clean),
        color="#E74C3C",
        linestyle="--",
        linewidth=2,
        label=f"Mean: {np.mean(freq_clean):.0f} Hz",
    )
    ax3.axvline(
        1000, color="#27AE60", linestyle="--", linewidth=2, label="Target: 1000 Hz"
    )

    ax3.set_xlabel("Control Frequency (Hz)", fontsize=11)
    ax3.set_ylabel("Count", fontsize=11)
    ax3.set_title("Control Loop Performance", fontsize=12, fontweight="bold")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Add performance summary text
    summary_text = f"""Performance Summary:
• Simulation time: {time_rel.iloc[-1]:.1f}s
• Data points: {len(data):,}
• Avg frequency: {np.mean(freq):.0f} Hz
• Mean error: {np.mean(total_error):.2f} m
• Max error: {np.max(total_error):.2f} m
• Final error: {total_error.iloc[-1]:.2f} m"""

    if "failsafe_active" in data.columns:
        failsafe_count = np.sum(data["failsafe_active"].astype(int))
        summary_text += f"\n• Failsafe activations: {failsafe_count}"

    # Add text box
    plt.figtext(
        0.02,
        0.02,
        summary_text,
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8),
    )

    plt.tight_layout()

    # Save figure
    output_file = "clean_trajectory_visualization.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"Clean trajectory visualization saved to: {output_file}")

    plt.show()

    return {
        "mean_error": np.mean(total_error),
        "final_error": total_error.iloc[-1],
        "avg_frequency": np.mean(freq),
        "simulation_time": time_rel.iloc[-1],
    }


if __name__ == "__main__":
    import glob

    # Find latest improved log
    improved_files = glob.glob("improved_trajectory_log_*.csv")
    if improved_files:
        latest_file = max(
            improved_files, key=lambda x: x.split("_")[-1].replace(".csv", "")
        )
        print(f"Visualizing: {latest_file}")
        create_clean_trajectory_viz(latest_file)
    else:
        print("No improved trajectory log files found!")
