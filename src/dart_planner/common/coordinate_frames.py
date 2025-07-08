"""
Coordinate Frame Utilities for DART-Planner

This module provides consistent coordinate frame handling across the system.
Addresses the critical issue where inconsistent ENU/NED frame assumptions
lead to thrust inversion and incorrect control commands.

HARDENED VERSION:
- Read-only dataclasses for global frame variables
- Thread-local context for multi-sim test safety
- Enhanced validation for gravity and axis signs
- Exhaustive coordinate transformation validation
"""

import numpy as np
from enum import Enum
from typing import Union, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from threading import local
import threading

from dart_planner.common.units import Q_, Quantity
from dart_planner.common.errors import ConfigurationError


class WorldFrame(Enum):
    """
    World coordinate frame convention.
    
    ENU (East-North-Up): 
        - X: East (positive)
        - Y: North (positive) 
        - Z: Up (positive)
        - Gravity: [0, 0, -9.81] m/s²
        
    NED (North-East-Down):
        - X: North (positive)
        - Y: East (positive)
        - Z: Down (positive)
        - Gravity: [0, 0, +9.81] m/s²
    """
    ENU = "ENU"
    NED = "NED"


@dataclass(frozen=True)
class FrameConstants:
    """
    Read-only constants for coordinate frame definitions.
    
    This dataclass ensures frame constants cannot be modified
    after initialization, preventing runtime corruption.
    """
    # Standard gravity magnitude (m/s²)
    GRAVITY_MAGNITUDE: float = 9.80665
    
    # Frame transformation matrices
    ENU_TO_NED_MATRIX: np.ndarray = field(
        default_factory=lambda: np.array([
            [0, 1, 0],   # North = Y
            [1, 0, 0],   # East = X  
            [0, 0, -1]   # Down = -Z
        ])
    )
    
    NED_TO_ENU_MATRIX: np.ndarray = field(
        default_factory=lambda: np.array([
            [0, 1, 0],   # East = Y
            [1, 0, 0],   # North = X
            [0, 0, -1]   # Up = -Z
        ])
    )
    
    # Validation tolerances
    GRAVITY_TOLERANCE: float = 1e-3
    VECTOR_TOLERANCE: float = 1e-6
    
    def __post_init__(self):
        """Validate constants after initialization."""
        if self.GRAVITY_MAGNITUDE <= 0:
            raise ValueError("Gravity magnitude must be positive")
        if self.GRAVITY_TOLERANCE <= 0 or self.VECTOR_TOLERANCE <= 0:
            raise ValueError("Tolerances must be positive")


@dataclass(frozen=True)
class CoordinateFrameConfig:
    """
    Read-only configuration for coordinate frame handling.
    
    This dataclass ensures configuration cannot be modified
    after initialization, preventing runtime corruption.
    """
    world_frame: WorldFrame = WorldFrame.ENU
    enforce_consistency: bool = True
    validate_transforms: bool = True
    enable_thread_safety: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not isinstance(self.world_frame, WorldFrame):
            raise ConfigurationError(f"Invalid world frame: {self.world_frame}")


@dataclass(frozen=True)
class FrameValidationResult:
    """
    Read-only result of coordinate frame validation.
    """
    is_valid: bool
    errors: Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    
    def __post_init__(self):
        """Ensure errors and warnings are tuples."""
        object.__setattr__(self, 'errors', tuple(self.errors))
        object.__setattr__(self, 'warnings', tuple(self.warnings))


class ThreadLocalFrameContext:
    """
    Thread-local context for coordinate frame management.
    
    This ensures that each thread can have its own coordinate frame
    configuration without interfering with other threads, which is
    critical for multi-simulation testing scenarios.
    """
    
    def __init__(self):
        self._thread_local = local()
        self._lock = threading.RLock()
    
    def get_manager(self) -> Optional['CoordinateFrameManager']:
        """Get the coordinate frame manager for the current thread."""
        return getattr(self._thread_local, 'manager', None)
    
    def set_manager(self, manager: 'CoordinateFrameManager') -> None:
        """Set the coordinate frame manager for the current thread."""
        with self._lock:
            self._thread_local.manager = manager
    
    def clear_manager(self) -> None:
        """Clear the coordinate frame manager for the current thread."""
        with self._lock:
            if hasattr(self._thread_local, 'manager'):
                delattr(self._thread_local, 'manager')
    
    def get_thread_id(self) -> int:
        """Get the current thread ID for debugging."""
        return threading.get_ident()


class CoordinateFrameManager:
    """
    Manages coordinate frame conversions and ensures consistency.
    
    This class provides:
    1. Gravity vector in the correct frame
    2. Coordinate transformation utilities
    3. Validation of frame-dependent operations
    4. Thread-safe operation for multi-sim scenarios
    """
    
    def __init__(self, config: Optional[CoordinateFrameConfig] = None):
        self.config = config or CoordinateFrameConfig()
        self._constants = FrameConstants()
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate coordinate frame configuration."""
        if not isinstance(self.config.world_frame, WorldFrame):
            raise ConfigurationError(f"Invalid world frame: {self.config.world_frame}")
    
    @property
    def world_frame(self) -> WorldFrame:
        """Get the current world frame convention."""
        return self.config.world_frame
    
    @property
    def constants(self) -> FrameConstants:
        """Get read-only frame constants."""
        return self._constants
    
    def get_gravity_vector(self, magnitude: Optional[float] = None) -> np.ndarray:
        """
        Get gravity vector in the current world frame.
        
        Args:
            magnitude: Gravity magnitude in m/s² (uses standard if None)
            
        Returns:
            Gravity vector as np.ndarray [x, y, z]
        """
        mag = magnitude if magnitude is not None else self._constants.GRAVITY_MAGNITUDE
        
        if self.config.world_frame == WorldFrame.ENU:
            return np.array([0.0, 0.0, -mag])  # Down is negative Z
        elif self.config.world_frame == WorldFrame.NED:
            return np.array([0.0, 0.0, mag])   # Down is positive Z
        else:
            raise ConfigurationError(f"Unsupported world frame: {self.config.world_frame}")
    
    def get_up_vector(self) -> np.ndarray:
        """
        Get unit vector pointing upward in the current world frame.
        
        Returns:
            Unit vector pointing up [x, y, z]
        """
        if self.config.world_frame == WorldFrame.ENU:
            return np.array([0.0, 0.0, 1.0])   # Up is positive Z
        elif self.config.world_frame == WorldFrame.NED:
            return np.array([0.0, 0.0, -1.0])  # Up is negative Z
        else:
            raise ConfigurationError(f"Unsupported world frame: {self.config.world_frame}")
    
    def get_altitude_from_position(self, position: Union[np.ndarray, Quantity]) -> float:
        """
        Extract altitude from position vector based on current frame.
        
        Args:
            position: Position vector [x, y, z] in meters
            
        Returns:
            Altitude in meters (positive = above ground)
        """
        if isinstance(position, Quantity):
            pos_array = position.to('m').magnitude
        else:
            pos_array = position
        
        # Return signed altitude (distance above ground, can be negative)
        if self.config.world_frame == WorldFrame.ENU:
            return float(pos_array[2])      # Z is altitude
        elif self.config.world_frame == WorldFrame.NED:
            return float(-pos_array[2])     # -Z is altitude
        else:
            raise ConfigurationError(f"Unsupported world frame: {self.config.world_frame}")
    
    def create_position_from_altitude(self, x: float, y: float, altitude: float) -> np.ndarray:
        """
        Create position vector from x, y, and altitude.
        
        Args:
            x: X coordinate (East in ENU, North in NED)
            y: Y coordinate (North in ENU, East in NED)
            altitude: Altitude above ground (positive = up)
            
        Returns:
            Position vector [x, y, z] in current frame
        """
        if self.config.world_frame == WorldFrame.ENU:
            return np.array([x, y, altitude])     # Z = altitude
        elif self.config.world_frame == WorldFrame.NED:
            return np.array([x, y, -altitude])    # Z = -altitude
        else:
            raise ConfigurationError(f"Unsupported world frame: {self.config.world_frame}")
    
    def transform_enu_to_ned(self, vector: np.ndarray) -> np.ndarray:
        """
        Transform vector from ENU to NED frame.
        
        ENU [E, N, U] -> NED [N, E, D]
        
        Args:
            vector: Vector in ENU frame [East, North, Up]
            
        Returns:
            Vector in NED frame [North, East, Down]
        """
        if len(vector) != 3:
            raise ValueError("Vector must have 3 components")
        
        # Use matrix multiplication for consistency
        return self._constants.ENU_TO_NED_MATRIX @ vector
    
    def transform_ned_to_enu(self, vector: np.ndarray) -> np.ndarray:
        """
        Transform vector from NED to ENU frame.
        
        NED [N, E, D] -> ENU [E, N, U]
        
        Args:
            vector: Vector in NED frame [North, East, Down]
            
        Returns:
            Vector in ENU frame [East, North, Up]
        """
        if len(vector) != 3:
            raise ValueError("Vector must have 3 components")
        
        # Use matrix multiplication for consistency
        return self._constants.NED_TO_ENU_MATRIX @ vector
    
    def validate_frame_consistent_operation(self, operation_name: str, 
                                          gravity_vector: np.ndarray) -> None:
        """
        Validate that an operation uses gravity consistently with the current frame.
        
        Args:
            operation_name: Name of the operation being validated
            gravity_vector: The gravity vector being used
            
        Raises:
            ConfigurationError: If gravity vector is inconsistent with current frame
        """
        if not self.config.enforce_consistency:
            return
        
        expected_gravity = self.get_gravity_vector()
        
        if not np.allclose(gravity_vector, expected_gravity, 
                          atol=self._constants.GRAVITY_TOLERANCE):
            raise ConfigurationError(
                f"Frame inconsistency in {operation_name}: "
                f"Expected gravity {expected_gravity} for {self.config.world_frame.value} frame, "
                f"but got {gravity_vector}"
            )
    
    def validate_coordinate_transformation(self, 
                                         source_frame: WorldFrame,
                                         target_frame: WorldFrame,
                                         vector: np.ndarray,
                                         transformed_vector: np.ndarray) -> FrameValidationResult:
        """
        Validate coordinate transformation for correctness.
        
        Args:
            source_frame: Source coordinate frame
            target_frame: Target coordinate frame
            vector: Original vector
            transformed_vector: Transformed vector
            
        Returns:
            FrameValidationResult with validation status
        """
        errors = []
        warnings = []
        
        # Check vector dimensions
        if len(vector) != 3 or len(transformed_vector) != 3:
            errors.append("Vectors must have exactly 3 components")
            return FrameValidationResult(False, tuple(errors), tuple(warnings))
        
        # Validate transformation based on frame pair
        if source_frame == WorldFrame.ENU and target_frame == WorldFrame.NED:
            expected = self.transform_enu_to_ned(vector)
        elif source_frame == WorldFrame.NED and target_frame == WorldFrame.ENU:
            expected = self.transform_ned_to_enu(vector)
        else:
            errors.append(f"Unsupported transformation: {source_frame.value} -> {target_frame.value}")
            return FrameValidationResult(False, tuple(errors), tuple(warnings))
        
        # Check transformation accuracy
        if not np.allclose(transformed_vector, expected, 
                          atol=self._constants.VECTOR_TOLERANCE):
            errors.append(
                f"Transformation mismatch: expected {expected}, got {transformed_vector}"
            )
        
        # Check round-trip consistency
        if source_frame != target_frame:
            round_trip = self.transform_ned_to_enu(
                self.transform_enu_to_ned(vector)
            ) if source_frame == WorldFrame.ENU else self.transform_enu_to_ned(
                self.transform_ned_to_enu(vector)
            )
            
            if not np.allclose(vector, round_trip, atol=self._constants.VECTOR_TOLERANCE):
                warnings.append("Round-trip transformation not identity")
        
        is_valid = len(errors) == 0
        return FrameValidationResult(is_valid, tuple(errors), tuple(warnings))
    
    def validate_gravity_and_axis_signs(self) -> FrameValidationResult:
        """
        Comprehensive validation of gravity and axis signs across conversions.
        
        Returns:
            FrameValidationResult with validation status
        """
        errors = []
        warnings = []
        
        # Test gravity vectors
        enu_gravity = np.array([0.0, 0.0, -self._constants.GRAVITY_MAGNITUDE])
        ned_gravity = np.array([0.0, 0.0, self._constants.GRAVITY_MAGNITUDE])
        
        # Test ENU frame gravity
        if self.config.world_frame == WorldFrame.ENU:
            actual_gravity = self.get_gravity_vector()
            if not np.allclose(actual_gravity, enu_gravity, 
                              atol=self._constants.GRAVITY_TOLERANCE):
                errors.append(f"ENU gravity mismatch: expected {enu_gravity}, got {actual_gravity}")
        
        # Test NED frame gravity
        if self.config.world_frame == WorldFrame.NED:
            actual_gravity = self.get_gravity_vector()
            if not np.allclose(actual_gravity, ned_gravity, 
                              atol=self._constants.GRAVITY_TOLERANCE):
                errors.append(f"NED gravity mismatch: expected {ned_gravity}, got {actual_gravity}")
        
        # Test up vectors
        enu_up = np.array([0.0, 0.0, 1.0])
        ned_up = np.array([0.0, 0.0, -1.0])
        
        if self.config.world_frame == WorldFrame.ENU:
            actual_up = self.get_up_vector()
            if not np.allclose(actual_up, enu_up, atol=self._constants.VECTOR_TOLERANCE):
                errors.append(f"ENU up vector mismatch: expected {enu_up}, got {actual_up}")
        
        if self.config.world_frame == WorldFrame.NED:
            actual_up = self.get_up_vector()
            if not np.allclose(actual_up, ned_up, atol=self._constants.VECTOR_TOLERANCE):
                errors.append(f"NED up vector mismatch: expected {ned_up}, got {actual_up}")
        
        # Test altitude extraction consistency
        test_positions = [
            np.array([1.0, 2.0, 5.0]),   # Positive altitude
            np.array([1.0, 2.0, -3.0]),  # Negative altitude
            np.array([0.0, 0.0, 0.0])    # Zero altitude
        ]
        
        for pos in test_positions:
            altitude = self.get_altitude_from_position(pos)
            reconstructed = self.create_position_from_altitude(pos[0], pos[1], altitude)
            
            # Check that altitude extraction and reconstruction are consistent
            # Altitude is a SIGNED value (height above origin)
            expected_altitude = pos[2] if self.config.world_frame == WorldFrame.ENU else -pos[2]
            
            if abs(altitude - expected_altitude) > self._constants.VECTOR_TOLERANCE:
                errors.append(f"Altitude inconsistency: pos={pos}, altitude={altitude}, expected={expected_altitude}")
            
            # Check reconstruction
            if not np.allclose(pos, reconstructed, atol=self._constants.VECTOR_TOLERANCE):
                errors.append(f"Position reconstruction mismatch: {pos} -> {reconstructed}")
        
        is_valid = len(errors) == 0
        return FrameValidationResult(is_valid, tuple(errors), tuple(warnings))
    
    def get_frame_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the current coordinate frame.
        
        Returns:
            Dictionary with frame information including validation results
        """
        validation_result = self.validate_gravity_and_axis_signs()
        
        return {
            'world_frame': self.config.world_frame.value,
            'gravity_vector': self.get_gravity_vector().tolist(),
            'up_vector': self.get_up_vector().tolist(),
            'description': self._get_frame_description(),
            'validation': {
                'is_valid': validation_result.is_valid,
                'errors': validation_result.errors,
                'warnings': validation_result.warnings
            },
            'constants': {
                'gravity_magnitude': self._constants.GRAVITY_MAGNITUDE,
                'gravity_tolerance': self._constants.GRAVITY_TOLERANCE,
                'vector_tolerance': self._constants.VECTOR_TOLERANCE
            }
        }
    
    def _get_frame_description(self) -> str:
        """Get description of the current frame."""
        if self.config.world_frame == WorldFrame.ENU:
            return "East-North-Up: X=East, Y=North, Z=Up, Gravity=[0,0,-9.81]"
        elif self.config.world_frame == WorldFrame.NED:
            return "North-East-Down: X=North, Y=East, Z=Down, Gravity=[0,0,+9.81]"
        else:
            return f"Unknown frame: {self.config.world_frame}"


# Thread-local context for multi-sim safety
_thread_local_context = ThreadLocalFrameContext()

# Global coordinate frame manager instance (fallback)
_global_frame_manager: Optional[CoordinateFrameManager] = None


def get_coordinate_frame_manager() -> CoordinateFrameManager:
    """
    Get the coordinate frame manager instance.
    
    Returns thread-local manager if available, otherwise global manager.
    """
    # Try thread-local first
    thread_manager = _thread_local_context.get_manager()
    if thread_manager is not None:
        return thread_manager
    
    # Fallback to global
    global _global_frame_manager
    if _global_frame_manager is None:
        _global_frame_manager = CoordinateFrameManager()
    return _global_frame_manager


def set_coordinate_frame_manager(manager: CoordinateFrameManager, 
                                use_thread_local: bool = True) -> None:
    """
    Set the coordinate frame manager instance.
    
    Args:
        manager: The coordinate frame manager to set
        use_thread_local: If True, set thread-local; otherwise set global
    """
    if use_thread_local and manager.config.enable_thread_safety:
        _thread_local_context.set_manager(manager)
    else:
        global _global_frame_manager
        _global_frame_manager = manager


def clear_thread_local_manager() -> None:
    """Clear the thread-local coordinate frame manager."""
    _thread_local_context.clear_manager()


# Global helper functions for convenience
def get_gravity_vector(magnitude: Optional[float] = None) -> np.ndarray:
    """
    Get gravity vector using the current thread's coordinate frame manager.
    
    Args:
        magnitude: Gravity magnitude in m/s² (uses standard if None)
        
    Returns:
        Gravity vector as np.ndarray [x, y, z]
    """
    manager = get_coordinate_frame_manager()
    return manager.get_gravity_vector(magnitude)


def get_up_vector() -> np.ndarray:
    """
    Get unit vector pointing upward using the current thread's coordinate frame manager.
    
    Returns:
        Unit vector pointing up [x, y, z]
    """
    manager = get_coordinate_frame_manager()
    return manager.get_up_vector()


def get_altitude_from_position(position: Union[np.ndarray, Quantity]) -> float:
    """
    Extract altitude from position vector using the current thread's coordinate frame manager.
    
    Args:
        position: Position vector [x, y, z] in meters
        
    Returns:
        Altitude in meters (positive = above ground)
    """
    manager = get_coordinate_frame_manager()
    return manager.get_altitude_from_position(position)


def validate_gravity_and_axis_signs() -> FrameValidationResult:
    """
    Validate gravity and axis signs using the current thread's coordinate frame manager.
    
    Returns:
        FrameValidationResult with validation status
    """
    manager = get_coordinate_frame_manager()
    return manager.validate_gravity_and_axis_signs()


def get_frame_info() -> Dict[str, Any]:
    """
    Get comprehensive frame information using the current thread's coordinate frame manager.
    
    Returns:
        Dictionary with frame information including validation results
    """
    manager = get_coordinate_frame_manager()
    return manager.get_frame_info()


def validate_coordinate_transformation(source_frame: WorldFrame,
                                     target_frame: WorldFrame,
                                     vector: np.ndarray,
                                     transformed_vector: np.ndarray) -> FrameValidationResult:
    """
    Validate coordinate transformation using the current thread's coordinate frame manager.
    
    Args:
        source_frame: Source coordinate frame
        target_frame: Target coordinate frame
        vector: Original vector
        transformed_vector: Transformed vector
        
    Returns:
        FrameValidationResult with validation status
    """
    manager = get_coordinate_frame_manager()
    return manager.validate_coordinate_transformation(source_frame, target_frame, vector, transformed_vector)


def validate_frame_consistent_operation(operation_name: str, gravity_vector: np.ndarray) -> None:
    """
    Validate that an operation uses gravity consistently with the current frame.
    
    Args:
        operation_name: Name of the operation being validated
        gravity_vector: The gravity vector being used
        
    Raises:
        ConfigurationError: If gravity vector is inconsistent with current frame
    """
    manager = get_coordinate_frame_manager()
    manager.validate_frame_consistent_operation(operation_name, gravity_vector) 