"""
Coordinate Frame Utilities for DART-Planner

This module provides consistent coordinate frame handling across the system.
Addresses the critical issue where inconsistent ENU/NED frame assumptions
lead to thrust inversion and incorrect control commands.
"""

import numpy as np
from enum import Enum
from typing import Union, Optional
from dataclasses import dataclass

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


@dataclass
class CoordinateFrameConfig:
    """Configuration for coordinate frame handling."""
    world_frame: WorldFrame = WorldFrame.ENU
    enforce_consistency: bool = True
    validate_transforms: bool = True


class CoordinateFrameManager:
    """
    Manages coordinate frame conversions and ensures consistency.
    
    This class provides:
    1. Gravity vector in the correct frame
    2. Coordinate transformation utilities
    3. Validation of frame-dependent operations
    """
    
    def __init__(self, config: Optional[CoordinateFrameConfig] = None):
        self.config = config or CoordinateFrameConfig()
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate coordinate frame configuration."""
        if not isinstance(self.config.world_frame, WorldFrame):
            raise ConfigurationError(f"Invalid world frame: {self.config.world_frame}")
    
    @property
    def world_frame(self) -> WorldFrame:
        """Get the current world frame convention."""
        return self.config.world_frame
    
    def get_gravity_vector(self, magnitude: float = 9.80665) -> np.ndarray:
        """
        Get gravity vector in the current world frame.
        
        Args:
            magnitude: Gravity magnitude in m/s²
            
        Returns:
            Gravity vector as np.ndarray [x, y, z]
        """
        if self.config.world_frame == WorldFrame.ENU:
            return np.array([0.0, 0.0, -magnitude])  # Down is negative Z
        elif self.config.world_frame == WorldFrame.NED:
            return np.array([0.0, 0.0, magnitude])   # Down is positive Z
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
        
        # ENU [E, N, U] -> NED [N, E, D]
        return np.array([vector[1], vector[0], -vector[2]])
    
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
        
        # NED [N, E, D] -> ENU [E, N, U]
        return np.array([vector[1], vector[0], -vector[2]])
    
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
        
        if not np.allclose(gravity_vector, expected_gravity, atol=1e-3):
            raise ConfigurationError(
                f"Frame inconsistency in {operation_name}: "
                f"Expected gravity {expected_gravity} for {self.config.world_frame.value} frame, "
                f"but got {gravity_vector}"
            )
    
    def get_frame_info(self) -> dict:
        """
        Get information about the current coordinate frame.
        
        Returns:
            Dictionary with frame information
        """
        return {
            'world_frame': self.config.world_frame.value,
            'gravity_vector': self.get_gravity_vector().tolist(),
            'up_vector': self.get_up_vector().tolist(),
            'description': self._get_frame_description()
        }
    
    def _get_frame_description(self) -> str:
        """Get description of the current frame."""
        if self.config.world_frame == WorldFrame.ENU:
            return "East-North-Up: X=East, Y=North, Z=Up, Gravity=[0,0,-9.81]"
        elif self.config.world_frame == WorldFrame.NED:
            return "North-East-Down: X=North, Y=East, Z=Down, Gravity=[0,0,+9.81]"
        else:
            return f"Unknown frame: {self.config.world_frame}"


# Global coordinate frame manager instance
_global_frame_manager: Optional[CoordinateFrameManager] = None


def get_coordinate_frame_manager() -> CoordinateFrameManager:
    """Get the global coordinate frame manager instance."""
    global _global_frame_manager
    if _global_frame_manager is None:
        _global_frame_manager = CoordinateFrameManager()
    return _global_frame_manager


def set_coordinate_frame_manager(manager: CoordinateFrameManager) -> None:
    """Set the global coordinate frame manager instance."""
    global _global_frame_manager
    _global_frame_manager = manager


def get_world_frame() -> WorldFrame:
    """Get the current world frame convention."""
    return get_coordinate_frame_manager().world_frame


def get_gravity_vector(magnitude: float = 9.80665) -> np.ndarray:
    """Get gravity vector in the current world frame."""
    return get_coordinate_frame_manager().get_gravity_vector(magnitude)


def get_up_vector() -> np.ndarray:
    """Get unit vector pointing upward in the current world frame."""
    return get_coordinate_frame_manager().get_up_vector()


def get_altitude_from_position(position: Union[np.ndarray, Quantity]) -> float:
    """Extract altitude from position vector based on current frame."""
    return get_coordinate_frame_manager().get_altitude_from_position(position)


def validate_frame_consistent_operation(operation_name: str, 
                                       gravity_vector: np.ndarray) -> None:
    """Validate that an operation uses gravity consistently with the current frame."""
    get_coordinate_frame_manager().validate_frame_consistent_operation(
        operation_name, gravity_vector
    ) 