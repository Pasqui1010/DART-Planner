import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from unittest.mock import MagicMock, patch
from dart_planner.hardware.pixhawk_adapter import PixhawkAdapter
from dart_planner.hardware.pixhawk_interface import HardwareConfig

@pytest.fixture
def mock_pixhawk_interface(monkeypatch):
    # Patch PixhawkInterface in the adapter module
    with patch('src.hardware.pixhawk_adapter.PixhawkInterface') as MockIface:
        yield MockIface


def test_connect_disconnect(mock_pixhawk_interface):
    adapter = PixhawkAdapter(HardwareConfig())
    adapter._iface.connect = MagicMock()
    adapter._iface.close = MagicMock()
    adapter.connect()
    adapter._iface.connect.assert_called_once()
    adapter.disconnect()
    adapter._iface.close.assert_called_once()


def test_is_connected(mock_pixhawk_interface):
    adapter = PixhawkAdapter(HardwareConfig())
    adapter._iface.is_connected = True
    assert adapter.is_connected() is True
    adapter._iface.is_connected = False
    assert adapter.is_connected() is False


def test_send_command_arm(mock_pixhawk_interface):
    adapter = PixhawkAdapter(HardwareConfig())
    adapter._iface.arm = MagicMock(return_value=True)
    result = adapter.send_command("arm")
    adapter._iface.arm.assert_called_once()
    assert result is True


def test_send_command_not_implemented(mock_pixhawk_interface):
    adapter = PixhawkAdapter(HardwareConfig())
    with pytest.raises(NotImplementedError):
        adapter.send_command("unsupported_command")


def test_get_state(mock_pixhawk_interface):
    adapter = PixhawkAdapter(HardwareConfig())
    adapter._iface.current_state = MagicMock()
    adapter._iface.current_state.__dict__ = {"foo": 123}
    state = adapter.get_state()
    assert state == {"foo": 123}


def test_reset(mock_pixhawk_interface):
    adapter = PixhawkAdapter(HardwareConfig())
    adapter._iface.current_state = MagicMock()
    adapter._iface.performance_stats = {"dummy": 1}
    adapter.reset()
    assert adapter._iface.performance_stats["total_commands_sent"] == 0


def test_emergency_stop(mock_pixhawk_interface):
    adapter = PixhawkAdapter(HardwareConfig())
    adapter._iface._trigger_failsafe = MagicMock()
    adapter.emergency_stop()
    adapter._iface._trigger_failsafe.assert_called_once()


def test_get_capabilities(mock_pixhawk_interface):
    config = HardwareConfig(max_velocity=10, max_acceleration=5, max_altitude=100, safety_radius=50, max_thrust=20)
    adapter = PixhawkAdapter(config)
    caps = adapter.get_capabilities()
    assert caps["max_velocity"] == 10
    assert caps["max_acceleration"] == 5
    assert caps["max_altitude"] == 100
    assert caps["safety_radius"] == 50
    assert caps["max_thrust"] == 20


def test_update(mock_pixhawk_interface):
    adapter = PixhawkAdapter(HardwareConfig())
    # Should not raise
    adapter.update() 
