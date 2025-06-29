#!/usr/bin/env python3
"""
Phase 2C-5B: Conservative Frequency Test
Find stability boundary starting from very low frequencies
Target: Find lowest frequency where system is stable, then optimize upward
"""

import numpy as np
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.control.geometric_controller import GeometricController
from src.utils.drone_simulator import DroneSimulator
from src.common.types import DroneState


class ConservativeFrequencyTest:
    """Conservative approach to finding stable control frequency"""

    def __init__(self):
        print("🚀 Conservative frequency testing system")

        # Use ORIGINAL gains from before Phase 1 optimizations
        # to isolate the frequency stability issue
        self.controller = GeometricController()
        self.simulator = DroneSimulator()

        print("✅ Conservative system initialized")

    def reset_to_baseline_gains(self):
        """Reset controller to baseline (pre-optimization) gains for stability"""
        print("🔧 Resetting to baseline controller gains...")

        # These are the original gains before Phase 1 optimization
        baseline_gains = {
            "position": {
                "Kp": np.array([6.0, 6.0, 8.0]),
                "Ki": np.array([1.0, 1.0, 2.0]),
                "Kd": np.array([4.0, 4.0, 5.0]),
            },
            "attitude": {
                "Kp": np.array([10.0, 10.0, 4.0]),
                "Kd": np.array([3.0, 3.0, 1.5]),
            },
            "feedforward": {"pos": 0.8, "vel": 0.9},
        }

        # Apply baseline gains
        self.controller.config.kp_pos = baseline_gains["position"]["Kp"]
        self.controller.config.ki_pos = baseline_gains["position"]["Ki"]
        self.controller.config.kd_pos = baseline_gains["position"]["Kd"]

        self.controller.config.kp_att = baseline_gains["attitude"]["Kp"]
        self.controller.config.kd_att = baseline_gains["attitude"]["Kd"]

        self.controller.config.ff_pos = baseline_gains["feedforward"]["pos"]
        self.controller.config.ff_vel = baseline_gains["feedforward"]["vel"]

        print("✅ Reset to baseline gains:")
        print(
            f"   Position: Kp={baseline_gains['position']['Kp']}, Ki={baseline_gains['position']['Ki']}, Kd={baseline_gains['position']['Kd']}"
        )
        print(
            f"   Attitude: Kp={baseline_gains['attitude']['Kp']}, Kd={baseline_gains['attitude']['Kd']}"
        )
        print(
            f"   Feedforward: pos={baseline_gains['feedforward']['pos']}, vel={baseline_gains['feedforward']['vel']}"
        )

    def test_frequency_simple(
        self, target_freq: int, test_duration: float = 10.0
    ) -> dict:
        """Simple, conservative frequency test"""

        print(f"\n🔧 Testing {target_freq}Hz...")

        dt = 1.0 / target_freq

        # Very simple, gentle trajectory
        radius = 3.0  # Smaller radius
        angular_vel = 0.1  # Very slow motion

        # Initialize at rest
        current_state = DroneState(
            timestamp=time.time(),
            position=np.array([radius, 0.0, 2.0]),
            velocity=np.zeros(3),
            attitude=np.zeros(3),
            angular_velocity=np.zeros(3),
        )

        start_time = time.time()
        position_errors = []
        velocity_errors = []
        large_error_count = 0
        cycle_count = 0

        try:
            while time.time() - start_time < test_duration:
                cycle_start = time.perf_counter()
                current_time = time.time() - start_time

                # Gentle circular reference
                x_ref = radius * np.cos(angular_vel * current_time)
                y_ref = radius * np.sin(angular_vel * current_time)
                z_ref = 2.0

                vx_ref = -radius * angular_vel * np.sin(angular_vel * current_time)
                vy_ref = radius * angular_vel * np.cos(angular_vel * current_time)
                vz_ref = 0.0

                ax_ref = (
                    -radius
                    * angular_vel
                    * angular_vel
                    * np.cos(angular_vel * current_time)
                )
                ay_ref = (
                    -radius
                    * angular_vel
                    * angular_vel
                    * np.sin(angular_vel * current_time)
                )
                az_ref = 0.0

                desired_pos = np.array([x_ref, y_ref, z_ref])
                desired_vel = np.array([vx_ref, vy_ref, vz_ref])
                desired_acc = np.array([ax_ref, ay_ref, az_ref])

                # Control computation
                control_output = self.controller.compute_control(
                    current_state, desired_pos, desired_vel, desired_acc
                )

                # Gentle simulation step
                current_state = self.simulator.step(current_state, control_output, dt)

                # Track errors
                pos_error = np.linalg.norm(current_state.position - desired_pos)
                vel_error = np.linalg.norm(current_state.velocity - desired_vel)

                position_errors.append(pos_error)
                velocity_errors.append(vel_error)

                # Check for large errors (instability indicator)
                if pos_error > 10.0 or vel_error > 15.0:
                    large_error_count += 1

                cycle_count += 1

                # Maintain frequency
                elapsed = time.perf_counter() - cycle_start
                sleep_time = dt - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return {"failed": True, "error": str(e)}

        # Analyze results
        pos_errors = np.array(position_errors)
        vel_errors = np.array(velocity_errors)

        mean_pos_error = np.mean(pos_errors)
        mean_vel_error = np.mean(vel_errors)
        instability_rate = (
            large_error_count / cycle_count * 100 if cycle_count > 0 else 100
        )
        stable = instability_rate < 5.0  # Less than 5% large errors

        print(f"   Position error: {mean_pos_error:.2f}m")
        print(f"   Velocity error: {mean_vel_error:.2f}m/s")
        print(f"   Instability rate: {instability_rate:.1f}%")
        print(f"   Status: {'✅ Stable' if stable else '❌ Unstable'}")

        return {
            "frequency": target_freq,
            "mean_position_error": mean_pos_error,
            "mean_velocity_error": mean_vel_error,
            "instability_rate": instability_rate,
            "stable": stable,
            "total_cycles": cycle_count,
        }

    def find_stability_boundary(self):
        """Find the frequency where system becomes stable"""

        print("🎯 Finding stability boundary...")
        print("🔧 Starting with baseline gains for maximum stability")

        # Reset to baseline gains
        self.reset_to_baseline_gains()

        # Test very conservative frequencies first
        test_frequencies = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]

        stable_frequencies = []
        results = {}

        for freq in test_frequencies:
            result = self.test_frequency_simple(freq, test_duration=8.0)
            results[freq] = result

            if not result.get("failed", False) and result["stable"]:
                stable_frequencies.append(freq)
                print(f"   ✅ {freq}Hz is STABLE")
            else:
                print(f"   ❌ {freq}Hz is UNSTABLE")
                # Stop at first unstable frequency
                break

        print(f"\n📊 STABILITY ANALYSIS:")
        if stable_frequencies:
            max_stable_freq = max(stable_frequencies)
            print(f"✅ Maximum stable frequency: {max_stable_freq}Hz")

            # Test the best stable frequency
            best_result = results[max_stable_freq]
            print(f"   Position error: {best_result['mean_position_error']:.2f}m")
            print(f"   Velocity error: {best_result['mean_velocity_error']:.2f}m/s")

            # Compare with targets
            if best_result["mean_velocity_error"] < 5.0:
                print(f"🎉 VELOCITY TARGET ACHIEVED at {max_stable_freq}Hz!")
            elif best_result["mean_velocity_error"] < 9.28:
                improvement = (9.28 - best_result["mean_velocity_error"]) / 9.28 * 100
                print(
                    f"📊 Velocity improvement: {improvement:.1f}% (vs 9.28m/s baseline)"
                )
            else:
                print(f"⚠️  Velocity worse than baseline")

            return max_stable_freq, best_result
        else:
            print("❌ No stable frequencies found in tested range")
            print("🔧 System may need fundamental control parameter adjustment")
            return None, {}

    def test_optimized_gains_at_stable_frequency(self, stable_freq: int):
        """Test if Phase 1 optimized gains work at the stable frequency"""

        print(
            f"\n🧪 Testing Phase 1 optimized gains at stable frequency {stable_freq}Hz..."
        )

        # Apply Phase 1 optimized gains
        optimized_gains = {
            "position": {
                "Kp": np.array([10.0, 10.0, 12.0]),
                "Ki": np.array([0.5, 0.5, 1.0]),
                "Kd": np.array([6.0, 6.0, 8.0]),
            },
            "attitude": {
                "Kp": np.array([12.0, 12.0, 5.0]),
                "Kd": np.array([4.0, 4.0, 2.0]),
            },
            "feedforward": {"pos": 1.2, "vel": 0.8},
        }

        self.controller.config.kp_pos = optimized_gains["position"]["Kp"]
        self.controller.config.ki_pos = optimized_gains["position"]["Ki"]
        self.controller.config.kd_pos = optimized_gains["position"]["Kd"]

        self.controller.config.kp_att = optimized_gains["attitude"]["Kp"]
        self.controller.config.kd_att = optimized_gains["attitude"]["Kd"]

        self.controller.config.ff_pos = optimized_gains["feedforward"]["pos"]
        self.controller.config.ff_vel = optimized_gains["feedforward"]["vel"]

        print("🔧 Applied Phase 1 optimized gains")

        # Test at stable frequency
        result = self.test_frequency_simple(stable_freq, test_duration=12.0)

        if result.get("stable", False):
            print(f"✅ Phase 1 gains STABLE at {stable_freq}Hz")
            print(f"   Velocity error: {result['mean_velocity_error']:.2f}m/s")

            if result["mean_velocity_error"] < 5.0:
                print(f"🎉 VELOCITY TARGET ACHIEVED with optimized gains!")
                return True
        else:
            print(f"❌ Phase 1 gains UNSTABLE at {stable_freq}Hz")
            print(f"🔧 Need to use baseline gains for stability")

        return result.get("stable", False)


def main():
    """Run conservative frequency analysis"""

    print("🚀 Phase 2C-5B: Conservative Frequency Stability Analysis")
    print("=" * 60)
    print("🎯 Find stable operating frequency for velocity tracking optimization")

    system = ConservativeFrequencyTest()

    # Find stability boundary
    stable_freq, baseline_result = system.find_stability_boundary()

    if stable_freq:
        # Test if optimized gains work at stable frequency
        optimized_stable = system.test_optimized_gains_at_stable_frequency(stable_freq)

        print(f"\n🎯 FINAL RECOMMENDATIONS:")
        print(f"✅ Use control frequency: {stable_freq}Hz")

        if optimized_stable:
            print(f"✅ Use Phase 1 optimized gains")
            print(f"🎉 System ready for stable high-performance operation")
        else:
            print(f"🔧 Use baseline gains for stability")
            print(f"📊 Prioritize stability over optimization")

    else:
        print(f"\n⚠️  CRITICAL FINDING:")
        print(f"❌ System unstable even at very low frequencies")
        print(f"🔧 Requires fundamental control system review")

    return stable_freq


if __name__ == "__main__":
    stable_frequency = main()
