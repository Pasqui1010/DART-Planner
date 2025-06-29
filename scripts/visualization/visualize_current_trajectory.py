#!/usr/bin/env python3
"""
Current Trajectory Visualization
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D


def visualize_current_trajectory():
    """Visualize the most recent trajectory log."""

    # Load the latest log
    log_file = "improved_trajectory_log_1751102498.csv"
    print(f"📊 Visualizing trajectory from: {log_file}")

    try:
        df = pd.read_csv(log_file)
        print(f"  📈 Loaded {len(df)} data points")

        # Create figure with subplots
        fig = plt.figure(figsize=(16, 12))

        # 1. 3D Trajectory Plot
        ax1 = fig.add_subplot(2, 3, 1, projection="3d")

        # Plot actual trajectory
        ax1.plot(
            df["actual_x"],
            df["actual_y"],
            df["actual_z"],
            "b-",
            linewidth=2,
            alpha=0.8,
            label="Actual Trajectory",
        )

        # Plot desired trajectory
        ax1.plot(
            df["desired_x"],
            df["desired_y"],
            df["desired_z"],
            "r--",
            linewidth=2,
            alpha=0.8,
            label="Desired Trajectory",
        )

        # Mark start and end points
        ax1.scatter(
            df["actual_x"].iloc[0],
            df["actual_y"].iloc[0],
            df["actual_z"].iloc[0],
            color="green",
            s=100,
            label="Start",
            alpha=0.8,
        )
        ax1.scatter(
            df["actual_x"].iloc[-1],
            df["actual_y"].iloc[-1],
            df["actual_z"].iloc[-1],
            color="red",
            s=100,
            label="End",
            alpha=0.8,
        )

        ax1.set_xlabel("X Position (m)")
        ax1.set_ylabel("Y Position (m)")
        ax1.set_zlabel("Z Position (m)")
        ax1.set_title("3D Flight Trajectory", fontweight="bold")
        ax1.legend()

        # 2. Position tracking over time
        ax2 = fig.add_subplot(2, 3, 2)
        time = df["timestamp"] - df["timestamp"].iloc[0]  # Relative time

        ax2.plot(time, df["actual_x"], "b-", label="Actual X", alpha=0.8)
        ax2.plot(time, df["desired_x"], "r--", label="Desired X", alpha=0.8)
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("X Position (m)")
        ax2.set_title("X Position Tracking", fontweight="bold")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 3. Position error over time
        ax3 = fig.add_subplot(2, 3, 3)
        pos_error = np.sqrt(
            (df["actual_x"] - df["desired_x"]) ** 2
            + (df["actual_y"] - df["desired_y"]) ** 2
            + (df["actual_z"] - df["desired_z"]) ** 2
        )

        ax3.plot(time, pos_error, "r-", linewidth=2, alpha=0.8)
        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("Position Error (m)")
        ax3.set_title("Position Tracking Error", fontweight="bold")
        ax3.grid(True, alpha=0.3)

        # Add statistics
        mean_error = pos_error.mean()
        max_error = pos_error.max()
        ax3.text(
            0.02,
            0.98,
            f"Mean: {mean_error:.2f}m\nMax: {max_error:.2f}m",
            transform=ax3.transAxes,
            va="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

        # 4. Velocity profile
        ax4 = fig.add_subplot(2, 3, 4)
        actual_speed = np.sqrt(
            df["actual_vx"] ** 2 + df["actual_vy"] ** 2 + df["actual_vz"] ** 2
        )
        desired_speed = np.sqrt(
            df["desired_vx"] ** 2 + df["desired_vy"] ** 2 + df["desired_vz"] ** 2
        )

        ax4.plot(time, actual_speed, "b-", label="Actual Speed", alpha=0.8)
        ax4.plot(time, desired_speed, "r--", label="Desired Speed", alpha=0.8)
        ax4.set_xlabel("Time (s)")
        ax4.set_ylabel("Speed (m/s)")
        ax4.set_title("Velocity Profile", fontweight="bold")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        # 5. Control inputs
        ax5 = fig.add_subplot(2, 3, 5)
        ax5.plot(time, df["thrust"], "g-", label="Thrust", alpha=0.8)
        ax5_twin = ax5.twinx()
        ax5_twin.plot(time, df["torque_norm"], "purple", label="Torque Norm", alpha=0.8)

        ax5.set_xlabel("Time (s)")
        ax5.set_ylabel("Thrust (N)", color="g")
        ax5_twin.set_ylabel("Torque Norm (N⋅m)", color="purple")
        ax5.set_title("Control Inputs", fontweight="bold")
        ax5.grid(True, alpha=0.3)

        # 6. System status
        ax6 = fig.add_subplot(2, 3, 6)
        ax6.axis("off")

        # Calculate statistics
        duration = time.iloc[-1]
        frequency = len(df) / duration
        failsafe_count = df["failsafe_active"].sum()

        status_text = f"""FLIGHT SUMMARY
=================

Duration: {duration:.1f} seconds
Data Points: {len(df):,}
Avg Frequency: {frequency:.1f} Hz

Position Tracking:
• Mean Error: {mean_error:.2f} m
• Max Error: {max_error:.2f} m
• Final Error: {pos_error.iloc[-1]:.2f} m

Motion:
• Avg Speed: {actual_speed.mean():.1f} m/s
• Max Speed: {actual_speed.max():.1f} m/s

Control:
• Avg Thrust: {df['thrust'].mean():.1f} N
• Max Torque: {df['torque_norm'].max():.2f} N⋅m

Safety:
• Failsafe Acts: {failsafe_count} times
• Status: {"✅ SAFE" if failsafe_count == 0 else "⚠️ CHECK"}
"""

        ax6.text(
            0.05,
            0.95,
            status_text,
            transform=ax6.transAxes,
            fontsize=10,
            verticalalignment="top",
            fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.3),
        )

        plt.suptitle(
            "Drone Control System - Current Flight Analysis",
            fontsize=16,
            fontweight="bold",
        )
        plt.tight_layout()

        # Save the plot
        output_file = "current_trajectory_analysis.png"
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"  💾 Trajectory analysis saved: {output_file}")

        return output_file

    except Exception as e:
        print(f"  ❌ Error visualizing trajectory: {e}")
        return None


if __name__ == "__main__":
    visualize_current_trajectory()
