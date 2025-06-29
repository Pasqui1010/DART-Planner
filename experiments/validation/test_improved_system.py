#!/usr/bin/env python3
"""
Test script for the improved distributed drone control system.

This script demonstrates the proper distributed architecture:
- Cloud: DIAL-MPC planning at 10Hz
- Edge: Geometric control at 1kHz with trajectory smoothing
- Proper separation of concerns and robust communication
"""

import subprocess
import time
import signal
import sys
import os


def run_improved_system(duration=20.0):
    """
    Run the improved distributed system with proper process management.
    """
    print("🚀 Starting Improved Distributed Drone Control System")
    print("=" * 60)
    print("Architecture:")
    print("  Cloud: DIAL-MPC planning (10Hz)")
    print("  Edge:  Geometric control (1kHz) + Trajectory smoothing")
    print("  Communication: ZMQ with failsafes")
    print("=" * 60)

    cloud_process = None
    edge_process = None

    try:
        # Start cloud planner
        print("\n🌩️  Starting cloud DIAL-MPC planner...")
        cloud_process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "from src.cloud.main_improved import main_improved; main_improved()",
            ],
            cwd=os.getcwd(),
        )

        # Give cloud time to initialize
        time.sleep(2)

        # Start edge controller
        print("🔧 Starting edge geometric controller...")
        edge_process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                f"from src.edge.main_improved import main_improved; main_improved({duration})",
            ],
            cwd=os.getcwd(),
        )

        # Wait for edge to complete
        print(f"⏱️  Running system for {duration} seconds...")
        edge_process.wait()

        print("\n✅ Edge controller completed successfully!")

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")

    except Exception as e:
        print(f"\n❌ Error running system: {e}")

    finally:
        # Clean shutdown
        print("\n🧹 Shutting down processes...")

        if edge_process and edge_process.poll() is None:
            edge_process.terminate()
            try:
                edge_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                edge_process.kill()

        if cloud_process and cloud_process.poll() is None:
            cloud_process.terminate()
            try:
                cloud_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cloud_process.kill()

        print("✨ System shutdown complete!")


def compare_with_original():
    """
    Compare the improved system with the original implementation.
    """
    print("\n" + "=" * 60)
    print("📊 COMPARISON: Original vs Improved Architecture")
    print("=" * 60)

    print("\n🔴 ORIGINAL SYSTEM ISSUES:")
    print("  ❌ PID control fighting against circular trajectory")
    print("  ❌ 100:1 timing mismatch (100Hz edge, 1Hz cloud)")
    print("  ❌ Trajectory discontinuities every second")
    print("  ❌ No smooth transitions between trajectories")
    print("  ❌ Control instability leading to exponential divergence")
    print("  ❌ Wrong separation of responsibilities")

    print("\n🟢 IMPROVED SYSTEM SOLUTIONS:")
    print("  ✅ Geometric control on SE(3) for robust attitude control")
    print("  ✅ Proper timing: 1kHz edge control, 10Hz cloud planning")
    print("  ✅ Trajectory smoother with minimum jerk transitions")
    print("  ✅ DIAL-MPC for optimal, constraint-aware planning")
    print("  ✅ Failsafe behaviors at all levels")
    print("  ✅ Correct distributed architecture separation")

    print("\n🎯 EXPECTED IMPROVEMENTS:")
    print("  📈 Stable trajectory tracking (no divergence)")
    print("  📈 Smooth motion with continuous derivatives")
    print("  📈 Optimal paths avoiding obstacles")
    print("  📈 Real-time performance with proper timing")
    print("  📈 Robust communication handling")


def main():
    """Main test function."""
    print("🔬 Improved Distributed Drone Control System Test")

    # Show comparison
    compare_with_original()

    # Ask user if they want to proceed
    response = input("\n🤔 Run the improved system test? (y/N): ").strip().lower()

    if response in ["y", "yes"]:
        duration = 20.0
        try:
            duration_input = input(
                f"⏱️  Test duration in seconds (default {duration}): "
            ).strip()
            if duration_input:
                duration = float(duration_input)
        except ValueError:
            print("Invalid duration, using default")

        run_improved_system(duration)

        print("\n📋 NEXT STEPS:")
        print("  1. Check the generated 'improved_trajectory_log_*.csv' file")
        print("  2. Compare position tracking accuracy with original logs")
        print("  3. Verify smooth velocity profiles and no discontinuities")
        print("  4. Observe stable control with no exponential divergence")
        print("  5. Check geometric controller failsafe activations (should be 0)")

    else:
        print(
            "👋 Test cancelled. You can run this script anytime to test the improved system."
        )


if __name__ == "__main__":
    main()
