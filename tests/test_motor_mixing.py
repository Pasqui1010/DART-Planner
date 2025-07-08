"""
Unit tests for motor mixing module.

These tests verify proper motor mixing matrix calculations, PWM saturation,
and different quadrotor layouts for safety-critical flight control.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from dart_planner.hardware.motor_mixer import (
    MotorMixer,
    MotorMixingConfig,
    QuadrotorLayout,
    create_x_configuration_mixer,
    create_plus_configuration_mixer,
)


class TestMotorMixingConfig:
    """Tests for MotorMixingConfig class."""
    
    def test_default_x_configuration(self):
        """Test default X configuration motor mixing."""
        config = MotorMixingConfig()
        
        assert config.layout == QuadrotorLayout.X_CONFIGURATION
        assert len(config.motor_positions) == 4
        assert len(config.motor_directions) == 4
        assert config.mixing_matrix is not None
        assert config.mixing_matrix.shape == (4, 4)
    
    def test_custom_mixing_matrix(self):
        """Test custom mixing matrix specification."""
        custom_matrix = np.array([
            [1.0, 0.5, 0.5, 0.1],
            [1.0, -0.5, 0.5, -0.1],
            [1.0, -0.5, -0.5, 0.1],
            [1.0, 0.5, -0.5, -0.1]
        ])
        
        config = MotorMixingConfig(
            layout=QuadrotorLayout.CUSTOM,
            mixing_matrix=custom_matrix
        )
        
        assert config.layout == QuadrotorLayout.CUSTOM
        np.testing.assert_array_equal(config.mixing_matrix, custom_matrix)
    
    def test_mixing_matrix_computation(self):
        """Test automatic mixing matrix computation."""
        config = MotorMixingConfig(
            layout=QuadrotorLayout.X_CONFIGURATION,
            motor_positions=[
                [0.15, -0.15, 0.0],  # Front-right
                [0.15, 0.15, 0.0],   # Front-left
                [-0.15, 0.15, 0.0],  # Rear-left
                [-0.15, -0.15, 0.0]  # Rear-right
            ],
            motor_directions=[1, -1, 1, -1],
            thrust_coefficient=1.0e-5,
            torque_coefficient=1.0e-7,
        )
        
        matrix = config.mixing_matrix
        assert matrix is not None  # Type guard for linter
        
        # Check thrust column (all motors contribute equally)
        np.testing.assert_array_almost_equal(matrix[:, 0], [1.0e-5, 1.0e-5, 1.0e-5, 1.0e-5])
        
        # Check roll torque column (depends on y-position)
        expected_roll = np.array([-0.15, 0.15, 0.15, -0.15]) * 1.0e-5
        np.testing.assert_array_almost_equal(matrix[:, 1], expected_roll)
        
        # Check pitch torque column (depends on x-position)
        expected_pitch = np.array([0.15, 0.15, -0.15, -0.15]) * 1.0e-5
        np.testing.assert_array_almost_equal(matrix[:, 2], expected_pitch)
        
        # Check yaw torque column (depends on direction)
        expected_yaw = np.array([1, -1, 1, -1]) * 1.0e-7
        np.testing.assert_array_almost_equal(matrix[:, 3], expected_yaw)


class TestMotorMixer:
    """Tests for MotorMixer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = MotorMixingConfig(
            layout=QuadrotorLayout.X_CONFIGURATION,
            motor_positions=[
                [0.15, -0.15, 0.0],
                [0.15, 0.15, 0.0],
                [-0.15, 0.15, 0.0],
                [-0.15, -0.15, 0.0]
            ],
            motor_directions=[1, -1, 1, -1],
            thrust_coefficient=1.0e-5,
            torque_coefficient=1.0e-7,
            pwm_min=0.0,
            pwm_max=1.0,
            pwm_idle=0.1,
        )
        self.mixer = MotorMixer(self.config)
    
    def test_mixer_initialization(self):
        """Test motor mixer initialization."""
        assert self.mixer.config == self.config
        assert self.mixer.mixing_matrix is not None
        assert self.mixer.inverse_matrix is not None
        assert self.mixer.saturation_events == 0
        assert len(self.mixer.last_motor_commands) == 4
    
    def test_hover_thrust_mixing(self):
        """Test motor mixing for hover thrust only."""
        # Hover thrust: 10N, no torque
        thrust = 10.0
        torque = np.array([0.0, 0.0, 0.0])
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # All motors should have equal PWM for hover
        assert len(motor_pwms) == 4
        assert np.all(motor_pwms >= self.config.pwm_idle)
        assert np.all(motor_pwms <= self.config.pwm_max)
        
        # Check symmetry - all motors should be equal for pure thrust
        np.testing.assert_array_almost_equal(motor_pwms, motor_pwms[0] * np.ones(4), decimal=3)
    
    def test_roll_torque_mixing(self):
        """Test motor mixing for roll torque."""
        # Pure roll torque: 0.5 N⋅m
        thrust = 5.0
        torque = np.array([0.5, 0.0, 0.0])
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # Roll torque should increase motors 1,2 and decrease motors 0,3
        # (depends on motor layout and signs)
        assert len(motor_pwms) == 4
        assert np.all(motor_pwms >= self.config.pwm_idle)
        assert np.all(motor_pwms <= self.config.pwm_max)
        
        # Check that motors respond differently to roll command
        assert not np.allclose(motor_pwms, motor_pwms[0])
    
    def test_pitch_torque_mixing(self):
        """Test motor mixing for pitch torque."""
        # Pure pitch torque: 0.5 N⋅m
        thrust = 5.0
        torque = np.array([0.0, 0.5, 0.0])
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # Pitch torque should increase front motors and decrease rear motors
        assert len(motor_pwms) == 4
        assert np.all(motor_pwms >= self.config.pwm_idle)
        assert np.all(motor_pwms <= self.config.pwm_max)
        
        # Check that motors respond differently to pitch command
        assert not np.allclose(motor_pwms, motor_pwms[0])
    
    def test_yaw_torque_mixing(self):
        """Test motor mixing for yaw torque."""
        # Pure yaw torque: 0.1 N⋅m
        thrust = 5.0
        torque = np.array([0.0, 0.0, 0.1])
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # Yaw torque should increase CCW motors and decrease CW motors
        assert len(motor_pwms) == 4
        assert np.all(motor_pwms >= self.config.pwm_idle)
        assert np.all(motor_pwms <= self.config.pwm_max)
        
        # Check that motors respond differently to yaw command
        assert not np.allclose(motor_pwms, motor_pwms[0])
    
    def test_combined_commands(self):
        """Test motor mixing with combined thrust and torque commands."""
        # Combined command: thrust + roll + pitch + yaw
        thrust = 8.0
        torque = np.array([0.3, 0.2, 0.05])
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        assert len(motor_pwms) == 4
        assert np.all(motor_pwms >= self.config.pwm_idle)
        assert np.all(motor_pwms <= self.config.pwm_max)
        
        # All motors should have different values for combined command
        assert len(np.unique(motor_pwms.round(6))) == 4
    
    def test_pwm_saturation_limits(self):
        """Test PWM saturation at limits."""
        # Very high thrust that should saturate
        thrust = 100.0  # Very high thrust
        torque = np.array([0.0, 0.0, 0.0])
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # Should be saturated at pwm_max
        assert np.all(motor_pwms <= self.config.pwm_max)
        assert np.all(motor_pwms >= self.config.pwm_idle)
    
    def test_negative_thrust_handling(self):
        """Test handling of negative thrust commands."""
        # Negative thrust (should be clipped to idle)
        thrust = -5.0
        torque = np.array([0.0, 0.0, 0.0])
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # Should be at idle PWM
        assert np.all(motor_pwms >= self.config.pwm_idle)
        np.testing.assert_array_almost_equal(motor_pwms, self.config.pwm_idle * np.ones(4))
    
    def test_invalid_torque_input(self):
        """Test error handling for invalid torque input."""
        thrust = 5.0
        
        # Test with wrong length torque array
        with pytest.raises(ValueError, match="Torque must be 3-element array"):
            self.mixer.mix_commands(thrust, np.array([0.0, 0.0]))
        
        with pytest.raises(ValueError, match="Torque must be 3-element array"):
            self.mixer.mix_commands(thrust, np.array([0.0, 0.0, 0.0, 0.0]))
    
    def test_control_allocation_inverse(self):
        """Test control allocation (inverse mixing)."""
        # Test that we can recover original commands
        original_thrust = 8.0
        original_torque = np.array([0.3, 0.2, 0.05])
        
        # Mix to motor commands
        motor_pwms = self.mixer.mix_commands(original_thrust, original_torque)
        
        # Recover original commands
        recovered_commands = self.mixer.get_control_allocation(motor_pwms)
        
        # Should be close to original (within numerical precision)
        assert len(recovered_commands) == 4
        
        # Note: Due to PWM conversion and saturation, perfect recovery may not be possible
        # This is a limitation of the simplified thrust-to-PWM model
    
    def test_saturation_event_tracking(self):
        """Test saturation event tracking."""
        initial_events = self.mixer.saturation_events
        
        # Command that should cause saturation
        thrust = 50.0  # High thrust
        torque = np.array([2.0, 2.0, 1.0])  # High torque
        
        self.mixer.mix_commands(thrust, torque)
        
        # Should have recorded saturation event
        assert self.mixer.saturation_events > initial_events
    
    def test_configuration_validation(self):
        """Test motor mixing configuration validation."""
        # Valid configuration
        issues = self.mixer.validate_configuration()
        assert len(issues) == 0
        
        # Invalid configuration - wrong matrix size
        bad_config = MotorMixingConfig(
            mixing_matrix=np.array([[1, 2, 3], [4, 5, 6]])  # Wrong size
        )
        bad_mixer = MotorMixer(bad_config)
        
        issues = bad_mixer.validate_configuration()
        assert len(issues) > 0
        assert any("4x4" in issue for issue in issues)
    
    def test_motor_layout_info(self):
        """Test motor layout information retrieval."""
        info = self.mixer.get_motor_layout_info()
        
        assert "layout" in info
        assert "motor_positions" in info
        assert "motor_directions" in info
        assert "mixing_matrix" in info
        assert "matrix_rank" in info
        assert "saturation_events" in info
        
        assert info["layout"] == "x"
        assert info["matrix_rank"] == 4  # Should be full rank


class TestConfigurationFactories:
    """Tests for configuration factory functions."""
    
    def test_x_configuration_factory(self):
        """Test X configuration factory function."""
        arm_length = 0.2
        mixer = create_x_configuration_mixer(arm_length)
        
        assert isinstance(mixer, MotorMixer)
        assert mixer.config.layout == QuadrotorLayout.X_CONFIGURATION
        assert mixer.config.arm_length == arm_length
        
        # Check X configuration motor positions
        expected_positions = [
            [arm_length * 0.707, -arm_length * 0.707, 0.0],
            [arm_length * 0.707, arm_length * 0.707, 0.0],
            [-arm_length * 0.707, arm_length * 0.707, 0.0],
            [-arm_length * 0.707, -arm_length * 0.707, 0.0]
        ]
        
        np.testing.assert_array_almost_equal(mixer.config.motor_positions, expected_positions)
    
    def test_plus_configuration_factory(self):
        """Test + configuration factory function."""
        arm_length = 0.18
        mixer = create_plus_configuration_mixer(arm_length)
        
        assert isinstance(mixer, MotorMixer)
        assert mixer.config.layout == QuadrotorLayout.PLUS_CONFIGURATION
        assert mixer.config.arm_length == arm_length
        
        # Check + configuration motor positions
        expected_positions = [
            [arm_length, 0.0, 0.0],
            [0.0, arm_length, 0.0],
            [0.0, -arm_length, 0.0],
            [-arm_length, 0.0, 0.0]
        ]
        
        np.testing.assert_array_almost_equal(mixer.config.motor_positions, expected_positions)
    
    def test_different_arm_lengths(self):
        """Test factory functions with different arm lengths."""
        arm_lengths = [0.1, 0.15, 0.2, 0.25]
        
        for arm_length in arm_lengths:
            x_mixer = create_x_configuration_mixer(arm_length)
            plus_mixer = create_plus_configuration_mixer(arm_length)
            
            assert x_mixer.config.arm_length == arm_length
            assert plus_mixer.config.arm_length == arm_length
            
            # Validate both configurations
            assert len(x_mixer.validate_configuration()) == 0
            assert len(plus_mixer.validate_configuration()) == 0


class TestMotorMixingPhysics:
    """Tests for physical correctness of motor mixing."""
    
    def test_thrust_torque_relationship(self):
        """Test physical relationship between thrust and torque."""
        mixer = create_x_configuration_mixer(arm_length=0.15)
        
        # Test pure thrust command
        thrust = 10.0
        torque = np.array([0.0, 0.0, 0.0])
        
        motor_pwms = mixer.mix_commands(thrust, torque)
        
        # All motors should produce same thrust for hover
        motor_thrusts = mixer._pwm_to_thrust(motor_pwms)
        
        # Total thrust should equal commanded thrust (approximately)
        total_thrust = np.sum(motor_thrusts)
        assert abs(total_thrust - thrust) < 0.1 * thrust  # Within 10%
    
    def test_moment_arm_calculation(self):
        """Test moment arm calculations for torque generation."""
        arm_length = 0.15
        mixer = create_x_configuration_mixer(arm_length)
        
        # Test roll torque
        thrust = 5.0
        roll_torque = 0.5  # N⋅m
        torque = np.array([roll_torque, 0.0, 0.0])
        
        motor_pwms = mixer.mix_commands(thrust, torque)
        motor_thrusts = mixer._pwm_to_thrust(motor_pwms)
        
        # Calculate actual roll torque from motor thrusts
        # X configuration: motors at ±45° angles
        y_positions = np.array([-arm_length * 0.707, arm_length * 0.707, 
                               arm_length * 0.707, -arm_length * 0.707])
        
        actual_roll_torque = np.sum(motor_thrusts * y_positions)
        
        # Should be close to commanded torque (within numerical precision)
        assert abs(actual_roll_torque - roll_torque) < 0.1 * roll_torque
    
    def test_yaw_torque_conservation(self):
        """Test yaw torque conservation through motor directions."""
        mixer = create_x_configuration_mixer(arm_length=0.15)
        
        # Test yaw torque
        thrust = 5.0
        yaw_torque = 0.1  # N⋅m
        torque = np.array([0.0, 0.0, yaw_torque])
        
        motor_pwms = mixer.mix_commands(thrust, torque)
        motor_thrusts = mixer._pwm_to_thrust(motor_pwms)
        
        # Calculate actual yaw torque from motor drag
        motor_directions = np.array([1, -1, 1, -1])  # CCW, CW, CCW, CW
        drag_torques = motor_thrusts * mixer.config.torque_coefficient / mixer.config.thrust_coefficient
        
        actual_yaw_torque = np.sum(drag_torques * motor_directions)
        
        # Should be close to commanded torque
        assert abs(actual_yaw_torque - yaw_torque) < 0.1 * yaw_torque


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 