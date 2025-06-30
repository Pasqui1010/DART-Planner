#!/usr/bin/env python3
"""
System Verification and Visualization Script
"""

import os
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

print("🚀 Starting System Verification")
print("=" * 50)


def check_component_imports():
    """Check if all components can be imported."""
    print("🔧 Checking component imports...")

    results = {}

    # Add src to path
    sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

    try:
        from src.utils.drone_simulator import DroneSimulator

        results["DroneSimulator"] = "✅ Pass"
        print("  ✅ DroneSimulator: Pass")
    except Exception as e:
        results["DroneSimulator"] = f"❌ Fail: {str(e)}"
        print(f"  ❌ DroneSimulator: Fail - {e}")

    try:
        from src.control.geometric_controller import GeometricController

        results["GeometricController"] = "✅ Pass"
        print("  ✅ GeometricController: Pass")
    except Exception as e:
        results["GeometricController"] = f"❌ Fail: {str(e)}"
        print(f"  ❌ GeometricController: Fail - {e}")

    try:
        from src.planning.dial_mpc_planner import DIALMPCPlanner

        results["DIALMPCPlanner"] = "✅ Pass"
        print("  ✅ DIALMPCPlanner: Pass")
    except Exception as e:
        results["DIALMPCPlanner"] = f"❌ Fail: {str(e)}"
        print(f"  ❌ DIALMPCPlanner: Fail - {e}")

    return results


def analyze_latest_log():
    """Analyze the most recent trajectory log."""
    print("\n📋 Analyzing latest trajectory log...")

    log_files = list(Path(".").glob("*trajectory_log_*.csv"))
    if not log_files:
        print("  ❌ No trajectory log files found")
        return None

    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
    print(f"  📄 Latest log: {latest_log}")

    try:
        df = pd.read_csv(latest_log)

        # Handle different time column names
        time_col = "timestamp" if "timestamp" in df.columns else "time"

        if time_col in df.columns:
            duration = df[time_col].iloc[-1] - df[time_col].iloc[0]
            control_freq = len(df) / duration

            print(f"  ⏱️  Duration: {duration:.2f}s")
            print(f"  🔄 Frequency: {control_freq:.1f}Hz")
            print(f"  📊 Data points: {len(df)}")

            return {
                "dataframe": df,
                "duration": duration,
                "frequency": control_freq,
                "filename": latest_log,
                "time_column": time_col,
            }
        else:
            print(f"  ❌ No time column found in log")
            return None

    except Exception as e:
        print(f"  ❌ Error analyzing log: {e}")
        return None


def create_status_visualization(component_results, log_data):
    """Create system status visualization."""
    print("\n🎨 Creating system status visualization...")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

    # 1. Component Status
    components = list(component_results.keys())
    statuses = [1 if "✅" in status else 0 for status in component_results.values()]
    colors = ["green" if status == 1 else "red" for status in statuses]

    bars = ax1.bar(components, statuses, color=colors, alpha=0.7)
    ax1.set_ylim(0, 1.2)
    ax1.set_ylabel("Status")
    ax1.set_title("Component Status", fontweight="bold")
    ax1.tick_params(axis="x", rotation=45)

    for i, status in enumerate(statuses):
        text = "✅ PASS" if status == 1 else "❌ FAIL"
        ax1.text(i, 0.5, text, ha="center", va="center", fontweight="bold")

    # 2. Log Analysis
    if log_data:
        df = log_data["dataframe"]

        # Check if we have position data
        time_col = log_data.get("time_column", "time")
        if "actual_x" in df.columns and "desired_x" in df.columns:
            pos_errors = np.sqrt(
                (df["actual_x"] - df["desired_x"]) ** 2
                + (df["actual_y"] - df["desired_y"]) ** 2
                + (df["actual_z"] - df["desired_z"]) ** 2
            )

            ax2.plot(df[time_col], pos_errors, linewidth=2, color="blue")
            ax2.set_xlabel("Time (s)")
            ax2.set_ylabel("Position Error (m)")
            ax2.set_title("Position Tracking Error", fontweight="bold")
            ax2.grid(True, alpha=0.3)

            # Add statistics
            mean_error = pos_errors.mean()
            max_error = pos_errors.max()
            ax2.text(
                0.02,
                0.98,
                f"Mean: {mean_error:.3f}m\nMax: {max_error:.3f}m",
                transform=ax2.transAxes,
                va="top",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
            )
        else:
            ax2.text(
                0.5,
                0.5,
                "No position tracking data",
                ha="center",
                va="center",
                transform=ax2.transAxes,
            )
            ax2.set_title("Position Tracking (No Data)", fontweight="bold")
    else:
        ax2.text(
            0.5,
            0.5,
            "No log data available",
            ha="center",
            va="center",
            transform=ax2.transAxes,
        )
        ax2.set_title("Log Analysis (No Data)", fontweight="bold")

    # 3. Velocity Analysis
    if log_data and "actual_vx" in log_data["dataframe"].columns:
        df = log_data["dataframe"]
        time_col = log_data.get("time_column", "time")
        velocities = np.sqrt(
            df["actual_vx"] ** 2 + df["actual_vy"] ** 2 + df["actual_vz"] ** 2
        )

        ax3.plot(df[time_col], velocities, linewidth=2, color="green")
        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("Velocity (m/s)")
        ax3.set_title("Velocity Profile", fontweight="bold")
        ax3.grid(True, alpha=0.3)

        mean_vel = velocities.mean()
        max_vel = velocities.max()
        ax3.text(
            0.02,
            0.98,
            f"Mean: {mean_vel:.2f}m/s\nMax: {max_vel:.2f}m/s",
            transform=ax3.transAxes,
            va="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )
    else:
        ax3.text(
            0.5,
            0.5,
            "No velocity data available",
            ha="center",
            va="center",
            transform=ax3.transAxes,
        )
        ax3.set_title("Velocity Profile (No Data)", fontweight="bold")

    # 4. System Summary
    ax4.axis("off")

    # Create summary text
    summary = "SYSTEM STATUS SUMMARY\n" + "=" * 25 + "\n\n"

    # Component status
    all_pass = all("✅" in status for status in component_results.values())
    summary += (
        f"🔧 Components: {'✅ ALL OPERATIONAL' if all_pass else '❌ ISSUES DETECTED'}\n\n"
    )

    for comp, status in component_results.items():
        summary += f"  • {comp}: {'✅' if '✅' in status else '❌'}\n"

    # Log status
    if log_data:
        summary += f"\n📋 Latest Log Analysis:\n"
        summary += f"  • Duration: {log_data['duration']:.1f}s\n"
        summary += f"  • Frequency: {log_data['frequency']:.1f}Hz\n"
        summary += f"  • Data points: {len(log_data['dataframe'])}\n"
    else:
        summary += f"\n📋 Log Analysis: ❌ No data\n"

    # Overall status
    summary += f"\n{'='*25}\n"
    overall_ok = all_pass and (log_data is not None)
    summary += f"🎯 Overall: {'✅ SYSTEM READY' if overall_ok else '⚠️ ATTENTION NEEDED'}"

    ax4.text(
        0.05,
        0.95,
        summary,
        transform=ax4.transAxes,
        fontsize=11,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.3),
    )

    plt.suptitle("Drone Control System - Status Report", fontsize=16, fontweight="bold")
    plt.tight_layout()

    # Save the plot
    timestamp = int(time.time())
    output_file = f"system_status_report_{timestamp}.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"  💾 Status report saved: {output_file}")

    return output_file


def main():
    """Main verification function."""

    # 1. Check component imports
    component_results = check_component_imports()

    # 2. Analyze latest log
    log_data = analyze_latest_log()

    # 3. Create visualization
    output_file = create_status_visualization(component_results, log_data)

    print("\n" + "=" * 50)
    print("🎉 System Verification Complete!")

    # Print final summary
    all_components_ok = all("✅" in status for status in component_results.values())
    print(f"\n📋 FINAL SUMMARY:")
    print(
        f"  🔧 Components: {'✅ All functional' if all_components_ok else '❌ Issues detected'}"
    )
    print(
        f"  📊 Data Analysis: {'✅ Recent logs found' if log_data else '❌ No recent data'}"
    )
    print(f"  🎨 Visualization: ✅ {output_file}")

    overall_status = all_components_ok and (log_data is not None)
    print(
        f"\n🎯 SYSTEM STATUS: {'✅ OPERATIONAL' if overall_status else '⚠️ NEEDS ATTENTION'}"
    )


if __name__ == "__main__":
    main()
