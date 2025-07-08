import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from unittest.mock import MagicMock, patch
from dart_planner.hardware.airsim_adapter import AirSimAdapter

@pytest.fixture
def mock_airsim_client():
    client = MagicMock()
    client.getMultirotorState.return_value.kinematics_estimated.position = (1,2,3)
    client.getMultirotorState.return_value.kinematics_estimated.linear_velocity = (0,0,0)
    client.getMultirotorState.return_value.kinematics_estimated.orientation = (1,0,0,0)
    client.getMultirotorState.return_value.landed_state = 1
    return client


def test_connect_disconnect(mock_airsim_client):
    adapter = AirSimAdapter(client=mock_airsim_client)
    mock_airsim_client.confirmConnection = MagicMock()
    mock_airsim_client.enableApiControl = MagicMock()
    adapter.connect()
    assert adapter.is_connected() is True
    adapter.disconnect()
    assert adapter.is_connected() is False


def test_send_command_arm(mock_airsim_client):
    adapter = AirSimAdapter(client=mock_airsim_client)
    mock_airsim_client.armDisarm = MagicMock()
    adapter.send_command("arm")
    mock_airsim_client.armDisarm.assert_called_with(True)


def test_send_command_takeoff(mock_airsim_client):
    adapter = AirSimAdapter(client=mock_airsim_client)
    mock_airsim_client.takeoffAsync = MagicMock(return_value=MagicMock(join=lambda: None))
    adapter.send_command("takeoff")
    mock_airsim_client.takeoffAsync.assert_called_once()


def test_send_command_not_implemented(mock_airsim_client):
    adapter = AirSimAdapter(client=mock_airsim_client)
    with pytest.raises(NotImplementedError):
        adapter.send_command("unsupported_command")


def test_get_state(mock_airsim_client):
    adapter = AirSimAdapter(client=mock_airsim_client)
    state = adapter.get_state()
    assert "position" in state
    assert "velocity" in state
    assert "orientation" in state
    assert "armed" in state


def test_reset(mock_airsim_client):
    adapter = AirSimAdapter(client=mock_airsim_client)
    mock_airsim_client.reset = MagicMock()
    adapter.reset()
    mock_airsim_client.reset.assert_called_once()


def test_emergency_stop(mock_airsim_client):
    adapter = AirSimAdapter(client=mock_airsim_client)
    mock_airsim_client.emergencyStop = MagicMock()
    adapter.client.emergencyStop = mock_airsim_client.emergencyStop
    adapter.emergency_stop()
    mock_airsim_client.emergencyStop.assert_called_once()


def test_get_capabilities(mock_airsim_client):
    adapter = AirSimAdapter(client=mock_airsim_client)
    caps = adapter.get_capabilities()
    assert caps["simulated"] is True


def test_update(mock_airsim_client):
    adapter = AirSimAdapter(client=mock_airsim_client)
    # Should not raise
    adapter.update() 
