#!/usr/bin/env python3
"""
Test Optimized Geometric Controller
===================================
Validates the improved controller and compares against baseline performance
"""

import os
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
import pytest
from mpl_toolkits.mplot3d import Axes3D

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from dart_planner.common.types import ControlCommand, DroneState
from dart_planner.control.geometric_controller import (
    GeometricController,
    GeometricControllerConfig,
)
from dart_planner.utils.drone_simulator import DroneSimulator

# Heavy physics simulation & figure generation – run only in the slow CI job
pytestmark = pytest.mark.slow


def create_test_trajectory(duration=10.0, dt=0.001):
    """Create a challenging test trajectory."""

    t = np.arange(0, duration, dt)

    # Figure-8 trajectory in 3D space
    x = 5 * np.sin(0.5 * t)
    y = 3 * np.cos(1.0 * t)
    z = 2 + 1 * np.sin(0.8 * t)

    # Velocities (derivatives)
    vx = 5 * 0.5 * np.cos(0.5 * t)
    vy = 3 * (-1.0) * np.sin(1.0 * t)
    vz = 1 * 0.8 * np.cos(0.8 * t)

    # Accelerations (second derivatives)
    ax = 5 * (-0.25) * np.sin(0.5 * t)
    ay = 3 * (-1.0) * np.cos(1.0 * t)
    az = 1 * (-0.64) * np.sin(0.8 * t)

    trajectory = {
        "time": t,
        "position": np.column_stack([x, y, z]),
        "velocity": np.column_stack([vx, vy, vz]),
        "acceleration": np.column_stack([ax, ay, az]),
        "yaw": 0.1 * t,  # Slow yaw rotation
    }

    return trajectory


def test_controller_performance(controller, trajectory, simulator):
    """Test controller performance on the given trajectory."""

    print(f"🧪 Testing controller performance...")

    # Initialize drone at starting position
    current_state = DroneState(
        position=trajectory["position"][0],
        velocity=np.zeros(3),
        attitude=np.zeros(3),
        angular_velocity=np.zeros(3),
        timestamp=0.0,
    )

    # Storage for results
    results = {
        "time": [],
        "actual_pos": [],
        "desired_pos": [],
        "actual_vel": [],
        "desired_vel": [],
        "position_errors": [],
        "velocity_errors": [],
        "control_commands": [],
        "thrust_commands": [],
        "torque_commands": [],
    }

    dt = 0.001  # 1kHz control rate
    total_steps = len(trajectory["time"])

    print(f"   Running {total_steps} steps at {1/dt:.0f}Hz...")

    start_time = time.time()

    for i, t in enumerate(trajectory["time"]):
        if i % 1000 == 0:
            progress = (i / total_steps) * 100
            print(f"   Progress: {progress:.1f}%")

        # Update timestamp
        current_state.timestamp = t

        # Get desired trajectory point
        desired_pos = trajectory["position"][i]
        desired_vel = trajectory["velocity"][i]
        desired_acc = trajectory["acceleration"][i]
        desired_yaw = trajectory["yaw"][i]

        # Compute control command
        control_cmd = controller.compute_control(
            current_state, desired_pos, desired_vel, desired_acc, desired_yaw
        )

        # Simulate one step
        current_state = simulator.step(current_state, control_cmd, dt)

        # Store results
        pos_error = np.linalg.norm(desired_pos - current_state.position)
        vel_error = np.linalg.norm(desired_vel - current_state.velocity)

        results["time"].append(t)
        results["actual_pos"].append(current_state.position.copy())
        results["desired_pos"].append(desired_pos.copy())
        results["actual_vel"].append(current_state.velocity.copy())
        results["desired_vel"].append(desired_vel.copy())
        results["position_errors"].append(pos_error)
        results["velocity_errors"].append(vel_error)
        results["control_commands"].append([control_cmd.thrust, *control_cmd.torque])
        results["thrust_commands"].append(control_cmd.thrust)
        results["torque_commands"].append(np.linalg.norm(control_cmd.torque))

    execution_time = time.time() - start_time

    # Convert lists to arrays
    for key in ["actual_pos", "desired_pos", "actual_vel", "desired_vel"]:
        results[key] = np.array(results[key])

    # Calculate performance metrics
    metrics = {
        "mean_position_error": np.mean(results["position_errors"]),
        "max_position_error": np.max(results["position_errors"]),
        "rms_position_error": np.sqrt(
            np.mean(np.array(results["position_errors"]) ** 2)
        ),
        "mean_velocity_error": np.mean(results["velocity_errors"]),
        "max_velocity_error": np.max(results["velocity_errors"]),
        "final_position_error": results["position_errors"][-1],
        "control_frequency_achieved": total_steps / execution_time,
        "execution_time": execution_time,
        "controller_metrics": controller.get_performance_metrics(),
    }

    print(f"✅ Test completed in {execution_time:.2f}s")
    print(f"   Achieved frequency: {metrics['control_frequency_achieved']:.1f}Hz")

    return results, metrics


def create_comparison_plot(results1, metrics1, results2, metrics2, labels):
    """Create comparison plots between two controller results."""

    fig = plt.figure(figsize=(18, 12))
    fig.suptitle(
        "Optimized vs Original Controller Performance Comparison",
        fontsize=16,
        fontweight="bold",
    )

    # 1. 3D Trajectory Plot
    ax = fig.add_subplot(2, 3, 1, projection="3d")
    ax.plot(
        results1["desired_pos"][:, 0],
        results1["desired_pos"][:, 1],
        results1["desired_pos"][:, 2],
        "k--",
        linewidth=2,
        label="Desired",
        alpha=0.8,
    )
    ax.plot(
        results1["actual_pos"][:, 0],
        results1["actual_pos"][:, 1],
        results1["actual_pos"][:, 2],
        "b-",
        linewidth=1.5,
        label=labels[0],
        alpha=0.8,
    )
    ax.plot(
        results2["actual_pos"][:, 0],
        results2["actual_pos"][:, 1],
        results2["actual_pos"][:, 2],
        "r-",
        linewidth=1.5,
        label=labels[1],
        alpha=0.8,
    )
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.set_title("3D Trajectory Tracking")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Create 2D subplot grid for remaining plots
    axes = []
    for i in range(2, 7):  # positions 2-6
        axes.append(fig.add_subplot(2, 3, i))

    # 2. Position Errors Over Time
    ax = axes[0]  # Second subplot (position 2)
    ax.plot(
        results1["time"],
        results1["position_errors"],
        "b-",
        label=labels[0],
        linewidth=1.5,
    )
    ax.plot(
        results2["time"],
        results2["position_errors"],
        "r-",
        label=labels[1],
        linewidth=1.5,
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Position Error (m)")
    ax.set_title("Position Tracking Error")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_yscale("log")

    # 3. Velocity Errors Over Time
    ax = axes[1]  # Third subplot (position 3)
    ax.plot(
        results1["time"],
        results1["velocity_errors"],
        "b-",
        label=labels[0],
        linewidth=1.5,
    )
    ax.plot(
        results2["time"],
        results2["velocity_errors"],
        "r-",
        label=labels[1],
        linewidth=1.5,
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Velocity Error (m/s)")
    ax.set_title("Velocity Tracking Error")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 4. Performance Metrics Comparison
    ax = axes[2]  # Fourth subplot (position 4)
    metrics_names = [
        "Mean Pos Error",
        "Max Pos Error",
        "RMS Pos Error",
        "Mean Vel Error",
    ]
    metrics1_values = [
        metrics1["mean_position_error"],
        metrics1["max_position_error"],
        metrics1["rms_position_error"],
        metrics1["mean_velocity_error"],
    ]
    metrics2_values = [
        metrics2["mean_position_error"],
        metrics2["max_position_error"],
        metrics2["rms_position_error"],
        metrics2["mean_velocity_error"],
    ]

    x = np.arange(len(metrics_names))
    width = 0.35

    bars1 = ax.bar(
        x - width / 2, metrics1_values, width, label=labels[0], color="blue", alpha=0.7
    )
    bars2 = ax.bar(
        x + width / 2, metrics2_values, width, label=labels[1], color="red", alpha=0.7
    )

    ax.set_ylabel("Error Magnitude")
    ax.set_title("Performance Metrics Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_names, rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + height * 0.01,
                f"{height:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    # 5. Control Commands
    ax = axes[3]  # Fifth subplot (position 5)
    ax.plot(
        results1["time"],
        results1["thrust_commands"],
        "b-",
        label=f"{labels[0]} Thrust",
        alpha=0.8,
    )
    ax.plot(
        results2["time"],
        results2["thrust_commands"],
        "r-",
        label=f"{labels[1]} Thrust",
        alpha=0.8,
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Thrust Command (N)")
    ax.set_title("Thrust Commands")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 6. Improvement Summary
    ax = axes[4]  # Sixth subplot (position 6)
    improvements = []
    improvement_names = []

    for metric_name, val1, val2 in zip(metrics_names, metrics1_values, metrics2_values):
        if val2 > 0:  # Avoid division by zero
            improvement = ((val2 - val1) / val2) * 100
            improvements.append(improvement)
            improvement_names.append(metric_name)

    colors = ["green" if x > 0 else "red" for x in improvements]
    bars = ax.bar(improvement_names, improvements, color=colors, alpha=0.7)
    ax.set_ylabel("Improvement (%)")
    ax.set_title(f"{labels[0]} vs {labels[1]}")
    ax.set_xticklabels(improvement_names, rotation=45)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="-", alpha=0.5)

    # Add value labels
    for bar, val in zip(bars, improvements):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            val + (1 if val > 0 else -1),
            f"{val:.1f}%",
            ha="center",
            va="bottom" if val > 0 else "top",
            fontweight="bold",
        )

    plt.tight_layout()
    plt.savefig("controller_optimization_comparison.png", dpi=300, bbox_inches="tight")
    plt.show()

    return fig


def main():
    """Run the controller optimization test."""

    print("🚀 CONTROLLER OPTIMIZATION TEST")
    print("=" * 50)

    # Create test trajectory
    print("📊 Generating challenging test trajectory...")
    trajectory = create_test_trajectory(duration=20.0)

    # Initialize simulator
    simulator = DroneSimulator()

    # Test original controller configuration (baseline)
    print("\n🔵 Testing ORIGINAL controller...")
    original_config = GeometricControllerConfig(
        kp_pos=np.array([5.0, 5.0, 5.0]),  # Original values
        ki_pos=np.array([0.0, 0.0, 0.0]),  # No integral
        kd_pos=np.array([3.0, 3.0, 3.0]),
        kp_att=np.array([8.0, 8.0, 4.0]),
        kd_att=np.array([2.5, 2.5, 1.0]),
        ff_pos=0.0,  # No feedforward
        ff_vel=0.0,
    )
    original_controller = GeometricController(original_config)
    results_original, metrics_original = test_controller_performance(
        original_controller, trajectory, simulator
    )

    # Test optimized controller
    print("\n🟢 Testing OPTIMIZED controller...")
    optimized_controller = GeometricController()  # Uses new default config
    results_optimized, metrics_optimized = test_controller_performance(
        optimized_controller, trajectory, simulator
    )

    # Print comparison results
    print(f"\n{'='*60}")
    print("📊 PERFORMANCE COMPARISON RESULTS")
    print("=" * 60)

    print(f"\n🔵 ORIGINAL Controller:")
    print(f"   Mean Position Error: {metrics_original['mean_position_error']:.3f}m")
    print(f"   Max Position Error:  {metrics_original['max_position_error']:.3f}m")
    print(f"   RMS Position Error:  {metrics_original['rms_position_error']:.3f}m")
    print(f"   Final Position Error: {metrics_original['final_position_error']:.3f}m")
    print(f"   Mean Velocity Error: {metrics_original['mean_velocity_error']:.3f}m/s")

    print(f"\n🟢 OPTIMIZED Controller:")
    print(f"   Mean Position Error: {metrics_optimized['mean_position_error']:.3f}m")
    print(f"   Max Position Error:  {metrics_optimized['max_position_error']:.3f}m")
    print(f"   RMS Position Error:  {metrics_optimized['rms_position_error']:.3f}m")
    print(f"   Final Position Error: {metrics_optimized['final_position_error']:.3f}m")
    print(f"   Mean Velocity Error: {metrics_optimized['mean_velocity_error']:.3f}m/s")

    # Calculate improvements
    pos_improvement = (
        (
            metrics_original["mean_position_error"]
            - metrics_optimized["mean_position_error"]
        )
        / metrics_original["mean_position_error"]
    ) * 100
    max_improvement = (
        (
            metrics_original["max_position_error"]
            - metrics_optimized["max_position_error"]
        )
        / metrics_original["max_position_error"]
    ) * 100
    vel_improvement = (
        (
            metrics_original["mean_velocity_error"]
            - metrics_optimized["mean_velocity_error"]
        )
        / metrics_original["mean_velocity_error"]
    ) * 100

    print(f"\n🎯 IMPROVEMENTS:")
    print(f"   Mean Position Error: {pos_improvement:+.1f}%")
    print(f"   Max Position Error:  {max_improvement:+.1f}%")
    print(f"   Mean Velocity Error: {vel_improvement:+.1f}%")

    # Create comparison plots
    print(f"\n📈 Creating comparison visualizations...")
    fig = create_comparison_plot(
        results_optimized,
        metrics_optimized,
        results_original,
        metrics_original,
        ["Optimized", "Original"],
    )

    print(f"\n{'='*60}")
    print("✅ OPTIMIZATION TEST COMPLETED!")
    print("=" * 60)
    print(f"📁 Results saved: controller_optimization_comparison.png")

    if pos_improvement > 30:
        print("🎉 EXCELLENT: >30% improvement achieved!")
    elif pos_improvement > 10:
        print("✅ GOOD: >10% improvement achieved!")
    elif pos_improvement > 0:
        print("👍 POSITIVE: Some improvement achieved!")
    else:
        print("⚠️  NO IMPROVEMENT: Consider different approach")

    return metrics_optimized, metrics_original


if __name__ == "__main__":
    main()
