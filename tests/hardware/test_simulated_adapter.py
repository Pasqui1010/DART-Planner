import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from dart_planner.hardware.simulated_adapter import SimulatedAdapter

def test_connect_disconnect():
    adapter = SimulatedAdapter()
    adapter.connect()
    assert adapter.is_connected() is True
    adapter.disconnect()
    assert adapter.is_connected() is False


def test_send_command_arm():
    adapter = SimulatedAdapter()
    adapter.send_command("arm")
    assert adapter.get_state()["armed"] is True
    adapter.send_command("disarm")
    assert adapter.get_state()["armed"] is False


def test_send_command_takeoff_land():
    adapter = SimulatedAdapter()
    adapter.send_command("takeoff")
    assert adapter.get_state()["position"] == (0.0, 0.0, 2.0)
    adapter.send_command("land")
    assert adapter.get_state()["position"] == (0.0, 0.0, 0.0)


def test_send_command_moveToPosition():
    adapter = SimulatedAdapter()
    adapter.send_command("moveToPosition", {"x": 1, "y": 2, "z": 3})
    assert adapter.get_state()["position"] == (1, 2, 3)


def test_send_command_not_implemented():
    adapter = SimulatedAdapter()
    with pytest.raises(NotImplementedError):
        adapter.send_command("unsupported_command")


def test_get_state():
    adapter = SimulatedAdapter()
    state = adapter.get_state()
    assert "position" in state
    assert "velocity" in state
    assert "orientation" in state
    assert "armed" in state


def test_reset():
    adapter = SimulatedAdapter()
    adapter.send_command("arm")
    adapter.send_command("moveToPosition", {"x": 5, "y": 5, "z": 5})
    adapter.reset()
    state = adapter.get_state()
    assert state["position"] == (0.0, 0.0, 0.0)
    assert state["armed"] is False


def test_emergency_stop():
    adapter = SimulatedAdapter()
    adapter.send_command("arm")
    adapter.send_command("moveToPosition", {"x": 1, "y": 2, "z": 3})
    adapter.emergency_stop()
    state = adapter.get_state()
    assert state["velocity"] == (0.0, 0.0, 0.0)
    assert state["armed"] is False


def test_get_capabilities():
    adapter = SimulatedAdapter()
    caps = adapter.get_capabilities()
    assert caps["simulated"] is True


def test_update():
    adapter = SimulatedAdapter()
    # Should not raise
    adapter.update() 
