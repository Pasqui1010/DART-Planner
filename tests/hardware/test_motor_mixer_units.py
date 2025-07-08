"""
Unit tests for motor mixer with consistent SI units.

Tests the complete thrust/torque → PWM conversion path with proper unit validation,
ensuring no magic scale factors and dimensional consistency.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from dart_planner.hardware.motor_mixer import (
    MotorMixer, 
    MotorMixingConfig, 
    QuadrotorLayout,
    create_x_configuration_mixer,
    create_plus_configuration_mixer
)
from dart_planner.hardware.motor_model import MotorModel, MotorParameters, MotorType


class MockMotorModel(MotorModel):
    """Mock motor model for testing with predictable behavior."""
    
    def __init__(self, thrust_scale: float = 10.0, torque_scale: float = 0.1):
        """
        Initialize mock motor model.
        
        Args:
            thrust_scale: Scale factor for thrust (N/PWM)
            torque_scale: Scale factor for torque (N⋅m/PWM)
        """
        self.thrust_scale = thrust_scale
        self.torque_scale = torque_scale
        
        # Create mock parameters for 4 motors
        self.motor_parameters = {
            i: MotorParameters(
                motor_id=i,
                thrust_a=thrust_scale * 0.5,  # Quadratic term
                thrust_b=thrust_scale * 0.5,  # Linear term
                thrust_c=0.0,                 # Offset
                torque_coefficient=torque_scale,
                rpm_coefficient=1000.0,
                rpm_offset=0.0,
                direction=1 if i % 2 == 0 else -1
            ) for i in range(4)
        }
    
    def thrust_from_pwm(self, pwm: float, motor_id: int) -> float:
        """Convert PWM to thrust: T = a*PWM² + b*PWM + c."""
        params = self.motor_parameters[motor_id]
        return params.thrust_a * pwm**2 + params.thrust_b * pwm + params.thrust_c
    
    def torque_from_pwm(self, pwm: float, motor_id: int) -> float:
        """Convert PWM to torque: τ = kQ * RPM²."""
        params = self.motor_parameters[motor_id]
        rpm = params.rpm_coefficient * pwm + params.rpm_offset
        return params.torque_coefficient * rpm**2
    
    def pwm_from_thrust(self, thrust: float, motor_id: int) -> float:
        """Convert thrust to PWM (inverse of thrust_from_pwm)."""
        params = self.motor_parameters[motor_id]
        # Solve quadratic equation: a*PWM² + b*PWM + c = thrust
        a, b, c = params.thrust_a, params.thrust_b, params.thrust_c - thrust
        
        if abs(a) < 1e-10:  # Linear case
            return max(0.0, min(1.0, -c / b if b != 0 else 0.0))
        
        # Quadratic case
        discriminant = b**2 - 4*a*c
        if discriminant < 0:
            return 0.0
        
        pwm1 = (-b + np.sqrt(discriminant)) / (2*a)
        pwm2 = (-b - np.sqrt(discriminant)) / (2*a)
        
        # Choose the positive solution in [0, 1]
        pwm = max(0.0, min(1.0, pwm1 if 0 <= pwm1 <= 1 else pwm2))
        return pwm
    
    def rpm_from_pwm(self, pwm: float, motor_id: int) -> float:
        """Convert PWM to RPM."""
        params = self.motor_parameters[motor_id]
        return params.rpm_coefficient * pwm + params.rpm_offset
    
    def get_motor_parameters(self, motor_id: int) -> MotorParameters:
        """Get motor parameters."""
        return self.motor_parameters[motor_id]
    
    def validate_pwm(self, pwm: float, motor_id: int) -> bool:
        """Validate PWM value."""
        params = self.motor_parameters[motor_id]
        return params.pwm_min <= pwm <= params.pwm_max


class TestMotorMixerUnits:
    """Test motor mixer with consistent SI units."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock motor model with predictable behavior
        self.mock_motor_model = MockMotorModel(thrust_scale=10.0, torque_scale=0.1)
        
        # Create X-configuration mixer
        self.config = MotorMixingConfig(
            layout=QuadrotorLayout.X_CONFIGURATION,
            motor_positions=[
                [0.15, -0.15, 0.0],  # Front-right
                [0.15, 0.15, 0.0],   # Front-left  
                [-0.15, 0.15, 0.0],  # Rear-left
                [-0.15, -0.15, 0.0]  # Rear-right
            ],
            motor_directions=[1, -1, 1, -1],
            arm_length=0.15,
            motor_model=self.mock_motor_model
        )
        
        self.mixer = MotorMixer(self.config)
    
    def test_mixing_matrix_physical_units(self):
        """Test that mixing matrix has proper physical units."""
        matrix = self.mixer.mixing_matrix
        
        # Check that matrix is not None
        assert matrix is not None
        
        # Check dimensions
        assert matrix.shape == (4, 4)
        
        # Check thrust column (all motors contribute equally)
        thrust_col = matrix[:, 0]
        assert np.allclose(thrust_col, [1.0, 1.0, 1.0, 1.0])
        
        # Check roll torque column (depends on y-position)
        roll_col = matrix[:, 1]
        expected_roll = [-0.15, 0.15, 0.15, -0.15]  # meters
        assert np.allclose(roll_col, expected_roll)
        
        # Check pitch torque column (depends on x-position)
        pitch_col = matrix[:, 2]
        expected_pitch = [0.15, 0.15, -0.15, -0.15]  # meters
        assert np.allclose(pitch_col, expected_pitch)
        
        # Check yaw torque column (depends on motor direction)
        yaw_col = matrix[:, 3]
        expected_yaw = [1, -1, 1, -1]  # unitless direction
        assert np.allclose(yaw_col, expected_yaw)
    
    def test_thrust_only_command(self):
        """Test pure thrust command (no torques)."""
        thrust = 20.0  # N
        torque = np.array([0.0, 0.0, 0.0])  # N⋅m
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # All motors should have same PWM for pure thrust
        assert len(motor_pwms) == 4
        assert np.allclose(motor_pwms, motor_pwms[0], rtol=1e-6)
        
        # PWM should be reasonable (0.0 to 1.0)
        assert np.all(motor_pwms >= 0.0) and np.all(motor_pwms <= 1.0)
        
        # Verify round-trip conversion
        reconstructed = self.mixer.get_control_allocation(motor_pwms)
        assert abs(reconstructed[0] - thrust) < 0.1  # Within 0.1 N
    
    def test_roll_torque_command(self):
        """Test pure roll torque command."""
        thrust = 20.0  # N
        torque = np.array([1.0, 0.0, 0.0])  # 1 N⋅m roll torque
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # Front motors should have different PWM than rear motors
        front_pwm_avg = (motor_pwms[0] + motor_pwms[1]) / 2
        rear_pwm_avg = (motor_pwms[2] + motor_pwms[3]) / 2
        
        # Should be different for roll torque
        assert abs(front_pwm_avg - rear_pwm_avg) > 0.01
        
        # Verify round-trip conversion
        reconstructed = self.mixer.get_control_allocation(motor_pwms)
        assert abs(reconstructed[1] - torque[0]) < 0.1  # Within 0.1 N⋅m
    
    def test_pitch_torque_command(self):
        """Test pure pitch torque command."""
        thrust = 20.0  # N
        torque = np.array([0.0, 1.0, 0.0])  # 1 N⋅m pitch torque
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # Left motors should have different PWM than right motors
        left_pwm_avg = (motor_pwms[1] + motor_pwms[2]) / 2
        right_pwm_avg = (motor_pwms[0] + motor_pwms[3]) / 2
        
        # Should be different for pitch torque
        assert abs(left_pwm_avg - right_pwm_avg) > 0.01
        
        # Verify round-trip conversion
        reconstructed = self.mixer.get_control_allocation(motor_pwms)
        assert abs(reconstructed[2] - torque[1]) < 0.1  # Within 0.1 N⋅m
    
    def test_yaw_torque_command(self):
        """Test pure yaw torque command."""
        thrust = 20.0  # N
        torque = np.array([0.0, 0.0, 1.0])  # 1 N⋅m yaw torque
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # CCW and CW motors should have different PWM
        ccw_motors = [motor_pwms[0], motor_pwms[2]]  # Motors 0, 2
        cw_motors = [motor_pwms[1], motor_pwms[3]]   # Motors 1, 3
        
        ccw_avg = np.mean(ccw_motors)
        cw_avg = np.mean(cw_motors)
        
        # Should be different for yaw torque
        assert abs(ccw_avg - cw_avg) > 0.01
        
        # Verify round-trip conversion
        reconstructed = self.mixer.get_control_allocation(motor_pwms)
        assert abs(reconstructed[3] - torque[2]) < 0.1  # Within 0.1 N⋅m
    
    def test_combined_command(self):
        """Test combined thrust and torque command."""
        thrust = 25.0  # N
        torque = np.array([0.5, -0.3, 0.2])  # N⋅m
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # All motors should have different PWM for combined command
        assert len(set(motor_pwms.round(4))) == 4  # All different
        
        # PWM should be within limits
        assert np.all(motor_pwms >= self.config.pwm_min)
        assert np.all(motor_pwms <= self.config.pwm_max)
        
        # Verify round-trip conversion
        reconstructed = self.mixer.get_control_allocation(motor_pwms)
        assert abs(reconstructed[0] - thrust) < 0.5  # Within 0.5 N
        assert np.allclose(reconstructed[1:], torque, atol=0.5)  # Within 0.5 N⋅m
    
    def test_negative_thrust_handling(self):
        """Test handling of negative thrust commands."""
        thrust = -5.0  # N (should be clamped to 0)
        torque = np.array([0.0, 0.0, 0.0])  # N⋅m
        
        motor_pwms = self.mixer.mix_commands(thrust, torque)
        
        # Should result in idle PWM for all motors
        assert np.allclose(motor_pwms, self.config.pwm_idle, rtol=1e-6)
    
    def test_saturation_handling(self):
        """Test PWM saturation handling."""
        # Create a motor model that produces high PWM values
        high_thrust_model = MockMotorModel(thrust_scale=100.0, torque_scale=1.0)
        config = MotorMixingConfig(
            layout=QuadrotorLayout.X_CONFIGURATION,
            motor_model=high_thrust_model
        )
        mixer = MotorMixer(config)
        
        # High thrust command that should saturate
        thrust = 50.0  # N
        torque = np.array([0.0, 0.0, 0.0])  # N⋅m
        
        motor_pwms = mixer.mix_commands(thrust, torque)
        
        # Should be saturated at max PWM
        assert np.allclose(motor_pwms, config.pwm_max, rtol=1e-6)
        assert mixer.saturation_events > 0
    
    def test_input_validation(self):
        """Test input validation."""
        # Invalid torque array length
        with pytest.raises(ValueError, match="Torque must be 3-element array"):
            self.mixer.mix_commands(10.0, np.array([1.0, 2.0]))
        
        # Non-finite values should be caught by motor model
        # (This would be tested in the motor model itself)
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Valid configuration should have no issues
        issues = self.mixer.validate_configuration()
        assert len(issues) == 0
        
        # Test invalid arm length
        invalid_config = MotorMixingConfig(arm_length=-0.1)
        mixer = MotorMixer(invalid_config)
        issues = mixer.validate_configuration()
        assert any("Arm length must be positive" in issue for issue in issues)
    
    def test_motor_layout_info(self):
        """Test motor layout information retrieval."""
        info = self.mixer.get_motor_layout_info()
        
        assert info["layout"] == "x"
        
        motor_positions = info["motor_positions"]
        motor_directions = info["motor_directions"]
        assert isinstance(motor_positions, list)
        assert isinstance(motor_directions, list)
        assert len(motor_positions) == 4
        assert len(motor_directions) == 4
        
        assert info["matrix_rank"] == 4
        assert info["saturation_events"] == 0
        
        # Check units documentation
        units = info["units"]
        assert isinstance(units, dict)
        assert units["thrust"] == "Newtons (N)"
        assert units["torque"] == "Newton-meters (N⋅m)"
        assert units["position"] == "meters (m)"
        assert units["pwm"] == "normalized (0.0 to 1.0)"


class TestMotorMixerFactoryFunctions:
    """Test factory functions for creating motor mixers."""
    
    def test_create_x_configuration_mixer(self):
        """Test X-configuration mixer creation."""
        arm_length = 0.2  # m
        mixer = create_x_configuration_mixer(arm_length)
        
        # Check motor positions
        positions = mixer.config.motor_positions
        expected_positions = [
            [arm_length * 0.707, -arm_length * 0.707, 0.0],  # Front-right
            [arm_length * 0.707, arm_length * 0.707, 0.0],   # Front-left
            [-arm_length * 0.707, arm_length * 0.707, 0.0],  # Rear-left
            [-arm_length * 0.707, -arm_length * 0.707, 0.0]  # Rear-right
        ]
        
        for pos, expected in zip(positions, expected_positions):
            assert np.allclose(pos, expected, rtol=1e-6)
        
        # Check motor directions
        assert mixer.config.motor_directions == [1, -1, 1, -1]
        assert mixer.config.arm_length == arm_length
    
    def test_create_plus_configuration_mixer(self):
        """Test +-configuration mixer creation."""
        arm_length = 0.18  # m
        mixer = create_plus_configuration_mixer(arm_length)
        
        # Check motor positions
        positions = mixer.config.motor_positions
        expected_positions = [
            [arm_length, 0.0, 0.0],   # Front
            [0.0, arm_length, 0.0],   # Left
            [0.0, -arm_length, 0.0],  # Right
            [-arm_length, 0.0, 0.0]   # Rear
        ]
        
        for pos, expected in zip(positions, expected_positions):
            assert np.allclose(pos, expected, rtol=1e-6)
        
        # Check motor directions
        assert mixer.config.motor_directions == [1, -1, 1, -1]
        assert mixer.config.arm_length == arm_length


class TestMotorMixerEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_thrust_command(self):
        """Test zero thrust command."""
        mixer = create_x_configuration_mixer()
        
        thrust = 0.0  # N
        torque = np.array([0.0, 0.0, 0.0])  # N⋅m
        
        motor_pwms = mixer.mix_commands(thrust, torque)
        
        # Should result in idle PWM
        assert np.allclose(motor_pwms, mixer.config.pwm_idle, rtol=1e-6)
    
    def test_large_torque_command(self):
        """Test large torque command that might cause saturation."""
        mixer = create_x_configuration_mixer()
        
        thrust = 10.0  # N
        torque = np.array([10.0, 10.0, 10.0])  # Large torques
        
        motor_pwms = mixer.mix_commands(thrust, torque)
        
        # Should handle without crashing
        assert len(motor_pwms) == 4
        assert np.all(motor_pwms >= 0.0) and np.all(motor_pwms <= 1.0)
    
    def test_reset_saturation_counter(self):
        """Test saturation counter reset."""
        mixer = create_x_configuration_mixer()
        
        # Generate some saturation events
        for _ in range(5):
            mixer.mix_commands(100.0, np.array([10.0, 10.0, 10.0]))
        
        assert mixer.saturation_events > 0
        
        # Reset counter
        mixer.reset_saturation_counter()
        assert mixer.saturation_events == 0


if __name__ == "__main__":
    pytest.main([__file__]) 