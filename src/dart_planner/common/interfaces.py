"""
Common interfaces for DART-Planner hardware abstraction.
"""

import abc
from typing import Any, Dict, Optional, List
from .types import DroneState, Trajectory

class HardwareInterface(abc.ABC):
    """
    Abstract base class for all hardware adapters in DART-Planner.
    Defines the contract for hardware communication and state access.
    """

    @abc.abstractmethod
    def connect(self) -> None:
        """Establish connection to the hardware device."""
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the hardware device."""
        pass

    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Return True if the hardware is connected."""
        pass

    @abc.abstractmethod
    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send a command to the hardware. Returns a result or raises on error."""
        pass

    @abc.abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the hardware (position, velocity, health, etc.)."""
        pass

    @abc.abstractmethod
    def reset(self) -> None:
        """Reset the hardware to a known state."""
        pass

    @abc.abstractmethod
    def emergency_stop(self) -> None:
        """Trigger an emergency stop on the hardware."""
        pass

    @abc.abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return a dictionary describing hardware capabilities (e.g., max velocity, sensors)."""
        pass

    @abc.abstractmethod
    def update(self) -> None:
        """Perform a periodic update (e.g., poll sensors, refresh state)."""
        pass

    @abc.abstractmethod
    def start_mission(self, mission_params: Optional[Dict[str, Any]] = None) -> bool:
        """Start a mission. Returns True if successful."""
        pass

    @abc.abstractmethod
    def pause_mission(self) -> bool:
        """Pause the current mission. Returns True if successful."""
        pass

    @abc.abstractmethod
    def resume_mission(self) -> bool:
        """Resume the paused mission. Returns True if successful."""
        pass

    @abc.abstractmethod
    def get_mission_state(self) -> Dict[str, Any]:
        """Get current mission state (running, paused, completed, etc.)."""
        pass


class IPlanner(abc.ABC):
    """
    Abstract base class for all planners in DART-Planner.
    Defines the contract for trajectory planning and optimization.
    """

    @abc.abstractmethod
    def plan_trajectory(self, current_state: DroneState, goal: Dict[str, Any]) -> Trajectory:
        """Plan a trajectory from current state to goal."""
        pass

    @abc.abstractmethod
    def update_plan(self, current_state: DroneState, obstacles: List[Dict[str, Any]]) -> Trajectory:
        """Update the current plan based on new state and obstacles."""
        pass

    @abc.abstractmethod
    def is_plan_valid(self, trajectory: Trajectory) -> bool:
        """Check if a trajectory is valid and safe."""
        pass

    @abc.abstractmethod
    def get_planning_stats(self) -> Dict[str, Any]:
        """Get planning statistics and performance metrics."""
        pass 
