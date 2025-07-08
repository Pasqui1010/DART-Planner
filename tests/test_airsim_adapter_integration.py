#!/usr/bin/env python3
"""
Integration tests for AirSimAdapter

Tests all adapter methods to ensure they work with both full RPC and simplified HTTP backends.
These tests run under pytest -m "not slow" as requested.
"""

import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import numpy as np

from dart_planner.hardware.airsim_adapter import AirSimAdapter
from dart_planner.hardware.simple_airsim_interface import SimpleAirSimConfig
from dart_planner.common.types import DroneState, ControlCommand


@pytest.fixture
def mock_airsim_available():
    """Mock that airsim package is available"""
    with patch('src.hardware.airsim_adapter._FULL_AIRSIM_OK', True):
        with patch('src.hardware.airsim_adapter.AirSimDroneInterface') as mock_interface:
            mock_interface.return_value = MagicMock()
            yield mock_interface


@pytest.fixture
def mock_airsim_unavailable():
    """Mock that airsim package is unavailable"""
    with patch('src.hardware.airsim_adapter._FULL_AIRSIM_OK', False):
        yield


@pytest.fixture
def waypoints():
    """Sample waypoints for testing"""
    return [
        np.array([0.0, 0.0, -2.0]),
        np.array([10.0, 0.0, -2.0]),
        np.array([10.0, 10.0, -2.0]),
        np.array([0.0, 10.0, -2.0]),
    ]


@pytest.fixture
def control_command():
    """Sample control command for testing"""
    return ControlCommand(
        thrust=9.8,  # 1g thrust
        torque=np.array([0.1, 0.2, 0.3])  # Small torques
    )


class TestAirSimAdapterIntegration:
    """Integration tests for AirSimAdapter with both backends"""

    def test_adapter_initialization_full_backend(self, mock_airsim_available):
        """Test adapter initialization with full RPC backend"""
        adapter = AirSimAdapter()
        assert adapter is not None
        assert adapter.backend is not None
        mock_airsim_available.assert_called_once()

    def test_adapter_initialization_simple_backend(self, mock_airsim_unavailable):
        """Test adapter initialization with simplified HTTP backend"""
        adapter = AirSimAdapter()
        assert adapter is not None
        assert adapter.backend is not None
        assert hasattr(adapter.backend, 'test_dart_mission')

    def test_adapter_initialization_force_simple(self, mock_airsim_available):
        """Test adapter initialization with forced simple backend"""
        adapter = AirSimAdapter(use_simple=True)
        assert adapter is not None
        assert adapter.backend is not None
        assert hasattr(adapter.backend, 'test_dart_mission')

    def test_adapter_initialization_environment_override(self, mock_airsim_available):
        """Test adapter initialization with environment variable override"""
        with patch.dict(os.environ, {'DART_SIMPLE_AIRSIM': '1'}):
            adapter = AirSimAdapter(use_simple=False)  # Should be overridden
            assert adapter is not None
            assert adapter.backend is not None
            assert hasattr(adapter.backend, 'test_dart_mission')

    @pytest.mark.asyncio
    async def test_connect_full_backend(self, mock_airsim_available):
        """Test connection with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock(return_value=True)
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.connect()

        assert result is True
        mock_backend.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_simple_backend(self, mock_airsim_unavailable):
        """Test connection with simplified HTTP backend"""
        with patch('src.hardware.simple_airsim_interface.SimpleAirSimInterface.connect') as mock_connect:
            mock_connect.return_value = True

            adapter = AirSimAdapter()
            result = await adapter.connect()

            assert result is True
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_full_backend(self, mock_airsim_available):
        """Test disconnection with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.disconnect = AsyncMock()
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        await adapter.disconnect()

        mock_backend.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_simple_backend(self, mock_airsim_unavailable):
        """Test disconnection with simplified HTTP backend"""
        adapter = AirSimAdapter()
        await adapter.disconnect()

        # Simple interface doesn't have disconnect method, so adapter should handle gracefully
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_start_mission_full_backend(self, mock_airsim_available, waypoints):
        """Test mission start with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.start_mission = AsyncMock(return_value=True)
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.start_mission(waypoints)

        assert result is True
        mock_backend.start_mission.assert_called_once_with(waypoints)

    @pytest.mark.asyncio
    async def test_start_mission_simple_backend(self, mock_airsim_unavailable, waypoints):
        """Test mission start with simplified HTTP backend"""
        with patch('src.hardware.simple_airsim_interface.SimpleAirSimInterface.test_dart_mission') as mock_test:
            mock_test.return_value = True

            adapter = AirSimAdapter()
            result = await adapter.start_mission(waypoints)

            assert result is True
            mock_test.assert_called_once()

    @pytest.mark.asyncio
    async def test_land_full_backend(self, mock_airsim_available):
        """Test landing with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.land = AsyncMock(return_value=True)
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.land()

        assert result is True
        mock_backend.land.assert_called_once()

    @pytest.mark.asyncio
    async def test_land_simple_backend(self, mock_airsim_unavailable):
        """Test landing with simplified HTTP backend"""
        with patch.object(AirSimAdapter, 'emergency_land', new_callable=AsyncMock) as mock_emergency:
            mock_emergency.return_value = True

            adapter = AirSimAdapter()
            result = await adapter.land()

            assert result is True
            mock_emergency.assert_called_once()

    @pytest.mark.asyncio
    async def test_takeoff_full_backend(self, mock_airsim_available):
        """Test takeoff with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.takeoff = AsyncMock(return_value=True)
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.takeoff(altitude=5.0)

        assert result is True
        mock_backend.takeoff.assert_called_once_with(5.0)

    @pytest.mark.asyncio
    async def test_takeoff_simple_backend(self, mock_airsim_unavailable):
        """Test takeoff with simplified HTTP backend"""
        adapter = AirSimAdapter()
        result = await adapter.takeoff(altitude=5.0)

        assert result is True

    @pytest.mark.asyncio
    async def test_pause_full_backend(self, mock_airsim_available):
        """Test pause with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.pause = AsyncMock(return_value=True)
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.pause()

        assert result is True
        mock_backend.pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_simple_backend(self, mock_airsim_unavailable):
        """Test pause with simplified HTTP backend"""
        adapter = AirSimAdapter()
        result = await adapter.pause()

        assert result is True

    @pytest.mark.asyncio
    async def test_resume_full_backend(self, mock_airsim_available):
        """Test resume with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.resume = AsyncMock(return_value=True)
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.resume()

        assert result is True
        mock_backend.resume.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_simple_backend(self, mock_airsim_unavailable):
        """Test resume with simplified HTTP backend"""
        adapter = AirSimAdapter()
        result = await adapter.resume()

        assert result is True

    @pytest.mark.asyncio
    async def test_emergency_land_full_backend(self, mock_airsim_available):
        """Test emergency landing with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.emergency_land = AsyncMock()
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.emergency_land()

        assert result is True
        mock_backend.emergency_land.assert_called_once()

    @pytest.mark.asyncio
    async def test_emergency_land_simple_backend(self, mock_airsim_unavailable):
        """Test emergency landing with simplified HTTP backend"""
        adapter = AirSimAdapter()
        result = await adapter.emergency_land()

        assert result is True

    @pytest.mark.asyncio
    async def test_get_state_full_backend(self, mock_airsim_available):
        """Test get state with full RPC backend"""
        mock_backend = MagicMock()
        mock_state = DroneState(timestamp=time.time())
        mock_backend.get_state = AsyncMock(return_value=mock_state)
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.get_state()

        assert result is mock_state
        mock_backend.get_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_simple_backend(self, mock_airsim_unavailable):
        """Test get state with simplified HTTP backend"""
        adapter = AirSimAdapter()
        result = await adapter.get_state()

        assert isinstance(result, DroneState)
        assert hasattr(result, 'timestamp')

    @pytest.mark.asyncio
    async def test_send_control_command_full_backend(self, mock_airsim_available, control_command):
        """Test send control command with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.send_control_command = AsyncMock(return_value=True)
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.send_control_command(control_command)

        assert result is True
        mock_backend.send_control_command.assert_called_once_with(control_command)

    @pytest.mark.asyncio
    async def test_send_control_command_simple_backend(self, mock_airsim_unavailable, control_command):
        """Test send control command with simplified HTTP backend"""
        adapter = AirSimAdapter()
        result = await adapter.send_control_command(control_command)

        assert result is True

    def test_backend_property(self, mock_airsim_available):
        """Test backend property access"""
        mock_backend = MagicMock()
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        assert adapter.backend is mock_backend


class TestAirSimAdapterErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_connect_failure_full_backend(self, mock_airsim_available):
        """Test connection failure with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock(return_value=False)
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.connect()

        assert result is False

    @pytest.mark.asyncio
    async def test_connect_failure_simple_backend(self, mock_airsim_unavailable):
        """Test connection failure with simplified HTTP backend"""
        with patch('src.hardware.simple_airsim_interface.SimpleAirSimInterface.connect') as mock_connect:
            mock_connect.return_value = False

            adapter = AirSimAdapter()
            result = await adapter.connect()

            assert result is False

    @pytest.mark.asyncio
    async def test_start_mission_failure_full_backend(self, mock_airsim_available, waypoints):
        """Test mission start failure with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.start_mission = AsyncMock(return_value=False)
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()
        result = await adapter.start_mission(waypoints)

        assert result is False

    @pytest.mark.asyncio
    async def test_start_mission_no_backend_support(self, mock_airsim_unavailable, waypoints):
        """Test mission start when backend doesn't support it"""
        with patch('src.hardware.simple_airsim_interface.SimpleAirSimInterface') as mock_interface:
            # Remove test_dart_mission method to simulate unsupported backend
            mock_instance = MagicMock()
            del mock_instance.test_dart_mission
            mock_interface.return_value = mock_instance

            adapter = AirSimAdapter()

            with pytest.raises(NotImplementedError, match="Backend does not support start_mission"):
                await adapter.start_mission(waypoints)


class TestAirSimAdapterConfiguration:
    """Test configuration handling"""

    def test_config_passing_full_backend(self, mock_airsim_available):
        """Test configuration passing to full RPC backend"""
        mock_config = MagicMock()
        mock_airsim_available.return_value = MagicMock()

        adapter = AirSimAdapter(rpc_cfg=mock_config)

        mock_airsim_available.assert_called_once_with(mock_config)

    def test_config_passing_simple_backend(self, mock_airsim_unavailable):
        """Test configuration passing to simplified HTTP backend"""
        mock_config = SimpleAirSimConfig(airsim_ip="192.168.1.100", airsim_port=41452)

        adapter = AirSimAdapter(simple_cfg=mock_config)

        # Verify the config was passed correctly to SimpleAirSimInterface
        assert hasattr(adapter.backend, 'config')
        assert adapter.backend.config.airsim_ip == "192.168.1.100"
        assert adapter.backend.config.airsim_port == 41452


class TestAirSimAdapterIntegrationWorkflow:
    """Test complete workflow scenarios"""

    @pytest.mark.asyncio
    async def test_complete_mission_workflow_full_backend(self, mock_airsim_available, waypoints):
        """Test complete mission workflow with full RPC backend"""
        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock(return_value=True)
        mock_backend.takeoff = AsyncMock(return_value=True)
        mock_backend.start_mission = AsyncMock(return_value=True)
        mock_backend.pause = AsyncMock(return_value=True)
        mock_backend.resume = AsyncMock(return_value=True)
        mock_backend.land = AsyncMock(return_value=True)
        mock_backend.disconnect = AsyncMock()
        mock_airsim_available.return_value = mock_backend

        adapter = AirSimAdapter()

        # Complete workflow
        assert await adapter.connect()
        assert await adapter.takeoff(altitude=3.0)
        assert await adapter.start_mission(waypoints)
        assert await adapter.pause()
        assert await adapter.resume()
        assert await adapter.land()
        await adapter.disconnect()

        # Verify all methods were called
        mock_backend.connect.assert_called_once()
        mock_backend.takeoff.assert_called_once_with(3.0)
        mock_backend.start_mission.assert_called_once_with(waypoints)
        mock_backend.pause.assert_called_once()
        mock_backend.resume.assert_called_once()
        mock_backend.land.assert_called_once()
        mock_backend.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_mission_workflow_simple_backend(self, mock_airsim_unavailable, waypoints):
        """Test complete mission workflow with simplified HTTP backend"""
        with patch('src.hardware.simple_airsim_interface.SimpleAirSimInterface.connect') as mock_connect:
            with patch('src.hardware.simple_airsim_interface.SimpleAirSimInterface.test_dart_mission') as mock_test:
                mock_connect.return_value = True
                mock_test.return_value = True

                adapter = AirSimAdapter()

                # Complete workflow (simplified backend)
                assert await adapter.connect()
                assert await adapter.takeoff(altitude=3.0)
                assert await adapter.start_mission(waypoints)
                assert await adapter.pause()
                assert await adapter.resume()
                assert await adapter.land()
                await adapter.disconnect()

                # Verify simplified backend methods were called
                mock_connect.assert_called_once()
                mock_test.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"]) 
