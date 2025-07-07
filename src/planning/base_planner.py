"""
Base Planner Interface for DART-Planner

This module defines the abstract base class for all planning algorithms,
ensuring consistent interfaces and enabling dependency injection.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

from ..common.types import DroneState, Trajectory


class BasePlanner(ABC):
    """
    Abstract base class for all trajectory planners.
    
    This ensures consistent interfaces across different planning algorithms
    and enables easy swapping of planners through dependency injection.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize planner with configuration."""
        self.config = config
        self.obstacles: List[Tuple[np.ndarray, float]] = []
        self.planning_stats = {
            "total_plans": 0,
            "successful_plans": 0,
            "planning_times": [],
            "last_plan_time": 0.0,
        }
    
    @abstractmethod
    def plan_trajectory(self, current_state: DroneState, goal: np.ndarray) -> Optional[Trajectory]:
        """
        Plan a trajectory from current state to goal.
        
        Args:
            current_state: Current drone state
            goal: Target position (3D numpy array)
            
        Returns:
            Trajectory object if planning succeeds, None otherwise
        """
        pass
    
    @abstractmethod
    def add_obstacle(self, center: np.ndarray, radius: float) -> None:
        """Add an obstacle for avoidance."""
        pass
    
    @abstractmethod
    def clear_obstacles(self) -> None:
        """Clear all obstacles."""
        pass
    
    @abstractmethod
    def get_planning_stats(self) -> Dict[str, Any]:
        """Get planning performance statistics."""
        pass
    
    def validate_goal(self, goal: np.ndarray) -> bool:
        """Validate that goal is reachable and within bounds."""
        if goal is None or goal.shape != (3,):
            return False
        
        # Check altitude bounds
        if goal[2] < 0.5:  # Minimum safe altitude
            return False
        
        return True
    
    def validate_state(self, state: DroneState) -> bool:
        """Validate that current state is reasonable."""
        if state is None:
            return False
        
        # Check position bounds
        if np.any(np.isnan(state.position)) or np.any(np.isinf(state.position)):
            return False
        
        # Check velocity bounds (reasonable limits)
        if np.any(np.abs(state.velocity) > 20.0):  # 20 m/s max
            return False
        
        return True
    
    def _update_planning_stats(self, planning_time: float, success: bool) -> None:
        """Update internal planning statistics."""
        self.planning_stats["total_plans"] += 1
        self.planning_stats["last_plan_time"] = planning_time
        
        if success:
            self.planning_stats["successful_plans"] += 1
        
        self.planning_stats["planning_times"].append(planning_time)
        
        # Keep only last 100 planning times for memory efficiency
        if len(self.planning_stats["planning_times"]) > 100:
            self.planning_stats["planning_times"] = self.planning_stats["planning_times"][-100:]
    
    def reset_stats(self) -> None:
        """Reset planning statistics."""
        self.planning_stats = {
            "total_plans": 0,
            "successful_plans": 0,
            "planning_times": [],
            "last_plan_time": 0.0,
        }


class PlannerFactory:
    """Factory for creating planner instances."""
    
    _planners = {}
    
    @classmethod
    def register(cls, name: str, planner_class: type):
        """Register a planner class with a name."""
        cls._planners[name] = planner_class
    
    @classmethod
    def create(cls, name: str, config: Dict[str, Any]) -> BasePlanner:
        """Create a planner instance by name."""
        if name not in cls._planners:
            raise ValueError(f"Unknown planner: {name}. Available: {list(cls._planners.keys())}")
        
        return cls._planners[name](config)
    
    @classmethod
    def list_available(cls) -> List[str]:
        """List all available planner names."""
        return list(cls._planners.keys()) 