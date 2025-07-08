"""
Integration Tests for Real-Time Performance Under Load

Tests the interaction between DI container, frozen configuration,
and real-time control extensions under various load conditions.
"""

import pytest
import time
import threading
import multiprocessing
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Dict, Any
import psutil
import gc

from dart_planner.common.di_container_v2 import (
    DIContainerV2, ContainerConfig, RegistrationStage, create_container
)
from dart_planner.config.frozen_config import (
    DARTPlannerFrozenConfig, RealTimeConfig, HardwareConfig,
    ConfigurationManager, get_frozen_config
)

# Import real-time control extension (will be built)
try:
    from dart_planner.control.rt_control_extension import (
        RealTimeControlLoop, create_control_loop,
        validate_real_time_requirements, get_real_time_capabilities
    )
    RT_EXTENSION_AVAILABLE = True
except ImportError:
    RT_EXTENSION_AVAILABLE = False
    # Mock for testing without extension
    class RealTimeControlLoop:
        def __init__(self, frequency_hz=400.0, priority=2):
            self.frequency_hz = frequency_hz
            self.priority = priority
            self.running = False
        
        def start(self): self.running = True
        def stop(self): self.running = False
        def is_running(self): return self.running
        def get_stats(self): return {'iteration_count': 100, 'frequency_actual_hz': 400.0}
    
    def create_control_loop(frequency_hz=400.0, priority=2):
        return RealTimeControlLoop(frequency_hz, priority)
    
    def validate_real_time_requirements(frequency_hz, max_jitter_ms=0.1):
        return True
    
    def get_real_time_capabilities():
        return {'platform': 'test', 'max_frequency_hz': 1000}


class MockController:
    """Mock controller for integration testing."""
    
    def __init__(self, config: RealTimeConfig):
        self.config = config
        self.control_count = 0
        self.last_control_time = 0
        self.jitter_samples = []
    
    def control_step(self, state, command):
        """Simulate control step with timing measurement."""
        current_time = time.time()
        
        if self.last_control_time > 0:
            jitter = abs(current_time - self.last_control_time - 1.0/self.config.control_loop_frequency_hz)
            self.jitter_samples.append(jitter * 1000)  # Convert to ms
        
        self.last_control_time = current_time
        self.control_count += 1
        
        # Simulate control computation
        time.sleep(0.001)  # 1ms computation time
        
        return {'thrust': 0.5, 'attitude': [0, 0, 0]}


class MockPlanner:
    """Mock planner for integration testing."""
    
    def __init__(self, config: RealTimeConfig):
        self.config = config
        self.planning_count = 0
        self.last_planning_time = 0
        self.jitter_samples = []
    
    def planning_step(self, state, goal):
        """Simulate planning step with timing measurement."""
        current_time = time.time()
        
        if self.last_planning_time > 0:
            jitter = abs(current_time - self.last_planning_time - 1.0/self.config.planning_loop_frequency_hz)
            self.jitter_samples.append(jitter * 1000)  # Convert to ms
        
        self.last_planning_time = current_time
        self.planning_count += 1
        
        # Simulate planning computation
        time.sleep(0.005)  # 5ms computation time
        
        return {'trajectory': [[0, 0, 0], [1, 1, 1]]}


class MockSafetyMonitor:
    """Mock safety monitor for integration testing."""
    
    def __init__(self, config: HardwareConfig):
        self.config = config
        self.safety_checks = 0
        self.violations = 0
    
    def check_safety(self, state):
        """Simulate safety check."""
        self.safety_checks += 1
        
        # Simulate safety violation
        if state.get('altitude', 0) > self.config.max_altitude_m:
            self.violations += 1
            return False
        
        return True


@pytest.mark.skipif(not RT_EXTENSION_AVAILABLE, reason="RT control extension not available")
class TestRealTimeIntegration:
    """Integration tests for real-time performance under load."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = DARTPlannerFrozenConfig(
            real_time=RealTimeConfig(
                control_loop_frequency_hz=100.0,  # Lower frequency for testing
                planning_loop_frequency_hz=25.0,
                safety_loop_frequency_hz=50.0,
                max_control_latency_ms=5.0,
                max_planning_latency_ms=20.0,
                max_safety_latency_ms=10.0
            ),
            hardware=HardwareConfig(
                max_velocity_mps=15.0,
                max_altitude_m=50.0
            )
        )
        
        # Create DI container
        container_config = ContainerConfig(
            enable_validation=True,
            enable_lifecycle_management=True,
            strict_mode=True
        )
        
        self.container = create_container(container_config)
        
        # Register dependencies
        bootstrap = self.container.bootstrap_stage()
        bootstrap.register_config(DARTPlannerFrozenConfig)
        
        runtime = self.container.runtime_stage()
        runtime.register_service(RealTimeConfig, RealTimeConfig)
        runtime.register_service(HardwareConfig, HardwareConfig)
        runtime.register_service(MockController, MockController)
        runtime.register_service(MockPlanner, MockPlanner)
        runtime.register_service(MockSafetyMonitor, MockSafetyMonitor)
        
        self.container = self.container.build()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if hasattr(self, 'container'):
            self.container.clear()
    
    def test_control_loop_under_load(self):
        """Test control loop performance under CPU load."""
        # Create control loop
        loop = create_control_loop(
            frequency_hz=self.config.real_time.control_loop_frequency_hz,
            priority=90
        )
        
        # Start background CPU load
        def cpu_load():
            while True:
                _ = sum(i * i for i in range(1000))
                time.sleep(0.001)
        
        load_thread = threading.Thread(target=cpu_load, daemon=True)
        load_thread.start()
        
        try:
            # Start control loop
            loop.start()
            time.sleep(1.0)  # Run for 1 second
            loop.stop()
            
            # Get statistics
            stats = loop.get_stats()
            
            # Verify performance
            assert stats['iteration_count'] > 0
            assert stats['frequency_actual_hz'] > self.config.real_time.control_loop_frequency_hz * 0.9
            
            # Check for missed deadlines
            if 'missed_deadlines' in stats:
                missed_rate = stats['missed_deadlines'] / stats['iteration_count']
                assert missed_rate < 0.01  # Less than 1% missed deadlines
                
        finally:
            load_thread.join(timeout=0.1)
    
    def test_multi_threaded_control(self):
        """Test control loop with multiple threads accessing shared resources."""
        controller = self.container.resolve(MockController)
        
        # Create multiple threads that update state
        def control_thread(thread_id):
            for i in range(50):
                state = {'position': [i, i, i], 'velocity': [0.1, 0.1, 0.1]}
                command = {'setpoint': [i+1, i+1, i+1]}
                result = controller.control_step(state, command)
                time.sleep(0.01)
        
        # Start multiple threads
        threads = []
        for i in range(4):
            thread = threading.Thread(target=control_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all threads completed
        assert controller.control_count == 200  # 4 threads * 50 iterations
    
    def test_memory_usage_under_load(self):
        """Test memory usage under sustained load."""
        initial_memory = psutil.Process().memory_info().rss
        
        # Create and run multiple control loops
        loops = []
        for i in range(5):
            loop = create_control_loop(frequency_hz=50.0)
            loops.append(loop)
            loop.start()
        
        # Run for some time
        time.sleep(2.0)
        
        # Stop all loops
        for loop in loops:
            loop.stop()
        
        # Force garbage collection
        gc.collect()
        
        # Check memory usage
        final_memory = psutil.Process().memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024
    
    def test_di_container_performance(self):
        """Test DI container performance under load."""
        # Measure resolution time
        start_time = time.time()
        
        for _ in range(1000):
            controller = self.container.resolve(MockController)
            planner = self.container.resolve(MockPlanner)
            safety = self.container.resolve(MockSafetyMonitor)
        
        resolution_time = time.time() - start_time
        
        # Resolution should be fast (less than 1 second for 1000 resolutions)
        assert resolution_time < 1.0
    
    def test_configuration_validation_performance(self):
        """Test configuration validation performance."""
        # Create complex configuration
        config_data = {
            'real_time': {
                'control_loop_frequency_hz': 400.0,
                'planning_loop_frequency_hz': 25.0,
                'max_control_latency_ms': 2.0
            },
            'hardware': {
                'max_velocity_mps': 15.0,
                'max_altitude_m': 50.0,
                'geofence_polygon': [[0, 0], [10, 0], [10, 10], [0, 10]]
            }
        }
        
        # Measure validation time
        start_time = time.time()
        
        for _ in range(100):
            config = DARTPlannerFrozenConfig(**config_data)
            config.validate_startup()
        
        validation_time = time.time() - start_time
        
        # Validation should be fast (less than 1 second for 100 validations)
        assert validation_time < 1.0
    
    def test_end_to_end_real_time_workflow(self):
        """Test end-to-end real-time workflow."""
        # Resolve all components
        controller = self.container.resolve(MockController)
        planner = self.container.resolve(MockPlanner)
        safety = self.container.resolve(MockSafetyMonitor)
        
        # Simulate real-time workflow
        start_time = time.time()
        iterations = 0
        
        while time.time() - start_time < 2.0:  # Run for 2 seconds
            # Update state
            state = {
                'position': [iterations * 0.1, 0, 0],
                'velocity': [0.1, 0, 0],
                'altitude': iterations * 0.05
            }
            
            # Safety check
            if not safety.check_safety(state):
                break
            
            # Planning step
            goal = {'target': [10, 0, 0]}
            trajectory = planner.planning_step(state, goal)
            
            # Control step
            command = {'setpoint': trajectory['trajectory'][0]}
            control_output = controller.control_step(state, command)
            
            iterations += 1
            time.sleep(0.01)  # 10ms cycle time
        
        # Verify workflow completed
        assert iterations > 0
        assert controller.control_count > 0
        assert planner.planning_count > 0
        assert safety.safety_checks > 0
    
    def test_concurrent_configuration_access(self):
        """Test concurrent access to frozen configuration."""
        config = self.container.resolve(DARTPlannerFrozenConfig)
        
        # Create multiple threads that read configuration
        def config_reader(thread_id):
            for i in range(100):
                _ = config.real_time.control_loop_frequency_hz
                _ = config.hardware.max_velocity_mps
                _ = config.security.enable_authentication
                time.sleep(0.001)
        
        # Start multiple threads
        threads = []
        for i in range(8):
            thread = threading.Thread(target=config_reader, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should complete without errors (immutable config is thread-safe)
        assert True
    
    def test_stress_test_di_container(self):
        """Stress test the DI container with complex dependency graphs."""
        # Create complex dependency scenario
        class ComplexService:
            def __init__(self, controller: MockController, planner: MockPlanner, safety: MockSafetyMonitor):
                self.controller = controller
                self.planner = planner
                self.safety = safety
        
        # Register complex service
        self.container.register_singleton(ComplexService, ComplexService)
        
        # Resolve many times concurrently
        def resolve_complex():
            for _ in range(100):
                service = self.container.resolve(ComplexService)
                assert service.controller is not None
                assert service.planner is not None
                assert service.safety is not None
        
        # Run multiple threads
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(resolve_complex) for _ in range(4)]
            for future in futures:
                future.result()
    
    def test_real_time_requirements_validation(self):
        """Test real-time requirements validation under various conditions."""
        # Test valid requirements
        assert validate_real_time_requirements(400.0, 0.1)
        
        # Test invalid requirements
        assert not validate_real_time_requirements(0.0, 0.1)
        assert not validate_real_time_requirements(400.0, 20.0)
        
        # Test capabilities
        capabilities = get_real_time_capabilities()
        assert 'platform' in capabilities
        assert 'max_frequency_hz' in capabilities
    
    def test_performance_regression(self):
        """Test for performance regressions."""
        # Baseline performance test
        start_time = time.time()
        
        # Create and run control loop
        loop = create_control_loop(frequency_hz=100.0)
        loop.start()
        time.sleep(0.5)
        loop.stop()
        
        baseline_time = time.time() - start_time
        
        # Performance should be consistent (within 20% of baseline)
        # This is a simple regression test - in practice, you'd store baseline metrics
        assert baseline_time < 1.0  # Should complete within 1 second


class TestRealTimeStressTests:
    """Stress tests for real-time components."""
    
    @pytest.mark.slow
    def test_extended_duration_control(self):
        """Test control loop over extended duration."""
        loop = create_control_loop(frequency_hz=50.0)
        
        try:
            loop.start()
            time.sleep(10.0)  # Run for 10 seconds
        finally:
            loop.stop()
        
        stats = loop.get_stats()
        assert stats['iteration_count'] > 400  # Should have many iterations
    
    @pytest.mark.slow
    def test_high_frequency_stress(self):
        """Test high-frequency control loop stress."""
        loop = create_control_loop(frequency_hz=500.0)
        
        try:
            loop.start()
            time.sleep(5.0)  # Run for 5 seconds
        finally:
            loop.stop()
        
        stats = loop.get_stats()
        assert stats['iteration_count'] > 2000  # Should have many iterations
        
        # Check for missed deadlines
        if 'missed_deadlines' in stats:
            missed_rate = stats['missed_deadlines'] / stats['iteration_count']
            assert missed_rate < 0.05  # Less than 5% missed deadlines under stress
    
    def test_memory_leak_detection(self):
        """Test for memory leaks in real-time components."""
        initial_memory = psutil.Process().memory_info().rss
        
        # Create and destroy many control loops
        for _ in range(100):
            loop = create_control_loop(frequency_hz=100.0)
            loop.start()
            time.sleep(0.01)
            loop.stop()
        
        # Force garbage collection
        gc.collect()
        
        final_memory = psutil.Process().memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024


class TestRealTimeIntegrationWithHardware:
    """Integration tests with hardware simulation."""
    
    def test_airsim_integration(self):
        """Test integration with AirSim simulation."""
        # This would test actual AirSim integration
        # For now, we'll simulate the interface
        config = DARTPlannerFrozenConfig(
            simulation=SimulationConfig(enable_airsim=True)
        )
        
        # Verify configuration
        assert config.simulation.enable_airsim is True
        assert config.simulation.airsim_host == "localhost"
        assert config.simulation.airsim_port == 41451
    
    def test_sitl_integration(self):
        """Test integration with SITL simulation."""
        config = DARTPlannerFrozenConfig(
            simulation=SimulationConfig(enable_sitl=True)
        )
        
        # Verify configuration
        assert config.simulation.enable_sitl is True
        assert config.simulation.sitl_host == "localhost"
        assert config.simulation.sitl_port == 5760 