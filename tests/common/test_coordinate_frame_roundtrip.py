import numpy as np
import pytest

from dart_planner.common.coordinate_frames import (
    CoordinateFrameManager, CoordinateFrameConfig, WorldFrame
)


@pytest.mark.parametrize("frame", [WorldFrame.ENU, WorldFrame.NED])
def test_random_vector_roundtrip(frame):
    """
    Test that transforming random vectors from ENU->NED->ENU (or NED->ENU->NED) yields the original vector.
    """
    config = CoordinateFrameConfig(world_frame=frame)
    manager = CoordinateFrameManager(config)

    np.random.seed(0)
    # Test 100 random vectors within [-10, 10]
    for _ in range(100):
        vec = np.random.uniform(-10, 10, size=3)
        if frame == WorldFrame.ENU:
            transformed = manager.transform_enu_to_ned(vec)
            round_trip = manager.transform_ned_to_enu(transformed)
        else:
            transformed = manager.transform_ned_to_enu(vec)
            round_trip = manager.transform_enu_to_ned(transformed)
        assert np.allclose(vec, round_trip, atol=1e-6), f"Round-trip failed for vec={vec}"


def test_validate_coordinate_transformation():
    """
    Validate that the validation function detects correct transformations.
    """
    manager = CoordinateFrameManager()
    # ENU->NED
    vec = np.array([1.0, 2.0, 3.0])
    ned = manager.transform_enu_to_ned(vec)
    result = manager.validate_coordinate_transformation(WorldFrame.ENU, WorldFrame.NED, vec, ned)
    assert result.is_valid, f"Expected valid ENU->NED, got errors: {result.errors}"

    # NED->ENU
    vec2 = np.array([4.0, 5.0, -6.0])
    enu = manager.transform_ned_to_enu(vec2)
    result2 = manager.validate_coordinate_transformation(WorldFrame.NED, WorldFrame.ENU, vec2, enu)
    assert result2.is_valid, f"Expected valid NED->ENU, got errors: {result2.errors}"

    # Unsupported transform
    result3 = manager.validate_coordinate_transformation(WorldFrame.ENU, WorldFrame.ENU, vec, vec)
    assert not result3.is_valid, "Expected invalid for same-frame transform" 