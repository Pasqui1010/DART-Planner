"""
Test configuration for DART-Planner professional testing framework.
"""

import pytest
import numpy as np
from src.common.types import DroneState


@pytest.fixture
def sample_drone_state():
    """Provide a sample drone state for testing."""
    return DroneState(
        timestamp=0.0,
        position=np.array([0.0, 0.0, 5.0]),
        velocity=np.array([1.0, 0.0, 0.0]),
        attitude=np.array([0.0, 0.0, 0.0]),
        angular_velocity=np.array([0.0, 0.0, 0.0]),
    )
