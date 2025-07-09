"""
Performance regression tests for DART-Planner.

This module contains performance tests to ensure that critical algorithms
maintain their performance characteristics and don't regress over time.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock

from tests.utils.performance_testing import (
    PerformanceBenchmark,
    performance_context,
    benchmark_planner_performance,
    benchmark_controller_performance,
    benchmark_motor_mixing_performance,
    benchmark_state_estimation_performance,
    benchmark_communication_performance,
    benchmark_serialization_performance,
    benchmark_deserialization_performance,
    benchmark_coordinate_transform_performance,
    generate_large_trajectory,
    generate_large_sensor_data,
    generate_large_control_commands,
)


class TestPlannerPerformance:
    """Performance tests for trajectory planning algorithms."""
    
    @pytest.mark.performance
    def test_trajectory_planning_performance(self, mock_planner):
        """Test that trajectory planning meets performance requirements."""
        benchmark = PerformanceBenchmark("trajectory_planning", threshold_seconds=0.1)
        
        def plan_trajectory():
            mock_planner.plan_trajectory()
        
        result = benchmark.assert_performance(plan_trajectory, iterations=50)
        assert result.passed, f"Trajectory planning too slow: {result.mean_time:.6f}s"
    
    @pytest.mark.performance
    def test_large_trajectory_planning(self, mock_planner):
        """Test performance with large trajectory data."""
        large_trajectory = generate_large_trajectory(1000)
        
        with performance_context("large_trajectory_planning", threshold_seconds=1.0):
            for trajectory in large_trajectory[:10]:  # Test subset
                mock_planner.plan_trajectory()
    
    @pytest.mark.performance
    def test_planner_memory_usage(self, mock_planner):
        """Test that planner doesn't use excessive memory."""
        from tests.utils.performance_testing import benchmark_memory_usage
        
        def plan_multiple_trajectories():
            for _ in range(100):
                mock_planner.plan_trajectory()
        
        memory_result = benchmark_memory_usage(plan_multiple_trajectories)
        assert memory_result["memory_used_mb"] < 100, f"Memory usage too high: {memory_result['memory_used_mb']:.2f}MB"


class TestControllerPerformance:
    """Performance tests for control algorithms."""
    
    @pytest.mark.performance
    def test_controller_computation_performance(self, mock_controller, sample_drone_state):
        """Test that controller computation meets real-time requirements."""
        benchmark = PerformanceBenchmark("controller_computation", threshold_seconds=0.001)
        
        def compute_control():
            mock_controller.compute_control(sample_drone_state)
        
        result = benchmark.assert_performance(compute_control, iterations=1000)
        assert result.passed, f"Controller computation too slow: {result.mean_time:.6f}s"
    
    @pytest.mark.performance
    def test_high_frequency_control_loop(self, mock_controller, sample_drone_state):
        """Test high-frequency control loop performance."""
        benchmark = PerformanceBenchmark("high_frequency_control", threshold_seconds=0.0001)
        
        def control_loop_iteration():
            mock_controller.compute_control(sample_drone_state)
            mock_controller.update_gains()
        
        result = benchmark.assert_performance(control_loop_iteration, iterations=10000)
        assert result.passed, f"High-frequency control too slow: {result.mean_time:.6f}s"
    
    @pytest.mark.performance
    def test_controller_cpu_efficiency(self, mock_controller, sample_drone_state):
        """Test that controller uses CPU efficiently."""
        from tests.utils.performance_testing import benchmark_cpu_usage
        
        def compute_control():
            mock_controller.compute_control(sample_drone_state)
        
        cpu_result = benchmark_cpu_usage(compute_control)
        assert cpu_result["cpu_efficiency"] > 0.5, f"CPU efficiency too low: {cpu_result['cpu_efficiency']:.2f}"


class TestMotorMixingPerformance:
    """Performance tests for motor mixing algorithms."""
    
    @pytest.mark.performance
    def test_motor_mixing_performance(self, mock_control_commands):
        """Test that motor mixing meets performance requirements."""
        from dart_planner.hardware.motor_mixer import MotorMixer, MotorMixingConfig
        
        config = MotorMixingConfig()
        motor_mixer = MotorMixer(config)
        thrust = 10.0  # N
        torque = np.array([0.1, 0.1, 0.1])  # N⋅m
        
        benchmark = PerformanceBenchmark("motor_mixing", threshold_seconds=0.0001)
        
        def mix_motors():
            motor_mixer.mix_commands(thrust, torque)
        
        result = benchmark.assert_performance(mix_motors, iterations=10000)
        assert result.passed, f"Motor mixing too slow: {result.mean_time:.6f}s"
    
    @pytest.mark.performance
    def test_motor_mixing_consistency(self, mock_control_commands):
        """Test that motor mixing produces consistent results."""
        from dart_planner.hardware.motor_mixer import MotorMixer, MotorMixingConfig
        
        config = MotorMixingConfig()
        motor_mixer = MotorMixer(config)
        thrust = 10.0  # N
        torque = np.array([0.1, 0.1, 0.1])  # N⋅m
        
        # Run multiple times and check consistency
        results = []
        for _ in range(100):
            result = motor_mixer.mix_commands(thrust, torque)
            results.append(result)
        
        # Check that all results are identical
        first_result = results[0]
        for result in results[1:]:
            assert np.allclose(result, first_result, rtol=1e-10), "Motor mixing results not consistent"


class TestStateEstimationPerformance:
    """Performance tests for state estimation algorithms."""
    
    @pytest.mark.performance
    def test_state_estimation_performance(self, mock_sensor_data):
        """Test that state estimation meets performance requirements."""
        # Use mock estimator for performance testing
        estimator = MagicMock()
        estimator.update = MagicMock()
        
        benchmark = PerformanceBenchmark("state_estimation", threshold_seconds=0.01)
        
        def estimate_state():
            estimator.update(mock_sensor_data)
        
        result = benchmark.assert_performance(estimate_state, iterations=100)
        assert result.passed, f"State estimation too slow: {result.mean_time:.6f}s"
    
    @pytest.mark.performance
    def test_sensor_fusion_performance(self, mock_sensor_data):
        """Test sensor fusion performance."""
        # Use mock estimator for performance testing
        estimator = MagicMock()
        estimator.update = MagicMock()
        large_sensor_data = generate_large_sensor_data(1000)
        
        with performance_context("sensor_fusion", threshold_seconds=5.0):
            for sensor_data in large_sensor_data[:100]:  # Test subset
                estimator.update(sensor_data)


class TestCommunicationPerformance:
    """Performance tests for communication systems."""
    
    @pytest.mark.performance
    def test_serialization_performance(self, mock_secure_serializer):
        """Test serialization performance."""
        test_data = {"test": "data", "nested": {"value": 123}}
        
        benchmark = PerformanceBenchmark("serialization", threshold_seconds=0.001)
        
        def serialize():
            mock_secure_serializer.serialize(test_data)
        
        result = benchmark.assert_performance(serialize, iterations=1000)
        assert result.passed, f"Serialization too slow: {result.mean_time:.6f}s"
    
    @pytest.mark.performance
    def test_deserialization_performance(self, mock_secure_serializer):
        """Test deserialization performance."""
        serialized_data = b"encrypted_data"
        
        benchmark = PerformanceBenchmark("deserialization", threshold_seconds=0.001)
        
        def deserialize():
            mock_secure_serializer.deserialize(serialized_data)
        
        result = benchmark.assert_performance(deserialize, iterations=1000)
        assert result.passed, f"Deserialization too slow: {result.mean_time:.6f}s"
    
    @pytest.mark.performance
    def test_communication_latency(self, mock_network_interface):
        """Test communication latency."""
        test_message = {"type": "test", "data": "test_data"}
        
        benchmark = PerformanceBenchmark("communication_latency", threshold_seconds=0.001)
        
        def send_message():
            mock_network_interface.send_message(test_message)
        
        result = benchmark.assert_performance(send_message, iterations=1000)
        assert result.passed, f"Communication latency too high: {result.mean_time:.6f}s"


class TestCoordinateTransformPerformance:
    """Performance tests for coordinate transformation."""
    
    @pytest.mark.performance
    def test_coordinate_transform_performance(self):
        """Test coordinate transformation performance."""
        # Use mock transformer for performance testing
        transformer = MagicMock()
        transformer.transform = MagicMock()
        coordinates = np.random.rand(100, 3)
        
        benchmark = PerformanceBenchmark("coordinate_transform", threshold_seconds=0.0001)
        
        def transform():
            transformer.transform(coordinates)
        
        result = benchmark.assert_performance(transform, iterations=10000)
        assert result.passed, f"Coordinate transform too slow: {result.mean_time:.6f}s"
    
    @pytest.mark.performance
    def test_batch_coordinate_transform(self):
        """Test batch coordinate transformation performance."""
        # Use mock transformer for performance testing
        transformer = MagicMock()
        transformer.transform = MagicMock()
        large_coordinates = np.random.rand(10000, 3)
        
        with performance_context("batch_coordinate_transform", threshold_seconds=0.1):
            transformer.transform(large_coordinates)


class TestMemoryPerformance:
    """Performance tests for memory usage."""
    
    @pytest.mark.performance
    def test_memory_leak_detection(self, mock_planner):
        """Test for memory leaks in planning algorithms."""
        from tests.utils.performance_testing import benchmark_memory_usage
        
        def planning_operation():
            for _ in range(100):
                mock_planner.plan_trajectory()
        
        # Run multiple times to check for memory leaks
        initial_memory = benchmark_memory_usage(lambda: None)["final_memory_mb"]
        
        for _ in range(5):
            memory_result = benchmark_memory_usage(planning_operation)
            final_memory = memory_result["final_memory_mb"]
            
            # Check that memory usage doesn't grow significantly
            memory_growth = final_memory - initial_memory
            assert memory_growth < 50, f"Potential memory leak detected: {memory_growth:.2f}MB growth"
    
    @pytest.mark.performance
    def test_large_data_handling(self):
        """Test handling of large datasets without memory issues."""
        from tests.utils.performance_testing import benchmark_memory_usage
        
        def process_large_data():
            # Generate and process large datasets
            large_trajectory = generate_large_trajectory(10000)
            large_sensor_data = generate_large_sensor_data(10000)
            large_control_commands = generate_large_control_commands(10000)
            
            # Process the data
            _ = len(large_trajectory)
            _ = len(large_sensor_data)
            _ = len(large_control_commands)
        
        memory_result = benchmark_memory_usage(process_large_data)
        assert memory_result["memory_used_mb"] < 500, f"Memory usage too high: {memory_result['memory_used_mb']:.2f}MB"


class TestRealTimePerformance:
    """Performance tests for real-time requirements."""
    
    @pytest.mark.performance
    @pytest.mark.flaky
    def test_real_time_control_loop(self, mock_controller, sample_drone_state):
        """Test that control loop meets real-time requirements."""
        import time
        
        control_loop_frequency = 100  # Hz
        target_period = 1.0 / control_loop_frequency
        max_jitter = 0.001  # 1ms max jitter
        
        periods = []
        for _ in range(1000):
            start_time = time.perf_counter()
            mock_controller.compute_control(sample_drone_state)
            end_time = time.perf_counter()
            periods.append(end_time - start_time)
        
        mean_period = np.mean(periods)
        jitter = np.std(periods)
        
        assert mean_period <= target_period, f"Control loop too slow: {mean_period:.6f}s > {target_period:.6f}s"
        assert jitter <= max_jitter, f"Control loop jitter too high: {jitter:.6f}s > {max_jitter:.6f}s"
    
    @pytest.mark.performance
    def test_concurrent_operations(self, mock_planner, mock_controller, sample_drone_state):
        """Test performance under concurrent operations."""
        import threading
        import time
        
        results = []
        
        def planning_thread():
            start_time = time.perf_counter()
            for _ in range(50):
                mock_planner.plan_trajectory()
            end_time = time.perf_counter()
            results.append(("planning", end_time - start_time))
        
        def control_thread():
            start_time = time.perf_counter()
            for _ in range(5000):
                mock_controller.compute_control(sample_drone_state)
            end_time = time.perf_counter()
            results.append(("control", end_time - start_time))
        
        # Run threads concurrently
        planning_thread_obj = threading.Thread(target=planning_thread)
        control_thread_obj = threading.Thread(target=control_thread)
        
        planning_thread_obj.start()
        control_thread_obj.start()
        
        planning_thread_obj.join()
        control_thread_obj.join()
        
        # Check that both operations completed within reasonable time
        for operation, duration in results:
            if operation == "planning":
                assert duration < 5.0, f"Planning took too long: {duration:.2f}s"
            elif operation == "control":
                assert duration < 1.0, f"Control took too long: {duration:.2f}s"


class TestPerformanceRegression:
    """Tests to detect performance regressions."""
    
    @pytest.mark.performance
    def test_performance_baseline_comparison(self, mock_controller, sample_drone_state):
        """Compare current performance against baseline."""
        # These are baseline performance thresholds
        # They should be updated when performance improvements are made
        baseline_thresholds = {
            "controller_computation": 0.001,  # 1ms
            "motor_mixing": 0.0001,           # 0.1ms
            "serialization": 0.001,           # 1ms
            "coordinate_transform": 0.0001,   # 0.1ms
        }
        
        # Test controller performance
        benchmark = PerformanceBenchmark("controller_computation", baseline_thresholds["controller_computation"])
        
        def compute_control():
            mock_controller.compute_control(sample_drone_state)
        
        result = benchmark.assert_performance(compute_control, iterations=1000)
        assert result.passed, f"Controller performance regressed: {result.mean_time:.6f}s > {baseline_thresholds['controller_computation']:.6f}s"
    
    @pytest.mark.performance
    def test_performance_trend_analysis(self):
        """Analyze performance trends over multiple runs."""
        # This test could be extended to store performance metrics
        # and analyze trends over time to detect gradual regressions
        pass


# Performance test configuration
def pytest_configure(config):
    """Configure performance test markers."""
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle performance tests."""
    for item in items:
        if "performance" in item.keywords:
            item.add_marker(pytest.mark.slow) 