"""
Vehicle I/O Interface for DART-Planner

This module provides a unified interface for vehicle communication,
abstracting the differences between real hardware (Pixhawk) and simulation (AirSim).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
import asyncio
import logging
import time
import numpy as np

from ..common.types import DroneState, Trajectory


class VehicleIO(ABC):
    """
    Abstract base class for vehicle I/O operations.
    
    This provides a unified interface for:
    - Real hardware (Pixhawk via MAVLink)
    - Simulation (AirSim)
    - Software-in-the-loop (SITL)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize vehicle I/O with configuration."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.connected = False
        self.last_state: Optional[DroneState] = None
        self.last_heartbeat = time.time()
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to vehicle."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from vehicle."""
        pass
    
    @abstractmethod
    async def get_state(self) -> Optional[DroneState]:
        """Get current vehicle state."""
        pass
    
    @abstractmethod
    async def send_trajectory(self, trajectory: Trajectory) -> bool:
        """Send trajectory to vehicle for execution."""
        pass
    
    @abstractmethod
    async def send_control_command(self, command: Dict[str, Any]) -> bool:
        """Send direct control command to vehicle."""
        pass
    
    @abstractmethod
    async def arm(self) -> bool:
        """Arm the vehicle."""
        pass
    
    @abstractmethod
    async def disarm(self) -> bool:
        """Disarm the vehicle."""
        pass
    
    @abstractmethod
    async def takeoff(self, target_altitude: float) -> bool:
        """Execute takeoff to target altitude."""
        pass
    
    @abstractmethod
    async def land(self) -> bool:
        """Execute landing."""
        pass
    
    @abstractmethod
    async def set_mode(self, mode: str) -> bool:
        """Set vehicle flight mode."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get vehicle status information."""
        pass
    
    @abstractmethod
    async def emergency_stop(self) -> bool:
        """Execute emergency stop procedure."""
        pass
    
    def is_connected(self) -> bool:
        """Check if connected to vehicle."""
        return self.connected
    
    def is_armed(self) -> bool:
        """Check if vehicle is armed."""
        # This should be implemented by concrete classes based on their specific state
        return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            "connected": self.connected,
            "last_heartbeat": self.last_heartbeat,
            "time_since_heartbeat": time.time() - self.last_heartbeat,
        }


class VehicleIOFactory:
    """Factory for creating vehicle I/O instances."""
    
    _adapters = {}
    
    @classmethod
    def register(cls, name: str, adapter_class: type):
        """Register a vehicle I/O adapter class."""
        cls._adapters[name] = adapter_class
    
    @classmethod
    def create(cls, name: str, config: Dict[str, Any]) -> VehicleIO:
        """Create a vehicle I/O instance by name."""
        if name not in cls._adapters:
            raise ValueError(f"Unknown vehicle I/O adapter: {name}. Available: {list(cls._adapters.keys())}")
        
        return cls._adapters[name](config)
    
    @classmethod
    def list_available(cls) -> List[str]:
        """List all available vehicle I/O adapters."""
        return list(cls._adapters.keys())


class VehicleIOAdapter:
    """
    Base adapter class that provides common functionality
    for vehicle I/O implementations.
    """
    
    def __init__(self, vehicle_io: VehicleIO):
        self.vehicle_io = vehicle_io
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def safe_connect(self) -> bool:
        """Safely connect with error handling."""
        try:
            return await self.vehicle_io.connect()
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False
    
    async def safe_get_state(self) -> Optional[DroneState]:
        """Safely get state with error handling."""
        try:
            return await self.vehicle_io.get_state()
        except Exception as e:
            self.logger.error(f"Failed to get state: {e}")
            return None
    
    async def safe_send_trajectory(self, trajectory: Trajectory) -> bool:
        """Safely send trajectory with validation."""
        if not self.vehicle_io.is_connected():
            self.logger.error("Cannot send trajectory: not connected")
            return False
        
        if not trajectory or len(trajectory.positions) == 0:
            self.logger.error("Cannot send empty trajectory")
            return False
        
        try:
            return await self.vehicle_io.send_trajectory(trajectory)
        except Exception as e:
            self.logger.error(f"Failed to send trajectory: {e}")
            return False
    
    def validate_trajectory(self, trajectory: Trajectory) -> List[str]:
        """Validate trajectory for safety and feasibility."""
        issues = []
        
        if not trajectory:
            issues.append("Trajectory is None")
            return issues
        
        if len(trajectory.positions) == 0:
            issues.append("Trajectory has no positions")
            return issues
        
        # Check for reasonable positions
        for i, pos in enumerate(trajectory.positions):
            if np.any(np.isnan(pos)) or np.any(np.isinf(pos)):
                issues.append(f"Invalid position at index {i}: {pos}")
            
            # Check altitude bounds
            if pos[2] < 0.1:  # Minimum safe altitude
                issues.append(f"Position {i} too low: {pos[2]}m")
        
        # Check for reasonable velocities
        if hasattr(trajectory, 'velocities') and trajectory.velocities:
            for i, vel in enumerate(trajectory.velocities):
                if np.any(np.abs(vel) > 20.0):  # 20 m/s max
                    issues.append(f"Velocity {i} too high: {vel}")
        
        return issues 