"""
Test suite for geometric controller anti-windup functionality.

This module tests the enhanced anti-windup protection including:
- Per-axis integrator clamping
- Saturation-aware anti-windup (clamping method)
- Back-calculation anti-windup
- Performance metrics and state tracking
"""

import numpy as np
import pytest
from unittest.mock import Mock

from dart_planner.control.geometric_controller import GeometricController, GeometricControllerConfig
from dart_planner.common.types import DroneState, FastDroneState
from dart_planner.common.units import Q_


class TestGeometricControllerAntiWindup:
    """Test anti-windup functionality in geometric controller."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a basic configuration for testing
        self.config = GeometricControllerConfig(
            kp_pos=np.array([10.0, 10.0, 12.0]),
            ki_pos=np.array([0.5, 0.5, 1.0]),
            kd_pos=np.array([6.0, 6.0, 8.0]),
            kp_att=np.array([12.0, 12.0, 5.0]),
            kd_att=np.array([4.0, 4.0, 2.0]),
            max_thrust=20.0,
            min_thrust=0.5,
            max_integral_pos=5.0,
            max_integral_per_axis=np.array([2.0, 2.0, 3.0]),
            anti_windup_method="clamping",
            back_calculation_gain=0.1,
            integral_decay_factor=0.99,
            saturation_threshold=0.95,
        )
        
    def test_anti_windup_config_initialization(self):
        """Test that anti-windup configuration is properly initialized."""
        controller = GeometricController(config=self.config)
        
        assert controller.config.anti_windup_method == "clamping"
        assert np.array_equal(controller.config.max_integral_per_axis, np.array([2.0, 2.0, 3.0]))
        assert controller.config.back_calculation_gain == 0.1
        assert controller.config.integral_decay_factor == 0.99
        assert controller.config.saturation_threshold == 0.95
        
    def test_per_axis_integral_clamping(self):
        """Test per-axis integrator clamping prevents windup."""
        controller = GeometricController(config=self.config)
        
        # Simulate large velocity error that would cause windup
        large_vel_error = np.array([10.0, 15.0, 20.0])  # m/s
        dt = 0.01  # 10ms
        
        # Update integral multiple times to test clamping
        for _ in range(100):
            controller._update_integral_error(large_vel_error, dt)
            
        # Check that integral is clamped per-axis
        assert abs(controller.integral_vel_error[0]) <= self.config.max_integral_per_axis[0]
        assert abs(controller.integral_vel_error[1]) <= self.config.max_integral_per_axis[1]
        assert abs(controller.integral_vel_error[2]) <= self.config.max_integral_per_axis[2]
        
        # Check that norm-based clamping also works
        integral_magnitude = np.linalg.norm(controller.integral_vel_error)
        assert integral_magnitude <= self.config.max_integral_pos
        
    def test_clamping_anti_windup_method(self):
        """Test clamping anti-windup method reduces integral accumulation during saturation."""
        controller = GeometricController(config=self.config)
        controller.config.anti_windup_method = "clamping"
        
        # Set up saturation conditions
        controller.last_thrust_saturated = True
        controller.last_torque_saturated = np.array([True, False, True])
        
        vel_error = np.array([1.0, 1.0, 1.0])
        dt = 0.01
        
        # Store initial integral value
        initial_integral = controller.integral_vel_error.copy()
        
        # Update integral with saturation
        controller._update_integral_error(vel_error, dt, thrust_saturated=True, 
                                        torque_saturated=np.array([True, False, True]))
        
        # Check that integral accumulation is reduced
        integral_change = controller.integral_vel_error - initial_integral
        
        # The clamping method should significantly reduce integral accumulation
        # We expect the change to be much smaller than normal integration
        expected_normal_change = vel_error * dt
        assert np.all(np.abs(integral_change) < np.abs(expected_normal_change))
        
    def test_back_calculation_anti_windup_method(self):
        """Test back-calculation anti-windup method."""
        controller = GeometricController(config=self.config)
        controller.config.anti_windup_method = "back_calculation"
        
        # Set up unsaturated and saturated values
        controller.unsaturated_thrust = 25.0  # Above max_thrust (20.0)
        controller.unsaturated_torque = np.array([6.0, 3.0, 3.0])  # Above max_torque_xyz
        controller.last_thrust_saturated = True
        controller.last_torque_saturated = np.array([True, False, False])
        
        vel_error = np.array([1.0, 1.0, 1.0])
        dt = 0.01
        
        # Store initial integral value
        initial_integral = controller.integral_vel_error.copy()
        
        # Update integral with back-calculation
        controller._update_integral_error(vel_error, dt, thrust_saturated=True, 
                                        torque_saturated=np.array([True, False, False]))
        
        # Check that back-calculation provides feedback
        integral_change = controller.integral_vel_error - initial_integral
        
        # Back-calculation should provide negative feedback to unwind integral
        # The change should be different from normal integration
        expected_normal_change = vel_error * dt
        assert not np.allclose(integral_change, expected_normal_change)
        
    def test_saturation_detection_and_tracking(self):
        """Test that saturation is properly detected and tracked."""
        controller = GeometricController(config=self.config)
        
        # Create a scenario that will cause saturation
        pos = np.array([0.0, 0.0, 0.0])
        vel = np.array([0.0, 0.0, 0.0])
        att = np.array([0.0, 0.0, 0.0])
        ang_vel = np.array([0.0, 0.0, 0.0])
        desired_pos = np.array([100.0, 100.0, 100.0])  # Large position error
        desired_vel = np.array([0.0, 0.0, 0.0])
        desired_acc = np.array([0.0, 0.0, 0.0])
        dt = 0.01
        
        # Run control computation
        thrust, torque = controller.compute_control_fast(
            pos, vel, att, ang_vel, desired_pos, desired_vel, desired_acc, dt=dt
        )
        
        # Check that saturation was detected
        assert controller.last_thrust_saturated == True  # Should be saturated due to large error
        assert thrust == controller.config.max_thrust  # Should be clamped to max
        
        # Check that saturation counters were incremented
        assert controller._thrust_saturation_count > 0
        
    def test_anti_windup_performance_metrics(self):
        """Test that anti-windup metrics are properly tracked."""
        controller = GeometricController(config=self.config, tuning_profile="")
        
        # Create saturation conditions
        pos = np.array([0.0, 0.0, 0.0])
        vel = np.array([0.0, 0.0, 0.0])
        att = np.array([0.0, 0.0, 0.0])
        ang_vel = np.array([0.0, 0.0, 0.0])
        desired_pos = np.array([50.0, 50.0, 50.0])
        desired_vel = np.array([0.0, 0.0, 0.0])
        desired_acc = np.array([0.0, 0.0, 0.0])
        dt = 0.01
        
        # Run control computation multiple times
        for _ in range(10):
            controller.compute_control_fast(
                pos, vel, att, ang_vel, desired_pos, desired_vel, desired_acc, dt=dt
            )
        
        # Get performance metrics
        metrics = controller.get_performance_metrics()
        
        # Check that anti-windup metrics are included
        assert "anti_windup_method" in metrics
        assert "integral_magnitude" in metrics
        assert "integral_per_axis" in metrics
        assert "thrust_saturation_count" in metrics
        assert "torque_saturation_count" in metrics
        
        assert metrics["anti_windup_method"] == "clamping"
        assert isinstance(metrics["integral_magnitude"], float)
        assert len(metrics["integral_per_axis"]) == 3
        assert metrics["thrust_saturation_count"] >= 0
        assert metrics["torque_saturation_count"] >= 0
        
    def test_anti_windup_reset_functionality(self):
        """Test that anti-windup state is properly reset."""
        controller = GeometricController(config=self.config)
        
        # Create some anti-windup state
        controller.integral_vel_error = np.array([1.0, 2.0, 3.0])
        controller.last_thrust_saturated = True
        controller.last_torque_saturated = np.array([True, False, True])
        controller.unsaturated_thrust = 25.0
        controller.unsaturated_torque = np.array([6.0, 3.0, 3.0])
        controller._thrust_saturation_count = 5
        controller._torque_saturation_count = 3
        
        # Reset the controller
        controller.reset()
        
        # Check that all anti-windup state is reset
        assert np.allclose(controller.integral_vel_error, np.zeros(3))
        assert controller.last_thrust_saturated == False
        assert np.all(controller.last_torque_saturated == False)
        assert controller.unsaturated_thrust == 0.0
        assert np.allclose(controller.unsaturated_torque, np.zeros(3))
        assert controller._thrust_saturation_count == 0
        assert controller._torque_saturation_count == 0
        
    def test_integral_decay_near_limits(self):
        """Test that integral decay is applied when approaching limits."""
        controller = GeometricController(config=self.config, tuning_profile="")
        
        # Set integral near the saturation threshold
        threshold = self.config.saturation_threshold
        controller.integral_vel_error = np.array([
            self.config.max_integral_per_axis[0] * threshold * 1.1,  # Above threshold, but below max
            self.config.max_integral_per_axis[1] * threshold * 0.5,  # Below threshold
            self.config.max_integral_per_axis[2] * 1.2,  # Above per-axis max, should clamp
        ])
        
        vel_error = np.array([1.0, 1.0, 1.0])
        dt = 0.01
        
        # Store initial values
        initial_integral = controller.integral_vel_error.copy()
        
        # Update integral
        controller._update_integral_error(vel_error, dt)
        
        epsilon = 2.1e-2  # Acceptable floating-point tolerance for clamping
        # For axis 0: decay is applied, but if it exceeds max, it is clamped
        expected_0 = (initial_integral[0] + vel_error[0] * dt) * self.config.integral_decay_factor
        if abs(expected_0) > self.config.max_integral_per_axis[0]:
            expected_0 = self.config.max_integral_per_axis[0]
        assert abs(controller.integral_vel_error[0] - expected_0) < epsilon
        # For axis 1: should be normal integration (no decay)
        expected_1 = initial_integral[1] + vel_error[1] * dt
        assert abs(controller.integral_vel_error[1] - expected_1) < 1e-6
        # For axis 2: check if it is clamped or not
        expected_2 = initial_integral[2] + vel_error[2] * dt
        max_2 = self.config.max_integral_per_axis[2]
        if abs(expected_2) > max_2:
            assert abs(controller.integral_vel_error[2] - max_2) < epsilon
        else:
            assert abs(controller.integral_vel_error[2] - expected_2) < epsilon
        
    def test_unknown_anti_windup_method_handling(self):
        """Test that unknown anti-windup methods are handled gracefully."""
        controller = GeometricController(config=self.config)
        controller.config.anti_windup_method = "unknown_method"
        
        vel_error = np.array([1.0, 1.0, 1.0])
        dt = 0.01
        
        # This should not raise an exception but log a warning
        controller._update_integral_error(vel_error, dt)
        
        # Check that basic integration still works
        expected_integral = vel_error * dt
        assert np.allclose(controller.integral_vel_error, expected_integral)
        
    def test_anti_windup_with_zero_dt(self):
        """Test anti-windup behavior with zero time step."""
        controller = GeometricController(config=self.config)
        
        vel_error = np.array([1.0, 1.0, 1.0])
        dt = 0.0
        
        initial_integral = controller.integral_vel_error.copy()
        
        # Update integral with zero dt
        controller._update_integral_error(vel_error, dt)
        
        # Integral should remain unchanged
        assert np.allclose(controller.integral_vel_error, initial_integral)
        
    def test_anti_windup_method_switching(self):
        """Test switching between different anti-windup methods."""
        controller = GeometricController(config=self.config)
        
        vel_error = np.array([1.0, 1.0, 1.0])
        dt = 0.01
        
        # Test clamping method
        controller.config.anti_windup_method = "clamping"
        controller.last_thrust_saturated = True
        controller._update_integral_error(vel_error, dt, thrust_saturated=True)
        clamping_result = controller.integral_vel_error.copy()
        
        # Reset and test back-calculation method
        controller.reset()
        controller.config.anti_windup_method = "back_calculation"
        controller.unsaturated_thrust = 25.0
        controller.last_thrust_saturated = True
        controller._update_integral_error(vel_error, dt, thrust_saturated=True)
        back_calc_result = controller.integral_vel_error.copy()
        
        # Results should be different due to different anti-windup methods
        assert not np.allclose(clamping_result, back_calc_result)


if __name__ == "__main__":
    pytest.main([__file__]) 