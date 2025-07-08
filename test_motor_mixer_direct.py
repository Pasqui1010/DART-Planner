"""
Direct test for motor mixer with consistent SI units.

This test directly imports the motor mixer file to avoid AirSim dependency issues.
"""

import numpy as np
from unittest.mock import Mock

from dart_planner.hardware.motor_mixer import (
    MotorMixer,
    MotorMixingConfig,
    QuadrotorLayout,
    create_x_configuration_mixer,
    create_plus_configuration_mixer
)

# Mock motor model for testing
class MockMotorModel:
    """Mock motor model for testing with predictable behavior."""
    
    def __init__(self, thrust_scale: float = 10.0, torque_scale: float = 0.1):
        self.thrust_scale = thrust_scale
        self.torque_scale = torque_scale
    
    def thrust_from_pwm(self, pwm: float, motor_id: int) -> float:
        """Convert PWM to thrust: T = scale * PWM."""
        return self.thrust_scale * pwm
    
    def pwm_from_thrust(self, thrust: float, motor_id: int) -> float:
        """Convert thrust to PWM: PWM = thrust / scale."""
        return max(0.0, min(1.0, thrust / self.thrust_scale))
    
    def get_motor_parameters(self, motor_id: int):
        """Get mock motor parameters."""
        return Mock(pwm_min=0.0, pwm_max=1.0)


def test_mixing_matrix_physical_units():
    """Test that mixing matrix has proper physical units."""
    # Create mock motor model
    mock_motor_model = MockMotorModel(thrust_scale=10.0, torque_scale=0.1)
    
    # Create X-configuration mixer
    config = MotorMixingConfig(
        layout=QuadrotorLayout.X_CONFIGURATION,
        motor_positions=[
            [0.15, -0.15, 0.0],  # Front-right
            [0.15, 0.15, 0.0],   # Front-left  
            [-0.15, 0.15, 0.0],  # Rear-left
            [-0.15, -0.15, 0.0]  # Rear-right
        ],
        motor_directions=[1, -1, 1, -1],
        arm_length=0.15,
        motor_model=mock_motor_model
    )
    
    mixer = MotorMixer(config)
    
    # Check that matrix is not None
    assert mixer.mixing_matrix is not None
    
    matrix = mixer.mixing_matrix
    
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
    
    print("✓ Mixing matrix physical units test passed")


def test_thrust_only_command():
    """Test pure thrust command (no torques)."""
    # Create mock motor model
    mock_motor_model = MockMotorModel(thrust_scale=10.0, torque_scale=0.1)
    
    # Create X-configuration mixer
    config = MotorMixingConfig(
        layout=QuadrotorLayout.X_CONFIGURATION,
        motor_model=mock_motor_model
    )
    
    mixer = MotorMixer(config)
    
    thrust = 20.0  # N
    torque = np.array([0.0, 0.0, 0.0])  # N⋅m
    
    motor_pwms = mixer.mix_commands(thrust, torque)
    
    # All motors should have same PWM for pure thrust
    assert len(motor_pwms) == 4
    assert np.allclose(motor_pwms, motor_pwms[0], rtol=1e-6)
    
    # PWM should be reasonable (0.0 to 1.0)
    assert np.all(motor_pwms >= 0.0) and np.all(motor_pwms <= 1.0)
    
    # Expected PWM should be thrust / scale = 20.0 / 10.0 = 2.0, but clamped to 1.0
    assert np.allclose(motor_pwms, 1.0, rtol=1e-6)
    
    print("✓ Thrust only command test passed")


def test_roll_torque_command():
    """Test pure roll torque command."""
    # Create mock motor model
    mock_motor_model = MockMotorModel(thrust_scale=10.0, torque_scale=0.1)
    
    # Create X-configuration mixer
    config = MotorMixingConfig(
        layout=QuadrotorLayout.X_CONFIGURATION,
        motor_model=mock_motor_model
    )
    
    mixer = MotorMixer(config)
    
    thrust = 20.0  # N
    torque = np.array([1.0, 0.0, 0.0])  # 1 N⋅m roll torque
    
    motor_pwms = mixer.mix_commands(thrust, torque)
    
    # Front motors should have different PWM than rear motors
    front_pwm_avg = (motor_pwms[0] + motor_pwms[1]) / 2
    rear_pwm_avg = (motor_pwms[2] + motor_pwms[3]) / 2
    
    # Should be different for roll torque
    assert abs(front_pwm_avg - rear_pwm_avg) > 0.01
    
    print("✓ Roll torque command test passed")


def test_negative_thrust_handling():
    """Test handling of negative thrust commands."""
    # Create mock motor model
    mock_motor_model = MockMotorModel(thrust_scale=10.0, torque_scale=0.1)
    
    # Create X-configuration mixer
    config = MotorMixingConfig(
        layout=QuadrotorLayout.X_CONFIGURATION,
        motor_model=mock_motor_model
    )
    
    mixer = MotorMixer(config)
    
    thrust = -5.0  # N (should be clamped to 0)
    torque = np.array([0.0, 0.0, 0.0])  # N⋅m
    
    motor_pwms = mixer.mix_commands(thrust, torque)
    
    # Should result in idle PWM for all motors
    assert np.allclose(motor_pwms, config.pwm_idle, rtol=1e-6)
    
    print("✓ Negative thrust handling test passed")


def test_configuration_validation():
    """Test configuration validation."""
    # Create mock motor model
    mock_motor_model = MockMotorModel(thrust_scale=10.0, torque_scale=0.1)
    
    # Valid configuration should have no issues
    config = MotorMixingConfig(
        layout=QuadrotorLayout.X_CONFIGURATION,
        motor_model=mock_motor_model
    )
    mixer = MotorMixer(config)
    issues = mixer.validate_configuration()
    assert len(issues) == 0
    
    # Test invalid arm length
    invalid_config = MotorMixingConfig(arm_length=-0.1)
    mixer = MotorMixer(invalid_config)
    issues = mixer.validate_configuration()
    assert any("Arm length must be positive" in issue for issue in issues)
    
    print("✓ Configuration validation test passed")


def test_factory_functions():
    """Test factory functions for creating motor mixers."""
    # Test X-configuration mixer
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
    
    print("✓ Factory functions test passed")


def main():
    """Run all tests."""
    print("Running motor mixer unit tests...")
    print("=" * 50)
    
    try:
        test_mixing_matrix_physical_units()
        test_thrust_only_command()
        test_roll_torque_command()
        test_negative_thrust_handling()
        test_configuration_validation()
        test_factory_functions()
        
        print("=" * 50)
        print("✓ All tests passed!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 