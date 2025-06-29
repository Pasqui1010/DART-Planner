import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import glob
import os


def create_before_after_comparison():
    """Create a side-by-side comparison of original vs improved system"""

    # Find log files
    improved_files = glob.glob("improved_trajectory_log_*.csv")
    original_files = glob.glob("trajectory_log_*.csv")
    original_files = [f for f in original_files if not f.startswith("improved_")]

    if not improved_files or not original_files:
        print("Missing log files for comparison!")
        return

    # Get latest files
    latest_improved = max(improved_files, key=os.path.getctime)
    latest_original = max(original_files, key=os.path.getctime)

    # Load data
    try:
        improved_data = pd.read_csv(latest_improved)
        original_data = pd.read_csv(latest_original)
        print(f"Loaded data:")
        print(f"  Original: {len(original_data)} points from {latest_original}")
        print(f"  Improved: {len(improved_data)} points from {latest_improved}")
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Calculate errors for both systems
    def calculate_errors(data, is_improved=False):
        target_x = "desired_x" if is_improved else "target_x"
        target_y = "desired_y" if is_improved else "target_y"
        target_z = "desired_z" if is_improved else "target_z"

        error_x = data["actual_x"] - data[target_x]
        error_y = data["actual_y"] - data[target_y]
        error_z = data["actual_z"] - data[target_z]
        total_error = np.sqrt(error_x**2 + error_y**2 + error_z**2)

        time_rel = data["timestamp"] - data["timestamp"].iloc[0]
        dt = np.diff(data["timestamp"])
        freq = 1.0 / dt

        return {
            "time": time_rel,
            "error": total_error,
            "freq": freq,
            "mean_error": np.mean(total_error),
            "max_error": np.max(total_error),
            "mean_freq": np.mean(freq),
        }

    original_metrics = calculate_errors(original_data, False)
    improved_metrics = calculate_errors(improved_data, True)

    # Create comparison figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(
        "🚁 DRONE CONTROL SYSTEM: BEFORE vs AFTER COMPARISON",
        fontsize=16,
        fontweight="bold",
        y=0.95,
    )

    # Position Error Comparison
    ax1 = axes[0, 0]
    ax1.plot(
        original_metrics["time"],
        original_metrics["error"],
        color="#E74C3C",
        linewidth=2,
        label="Original System",
        alpha=0.8,
    )
    ax1.fill_between(
        original_metrics["time"],
        0,
        original_metrics["error"],
        alpha=0.3,
        color="#E74C3C",
    )

    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Position Error (m)")
    ax1.set_title("📉 ORIGINAL SYSTEM\nPosition Error Over Time", fontweight="bold")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Add statistics text
    stats_text = f"Mean Error: {original_metrics['mean_error']:.1f}m\nMax Error: {original_metrics['max_error']:.1f}m"
    ax1.text(
        0.02,
        0.98,
        stats_text,
        transform=ax1.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    ax2 = axes[0, 1]
    ax2.plot(
        improved_metrics["time"],
        improved_metrics["error"],
        color="#27AE60",
        linewidth=2,
        label="Improved System",
        alpha=0.8,
    )
    ax2.fill_between(
        improved_metrics["time"],
        0,
        improved_metrics["error"],
        alpha=0.3,
        color="#27AE60",
    )

    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Position Error (m)")
    ax2.set_title("📈 IMPROVED SYSTEM\nPosition Error Over Time", fontweight="bold")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Add statistics text
    improvement_factor = original_metrics["mean_error"] / improved_metrics["mean_error"]
    stats_text = f"Mean Error: {improved_metrics['mean_error']:.1f}m\nMax Error: {improved_metrics['max_error']:.1f}m\n{improvement_factor:.1f}x BETTER! 🎉"
    ax2.text(
        0.02,
        0.98,
        stats_text,
        transform=ax2.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.8),
    )

    # Control Frequency Comparison
    ax3 = axes[1, 0]
    freq_clean_orig = original_metrics["freq"][
        original_metrics["freq"] <= np.percentile(original_metrics["freq"], 95)
    ]
    ax3.hist(freq_clean_orig, bins=20, alpha=0.7, color="#E74C3C", edgecolor="black")
    ax3.axvline(
        original_metrics["mean_freq"],
        color="darkred",
        linestyle="--",
        linewidth=2,
        label=f'Mean: {original_metrics["mean_freq"]:.0f} Hz',
    )

    ax3.set_xlabel("Control Frequency (Hz)")
    ax3.set_ylabel("Count")
    ax3.set_title(
        "⏱️ ORIGINAL SYSTEM\nControl Frequency Distribution", fontweight="bold"
    )
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    ax4 = axes[1, 1]
    freq_clean_imp = improved_metrics["freq"][
        improved_metrics["freq"] <= np.percentile(improved_metrics["freq"], 95)
    ]
    ax4.hist(freq_clean_imp, bins=30, alpha=0.7, color="#27AE60", edgecolor="black")
    ax4.axvline(
        improved_metrics["mean_freq"],
        color="darkgreen",
        linestyle="--",
        linewidth=2,
        label=f'Mean: {improved_metrics["mean_freq"]:.0f} Hz',
    )

    freq_improvement = improved_metrics["mean_freq"] / original_metrics["mean_freq"]
    ax4.text(
        0.02,
        0.98,
        f"{freq_improvement:.1f}x FASTER! ⚡",
        transform=ax4.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.8),
        fontsize=12,
        fontweight="bold",
    )

    ax4.set_xlabel("Control Frequency (Hz)")
    ax4.set_ylabel("Count")
    ax4.set_title(
        "⚡ IMPROVED SYSTEM\nControl Frequency Distribution", fontweight="bold"
    )
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save comparison
    output_file = "before_after_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"Before/After comparison saved to: {output_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("🎯 TRANSFORMATION SUMMARY")
    print("=" * 60)
    print(f"📏 Position Tracking:")
    print(f"   Before: {original_metrics['mean_error']:.1f}m mean error")
    print(f"   After:  {improved_metrics['mean_error']:.1f}m mean error")
    print(f"   Improvement: {improvement_factor:.1f}x better! 🎉")

    print(f"\n⚡ Control Performance:")
    print(f"   Before: {original_metrics['mean_freq']:.0f} Hz average")
    print(f"   After:  {improved_metrics['mean_freq']:.0f} Hz average")
    print(f"   Improvement: {freq_improvement:.1f}x faster! ⚡")

    print(f"\n🏗️ Architecture Changes:")
    print(f"   ✅ Proper distributed architecture (Cloud + Edge)")
    print(f"   ✅ Geometric control instead of simple PID")
    print(f"   ✅ Trajectory smoothing for continuous motion")
    print(f"   ✅ Enhanced logging and safety monitoring")
    print(f"   ✅ Training-free DIAL-MPC maintained")

    plt.show()


if __name__ == "__main__":
    create_before_after_comparison()
