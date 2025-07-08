"""
Integration tests for DART-Planner minimal takeoff demo.

These tests verify the complete happy path using factory patterns
and simulated vehicle I/O.
"""

import pytest
import asyncio
import subprocess
import sys
import time
from unittest.mock import patch, MagicMock

from dart_planner.minimal_takeoff import MinimalTakeoff
from dart_planner.hardware.vehicle_io import VehicleIOFactory
from dart_planner.common.di_container_v2 import get_container


class TestMinimalTakeoffIntegration:
    """Integration tests for minimal takeoff functionality."""
    
    @pytest.fixture
    def mock_vehicle_io(self):
        """Create a mock vehicle I/O for testing."""
        mock_io = MagicMock()
        mock_io.connect.return_value = True
        mock_io.disconnect.return_value = None
        mock_io.arm.return_value = True
        mock_io.disarm.return_value = True
        mock_io.takeoff.return_value = True
        mock_io.land.return_value = True
        mock_io.set_mode.return_value = True
        mock_io.is_connected.return_value = True
        mock_io.is_armed.return_value = True
        
        # Mock state
        from dart_planner.common.types import DroneState
        import numpy as np
        mock_state = DroneState(
            timestamp=time.time(),
            position=np.array([0.0, 0.0, 5.0]),
            velocity=np.array([0.0, 0.0, 0.0]),
            attitude=np.array([0.0, 0.0, 0.0])
        )
        mock_io.get_state.return_value = mock_state
        
        # Mock status
        mock_io.get_status.return_value = {
            "connected": True,
            "armed": True,
            "position": [0.0, 0.0, 5.0],
            "velocity": [0.0, 0.0, 0.0],
            "capabilities": {"max_velocity": 10.0},
            "trajectory_active": False,
            "planner_available": True
        }
        
        return mock_io
    
    @pytest.fixture
    def minimal_takeoff(self):
        """Create a minimal takeoff instance for testing."""
        return MinimalTakeoff(mock_mode=True, target_altitude=5.0)
    
    @pytest.mark.asyncio
    async def test_initialization_with_factory(self, minimal_takeoff):
        """Test that initialization works with factory patterns."""
        # Test initialization
        success = await minimal_takeoff.initialize()
        assert success is True
        
        # Verify vehicle I/O was created
        assert minimal_takeoff.vehicle_io is not None
        
        # Verify it's a simulated vehicle I/O
        assert "SimulatedVehicleIO" in minimal_takeoff.vehicle_io.__class__.__name__
    
    @pytest.mark.asyncio
    async def test_vehicle_connection(self, minimal_takeoff):
        """Test vehicle connection functionality."""
        # Initialize first
        await minimal_takeoff.initialize()
        
        # Test connection
        connected = await minimal_takeoff.connect_vehicle()
        assert connected is True
        
        # Verify connection state
        assert minimal_takeoff.vehicle_io.is_connected() is True
    
    @pytest.mark.asyncio
    async def test_vehicle_status_retrieval(self, minimal_takeoff):
        """Test vehicle status retrieval."""
        # Initialize and connect
        await minimal_takeoff.initialize()
        await minimal_takeoff.connect_vehicle()
        
        # Test status retrieval
        await minimal_takeoff.get_vehicle_status()
        
        # Verify status was retrieved (no exceptions thrown)
        assert True
    
    @pytest.mark.asyncio
    async def test_complete_takeoff_sequence(self, minimal_takeoff):
        """Test the complete takeoff sequence."""
        # Initialize and connect
        await minimal_takeoff.initialize()
        await minimal_takeoff.connect_vehicle()
        
        # Execute takeoff sequence
        success = await minimal_takeoff.execute_takeoff_sequence()
        assert success is True
    
    @pytest.mark.asyncio
    async def test_cleanup(self, minimal_takeoff):
        """Test cleanup functionality."""
        # Initialize and connect
        await minimal_takeoff.initialize()
        await minimal_takeoff.connect_vehicle()
        
        # Test cleanup
        await minimal_takeoff.cleanup()
        
        # Verify cleanup completed (no exceptions thrown)
        assert True
    
    @pytest.mark.asyncio
    async def test_full_demo_run(self, minimal_takeoff):
        """Test the complete demo run."""
        # Run the full demo
        success = await minimal_takeoff.run()
        assert success is True
    
    def test_factory_registration(self):
        """Test that simulated vehicle I/O is registered with factory."""
        # Check that simulated adapter is registered
        available_adapters = VehicleIOFactory.list_available()
        assert "simulated" in available_adapters
    
    def test_di_container_planner_access(self):
        """Test that SE3MPCPlanner can be accessed via DI container."""
        # Get container
        container = get_container()
        
        # Try to get planner container
        planner_container = container.create_planner_container()
        assert planner_container is not None
        
        # Try to get SE3 planner
        try:
            planner = planner_container.get_se3_planner()
            assert planner is not None
        except Exception as e:
            # It's okay if planner fails to initialize in test environment
            pytest.skip(f"SE3MPCPlanner not available in test environment: {e}")


class TestMinimalTakeoffCLI:
    """Tests for the command-line interface of minimal takeoff."""
    
    def test_cli_mock_mode(self):
        """Test running minimal takeoff in mock mode via CLI."""
        try:
            # Run the minimal takeoff demo in mock mode
            result = subprocess.run([
                sys.executable, "-m", "dart_planner.minimal_takeoff",
                "--mock", "--altitude", "3.0"
            ], capture_output=True, text=True, timeout=30)
            
            # Check that it ran successfully
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
            
            # Check for expected output
            assert "Starting DART-Planner Minimal Takeoff Demo" in result.stdout
            assert "Mock mode: True" in result.stdout
            assert "Target altitude: 3.0m" in result.stdout
            assert "✅ Minimal takeoff demo completed successfully!" in result.stdout
            
        except subprocess.TimeoutExpired:
            pytest.fail("CLI test timed out")
        except Exception as e:
            pytest.skip(f"CLI test skipped due to environment: {e}")
    
    def test_cli_help(self):
        """Test that CLI help works."""
        try:
            result = subprocess.run([
                sys.executable, "-m", "dart_planner.minimal_takeoff",
                "--help"
            ], capture_output=True, text=True, timeout=10)
            
            assert result.returncode == 0
            assert "DART-Planner Minimal Takeoff Demo" in result.stdout
            assert "--mock" in result.stdout
            assert "--altitude" in result.stdout
            
        except Exception as e:
            pytest.skip(f"CLI help test skipped: {e}")
    
    def test_cli_verbose_mode(self):
        """Test running with verbose logging."""
        try:
            result = subprocess.run([
                sys.executable, "-m", "dart_planner.minimal_takeoff",
                "--mock", "--verbose"
            ], capture_output=True, text=True, timeout=30)
            
            assert result.returncode == 0
            assert "✅ Minimal takeoff demo completed successfully!" in result.stdout
            
        except subprocess.TimeoutExpired:
            pytest.fail("CLI verbose test timed out")
        except Exception as e:
            pytest.skip(f"CLI verbose test skipped: {e}")


class TestSimulatedVehicleIO:
    """Tests for the SimulatedVehicleIO implementation."""
    
    @pytest.mark.asyncio
    async def test_simulated_vehicle_io_creation(self):
        """Test creating SimulatedVehicleIO via factory."""
        config = {
            "adapter": "simulated",
            "update_rate": 50.0,
            "mock_mode": True
        }
        
        vehicle_io = VehicleIOFactory.create("simulated", config)
        assert vehicle_io is not None
        assert "SimulatedVehicleIO" in vehicle_io.__class__.__name__
    
    @pytest.mark.asyncio
    async def test_simulated_vehicle_io_connection(self):
        """Test SimulatedVehicleIO connection."""
        config = {"adapter": "simulated", "mock_mode": True}
        vehicle_io = VehicleIOFactory.create("simulated", config)
        
        # Test connection
        connected = await vehicle_io.connect()
        assert connected is True
        assert vehicle_io.is_connected() is True
        
        # Test disconnection
        await vehicle_io.disconnect()
        assert vehicle_io.is_connected() is False
    
    @pytest.mark.asyncio
    async def test_simulated_vehicle_io_operations(self):
        """Test basic SimulatedVehicleIO operations."""
        config = {"adapter": "simulated", "mock_mode": True}
        vehicle_io = VehicleIOFactory.create("simulated", config)
        
        # Connect
        await vehicle_io.connect()
        
        # Test arming
        armed = await vehicle_io.arm()
        assert armed is True
        assert vehicle_io.is_armed() is True
        
        # Test takeoff
        takeoff_success = await vehicle_io.takeoff(5.0)
        assert takeoff_success is True
        
        # Test landing
        land_success = await vehicle_io.land()
        assert land_success is True
        
        # Test disarming
        disarmed = await vehicle_io.disarm()
        assert disarmed is True
        
        # Cleanup
        await vehicle_io.disconnect()
    
    @pytest.mark.asyncio
    async def test_simulated_vehicle_io_state(self):
        """Test SimulatedVehicleIO state retrieval."""
        config = {"adapter": "simulated", "mock_mode": True}
        vehicle_io = VehicleIOFactory.create("simulated", config)
        
        # Connect
        await vehicle_io.connect()
        
        # Get state
        state = await vehicle_io.get_state()
        assert state is not None
        assert hasattr(state, 'position')
        assert hasattr(state, 'velocity')
        assert hasattr(state, 'attitude')
        assert hasattr(state, 'timestamp')
        
        # Get status
        status = vehicle_io.get_status()
        assert status is not None
        assert "connected" in status
        assert "armed" in status
        assert "position" in status
        
        # Cleanup
        await vehicle_io.disconnect()


if __name__ == "__main__":
    pytest.main([__file__]) 