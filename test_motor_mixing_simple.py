#!/usr/bin/env python3
"""
Simple test script for motor mixing implementation.
This bypasses the AirSim dependency issues for testing.
"""

import sys
import numpy as np
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Direct import to avoid AirSim dependency issues
sys.path.insert(0, str(Path(__file__).parent / "src" / "dart_planner" / "hardware"))

from motor_mixer import (
    MotorMixer,
    MotorMixingConfig,
    QuadrotorLayout,
    create_x_configuration_mixer,
    create_plus_configuration_mixer,
)

def test_basic_functionality():
    """Test basic motor mixing functionality."""
    print("Testing basic motor mixing functionality...")
    
    # Create X configuration mixer
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    # Test hover command
    thrust = 10.0  # 10N
    torque = np.array([0.0, 0.0, 0.0])  # No torque
    
    motor_pwms = mixer.mix_commands(thrust, torque)
    print(f"Hover command (thrust={thrust}N, torque={torque})")
    print(f"Motor PWMs: {motor_pwms}")
    
    # Verify all motors have same PWM for hover
    assert np.allclose(motor_pwms, motor_pwms[0], rtol=1e-3), "Motors should have equal PWM for hover"
    assert np.all(motor_pwms >= mixer.config.pwm_idle), "All motors should be above idle PWM"
    assert np.all(motor_pwms <= mixer.config.pwm_max), "All motors should be below max PWM"
    
    print("✓ Hover test passed")

def test_roll_torque():
    """Test roll torque mixing."""
    print("\nTesting roll torque mixing...")
    
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    # Roll torque command
    thrust = 5.0
    torque = np.array([0.5, 0.0, 0.0])  # 0.5 N⋅m roll
    
    motor_pwms = mixer.mix_commands(thrust, torque)
    print(f"Roll command (thrust={thrust}N, roll_torque={torque[0]}N⋅m)")
    print(f"Motor PWMs: {motor_pwms}")
    
    # Verify motors respond differently to roll
    assert not np.allclose(motor_pwms, motor_pwms[0]), "Motors should have different PWM for roll"
    assert np.all(motor_pwms >= mixer.config.pwm_idle), "All motors should be above idle PWM"
    assert np.all(motor_pwms <= mixer.config.pwm_max), "All motors should be below max PWM"
    
    print("✓ Roll torque test passed")

def test_pitch_torque():
    """Test pitch torque mixing."""
    print("\nTesting pitch torque mixing...")
    
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    # Pitch torque command
    thrust = 5.0
    torque = np.array([0.0, 0.5, 0.0])  # 0.5 N⋅m pitch
    
    motor_pwms = mixer.mix_commands(thrust, torque)
    print(f"Pitch command (thrust={thrust}N, pitch_torque={torque[1]}N⋅m)")
    print(f"Motor PWMs: {motor_pwms}")
    
    # Verify motors respond differently to pitch
    assert not np.allclose(motor_pwms, motor_pwms[0]), "Motors should have different PWM for pitch"
    assert np.all(motor_pwms >= mixer.config.pwm_idle), "All motors should be above idle PWM"
    assert np.all(motor_pwms <= mixer.config.pwm_max), "All motors should be below max PWM"
    
    print("✓ Pitch torque test passed")

def test_yaw_torque():
    """Test yaw torque mixing."""
    print("\nTesting yaw torque mixing...")
    
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    # Yaw torque command
    thrust = 5.0
    torque = np.array([0.0, 0.0, 0.1])  # 0.1 N⋅m yaw
    
    motor_pwms = mixer.mix_commands(thrust, torque)
    print(f"Yaw command (thrust={thrust}N, yaw_torque={torque[2]}N⋅m)")
    print(f"Motor PWMs: {motor_pwms}")
    
    # Verify motors respond differently to yaw
    assert not np.allclose(motor_pwms, motor_pwms[0]), "Motors should have different PWM for yaw"
    assert np.all(motor_pwms >= mixer.config.pwm_idle), "All motors should be above idle PWM"
    assert np.all(motor_pwms <= mixer.config.pwm_max), "All motors should be below max PWM"
    
    print("✓ Yaw torque test passed")

def test_combined_commands():
    """Test combined thrust and torque commands."""
    print("\nTesting combined commands...")
    
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    # Combined command
    thrust = 8.0
    torque = np.array([0.3, 0.2, 0.05])  # Combined torques
    
    motor_pwms = mixer.mix_commands(thrust, torque)
    print(f"Combined command (thrust={thrust}N, torque={torque}N⋅m)")
    print(f"Motor PWMs: {motor_pwms}")
    
    # Verify all motors have different values
    unique_pwms = np.unique(motor_pwms.round(6))
    assert len(unique_pwms) == 4, "All motors should have different PWM for combined command"
    assert np.all(motor_pwms >= mixer.config.pwm_idle), "All motors should be above idle PWM"
    assert np.all(motor_pwms <= mixer.config.pwm_max), "All motors should be below max PWM"
    
    print("✓ Combined commands test passed")

def test_saturation():
    """Test PWM saturation."""
    print("\nTesting PWM saturation...")
    
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    # Very high thrust that should saturate
    thrust = 100.0
    torque = np.array([0.0, 0.0, 0.0])
    
    motor_pwms = mixer.mix_commands(thrust, torque)
    print(f"High thrust command (thrust={thrust}N)")
    print(f"Motor PWMs: {motor_pwms}")
    
    # Should be saturated at max PWM
    assert np.all(motor_pwms <= mixer.config.pwm_max), "Should be saturated at max PWM"
    assert np.all(motor_pwms >= mixer.config.pwm_idle), "Should be above idle PWM"
    
    print("✓ Saturation test passed")

def test_configuration_validation():
    """Test configuration validation."""
    print("\nTesting configuration validation...")
    
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    # Valid configuration should have no issues
    issues = mixer.validate_configuration()
    print(f"Validation issues: {issues}")
    assert len(issues) == 0, "Valid configuration should have no issues"
    
    print("✓ Configuration validation test passed")

def test_mixing_matrix():
    """Test mixing matrix properties."""
    print("\nTesting mixing matrix properties...")
    
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    # Type guard for linter
    assert mixer.mixing_matrix is not None, "Mixing matrix should exist"
    
    # Check matrix dimensions
    assert mixer.mixing_matrix.shape == (4, 4), "Mixing matrix should be 4x4"
    
    # Check matrix rank (should be full rank)
    rank = np.linalg.matrix_rank(mixer.mixing_matrix)
    assert rank == 4, f"Mixing matrix should be full rank, got {rank}"
    
    # Check that inverse exists
    assert mixer.inverse_matrix is not None, "Inverse matrix should exist"
    
    print(f"Mixing matrix shape: {mixer.mixing_matrix.shape}")
    print(f"Mixing matrix rank: {rank}")
    print(f"Mixing matrix:\n{mixer.mixing_matrix}")
    
    print("✓ Mixing matrix test passed")

def test_plus_configuration():
    """Test + configuration."""
    print("\nTesting + configuration...")
    
    mixer = create_plus_configuration_mixer(arm_length=0.15)
    
    # Test hover command
    thrust = 10.0
    torque = np.array([0.0, 0.0, 0.0])
    
    motor_pwms = mixer.mix_commands(thrust, torque)
    print(f"+ config hover command (thrust={thrust}N)")
    print(f"Motor PWMs: {motor_pwms}")
    
    # Verify configuration
    assert mixer.config.layout == QuadrotorLayout.PLUS_CONFIGURATION
    assert np.allclose(motor_pwms, motor_pwms[0], rtol=1e-3), "Motors should have equal PWM for hover"
    
    print("✓ + configuration test passed")

if __name__ == "__main__":
    print("Motor Mixing Implementation Test Suite")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        test_roll_torque()
        test_pitch_torque()
        test_yaw_torque()
        test_combined_commands()
        test_saturation()
        test_configuration_validation()
        test_mixing_matrix()
        test_plus_configuration()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! Motor mixing implementation is working correctly.")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 