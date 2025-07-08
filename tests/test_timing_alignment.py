"""
Tests for timing alignment functionality.
"""

import pytest
import time
import numpy as np
from unittest.mock import Mock, patch

from dart_planner.common.timing_alignment import (
    TimingManager, 
    TimingConfig, 
    ControllerThrottler,
    TimingMode,
    get_timing_manager,
    reset_timing_manager
)
from dart_planner.common.types import Trajectory


class TestTimingConfig:
    """Test timing configuration."""
    
    def test_default_config(self):
        """Test default timing configuration."""
        config = TimingConfig()
        assert config.control_frequency == 400.0
        assert config.planning_frequency == 50.0
        assert config.mode == TimingMode.ADAPTIVE
        assert config.enable_throttling is True
        assert config.enable_interpolation is True
    
    def test_custom_config(self):
        """Test custom timing configuration."""
        config = TimingConfig(
            control_frequency=200.0,
            planning_frequency=25.0,
            mode=TimingMode.PLANNER_DRIVEN,
            enable_throttling=False
        )
        assert config.control_frequency == 200.0
        assert config.planning_frequency == 25.0
        assert config.mode == TimingMode.PLANNER_DRIVEN
        assert config.enable_throttling is False


class TestTimingManager:
    """Test timing manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TimingConfig(
            control_frequency=100.0,  # 10ms dt
            planning_frequency=20.0,  # 50ms dt
            max_planning_latency=0.05,
            min_planning_interval=0.01
        )
        self.timing_manager = TimingManager(self.config)
    
    def test_initialization(self):
        """Test timing manager initialization."""
        assert self.timing_manager.control_dt == 0.01  # 1/100 Hz
        assert self.timing_manager.planning_dt == 0.05  # 1/20 Hz
        assert self.timing_manager.throttling_events == 0
    
    def test_get_planner_dt(self):
        """Test planner dt calculation."""
        dt = self.timing_manager.get_planner_dt()
        assert dt == 0.01  # Should be 1/control_frequency
    
    def test_should_plan_no_throttling(self):
        """Test planning decision without throttling."""
        self.timing_manager.config.enable_throttling = False
        assert self.timing_manager.should_plan(time.time()) is True
    
    def test_should_plan_with_throttling(self):
        """Test planning decision with throttling."""
        current_time = time.time()
        
        # First call should allow planning
        assert self.timing_manager.should_plan(current_time) is True
        
        # Second call immediately after should be throttled
        assert self.timing_manager.should_plan(current_time) is False
        
        # Call after minimum interval should be allowed
        future_time = current_time + 0.02  # 20ms later
        assert self.timing_manager.should_plan(future_time) is True
    
    def test_should_plan_with_latency_throttling(self):
        """Test planning throttling due to high latency."""
        current_time = time.time()
        
        # Simulate high planning latency
        self.timing_manager.planning_latency = 0.1  # 100ms, above threshold
        
        assert self.timing_manager.should_plan(current_time) is False
        assert self.timing_manager.throttling_events == 1
    
    def test_should_control(self):
        """Test control execution decision."""
        current_time = time.time()
        
        # First call should allow control
        assert self.timing_manager.should_control(current_time) is True
        
        # Second call immediately after should be throttled
        assert self.timing_manager.should_control(current_time) is False
        
        # Call after control dt should be allowed
        future_time = current_time + 0.015  # 15ms later
        assert self.timing_manager.should_control(future_time) is True
    
    def test_update_planning_timing(self):
        """Test planning timing updates."""
        current_time = time.time()
        planning_duration = 0.03
        
        self.timing_manager.update_planning_timing(current_time, planning_duration)
        
        assert self.timing_manager.last_plan_time == current_time
        assert self.timing_manager.planning_latency == planning_duration
        assert len(self.timing_manager.planning_times) == 1
        assert self.timing_manager.planning_times[0] == planning_duration
    
    def test_update_control_timing(self):
        """Test control timing updates."""
        current_time = time.time()
        
        self.timing_manager.update_control_timing(current_time)
        
        assert self.timing_manager.last_control_time == current_time
        assert len(self.timing_manager.control_times) == 1
        assert self.timing_manager.control_times[0] == current_time
    
    def test_get_timing_stats(self):
        """Test timing statistics."""
        # Add some planning times
        self.timing_manager.planning_times = [0.01, 0.02, 0.03]
        self.timing_manager.throttling_events = 2
        
        stats = self.timing_manager.get_timing_stats()
        
        assert stats["avg_planning_time"] == 0.02
        assert stats["max_planning_time"] == 0.03
        assert stats["throttling_events"] == 2
        assert stats["control_dt"] == 0.01
        assert stats["planning_dt"] == 0.05
    
    def test_reset_stats(self):
        """Test statistics reset."""
        # Add some data
        self.timing_manager.planning_times = [0.01, 0.02]
        self.timing_manager.control_times = [time.time()]
        self.timing_manager.throttling_events = 1
        self.timing_manager.planning_latency = 0.05
        
        self.timing_manager.reset_stats()
        
        assert len(self.timing_manager.planning_times) == 0
        assert len(self.timing_manager.control_times) == 0
        assert self.timing_manager.throttling_events == 0
        assert self.timing_manager.planning_latency == 0.0


class TestControllerThrottler:
    """Test controller throttler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TimingConfig(control_frequency=100.0)
        self.timing_manager = TimingManager(self.config)
        self.throttler = ControllerThrottler(self.timing_manager)
    
    def test_initialization(self):
        """Test controller throttler initialization."""
        assert self.throttler.timing_manager == self.timing_manager
        assert self.throttler.current_trajectory is None
    
    def test_should_execute_control(self):
        """Test control execution decision."""
        current_time = time.time()
        
        # Should delegate to timing manager
        assert self.throttler.should_execute_control(current_time) == \
               self.timing_manager.should_control(current_time)
    
    def test_get_control_state_no_trajectory(self):
        """Test control state retrieval without trajectory."""
        current_time = time.time()
        
        state = self.throttler.get_control_state(current_time)
        assert state is None
    
    def test_update_trajectory(self):
        """Test trajectory update."""
        # Create a mock trajectory
        trajectory = Mock(spec=Trajectory)
        trajectory.timestamps = [0.0, 0.1, 0.2]
        trajectory.positions = [np.array([0, 0, 0]), np.array([1, 1, 1]), np.array([2, 2, 2])]
        trajectory.velocities = [np.array([0, 0, 0]), np.array([1, 1, 1]), np.array([2, 2, 2])]
        trajectory.attitudes = [np.array([0, 0, 0]), np.array([0.1, 0.1, 0.1]), np.array([0.2, 0.2, 0.2])]
        
        self.throttler.update_trajectory(trajectory)
        
        assert self.throttler.current_trajectory == trajectory
    
    def test_get_throttling_info(self):
        """Test throttling information retrieval."""
        info = self.throttler.get_throttling_info()
        
        assert info["has_trajectory"] is False
        assert info["trajectory_length"] == 0
        assert "timing_stats" in info


class TestGlobalTimingManager:
    """Test global timing manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_timing_manager()
    
    def test_get_timing_manager_default(self):
        """Test getting default timing manager."""
        with patch('dart_planner.config.frozen_config.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.hardware.control_frequency = 200.0
            mock_config.hardware.planning_frequency = 25.0
            mock_config.hardware.max_planning_latency = 0.1
            mock_config.hardware.min_planning_interval = 0.02
            mock_config.hardware.enable_controller_throttling = True
            mock_config.hardware.enable_trajectory_interpolation = True
            mock_get_config.return_value = mock_config
            
            timing_manager = get_timing_manager()
            
            assert timing_manager.config.control_frequency == 200.0
            assert timing_manager.config.planning_frequency == 25.0
            assert timing_manager.config.max_planning_latency == 0.1
            assert timing_manager.config.enable_throttling is True
    
    def test_get_timing_manager_custom_config(self):
        """Test getting timing manager with custom config."""
        custom_config = TimingConfig(control_frequency=150.0)
        
        timing_manager = get_timing_manager(custom_config)
        
        assert timing_manager.config.control_frequency == 150.0
    
    def test_reset_timing_manager(self):
        """Test timing manager reset."""
        # Get a timing manager
        timing_manager1 = get_timing_manager()
        
        # Reset
        reset_timing_manager()
        
        # Get another timing manager
        timing_manager2 = get_timing_manager()
        
        # Should be different instances
        assert timing_manager1 is not timing_manager2


class TestTrajectoryInterpolation:
    """Test trajectory interpolation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TimingConfig(enable_interpolation=True)
        self.timing_manager = TimingManager(self.config)
    
    def test_interpolate_trajectory_none(self):
        """Test interpolation with None trajectory."""
        result = self.timing_manager.interpolate_trajectory(None, 0.0)
        assert result is None
    
    def test_interpolate_trajectory_empty(self):
        """Test interpolation with empty trajectory."""
        trajectory = Mock(spec=Trajectory)
        trajectory.timestamps = []
        
        result = self.timing_manager.interpolate_trajectory(trajectory, 0.0)
        assert result is None
    
    def test_interpolate_trajectory_before_start(self):
        """Test interpolation before trajectory start."""
        trajectory = Mock(spec=Trajectory)
        trajectory.timestamps = [1.0, 2.0]
        trajectory.positions = [np.array([1, 1, 1]), np.array([2, 2, 2])]
        trajectory.velocities = [np.array([0, 0, 0]), np.array([1, 1, 1])]
        trajectory.attitudes = [np.array([0, 0, 0]), np.array([0.1, 0.1, 0.1])]
        
        result = self.timing_manager.interpolate_trajectory(trajectory, 0.5)
        
        assert result is not None
        np.testing.assert_array_equal(result[:3], np.array([1, 1, 1]))  # Position
        np.testing.assert_array_equal(result[3:6], np.array([0, 0, 0]))  # Velocity
        np.testing.assert_array_equal(result[6:9], np.array([0, 0, 0]))  # Attitude
    
    def test_interpolate_trajectory_after_end(self):
        """Test interpolation after trajectory end."""
        trajectory = Mock(spec=Trajectory)
        trajectory.timestamps = [1.0, 2.0]
        trajectory.positions = [np.array([1, 1, 1]), np.array([2, 2, 2])]
        trajectory.velocities = [np.array([0, 0, 0]), np.array([1, 1, 1])]
        trajectory.attitudes = [np.array([0, 0, 0]), np.array([0.1, 0.1, 0.1])]
        
        result = self.timing_manager.interpolate_trajectory(trajectory, 3.0)
        
        assert result is not None
        np.testing.assert_array_equal(result[:3], np.array([2, 2, 2]))  # Position
        np.testing.assert_array_equal(result[3:6], np.array([1, 1, 1]))  # Velocity
        np.testing.assert_array_equal(result[6:9], np.array([0.1, 0.1, 0.1]))  # Attitude
    
    def test_interpolate_trajectory_middle(self):
        """Test interpolation in the middle of trajectory."""
        trajectory = Mock(spec=Trajectory)
        trajectory.timestamps = [0.0, 1.0]
        trajectory.positions = [np.array([0, 0, 0]), np.array([1, 1, 1])]
        trajectory.velocities = [np.array([0, 0, 0]), np.array([1, 1, 1])]
        trajectory.attitudes = [np.array([0, 0, 0]), np.array([0.1, 0.1, 0.1])]
        
        result = self.timing_manager.interpolate_trajectory(trajectory, 0.5)
        
        assert result is not None
        np.testing.assert_array_almost_equal(result[:3], np.array([0.5, 0.5, 0.5]))  # Position
        np.testing.assert_array_almost_equal(result[3:6], np.array([0.5, 0.5, 0.5]))  # Velocity
        np.testing.assert_array_almost_equal(result[6:9], np.array([0.05, 0.05, 0.05]))  # Attitude


if __name__ == "__main__":
    pytest.main([__file__]) 