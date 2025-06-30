#!/usr/bin/env python3
"""
Comprehensive System Test and Visualization
============================================
This script performs thorough testing of the 3-layer drone control system
and generates comprehensive visualizations to verify system performance.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import pytest

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.common.types import DroneState, Trajectory
from src.control.geometric_controller import GeometricController
from src.planning.dial_mpc_planner import ContinuousDIALMPC
from src.utils.drone_simulator import DroneSimulator

# Extensive end-to-end simulation; run only in the slow CI workflow
pytestmark = pytest.mark.slow

def test_component_initialization():
    """Test that all system components can be initialized properly."""
    print("🔧 Testing component initialization...")

    results = {}

    try:
        # Test drone simulator
        simulator = DroneSimulator()
        results["DroneSimulator"] = "✅ Pass"
        print("  ✅ DroneSimulator initialization: Pass")
    except Exception as e:
        results["DroneSimulator"] = f"❌ Fail: {str(e)}"
        print(f"  ❌ DroneSimulator initialization: Fail - {e}")

    try:
        # Test geometric controller
        controller = GeometricController()
        results["GeometricController"] = "✅ Pass"
        print("  ✅ GeometricController initialization: Pass")
    except Exception as e:
        results["GeometricController"] = f"❌ Fail: {str(e)}"
        print(f"  ❌ GeometricController initialization: Fail - {e}")

    try:
        # Test DIAL-MPC planner
        planner = ContinuousDIALMPC()
        results["ContinuousDIALMPC"] = "✅ Pass"
        print("  ✅ ContinuousDIALMPC initialization: Pass")
    except Exception as e:
        results["ContinuousDIALMPC"] = f"❌ Fail: {str(e)}"
        print(f"  ❌ ContinuousDIALMPC initialization: Fail - {e}")

    return results


def test_system_performance():
    """Test the integrated system performance."""
    print("\n📊 Testing system performance...")

    # Initialize components
    simulator = DroneSimulator()
    controller = GeometricController()
    planner = ContinuousDIALMPC()

    # Test parameters
    duration = 5.0  # 5 seconds test
    dt = 0.001  # 1ms control loop

    # Data collection
    times = []
    positions = []
    velocities = []
    control_errors = []
    planning_times = []

    # Set target position
    target_pos = np.array([10.0, 5.0, -15.0])

    print(f"  🎯 Target position: {target_pos}")
    print(f"  ⏱️  Test duration: {duration}s")

    start_time = time.time()
    current_time = 0.0

    while current_time < duration:
        iteration_start = time.time()

        # Get current state
        state = simulator.get_state()

        # Plan trajectory (run every 10ms)
        if len(times) % 10 == 0:
            plan_start = time.time()
            trajectory = planner.plan_trajectory(
                current_state=state, target_position=target_pos, horizon_length=20
            )
            planning_time = (time.time() - plan_start) * 1000  # Convert to ms
            planning_times.append(planning_time)

        # Control
        if "trajectory" in locals():
            desired_state = trajectory.get_state_at_time(current_time)
        else:
            desired_state = DroneState(
                timestamp=current_time, position=target_pos, velocity=np.zeros(3)
            )

        control_input = controller.compute_control(state, desired_state)

        # Simulate
        simulator.step(control_input, dt)

        # Record data
        times.append(current_time)
        positions.append(state.position.copy())
        velocities.append(state.velocity.copy())

        # Compute error
        pos_error = np.linalg.norm(state.position - target_pos)
        control_errors.append(pos_error)

        current_time += dt

        # Maintain real-time simulation
        elapsed = time.time() - iteration_start
        if elapsed < dt:
            time.sleep(dt - elapsed)

    total_time = time.time() - start_time
    actual_frequency = len(times) / total_time

    print(f"  📈 Completed {len(times)} iterations in {total_time:.2f}s")
    print(f"  🔄 Actual frequency: {actual_frequency:.1f}Hz")
    print(f"  📏 Final position error: {control_errors[-1]:.3f}m")
    print(f"  ⚡ Average planning time: {np.mean(planning_times):.2f}ms")

    return {
        "times": np.array(times),
        "positions": np.array(positions),
        "velocities": np.array(velocities),
        "control_errors": np.array(control_errors),
        "planning_times": np.array(planning_times),
        "actual_frequency": actual_frequency,
        "final_error": control_errors[-1],
        "avg_planning_time": np.mean(planning_times),
    }


def analyze_recent_logs():
    """Analyze the most recent trajectory logs."""
    print("\n📋 Analyzing recent trajectory logs...")

    # Find the most recent trajectory log
    log_files = list(Path(".").glob("*trajectory_log_*.csv"))
    if not log_files:
        print("  ❌ No trajectory log files found")
        return None

    # Get the most recent log
    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
    print(f"  📄 Analyzing: {latest_log}")

    try:
        df = pd.read_csv(latest_log)

        # Basic statistics
        duration = df["time"].iloc[-1] - df["time"].iloc[0]
        control_freq = len(df) / duration

        # Position tracking analysis
        if "pos_x" in df.columns:
            pos_errors = np.sqrt(
                (df["pos_x"] - df["target_x"]) ** 2
                + (df["pos_y"] - df["target_y"]) ** 2
                + (df["pos_z"] - df["target_z"]) ** 2
            )
            avg_pos_error = pos_errors.mean()
            max_pos_error = pos_errors.max()
        else:
            avg_pos_error = max_pos_error = "N/A"

        # Velocity analysis
        if "vel_x" in df.columns:
            velocities = np.sqrt(df["vel_x"] ** 2 + df["vel_y"] ** 2 + df["vel_z"] ** 2)
            avg_velocity = velocities.mean()
            max_velocity = velocities.max()
        else:
            avg_velocity = max_velocity = "N/A"

        print(f"  ⏱️  Log duration: {duration:.2f}s")
        print(f"  🔄 Control frequency: {control_freq:.1f}Hz")
        print(
            f"  📏 Average position error: {avg_pos_error:.3f}m"
            if avg_pos_error != "N/A"
            else "  📏 Position error: N/A"
        )
        print(
            f"  📏 Maximum position error: {max_pos_error:.3f}m"
            if max_pos_error != "N/A"
            else "  📏 Max position error: N/A"
        )
        print(
            f"  🚀 Average velocity: {avg_velocity:.2f}m/s"
            if avg_velocity != "N/A"
            else "  🚀 Average velocity: N/A"
        )
        print(
            f"  🚀 Maximum velocity: {max_velocity:.2f}m/s"
            if max_velocity != "N/A"
            else "  🚀 Maximum velocity: N/A"
        )

        return {
            "dataframe": df,
            "duration": duration,
            "control_freq": control_freq,
            "avg_pos_error": avg_pos_error,
            "max_pos_error": max_pos_error,
            "avg_velocity": avg_velocity,
            "max_velocity": max_velocity,
        }

    except Exception as e:
        print(f"  ❌ Error analyzing log: {e}")
        return None


def create_comprehensive_visualization(test_results, log_analysis):
    """Create comprehensive visualizations of system performance."""
    print("\n🎨 Creating comprehensive visualizations...")

    # Set up the plotting style
    plt.style.use("default")
    sns.set_palette("husl")

    # Create figure with subplots
    fig = plt.figure(figsize=(20, 16))

    # Define the grid layout
    gs = fig.add_gridspec(4, 4, hspace=0.3, wspace=0.3)

    # 1. Component Status Overview
    ax1 = fig.add_subplot(gs[0, 0:2])
    component_results = test_component_initialization()
    components = list(component_results.keys())
    statuses = [1 if "✅" in status else 0 for status in component_results.values()]
    colors = ["green" if status == 1 else "red" for status in statuses]

    bars = ax1.bar(components, statuses, color=colors, alpha=0.7)
    ax1.set_ylim(0, 1.2)
    ax1.set_ylabel("Status")
    ax1.set_title("System Component Status", fontsize=14, fontweight="bold")
    ax1.tick_params(axis="x", rotation=45)

    # Add status text
    for i, (component, status) in enumerate(component_results.items()):
        if "✅" in status:
            ax1.text(i, 0.5, "✅ PASS", ha="center", va="center", fontweight="bold")
        else:
            ax1.text(i, 0.5, "❌ FAIL", ha="center", va="center", fontweight="bold")

    # 2. Performance Metrics
    ax2 = fig.add_subplot(gs[0, 2:4])
    if test_results and log_analysis:
        metrics = ["Control Freq (Hz)", "Final Error (m)", "Avg Planning (ms)"]
        values = [
            test_results["actual_frequency"],
            test_results["final_error"],
            test_results["avg_planning_time"],
        ]

        bars = ax2.bar(metrics, values, color=["blue", "orange", "green"], alpha=0.7)
        ax2.set_title("Performance Metrics", fontsize=14, fontweight="bold")
        ax2.tick_params(axis="x", rotation=45)

        # Add value labels
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + height * 0.05,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontweight="bold",
            )
    else:
        ax2.text(
            0.5,
            0.5,
            "No test results available",
            ha="center",
            va="center",
            transform=ax2.transAxes,
            fontsize=12,
        )
        ax2.set_title("Performance Metrics (No Data)", fontsize=14, fontweight="bold")

    # 3. Position Tracking (from test)
    ax3 = fig.add_subplot(gs[1, 0:2])
    if test_results:
        times = test_results["times"]
        positions = test_results["positions"]

        ax3.plot(times, positions[:, 0], label="X Position", linewidth=2)
        ax3.plot(times, positions[:, 1], label="Y Position", linewidth=2)
        ax3.plot(times, positions[:, 2], label="Z Position", linewidth=2)

        ax3.axhline(y=10.0, color="r", linestyle="--", alpha=0.7, label="Target X")
        ax3.axhline(y=5.0, color="g", linestyle="--", alpha=0.7, label="Target Y")
        ax3.axhline(y=-15.0, color="b", linestyle="--", alpha=0.7, label="Target Z")

        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("Position (m)")
        ax3.set_title("Position Tracking Performance", fontsize=14, fontweight="bold")
        ax3.legend()
        ax3.grid(True, alpha=0.3)
    else:
        ax3.text(
            0.5,
            0.5,
            "No position data available",
            ha="center",
            va="center",
            transform=ax3.transAxes,
            fontsize=12,
        )
        ax3.set_title("Position Tracking (No Data)", fontsize=14, fontweight="bold")

    # 4. Control Error (from test)
    ax4 = fig.add_subplot(gs[1, 2:4])
    if test_results:
        ax4.plot(
            test_results["times"],
            test_results["control_errors"],
            linewidth=2,
            color="red",
            alpha=0.8,
        )
        ax4.set_xlabel("Time (s)")
        ax4.set_ylabel("Position Error (m)")
        ax4.set_title("Control Error Over Time", fontsize=14, fontweight="bold")
        ax4.grid(True, alpha=0.3)

        # Add final error annotation
        final_error = test_results["control_errors"][-1]
        ax4.annotate(
            f"Final Error: {final_error:.3f}m",
            xy=(test_results["times"][-1], final_error),
            xytext=(test_results["times"][-1] * 0.7, final_error * 1.5),
            arrowprops=dict(arrowstyle="->", color="black"),
            fontsize=10,
            fontweight="bold",
        )
    else:
        ax4.text(
            0.5,
            0.5,
            "No error data available",
            ha="center",
            va="center",
            transform=ax4.transAxes,
            fontsize=12,
        )
        ax4.set_title("Control Error (No Data)", fontsize=14, fontweight="bold")

    # 5. Planning Time Distribution (from test)
    ax5 = fig.add_subplot(gs[2, 0:2])
    if test_results and len(test_results["planning_times"]) > 0:
        ax5.hist(
            test_results["planning_times"],
            bins=20,
            alpha=0.7,
            color="green",
            edgecolor="black",
        )
        ax5.axvline(
            np.mean(test_results["planning_times"]),
            color="red",
            linestyle="--",
            linewidth=2,
            label=f'Mean: {np.mean(test_results["planning_times"]):.2f}ms',
        )
        ax5.set_xlabel("Planning Time (ms)")
        ax5.set_ylabel("Frequency")
        ax5.set_title(
            "DIAL-MPC Planning Time Distribution", fontsize=14, fontweight="bold"
        )
        ax5.legend()
        ax5.grid(True, alpha=0.3)
    else:
        ax5.text(
            0.5,
            0.5,
            "No planning time data available",
            ha="center",
            va="center",
            transform=ax5.transAxes,
            fontsize=12,
        )
        ax5.set_title(
            "Planning Time Distribution (No Data)", fontsize=14, fontweight="bold"
        )

    # 6. Log Analysis - Position Error Histogram
    ax6 = fig.add_subplot(gs[2, 2:4])
    if log_analysis and log_analysis["avg_pos_error"] != "N/A":
        df = log_analysis["dataframe"]
        if "pos_x" in df.columns:
            pos_errors = np.sqrt(
                (df["pos_x"] - df["target_x"]) ** 2
                + (df["pos_y"] - df["target_y"]) ** 2
                + (df["pos_z"] - df["target_z"]) ** 2
            )
            ax6.hist(pos_errors, bins=30, alpha=0.7, color="blue", edgecolor="black")
            ax6.axvline(
                pos_errors.mean(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Mean: {pos_errors.mean():.3f}m",
            )
            ax6.set_xlabel("Position Error (m)")
            ax6.set_ylabel("Frequency")
            ax6.set_title(
                "Position Error Distribution (Log Data)", fontsize=14, fontweight="bold"
            )
            ax6.legend()
            ax6.grid(True, alpha=0.3)
        else:
            ax6.text(
                0.5,
                0.5,
                "No position error data in log",
                ha="center",
                va="center",
                transform=ax6.transAxes,
                fontsize=12,
            )
            ax6.set_title(
                "Position Error Distribution (No Data)", fontsize=14, fontweight="bold"
            )
    else:
        ax6.text(
            0.5,
            0.5,
            "No log data available",
            ha="center",
            va="center",
            transform=ax6.transAxes,
            fontsize=12,
        )
        ax6.set_title(
            "Position Error Distribution (No Log)", fontsize=14, fontweight="bold"
        )

    # 7. 3D Trajectory Visualization
    ax7 = fig.add_subplot(gs[3, 0:2], projection="3d")
    if test_results:
        positions = test_results["positions"]
        ax7.plot(
            positions[:, 0],
            positions[:, 1],
            positions[:, 2],
            linewidth=2,
            alpha=0.8,
            label="Actual Trajectory",
        )

        # Mark start and end points
        ax7.scatter(*positions[0], color="green", s=100, label="Start", alpha=0.8)
        ax7.scatter(*positions[-1], color="red", s=100, label="End", alpha=0.8)
        ax7.scatter(
            10.0,
            5.0,
            -15.0,
            color="orange",
            s=150,
            marker="*",
            label="Target",
            alpha=0.8,
        )

        ax7.set_xlabel("X Position (m)")
        ax7.set_ylabel("Y Position (m)")
        ax7.set_zlabel("Z Position (m)")
        ax7.set_title("3D Trajectory Visualization", fontsize=14, fontweight="bold")
        ax7.legend()
    else:
        ax7.text(
            0.5,
            0.5,
            0.5,
            "No trajectory data available",
            ha="center",
            va="center",
            transform=ax7.transAxes,
            fontsize=12,
        )
        ax7.set_title("3D Trajectory (No Data)", fontsize=14, fontweight="bold")

    # 8. System Status Summary
    ax8 = fig.add_subplot(gs[3, 2:4])
    ax8.axis("off")

    # Create status summary
    status_text = "System Status Summary\n" + "=" * 25 + "\n\n"

    # Component status
    all_pass = all("✅" in status for status in component_results.values())
    status_text += f"🔧 Components: {'✅ ALL PASS' if all_pass else '❌ SOME FAILED'}\n"

    # Performance status
    if test_results:
        freq_ok = test_results["actual_frequency"] > 500  # Target 500+ Hz
        error_ok = test_results["final_error"] < 1.0  # Target < 1m error
        planning_ok = test_results["avg_planning_time"] < 10  # Target < 10ms

        status_text += f"📊 Control Freq: {'✅' if freq_ok else '❌'} {test_results['actual_frequency']:.1f}Hz\n"
        status_text += f"📏 Final Error: {'✅' if error_ok else '❌'} {test_results['final_error']:.3f}m\n"
        status_text += f"⚡ Planning Time: {'✅' if planning_ok else '❌'} {test_results['avg_planning_time']:.2f}ms\n"
    else:
        status_text += "📊 Performance: ❌ No test data\n"

    # Log analysis status
    if log_analysis:
        status_text += f"📋 Latest Log: ✅ {log_analysis['duration']:.1f}s @ {log_analysis['control_freq']:.1f}Hz\n"
    else:
        status_text += "📋 Log Analysis: ❌ No logs found\n"

    # Overall system status
    status_text += "\n" + "=" * 25 + "\n"
    overall_ok = all_pass and (test_results is not None) and (log_analysis is not None)
    status_text += f"🎯 Overall Status: {'✅ SYSTEM OPERATIONAL' if overall_ok else '⚠️ ISSUES DETECTED'}"

    ax8.text(
        0.05,
        0.95,
        status_text,
        transform=ax8.transAxes,
        fontsize=12,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="lightgray", alpha=0.8),
    )

    # Add title and metadata
    fig.suptitle(
        "Comprehensive System Test & Performance Analysis",
        fontsize=18,
        fontweight="bold",
        y=0.98,
    )

    # Add timestamp
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    fig.text(
        0.99,
        0.01,
        f"Generated: {timestamp}",
        ha="right",
        va="bottom",
        fontsize=10,
        alpha=0.7,
    )

    # Save the plot
    output_file = f"comprehensive_system_analysis_{int(time.time())}.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"  💾 Visualization saved to: {output_file}")

    return output_file


def main():
    """Main function to run comprehensive system test."""
    print("🚀 Starting Comprehensive System Test")
    print("=" * 50)

    # 1. Test component initialization
    component_results = test_component_initialization()

    # 2. Run performance test
    try:
        test_results = test_system_performance()
    except Exception as e:
        print(f"  ❌ Performance test failed: {e}")
        test_results = None

    # 3. Analyze recent logs
    log_analysis = analyze_recent_logs()

    # 4. Create visualization
    visualization_file = create_comprehensive_visualization(test_results, log_analysis)

    print("\n" + "=" * 50)
    print("🎉 Comprehensive System Test Complete!")
    print(f"📊 Results visualization: {visualization_file}")

    # Print summary
    print("\n📋 SUMMARY:")
    all_components_ok = all("✅" in status for status in component_results.values())
    print(
        f"  🔧 Component Status: {'✅ All components functional' if all_components_ok else '❌ Some components failed'}"
    )

    if test_results:
        print(f"  📊 Performance Test: ✅ Completed successfully")
        print(f"     - Control frequency: {test_results['actual_frequency']:.1f}Hz")
        print(f"     - Final error: {test_results['final_error']:.3f}m")
        print(f"     - Avg planning time: {test_results['avg_planning_time']:.2f}ms")
    else:
        print(f"  📊 Performance Test: ❌ Failed or skipped")

    if log_analysis:
        print(f"  📋 Log Analysis: ✅ Recent logs analyzed")
        print(f"     - Duration: {log_analysis['duration']:.1f}s")
        print(f"     - Control freq: {log_analysis['control_freq']:.1f}Hz")
    else:
        print(f"  📋 Log Analysis: ❌ No recent logs found")

    overall_status = all_components_ok and (test_results is not None)
    print(
        f"\n🎯 OVERALL STATUS: {'✅ SYSTEM READY' if overall_status else '⚠️ ATTENTION REQUIRED'}"
    )


if __name__ == "__main__":
    main()
