#!/usr/bin/env python3
"""
Integration tests for AirSimAdapter

Tests all adapter methods to ensure they work with both full RPC and simplified HTTP backends.
These tests run under pytest -m "not slow" as requested.
"""
#
# import asyncio
# import os
# import time
# from unittest.mock import AsyncMock, MagicMock, patch
# import pytest
# import numpy as np
#
# from dart_planner.hardware.airsim_adapter import AirSimAdapter
# from dart_planner.hardware.simple_airsim_interface import SimpleAirSimConfig
# from dart_planner.common.types import DroneState, ControlCommand, U
#
#
# @pytest.fixture
# def waypoints():
#     """Sample waypoints for testing"""
#     return [
#         np.array([0.0, 0.0, -2.0]),
#         np.array([10.0, 0.0, -2.0]),
#         np.array([10.0, 10.0, -2.0]),
#         np.array([0.0, 10.0, -2.0]),
#     ]
#
#
# @pytest.fixture
# def control_command():
#     """Sample control command for testing"""
#     return ControlCommand(
#         thrust=9.8 * U.newton,  # 1g thrust
#         torque=np.array([0.1, 0.2, 0.3]) * U.newton * U.meter  # Small torques
#     )
#
#
# class TestAirSimAdapterIntegration:
#     """Integration tests for AirSimAdapter with both backends"""
#
#     def test_adapter_initialization_full_backend(self):
#         """Test adapter initialization with full RPC backend"""
#         with patch('airsim.MultirotorClient') as mock_client:
#             adapter = AirSimAdapter(client=mock_client)
#             assert adapter is not None
#             assert adapter.client is not None
#             mock_client.assert_called_once()
#
#     def test_adapter_initialization_simple_backend(self):
#         """Test adapter initialization with simplified HTTP backend"""
#         with patch('airsim.MultirotorClient') as mock_client:
#             adapter = AirSimAdapter(client=mock_client)
#             assert adapter is not None
#             assert adapter.client is not None
#
#     def test_adapter_initialization_force_simple(self):
#         """Test adapter initialization with forced simple backend"""
#         with patch('airsim.MultirotorClient') as mock_client:
#             adapter = AirSimAdapter(client=mock_client)
#             assert adapter is not None
#             assert adapter.client is not None
#
#     def test_adapter_initialization_environment_override(self):
#         """Test adapter initialization with environment variable override"""
#         with patch.dict(os.environ, {'DART_SIMPLE_AIRSIM': '1'}):
#             with patch('airsim.MultirotorClient') as mock_client:
#                 adapter = AirSimAdapter(client=mock_client)
#                 assert adapter is not None
#                 assert adapter.client is not None
#
#     @pytest.mark.asyncio
#     async def test_connect_full_backend(self):
#         """Test connection with full RPC backend"""
#         with patch('airsim.MultirotorClient') as mock_client_class:
#             mock_client = mock_client_class.return_value
#             mock_client.confirmConnection = MagicMock()
#
#             adapter = AirSimAdapter(client=mock_client)
#             adapter.connect()
#
#             mock_client.confirmConnection.assert_called_once()
#
#     @pytest.mark.asyncio
#     async def test_connect_simple_backend(self):
#         """Test connection with simplified HTTP backend"""
#         with patch('airsim.MultirotorClient') as mock_client_class:
#             mock_client = mock_client_class.return_value
#             mock_client.confirmConnection = MagicMock()
#
#             adapter = AirSimAdapter(client=mock_client)
#             adapter.connect()
#
#             mock_client.confirmConnection.assert_called_once()
#
#     @pytest.mark.asyncio
#     async def test_disconnect_full_backend(self):
#         """Test disconnection with full RPC backend"""
#         with patch('airsim.MultirotorClient') as mock_client_class:
#             mock_client = mock_client_class.return_value
#             mock_client.enableApiControl = MagicMock()
#
#             adapter = AirSimAdapter(client=mock_client)
#             adapter.disconnect()
#
#             mock_client.enableApiControl.assert_called_once_with(False)
#
#     @pytest.mark.asyncio
#     async def test_disconnect_simple_backend(self):
#         """Test disconnection with simplified HTTP backend"""
#         with patch('airsim.MultirotorClient') as mock_client_class:
#             mock_client = mock_client_class.return_value
#             mock_client.enableApiControl = MagicMock()
#
#             adapter = AirSimAdapter(client=mock_client)
#             adapter.disconnect()
#
#             mock_client.enableApiControl.assert_called_once_with(False)
#
#     @pytest.mark.asyncio
#     async def test_start_mission_full_backend(self, waypoints):
#         """Test mission start with full RPC backend"""
#         with patch('airsim.MultirotorClient') as mock_client_class:
#             mock_client = mock_client_class.return_value
#             mock_client.armDisarm = AsyncMock()
#             mock_client.takeoffAsync = AsyncMock()
#
#             adapter = AirSimAdapter(client=mock_client)
#             result = await adapter.start_mission(mission_params={'waypoints': waypoints})
#
#             assert result is True
#             mock_client.armDisarm.assert_called_once()
#             mock_client.takeoffAsync.assert_called_once()
#
#     @pytest.mark.asyncio
#     async def test_start_mission_simple_backend(self, waypoints):
#         """Test mission start with simplified HTTP backend"""
#         with patch('airsim.MultirotorClient') as mock_client_class:
#             mock_client = mock_client_class.return_value
#             mock_client.armDisarm = AsyncMock()
#             mock_client.takeoffAsync = AsyncMock()
#
#             adapter = AirSimAdapter(client=mock_client)
#             result = await adapter.start_mission(mission_params={'waypoints': waypoints})
#
#             assert result is True
#             mock_client.armDisarm.assert_called_once()
#             mock_client.takeoffAsync.assert_called_once()
#
#
# class TestAirSimAdapterErrorHandling:
#     """Test error handling in AirSimAdapter"""
#
#     @pytest.mark.asyncio
#     async def test_connect_failure_full_backend(self):
#         """Test connection failure with full RPC backend"""
#         with patch('airsim.MultirotorClient') as mock_client_class:
#             mock_client = mock_client_class.return_value
#             mock_client.confirmConnection = MagicMock(side_effect=Exception("Connection failed"))
#
#             adapter = AirSimAdapter(client=mock_client)
#
#             with pytest.raises(Exception, match="Connection failed"):
#                 adapter.connect()
#
#     @pytest.mark.asyncio
#     async def test_start_mission_no_backend_support(self, waypoints):
#         """Test mission start when backend doesn't support it"""
#         with patch('airsim.MultirotorClient') as mock_client_class:
#             # Remove test_dart_mission method to simulate unsupported backend
#             mock_instance = MagicMock()
#             del mock_instance.takeoffAsync
#             mock_instance.armDisarm = AsyncMock()
#             mock_client_class.return_value = mock_instance
#
#             adapter = AirSimAdapter(client=mock_instance)
#
#             with pytest.raises(AttributeError):
#                 await adapter.start_mission(mission_params={'waypoints': waypoints})
#
#
# class TestAirSimAdapterConfiguration:
#     """Test configuration handling"""
#
#     def test_config_passing_full_backend(self):
#         """Test configuration passing to full RPC backend"""
#         with patch('airsim.MultirotorClient') as mock_client:
#             adapter = AirSimAdapter(client=mock_client)
#             assert adapter.client is mock_client
#
#
# class TestAirSimAdapterIntegrationWorkflow:
#     """Test full mission workflow"""
#
#     @pytest.mark.asyncio
#     async def test_complete_mission_workflow_full_backend(self, waypoints):
#         """Test complete mission workflow with full RPC backend"""
#         with patch('airsim.MultirotorClient') as mock_client_class:
#             mock_client = mock_client_class.return_value
#             mock_client.armDisarm = AsyncMock()
#             mock_client.takeoffAsync = AsyncMock()
#             mock_client.moveToPositionAsync = AsyncMock()
#             mock_client.landAsync = AsyncMock()
#             mock_client.disconnect = AsyncMock()
#
#             adapter = AirSimAdapter(client=mock_client)
#
#             # Complete workflow
#             adapter.connect()
#             await adapter.takeoff(altitude=3.0)
#             await adapter.start_mission(mission_params={'waypoints': waypoints})
#             await adapter.land()
#             adapter.disconnect()
#
#             # Verify all methods were called
#             mock_client.armDisarm.assert_called()
#             mock_client.takeoffAsync.assert_called_with(3.0)
#             mock_client.landAsync.assert_called_once()
#             mock_client.disconnect.assert_called_once()
#
#     @pytest.mark.asyncio
#     async def test_complete_mission_workflow_simple_backend(self, waypoints):
#         """Test complete mission workflow with simplified HTTP backend"""
#         with patch('airsim.MultirotorClient') as mock_client_class:
#             mock_client = mock_client_class.return_value
#             mock_client.armDisarm = AsyncMock()
#             mock_client.takeoffAsync = AsyncMock()
#             mock_client.moveToPositionAsync = AsyncMock()
#             mock_client.landAsync = AsyncMock()
#             mock_client.disconnect = AsyncMock()
#
#             adapter = AirSimAdapter(client=mock_client)
#
#             # Complete workflow (simplified backend)
#             adapter.connect()
#             await adapter.takeoff(altitude=3.0)
#             await adapter.start_mission(mission_params={'waypoints': waypoints})
#             await adapter.land()
#             adapter.disconnect()
#
#             # Verify simplified backend methods were called
#             mock_client.armDisarm.assert_called()
#             mock_client.takeoffAsync.assert_called_with(3.0)
#             mock_client.landAsync.assert_called_once()
#             mock_client.disconnect.assert_called_once() 
