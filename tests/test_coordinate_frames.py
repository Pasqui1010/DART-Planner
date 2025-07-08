"""
Tests for coordinate frame functionality.

This module tests the coordinate frame management system to ensure
consistent handling of ENU/NED coordinate frames across the system.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from dart_planner.common.coordinate_frames import (
    WorldFrame, CoordinateFrameManager, CoordinateFrameConfig,
    get_coordinate_frame_manager, set_coordinate_frame_manager,
    get_gravity_vector, get_up_vector, get_altitude_from_position,
    validate_frame_consistent_operation
)
from dart_planner.common.errors import ConfigurationError
from dart_planner.common.units import Q_


class TestWorldFrame:
    """Test WorldFrame enum."""
    
    def test_world_frame_values(self):
        """Test that WorldFrame enum has correct values."""
        assert WorldFrame.ENU.value == "ENU"
        assert WorldFrame.NED.value == "NED"
    
    def test_world_frame_string_conversion(self):
        """Test conversion from string to WorldFrame."""
        assert WorldFrame("ENU") == WorldFrame.ENU
        assert WorldFrame("NED") == WorldFrame.NED
        
        with pytest.raises(ValueError):
            WorldFrame("INVALID")


class TestCoordinateFrameConfig:
    """Test CoordinateFrameConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CoordinateFrameConfig()
        assert config.world_frame == WorldFrame.ENU
        assert config.enforce_consistency is True
        assert config.validate_transforms is True
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = CoordinateFrameConfig(
            world_frame=WorldFrame.NED,
            enforce_consistency=False,
            validate_transforms=False
        )
        assert config.world_frame == WorldFrame.NED
        assert config.enforce_consistency is False
        assert config.validate_transforms is False


class TestCoordinateFrameManager:
    """Test CoordinateFrameManager class."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        manager = CoordinateFrameManager()
        assert manager.world_frame == WorldFrame.ENU
    
    def test_initialization_custom(self):
        """Test custom initialization."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.NED)
        manager = CoordinateFrameManager(config)
        assert manager.world_frame == WorldFrame.NED
    
    def test_unsupported_frame_raises_error(self):
        """Test that unsupported frame raises ConfigurationError in gravity calculation."""
        # Test that using an unsupported frame in gravity calculation raises error
        config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
        manager = CoordinateFrameManager(config)
        
        # Mock the world_frame to be unsupported
        manager.config.world_frame = "UNSUPPORTED"  # type: ignore
        
        with pytest.raises(ConfigurationError, match="Unsupported world frame"):
            manager.get_gravity_vector()
    
    def test_gravity_vector_enu(self):
        """Test gravity vector in ENU frame."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
        manager = CoordinateFrameManager(config)
        
        gravity = manager.get_gravity_vector()
        expected = np.array([0.0, 0.0, -9.80665])
        np.testing.assert_array_almost_equal(gravity, expected)
    
    def test_gravity_vector_ned(self):
        """Test gravity vector in NED frame."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.NED)
        manager = CoordinateFrameManager(config)
        
        gravity = manager.get_gravity_vector()
        expected = np.array([0.0, 0.0, 9.80665])
        np.testing.assert_array_almost_equal(gravity, expected)
    
    def test_gravity_vector_custom_magnitude(self):
        """Test gravity vector with custom magnitude."""
        manager = CoordinateFrameManager()
        
        gravity = manager.get_gravity_vector(magnitude=10.0)
        expected = np.array([0.0, 0.0, -10.0])
        np.testing.assert_array_almost_equal(gravity, expected)
    
    def test_up_vector_enu(self):
        """Test up vector in ENU frame."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
        manager = CoordinateFrameManager(config)
        
        up = manager.get_up_vector()
        expected = np.array([0.0, 0.0, 1.0])
        np.testing.assert_array_almost_equal(up, expected)
    
    def test_up_vector_ned(self):
        """Test up vector in NED frame."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.NED)
        manager = CoordinateFrameManager(config)
        
        up = manager.get_up_vector()
        expected = np.array([0.0, 0.0, -1.0])
        np.testing.assert_array_almost_equal(up, expected)
    
    def test_altitude_from_position_enu(self):
        """Test altitude extraction in ENU frame."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
        manager = CoordinateFrameManager(config)
        
        position = np.array([1.0, 2.0, 5.0])
        altitude = manager.get_altitude_from_position(position)
        assert altitude == 5.0
    
    def test_altitude_from_position_ned(self):
        """Test altitude extraction in NED frame."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.NED)
        manager = CoordinateFrameManager(config)
        
        position = np.array([1.0, 2.0, -5.0])
        altitude = manager.get_altitude_from_position(position)
        assert altitude == 5.0
    
    def test_altitude_from_position_with_quantity(self):
        """Test altitude extraction with Quantity input."""
        manager = CoordinateFrameManager()
        
        position = Q_(np.array([1.0, 2.0, 5.0]), 'm')
        altitude = manager.get_altitude_from_position(position)
        assert altitude == 5.0
    
    def test_create_position_from_altitude_enu(self):
        """Test position creation from altitude in ENU frame."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
        manager = CoordinateFrameManager(config)
        
        position = manager.create_position_from_altitude(1.0, 2.0, 5.0)
        expected = np.array([1.0, 2.0, 5.0])
        np.testing.assert_array_almost_equal(position, expected)
    
    def test_create_position_from_altitude_ned(self):
        """Test position creation from altitude in NED frame."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.NED)
        manager = CoordinateFrameManager(config)
        
        position = manager.create_position_from_altitude(1.0, 2.0, 5.0)
        expected = np.array([1.0, 2.0, -5.0])
        np.testing.assert_array_almost_equal(position, expected)
    
    def test_transform_enu_to_ned(self):
        """Test ENU to NED transformation."""
        manager = CoordinateFrameManager()
        
        enu_vector = np.array([1.0, 2.0, 3.0])  # East, North, Up
        ned_vector = manager.transform_enu_to_ned(enu_vector)
        expected = np.array([2.0, 1.0, -3.0])  # North, East, Down
        np.testing.assert_array_almost_equal(ned_vector, expected)
    
    def test_transform_ned_to_enu(self):
        """Test NED to ENU transformation."""
        manager = CoordinateFrameManager()
        
        ned_vector = np.array([1.0, 2.0, 3.0])  # North, East, Down
        enu_vector = manager.transform_ned_to_enu(ned_vector)
        expected = np.array([2.0, 1.0, -3.0])  # East, North, Up
        np.testing.assert_array_almost_equal(enu_vector, expected)
    
    def test_transform_roundtrip(self):
        """Test that ENU->NED->ENU transformation is identity."""
        manager = CoordinateFrameManager()
        
        original = np.array([1.0, 2.0, 3.0])
        transformed = manager.transform_ned_to_enu(
            manager.transform_enu_to_ned(original)
        )
        np.testing.assert_array_almost_equal(original, transformed)
    
    def test_validate_frame_consistent_operation_pass(self):
        """Test frame consistency validation passes with correct gravity."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
        manager = CoordinateFrameManager(config)
        
        correct_gravity = np.array([0.0, 0.0, -9.80665])
        # Should not raise an exception
        manager.validate_frame_consistent_operation("test_operation", correct_gravity)
    
    def test_validate_frame_consistent_operation_fail(self):
        """Test frame consistency validation fails with incorrect gravity."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
        manager = CoordinateFrameManager(config)
        
        incorrect_gravity = np.array([0.0, 0.0, 9.80665])  # Wrong sign for ENU
        with pytest.raises(ConfigurationError):
            manager.validate_frame_consistent_operation("test_operation", incorrect_gravity)
    
    def test_validate_frame_consistent_operation_disabled(self):
        """Test frame consistency validation disabled."""
        config = CoordinateFrameConfig(
            world_frame=WorldFrame.ENU,
            enforce_consistency=False
        )
        manager = CoordinateFrameManager(config)
        
        incorrect_gravity = np.array([0.0, 0.0, 9.80665])  # Wrong sign for ENU
        # Should not raise an exception when validation is disabled
        manager.validate_frame_consistent_operation("test_operation", incorrect_gravity)
    
    def test_get_frame_info(self):
        """Test frame information retrieval."""
        config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
        manager = CoordinateFrameManager(config)
        
        info = manager.get_frame_info()
        assert info['world_frame'] == 'ENU'
        assert info['gravity_vector'] == [0.0, 0.0, -9.80665]
        assert info['up_vector'] == [0.0, 0.0, 1.0]
        assert 'East-North-Up' in info['description']


class TestGlobalFunctions:
    """Test global coordinate frame functions."""
    
    def test_get_coordinate_frame_manager(self):
        """Test global coordinate frame manager retrieval."""
        manager = get_coordinate_frame_manager()
        assert isinstance(manager, CoordinateFrameManager)
    
    def test_set_coordinate_frame_manager(self):
        """Test global coordinate frame manager setting."""
        original_manager = get_coordinate_frame_manager()
        
        new_config = CoordinateFrameConfig(world_frame=WorldFrame.NED)
        new_manager = CoordinateFrameManager(new_config)
        
        set_coordinate_frame_manager(new_manager)
        
        # Check that the global manager was updated
        current_manager = get_coordinate_frame_manager()
        assert current_manager.world_frame == WorldFrame.NED
        
        # Restore original manager
        set_coordinate_frame_manager(original_manager)
    
    def test_get_gravity_vector_global(self):
        """Test global gravity vector function."""
        gravity = get_gravity_vector()
        assert isinstance(gravity, np.ndarray)
        assert len(gravity) == 3
    
    def test_get_up_vector_global(self):
        """Test global up vector function."""
        up = get_up_vector()
        assert isinstance(up, np.ndarray)
        assert len(up) == 3
    
    def test_get_altitude_from_position_global(self):
        """Test global altitude extraction function."""
        position = np.array([1.0, 2.0, 5.0])
        altitude = get_altitude_from_position(position)
        assert isinstance(altitude, float)
    
    def test_validate_frame_consistent_operation_global(self):
        """Test global frame consistency validation function."""
        correct_gravity = get_gravity_vector()
        # Should not raise an exception
        validate_frame_consistent_operation("test_operation", correct_gravity)


class TestCoordinateFrameIntegration:
    """Integration tests for coordinate frame system."""
    
    def test_different_frames_different_gravity(self):
        """Test that different frames produce different gravity vectors."""
        enu_config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
        ned_config = CoordinateFrameConfig(world_frame=WorldFrame.NED)
        
        enu_manager = CoordinateFrameManager(enu_config)
        ned_manager = CoordinateFrameManager(ned_config)
        
        enu_gravity = enu_manager.get_gravity_vector()
        ned_gravity = ned_manager.get_gravity_vector()
        
        # Should have opposite signs for Z component
        assert enu_gravity[2] < 0
        assert ned_gravity[2] > 0
        assert abs(enu_gravity[2]) == abs(ned_gravity[2])
    
    def test_altitude_consistency_across_frames(self):
        """Test that altitude calculation is consistent across frames."""
        enu_config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
        ned_config = CoordinateFrameConfig(world_frame=WorldFrame.NED)
        
        enu_manager = CoordinateFrameManager(enu_config)
        ned_manager = CoordinateFrameManager(ned_config)
        
        altitude = 10.0
        
        # Create positions in each frame
        enu_position = enu_manager.create_position_from_altitude(0, 0, altitude)
        ned_position = ned_manager.create_position_from_altitude(0, 0, altitude)
        
        # Extract altitude back
        enu_altitude = enu_manager.get_altitude_from_position(enu_position)
        ned_altitude = ned_manager.get_altitude_from_position(ned_position)
        
        # Should get the same altitude back
        assert abs(enu_altitude - altitude) < 1e-10
        assert abs(ned_altitude - altitude) < 1e-10
    
    def test_coordinate_transformation_consistency(self):
        """Test that coordinate transformations are consistent."""
        manager = CoordinateFrameManager()
        
        # Test vector
        test_vector = np.array([1.0, 2.0, 3.0])
        
        # Transform ENU->NED->ENU should be identity
        ned_vector = manager.transform_enu_to_ned(test_vector)
        enu_vector = manager.transform_ned_to_enu(ned_vector)
        
        np.testing.assert_array_almost_equal(test_vector, enu_vector)
        
        # Transform NED->ENU->NED should be identity
        enu_vector = manager.transform_ned_to_enu(test_vector)
        ned_vector = manager.transform_enu_to_ned(enu_vector)
        
        np.testing.assert_array_almost_equal(test_vector, ned_vector) 