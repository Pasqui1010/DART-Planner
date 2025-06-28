#!/usr/bin/env python3
"""
Controller Benchmark: DIAL-MPC vs SE(3) MPC Comparison

CRITICAL REFACTOR VALIDATION:
This benchmark addresses Problem 1 from the technical audit by providing 
quantitative evidence that SE(3) MPC outperforms the misapplied DIAL-MPC 
for aerial robotics applications.

The benchmark measures:
1. Trajectory tracking accuracy
2. Computational performance 
3. Stability and robustness
4. Control effort efficiency

This validation is essential to justify the core algorithm replacement.
"""

import numpy as np
import time
import sys
import os
from typing import Dict, List, Tuple, Any
import matplotlib.pyplot as plt
from dataclasses import dataclass

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.planning.dial_mpc_planner import DIALMPCPlanner, DIALMPCConfig
from src.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
from src.control.geometric_controller import GeometricController
from src.utils.drone_simulator import DroneSimulator
from src.common.types import DroneState, Trajectory


@dataclass
class BenchmarkConfig:
    """Configuration for benchmarking tests"""
    test_duration: float = 30.0  # seconds
    control_frequency: float = 100.0  # Hz
    planning_frequency: float = 10.0  # Hz
    
    # Test scenarios
    scenarios: List[str] = None
    
    def __post_init__(self):
        if self.scenarios is None:
            self.scenarios = [
                'hover_stability',
                'step_response',
                'circular_trajectory',
                'aggressive_maneuver',
                'disturbance_rejection'
            ]


@dataclass 
class BenchmarkResults:
    """Results from controller benchmarking"""
    controller_name: str
    scenario: str
    
    # Performance metrics
    mean_position_error: float = 0.0
    max_position_error: float = 0.0
    rms_position_error: float = 0.0
    
    mean_velocity_error: float = 0.0
    max_velocity_error: float = 0.0
    
    # Computational metrics
    mean_planning_time_ms: float = 0.0
    max_planning_time_ms: float = 0.0
    planning_success_rate: float = 0.0
    
    # Control effort metrics
    mean_thrust: float = 0.0
    thrust_variation: float = 0.0
    
    # Stability metrics
    oscillation_metric: float = 0.0
    settling_time: float = 0.0
    
    # Raw data for detailed analysis
    position_errors: List[float] = None
    velocity_errors: List[float] = None
    planning_times: List[float] = None
    timestamps: List[float] = None
    
    def __post_init__(self):
        if self.position_errors is None:
            self.position_errors = []
        if self.velocity_errors is None:
            self.velocity_errors = []
        if self.planning_times is None:
            self.planning_times = []
        if self.timestamps is None:
            self.timestamps = []


class ControllerBenchmark:
    """
    Comprehensive benchmarking framework for trajectory planners
    """
    
    def __init__(self, config: BenchmarkConfig = None):
        self.config = config if config else BenchmarkConfig()
        
        # Initialize controllers
        self.dial_mpc = DIALMPCPlanner()
        self.se3_mpc = SE3MPCPlanner()
        self.geometric_controller = GeometricController()
        self.simulator = DroneSimulator()
        
        # Results storage
        self.results: Dict[str, Dict[str, BenchmarkResults]] = {}
        
        print("Controller Benchmark initialized")
        print(f"  Test scenarios: {self.config.scenarios}")
        print(f"  Test duration: {self.config.test_duration}s each")
    
    def run_full_benchmark(self) -> Dict[str, Dict[str, BenchmarkResults]]:
        """Run complete benchmark suite comparing both controllers"""
        
        print("\n" + "="*60)
        print("🚀 CONTROLLER BENCHMARK: DIAL-MPC vs SE(3) MPC")
        print("="*60)
        print("Validating refactor from legged locomotion to aerial robotics")
        
        controllers = {
            'DIAL-MPC': self.dial_mpc,
            'SE(3)-MPC': self.se3_mpc
        }
        
        for controller_name, planner in controllers.items():
            print(f"\n📊 Testing {controller_name}...")
            self.results[controller_name] = {}
            
            for scenario in self.config.scenarios:
                print(f"  Running scenario: {scenario}")
                result = self._run_scenario_test(planner, controller_name, scenario)
                self.results[controller_name][scenario] = result
                
                # Quick summary
                print(f"    Position error: {result.mean_position_error:.2f}m mean, {result.max_position_error:.2f}m max")
                print(f"    Planning time: {result.mean_planning_time_ms:.1f}ms mean")
        
        # Generate comparison report
        self._generate_comparison_report()
        
        return self.results
    
    def _run_scenario_test(self, planner, controller_name: str, scenario: str) -> BenchmarkResults:
        """Run a single test scenario"""
        
        # Initialize result object
        result = BenchmarkResults(
            controller_name=controller_name,
            scenario=scenario
        )
        
        # Set up scenario parameters
        initial_state, reference_trajectory = self._setup_scenario(scenario)
        
        # Reset planner state
        if hasattr(planner, 'reset_performance_tracking'):
            planner.reset_performance_tracking()
        
        # Run test
        current_state = initial_state
        dt_control = 1.0 / self.config.control_frequency
        dt_planning = 1.0 / self.config.planning_frequency
        
        planning_counter = 0
        current_trajectory = None
        
        position_errors = []
        velocity_errors = []
        planning_times = []
        timestamps = []
        
        test_start_time = time.time()
        
        try:
            while time.time() - test_start_time < self.config.test_duration:
                current_time = time.time() - test_start_time
                
                # Get reference state for this time
                ref_pos, ref_vel = self._get_reference_state(reference_trajectory, current_time)
                
                # Planning update at lower frequency
                if planning_counter % int(self.config.control_frequency / self.config.planning_frequency) == 0:
                    plan_start = time.perf_counter()
                    
                    try:
                        current_trajectory = planner.plan_trajectory(current_state, ref_pos)
                        planning_time = (time.perf_counter() - plan_start) * 1000  # ms
                        planning_times.append(planning_time)
                    except Exception as e:
                        print(f"Planning failed: {e}")
                        planning_times.append(1000.0)  # Large penalty for failures
                
                # Control update
                if current_trajectory and len(current_trajectory.positions) > 0:
                    # Use first waypoint from trajectory
                    desired_pos = current_trajectory.positions[0]
                    desired_vel = current_trajectory.velocities[0] if current_trajectory.velocities is not None else np.zeros(3)
                    desired_acc = current_trajectory.accelerations[0] if current_trajectory.accelerations is not None else np.zeros(3)
                else:
                    # Fallback to reference
                    desired_pos = ref_pos
                    desired_vel = ref_vel
                    desired_acc = np.zeros(3)
                
                # Compute control
                control_output = self.geometric_controller.compute_control(
                    current_state, desired_pos, desired_vel, desired_acc
                )
                
                # Simulate system
                current_state = self.simulator.step(current_state, control_output, dt_control)
                
                # Record metrics
                pos_error = np.linalg.norm(current_state.position - ref_pos)
                vel_error = np.linalg.norm(current_state.velocity - ref_vel)
                
                position_errors.append(pos_error)
                velocity_errors.append(vel_error)
                timestamps.append(current_time)
                
                planning_counter += 1
                time.sleep(dt_control)  # Simulate real-time
                
        except KeyboardInterrupt:
            print("  Test interrupted")
        
        # Compute metrics
        result.position_errors = position_errors
        result.velocity_errors = velocity_errors
        result.planning_times = planning_times
        result.timestamps = timestamps
        
        if position_errors:
            result.mean_position_error = np.mean(position_errors)
            result.max_position_error = np.max(position_errors)
            result.rms_position_error = np.sqrt(np.mean(np.array(position_errors)**2))
        
        if velocity_errors:
            result.mean_velocity_error = np.mean(velocity_errors)
            result.max_velocity_error = np.max(velocity_errors)
        
        if planning_times:
            result.mean_planning_time_ms = np.mean(planning_times)
            result.max_planning_time_ms = np.max(planning_times)
            result.planning_success_rate = np.mean([t < 100.0 for t in planning_times])  # <100ms = success
        
        # Stability metrics
        if len(position_errors) > 100:
            # Oscillation metric: variance of position error derivative
            pos_error_diff = np.diff(position_errors)
            result.oscillation_metric = np.var(pos_error_diff)
            
            # Settling time: time to reach within 5% of final error
            final_error = np.mean(position_errors[-50:])  # Last 50 samples
            threshold = final_error * 1.05
            settled_indices = np.where(np.array(position_errors) < threshold)[0]
            if len(settled_indices) > 0:
                result.settling_time = timestamps[settled_indices[0]]
        
        return result
    
    def _setup_scenario(self, scenario: str) -> Tuple[DroneState, Dict[str, Any]]:
        """Set up test scenario parameters"""
        
        # Common initial state
        initial_state = DroneState(
            timestamp=time.time(),
            position=np.array([0.0, 0.0, 2.0]),
            velocity=np.zeros(3),
            attitude=np.zeros(3),
            angular_velocity=np.zeros(3)
        )
        
        if scenario == 'hover_stability':
            reference = {
                'type': 'static',
                'position': np.array([0.0, 0.0, 2.0]),
                'velocity': np.zeros(3)
            }
            
        elif scenario == 'step_response':
            reference = {
                'type': 'step',
                'initial_pos': np.array([0.0, 0.0, 2.0]),
                'final_pos': np.array([5.0, 5.0, 3.0]),
                'step_time': 2.0
            }
            
        elif scenario == 'circular_trajectory':
            reference = {
                'type': 'circular',
                'center': np.array([0.0, 0.0, 2.0]),
                'radius': 5.0,
                'angular_velocity': 0.5  # rad/s
            }
            
        elif scenario == 'aggressive_maneuver':
            reference = {
                'type': 'figure_eight',
                'center': np.array([0.0, 0.0, 2.0]),
                'radius': 3.0,
                'angular_velocity': 1.0  # rad/s
            }
            
        elif scenario == 'disturbance_rejection':
            reference = {
                'type': 'static_with_disturbance',
                'position': np.array([0.0, 0.0, 2.0]),
                'disturbance_start': 10.0,
                'disturbance_magnitude': 2.0  # m/s wind
            }
            
        else:
            # Default hover
            reference = {
                'type': 'static',
                'position': np.array([0.0, 0.0, 2.0]),
                'velocity': np.zeros(3)
            }
        
        return initial_state, reference
    
    def _get_reference_state(self, reference: Dict[str, Any], time: float) -> Tuple[np.ndarray, np.ndarray]:
        """Get reference position and velocity at given time"""
        
        if reference['type'] == 'static':
            return reference['position'], reference['velocity']
        
        elif reference['type'] == 'step':
            if time < reference['step_time']:
                return reference['initial_pos'], np.zeros(3)
            else:
                return reference['final_pos'], np.zeros(3)
        
        elif reference['type'] == 'circular':
            center = reference['center']
            radius = reference['radius']
            omega = reference['angular_velocity']
            
            pos = center + radius * np.array([
                np.cos(omega * time),
                np.sin(omega * time),
                0.0
            ])
            vel = radius * omega * np.array([
                -np.sin(omega * time),
                np.cos(omega * time),
                0.0
            ])
            return pos, vel
        
        elif reference['type'] == 'figure_eight':
            center = reference['center']
            radius = reference['radius']
            omega = reference['angular_velocity']
            
            pos = center + radius * np.array([
                np.sin(omega * time),
                np.sin(2 * omega * time) / 2,
                0.0
            ])
            vel = radius * omega * np.array([
                np.cos(omega * time),
                np.cos(2 * omega * time),
                0.0
            ])
            return pos, vel
        
        elif reference['type'] == 'static_with_disturbance':
            pos = reference['position']
            
            # Add wind disturbance after certain time
            if time > reference['disturbance_start']:
                # Sinusoidal wind disturbance
                disturbance = reference['disturbance_magnitude'] * np.array([
                    np.sin(2 * np.pi * 0.5 * time),  # 0.5 Hz disturbance
                    np.cos(2 * np.pi * 0.3 * time),  # 0.3 Hz disturbance
                    0.0
                ])
                vel = disturbance
            else:
                vel = np.zeros(3)
                
            return pos, vel
        
        # Default
        return np.zeros(3), np.zeros(3)
    
    def _generate_comparison_report(self) -> None:
        """Generate detailed comparison report"""
        
        print("\n" + "="*60)
        print("📈 BENCHMARK RESULTS SUMMARY")
        print("="*60)
        
        if 'DIAL-MPC' not in self.results or 'SE(3)-MPC' not in self.results:
            print("❌ Incomplete results - cannot generate comparison")
            return
        
        # Compare overall performance
        dial_results = self.results['DIAL-MPC']
        se3_results = self.results['SE(3)-MPC']
        
        print("\n🎯 POSITION TRACKING ACCURACY:")
        print("-" * 40)
        for scenario in self.config.scenarios:
            if scenario in dial_results and scenario in se3_results:
                dial_error = dial_results[scenario].mean_position_error
                se3_error = se3_results[scenario].mean_position_error
                improvement = (dial_error - se3_error) / dial_error * 100
                
                print(f"{scenario:20s}: DIAL-MPC {dial_error:.2f}m, SE(3)-MPC {se3_error:.2f}m ({improvement:+.1f}%)")
        
        print("\n⚡ COMPUTATIONAL PERFORMANCE:")
        print("-" * 40)
        for scenario in self.config.scenarios:
            if scenario in dial_results and scenario in se3_results:
                dial_time = dial_results[scenario].mean_planning_time_ms
                se3_time = se3_results[scenario].mean_planning_time_ms
                speedup = dial_time / se3_time if se3_time > 0 else float('inf')
                
                print(f"{scenario:20s}: DIAL-MPC {dial_time:.1f}ms, SE(3)-MPC {se3_time:.1f}ms ({speedup:.1f}x speedup)")
        
        print("\n🎯 SUCCESS RATES:")
        print("-" * 40)
        for scenario in self.config.scenarios:
            if scenario in dial_results and scenario in se3_results:
                dial_success = dial_results[scenario].planning_success_rate * 100
                se3_success = se3_results[scenario].planning_success_rate * 100
                
                print(f"{scenario:20s}: DIAL-MPC {dial_success:.1f}%, SE(3)-MPC {se3_success:.1f}%")
        
        # Overall recommendation
        overall_dial_error = np.mean([r.mean_position_error for r in dial_results.values()])
        overall_se3_error = np.mean([r.mean_position_error for r in se3_results.values()])
        overall_improvement = (overall_dial_error - overall_se3_error) / overall_dial_error * 100
        
        overall_dial_time = np.mean([r.mean_planning_time_ms for r in dial_results.values()])
        overall_se3_time = np.mean([r.mean_planning_time_ms for r in se3_results.values()])
        overall_speedup = overall_dial_time / overall_se3_time if overall_se3_time > 0 else float('inf')
        
        print("\n" + "="*60)
        print("🏆 OVERALL PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Position Tracking: SE(3)-MPC is {overall_improvement:.1f}% more accurate")
        print(f"Computational Speed: SE(3)-MPC is {overall_speedup:.1f}x faster")
        
        if overall_improvement > 10 and overall_speedup > 1.5:
            print("\n✅ CONCLUSION: SE(3) MPC significantly outperforms DIAL-MPC")
            print("   Refactor from DIAL-MPC to SE(3) MPC is VALIDATED")
        elif overall_improvement > 0:
            print("\n⚠️  CONCLUSION: SE(3) MPC shows modest improvements")
            print("   Refactor may be beneficial but not critical")
        else:
            print("\n❌ CONCLUSION: DIAL-MPC performs better in this test")
            print("   Refactor strategy needs reconsideration")
    
    def save_detailed_results(self, filename: str = "controller_benchmark_results.csv") -> None:
        """Save detailed results to CSV for further analysis"""
        import csv
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = [
                'controller', 'scenario', 'mean_pos_error', 'max_pos_error', 'rms_pos_error',
                'mean_vel_error', 'max_vel_error', 'mean_planning_time_ms', 'max_planning_time_ms',
                'planning_success_rate', 'oscillation_metric', 'settling_time'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for controller_name, scenarios in self.results.items():
                for scenario_name, result in scenarios.items():
                    writer.writerow({
                        'controller': controller_name,
                        'scenario': scenario_name,
                        'mean_pos_error': result.mean_position_error,
                        'max_pos_error': result.max_position_error,
                        'rms_pos_error': result.rms_position_error,
                        'mean_vel_error': result.mean_velocity_error,
                        'max_vel_error': result.max_velocity_error,
                        'mean_planning_time_ms': result.mean_planning_time_ms,
                        'max_planning_time_ms': result.max_planning_time_ms,
                        'planning_success_rate': result.planning_success_rate,
                        'oscillation_metric': result.oscillation_metric,
                        'settling_time': result.settling_time
                    })
        
        print(f"📊 Detailed results saved to {filename}")


def main():
    """Run controller benchmark"""
    
    # Configure benchmark
    config = BenchmarkConfig(
        test_duration=15.0,  # Shorter for quick testing
        scenarios=['hover_stability', 'step_response', 'circular_trajectory']
    )
    
    # Run benchmark
    benchmark = ControllerBenchmark(config)
    results = benchmark.run_full_benchmark()
    
    # Save results
    benchmark.save_detailed_results("results/controller_benchmark_results.csv")
    
    print("\n🎉 Benchmark complete!")
    return results


if __name__ == "__main__":
    main() 