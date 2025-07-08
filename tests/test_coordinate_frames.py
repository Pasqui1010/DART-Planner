#!/usr/bin/env python3
# pyright: reportArgumentType=false
"""
Tests for hardened coordinate frame functionality.

This module tests the hardened coordinate frame management system to ensure
consistent handling of ENU/NED coordinate frames across the system with
thread safety and comprehensive validation.
"""

import pytest
import numpy as np
import threading
import time
from unittest.mock import patch, MagicMock
import dataclasses

from dart_planner.common.coordinate_frames import (
    WorldFrame, CoordinateFrameManager, CoordinateFrameConfig,
    FrameConstants, FrameValidationResult, ThreadLocalFrameContext,
    get_coordinate_frame_manager, set_coordinate_frame_manager,
    clear_thread_local_manager, get_gravity_vector, get_up_vector, 
    get_altitude_from_position, validate_frame_consistent_operation,
    validate_coordinate_transformation, validate_gravity_and_axis_signs,
    get_frame_info
)
from dart_planner.common.errors import ConfigurationError
from dart_planner.common.units import Q_


@pytest.fixture(autouse=True)
def reset_global_frame_manager():
    """
    Fixture to reset the global coordinate frame manager before each test.
    This prevents state leakage between tests and ensures a clean environment.
    """
    # Create a fresh default manager (ENU)
    default_manager = CoordinateFrameManager()
    set_coordinate_frame_manager(default_manager, use_thread_local=False)
    
    # Also clear any thread-local manager that might persist
    clear_thread_local_manager()
    
    yield  # Run the test
    
    # Teardown: Clean up after the test by resetting again
    default_manager = CoordinateFrameManager()
    set_coordinate_frame_manager(default_manager, use_thread_local=False)
    clear_thread_local_manager()


class TestFrameConstants:
    """Test FrameConstants read-only dataclass."""
    
    def test_frame_constants_immutability(self):
        """Test that FrameConstants cannot be modified after creation."""
        constants = FrameConstants()
        
        original_gravity = constants.GRAVITY_MAGNITUDE
        original_tolerance = constants.GRAVITY_TOLERANCE
        
        assert original_gravity == 9.80665
        assert original_tolerance == 1e-3
        
        assert dataclasses.is_dataclass(constants)
        assert getattr(constants.__class__, '__dataclass_params__').frozen
    
    def test_frame_constants_validation(self):
        """Test that FrameConstants validates input values."""
        with pytest.raises(ValueError, match="Gravity magnitude must be positive"):
            FrameConstants(GRAVITY_MAGNITUDE=-1.0)
        
        with pytest.raises(ValueError, match="Tolerances must be positive"):
            FrameConstants(GRAVITY_TOLERANCE=-1e-3)
        
        with pytest.raises(ValueError, match="Tolerances must be positive"):
            FrameConstants(VECTOR_TOLERANCE=0.0)
    
    def test_transformation_matrices(self):
        """Test that transformation matrices are correct."""
        constants = FrameConstants()
        
        expected_enu_to_ned = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1]])
        np.testing.assert_array_equal(constants.ENU_TO_NED_MATRIX, expected_enu_to_ned)
        
        expected_ned_to_enu = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1]])
        np.testing.assert_array_equal(constants.NED_TO_ENU_MATRIX, expected_ned_to_enu)


class TestCoordinateFrameConfig:
    """Test CoordinateFrameConfig read-only dataclass."""
    
    def test_config_immutability(self):
        config = CoordinateFrameConfig()
        assert config.world_frame == WorldFrame.ENU
        assert dataclasses.is_dataclass(config)
        assert getattr(config.__class__, '__dataclass_params__').frozen
    
    def test_config_validation(self):
        with pytest.raises(ConfigurationError, match="Invalid world frame"):
            CoordinateFrameConfig(world_frame="INVALID")
    
    def test_default_config(self):
        config = CoordinateFrameConfig()
        assert config.world_frame == WorldFrame.ENU
        assert config.enforce_consistency is True
    
    def test_custom_config(self):
        config = CoordinateFrameConfig(world_frame=WorldFrame.NED, enforce_consistency=False)
        assert config.world_frame == WorldFrame.NED
        assert config.enforce_consistency is False


class TestFrameValidationResult:
    """Test FrameValidationResult read-only dataclass."""
    
    def test_validation_result_immutability(self):
        result = FrameValidationResult(True, ("error1",), ("warning1",))
        assert result.is_valid is True
        assert dataclasses.is_dataclass(result)
        assert getattr(result.__class__, '__dataclass_params__').frozen
    
    def test_validation_result_conversion(self):
        result = FrameValidationResult(True, ["error1"], ["warning1"])
        assert isinstance(result.errors, tuple)
        assert isinstance(result.warnings, tuple)


class TestThreadLocalFrameContext:
    """Test ThreadLocalFrameContext for multi-sim safety."""
    
    def test_thread_local_context_basic(self):
        context = ThreadLocalFrameContext()
        manager = CoordinateFrameManager()
        assert context.get_manager() is None
        context.set_manager(manager)
        assert context.get_manager() is manager
        context.clear_manager()
        assert context.get_manager() is None
    
    def test_thread_local_context_thread_safety(self):
        context = ThreadLocalFrameContext()
        manager1 = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.ENU))
        manager2 = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.NED))
        context.set_manager(manager1)
        
        results = {}
        def thread_function():
            results['id'] = context.get_thread_id()
            context.set_manager(manager2)
            results['manager'] = context.get_manager()
        
        thread = threading.Thread(target=thread_function)
        thread.start()
        thread.join()
        
        assert context.get_manager() is manager1
        assert results['manager'] is manager2
        assert results['id'] != context.get_thread_id()


class TestCoordinateFrameManager:
    """Test CoordinateFrameManager class with hardened features."""
    
    def test_initialization(self):
        manager = CoordinateFrameManager()
        assert manager.world_frame == WorldFrame.ENU
        manager_ned = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.NED))
        assert manager_ned.world_frame == WorldFrame.NED
        
    def test_gravity_vector(self):
        manager_enu = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.ENU))
        np.testing.assert_allclose(manager_enu.get_gravity_vector(), [0, 0, -9.80665])
        manager_ned = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.NED))
        np.testing.assert_allclose(manager_ned.get_gravity_vector(), [0, 0, 9.80665])

    def test_up_vector(self):
        manager_enu = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.ENU))
        np.testing.assert_allclose(manager_enu.get_up_vector(), [0, 0, 1.0])
        manager_ned = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.NED))
        np.testing.assert_allclose(manager_ned.get_up_vector(), [0, 0, -1.0])

    def test_validate_gravity_and_axis_signs_enu(self):
        manager = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.ENU))
        result = manager.validate_gravity_and_axis_signs()
        assert result.is_valid, result.errors

    def test_validate_gravity_and_axis_signs_ned(self):
        manager = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.NED))
        result = manager.validate_gravity_and_axis_signs()
        assert result.is_valid, result.errors

    def test_get_frame_info_comprehensive(self):
        manager = CoordinateFrameManager()
        info = manager.get_frame_info()
        assert info['world_frame'] == 'ENU'
        assert info['validation']['is_valid'] is True


class TestGlobalFunctions:
    """Test global helper functions."""

    def test_get_coordinate_frame_manager_thread_local(self):
        manager = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.NED))
        set_coordinate_frame_manager(manager, use_thread_local=True)
        assert get_coordinate_frame_manager() is manager

    def test_set_coordinate_frame_manager_global(self):
        manager = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.NED))
        set_coordinate_frame_manager(manager, use_thread_local=False)
        assert get_coordinate_frame_manager().world_frame == WorldFrame.NED

    def test_clear_thread_local_manager(self):
        manager = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.NED))
        set_coordinate_frame_manager(manager, use_thread_local=True)
        assert get_coordinate_frame_manager() is manager
        clear_thread_local_manager()
        assert get_coordinate_frame_manager().world_frame == WorldFrame.ENU

    def test_validate_gravity_and_axis_signs_global(self):
        result = validate_gravity_and_axis_signs()
        assert result.is_valid

    def test_get_frame_info_global(self):
        info = get_frame_info()
        assert info['validation']['is_valid'] is True


class TestCoordinateFrameIntegration:
    """Test integration of coordinate frame components."""

    def test_multiple_threads_different_frames(self):
        results = {}
        lock = threading.Lock()

        def worker(frame_type, thread_id):
            config = CoordinateFrameConfig(world_frame=frame_type)
            manager = CoordinateFrameManager(config)
            set_coordinate_frame_manager(manager)
            time.sleep(0.01)
            gravity = get_gravity_vector()
            with lock:
                results[thread_id] = gravity

        thread1 = threading.Thread(target=worker, args=(WorldFrame.ENU, 1))
        thread2 = threading.Thread(target=worker, args=(WorldFrame.NED, 2))
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()
        np.testing.assert_allclose(results[1], [0, 0, -9.80665])
        np.testing.assert_allclose(results[2], [0, 0, 9.80665])

    def test_bidirectional_transformation_identity(self):
        manager = CoordinateFrameManager()
        vector_enu = np.array([10.5, -20.1, 30.2])
        vector_ned = np.array([-5.5, 15.2, -25.8])
        
        transformed_ned = manager.transform_enu_to_ned(vector_enu)
        reverted_enu = manager.transform_ned_to_enu(transformed_ned)
        np.testing.assert_allclose(reverted_enu, vector_enu, atol=1e-9)

        transformed_enu = manager.transform_ned_to_enu(vector_ned)
        reverted_ned = manager.transform_enu_to_ned(transformed_enu)
        np.testing.assert_allclose(reverted_ned, vector_ned, atol=1e-9)

    def test_altitude_reconstruction_consistency(self):
        enu_manager = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.ENU))
        ned_manager = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.NED))
        test_positions = [np.array([1, 2, 5]), np.array([10, -20, -3]), np.array([0,0,0])]

        for pos in test_positions:
            altitude = enu_manager.get_altitude_from_position(pos)
            reconstructed = enu_manager.create_position_from_altitude(pos[0], pos[1], altitude)
            np.testing.assert_allclose(pos, reconstructed, atol=1e-9)

        for pos in test_positions:
            altitude = ned_manager.get_altitude_from_position(pos)
            reconstructed = ned_manager.create_position_from_altitude(pos[0], pos[1], altitude)
            np.testing.assert_allclose(pos, reconstructed, atol=1e-9)


class TestCoordinateFrameEdgeCases:
    """Test edge cases and error handling in coordinate frame utilities."""

    def test_invalid_world_frame_handling(self):
        with pytest.raises(ConfigurationError):
            CoordinateFrameManager(CoordinateFrameConfig(world_frame="invalid"))

    def test_vector_dimension_validation(self):
        manager = CoordinateFrameManager()
        with pytest.raises(ValueError):
            manager.transform_enu_to_ned(np.array([1, 2]))
        with pytest.raises(ValueError):
            manager.transform_ned_to_enu(np.array([1, 2]))

    def test_quantity_handling(self):
        manager_enu = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.ENU))
        position_enu_q = Q_(np.array([1, 2, 10]), 'm')
        assert manager_enu.get_altitude_from_position(position_enu_q) == 10.0

    def test_altitude_with_negative_z(self):
        manager_enu = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.ENU))
        manager_ned = CoordinateFrameManager(CoordinateFrameConfig(world_frame=WorldFrame.NED))

        position_enu_below = np.array([1.0, 2.0, -15.0])
        np.testing.assert_allclose(manager_enu.get_altitude_from_position(position_enu_below), -15.0)

        position_ned_below = np.array([1.0, 2.0, 15.0])
        np.testing.assert_allclose(manager_ned.get_altitude_from_position(position_ned_below), -15.0) 