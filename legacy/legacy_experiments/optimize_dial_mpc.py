#!/usr/bin/env python3
"""
DIAL-MPC Optimization for Better Trajectory Tracking
====================================================
Optimizes the DIAL-MPC planner based on the research showing 13.4x improvement
"""

import numpy as np
import sys
import os
import time
import matplotlib.pyplot as plt

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.planning.dial_mpc_planner import DIALMPCPlanner, DIALMPCConfig
from src.common.types import DroneState


def create_optimized_dial_mpc_config():
    """Create optimized DIAL-MPC configuration based on research findings."""

    print("🧠 Creating OPTIMIZED DIAL-MPC Configuration")
    print("=" * 50)

    # Based on DIAL-MPC paper findings:
    # - Longer prediction horizons improve performance
    # - Higher position tracking weight critical for accuracy
    # - More iterations needed for convergence

    optimized_config = DIALMPCConfig(
        # Longer prediction horizon for better optimization
        prediction_horizon=40,  # 4 seconds (was 20 = 2 seconds)
        dt=0.05,  # Higher frequency planning (50ms vs 100ms)
        # More aggressive but realistic physical constraints
        max_velocity=12.0,  # m/s (increased from 8.0)
        max_acceleration=6.0,  # m/s² (increased from 4.0)
        max_jerk=12.0,  # m/s³ (increased from 8.0)
        # OPTIMIZED cost function weights for tracking performance
        position_weight=100.0,  # 10x increase! (was 10.0)
        velocity_weight=10.0,  # 10x increase! (was 1.0)
        acceleration_weight=1.0,  # 10x increase! (was 0.1)
        jerk_weight=0.1,  # 10x increase! (was 0.01)
        # Obstacle avoidance (unchanged for now)
        obstacle_weight=100.0,
        safety_margin=1.0,
        # Enhanced smoothness
        smoothness_weight=5.0,  # 5x increase! (was 1.0)
    )

    print("📊 Configuration Improvements:")
    print(f"   Prediction Horizon: 20 → {optimized_config.prediction_horizon} steps")
    print(f"   Planning Frequency: 100ms → {optimized_config.dt*1000:.0f}ms")
    print(f"   Position Weight: 10.0 → {optimized_config.position_weight}")
    print(f"   Velocity Weight: 1.0 → {optimized_config.velocity_weight}")
    print(f"   Max Acceleration: 4.0 → {optimized_config.max_acceleration} m/s²")

    return optimized_config


def test_dial_mpc_optimization():
    """Test the DIAL-MPC optimization improvements."""

    print("🚀 TESTING DIAL-MPC OPTIMIZATION")
    print("=" * 50)

    # Create test scenario
    start_pos = np.array([0.0, 0.0, 2.0])
    goal_pos = np.array([10.0, 5.0, 3.0])

    current_state = DroneState(
        position=start_pos,
        velocity=np.array([1.0, 0.5, 0.0]),
        attitude=np.zeros(3),
        angular_velocity=np.zeros(3),
        timestamp=time.time(),
    )

    # Test original DIAL-MPC
    print("\n🔵 Testing ORIGINAL DIAL-MPC...")
    original_config = DIALMPCConfig()  # Default config
    original_planner = DIALMPCPlanner(original_config)

    start_time = time.time()
    original_trajectory = original_planner.plan_trajectory(current_state, goal_pos)
    original_time = time.time() - start_time

    # Test optimized DIAL-MPC
    print("\n🟢 Testing OPTIMIZED DIAL-MPC...")
    optimized_config = create_optimized_dial_mpc_config()
    optimized_planner = DIALMPCPlanner(optimized_config)

    start_time = time.time()
    optimized_trajectory = optimized_planner.plan_trajectory(current_state, goal_pos)
    optimized_time = time.time() - start_time

    # Analyze results
    print(f"\n{'='*50}")
    print("📊 DIAL-MPC OPTIMIZATION RESULTS")
    print("=" * 50)

    # Planning time comparison
    print(f"\n⏱️  Planning Time:")
    print(f"   Original: {original_time*1000:.1f}ms")
    print(f"   Optimized: {optimized_time*1000:.1f}ms")
    print(f"   Ratio: {optimized_time/original_time:.1f}x")

    # Trajectory quality comparison
    def analyze_trajectory(traj, name):
        if traj is None or traj.positions is None:
            return None

        # Goal reaching accuracy
        final_error = np.linalg.norm(traj.positions[-1] - goal_pos)

        # Path efficiency (total distance vs direct distance)
        total_distance = np.sum(np.linalg.norm(np.diff(traj.positions, axis=0), axis=1))
        direct_distance = np.linalg.norm(goal_pos - start_pos)
        efficiency = direct_distance / total_distance if total_distance > 0 else 0

        return {
            "final_error": final_error,
            "path_efficiency": efficiency,
            "trajectory_length": len(traj.positions),
        }

    original_analysis = analyze_trajectory(original_trajectory, "Original")
    optimized_analysis = analyze_trajectory(optimized_trajectory, "Optimized")

    if original_analysis and optimized_analysis:
        print(f"\n🎯 Trajectory Quality:")
        print(
            f"   Final Error: {original_analysis['final_error']:.3f}m → {optimized_analysis['final_error']:.3f}m"
        )
        print(
            f"   Path Efficiency: {original_analysis['path_efficiency']:.3f} → {optimized_analysis['path_efficiency']:.3f}"
        )
        print(
            f"   Trajectory Length: {original_analysis['trajectory_length']} → {optimized_analysis['trajectory_length']}"
        )

        # Calculate improvements
        error_improvement = (
            (original_analysis["final_error"] - optimized_analysis["final_error"])
            / original_analysis["final_error"]
        ) * 100
        efficiency_improvement = (
            (
                optimized_analysis["path_efficiency"]
                - original_analysis["path_efficiency"]
            )
            / original_analysis["path_efficiency"]
        ) * 100

        print(f"\n🎉 IMPROVEMENTS:")
        print(f"   Final Error: {error_improvement:+.1f}%")
        print(f"   Path Efficiency: {efficiency_improvement:+.1f}%")

    return optimized_config, optimized_analysis, original_analysis


def main():
    """Run the complete DIAL-MPC optimization test."""

    print("🎯 DIAL-MPC OPTIMIZATION FOR BETTER TRACKING")
    print("=" * 55)
    print("Based on research showing 13.4x tracking improvement")

    optimized_config, opt_analysis, orig_analysis = test_dial_mpc_optimization()

    print(f"\n{'='*55}")
    print("🎯 RECOMMENDATION")
    print("=" * 55)

    if opt_analysis and orig_analysis:
        error_improvement = (
            (orig_analysis["final_error"] - opt_analysis["final_error"])
            / orig_analysis["final_error"]
        ) * 100

        if error_improvement > 50:
            print("🎉 EXCELLENT: >50% improvement in trajectory accuracy!")
            print("✅ Apply optimized DIAL-MPC configuration to your system")
        elif error_improvement > 20:
            print("✅ GOOD: >20% improvement achieved!")
            print("👍 Optimized DIAL-MPC shows clear benefits")
        elif error_improvement > 0:
            print("👍 POSITIVE: Some improvement in trajectory planning")
        else:
            print("⚠️  Mixed results - may need further tuning")

    print(f"\n🔧 Next Steps:")
    print(f"1. Update src/planning/dial_mpc_planner.py with optimized config")
    print(f"2. Test the complete 3-layer system")
    print(f"3. Expect significantly better tracking performance")
    print(f"4. Fine-tune based on results")


if __name__ == "__main__":
    main()
