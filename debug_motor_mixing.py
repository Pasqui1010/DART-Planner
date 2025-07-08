#!/usr/bin/env python3
"""
Debug script for motor mixing issues.
"""

import sys
import numpy as np
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "src" / "dart_planner" / "hardware"))

from motor_mixer import (
    MotorMixer,
    MotorMixingConfig,
    QuadrotorLayout,
    create_x_configuration_mixer,
)

def debug_mixing_matrix():
    """Debug the mixing matrix calculation."""
    print("=== Debugging Mixing Matrix ===")
    
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    print(f"Configuration:")
    print(f"  Layout: {mixer.config.layout}")
    print(f"  Arm length: {mixer.config.arm_length}")
    print(f"  Thrust coefficient: {mixer.config.thrust_coefficient}")
    print(f"  Torque coefficient: {mixer.config.torque_coefficient}")
    print(f"  Motor positions: {mixer.config.motor_positions}")
    print(f"  Motor directions: {mixer.config.motor_directions}")
    
    print(f"\nMixing matrix:")
    print(mixer.mixing_matrix)
    
    print(f"\nMixing matrix shape: {mixer.mixing_matrix.shape}")
    print(f"Mixing matrix rank: {np.linalg.matrix_rank(mixer.mixing_matrix)}")
    
    return mixer

def debug_thrust_to_pwm():
    """Debug the thrust-to-PWM conversion."""
    print("\n=== Debugging Thrust-to-PWM Conversion ===")
    
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    # Test different thrust values
    test_thrusts = np.array([0.0, 1.0, 5.0, 10.0, 20.0])
    
    print(f"Testing thrust-to-PWM conversion:")
    for thrust in test_thrusts:
        pwm = mixer._thrust_to_pwm(np.array([thrust]))
        print(f"  Thrust: {thrust:.1f}N -> PWM: {pwm[0]:.4f}")
    
    # Test PWM normalization parameters
    max_pwm_theoretical = np.sqrt(mixer.config.thrust_coefficient * 100)
    print(f"\nPWM normalization parameters:")
    print(f"  Thrust coefficient: {mixer.config.thrust_coefficient}")
    print(f"  Max PWM theoretical: {max_pwm_theoretical}")
    print(f"  Max thrust assumption: 100N")

def debug_command_mixing():
    """Debug the command mixing process."""
    print("\n=== Debugging Command Mixing ===")
    
    mixer = create_x_configuration_mixer(arm_length=0.15)
    
    # Test hover command
    thrust = 10.0
    torque = np.array([0.0, 0.0, 0.0])
    
    print(f"Testing hover command:")
    print(f"  Input: thrust={thrust}N, torque={torque}")
    
    # Step by step mixing
    command_vector = np.array([thrust, torque[0], torque[1], torque[2]])
    print(f"  Command vector: {command_vector}")
    
    motor_thrusts = mixer.mixing_matrix @ command_vector
    print(f"  Motor thrusts: {motor_thrusts}")
    
    motor_pwms_raw = mixer._thrust_to_pwm(motor_thrusts)
    print(f"  Motor PWMs (raw): {motor_pwms_raw}")
    
    motor_pwms_saturated = mixer._saturate_pwm(motor_pwms_raw)
    print(f"  Motor PWMs (saturated): {motor_pwms_saturated}")
    
    # Test roll command
    print(f"\nTesting roll command:")
    thrust = 5.0
    torque = np.array([0.5, 0.0, 0.0])
    
    print(f"  Input: thrust={thrust}N, torque={torque}")
    
    command_vector = np.array([thrust, torque[0], torque[1], torque[2]])
    print(f"  Command vector: {command_vector}")
    
    motor_thrusts = mixer.mixing_matrix @ command_vector
    print(f"  Motor thrusts: {motor_thrusts}")
    
    motor_pwms_raw = mixer._thrust_to_pwm(motor_thrusts)
    print(f"  Motor PWMs (raw): {motor_pwms_raw}")
    
    motor_pwms_saturated = mixer._saturate_pwm(motor_pwms_raw)
    print(f"  Motor PWMs (saturated): {motor_pwms_saturated}")

def test_matrix_physics():
    """Test the physics of the mixing matrix."""
    print("\n=== Testing Matrix Physics ===")
    
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
    
    mixer = MotorMixer(config)
    
    print(f"Expected mixing matrix for X configuration:")
    print(f"Row format: [thrust, roll, pitch, yaw]")
    print(f"Column format: [Motor0, Motor1, Motor2, Motor3]")
    
    expected_matrix = np.array([
        [1.0e-5, -1.5e-6, 1.5e-6, 1.0e-7],   # Motor 0: Front-right
        [1.0e-5, 1.5e-6, 1.5e-6, -1.0e-7],   # Motor 1: Front-left
        [1.0e-5, 1.5e-6, -1.5e-6, 1.0e-7],   # Motor 2: Rear-left
        [1.0e-5, -1.5e-6, -1.5e-6, -1.0e-7]  # Motor 3: Rear-right
    ])
    
    print(f"\nExpected matrix:")
    print(expected_matrix)
    print(f"\nActual matrix:")
    print(mixer.mixing_matrix)
    
    print(f"\nMatrix difference:")
    print(mixer.mixing_matrix - expected_matrix)

if __name__ == "__main__":
    debug_mixing_matrix()
    debug_thrust_to_pwm()
    debug_command_mixing()
    test_matrix_physics() 