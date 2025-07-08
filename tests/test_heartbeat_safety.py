"""
Integration tests for heartbeat and safety watchdog system
"""

import time
from dart_planner.common.di_container import get_container
import threading
import pytest
from unittest.mock import Mock, patch

from dart_planner.communication.heartbeat import HeartbeatMonitor, HeartbeatConfig, HeartbeatMessage
from dart_planner.communication.zmq_server import ZmqServer
from dart_planner.communication.zmq_client import ZmqClient
from dart_planner.hardware.safety_watchdog import SafetyWatchdog, MavlinkHeartbeatAdapter


class TestHeartbeatMonitor:
    """Test the heartbeat monitoring functionality"""
    
    def test_heartbeat_config(self):
        """Test heartbeat configuration"""
        config = HeartbeatConfig(
            heartbeat_interval_ms=50,
            timeout_ms=200,
            emergency_callback=lambda: None
        )
        
        assert config.heartbeat_interval_ms == 50
        assert config.timeout_ms == 200
        assert config.emergency_callback is not None
        
    def test_heartbeat_message(self):
        """Test heartbeat message creation and parsing"""
        msg = HeartbeatMessage("test_sender", 123.456)
        
        data = msg.to_dict()
        assert data["type"] == "heartbeat"
        assert data["sender_id"] == "test_sender"
        assert data["timestamp"] == 123.456
        
        # Test parsing
        parsed_msg = HeartbeatMessage.from_dict(data)
        assert parsed_msg.sender_id == "test_sender"
        assert parsed_msg.timestamp == 123.456
        
    def test_heartbeat_monitor_basic(self):
        """Test basic heartbeat monitoring"""
        emergency_called = False
        
        def emergency_callback():
            nonlocal emergency_called
            emergency_called = True
            
        config = HeartbeatConfig(
            heartbeat_interval_ms=50,
            timeout_ms=100,
            emergency_callback=emergency_callback
        )
        
        monitor = HeartbeatMonitor(config)
        monitor.start_monitoring()
        
        # Send heartbeats for a while
        for _ in range(5):
            monitor.heartbeat_received()
            time.sleep(0.02)  # 20ms
            
        # Stop monitoring
        monitor.stop_monitoring()
        
        # Emergency should not have been called
        assert not emergency_called
        
    def test_heartbeat_timeout(self):
        """Test that emergency is triggered on timeout"""
        emergency_called = False
        
        def emergency_callback():
            nonlocal emergency_called
            emergency_called = True
            
        config = HeartbeatConfig(
            heartbeat_interval_ms=50,
            timeout_ms=100,
            emergency_callback=emergency_callback
        )
        
        monitor = HeartbeatMonitor(config)
        monitor.start_monitoring()
        
        # Send one heartbeat then wait for timeout
        monitor.heartbeat_received()
        time.sleep(0.15)  # Wait longer than timeout
        
        # Emergency should have been called
        assert emergency_called
        
        monitor.stop_monitoring()
        
    def test_heartbeat_status(self):
        """Test heartbeat status reporting"""
        config = HeartbeatConfig()
        monitor = HeartbeatMonitor(config)
        
        status = monitor.get_status()
        assert "monitoring" in status
        assert "time_since_last_received_ms" in status
        assert "timeout_ms" in status


class TestZmqHeartbeat:
    """Test ZMQ communication with heartbeat"""
    
    def test_zmq_heartbeat_integration(self):
        """Test ZMQ server and client with heartbeat enabled"""
        # Start server
        server = ZmqServer(port="5556", enable_heartbeat=True)
        
        # Start client
        client = get_container().create_communication_container().get_zmq_client()
        
        # Let them exchange heartbeats
        time.sleep(0.2)
        
        # Check status
        assert server.heartbeat_monitor is not None
        assert client.heartbeat_monitor is not None
        
        server_status = server.heartbeat_monitor.get_status()
        client_status = client.heartbeat_monitor.get_status()
        
        assert server_status["monitoring"]
        assert client_status["monitoring"]
        
        # Cleanup
        client.close()
        server.close()
        
    def test_zmq_heartbeat_timeout(self):
        """Test ZMQ heartbeat timeout when connection is lost"""
        emergency_called = False
        
        def emergency_callback():
            nonlocal emergency_called
            emergency_called = True
            
        # Start server
        server = ZmqServer(port="5557", enable_heartbeat=True, emergency_callback=emergency_callback)
        
        # Start client
        client = get_container().create_communication_container().get_zmq_client()host="localhost", port="5557", enable_heartbeat=True, emergency_callback=emergency_callback)
        
        # Let them establish connection
        time.sleep(0.1)
        
        # Close client abruptly
        client.socket.close()
        client.context.term()
        
        # Wait for timeout
        time.sleep(0.6)  # Longer than 500ms timeout
        
        # Emergency should have been triggered
        assert emergency_called
        
        # Cleanup
        server.close()


class TestSafetyWatchdog:
    """Test the safety watchdog integration"""
    
    def test_safety_watchdog_creation(self):
        """Test safety watchdog creation and configuration"""
        config = {
            "heartbeat_interval_ms": 100,
            "heartbeat_timeout_ms": 500
        }
        
        watchdog = SafetyWatchdog(config)
        
        assert watchdog.heartbeat_monitor is not None
        assert not watchdog._emergency_triggered
        
    def test_safety_watchdog_emergency_callback(self):
        """Test custom emergency callback"""
        emergency_called = False
        
        def emergency_callback():
            nonlocal emergency_called
            emergency_called = True
            
        config = {"heartbeat_timeout_ms": 100}
        watchdog = SafetyWatchdog(config)
        watchdog.set_emergency_callback(emergency_callback)
        
        # Trigger emergency
        watchdog._trigger_emergency_landing()
        
        assert emergency_called
        assert watchdog._emergency_triggered
        
    def test_safety_watchdog_status(self):
        """Test safety watchdog status reporting"""
        config = {"heartbeat_timeout_ms": 500}
        watchdog = SafetyWatchdog(config)
        
        status = watchdog.get_status()
        
        assert "emergency_triggered" in status
        assert "heartbeat_status" in status
        assert "airsim_safety_configured" in status
        
    def test_safety_watchdog_reset(self):
        """Test emergency state reset"""
        config = {"heartbeat_timeout_ms": 100}
        watchdog = SafetyWatchdog(config)
        
        # Trigger emergency
        watchdog._trigger_emergency_landing()
        assert watchdog._emergency_triggered
        
        # Reset
        watchdog.reset_emergency_state()
        assert not watchdog._emergency_triggered


class TestMavlinkHeartbeatAdapter:
    """Test MAVLink heartbeat adapter"""
    
    def test_mavlink_adapter_creation(self):
        """Test MAVLink adapter creation"""
        config = {"heartbeat_timeout_ms": 500}
        watchdog = SafetyWatchdog(config)
        adapter = MavlinkHeartbeatAdapter(watchdog)
        
        assert adapter.safety_watchdog == watchdog
        
    def test_mavlink_heartbeat_received(self):
        """Test handling of MAVLink heartbeat messages"""
        config = {"heartbeat_timeout_ms": 500}
        watchdog = SafetyWatchdog(config)
        adapter = MavlinkHeartbeatAdapter(watchdog)
        
        # Mock MAVLink message
        mock_msg = Mock()
        mock_msg.get_srcSystem.return_value = 1
        mock_msg.get_srcComponent.return_value = 1
        
        # Process heartbeat
        adapter.on_mavlink_heartbeat(mock_msg)
        
        # Check that heartbeat was received
        status = watchdog.get_status()
        assert status["heartbeat_status"]["time_since_last_received_ms"] < 100  # Should be recent


if __name__ == "__main__":
    # Run basic tests
    print("Testing heartbeat monitor...")
    test_monitor = TestHeartbeatMonitor()
    test_monitor.test_heartbeat_config()
    test_monitor.test_heartbeat_message()
    test_monitor.test_heartbeat_monitor_basic()
    print("✅ Basic heartbeat tests passed")
    
    print("Testing safety watchdog...")
    test_watchdog = TestSafetyWatchdog()
    test_watchdog.test_safety_watchdog_creation()
    test_watchdog.test_safety_watchdog_emergency_callback()
    test_watchdog.test_safety_watchdog_status()
    print("✅ Safety watchdog tests passed")
    
    print("All tests completed successfully!") 
