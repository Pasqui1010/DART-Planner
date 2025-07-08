"""
Real-time Latency Testing Framework

Tests the end-to-end latency from planner to actuator to ensure
real-time performance requirements are met.

Requirements:
- Planner-to-actuator path < 50ms at 95th percentile
- End-to-end latency measurement with high precision
- Comprehensive latency profiling and analysis
"""

import asyncio
from dart_planner.common.di_container import get_container
import statistics
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

import numpy as np
import pytest

from dart_planner.common.types import DroneState, Trajectory
from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
from dart_planner.control.geometric_controller import GeometricController
# from dart_planner.hardware.state import HardwareState  # Not used in this test


@dataclass
class LatencyMeasurement:
    """Single latency measurement result"""
    timestamp: float
    planning_latency_ms: float
    control_latency_ms: float
    actuator_latency_ms: float
    total_latency_ms: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class LatencyTestResults:
    """Aggregated latency test results"""
    total_measurements: int
    successful_measurements: int
    success_rate: float
    
    # Latency statistics (ms)
    planning_p50_ms: float
    planning_p95_ms: float
    planning_p99_ms: float
    planning_mean_ms: float
    planning_max_ms: float
    
    control_p50_ms: float
    control_p95_ms: float
    control_p99_ms: float
    control_mean_ms: float
    control_max_ms: float
    
    actuator_p50_ms: float
    actuator_p95_ms: float
    actuator_p99_ms: float
    actuator_mean_ms: float
    actuator_max_ms: float
    
    total_p50_ms: float
    total_p95_ms: float
    total_p99_ms: float
    total_mean_ms: float
    total_max_ms: float
    
    # Performance requirements
    meets_planning_requirement: bool
    meets_control_requirement: bool
    meets_actuator_requirement: bool
    meets_total_requirement: bool
    
    # Detailed breakdown
    measurements: List[LatencyMeasurement]


class RealTimeLatencyTester:
    """Comprehensive real-time latency testing framework"""
    
    def __init__(self, test_duration_seconds: float = 30.0, measurement_frequency_hz: float = 10.0):
        self.test_duration = test_duration_seconds
        self.measurement_frequency = measurement_frequency_hz
        self.measurement_interval = 1.0 / measurement_frequency_hz
        
        # Performance requirements (ms)
        self.planning_p95_threshold = 50.0  # 95th percentile planning latency
        self.control_p95_threshold = 5.0    # 95th percentile control latency
        self.actuator_p95_threshold = 2.0   # 95th percentile actuator latency
        self.total_p95_threshold = 50.0     # 95th percentile total latency
        
        # Initialize components
        self.planner = get_container().create_planner_container().get_se3_planner()
        self.controller = get_container().create_control_container().get_geometric_controller()
        
        # Test state
        self.test_state = DroneState(
            timestamp=time.time(),
            position=np.array([0.0, 0.0, -5.0]),
            velocity=np.array([0.0, 0.0, 0.0]),
            attitude=np.array([1.0, 0.0, 0.0, 0.0]),
            angular_velocity=np.array([0.0, 0.0, 0.0])
        )
        
        # Results storage
        self.measurements: List[LatencyMeasurement] = []
        
    def _generate_test_goal(self, iteration: int) -> np.ndarray:
        """Generate realistic test goals"""
        # Create a circular pattern with varying altitude
        angle = 2 * np.pi * iteration / 100
        radius = 10.0
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        z = -5.0 + 2.0 * np.sin(angle * 2)
        return np.array([x, y, z])
    
    @asynccontextmanager
    async def _measure_latency(self, component_name: str):
        """Context manager for measuring component latency"""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000.0
            # Store for later analysis
            if not hasattr(self, '_current_measurement'):
                self._current_measurement = {}
            self._current_measurement[f'{component_name}_latency_ms'] = latency_ms
    
    async def _simulate_planning_phase(self, current_state: DroneState, goal: np.ndarray) -> Trajectory:
        """Simulate planning phase with latency measurement"""
        async with self._measure_latency('planning'):
            return self.planner.plan_trajectory(current_state, goal)
    
    async def _simulate_control_phase(self, current_state: DroneState, trajectory: Trajectory) -> Dict[str, Any]:
        """Simulate control phase with latency measurement"""
        async with self._measure_latency('control'):
            # Simulate control computation
            if len(trajectory.timestamps) > 0:
                t_current = trajectory.timestamps[0]
                control_cmd = self.controller.compute_control_from_trajectory(
                    current_state, trajectory, t_current
                )
                return control_cmd
            return {}
    
    async def _simulate_actuator_phase(self, control_cmd: Dict[str, Any]) -> bool:
        """Simulate actuator phase with latency measurement"""
        async with self._measure_latency('actuator'):
            # Simulate actuator command processing
            # In real system, this would be motor commands, PWM signals, etc.
            await asyncio.sleep(0.0001)  # 0.1ms actuator processing time
            return True
    
    async def run_latency_test(self) -> LatencyTestResults:
        """Run comprehensive latency test"""
        print(f"🚀 Starting Real-time Latency Test")
        print(f"   Duration: {self.test_duration}s")
        print(f"   Frequency: {self.measurement_frequency}Hz")
        print(f"   Target: <{self.total_p95_threshold}ms 95th percentile")
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < self.test_duration:
            iteration_start = time.time()
            
            # Initialize measurement for this iteration
            self._current_measurement = {}
            measurement_start = time.perf_counter()
            
            try:
                # Generate test goal
                goal = self._generate_test_goal(iteration)
                
                # Phase 1: Planning
                trajectory = await self._simulate_planning_phase(self.test_state, goal)
                
                # Phase 2: Control
                control_cmd = await self._simulate_control_phase(self.test_state, trajectory)
                
                # Phase 3: Actuator
                actuator_success = await self._simulate_actuator_phase(control_cmd)
                
                # Calculate total latency
                total_latency_ms = (time.perf_counter() - measurement_start) * 1000.0
                
                # Record measurement
                measurement = LatencyMeasurement(
                    timestamp=time.time(),
                    planning_latency_ms=self._current_measurement.get('planning_latency_ms', 0.0),
                    control_latency_ms=self._current_measurement.get('control_latency_ms', 0.0),
                    actuator_latency_ms=self._current_measurement.get('actuator_latency_ms', 0.0),
                    total_latency_ms=total_latency_ms,
                    success=actuator_success and trajectory is not None
                )
                
                self.measurements.append(measurement)
                
                # Progress update
                if iteration % 50 == 0:
                    elapsed = time.time() - start_time
                    progress = (elapsed / self.test_duration) * 100
                    print(f"   Progress: {progress:.1f}% - Total: {total_latency_ms:.1f}ms")
                
            except Exception as e:
                # Record failed measurement
                total_latency_ms = (time.perf_counter() - measurement_start) * 1000.0
                measurement = LatencyMeasurement(
                    timestamp=time.time(),
                    planning_latency_ms=self._current_measurement.get('planning_latency_ms', 0.0),
                    control_latency_ms=self._current_measurement.get('control_latency_ms', 0.0),
                    actuator_latency_ms=self._current_measurement.get('actuator_latency_ms', 0.0),
                    total_latency_ms=total_latency_ms,
                    success=False,
                    error_message=str(e)
                )
                self.measurements.append(measurement)
            
            # Maintain measurement frequency
            elapsed = time.time() - iteration_start
            if elapsed < self.measurement_interval:
                await asyncio.sleep(self.measurement_interval - elapsed)
            
            iteration += 1
        
        return self._analyze_results()
    
    def _analyze_results(self) -> LatencyTestResults:
        """Analyze latency measurements and generate results"""
        if not self.measurements:
            raise ValueError("No measurements recorded")
        
        # Extract latency arrays
        planning_latencies = [m.planning_latency_ms for m in self.measurements]
        control_latencies = [m.control_latency_ms for m in self.measurements]
        actuator_latencies = [m.actuator_latency_ms for m in self.measurements]
        total_latencies = [m.total_latency_ms for m in self.measurements]
        
        # Calculate statistics
        def calculate_percentiles(values: List[float]) -> Dict[str, float]:
            if not values:
                return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0, 'mean': 0.0, 'max': 0.0}
            return {
                'p50': np.percentile(values, 50),
                'p95': np.percentile(values, 95),
                'p99': np.percentile(values, 99),
                'mean': np.mean(values),
                'max': np.max(values)
            }
        
        planning_stats = calculate_percentiles(planning_latencies)
        control_stats = calculate_percentiles(control_latencies)
        actuator_stats = calculate_percentiles(actuator_latencies)
        total_stats = calculate_percentiles(total_latencies)
        
        # Check requirements
        meets_planning = planning_stats['p95'] <= self.planning_p95_threshold
        meets_control = control_stats['p95'] <= self.control_p95_threshold
        meets_actuator = actuator_stats['p95'] <= self.actuator_p95_threshold
        meets_total = total_stats['p95'] <= self.total_p95_threshold
        
        # Calculate success rate
        successful_measurements = sum(1 for m in self.measurements if m.success)
        success_rate = successful_measurements / len(self.measurements)
        
        return LatencyTestResults(
            total_measurements=len(self.measurements),
            successful_measurements=successful_measurements,
            success_rate=success_rate,
            
            # Planning statistics
            planning_p50_ms=planning_stats['p50'],
            planning_p95_ms=planning_stats['p95'],
            planning_p99_ms=planning_stats['p99'],
            planning_mean_ms=planning_stats['mean'],
            planning_max_ms=planning_stats['max'],
            
            # Control statistics
            control_p50_ms=control_stats['p50'],
            control_p95_ms=control_stats['p95'],
            control_p99_ms=control_stats['p99'],
            control_mean_ms=control_stats['mean'],
            control_max_ms=control_stats['max'],
            
            # Actuator statistics
            actuator_p50_ms=actuator_stats['p50'],
            actuator_p95_ms=actuator_stats['p95'],
            actuator_p99_ms=actuator_stats['p99'],
            actuator_mean_ms=actuator_stats['mean'],
            actuator_max_ms=actuator_stats['max'],
            
            # Total statistics
            total_p50_ms=total_stats['p50'],
            total_p95_ms=total_stats['p95'],
            total_p99_ms=total_stats['p99'],
            total_mean_ms=total_stats['mean'],
            total_max_ms=total_stats['max'],
            
            # Requirements
            meets_planning_requirement=meets_planning,
            meets_control_requirement=meets_control,
            meets_actuator_requirement=meets_actuator,
            meets_total_requirement=meets_total,
            
            # Detailed measurements
            measurements=self.measurements
        )
    
    def print_results(self, results: LatencyTestResults):
        """Print comprehensive latency test results"""
        print(f"\n" + "="*80)
        print("📊 REAL-TIME LATENCY TEST RESULTS")
        print("="*80)
        
        print(f"\n📈 Test Summary:")
        print(f"   Total Measurements: {results.total_measurements}")
        print(f"   Success Rate: {results.success_rate*100:.1f}%")
        print(f"   Test Duration: {self.test_duration:.1f}s")
        
        print(f"\n⚡ Latency Statistics (ms):")
        print(f"   {'Component':<12} {'Mean':<8} {'P50':<8} {'P95':<8} {'P99':<8} {'Max':<8} {'Status':<8}")
        print(f"   {'-'*12} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
        
        # Planning
        status = "✅ PASS" if results.meets_planning_requirement else "❌ FAIL"
        print(f"   {'Planning':<12} {results.planning_mean_ms:<8.1f} {results.planning_p50_ms:<8.1f} "
              f"{results.planning_p95_ms:<8.1f} {results.planning_p99_ms:<8.1f} {results.planning_max_ms:<8.1f} {status:<8}")
        
        # Control
        status = "✅ PASS" if results.meets_control_requirement else "❌ FAIL"
        print(f"   {'Control':<12} {results.control_mean_ms:<8.1f} {results.control_p50_ms:<8.1f} "
              f"{results.control_p95_ms:<8.1f} {results.control_p99_ms:<8.1f} {results.control_max_ms:<8.1f} {status:<8}")
        
        # Actuator
        status = "✅ PASS" if results.meets_actuator_requirement else "❌ FAIL"
        print(f"   {'Actuator':<12} {results.actuator_mean_ms:<8.1f} {results.actuator_p50_ms:<8.1f} "
              f"{results.actuator_p95_ms:<8.1f} {results.actuator_p99_ms:<8.1f} {results.actuator_max_ms:<8.1f} {status:<8}")
        
        # Total
        status = "✅ PASS" if results.meets_total_requirement else "❌ FAIL"
        print(f"   {'TOTAL':<12} {results.total_mean_ms:<8.1f} {results.total_p50_ms:<8.1f} "
              f"{results.total_p95_ms:<8.1f} {results.total_p99_ms:<8.1f} {results.total_max_ms:<8.1f} {status:<8}")
        
        print(f"\n🎯 Performance Requirements:")
        print(f"   Planning P95: {results.planning_p95_ms:.1f}ms (≤{self.planning_p95_threshold}ms) "
              f"{'✅' if results.meets_planning_requirement else '❌'}")
        print(f"   Control P95: {results.control_p95_ms:.1f}ms (≤{self.control_p95_threshold}ms) "
              f"{'✅' if results.meets_control_requirement else '❌'}")
        print(f"   Actuator P95: {results.actuator_p95_ms:.1f}ms (≤{self.actuator_p95_threshold}ms) "
              f"{'✅' if results.meets_actuator_requirement else '❌'}")
        print(f"   Total P95: {results.total_p95_ms:.1f}ms (≤{self.total_p95_threshold}ms) "
              f"{'✅' if results.meets_total_requirement else '❌'}")
        
        print(f"\n📊 Overall Status:")
        all_passed = (results.meets_planning_requirement and 
                     results.meets_control_requirement and 
                     results.meets_actuator_requirement and 
                     results.meets_total_requirement)
        
        if all_passed:
            print("   🎉 ALL LATENCY REQUIREMENTS MET!")
        else:
            print("   ⚠️  SOME LATENCY REQUIREMENTS FAILED")
            failed_components = []
            if not results.meets_planning_requirement:
                failed_components.append("Planning")
            if not results.meets_control_requirement:
                failed_components.append("Control")
            if not results.meets_actuator_requirement:
                failed_components.append("Actuator")
            if not results.meets_total_requirement:
                failed_components.append("Total")
            print(f"   Failed components: {', '.join(failed_components)}")


# Pytest test functions
@pytest.mark.asyncio
async def test_real_time_latency_requirements():
    """Test that the system meets real-time latency requirements"""
    tester = RealTimeLatencyTester(test_duration_seconds=10.0, measurement_frequency_hz=20.0)
    results = await tester.run_latency_test()
    tester.print_results(results)
    
    # Assert requirements
    assert results.meets_total_requirement, (
        f"Total latency P95 {results.total_p95_ms:.1f}ms exceeds {tester.total_p95_threshold}ms requirement"
    )
    assert results.meets_planning_requirement, (
        f"Planning latency P95 {results.planning_p95_ms:.1f}ms exceeds {tester.planning_p95_threshold}ms requirement"
    )
    assert results.success_rate >= 0.95, (
        f"Success rate {results.success_rate*100:.1f}% below 95% requirement"
    )


@pytest.mark.asyncio
async def test_latency_consistency():
    """Test that latency is consistent over time"""
    tester = RealTimeLatencyTester(test_duration_seconds=15.0, measurement_frequency_hz=10.0)
    results = await tester.run_latency_test()
    
    # Check for latency degradation (P99 should not be more than 3x P50)
    latency_ratio = results.total_p99_ms / results.total_p50_ms
    assert latency_ratio <= 3.0, (
        f"Latency inconsistency detected: P99/P50 ratio {latency_ratio:.1f} exceeds 3.0"
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_extended_latency_stability():
    """Extended test for latency stability over longer periods"""
    tester = RealTimeLatencyTester(test_duration_seconds=60.0, measurement_frequency_hz=5.0)
    results = await tester.run_latency_test()
    tester.print_results(results)
    
    # All requirements must be met
    assert results.meets_total_requirement
    assert results.meets_planning_requirement
    assert results.meets_control_requirement
    assert results.meets_actuator_requirement
    assert results.success_rate >= 0.95


if __name__ == "__main__":
    # Run standalone test
    async def main():
        tester = RealTimeLatencyTester(test_duration_seconds=30.0, measurement_frequency_hz=10.0)
        results = await tester.run_latency_test()
        tester.print_results(results)
        
        # Exit with error code if requirements not met
        if not (results.meets_total_requirement and results.meets_planning_requirement):
            exit(1)
    
    asyncio.run(main()) 
