#!/usr/bin/env python3
"""
Controller Auto-Tuning for DART-Planner SITL

This script automatically tunes controller gains to optimize tracking performance
in AirSim simulation environment.
"""

import asyncio
from dart_planner.common.di_container_v2 import get_container
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
import time

import sys
from pathlib import Path

from control.control_config import ControllerTuningProfile, tuning_manager
from control.geometric_controller import GeometricController, GeometricControllerConfig
from common.types import DroneState, ControlCommand


@dataclass
class TuningResult:
    """Result of a controller tuning test"""
    profile_name: str
    gains: Dict[str, np.ndarray]
    tracking_error: float
    control_frequency: float
    settling_time: float
    overshoot: float
    stability_margin: float
    success: bool


class ControllerAutoTuner:
    """Automatic controller tuning for SITL environment"""
    
    def __init__(self):
        self.results: List[TuningResult] = []
        self.best_result: Optional[TuningResult] = None
        
    async def run_tuning_sweep(self) -> List[TuningResult]:
        """Run comprehensive tuning sweep"""
        print("🎛️ Starting Controller Auto-Tuning for SITL")
        print("=" * 60)
        
        # Define tuning parameter ranges
        tuning_configs = self._generate_tuning_configurations()
        
        for i, config in enumerate(tuning_configs):
            print(f"\n📊 Testing configuration {i+1}/{len(tuning_configs)}: {config['name']}")
            
            try:
                result = await self._test_configuration(config)
                self.results.append(result)
                
                if result.success and (self.best_result is None or 
                                     result.tracking_error < self.best_result.tracking_error):
                    self.best_result = result
                    print(f"   🎯 New best result: {result.tracking_error:.2f}m tracking error")
                
            except Exception as e:
                print(f"   ❌ Configuration failed: {e}")
                
        return self.results
    
    def _generate_tuning_configurations(self) -> List[Dict]:
        """Generate systematic tuning configurations"""
        configs = []
        
        # Base configuration (current sitl_optimized)
        base_kp = np.array([20.0, 20.0, 25.0])
        base_ki = np.array([1.5, 1.5, 2.0])
        base_kd = np.array([10.0, 10.0, 12.0])
        
        # Systematic gain variations
        kp_multipliers = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5]
        ki_multipliers = [0.5, 0.75, 1.0, 1.25, 1.5]
        kd_multipliers = [0.6, 0.8, 1.0, 1.2, 1.4]
        
        # Generate combinations (subset to avoid explosion)
        for kp_mult in kp_multipliers:
            for ki_mult in ki_multipliers[::2]:  # Skip some to reduce combinations
                for kd_mult in kd_multipliers[::2]:
                    configs.append({
                        'name': f'Kp{kp_mult:.1f}_Ki{ki_mult:.1f}_Kd{kd_mult:.1f}',
                        'kp_pos': base_kp * kp_mult,
                        'ki_pos': base_ki * ki_mult,
                        'kd_pos': base_kd * kd_mult,
                        'kp_att': np.array([18.0, 18.0, 8.0]),  # Keep attitude gains fixed
                        'kd_att': np.array([7.0, 7.0, 3.5]),
                        'ff_pos': 1.8,
                        'ff_vel': 1.1
                    })
        
        # Add specialized configurations
        
        # High-precision configuration  
        configs.append({
            'name': 'High_Precision',
            'kp_pos': np.array([35.0, 35.0, 40.0]),  # Very high position gains
            'ki_pos': np.array([3.0, 3.0, 4.0]),    # Higher integral
            'kd_pos': np.array([15.0, 15.0, 18.0]), # Higher derivative
            'kp_att': np.array([25.0, 25.0, 12.0]), # Higher attitude gains
            'kd_att': np.array([10.0, 10.0, 5.0]),  # Higher attitude damping
            'ff_pos': 2.5,                          # Strong feedforward
            'ff_vel': 1.5
        })
        
        # Damping-focused configuration
        configs.append({
            'name': 'High_Damping',
            'kp_pos': np.array([25.0, 25.0, 30.0]),
            'ki_pos': np.array([1.0, 1.0, 1.5]),    # Lower integral to prevent oscillation
            'kd_pos': np.array([20.0, 20.0, 25.0]), # Very high derivative
            'kp_att': np.array([20.0, 20.0, 10.0]),
            'kd_att': np.array([12.0, 12.0, 6.0]),  # Very high attitude damping
            'ff_pos': 2.0,
            'ff_vel': 1.2
        })
        
        # Fast-response configuration
        configs.append({
            'name': 'Fast_Response',
            'kp_pos': np.array([50.0, 50.0, 60.0]), # Extremely high position gains
            'ki_pos': np.array([2.0, 2.0, 3.0]),
            'kd_pos': np.array([12.0, 12.0, 15.0]),
            'kp_att': np.array([30.0, 30.0, 15.0]), # Very high attitude gains
            'kd_att': np.array([8.0, 8.0, 4.0]),
            'ff_pos': 3.0,                          # Maximum feedforward
            'ff_vel': 2.0
        })
        
        print(f"📋 Generated {len(configs)} tuning configurations")
        return configs[:15]  # Limit to first 15 for practical testing
    
    async def _test_configuration(self, config: Dict) -> TuningResult:
        """Test a single tuning configuration"""
        
        # Create temporary tuning profile
        profile = ControllerTuningProfile(
            name=config['name'],
            description=f"Auto-tuned configuration: {config['name']}",
            kp_pos=config['kp_pos'].copy(),
            ki_pos=config['ki_pos'].copy(),
            kd_pos=config['kd_pos'].copy(),
            kp_att=config['kp_att'].copy(),
            kd_att=config['kd_att'].copy(),
            ff_pos=config['ff_pos'],
            ff_vel=config['ff_vel'],
            max_tilt_angle=np.pi / 4,
            max_thrust=25.0,
            min_thrust=0.8,
            tracking_error_threshold=1.0,
            velocity_error_threshold=0.6,
            max_integral_pos=2.5
        )
        
        # Create controller with this configuration
        controller = get_container().create_control_container().get_geometric_controller()tuning_profile=None)
        controller._apply_tuning_profile(controller.config, config['name'])
        
        # Run simplified tracking test
        tracking_error, control_frequency, settling_time, overshoot = await self._run_tracking_test(controller)
        
        # Evaluate stability (simplified)
        stability_margin = self._estimate_stability_margin(config)
        
        # Determine success
        success = (tracking_error < 5.0 and  # Target tracking error
                  control_frequency > 50.0 and  # Target control frequency
                  settling_time < 3.0 and      # Reasonable settling time
                  overshoot < 20.0 and         # Reasonable overshoot
                  stability_margin > 0.5)      # Stability margin
        
        return TuningResult(
            profile_name=config['name'],
            gains={
                'kp_pos': config['kp_pos'],
                'ki_pos': config['ki_pos'], 
                'kd_pos': config['kd_pos']
            },
            tracking_error=tracking_error,
            control_frequency=control_frequency,
            settling_time=settling_time,
            overshoot=overshoot,
            stability_margin=stability_margin,
            success=success
        )
    
    async def _run_tracking_test(self, controller: GeometricController) -> Tuple[float, float, float, float]:
        """Run simplified tracking test without AirSim"""
        
        # Simulate step response test
        dt = 0.01  # 100Hz simulation
        duration = 5.0  # 5 second test
        steps = int(duration / dt)
        
        # Initial state
        position = np.array([0.0, 0.0, 0.0])
        velocity = np.array([0.0, 0.0, 0.0])
        orientation = np.array([1.0, 0.0, 0.0, 0.0])  # Identity quaternion
        angular_velocity = np.array([0.0, 0.0, 0.0])
        
        # Target position (step input)
        target_pos = np.array([5.0, 0.0, -2.0])
        target_vel = np.array([0.0, 0.0, 0.0])
        target_acc = np.array([0.0, 0.0, 0.0])
        
        # Simplified quadrotor dynamics
        mass = 1.5
        J = np.eye(3) * 0.1  # Simplified inertia
        
        # Tracking data
        position_errors = []
        control_times = []
        positions = []
        
        for i in range(steps):
            current_time = i * dt
            
            # Create drone state
            state = DroneState(
                timestamp=current_time,
                position=position.copy(),
                velocity=velocity.copy(),
                orientation=orientation.copy(),
                angular_velocity=angular_velocity.copy()
            )
            
            # Time control computation
            start_time = time.time()
            
            try:
                # Compute control command
                cmd = controller.compute_control(
                    state, target_pos, target_vel, target_acc
                )
                
                control_time = (time.time() - start_time) * 1000  # ms
                control_times.append(control_time)
                
                # Simple quadrotor dynamics integration
                thrust_world = np.array([0, 0, cmd.thrust / mass])
                acceleration = thrust_world - np.array([0, 0, 9.81])
                
                # Euler integration
                velocity += acceleration * dt
                position += velocity * dt
                
                # Track error
                error = np.linalg.norm(position - target_pos)
                position_errors.append(error)
                positions.append(position.copy())
                
            except Exception as e:
                # If controller fails, return poor performance
                return 100.0, 10.0, 10.0, 100.0
        
        # Analyze results
        if not position_errors or not control_times:
            return 100.0, 10.0, 10.0, 100.0
            
        avg_tracking_error = np.mean(position_errors[-int(0.5/dt):])  # Last 0.5 seconds
        avg_control_frequency = 1000.0 / np.mean(control_times) if control_times else 10.0
        
        # Settling time (time to reach 5% of final value)
        final_error = position_errors[-1]
        settling_threshold = final_error + 0.25  # 25cm tolerance
        settling_time = duration
        for i, error in enumerate(position_errors):
            if error < settling_threshold and all(e < settling_threshold for e in position_errors[i:]):
                settling_time = i * dt
                break
        
        # Overshoot
        min_distance_to_target = min([np.linalg.norm(pos - target_pos) for pos in positions])
        if min_distance_to_target < np.linalg.norm(target_pos):
            overshoot = (np.linalg.norm(target_pos) - min_distance_to_target) / np.linalg.norm(target_pos) * 100
        else:
            overshoot = 0.0
        
        return avg_tracking_error, avg_control_frequency, settling_time, overshoot
    
    def _estimate_stability_margin(self, config: Dict) -> float:
        """Estimate stability margin based on gain ratios"""
        kp = np.mean(config['kp_pos'])
        ki = np.mean(config['ki_pos'])
        kd = np.mean(config['kd_pos'])
        
        # Simple stability heuristic based on PID gain relationships
        # Higher derivative relative to proportional typically improves stability
        kd_kp_ratio = kd / kp if kp > 0 else 0
        
        # Integral gain should be smaller than proportional for stability
        ki_kp_ratio = ki / kp if kp > 0 else 1
        
        # Heuristic stability measure
        stability = kd_kp_ratio * (1.0 - min(ki_kp_ratio, 1.0))
        return np.clip(stability, 0.0, 2.0)
    
    def analyze_results(self) -> Dict:
        """Analyze tuning results and recommend best configuration"""
        if not self.results:
            return {"error": "No tuning results available"}
        
        # Find successful configurations
        successful = [r for r in self.results if r.success]
        
        analysis = {
            "total_configs_tested": len(self.results),
            "successful_configs": len(successful),
            "success_rate": len(successful) / len(self.results) * 100,
        }
        
        if successful:
            # Best overall (lowest tracking error among successful)
            best = min(successful, key=lambda r: r.tracking_error)
            analysis["best_config"] = {
                "name": best.profile_name,
                "tracking_error": best.tracking_error,
                "control_frequency": best.control_frequency,
                "settling_time": best.settling_time,
                "overshoot": best.overshoot,
                "gains": {
                    "kp_pos": best.gains['kp_pos'].tolist(),
                    "ki_pos": best.gains['ki_pos'].tolist(),
                    "kd_pos": best.gains['kd_pos'].tolist()
                }
            }
            
            # Statistics
            tracking_errors = [r.tracking_error for r in successful]
            analysis["performance_stats"] = {
                "best_tracking_error": min(tracking_errors),
                "worst_tracking_error": max(tracking_errors),
                "avg_tracking_error": np.mean(tracking_errors),
                "std_tracking_error": np.std(tracking_errors)
            }
        
        return analysis
    
    def save_results(self, filename: str = "tuning_results.json"):
        """Save tuning results to file"""
        results_data = {
            "timestamp": time.time(),
            "analysis": self.analyze_results(),
            "all_results": []
        }
        
        for result in self.results:
            results_data["all_results"].append({
                "profile_name": result.profile_name,
                "tracking_error": result.tracking_error,
                "control_frequency": result.control_frequency,
                "settling_time": result.settling_time,
                "overshoot": result.overshoot,
                "stability_margin": result.stability_margin,
                "success": result.success,
                "gains": {
                    "kp_pos": result.gains['kp_pos'].tolist(),
                    "ki_pos": result.gains['ki_pos'].tolist(),
                    "kd_pos": result.gains['kd_pos'].tolist()
                }
            })
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"💾 Results saved to {filename}")
    
    def plot_results(self):
        """Plot tuning results"""
        if not self.results:
            print("❌ No results to plot")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Extract data
        names = [r.profile_name for r in self.results]
        tracking_errors = [r.tracking_error for r in self.results]
        control_frequencies = [r.control_frequency for r in self.results]
        settling_times = [r.settling_time for r in self.results]
        success = [r.success for r in self.results]
        
        # Color by success
        colors = ['green' if s else 'red' for s in success]
        
        # Tracking error vs control frequency
        axes[0,0].scatter(control_frequencies, tracking_errors, c=colors, alpha=0.7)
        axes[0,0].axhline(y=5.0, color='red', linestyle='--', label='Target tracking error')
        axes[0,0].axvline(x=50.0, color='red', linestyle='--', label='Target frequency')
        axes[0,0].set_xlabel('Control Frequency (Hz)')
        axes[0,0].set_ylabel('Tracking Error (m)')
        axes[0,0].set_title('Tracking Error vs Control Frequency')
        axes[0,0].legend()
        
        # Tracking error distribution
        axes[0,1].hist([r.tracking_error for r in self.results if r.success], 
                      bins=15, alpha=0.7, color='green', label='Successful')
        axes[0,1].hist([r.tracking_error for r in self.results if not r.success], 
                      bins=15, alpha=0.7, color='red', label='Failed')
        axes[0,1].axvline(x=5.0, color='black', linestyle='--', label='Target')
        axes[0,1].set_xlabel('Tracking Error (m)')
        axes[0,1].set_ylabel('Count')
        axes[0,1].set_title('Tracking Error Distribution')
        axes[0,1].legend()
        
        # Settling time vs tracking error
        axes[1,0].scatter(settling_times, tracking_errors, c=colors, alpha=0.7)
        axes[1,0].axhline(y=5.0, color='red', linestyle='--', label='Target tracking error')
        axes[1,0].axvline(x=3.0, color='red', linestyle='--', label='Target settling time')
        axes[1,0].set_xlabel('Settling Time (s)')
        axes[1,0].set_ylabel('Tracking Error (m)')
        axes[1,0].set_title('Settling Time vs Tracking Error')
        axes[1,0].legend()
        
        # Performance summary
        successful_configs = [r for r in self.results if r.success]
        if successful_configs:
            best = min(successful_configs, key=lambda r: r.tracking_error)
            summary_text = f"""Best Configuration: {best.profile_name}
Tracking Error: {best.tracking_error:.2f}m
Control Freq: {best.control_frequency:.1f}Hz
Settling Time: {best.settling_time:.2f}s
Success Rate: {len(successful_configs)}/{len(self.results)}"""
        else:
            summary_text = "No successful configurations found"
            
        axes[1,1].text(0.1, 0.5, summary_text, transform=axes[1,1].transAxes, 
                      fontsize=12, verticalalignment='center',
                      bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
        axes[1,1].set_title('Tuning Summary')
        axes[1,1].axis('off')
        
        plt.tight_layout()
        plt.savefig('controller_tuning_results.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("📊 Results plotted and saved to controller_tuning_results.png")


async def main():
    """Main tuning procedure"""
    tuner = ControllerAutoTuner()
    
    print("🎛️ DART-Planner Controller Auto-Tuning")
    print("Optimizing for SITL tracking performance")
    print("=" * 60)
    
    # Run tuning sweep
    results = await tuner.run_tuning_sweep()
    
    # Analyze results
    analysis = tuner.analyze_results()
    
    print(f"\n📊 TUNING ANALYSIS")
    print("=" * 40)
    print(f"Total configurations tested: {analysis['total_configs_tested']}")
    print(f"Successful configurations: {analysis['successful_configs']}")
    print(f"Success rate: {analysis['success_rate']:.1f}%")
    
    if "best_config" in analysis:
        best = analysis["best_config"]
        print(f"\n🏆 BEST CONFIGURATION: {best['name']}")
        print(f"   Tracking error: {best['tracking_error']:.2f}m")
        print(f"   Control frequency: {best['control_frequency']:.1f}Hz")
        print(f"   Settling time: {best['settling_time']:.2f}s")
        print(f"   Overshoot: {best['overshoot']:.1f}%")
        print("\n🎛️ Optimal Gains:")
        print(f"   Kp_pos: {best['gains']['kp_pos']}")
        print(f"   Ki_pos: {best['gains']['ki_pos']}")
        print(f"   Kd_pos: {best['gains']['kd_pos']}")
        
        # Update SITL configuration with best gains
        print(f"\n💾 Updating SITL configuration with optimal gains...")
        
        optimal_profile = ControllerTuningProfile(
            name="sitl_auto_tuned",
            description=f"Auto-tuned for SITL: {best['tracking_error']:.2f}m tracking error",
            kp_pos=np.array(best['gains']['kp_pos']),
            ki_pos=np.array(best['gains']['ki_pos']),
            kd_pos=np.array(best['gains']['kd_pos']),
            kp_att=np.array([18.0, 18.0, 8.0]),
            kd_att=np.array([7.0, 7.0, 3.5]),
            ff_pos=1.8,
            ff_vel=1.1,
            max_tilt_angle=np.pi / 4,
            max_thrust=25.0,
            min_thrust=0.8,
            tracking_error_threshold=best['tracking_error'],
            velocity_error_threshold=0.6,
            max_integral_pos=2.5
        )
        
        tuning_manager.add_custom_profile(optimal_profile)
        print(f"   ✅ Added 'sitl_auto_tuned' profile to tuning manager")
        
    else:
        print("\n❌ No successful configurations found")
        print("   Consider relaxing performance targets or expanding search space")
    
    # Save results
    tuner.save_results("controller_tuning_results.json")
    
    # Plot results
    tuner.plot_results()
    
    print(f"\n🎯 Auto-tuning complete!")


if __name__ == "__main__":
    asyncio.run(main()) 
