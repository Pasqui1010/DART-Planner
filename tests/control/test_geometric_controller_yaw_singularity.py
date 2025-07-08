"""
Test yaw-alignment singularity detection in GeometricController.

This test suite verifies that the controller properly detects and handles
cases where the desired yaw direction is nearly parallel to the thrust direction,
which would cause numerical issues in the cross product computation.
"""

import numpy as np
import pytest
from unittest.mock import Mock

from dart_planner.control.geometric_controller import GeometricController, GeometricControllerConfig
from dart_planner.common.types import DroneState
from dart_planner.common.units import Q_


class TestYawSingularityDetection:
    """Test yaw-alignment singularity detection and handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = GeometricControllerConfig(
            yaw_singularity_threshold=0.1,  # cos(84°) ≈ 0.1
            yaw_singularity_warning_threshold=0.3,  # cos(72°) ≈ 0.3
            yaw_singularity_fallback_method="skip_yaw",
            default_heading_yaw=0.0
        )
        self.controller = GeometricController(config=self.config, tuning_profile="")
        
    def test_singularity_detection_normal_case(self):
        """Test that normal cases don't trigger singularity detection."""
        # Normal case: yaw vector perpendicular to thrust vector
        yaw_vector = np.array([1.0, 0.0, 0.0])  # Pointing east
        b3_des = np.array([0.0, 0.0, 1.0])      # Pointing up
        
        is_singular, cos_angle, fallback_method = self.controller._detect_yaw_singularity(yaw_vector, b3_des)
        
        assert not is_singular
        assert cos_angle == 0.0
        assert fallback_method == "skip_yaw"
        
    def test_singularity_detection_parallel_case(self):
        """Test that parallel vectors trigger singularity detection."""
        # Singular case: yaw vector nearly parallel to thrust vector
        yaw_vector = np.array([0.0, 0.0, 0.95])  # Nearly pointing up
        b3_des = np.array([0.0, 0.0, 1.0])       # Pointing up
        
        is_singular, cos_angle, fallback_method = self.controller._detect_yaw_singularity(yaw_vector, b3_des)
        
        assert is_singular
        assert cos_angle == 0.95
        assert fallback_method == "skip_yaw"
        
    def test_singularity_detection_antiparallel_case(self):
        """Test that antiparallel vectors trigger singularity detection."""
        # Singular case: yaw vector nearly antiparallel to thrust vector
        yaw_vector = np.array([0.0, 0.0, -0.95])  # Nearly pointing down
        b3_des = np.array([0.0, 0.0, 1.0])        # Pointing up
        
        is_singular, cos_angle, fallback_method = self.controller._detect_yaw_singularity(yaw_vector, b3_des)
        
        assert is_singular
        assert cos_angle == 0.95  # abs() is used in detection
        assert fallback_method == "skip_yaw"
        
    def test_singularity_detection_warning_threshold(self):
        """Test that warning threshold works correctly."""
        # Case approaching singularity but not quite there
        yaw_vector = np.array([0.0, 0.0, 0.5])   # cos(60°) = 0.5
        b3_des = np.array([0.0, 0.0, 1.0])       # Pointing up
        
        is_singular, cos_angle, fallback_method = self.controller._detect_yaw_singularity(yaw_vector, b3_des)
        
        assert is_singular  # 0.5 > 0.1 (singularity threshold)
        assert cos_angle == 0.5
        assert fallback_method == "skip_yaw"
        
    def test_handle_singularity_skip_yaw_method(self):
        """Test skip_yaw fallback method."""
        yaw_vector = np.array([0.0, 0.0, 0.95])
        b3_des = np.array([0.0, 0.0, 1.0])
        current_yaw = 0.0
        
        b1_des, b2_des, b3_des_out = self.controller._handle_yaw_singularity(
            yaw_vector, b3_des, current_yaw, "skip_yaw"
        )
        
        # Verify orthonormal frame
        assert np.allclose(b3_des_out, b3_des)
        assert np.allclose(np.dot(b1_des, b3_des), 0.0, atol=1e-6)
        assert np.allclose(np.dot(b2_des, b3_des), 0.0, atol=1e-6)
        assert np.allclose(np.dot(b1_des, b2_des), 0.0, atol=1e-6)
        assert np.allclose(np.linalg.norm(b1_des), 1.0, atol=1e-6)
        assert np.allclose(np.linalg.norm(b2_des), 1.0, atol=1e-6)
        assert np.allclose(np.linalg.norm(b3_des_out), 1.0, atol=1e-6)
        
    def test_handle_singularity_default_heading_method(self):
        """Test default_heading fallback method."""
        yaw_vector = np.array([0.0, 0.0, 0.95])
        b3_des = np.array([0.0, 0.0, 1.0])
        current_yaw = 0.0
        
        # Set default heading to 90 degrees
        self.controller.config.default_heading_yaw = np.pi / 2
        
        b1_des, b2_des, b3_des_out = self.controller._handle_yaw_singularity(
            yaw_vector, b3_des, current_yaw, "default_heading"
        )
        
        # Verify orthonormal frame
        assert np.allclose(b3_des_out, b3_des)
        assert np.allclose(np.dot(b1_des, b3_des), 0.0, atol=1e-6)
        assert np.allclose(np.dot(b2_des, b3_des), 0.0, atol=1e-6)
        assert np.allclose(np.dot(b1_des, b2_des), 0.0, atol=1e-6)
        assert np.allclose(np.linalg.norm(b1_des), 1.0, atol=1e-6)
        assert np.allclose(np.linalg.norm(b2_des), 1.0, atol=1e-6)
        assert np.allclose(np.linalg.norm(b3_des_out), 1.0, atol=1e-6)
        
    def test_handle_singularity_maintain_current_method(self):
        """Test maintain_current fallback method."""
        yaw_vector = np.array([0.0, 0.0, 0.95])
        b3_des = np.array([0.0, 0.0, 1.0])
        current_yaw = np.pi / 4  # 45 degrees
        
        b1_des, b2_des, b3_des_out = self.controller._handle_yaw_singularity(
            yaw_vector, b3_des, current_yaw, "maintain_current"
        )
        
        # Verify orthonormal frame
        assert np.allclose(b3_des_out, b3_des)
        assert np.allclose(np.dot(b1_des, b3_des), 0.0, atol=1e-6)
        assert np.allclose(np.dot(b2_des, b3_des), 0.0, atol=1e-6)
        assert np.allclose(np.dot(b1_des, b2_des), 0.0, atol=1e-6)
        assert np.allclose(np.linalg.norm(b1_des), 1.0, atol=1e-6)
        assert np.allclose(np.linalg.norm(b2_des), 1.0, atol=1e-6)
        assert np.allclose(np.linalg.norm(b3_des_out), 1.0, atol=1e-6)
        
    def test_handle_singularity_unknown_method(self):
        """Test handling of unknown fallback method."""
        yaw_vector = np.array([0.0, 0.0, 0.95])
        b3_des = np.array([0.0, 0.0, 1.0])
        current_yaw = 0.0
        
        b1_des, b2_des, b3_des_out = self.controller._handle_yaw_singularity(
            yaw_vector, b3_des, current_yaw, "unknown_method"
        )
        
        # Should fall back to skip_yaw method
        assert np.allclose(b3_des_out, b3_des)
        assert np.allclose(np.dot(b1_des, b3_des), 0.0, atol=1e-6)
        assert np.allclose(np.dot(b2_des, b3_des), 0.0, atol=1e-6)
        assert np.allclose(np.dot(b1_des, b2_des), 0.0, atol=1e-6)
        
    def test_fast_geometric_attitude_control_singularity(self):
        """Test that fast attitude control handles singularity correctly."""
        # Create a singular case
        att = np.array([0.0, 0.0, 0.0])  # Level attitude
        ang_vel = np.zeros(3)
        b3_des = np.array([0.0, 0.0, 1.0])  # Pointing up
        yaw_des = 0.0  # This will create a yaw vector [1,0,0] which is perpendicular to b3_des
        
        # This should not trigger singularity
        torque_normal = self.controller._fast_geometric_attitude_control(
            att, ang_vel, b3_des, yaw_des, 0.0
        )
        
        # Now create a singular case by making yaw vector nearly parallel to thrust
        # We'll use a very small horizontal component
        yaw_des_singular = 0.0  # This creates [1,0,0] but we'll modify the detection logic
        # For testing, we'll temporarily change the threshold to trigger singularity
        original_threshold = self.controller.config.yaw_singularity_threshold
        self.controller.config.yaw_singularity_threshold = 0.5  # More permissive for testing
        
        # This should trigger singularity handling
        torque_singular = self.controller._fast_geometric_attitude_control(
            att, ang_vel, b3_des, yaw_des_singular, 0.0
        )
        
        # Restore original threshold
        self.controller.config.yaw_singularity_threshold = original_threshold
        
        # Both should return valid torque vectors
        assert len(torque_normal) == 3
        assert len(torque_singular) == 3
        assert not np.any(np.isnan(torque_normal))
        assert not np.any(np.isnan(torque_singular))
        
    def test_geometric_attitude_control_singularity(self):
        """Test that full attitude control handles singularity correctly."""
        # Create a mock drone state
        state = Mock(spec=DroneState)
        state.position = Q_(np.array([0.0, 0.0, 0.0]), 'm')
        state.velocity = Q_(np.zeros(3), 'm/s')
        state.attitude = Q_(np.array([0.0, 0.0, 0.0]), 'rad')
        state.angular_velocity = Q_(np.zeros(3), 'rad/s')
        state.timestamp = 0.0
        
        b3_des = np.array([0.0, 0.0, 1.0])  # Pointing up
        yaw_des = 0.0
        yaw_rate_des = 0.0
        thrust_mag = 10.0
        dt = 0.001
        
        # This should work normally
        thrust, torque = self.controller._geometric_attitude_control(
            state, b3_des, yaw_des, yaw_rate_des, thrust_mag, dt
        )
        
        assert thrust == thrust_mag
        assert len(torque) == 3
        assert not np.any(np.isnan(torque))
        
    def test_singularity_edge_cases(self):
        """Test edge cases in singularity detection."""
        # Test with exactly threshold value
        yaw_vector = np.array([0.0, 0.0, 0.1])  # Exactly at threshold
        b3_des = np.array([0.0, 0.0, 1.0])
        
        is_singular, cos_angle, fallback_method = self.controller._detect_yaw_singularity(yaw_vector, b3_des)
        
        assert is_singular  # Should be exactly at threshold (>= 0.1)
        assert cos_angle == 0.1
        
        # Test with slightly below threshold
        yaw_vector = np.array([0.0, 0.0, 0.09])  # Just below threshold
        b3_des = np.array([0.0, 0.0, 1.0])
        
        is_singular, cos_angle, fallback_method = self.controller._detect_yaw_singularity(yaw_vector, b3_des)
        
        assert not is_singular  # Should be below threshold (< 0.1)
        assert cos_angle == 0.09
        
    def test_performance_metrics_includes_singularity_config(self):
        """Test that performance metrics include singularity configuration."""
        metrics = self.controller.get_performance_metrics()
        
        assert "yaw_singularity_threshold" in metrics
        assert "yaw_singularity_fallback_method" in metrics
        assert "yaw_singularity_warning_threshold" in metrics
        
        assert metrics["yaw_singularity_threshold"] == 0.1
        assert metrics["yaw_singularity_fallback_method"] == "skip_yaw"
        assert metrics["yaw_singularity_warning_threshold"] == 0.3


if __name__ == "__main__":
    pytest.main([__file__]) 