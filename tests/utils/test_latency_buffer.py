"""
Test transport-delay compensation buffer functionality.

This test suite validates the latency buffer implementation for
estimator-controller communication delay compensation.
"""

import time
import pytest
import numpy as np
from unittest.mock import Mock

from dart_planner.utils.latency_buffer import (
    LatencyBuffer, 
    DroneStateLatencyBuffer, 
    create_latency_buffer
)
from dart_planner.common.types import DroneState
from dart_planner.common.units import Q_


class TestLatencyBuffer:
    """Test basic latency buffer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.delay_s = 0.025  # 25ms delay
        self.dt = 0.005       # 5ms control loop period
        self.buffer = LatencyBuffer(self.delay_s, self.dt)
        
    def test_buffer_initialization(self):
        """Test buffer is properly initialized."""
        assert self.buffer.delay_s == 0.025
        assert self.buffer.dt == 0.005
        assert self.buffer.required_size == 5  # 25ms / 5ms = 5 samples
        assert len(self.buffer.buffer) == 0
        assert not self.buffer.is_ready()
        
    def test_buffer_fill_sequence(self):
        """Test buffer fills up correctly and provides delayed data."""
        # Push data until buffer is full
        for i in range(5):
            result = self.buffer.push(f"data_{i}")
            # Buffer not full yet, should return current data
            assert result == f"data_{i}"
            if i < 4:
                assert not self.buffer.is_ready()
            else:
                assert self.buffer.is_ready()
        # Next push returns the first value pushed
        result = self.buffer.push("data_5")
        assert result == "data_0"
        assert self.buffer.is_ready()
        # Next push returns the second value pushed
        result = self.buffer.push("data_6")
        assert result == "data_1"
                
    def test_continuous_delayed_output(self):
        """Test continuous delayed output after buffer is full."""
        # Fill buffer
        for i in range(5):
            self.buffer.push(f"data_{i}")
            
        # Continue pushing - should always return delayed data
        for i in range(5, 10):
            result = self.buffer.push(f"data_{i}")
            expected_delayed = f"data_{i-5}"
            assert result == expected_delayed
            
    def test_timestamp_tracking(self):
        """Test timestamp tracking and actual delay calculation."""
        start_time = time.time()
        
        # Fill buffer
        for i in range(5):
            self.buffer.push(f"data_{i}", start_time + i * 0.001)
            
        # Push one more to get delayed data
        result = self.buffer.push("data_5", start_time + 0.005)
        
        assert result == "data_0"
        assert abs(self.buffer.actual_delay_s - 0.005) < 0.001
        
    def test_statistics(self):
        """Test buffer statistics collection."""
        # Fill buffer and push some more
        for i in range(7):
            self.buffer.push(f"data_{i}")
        stats = self.buffer.get_statistics()
        assert stats['requested_delay_s'] == 0.025
        assert stats['total_samples'] == 7
        assert stats['missed_samples'] == 5  # First 5 samples before buffer full
        assert stats['buffer_size'] == 5
        assert stats['fill_percentage'] == 100.0
        
    def test_reset_functionality(self):
        """Test buffer reset functionality."""
        # Fill buffer
        for i in range(5):
            self.buffer.push(f"data_{i}")
            
        assert self.buffer.is_ready()
        
        # Reset
        self.buffer.reset()
        
        assert not self.buffer.is_ready()
        assert len(self.buffer.buffer) == 0
        assert self.buffer.total_samples == 0
        assert self.buffer.missed_samples == 0
        
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test with very small delay
        small_buffer = LatencyBuffer(0.001, 0.005)  # 1ms delay, 5ms period
        assert small_buffer.required_size == 1
        
        # Test with delay smaller than dt
        tiny_buffer = LatencyBuffer(0.002, 0.005)  # 2ms delay, 5ms period
        assert tiny_buffer.required_size == 1  # Should round up to 1
        
        # Test with very large delay
        large_buffer = LatencyBuffer(1.0, 0.005)  # 1s delay, 5ms period
        assert large_buffer.required_size == 200
        
    def test_max_buffer_size_limit(self):
        """Test maximum buffer size limit."""
        # Create buffer with small max size
        limited_buffer = LatencyBuffer(1.0, 0.005, max_buffer_size=10)
        assert limited_buffer.buffer_size == 10  # Should be limited
        # Should still work correctly
        for i in range(10):
            result = limited_buffer.push(f"data_{i}")
            assert result == f"data_{i}"
        for i in range(10, 15):
            result = limited_buffer.push(f"data_{i}")
            assert result == f"data_{i-10}"


class TestDroneStateLatencyBuffer:
    """Test specialized drone state latency buffer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.delay_s = 0.025
        self.dt = 0.005
        self.buffer = DroneStateLatencyBuffer(self.delay_s, self.dt)
        
    def create_mock_drone_state(self, position, velocity, timestamp=0.0):
        """Create a mock drone state for testing."""
        state = Mock(spec=DroneState)
        state.position = Q_(np.array(position), 'm')
        state.velocity = Q_(np.array(velocity), 'm/s')
        state.attitude = Q_(np.array([0.0, 0.0, 0.0]), 'rad')
        state.angular_velocity = Q_(np.zeros(3), 'rad/s')
        state.timestamp = timestamp
        return state
        
    def test_drone_state_validation(self):
        """Test that invalid states are rejected."""
        # Test with object missing required attributes
        class IncompleteState:
            pass
        invalid_state = IncompleteState()
        with pytest.raises(ValueError, match="State must have position and velocity attributes"):
            self.buffer.push(invalid_state)
            
    def test_drone_state_delay_compensation(self):
        """Test delay compensation with drone states."""
        # Create sequence of drone states
        states = []
        for i in range(5):
            pos = [i * 0.1, i * 0.1, i * 0.1]
            vel = [i * 0.01, i * 0.01, i * 0.01]
            states.append(self.create_mock_drone_state(pos, vel, timestamp=i * 0.005))
        # Push states and verify delayed output
        for i, state in enumerate(states):
            result = self.buffer.push(state)
            assert result == state
        # Next push returns the first state
        delayed = self.buffer.push(self.create_mock_drone_state([0,0,0],[0,0,0]))
        assert np.allclose(delayed.position.magnitude, states[0].position.magnitude)
        assert np.allclose(delayed.velocity.magnitude, states[0].velocity.magnitude)

    def test_drone_state_continuous_operation(self):
        """Test continuous operation with drone states."""
        # Fill buffer first
        for i in range(5):
            state = self.create_mock_drone_state([i, i, i], [i*0.1, i*0.1, i*0.1])
            self.buffer.push(state)
            
        # Continue pushing - should get delayed states
        for i in range(5, 10):
            current_state = self.create_mock_drone_state([i, i, i], [i*0.1, i*0.1, i*0.1])
            delayed_state = self.buffer.push(current_state)
            
            # Should get state from 5 samples ago
            expected_pos = [i-5, i-5, i-5]
            expected_vel = [(i-5)*0.1, (i-5)*0.1, (i-5)*0.1]
            
            assert np.allclose(delayed_state.position.magnitude, expected_pos)
            assert np.allclose(delayed_state.velocity.magnitude, expected_vel)


class TestLatencyBufferFactory:
    """Test factory function for creating latency buffers."""
    
    def test_create_generic_buffer(self):
        """Test creating generic latency buffer."""
        buffer = create_latency_buffer(25.0, 5.0, "generic")
        assert isinstance(buffer, LatencyBuffer)
        assert buffer.delay_s == 0.025
        assert buffer.dt == 0.005
        
    def test_create_drone_state_buffer(self):
        """Test creating drone state latency buffer."""
        buffer = create_latency_buffer(25.0, 5.0, "drone_state")
        assert isinstance(buffer, DroneStateLatencyBuffer)
        assert buffer.delay_s == 0.025
        assert buffer.dt == 0.005
        
    def test_create_buffer_with_different_delays(self):
        """Test creating buffers with different delay values."""
        # Test 10ms delay
        buffer_10ms = create_latency_buffer(10.0, 5.0)
        assert buffer_10ms.delay_s == 0.01
        assert buffer_10ms.required_size == 2
        
        # Test 50ms delay
        buffer_50ms = create_latency_buffer(50.0, 5.0)
        assert buffer_50ms.delay_s == 0.05
        assert buffer_50ms.required_size == 10


class TestLatencyBufferPerformance:
    """Test latency buffer performance characteristics."""
    
    def test_buffer_performance_under_load(self):
        """Test buffer performance with many samples."""
        buffer = LatencyBuffer(0.025, 0.005, max_buffer_size=1000)
        # Push many samples quickly
        start_time = time.time()
        for i in range(1000):
            buffer.push(f"data_{i}")
        end_time = time.time()
        # Should complete quickly (less than 1 second for 1000 samples)
        assert end_time - start_time < 1.0
        # Verify correct delayed output
        assert buffer.get_delayed_data() == "data_994"  # 1000 - 5 = 995th push returns data_994

    def test_memory_usage(self):
        """Test that buffer doesn't grow beyond max size."""
        buffer = LatencyBuffer(0.025, 0.005, max_buffer_size=10)
        # Push more samples than max buffer size
        for i in range(100):
            buffer.push(f"data_{i}")
        # Buffer should not exceed max size
        assert len(buffer.buffer) <= 10
        # Should still provide correct delayed output
        assert buffer.get_delayed_data() == "data_94"  # 100 - 5 = 95th push returns data_94


if __name__ == "__main__":
    pytest.main([__file__]) 