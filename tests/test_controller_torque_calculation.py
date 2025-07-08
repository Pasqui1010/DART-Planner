"""
Unit tests for torque calculation in geometric controller.

These tests verify that the controller correctly applies inertia tensors
using matrix multiplication rather than element-wise multiplication.
"""

import pytest
import numpy as np
from unittest.mock import Mock

from dart_planner.control.geometric_controller import GeometricController, GeometricControllerConfig
from dart_planner.common.types import DroneState, FastDroneState
from dart_planner.common.units import Q_


class TestTorqueCalculation:
    """Test torque calculation correctness."""

    def test_diagonal_inertia_torque_calculation(self):
        """Test that diagonal inertia produces correct torque."""
        # Create controller with known diagonal inertia
        config = GeometricControllerConfig()
        config.inertia = np.array([0.025, 0.03, 0.045])  # kg·m² (from hardware.yaml)
        # Set high torque limits to avoid clipping
        config.max_torque_xyz = np.array([100.0, 100.0, 100.0])  # N·m
        # Set zero gains to isolate coriolis term
        config.kp_att = np.zeros(3)
        config.kd_att = np.zeros(3)
        # Create controller without tuning profile to avoid overriding config
        controller = GeometricController(config=config, tuning_profile="")
        
        # Test state with known angular velocity (smaller values to avoid hitting limits)
        ang_vel = np.array([0.1, 0.2, 0.3])  # rad/s
        
        # Expected: I @ ω = [0.025*0.1, 0.03*0.2, 0.045*0.3] = [0.0025, 0.006, 0.0135]
        expected_I_omega = np.array([0.0025, 0.006, 0.0135])
        
        # Call the fast attitude control method
        torque = controller._fast_geometric_attitude_control(
            att=np.zeros(3),
            ang_vel=ang_vel,
            b3_des=np.array([0, 0, 1]),
            yaw_des=0.0,
            yaw_rate_des=0.0
        )
        
        # The coriolis term should be ω × (I @ ω)
        expected_coriolis = np.cross(ang_vel, expected_I_omega)
        
        # With zero gains, torque should be just the coriolis term
        np.testing.assert_allclose(torque, expected_coriolis, rtol=1e-10)

    def test_non_diagonal_inertia_torque_calculation(self):
        """Test that non-diagonal inertia produces correct torque."""
        # Create controller with non-diagonal inertia
        config = GeometricControllerConfig()
        # Non-diagonal inertia matrix (off-diagonal terms simulate coupling)
        inertia_matrix = np.array([
            [0.02, 0.001, 0.002],
            [0.001, 0.02, 0.003],
            [0.002, 0.003, 0.04]
        ])
        config.inertia = np.diag(inertia_matrix)  # Store diagonal for compatibility
        # Set zero gains to isolate coriolis term
        config.kp_att = np.zeros(3)
        config.kd_att = np.zeros(3)
        controller = GeometricController(config=config, tuning_profile="")
        
        # Override the fast inertia to use the full matrix
        controller._fast_inertia = inertia_matrix
        
        # Test state with known angular velocity
        ang_vel = np.array([0.1, 0.2, 0.3])  # rad/s (smaller values to avoid limits)
        
        # Expected: I @ ω = matrix multiplication
        expected_I_omega = inertia_matrix @ ang_vel
        
        # Test the fast method
        torque = controller._fast_geometric_attitude_control(
            att=np.zeros(3),
            ang_vel=ang_vel,
            b3_des=np.array([0, 0, 1]),
            yaw_des=0.0,
            yaw_rate_des=0.0
        )
        
        # The coriolis term should be ω × (I @ ω)
        expected_coriolis = np.cross(ang_vel, expected_I_omega)
        
        # With zero gains, torque should be just the coriolis term
        np.testing.assert_allclose(torque, expected_coriolis, rtol=1e-10)

    def test_element_wise_vs_matrix_multiplication_difference(self):
        """Test that element-wise and matrix multiplication produce different results."""
        # Non-diagonal inertia matrix
        inertia_matrix = np.array([
            [0.02, 0.001, 0.002],
            [0.001, 0.02, 0.003],
            [0.002, 0.003, 0.04]
        ])
        
        ang_vel = np.array([1.0, 2.0, 3.0])
        
        # Element-wise multiplication (incorrect)
        element_wise_result = np.diag(inertia_matrix) * ang_vel
        
        # Matrix multiplication (correct)
        matrix_result = inertia_matrix @ ang_vel
        
        # These should be different for non-diagonal inertia
        assert not np.allclose(element_wise_result, matrix_result)
        
        # The difference should be significant
        difference = np.linalg.norm(matrix_result - element_wise_result)
        assert difference > 1e-6, "Element-wise and matrix multiplication should differ significantly"

    def test_original_vs_fast_method_consistency(self):
        """Test that original and fast methods produce consistent results for diagonal inertia."""
        config = GeometricControllerConfig()
        config.inertia = np.array([0.025, 0.03, 0.045])  # kg·m² (from hardware.yaml)
        controller = GeometricController(config=config, tuning_profile="")
        
        # Create test state
        state = DroneState(
            timestamp=0.0,
            position=Q_(np.zeros(3), 'm'),
            velocity=Q_(np.zeros(3), 'm/s'),
            attitude=Q_(np.zeros(3), 'rad'),
            angular_velocity=Q_(np.array([1.0, 2.0, 3.0]), 'rad/s')
        )
        
        # Test parameters
        b3_des = np.array([0, 0, 1])
        yaw_des = 0.0
        yaw_rate_des = 0.0
        thrust_mag = 10.0
        dt = 0.01
        
        # Call original method
        _, torque_original = controller._geometric_attitude_control(
            state, b3_des, yaw_des, yaw_rate_des, thrust_mag, dt
        )
        
        # Call fast method
        torque_fast = controller._fast_geometric_attitude_control(
            np.zeros(3),  # att
            np.array([1.0, 2.0, 3.0]),  # ang_vel
            b3_des, yaw_des, yaw_rate_des
        )
        
        # Results should be consistent (within numerical precision)
        np.testing.assert_allclose(torque_original, torque_fast, rtol=1e-10)

    def test_torque_limits_application(self):
        """Test that torque limits are properly applied."""
        config = GeometricControllerConfig()
        config.max_torque_xyz = np.array([1.0, 1.0, 2.0])  # N·m
        controller = GeometricController(config=config)
        
        # Create a scenario that would produce large torque
        ang_vel = np.array([10.0, 10.0, 10.0])  # Large angular velocity
        
        torque = controller._fast_geometric_attitude_control(
            att=np.zeros(3),
            ang_vel=ang_vel,
            b3_des=np.array([0, 0, 1]),
            yaw_des=0.0,
            yaw_rate_des=0.0
        )
        
        # Check that torque is within limits
        assert np.all(torque <= config.max_torque_xyz)
        assert np.all(torque >= -config.max_torque_xyz)

    def test_coriolis_term_physical_correctness(self):
        """Test that coriolis term has correct physical meaning."""
        config = GeometricControllerConfig()
        config.inertia = np.array([0.025, 0.03, 0.045])  # kg·m² (from hardware.yaml)
        # Set zero gains to isolate coriolis term
        config.kp_att = np.zeros(3)
        config.kd_att = np.zeros(3)
        controller = GeometricController(config=config, tuning_profile="")
        
        # Test with zero angular velocity (should give zero coriolis)
        ang_vel_zero = np.zeros(3)
        
        torque_zero = controller._fast_geometric_attitude_control(
            att=np.zeros(3),
            ang_vel=ang_vel_zero,
            b3_des=np.array([0, 0, 1]),
            yaw_des=0.0,
            yaw_rate_des=0.0
        )
        
        # With zero gains and zero angular velocity, torque should be zero
        np.testing.assert_allclose(torque_zero, np.zeros(3), atol=1e-10)
        
        # Test with non-zero angular velocity (should give non-zero coriolis)
        # Use non-parallel angular velocity to ensure non-zero coriolis
        ang_vel_nonzero = np.array([0.1, 0.2, 0.0])  # Small values to avoid limits
        
        torque_nonzero = controller._fast_geometric_attitude_control(
            att=np.zeros(3),
            ang_vel=ang_vel_nonzero,
            b3_des=np.array([0, 0, 1]),
            yaw_des=0.0,
            yaw_rate_des=0.0
        )
        
        # With zero gains, torque should be just the coriolis term
        # Coriolis should be non-zero
        assert np.any(np.abs(torque_nonzero) > 1e-10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 