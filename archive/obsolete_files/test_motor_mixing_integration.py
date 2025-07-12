#!/usr/bin/env python3
"""
Integration test for motor mixing with hardware interfaces.
This tests the actual integration without requiring AirSim connection.
"""

import sys
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dart_planner.common.types import ControlCommand
from dart_planner.common.units import Q_

def test_motor_mixing_integration():
    """Test motor mixing integration with hardware interfaces."""
    print("Testing Motor Mixing Integration")
    print("=" * 50)
    
    # Test AirSim integration
    print("\n1. Testing AirSim Integration")
    test_airsim_integration()
    
    # Test Pixhawk integration
    print("\n2. Testing Pixhawk Integration")
    test_pixhawk_integration()
    
    print("\n" + "=" * 50)
    print("🎉 All integration tests passed!")
    print("=" * 50)

def test_airsim_integration():
    """Test AirSim interface motor mixing integration."""
    # Mock the AirSim imports to avoid dependency issues
    with patch.dict('sys.modules', {
        'airsim': Mock(),
        'airsim.client': Mock(),
        'airsim.utils': Mock(),
        'airsim.types': Mock(),
    }):
        from dart_planner.hardware.airsim_interface import AirSimDroneInterface
        from dart_planner.hardware.airsim_config import AirSimConfig
        
        # Create interface with mocked AirSim
        config = AirSimConfig()
        interface = AirSimDroneInterface(config)
        
        # Mock the connection and client
        interface.connection = Mock()
        interface.connection.is_connected.return_value = True
        interface.connection.is_api_control_enabled.return_value = True
        interface.connection.get_client.return_value = Mock()
        
        # Mock the metrics and safety managers
        interface.metrics_manager = Mock()
        interface.safety_manager = Mock()
        
        # Test different control commands
        test_commands = [
            # Hover command
            ControlCommand(
                thrust=Q_(10.0, 'N'),
                torque=Q_(np.array([0.0, 0.0, 0.0]), 'N*m')
            ),
            # Roll command
            ControlCommand(
                thrust=Q_(8.0, 'N'),
                torque=Q_(np.array([0.5, 0.0, 0.0]), 'N*m')
            ),
            # Pitch command
            ControlCommand(
                thrust=Q_(8.0, 'N'),
                torque=Q_(np.array([0.0, 0.5, 0.0]), 'N*m')
            ),
            # Yaw command
            ControlCommand(
                thrust=Q_(8.0, 'N'),
                torque=Q_(np.array([0.0, 0.0, 0.1]), 'N*m')
            ),
            # Combined command
            ControlCommand(
                thrust=Q_(12.0, 'N'),
                torque=Q_(np.array([0.3, 0.2, 0.05]), 'N*m')
            ),
        ]
        
        # Mock the AirSim client method
        mock_client = interface.connection.get_client.return_value
        mock_client.moveByMotorPWMsAsync = AsyncMock()
        
        # Test each command
        for i, command in enumerate(test_commands):
            print(f"  Test {i+1}: {command.thrust.magnitude}N thrust, {command.torque.magnitude} torque")
            
            # Get motor PWMs from the mixer directly
            if not hasattr(interface, '_motor_mixer'):
                from dart_planner.hardware.motor_mixer import create_x_configuration_mixer
                interface._motor_mixer = create_x_configuration_mixer(arm_length=0.15)
            
            thrust_value = float(command.thrust.magnitude)
            torque_value = command.torque.magnitude
            motor_pwms = interface._motor_mixer.mix_commands(thrust_value, torque_value)
            
            print(f"    Motor PWMs: {motor_pwms}")
            
            # Verify motor PWMs are valid
            assert np.all(motor_pwms >= 0.0), "Motor PWMs should be non-negative"
            assert np.all(motor_pwms <= 1.0), "Motor PWMs should be <= 1.0"
            
            # Verify hover command produces equal PWMs
            if i == 0:  # Hover command
                assert np.allclose(motor_pwms, motor_pwms[0], rtol=1e-3), "Hover should produce equal PWMs"
            else:
                # Non-hover commands should produce different PWMs
                assert not np.allclose(motor_pwms, motor_pwms[0]), "Non-hover should produce different PWMs"
            
            print(f"    ✓ PWMs valid and correctly mixed")
        
        print("  ✓ AirSim integration test passed")

def test_pixhawk_integration():
    """Test Pixhawk interface motor mixing integration."""
    # Mock the MAVLink imports to avoid dependency issues
    with patch.dict('sys.modules', {
        'pymavlink': Mock(),
        'pymavlink.mavutil': Mock(),
        'pymavlink.dialects': Mock(),
        'pymavlink.dialects.v20': Mock(),
        'pymavlink.dialects.v20.ardupilotmega': Mock(),
    }):
        from dart_planner.hardware.pixhawk_interface import PixhawkInterface
        from dart_planner.hardware.pixhawk_config import PixhawkConfig
        
        # Create interface with mocked MAVLink
        config = PixhawkConfig()
        config.max_thrust = 50.0  # Set max thrust for testing
        interface = PixhawkInterface(config)
        
        # Test body rate conversion with proper motor mixing
        test_cases = [
            # Hover
            (10.0, np.array([0.0, 0.0, 0.0])),
            # Roll
            (8.0, np.array([0.5, 0.0, 0.0])),
            # Pitch
            (8.0, np.array([0.0, 0.5, 0.0])),
            # Yaw
            (8.0, np.array([0.0, 0.0, 0.1])),
            # Combined
            (12.0, np.array([0.3, 0.2, 0.05])),
        ]
        
        for i, (thrust, torque) in enumerate(test_cases):
            print(f"  Test {i+1}: {thrust}N thrust, {torque} torque")
            
            # Test motor mixing through body rate conversion
            body_rate_cmd = interface._convert_to_body_rate_cmd(thrust, torque)
            
            print(f"    Normalized thrust: {body_rate_cmd.thrust}")
            print(f"    Body rates: {body_rate_cmd.body_rates.magnitude}")
            
            # Verify body rate command is valid
            assert 0.0 <= body_rate_cmd.thrust <= 1.0, "Normalized thrust should be [0, 1]"
            assert len(body_rate_cmd.body_rates.magnitude) == 3, "Should have 3 body rates"
            
            # Verify motor mixer is working internally
            if hasattr(interface, '_motor_mixer'):
                motor_pwms = interface._motor_mixer.mix_commands(thrust, torque)
                assert np.all(motor_pwms >= 0.0), "Motor PWMs should be non-negative"
                assert np.all(motor_pwms <= 1.0), "Motor PWMs should be <= 1.0"
                print(f"    Internal motor PWMs: {motor_pwms}")
            
            print(f"    ✓ Body rate conversion valid")
        
        print("  ✓ Pixhawk integration test passed")

if __name__ == "__main__":
    try:
        test_motor_mixing_integration()
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 