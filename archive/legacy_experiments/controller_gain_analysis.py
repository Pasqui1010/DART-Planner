#!/usr/bin/env python3
"""
Controller Gain Analysis and Tuning Recommendations
===================================================
Systematic analysis of the geometric controller to identify and fix gain issues
causing large position tracking errors (67m).
"""

import matplotlib.pyplot as plt
import numpy as np

from dart_planner.control.control_config import default_control_config
from dart_planner.control.geometric_controller import GeometricControllerConfig


class ControllerGainAnalysis:
    """Analyze controller gains and provide tuning recommendations."""

    def __init__(self):
        self.geometric_config = GeometricControllerConfig()
        self.legacy_config = default_control_config

    def analyze_current_configuration(self):
        """Analyze the current controller configuration issues."""

        print("🔍 CONTROLLER GAIN ANALYSIS")
        print("=" * 60)

        print("\n📊 Current Configuration Comparison:")
        print("-" * 40)

        # Compare the two configurations
        print("Configuration Sources Found:")
        print("1. GeometricController internal config (ACTIVE)")
        print("2. control_config.py (LEGACY/UNUSED)")

        print(f"\n📈 Position Control Gains:")
        print(f"   Geometric Config - Kp: {self.geometric_config.kp_pos}")
        print(f"   Geometric Config - Ki: {self.geometric_config.ki_pos}")
        print(f"   Geometric Config - Kd: {self.geometric_config.kd_pos}")
        print(
            f"   Legacy Config - Kp: [{self.legacy_config.pos_x.Kp}, {self.legacy_config.pos_y.Kp}, {self.legacy_config.pos_z.Kp}]"
        )
        print(
            f"   Legacy Config - Ki: [{self.legacy_config.pos_x.Ki}, {self.legacy_config.pos_y.Ki}, {self.legacy_config.pos_z.Ki}]"
        )
        print(
            f"   Legacy Config - Kd: [{self.legacy_config.pos_x.Kd}, {self.legacy_config.pos_y.Kd}, {self.legacy_config.pos_z.Kd}]"
        )

        print(f"\n🎯 Attitude Control Gains:")
        print(f"   Geometric Config - Kp: {self.geometric_config.kp_att}")
        print(f"   Geometric Config - Kd: {self.geometric_config.kd_att}")
        print(
            f"   Legacy Config - Kp: [{self.legacy_config.roll.Kp}, {self.legacy_config.pitch.Kp}, {self.legacy_config.yaw_rate.Kp}]"
        )
        print(
            f"   Legacy Config - Kd: [{self.legacy_config.roll.Kd}, {self.legacy_config.pitch.Kd}, {self.legacy_config.yaw_rate.Kd}]"
        )

        # Analyze gain ratios
        self._analyze_gain_ratios()

        # Identify potential issues
        self._identify_issues()

        # Provide recommendations
        self._provide_recommendations()

    def _analyze_gain_ratios(self):
        """Analyze gain ratios and balance."""

        print(f"\n⚖️ Gain Ratio Analysis:")
        print("-" * 30)

        # Position control analysis
        kp_pos = self.geometric_config.kp_pos
        ki_pos = self.geometric_config.ki_pos
        kd_pos = self.geometric_config.kd_pos

        print(f"Position Control Ratios:")
        for axis, label in enumerate(["X", "Y", "Z"]):
            kp = kp_pos[axis]
            ki = ki_pos[axis]
            kd = kd_pos[axis]

            # Standard PID tuning ratios
            ki_kp_ratio = ki / kp if kp > 0 else 0
            kd_kp_ratio = kd / kp if kp > 0 else 0

            print(
                f"   {label}-axis: Kp={kp:.1f}, Ki/Kp={ki_kp_ratio:.2f}, Kd/Kp={kd_kp_ratio:.2f}"
            )

            # Check for common tuning issues
            if ki_kp_ratio > 0.3:
                print(f"      ⚠️  High integral gain ratio - may cause instability")
            if kd_kp_ratio > 1.0:
                print(
                    f"      ⚠️  High derivative gain ratio - may cause noise sensitivity"
                )
            if kp < 1.0:
                print(f"      ⚠️  Low proportional gain - poor tracking response")

        # Attitude control analysis
        kp_att = self.geometric_config.kp_att
        kd_att = self.geometric_config.kd_att

        print(f"\nAttitude Control Ratios:")
        for axis, label in enumerate(["Roll", "Pitch", "Yaw"]):
            kp = kp_att[axis]
            kd = kd_att[axis]
            kd_kp_ratio = kd / kp if kp > 0 else 0

            print(f"   {label}: Kp={kp:.1f}, Kd/Kp={kd_kp_ratio:.2f}")

    def _identify_issues(self):
        """Identify specific issues causing poor tracking."""

        print(f"\n🚨 IDENTIFIED ISSUES:")
        print("-" * 25)

        issues = []

        # Check position gains
        kp_pos = self.geometric_config.kp_pos
        if np.any(kp_pos < 5.0):
            issues.append(
                {
                    "issue": "Low Position Proportional Gains",
                    "details": f"Kp_pos = {kp_pos}, recommended > 8.0 for each axis",
                    "impact": "Poor position tracking, large steady-state errors",
                    "severity": "HIGH",
                }
            )

        # Check gain consistency
        config_mismatch = (
            abs(self.geometric_config.kp_pos[0] - self.legacy_config.pos_x.Kp) > 1.0
        )
        if config_mismatch:
            issues.append(
                {
                    "issue": "Configuration Inconsistency",
                    "details": "Two different control configs exist with conflicting gains",
                    "impact": "Unclear which gains are actually being used",
                    "severity": "MEDIUM",
                }
            )

        # Check feedforward gains
        if self.geometric_config.ff_pos < 0.5:
            issues.append(
                {
                    "issue": "Low Feedforward Gains",
                    "details": f"ff_pos = {self.geometric_config.ff_pos}, ff_vel = {self.geometric_config.ff_vel}",
                    "impact": "Sluggish response to trajectory changes",
                    "severity": "MEDIUM",
                }
            )

        # Check integral windup protection
        if self.geometric_config.max_integral_pos > 10.0:
            issues.append(
                {
                    "issue": "High Integral Limits",
                    "details": f"max_integral_pos = {self.geometric_config.max_integral_pos}",
                    "impact": "Potential integral windup during large errors",
                    "severity": "LOW",
                }
            )

        # Print issues
        for i, issue in enumerate(issues, 1):
            severity_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[issue["severity"]]
            print(f"\n{i}. {severity_emoji} {issue['issue']} ({issue['severity']})")
            print(f"   Details: {issue['details']}")
            print(f"   Impact: {issue['impact']}")

        if not issues:
            print("✅ No obvious configuration issues detected")

        return issues

    def _provide_recommendations(self):
        """Provide specific tuning recommendations."""

        print(f"\n🎯 TUNING RECOMMENDATIONS:")
        print("-" * 30)

        recommendations = [
            {
                "priority": 1,
                "change": "Increase Position Proportional Gains",
                "current": f"Kp = {self.geometric_config.kp_pos}",
                "recommended": "Kp = [10.0, 10.0, 12.0]",
                "reason": "Higher gains for better tracking, especially Z-axis for altitude hold",
                "expected_improvement": "40-60% error reduction",
            },
            {
                "priority": 2,
                "change": "Reduce Integral Gains",
                "current": f"Ki = {self.geometric_config.ki_pos}",
                "recommended": "Ki = [0.5, 0.5, 1.0]",
                "reason": "Prevent integral windup while maintaining steady-state accuracy",
                "expected_improvement": "15-25% stability improvement",
            },
            {
                "priority": 3,
                "change": "Increase Derivative Gains",
                "current": f"Kd = {self.geometric_config.kd_pos}",
                "recommended": "Kd = [6.0, 6.0, 8.0]",
                "reason": "Better damping and overshoot reduction",
                "expected_improvement": "10-20% overshoot reduction",
            },
            {
                "priority": 4,
                "change": "Optimize Feedforward",
                "current": f"ff_pos = {self.geometric_config.ff_pos}, ff_vel = {self.geometric_config.ff_vel}",
                "recommended": "ff_pos = 1.2, ff_vel = 0.8",
                "reason": "Better tracking of reference trajectories",
                "expected_improvement": "5-15% tracking improvement",
            },
            {
                "priority": 5,
                "change": "Consolidate Configuration",
                "current": "Two separate config systems",
                "recommended": "Single unified configuration",
                "reason": "Eliminate confusion and ensure consistent tuning",
                "expected_improvement": "Better maintainability",
            },
        ]

        for rec in recommendations:
            print(f"\n{rec['priority']}. {rec['change']} (Priority {rec['priority']})")
            print(f"   Current: {rec['current']}")
            print(f"   Recommended: {rec['recommended']}")
            print(f"   Reason: {rec['reason']}")
            print(f"   Expected: {rec['expected_improvement']}")

    def generate_optimized_config(self):
        """Generate an optimized controller configuration."""

        print(f"\n🚀 OPTIMIZED CONFIGURATION:")
        print("-" * 35)

        optimized_config = f"""
# OPTIMIZED GEOMETRIC CONTROLLER CONFIG
# Target: Reduce position error from 67m to <30m (50-70% improvement)

@dataclass
class OptimizedGeometricControllerConfig:
    # Position control gains (Tuned for aggressive tracking)
    kp_pos: np.ndarray = field(default_factory=lambda: np.array([10.0, 10.0, 12.0]))  # Higher response
    ki_pos: np.ndarray = field(default_factory=lambda: np.array([0.5, 0.5, 1.0]))    # Reduced windup
    kd_pos: np.ndarray = field(default_factory=lambda: np.array([6.0, 6.0, 8.0]))     # Better damping

    # Attitude control gains (Increased for stability)
    kp_att: np.ndarray = field(default_factory=lambda: np.array([12.0, 12.0, 5.0]))   # Higher response
    kd_att: np.ndarray = field(default_factory=lambda: np.array([4.0, 4.0, 2.0]))     # Better damping

    # Feedforward gains (Optimized for tracking)
    ff_pos: float = 1.2   # Increased position feedforward
    ff_vel: float = 0.8   # Optimized velocity feedforward

    # Safety limits (Adjusted for better performance)
    max_integral_pos: float = 3.0        # Reduced windup limit
    max_tilt_angle: float = np.pi/4       # 45 degrees (safer)

    # Tracking thresholds (Tighter for better performance)
    tracking_error_threshold: float = 5.0   # More sensitive failsafe
    velocity_error_threshold: float = 2.0   # Better velocity tracking
        """

        print(optimized_config)

        return optimized_config

    def create_tuning_test_plan(self):
        """Create a systematic testing plan for gain tuning."""

        print(f"\n📋 SYSTEMATIC TUNING TEST PLAN:")
        print("-" * 40)

        test_plan = [
            {
                "step": 1,
                "test": "Baseline Measurement",
                "action": "Run current system for 20s",
                "command": "python comprehensive_system_test.py",
                "target": "Document current 67m error",
                "success": "Consistent baseline measurement",
            },
            {
                "step": 2,
                "test": "Position Gain Increase",
                "action": "Increase Kp_pos to [10, 10, 12]",
                "command": "Modify geometric_controller.py",
                "target": "<40m position error",
                "success": "40%+ error reduction",
            },
            {
                "step": 3,
                "test": "Integral Gain Reduction",
                "action": "Reduce Ki_pos to [0.5, 0.5, 1.0]",
                "command": "Test stability",
                "target": "No oscillations",
                "success": "Stable response",
            },
            {
                "step": 4,
                "test": "Derivative Gain Tuning",
                "action": "Increase Kd_pos to [6, 6, 8]",
                "command": "Test overshoot",
                "target": "<20% overshoot",
                "success": "Well-damped response",
            },
            {
                "step": 5,
                "test": "Feedforward Optimization",
                "action": "Tune ff_pos=1.2, ff_vel=0.8",
                "command": "Test tracking",
                "target": "<30m final error",
                "success": "50%+ improvement from baseline",
            },
        ]

        for test in test_plan:
            print(f"\nStep {test['step']}: {test['test']}")
            print(f"   Action: {test['action']}")
            print(f"   Command: {test['command']}")
            print(f"   Target: {test['target']}")
            print(f"   Success: {test['success']}")

    def estimate_improvements(self):
        """Estimate expected improvements from tuning."""

        print(f"\n📈 EXPECTED IMPROVEMENT ESTIMATES:")
        print("-" * 40)

        current_error = 67.0
        improvements = [
            {"change": "Baseline", "error": 67.0, "improvement": "0%"},
            {"change": "Higher Kp gains", "error": 40.0, "improvement": "40%"},
            {"change": "+ Reduced Ki", "error": 35.0, "improvement": "48%"},
            {"change": "+ Better Kd", "error": 30.0, "improvement": "55%"},
            {"change": "+ Feedforward", "error": 25.0, "improvement": "63%"},
            {"change": "Target (Phase 1)", "error": 20.0, "improvement": "70%"},
        ]

        print(f"Current position error: {current_error:.1f}m")
        print(f"Phase 1 target: <30m (55%+ improvement)")
        print()

        for imp in improvements:
            if imp["change"] == "Baseline":
                print(f"🔴 {imp['change']}: {imp['error']:.1f}m ({imp['improvement']})")
            elif "Target" in imp["change"]:
                print(f"🟢 {imp['change']}: {imp['error']:.1f}m ({imp['improvement']})")
            else:
                print(f"🟡 {imp['change']}: {imp['error']:.1f}m ({imp['improvement']})")


def main():
    """Run comprehensive controller analysis."""

    analyzer = ControllerGainAnalysis()

    # Run full analysis
    analyzer.analyze_current_configuration()

    # Generate optimized config
    analyzer.generate_optimized_config()

    # Create test plan
    analyzer.create_tuning_test_plan()

    # Show improvement estimates
    analyzer.estimate_improvements()

    print(f"\n{'=' * 60}")
    print("🎯 IMMEDIATE NEXT STEPS:")
    print("=" * 60)
    print("1. Backup current geometric_controller.py")
    print("2. Implement optimized gains (start with Kp increase)")
    print("3. Test each change systematically")
    print("4. Measure and document improvements")
    print("5. Achieve <30m error before Phase 2")

    print(f"\n⚠️  CRITICAL: Test each gain change individually!")
    print("   Avoid changing multiple parameters simultaneously")
    print("   This ensures we can isolate the impact of each change")


if __name__ == "__main__":
    main()
