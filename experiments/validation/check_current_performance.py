#!/usr/bin/env python3
"""
Quick Performance Check After Phase 1 Optimizations
Measures key metrics to evaluate controller improvements
"""

import numpy as np
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from utils.drone_simulator import DroneSimulator
from control.geometric_controller import GeometricController
from planning.dial_mpc_planner import DIALMPCPlanner
from planning.global_mission_planner import GlobalMissionPlanner
from common.types import State, Control, Trajectory, TrajectoryPoint
from utils.pid_controller import PIDController


def run_performance_test():
    """Run a quick performance test to evaluate current system"""

    print("🔍 Phase 1 Performance Evaluation")
    print("=" * 60)

    # Initialize components
    drone = DroneSimulator()
    controller = GeometricController()
    planner = DIALMPCPlanner()
    mission_planner = GlobalMissionPlanner()

    # Test parameters
    test_duration = 30.0  # seconds
    dt = 0.001  # 1kHz control loop

    # Define test trajectory (circular path)
    radius = 5.0
    period = 20.0
    center = np.array([0.0, 0.0, 5.0])

    # Storage for metrics
    position_errors = []
    velocity_errors = []
    control_signals = []
    timestamps = []

    print(f"📊 Running {test_duration}s test with circular trajectory (R={radius}m)")
    print(f"🎯 Target: <30m position error (Phase 1 goal)")

    # Initialize state
    current_state = State()
    current_state.position = np.array([radius, 0.0, 5.0])
    current_state.velocity = np.array([0.0, 0.0, 0.0])
    current_state.attitude = np.array([1.0, 0.0, 0.0, 0.0])  # quaternion
    current_state.angular_velocity = np.array([0.0, 0.0, 0.0])

    start_time = time.time()
    t = 0.0

    while t < test_duration:
        # Generate desired trajectory point
        angle = 2 * np.pi * t / period
        desired_pos = center + radius * np.array([np.cos(angle), np.sin(angle), 0])
        desired_vel = (
            radius * 2 * np.pi / period * np.array([-np.sin(angle), np.cos(angle), 0])
        )
        desired_acc = (
            radius
            * (2 * np.pi / period) ** 2
            * np.array([-np.cos(angle), -np.sin(angle), 0])
        )

        # Desired trajectory point
        traj_point = TrajectoryPoint()
        traj_point.position = desired_pos
        traj_point.velocity = desired_vel
        traj_point.acceleration = desired_acc
        traj_point.yaw = angle
        traj_point.timestamp = t

        # Compute control
        control = controller.compute_control(current_state, traj_point)

        # Simulate drone dynamics
        current_state = drone.step(control, dt)

        # Record metrics
        pos_error = np.linalg.norm(current_state.position - desired_pos)
        vel_error = np.linalg.norm(current_state.velocity - desired_vel)

        position_errors.append(pos_error)
        velocity_errors.append(vel_error)
        control_signals.append(np.linalg.norm(control.thrust))
        timestamps.append(t)

        t += dt

        # Progress indicator
        if int(t * 10) % 50 == 0:  # Every 5 seconds
            print(f"⏱️  {t:.1f}s - Position Error: {pos_error:.2f}m")

    # Analyze results
    print("\n📈 PERFORMANCE ANALYSIS")
    print("=" * 60)

    pos_errors = np.array(position_errors)
    vel_errors = np.array(velocity_errors)
    control_signals = np.array(control_signals)

    # Key metrics
    mean_pos_error = np.mean(pos_errors)
    max_pos_error = np.max(pos_errors)
    steady_state_error = np.mean(pos_errors[-int(0.3 * len(pos_errors)) :])  # Last 30%

    print(f"📏 Position Tracking:")
    print(f"   Mean Error: {mean_pos_error:.2f}m")
    print(f"   Max Error:  {max_pos_error:.2f}m")
    print(f"   Steady State: {steady_state_error:.2f}m")

    print(f"\n🎯 Phase 1 Assessment:")
    if mean_pos_error < 30.0:
        print(f"   ✅ SUCCESS: {mean_pos_error:.2f}m < 30m target")
        improvement = (67.02 - mean_pos_error) / 67.02 * 100
        print(f"   📈 Improvement: {improvement:.1f}% from baseline (67.02m)")

        if mean_pos_error < 15.0:
            print(f"   🎉 EXCELLENT: Already exceeding Phase 2 target!")

        print(f"\n🔄 Ready for Phase 2: DIAL-MPC Parameter Tuning")

    else:
        print(f"   ⚠️  NEEDS WORK: {mean_pos_error:.2f}m > 30m target")
        print(f"   🔧 Recommend: Further controller tuning needed")

    print(f"\n🚀 Velocity Tracking:")
    print(f"   Mean Error: {np.mean(vel_errors):.2f}m/s")
    print(f"   Max Error:  {np.max(vel_errors):.2f}m/s")

    print(f"\n⚡ Control Performance:")
    print(f"   Mean Thrust: {np.mean(control_signals):.2f}N")
    print(f"   Max Thrust:  {np.max(control_signals):.2f}N")

    # Save results
    timestamp = int(time.time())
    results_file = f"phase1_results_{timestamp}.csv"

    with open(results_file, "w") as f:
        f.write("time,position_error,velocity_error,thrust\n")
        for i, t in enumerate(timestamps):
            f.write(
                f"{t:.3f},{position_errors[i]:.6f},{velocity_errors[i]:.6f},{control_signals[i]:.6f}\n"
            )

    print(f"\n💾 Results saved to: {results_file}")

    return mean_pos_error, max_pos_error, steady_state_error


if __name__ == "__main__":
    run_performance_test()
