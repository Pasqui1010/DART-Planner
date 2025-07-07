#!/usr/bin/env python3
"""
Unit tests for PixhawkInterface with MAVLink connection mocking.

Tests the hardware interface without requiring actual hardware or MAVLink connections.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import pytest
import numpy as np

from src.hardware.pixhawk_interface import PixhawkInterface, HardwareConfig
from src.common.types import DroneState, BodyRateCommand


class MockMAVLinkMessage:
    """Mock MAVLink message for testing"""
    
    def __init__(self, msg_type: str, **kwargs):
        self._type = msg_type
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def get_type(self):
        return self._type


class MockMAVLinkConnection:
    """Mock MAVLink connection for testing"""
    
    def __init__(self):
        self.target_system = 1
        self.target_component = 1
        self.mav = Mock()
        self.mav.request_data_stream_send = Mock()
        self.mav.set_mode_send = Mock()
        self.mav.command_long_send = Mock()
        self.mav.set_attitude_target_send = Mock()
        self.mav.set_position_target_local_ned_send = Mock()
        
        # Mock mode mapping
        self._mode_mapping = {
            'OFFBOARD': 4,
            'GUIDED': 3,
            'STABILIZE': 0,
            'AUTO': 3
        }
    
    def mode_mapping(self):
        return self._mode_mapping
    
    def wait_heartbeat(self, timeout=None):
        """Mock heartbeat wait"""
        pass
    
    def recv_match(self, type=None, blocking=False, timeout=None):
        """Mock message reception"""
        if type == 'COMMAND_ACK':
            return MockMAVLinkMessage('COMMAND_ACK', result=0)  # MAV_RESULT_ACCEPTED
        elif type == 'HEARTBEAT':
            return MockMAVLinkMessage('HEARTBEAT', base_mode=0x80, custom_mode=4)  # Armed, OFFBOARD
        elif type == 'ATTITUDE':
            return MockMAVLinkMessage('ATTITUDE', 
                                    roll=0.1, pitch=0.2, yaw=0.3,
                                    rollspeed=0.01, pitchspeed=0.02, yawspeed=0.03)
        elif type == 'GLOBAL_POSITION_INT':
            return MockMAVLinkMessage('GLOBAL_POSITION_INT',
                                    lat=10000000, lon=20000000, alt=5000,  # 1.0, 2.0, 5.0
                                    vx=100, vy=200, vz=50)  # 1.0, 2.0, 0.5 m/s
        return None
    
    def close(self):
        """Mock connection close"""
        pass


@pytest.fixture
def mock_mavlink_connection():
    """Fixture to provide a mock MAVLink connection"""
    return MockMAVLinkConnection()


@pytest.fixture
def pixhawk_interface():
    """Fixture to provide a PixhawkInterface instance"""
    config = HardwareConfig(
        mavlink_connection="udp:127.0.0.1:14550",  # SITL connection
        control_frequency=100.0,  # Lower for testing
        planning_frequency=20.0,  # Lower for testing
        max_planning_time_ms=50.0  # More lenient for testing
    )
    return PixhawkInterface(config)


class TestPixhawkInterface:
    """Test cases for PixhawkInterface"""
    
    def test_initialization(self, pixhawk_interface):
        """Test PixhawkInterface initialization"""
        assert pixhawk_interface is not None
        assert pixhawk_interface.config.control_frequency == 100.0
        assert pixhawk_interface.config.planning_frequency == 20.0
        assert not pixhawk_interface.is_connected
        assert not pixhawk_interface.is_armed
        assert pixhawk_interface.planner is not None
        assert pixhawk_interface.controller is not None
    
    def test_euler_to_quaternion(self, pixhawk_interface):
        """Test euler to quaternion conversion"""
        # Test zero angles
        q = pixhawk_interface._euler_to_quaternion(0.0, 0.0, 0.0)
        np.testing.assert_array_almost_equal(q, [1.0, 0.0, 0.0, 0.0])
        
        # Test 90 degree roll
        q = pixhawk_interface._euler_to_quaternion(np.pi/2, 0.0, 0.0)
        expected = [0.7071068, 0.7071068, 0.0, 0.0]
        np.testing.assert_array_almost_equal(q, expected, decimal=6)
        
        # Test 90 degree pitch
        q = pixhawk_interface._euler_to_quaternion(0.0, np.pi/2, 0.0)
        expected = [0.7071068, 0.0, 0.7071068, 0.0]
        np.testing.assert_array_almost_equal(q, expected, decimal=6)
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_connect_success(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test successful connection to Pixhawk"""
        mock_mavutil.return_value = mock_mavlink_connection
        
        result = await pixhawk_interface.connect()
        
        assert result is True
        assert pixhawk_interface.is_connected is True
        assert pixhawk_interface.mavlink_connection is not None
        assert pixhawk_interface.target_system == 1
        assert pixhawk_interface.target_component == 1
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_connect_failure(self, mock_mavutil, pixhawk_interface):
        """Test connection failure"""
        mock_mavutil.side_effect = Exception("Connection failed")
        
        result = await pixhawk_interface.connect()
        
        assert result is False
        assert pixhawk_interface.is_connected is False
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_set_mode_success(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test successful mode setting"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        
        result = await pixhawk_interface.set_mode("OFFBOARD")
        
        assert result is True
        mock_mavlink_connection.mav.set_mode_send.assert_called_once()
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_set_mode_failure(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test mode setting failure"""
        mock_mavutil.return_value = mock_mavlink_connection
        # Override recv_match to return failure
        mock_mavlink_connection.recv_match.return_value = MockMAVLinkMessage('COMMAND_ACK', result=1)  # MAV_RESULT_DENIED
        await pixhawk_interface.connect()
        
        result = await pixhawk_interface.set_mode("OFFBOARD")
        
        assert result is False
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_arm_success(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test successful arming"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        
        result = await pixhawk_interface.arm()
        
        assert result is True
        assert pixhawk_interface.is_armed is True
        mock_mavlink_connection.mav.command_long_send.assert_called_once()
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_disarm_success(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test successful disarming"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        pixhawk_interface.is_armed = True
        
        result = await pixhawk_interface.disarm()
        
        assert result is True
        assert pixhawk_interface.is_armed is False
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_takeoff_success(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test successful takeoff command"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        pixhawk_interface.is_armed = True
        pixhawk_interface.current_state.position = np.array([0.0, 0.0, 0.0])
        
        result = await pixhawk_interface.takeoff(10.0)
        
        assert result is True
        mock_mavlink_connection.mav.command_long_send.assert_called_once()
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_takeoff_not_armed(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test takeoff when not armed"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        # Not armed
        
        result = await pixhawk_interface.takeoff(10.0)
        
        assert result is False
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_land_success(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test successful land command"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        
        result = await pixhawk_interface.land()
        
        assert result is True
        mock_mavlink_connection.mav.command_long_send.assert_called_once()
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_send_body_rate_target(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test sending body rate target command"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        pixhawk_interface.is_armed = True
        
        body_rate_cmd = BodyRateCommand(
            body_rates=np.array([0.1, 0.2, 0.3]),
            thrust=0.5
        )
        
        await pixhawk_interface._send_body_rate_target(body_rate_cmd)
        
        mock_mavlink_connection.mav.set_attitude_target_send.assert_called_once()
        call_args = mock_mavlink_connection.mav.set_attitude_target_send.call_args
        assert call_args[0][4] == 0.1  # roll rate
        assert call_args[0][5] == 0.2  # pitch rate
        assert call_args[0][6] == 0.3  # yaw rate
        assert call_args[0][7] == 0.5  # thrust
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_update_state_from_messages(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test state update from MAVLink messages"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        
        # Mock message queue
        messages = [
            MockMAVLinkMessage('ATTITUDE', 
                             roll=0.1, pitch=0.2, yaw=0.3,
                             rollspeed=0.01, pitchspeed=0.02, yawspeed=0.03),
            MockMAVLinkMessage('GLOBAL_POSITION_INT',
                             lat=10000000, lon=20000000, alt=5000,
                             vx=100, vy=200, vz=50),
            MockMAVLinkMessage('HEARTBEAT', base_mode=0x80, custom_mode=4)
        ]
        
        mock_mavlink_connection.recv_match.side_effect = messages + [None]
        
        await pixhawk_interface._update_state()
        
        # Check state was updated
        assert pixhawk_interface.current_state.attitude[0] == 0.1
        assert pixhawk_interface.current_state.attitude[1] == 0.2
        assert pixhawk_interface.current_state.attitude[2] == 0.3
        assert pixhawk_interface.is_armed is True
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_get_current_mode(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test getting current flight mode"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        
        mode = await pixhawk_interface.get_current_mode()
        
        assert mode == "OFFBOARD"
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_get_current_mode_disconnected(self, mock_mavutil, pixhawk_interface):
        """Test getting mode when disconnected"""
        mode = await pixhawk_interface.get_current_mode()
        assert mode == "DISCONNECTED"
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_performance_report(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test performance report generation"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        
        # Add some mock performance data
        pixhawk_interface.performance_stats["planning_times"] = [10.0, 15.0, 20.0]
        pixhawk_interface.performance_stats["control_loop_times"] = [2.0, 3.0, 4.0]
        pixhawk_interface.performance_stats["total_commands_sent"] = 100
        pixhawk_interface.performance_stats["planning_failures"] = 2
        
        report = pixhawk_interface.get_performance_report()
        
        assert "avg_planning_time_ms" in report
        assert "max_planning_time_ms" in report
        assert "avg_control_loop_time_ms" in report
        assert "total_commands_sent" in report
        assert "planning_failures" in report
        assert report["avg_planning_time_ms"] == 15.0
        assert report["total_commands_sent"] == 100
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_safety_monitoring(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test safety monitoring functionality"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        
        # Test velocity limit violation
        pixhawk_interface.current_state.velocity = np.array([20.0, 0.0, 0.0])  # Exceeds 15 m/s limit
        
        await pixhawk_interface._check_safety_conditions()
        
        assert pixhawk_interface.failsafe_active is True
        assert pixhawk_interface.emergency_stop is True
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_heartbeat_timeout_failsafe(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test failsafe triggered by heartbeat timeout"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        
        # Simulate old heartbeat
        pixhawk_interface.last_heartbeat = time.time() - 10.0  # 10 seconds ago
        
        await pixhawk_interface._safety_monitor_loop()
        
        assert pixhawk_interface.failsafe_active is True
        assert pixhawk_interface.emergency_stop is True
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_close_connection(self, mock_mavutil, pixhawk_interface, mock_mavlink_connection):
        """Test closing the connection"""
        mock_mavutil.return_value = mock_mavlink_connection
        await pixhawk_interface.connect()
        
        await pixhawk_interface.close()
        
        assert pixhawk_interface.is_connected is False
        mock_mavlink_connection.close.assert_called_once()


class TestPixhawkInterfaceIntegration:
    """Integration tests for PixhawkInterface"""
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_full_connection_workflow(self, mock_mavutil):
        """Test complete connection and setup workflow"""
        mock_connection = MockMAVLinkConnection()
        mock_mavutil.return_value = mock_connection
        
        interface = PixhawkInterface()
        
        # Connect
        assert await interface.connect()
        assert interface.is_connected
        
        # Set mode
        assert await interface.set_mode("OFFBOARD")
        
        # Arm
        assert await interface.arm()
        assert interface.is_armed
        
        # Close
        await interface.close()
        assert not interface.is_connected
    
    @patch('src.hardware.pixhawk_interface.mavutil.mavlink_connection')
    async def test_mission_start_stop(self, mock_mavutil):
        """Test mission start and stop functionality"""
        mock_connection = MockMAVLinkConnection()
        mock_mavutil.return_value = mock_connection
        
        interface = PixhawkInterface()
        await interface.connect()
        await interface.arm()
        
        # Start mission
        waypoints = np.array([[10.0, 0.0, 5.0], [10.0, 10.0, 5.0]])
        assert await interface.start_mission(waypoints)
        assert interface.mission_active
        
        # Stop mission
        await interface.stop_mission()
        assert not interface.mission_active
        assert interface.emergency_stop


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 