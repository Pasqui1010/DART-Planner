"""
Test configuration for DART-Planner professional testing framework.
Consolidated fixtures for improved maintainability and reduced duplication.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

from dart_planner.common.di_container_v2 import DIContainerV2
from dart_planner.common.types import DroneState
from dart_planner.common.units import Q_


@pytest.fixture
def sample_drone_state():
    """Provide a sample drone state for testing."""
    return DroneState(
        timestamp=0.0,
        position=Q_(np.array([0.0, 0.0, 5.0]), 'm'),
        velocity=Q_(np.array([1.0, 0.0, 0.0]), 'm/s'),
        attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
        angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s'),
    )


@pytest.fixture
def sample_drone_states():
    """Provide multiple sample drone states for testing."""
    return [
        DroneState(
            timestamp=i * 0.1,
            position=Q_(np.array([i * 0.1, 0.0, 5.0]), 'm'),
            velocity=Q_(np.array([1.0, 0.0, 0.0]), 'm/s'),
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s'),
        )
        for i in range(10)
    ]


@pytest.fixture
def mock_config():
    """Provide a mock configuration for testing."""
    config = MagicMock()
    config.control_loop_frequency = 100.0
    config.max_velocity = 10.0
    config.max_acceleration = 5.0
    config.safety_timeout = 1.0
    return config


@pytest.fixture
def mock_di_container():
    """Provide a mock DI container for testing."""
    container = MagicMock(spec=DIContainerV2)
    container.get = MagicMock()
    container.register = MagicMock()
    return container


@pytest.fixture
def temp_db_path():
    """Provide a temporary database path for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        return tmp.name


@pytest.fixture
def mock_auth_service():
    """Provide a mock authentication service for testing."""
    auth_service = MagicMock()
    auth_service.authenticate_user = AsyncMock(return_value=True)
    auth_service.create_access_token = MagicMock(return_value="mock_token")
    auth_service.verify_token = MagicMock(return_value={"sub": "test_user"})
    return auth_service


@pytest.fixture
def mock_database():
    """Provide a mock database for testing."""
    db = MagicMock()
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()
    db.execute = AsyncMock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    return db


@pytest.fixture
def test_client():
    """Provide a test client for FastAPI applications."""
    # This will be overridden in specific test files that need it
    return None


@pytest.fixture
def event_loop():
    """Provide an event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def mock_airsim_interface():
    """Provide a mock AirSim interface for testing."""
    interface = MagicMock()
    interface.connect = AsyncMock(return_value=True)
    interface.disconnect = AsyncMock()
    interface.get_drone_state = AsyncMock(return_value=sample_drone_state())
    interface.send_control_command = AsyncMock()
    interface.is_connected = MagicMock(return_value=True)
    return interface


@pytest.fixture
def mock_pixhawk_interface():
    """Provide a mock Pixhawk interface for testing."""
    interface = MagicMock()
    interface.connect = AsyncMock(return_value=True)
    interface.disconnect = AsyncMock()
    interface.get_drone_state = AsyncMock(return_value=sample_drone_state())
    interface.send_control_command = AsyncMock()
    interface.is_connected = MagicMock(return_value=True)
    return interface


@pytest.fixture
def mock_controller():
    """Provide a mock controller for testing."""
    controller = MagicMock()
    controller.compute_control = MagicMock(return_value=np.array([0.1, 0.1, 0.1, 0.1]))
    controller.update_gains = MagicMock()
    controller.reset = MagicMock()
    return controller


@pytest.fixture
def mock_planner():
    """Provide a mock planner for testing."""
    planner = MagicMock()
    planner.plan_trajectory = AsyncMock(return_value=sample_drone_states())
    planner.update_obstacles = MagicMock()
    planner.reset = MagicMock()
    return planner


@pytest.fixture
def mock_heartbeat():
    """Provide a mock heartbeat service for testing."""
    heartbeat = MagicMock()
    heartbeat.start = AsyncMock()
    heartbeat.stop = AsyncMock()
    heartbeat.is_alive = MagicMock(return_value=True)
    heartbeat.get_latency = MagicMock(return_value=0.001)
    return heartbeat


@pytest.fixture
def mock_secure_serializer():
    """Provide a mock secure serializer for testing."""
    serializer = MagicMock()
    serializer.serialize = MagicMock(return_value=b"encrypted_data")
    serializer.deserialize = MagicMock(return_value={"test": "data"})
    serializer.encrypt = MagicMock(return_value=b"encrypted")
    serializer.decrypt = MagicMock(return_value=b"decrypted")
    return serializer


@pytest.fixture
def mock_rate_limiter():
    """Provide a mock rate limiter for testing."""
    limiter = MagicMock()
    limiter.is_allowed = MagicMock(return_value=True)
    limiter.add_request = MagicMock()
    limiter.get_current_rate = MagicMock(return_value=10.0)
    return limiter


@pytest.fixture
def sample_trajectory():
    """Provide a sample trajectory for testing."""
    return [
        {
            "timestamp": i * 0.1,
            "position": [i * 0.1, 0.0, 5.0],
            "velocity": [1.0, 0.0, 0.0],
            "attitude": [0.0, 0.0, 0.0],
            "angular_velocity": [0.0, 0.0, 0.0],
        }
        for i in range(20)
    ]


@pytest.fixture
def mock_file_system():
    """Provide a mock file system for testing."""
    fs = MagicMock()
    fs.exists = MagicMock(return_value=True)
    fs.read_file = MagicMock(return_value="test content")
    fs.write_file = MagicMock()
    fs.delete_file = MagicMock()
    fs.create_directory = MagicMock()
    return fs


@pytest.fixture
def mock_network_interface():
    """Provide a mock network interface for testing."""
    interface = MagicMock()
    interface.send_message = AsyncMock()
    interface.receive_message = AsyncMock(return_value={"type": "test", "data": "test"})
    interface.is_connected = MagicMock(return_value=True)
    interface.connect = AsyncMock(return_value=True)
    interface.disconnect = AsyncMock()
    return interface


@pytest.fixture
def performance_benchmark():
    """Provide a performance benchmark fixture for testing."""
    class PerformanceBenchmark:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.perf_counter()
            
        def stop(self):
            self.end_time = time.perf_counter()
            
        def get_duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
            
        def assert_faster_than(self, threshold_seconds):
            duration = self.get_duration()
            assert duration is not None, "Benchmark not run"
            assert duration < threshold_seconds, f"Performance threshold exceeded: {duration:.6f}s > {threshold_seconds}s"
    
    return PerformanceBenchmark()


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    logger.critical = MagicMock()
    return logger


@pytest.fixture
def sample_error_scenarios():
    """Provide sample error scenarios for testing error handling."""
    return {
        "connection_timeout": Exception("Connection timeout"),
        "invalid_data": ValueError("Invalid data format"),
        "permission_denied": PermissionError("Permission denied"),
        "resource_not_found": FileNotFoundError("Resource not found"),
        "network_error": ConnectionError("Network error"),
    }


@pytest.fixture
def mock_async_context_manager():
    """Provide a mock async context manager for testing."""
    class MockAsyncContextManager:
        def __init__(self, return_value=None):
            self.return_value = return_value
            self.entered = False
            self.exited = False
            
        async def __aenter__(self):
            self.entered = True
            return self.return_value
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.exited = True
            return False  # Don't suppress exceptions
    
    return MockAsyncContextManager


@pytest.fixture
def mock_sensor_data():
    """Provide mock sensor data for testing."""
    return {
        "accelerometer": np.array([0.1, 0.2, 9.8]),
        "gyroscope": np.array([0.01, 0.02, 0.03]),
        "magnetometer": np.array([0.5, 0.6, 0.7]),
        "barometer": 101325.0,  # Standard atmospheric pressure
        "gps": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 100.0,
            "satellites": 8,
        },
        "timestamp": time.time(),
    }


@pytest.fixture
def mock_control_commands():
    """Provide mock control commands for testing."""
    return {
        "throttle": 0.5,
        "roll": 0.1,
        "pitch": 0.1,
        "yaw": 0.0,
        "mode": "MANUAL",
        "timestamp": time.time(),
    }
