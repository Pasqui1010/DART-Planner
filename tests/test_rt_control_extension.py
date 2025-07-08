"""
Tests for Real-Time Control Extension

Tests the Cython-based real-time control loop with strict deadline enforcement
and minimal jitter for high-performance drone control.
"""

import pytest
import time
import threading
import numpy as np
from unittest.mock import Mock, patch

# Import the extension (will be built by setup_rt_control.py)
try:
    from dart_planner.control.rt_control_extension import (
        RealTimeControlLoop, create_control_loop,
        validate_real_time_requirements, get_real_time_capabilities,
        PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_CRITICAL,
        LOOP_IDLE, LOOP_RUNNING, LOOP_STOPPING, LOOP_ERROR
    )
    RT_EXTENSION_AVAILABLE = True
except ImportError:
    RT_EXTENSION_AVAILABLE = False
    # Mock classes for testing without extension
    class RealTimeControlLoop:
        def __init__(self, frequency_hz=400.0, priority=2):
            self.frequency_hz = frequency_hz
            self.priority = priority
            self.running = False
            self.state = LOOP_IDLE
    
    def create_control_loop(frequency_hz=400.0, priority=2):
        return RealTimeControlLoop(frequency_hz, priority)
    
    def validate_real_time_requirements(frequency_hz, max_jitter_ms=0.1):
        return True
    
    def get_real_time_capabilities():
        return {'platform': 'unknown', 'max_frequency_hz': 1000}


@pytest.mark.skipif(not RT_EXTENSION_AVAILABLE, reason="RT control extension not available")
class TestRealTimeControlLoop:
    """Test real-time control loop functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.loop = None
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.loop and self.loop.is_running():
            self.loop.stop()
    
    def test_initialization(self):
        """Test control loop initialization."""
        loop = RealTimeControlLoop(frequency_hz=400.0, priority=PRIORITY_HIGH)
        
        assert loop.frequency_hz == 400.0
        assert loop.priority == PRIORITY_HIGH
        assert not loop.is_running()
        assert loop.get_state() == LOOP_IDLE
    
    def test_start_stop(self):
        """Test starting and stopping the control loop."""
        loop = RealTimeControlLoop(frequency_hz=100.0)  # Lower frequency for testing
        
        # Start loop
        loop.start()
        assert loop.is_running()
        assert loop.get_state() == LOOP_RUNNING
        
        # Wait a bit for loop to run
        time.sleep(0.1)
        
        # Stop loop
        loop.stop()
        assert not loop.is_running()
        assert loop.get_state() == LOOP_IDLE
    
    def test_state_updates(self):
        """Test state update functionality."""
        loop = RealTimeControlLoop(frequency_hz=100.0)
        
        # Update state
        position = [1.0, 2.0, 3.0]
        velocity = [0.1, 0.2, 0.3]
        attitude = [0.1, 0.2, 0.3]
        angular_velocity = [0.01, 0.02, 0.03]
        
        loop.update_state(position, velocity, attitude, angular_velocity)
        
        # Verify state was updated (access internal state for testing)
        assert loop.current_state.valid
        assert loop.current_state.position[0] == 1.0
        assert loop.current_state.position[1] == 2.0
        assert loop.current_state.position[2] == 3.0
    
    def test_command_updates(self):
        """Test command update functionality."""
        loop = RealTimeControlLoop(frequency_hz=100.0)
        
        # Update command
        position_setpoint = [5.0, 6.0, 7.0]
        velocity_setpoint = [0.5, 0.6, 0.7]
        attitude_setpoint = [0.5, 0.6, 0.7]
        angular_velocity_setpoint = [0.05, 0.06, 0.07]
        thrust = 0.8
        
        loop.update_command(
            position_setpoint, velocity_setpoint,
            attitude_setpoint, angular_velocity_setpoint, thrust
        )
        
        # Verify command was updated
        assert loop.current_command.valid
        assert loop.current_command.position_setpoint[0] == 5.0
        assert loop.current_command.thrust == 0.8
    
    def test_gain_setting(self):
        """Test control gain setting."""
        loop = RealTimeControlLoop(frequency_hz=100.0)
        
        # Set gains
        kp_pos = [2.0, 2.1, 2.2]
        ki_pos = [0.1, 0.11, 0.12]
        kd_pos = [0.5, 0.51, 0.52]
        kp_att = [8.0, 8.1, 8.2]
        ki_att = [0.1, 0.11, 0.12]
        kd_att = [0.5, 0.51, 0.52]
        
        loop.set_gains(kp_pos, ki_pos, kd_pos, kp_att, ki_att, kd_att)
        
        # Verify gains were set
        assert loop.gains.kp_pos[0] == 2.0
        assert loop.gains.kp_pos[1] == 2.1
        assert loop.gains.kp_att[0] == 8.0
    
    def test_callback_functionality(self):
        """Test callback functionality."""
        loop = RealTimeControlLoop(frequency_hz=100.0)
        
        # Mock callbacks
        state_callback = Mock()
        command_callback = Mock()
        error_callback = Mock()
        
        loop.set_state_callback(state_callback)
        loop.set_command_callback(command_callback)
        loop.set_error_callback(error_callback)
        
        # Update state and command
        loop.update_state([1.0, 2.0, 3.0], [0.1, 0.2, 0.3], [0.1, 0.2, 0.3], [0.01, 0.02, 0.03])
        loop.update_command([5.0, 6.0, 7.0], [0.5, 0.6, 0.7], [0.5, 0.6, 0.7], [0.05, 0.06, 0.07], 0.8)
        
        # Start loop briefly to trigger callbacks
        loop.start()
        time.sleep(0.05)  # Wait for a few iterations
        loop.stop()
        
        # Verify callbacks were called
        assert state_callback.called
        assert command_callback.called
    
    def test_statistics_collection(self):
        """Test statistics collection."""
        loop = RealTimeControlLoop(frequency_hz=100.0)
        
        # Start loop and let it run
        loop.start()
        time.sleep(0.2)  # Let it run for 200ms
        loop.stop()
        
        # Get statistics
        stats = loop.get_stats()
        
        # Verify statistics
        assert 'iteration_count' in stats
        assert 'frequency_actual_hz' in stats
        assert 'mean_execution_time_ms' in stats
        assert 'jitter_rms_ms' in stats
        assert 'success_rate' in stats
        
        # Should have some iterations
        assert stats['iteration_count'] > 0
        assert stats['frequency_actual_hz'] > 0
    
    def test_deadline_enforcement(self):
        """Test deadline enforcement."""
        loop = RealTimeControlLoop(frequency_hz=1000.0)  # High frequency to test deadlines
        
        # Start loop
        loop.start()
        time.sleep(0.1)  # Run for 100ms
        loop.stop()
        
        # Get statistics
        stats = loop.get_stats()
        
        # Check if deadlines were missed (depends on system performance)
        assert 'missed_deadlines' in stats
        assert stats['missed_deadlines'] >= 0
    
    def test_priority_levels(self):
        """Test different priority levels."""
        priorities = [PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_CRITICAL]
        
        for priority in priorities:
            loop = RealTimeControlLoop(frequency_hz=100.0, priority=priority)
            assert loop.priority == priority
            loop.stop()


class TestControlLoopFactory:
    """Test control loop factory function."""
    
    def test_create_control_loop(self):
        """Test creating control loops with factory function."""
        loop = create_control_loop(frequency_hz=400.0, priority=PRIORITY_HIGH)
        
        assert isinstance(loop, RealTimeControlLoop)
        assert loop.frequency_hz == 400.0
        assert loop.priority == PRIORITY_HIGH
    
    def test_create_control_loop_defaults(self):
        """Test creating control loop with defaults."""
        loop = create_control_loop()
        
        assert isinstance(loop, RealTimeControlLoop)
        assert loop.frequency_hz == 400.0
        assert loop.priority == PRIORITY_HIGH


class TestRealTimeValidation:
    """Test real-time requirement validation."""
    
    def test_validate_real_time_requirements_valid(self):
        """Test validation with valid requirements."""
        # Valid requirements
        assert validate_real_time_requirements(400.0, 0.1) is True
        assert validate_real_time_requirements(1000.0, 0.05) is True
    
    def test_validate_real_time_requirements_invalid_frequency(self):
        """Test validation with invalid frequency."""
        # Invalid frequencies
        assert validate_real_time_requirements(0.0, 0.1) is False
        assert validate_real_time_requirements(-100.0, 0.1) is False
        assert validate_real_time_requirements(2000.0, 0.1) is False  # Too high
    
    def test_validate_real_time_requirements_invalid_jitter(self):
        """Test validation with invalid jitter."""
        # Jitter too high relative to period
        assert validate_real_time_requirements(100.0, 20.0) is False  # 20ms jitter for 10ms period
    
    def test_get_real_time_capabilities(self):
        """Test getting real-time capabilities."""
        capabilities = get_real_time_capabilities()
        
        # Verify required keys
        required_keys = [
            'platform', 'max_frequency_hz', 'min_period_ms',
            'max_jitter_ms', 'deadline_margin_ms', 'priority_levels'
        ]
        
        for key in required_keys:
            assert key in capabilities
        
        # Verify priority levels
        priority_levels = capabilities['priority_levels']
        assert 'LOW' in priority_levels
        assert 'NORMAL' in priority_levels
        assert 'HIGH' in priority_levels
        assert 'CRITICAL' in priority_levels


class TestControlLoopPerformance:
    """Test control loop performance characteristics."""
    
    @pytest.mark.slow
    def test_frequency_accuracy(self):
        """Test that the control loop maintains accurate frequency."""
        target_frequency = 100.0
        loop = RealTimeControlLoop(frequency_hz=target_frequency)
        
        # Start loop
        loop.start()
        time.sleep(1.0)  # Run for 1 second
        loop.stop()
        
        # Get statistics
        stats = loop.get_stats()
        actual_frequency = stats['frequency_actual_hz']
        
        # Frequency should be within 5% of target
        frequency_error = abs(actual_frequency - target_frequency) / target_frequency
        assert frequency_error < 0.05, f"Frequency error {frequency_error:.3f} exceeds 5%"
    
    @pytest.mark.slow
    def test_jitter_characteristics(self):
        """Test jitter characteristics."""
        loop = RealTimeControlLoop(frequency_hz=100.0)
        
        # Start loop
        loop.start()
        time.sleep(0.5)  # Run for 500ms
        loop.stop()
        
        # Get statistics
        stats = loop.get_stats()
        jitter_rms = stats['jitter_rms_ms']
        
        # Jitter should be reasonable (less than 1ms for 100Hz)
        assert jitter_rms < 1.0, f"Jitter RMS {jitter_rms:.3f}ms exceeds 1ms"
    
    @pytest.mark.slow
    def test_execution_time_consistency(self):
        """Test execution time consistency."""
        loop = RealTimeControlLoop(frequency_hz=100.0)
        
        # Start loop
        loop.start()
        time.sleep(0.5)  # Run for 500ms
        loop.stop()
        
        # Get statistics
        stats = loop.get_stats()
        mean_time = stats['mean_execution_time_ms']
        max_time = stats['max_execution_time_ms']
        
        # Max execution time should not be more than 3x mean
        if mean_time > 0:
            time_ratio = max_time / mean_time
            assert time_ratio < 3.0, f"Execution time ratio {time_ratio:.2f} exceeds 3.0"


class TestControlLoopThreading:
    """Test control loop threading behavior."""
    
    def test_thread_safety(self):
        """Test thread safety of control loop operations."""
        loop = RealTimeControlLoop(frequency_hz=100.0)
        
        # Create multiple threads that update state/command
        def update_state_thread():
            for i in range(10):
                loop.update_state([i, i+1, i+2], [0.1, 0.2, 0.3], [0.1, 0.2, 0.3], [0.01, 0.02, 0.03])
                time.sleep(0.01)
        
        def update_command_thread():
            for i in range(10):
                loop.update_command([i*2, i*2+1, i*2+2], [0.5, 0.6, 0.7], [0.5, 0.6, 0.7], [0.05, 0.06, 0.07], 0.8)
                time.sleep(0.01)
        
        # Start threads
        state_thread = threading.Thread(target=update_state_thread)
        command_thread = threading.Thread(target=update_command_thread)
        
        state_thread.start()
        command_thread.start()
        
        # Wait for threads to complete
        state_thread.join()
        command_thread.join()
        
        # Should not have crashed
        assert True
    
    def test_concurrent_start_stop(self):
        """Test concurrent start/stop operations."""
        loop = RealTimeControlLoop(frequency_hz=100.0)
        
        # Create threads that start/stop the loop
        def start_stop_thread():
            for i in range(5):
                loop.start()
                time.sleep(0.01)
                loop.stop()
                time.sleep(0.01)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=start_stop_thread)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should not have crashed
        assert True


# Integration tests
class TestControlLoopIntegration:
    """Integration tests for control loop with real control algorithms."""
    
    def test_pid_control_integration(self):
        """Test integration with PID control algorithms."""
        loop = RealTimeControlLoop(frequency_hz=100.0)
        
        # Set reasonable gains
        kp_pos = [2.0, 2.0, 2.0]
        ki_pos = [0.1, 0.1, 0.1]
        kd_pos = [0.5, 0.5, 0.5]
        kp_att = [8.0, 8.0, 8.0]
        ki_att = [0.1, 0.1, 0.1]
        kd_att = [0.5, 0.5, 0.5]
        
        loop.set_gains(kp_pos, ki_pos, kd_pos, kp_att, ki_att, kd_att)
        
        # Set initial state and command
        loop.update_state([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
        loop.update_command([1.0, 1.0, 1.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], 0.5)
        
        # Start loop
        loop.start()
        time.sleep(0.1)  # Run for 100ms
        loop.stop()
        
        # Should have run without errors
        stats = loop.get_stats()
        assert stats['iteration_count'] > 0
        assert stats['success_rate'] > 0.9  # Should have high success rate 