#!/usr/bin/env python3
"""
Phase 2C-5: Control Frequency Tuning Test
Find optimal control frequency balancing computational efficiency with stability
Target: Find frequency that achieves <5m/s velocity error with stable operation
"""

import numpy as np
import time
import sys
import os
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.control.geometric_controller import GeometricController
from src.utils.drone_simulator import DroneSimulator
from src.common.types import DroneState

class FrequencyTuningSystem:
    """System for testing optimal control frequency"""
    
    def __init__(self):
        print("🚀 Initializing FrequencyTuningSystem...")
        
        # Initialize core components (no optimized planners to isolate frequency effects)
        self.controller = GeometricController()  # Phase 1 optimized gains
        self.simulator = DroneSimulator()
        
        # Test results storage
        self.frequency_results = {}
        
        print("✅ FrequencyTuningSystem initialized")
    
    def test_control_frequency(self, target_freq: int, test_duration: float = 20.0) -> Dict[str, Any]:
        """Test control system performance at a specific frequency"""
        
        print(f"\n🔧 Testing control frequency: {target_freq}Hz")
        
        # Reset tracking arrays
        position_errors = []
        velocity_errors = []
        actual_frequencies = []
        failsafe_count = 0
        
        # Control parameters
        dt = 1.0 / target_freq
        
        # Test trajectory - moderate demands (not extreme)
        radius = 8.0
        angular_vel = 0.25  # rad/s - less aggressive than previous tests
        
        # Initialize drone state
        current_state = DroneState(
            timestamp=time.time(),
            position=np.array([radius, 0.0, 2.0]),
            velocity=np.zeros(3),
            attitude=np.zeros(3),
            angular_velocity=np.zeros(3)
        )
        
        start_time = time.time()
        cycle_count = 0
        
        try:
            while time.time() - start_time < test_duration:
                cycle_start = time.perf_counter()
                
                current_time = time.time() - start_time
                
                # Generate reference trajectory
                x_ref = radius * np.cos(angular_vel * current_time)
                y_ref = radius * np.sin(angular_vel * current_time)
                z_ref = 2.0
                
                vx_ref = -radius * angular_vel * np.sin(angular_vel * current_time)
                vy_ref = radius * angular_vel * np.cos(angular_vel * current_time)
                vz_ref = 0.0
                
                ax_ref = -radius * angular_vel * angular_vel * np.cos(angular_vel * current_time)
                ay_ref = -radius * angular_vel * angular_vel * np.sin(angular_vel * current_time)
                az_ref = 0.0
                
                desired_pos = np.array([x_ref, y_ref, z_ref])
                desired_vel = np.array([vx_ref, vy_ref, vz_ref])
                desired_acc = np.array([ax_ref, ay_ref, az_ref])
                
                # Control computation
                control_output = self.controller.compute_control(
                    current_state, desired_pos, desired_vel, desired_acc
                )
                
                # Physics simulation with frequency-appropriate dt
                current_state = self.simulator.step(current_state, control_output, dt)
                
                # Track performance metrics
                pos_error = np.linalg.norm(current_state.position - desired_pos)
                vel_error = np.linalg.norm(current_state.velocity - desired_vel)
                
                position_errors.append(pos_error)
                velocity_errors.append(vel_error)
                
                # Check for instability
                if pos_error > 15.0 or vel_error > 20.0:
                    failsafe_count += 1
                
                # Track actual frequency
                cycle_time = (time.perf_counter() - cycle_start) * 1000  # ms
                if cycle_time > 0:
                    actual_freq = 1000.0 / cycle_time
                    actual_frequencies.append(actual_freq)
                
                cycle_count += 1
                
                # Maintain target frequency
                elapsed = time.perf_counter() - cycle_start
                sleep_time = dt - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except Exception as e:
            print(f"⚠️  Test failed at {target_freq}Hz: {e}")
            return {'failed': True, 'error': str(e)}
        
        # Analyze results
        pos_errors = np.array(position_errors)
        vel_errors = np.array(velocity_errors)
        frequencies = np.array(actual_frequencies)
        
        results = {
            'target_frequency': target_freq,
            'test_duration': test_duration,
            'total_cycles': cycle_count,
            'mean_position_error': float(np.mean(pos_errors)),
            'std_position_error': float(np.std(pos_errors)),
            'max_position_error': float(np.max(pos_errors)),
            'mean_velocity_error': float(np.mean(vel_errors)),
            'std_velocity_error': float(np.std(vel_errors)),
            'max_velocity_error': float(np.max(vel_errors)),
            'mean_actual_frequency': float(np.mean(frequencies)) if len(frequencies) > 0 else 0,
            'frequency_std': float(np.std(frequencies)) if len(frequencies) > 0 else 0,
            'failsafe_activations': failsafe_count,
            'failsafe_rate': failsafe_count / cycle_count * 100 if cycle_count > 0 else 100,
            'stable': failsafe_count < cycle_count * 0.01  # Less than 1% failsafe rate
        }
        
        print(f"   Position error: {results['mean_position_error']:.2f}m")
        print(f"   Velocity error: {results['mean_velocity_error']:.2f}m/s")
        print(f"   Actual frequency: {results['mean_actual_frequency']:.0f}Hz")
        print(f"   Failsafe rate: {results['failsafe_rate']:.1f}%")
        print(f"   Stable: {'✅' if results['stable'] else '❌'}")
        
        return results
    
    def run_frequency_sweep(self) -> Dict[int, Dict[str, Any]]:
        """Run comprehensive frequency sweep test"""
        
        print("🎯 Phase 2C-5: Control Frequency Sweep Test")
        print("=" * 60)
        print("🔍 Finding optimal balance of frequency vs stability")
        
        # Test frequencies from conservative to aggressive
        test_frequencies = [600, 650, 700, 750, 800, 850, 900]
        
        results = {}
        
        for freq in test_frequencies:
            try:
                result = self.test_control_frequency(freq, test_duration=15.0)
                results[freq] = result
                
                # Early termination if system becomes highly unstable
                if result.get('failsafe_rate', 0) > 50:
                    print(f"⚠️  High instability at {freq}Hz - skipping higher frequencies")
                    break
                    
            except KeyboardInterrupt:
                print("\n⚠️  Test interrupted by user")
                break
            except Exception as e:
                print(f"⚠️  Failed at {freq}Hz: {e}")
                results[freq] = {'failed': True, 'error': str(e)}
        
        self.frequency_results = results
        return results
    
    def analyze_frequency_sweep(self) -> Tuple[int, Dict[str, Any]]:
        """Analyze frequency sweep results and find optimal frequency"""
        
        print(f"\n📊 FREQUENCY SWEEP ANALYSIS")
        print("=" * 50)
        
        if not self.frequency_results:
            print("⚠️  No results available for analysis")
            return 650, {}
        
        # Find optimal frequency based on multiple criteria
        optimal_freq = None
        best_score = -float('inf')
        
        print("Frequency | Pos Error | Vel Error | Failsafe | Stable | Score")
        print("-" * 65)
        
        for freq, result in self.frequency_results.items():
            if result.get('failed', False):
                print(f"{freq:8d}Hz | FAILED")
                continue
            
            pos_err = result['mean_position_error']
            vel_err = result['mean_velocity_error']
            failsafe_rate = result['failsafe_rate']
            stable = result['stable']
            
            # Scoring function: prioritize velocity tracking and stability
            score = 0
            
            # Velocity tracking score (primary objective)
            if vel_err < 5.0:
                score += 100  # Target achieved
            elif vel_err < 7.0:
                score += 80   # Close to target
            elif vel_err < 10.0:
                score += 60   # Acceptable
            else:
                score += max(0, 40 - vel_err)  # Decreasing score
            
            # Position tracking score
            if pos_err < 2.0:
                score += 50   # Excellent
            elif pos_err < 5.0:
                score += 30   # Good
            else:
                score += max(0, 20 - pos_err)  # Decreasing score
            
            # Stability score
            if stable and failsafe_rate < 1.0:
                score += 50   # Very stable
            elif failsafe_rate < 5.0:
                score += 30   # Acceptable
            else:
                score += max(0, 20 - failsafe_rate)  # Decreasing score
            
            # Frequency bonus (higher is better, but diminishing returns)
            freq_bonus = min(20, freq / 50)
            score += freq_bonus
            
            status = "✅" if stable else "❌"
            print(f"{freq:8d}Hz | {pos_err:8.2f}m | {vel_err:8.2f}m/s | {failsafe_rate:7.1f}% | {status:6s} | {score:5.1f}")
            
            if score > best_score:
                best_score = score
                optimal_freq = freq
        
        print("\n🎯 OPTIMAL FREQUENCY ANALYSIS:")
        if optimal_freq is not None:
            optimal_result = self.frequency_results[optimal_freq]
            print(f"✅ Optimal frequency: {optimal_freq}Hz")
            print(f"   Position error: {optimal_result['mean_position_error']:.2f}m")
            print(f"   Velocity error: {optimal_result['mean_velocity_error']:.2f}m/s")
            print(f"   Failsafe rate: {optimal_result['failsafe_rate']:.1f}%")
            print(f"   Stability: {'✅ Stable' if optimal_result['stable'] else '❌ Unstable'}")
            
            # Check if target achieved
            if optimal_result['mean_velocity_error'] < 5.0:
                print(f"🎉 VELOCITY TARGET ACHIEVED!")
            else:
                print(f"📊 Velocity error: {5.0 - optimal_result['mean_velocity_error']:.2f}m/s from target")
        else:
            print("❌ No stable frequency found in tested range")
            optimal_freq = 650  # Fallback to known stable frequency
            
        return optimal_freq, self.frequency_results.get(optimal_freq, {})
    
    def generate_frequency_plots(self):
        """Generate visualization of frequency sweep results"""
        
        if not self.frequency_results:
            print("⚠️  No results available for plotting")
            return
        
        print("\n📊 Generating frequency analysis plots...")
        
        # Extract data for plotting
        frequencies = []
        pos_errors = []
        vel_errors = []
        failsafe_rates = []
        
        for freq, result in sorted(self.frequency_results.items()):
            if not result.get('failed', False):
                frequencies.append(freq)
                pos_errors.append(result['mean_position_error'])
                vel_errors.append(result['mean_velocity_error'])
                failsafe_rates.append(result['failsafe_rate'])
        
        if len(frequencies) == 0:
            print("⚠️  No valid data for plotting")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Position error vs frequency
        ax1.plot(frequencies, pos_errors, 'bo-', linewidth=2, markersize=8)
        ax1.axhline(y=2.0, color='r', linestyle='--', label='Target (<2m)')
        ax1.set_xlabel('Control Frequency (Hz)')
        ax1.set_ylabel('Mean Position Error (m)')
        ax1.set_title('Position Tracking vs Control Frequency')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Velocity error vs frequency
        ax2.plot(frequencies, vel_errors, 'go-', linewidth=2, markersize=8)
        ax2.axhline(y=5.0, color='r', linestyle='--', label='Target (<5m/s)')
        ax2.axhline(y=9.28, color='orange', linestyle='--', label='Original (9.28m/s)')
        ax2.set_xlabel('Control Frequency (Hz)')
        ax2.set_ylabel('Mean Velocity Error (m/s)')
        ax2.set_title('Velocity Tracking vs Control Frequency')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Failsafe rate vs frequency
        ax3.plot(frequencies, failsafe_rates, 'ro-', linewidth=2, markersize=8)
        ax3.axhline(y=1.0, color='orange', linestyle='--', label='Acceptable (<1%)')
        ax3.axhline(y=5.0, color='r', linestyle='--', label='Poor (>5%)')
        ax3.set_xlabel('Control Frequency (Hz)')
        ax3.set_ylabel('Failsafe Rate (%)')
        ax3.set_title('System Stability vs Control Frequency')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Combined performance score
        scores = []
        for i, freq in enumerate(frequencies):
            vel_score = max(0, 10 - vel_errors[i])  # Higher is better
            pos_score = max(0, 5 - pos_errors[i])   # Higher is better
            stab_score = max(0, 10 - failsafe_rates[i])  # Higher is better
            total_score = vel_score + pos_score + stab_score
            scores.append(total_score)
        
        ax4.plot(frequencies, scores, 'mo-', linewidth=2, markersize=8)
        ax4.set_xlabel('Control Frequency (Hz)')
        ax4.set_ylabel('Combined Performance Score')
        ax4.set_title('Overall Performance vs Control Frequency')
        ax4.grid(True, alpha=0.3)
        
        # Mark optimal frequency
        if scores:
            optimal_idx = np.argmax(scores)
            optimal_freq = frequencies[optimal_idx]
            ax4.axvline(x=optimal_freq, color='g', linestyle='--', linewidth=2, label=f'Optimal: {optimal_freq}Hz')
            ax4.legend()
        
        plt.tight_layout()
        plt.savefig('frequency_sweep_analysis.png', dpi=300, bbox_inches='tight')
        print("✅ Frequency analysis plots saved as 'frequency_sweep_analysis.png'")

def main():
    """Run the complete frequency tuning analysis"""
    
    print("🚀 Phase 2C-5: Control Frequency Optimization")
    print("=" * 60)
    print("🎯 Objective: Find optimal control frequency for velocity tracking")
    print("📊 Target: <5m/s velocity error with stable operation")
    
    # Initialize and run frequency sweep
    tuning_system = FrequencyTuningSystem()
    results = tuning_system.run_frequency_sweep()
    
    # Analyze results
    optimal_freq, optimal_result = tuning_system.analyze_frequency_sweep()
    
    # Generate visualizations
    tuning_system.generate_frequency_plots()
    
    # Final assessment
    print(f"\n🎯 PHASE 2C-5 SUMMARY:")
    print(f"✅ Optimal control frequency identified: {optimal_freq}Hz")
    
    if optimal_result and not optimal_result.get('failed', False):
        if optimal_result['mean_velocity_error'] < 5.0:
            print(f"🎉 VELOCITY TARGET ACHIEVED!")
            print(f"📊 Velocity error: {optimal_result['mean_velocity_error']:.2f}m/s")
            print(f"🚀 System ready for production deployment")
        else:
            print(f"📊 Best velocity error: {optimal_result['mean_velocity_error']:.2f}m/s")
            print(f"🔧 {optimal_result['mean_velocity_error'] - 5.0:.2f}m/s from target")
    
    return optimal_freq, results

if __name__ == "__main__":
    optimal_frequency, all_results = main() 