"""
Performance testing utilities for DART-Planner.

This module provides utilities for performance benchmarking and regression testing
to ensure that critical algorithms maintain their performance characteristics.
"""

import time
import statistics
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass
from contextlib import contextmanager
import pytest


@dataclass
class PerformanceResult:
    """Result of a performance benchmark."""
    name: str
    mean_time: float
    std_time: float
    min_time: float
    max_time: float
    iterations: int
    threshold: Optional[float] = None
    passed: bool = True

    def __str__(self) -> str:
        result = f"{self.name}: {self.mean_time:.6f}s ± {self.std_time:.6f}s"
        if self.threshold:
            result += f" (threshold: {self.threshold:.6f}s)"
            result += " ✅" if self.passed else " ❌"
        return result


class PerformanceBenchmark:
    """Performance benchmarking utility for testing critical algorithms."""
    
    def __init__(self, name: str, threshold_seconds: Optional[float] = None):
        self.name = name
        self.threshold_seconds = threshold_seconds
        self.times: List[float] = []
        
    def benchmark(self, func: Callable, *args, iterations: int = 100, **kwargs) -> PerformanceResult:
        """Benchmark a function and return performance results."""
        self.times.clear()
        
        # Warm up
        for _ in range(10):
            func(*args, **kwargs)
        
        # Actual benchmark
        for _ in range(iterations):
            start_time = time.perf_counter()
            func(*args, **kwargs)
            end_time = time.perf_counter()
            self.times.append(end_time - start_time)
        
        # Calculate statistics
        mean_time = statistics.mean(self.times)
        std_time = statistics.stdev(self.times) if len(self.times) > 1 else 0.0
        min_time = min(self.times)
        max_time = max(self.times)
        
        # Check against threshold
        passed = True
        if self.threshold_seconds is not None:
            passed = mean_time <= self.threshold_seconds
        
        return PerformanceResult(
            name=self.name,
            mean_time=mean_time,
            std_time=std_time,
            min_time=min_time,
            max_time=max_time,
            iterations=iterations,
            threshold=self.threshold_seconds,
            passed=passed
        )
    
    def assert_performance(self, func: Callable, *args, iterations: int = 100, **kwargs):
        """Benchmark a function and assert it meets performance requirements."""
        result = self.benchmark(func, *args, iterations=iterations, **kwargs)
        
        if not result.passed:
            raise AssertionError(
                f"Performance threshold exceeded for {self.name}: "
                f"{result.mean_time:.6f}s > {self.threshold_seconds:.6f}s"
            )
        
        return result


@contextmanager
def performance_context(name: str, threshold_seconds: Optional[float] = None):
    """Context manager for measuring performance of code blocks."""
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        if threshold_seconds is not None:
            assert duration <= threshold_seconds, (
                f"Performance threshold exceeded for {name}: "
                f"{duration:.6f}s > {threshold_seconds:.6f}s"
            )


def benchmark_planner_performance(planner, trajectory_length: int = 100) -> PerformanceResult:
    """Benchmark trajectory planning performance."""
    benchmark = PerformanceBenchmark("trajectory_planning", threshold_seconds=0.1)
    
    def plan_trajectory():
        # Create a simple trajectory planning scenario
        start_state = None  # Will be set by the planner
        goal_state = None   # Will be set by the planner
        planner.plan_trajectory(start_state, goal_state, trajectory_length)
    
    return benchmark.benchmark(plan_trajectory, iterations=50)


def benchmark_controller_performance(controller, state) -> PerformanceResult:
    """Benchmark controller computation performance."""
    benchmark = PerformanceBenchmark("controller_computation", threshold_seconds=0.001)
    
    def compute_control():
        controller.compute_control(state)
    
    return benchmark.benchmark(compute_control, iterations=1000)


def benchmark_motor_mixing_performance(motor_mixer, control_command) -> PerformanceResult:
    """Benchmark motor mixing performance."""
    benchmark = PerformanceBenchmark("motor_mixing", threshold_seconds=0.0001)
    
    def mix_motors():
        motor_mixer.mix_motors(control_command)
    
    return benchmark.benchmark(mix_motors, iterations=10000)


def benchmark_state_estimation_performance(estimator, sensor_data) -> PerformanceResult:
    """Benchmark state estimation performance."""
    benchmark = PerformanceBenchmark("state_estimation", threshold_seconds=0.01)
    
    def estimate_state():
        estimator.update(sensor_data)
    
    return benchmark.benchmark(estimate_state, iterations=100)


def benchmark_communication_performance(interface, message) -> PerformanceResult:
    """Benchmark communication performance."""
    benchmark = PerformanceBenchmark("communication", threshold_seconds=0.001)
    
    def send_message():
        interface.send_message(message)
    
    return benchmark.benchmark(send_message, iterations=1000)


def benchmark_serialization_performance(serializer, data) -> PerformanceResult:
    """Benchmark serialization performance."""
    benchmark = PerformanceBenchmark("serialization", threshold_seconds=0.001)
    
    def serialize():
        serializer.serialize(data)
    
    return benchmark.benchmark(serialize, iterations=1000)


def benchmark_deserialization_performance(serializer, serialized_data) -> PerformanceResult:
    """Benchmark deserialization performance."""
    benchmark = PerformanceBenchmark("deserialization", threshold_seconds=0.001)
    
    def deserialize():
        serializer.deserialize(serialized_data)
    
    return benchmark.benchmark(deserialize, iterations=1000)


def benchmark_coordinate_transform_performance(transformer, coordinates) -> PerformanceResult:
    """Benchmark coordinate transformation performance."""
    benchmark = PerformanceBenchmark("coordinate_transform", threshold_seconds=0.0001)
    
    def transform():
        transformer.transform(coordinates)
    
    return benchmark.benchmark(transform, iterations=10000)


def benchmark_memory_usage(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """Benchmark memory usage of a function."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Run function
    result = func(*args, **kwargs)
    
    final_memory = process.memory_info().rss
    memory_used = final_memory - initial_memory
    
    return {
        "initial_memory_mb": initial_memory / 1024 / 1024,
        "final_memory_mb": final_memory / 1024 / 1024,
        "memory_used_mb": memory_used / 1024 / 1024,
        "result": result
    }


def benchmark_cpu_usage(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """Benchmark CPU usage of a function."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    # Get initial CPU times
    initial_cpu_times = process.cpu_times()
    
    # Run function
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    end_time = time.perf_counter()
    
    # Get final CPU times
    final_cpu_times = process.cpu_times()
    
    # Calculate CPU usage
    user_time = final_cpu_times.user - initial_cpu_times.user
    system_time = final_cpu_times.system - initial_cpu_times.system
    total_cpu_time = user_time + system_time
    wall_time = end_time - start_time
    
    return {
        "wall_time": wall_time,
        "user_time": user_time,
        "system_time": system_time,
        "total_cpu_time": total_cpu_time,
        "cpu_efficiency": total_cpu_time / wall_time if wall_time > 0 else 0,
        "result": result
    }


# Pytest fixtures for performance testing
@pytest.fixture
def performance_benchmark():
    """Provide a performance benchmark fixture for testing."""
    return PerformanceBenchmark("test_benchmark")


@pytest.fixture
def performance_context_manager():
    """Provide a performance context manager fixture for testing."""
    return performance_context


# Utility functions for test data generation
def generate_large_trajectory(length: int = 1000) -> List[Dict[str, Any]]:
    """Generate a large trajectory for performance testing."""
    import numpy as np
    
    return [
        {
            "timestamp": i * 0.1,
            "position": np.random.rand(3).tolist(),
            "velocity": np.random.rand(3).tolist(),
            "attitude": np.random.rand(3).tolist(),
            "angular_velocity": np.random.rand(3).tolist(),
        }
        for i in range(length)
    ]


def generate_large_sensor_data(length: int = 1000) -> List[Dict[str, Any]]:
    """Generate large sensor data for performance testing."""
    import numpy as np
    
    return [
        {
            "accelerometer": np.random.rand(3).tolist(),
            "gyroscope": np.random.rand(3).tolist(),
            "magnetometer": np.random.rand(3).tolist(),
            "barometer": np.random.uniform(90000, 110000),
            "gps": {
                "latitude": np.random.uniform(-90, 90),
                "longitude": np.random.uniform(-180, 180),
                "altitude": np.random.uniform(0, 1000),
                "satellites": np.random.randint(4, 12),
            },
            "timestamp": i * 0.01,
        }
        for i in range(length)
    ]


def generate_large_control_commands(length: int = 1000) -> List[Dict[str, Any]]:
    """Generate large control commands for performance testing."""
    import numpy as np
    
    return [
        {
            "throttle": np.random.uniform(0, 1),
            "roll": np.random.uniform(-1, 1),
            "pitch": np.random.uniform(-1, 1),
            "yaw": np.random.uniform(-1, 1),
            "mode": np.random.choice(["MANUAL", "AUTO", "LOITER"]),
            "timestamp": i * 0.01,
        }
        for i in range(length)
    ] 