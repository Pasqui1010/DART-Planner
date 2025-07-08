"""
Pixhawk Adapter implementing the HardwareInterface for DART-Planner.
"""

from dart_planner.common.interfaces import HardwareInterface
from typing import Any, Dict, Optional
from dart_planner.hardware.pixhawk_interface import PixhawkInterface, HardwareConfig
from dart_planner.common.errors import UnsupportedCommandError
import logging

logger = logging.getLogger(__name__)

class PixhawkAdapter(HardwareInterface):
    """
    Adapter for Pixhawk hardware, implementing the common HardwareInterface.
    Wraps PixhawkInterface and exposes a unified API for the planner.
    """
    def __init__(self, config: Optional[HardwareConfig] = None):
        self._iface = PixhawkInterface(config)
        self._mission_state = {
            "status": "idle",  # idle, running, paused, completed, failed
            "current_waypoint": 0,
            "total_waypoints": 0,
            "mission_params": None
        }

    def connect(self) -> None:
        # PixhawkInterface.connect is async, so we run it in the event loop
        import asyncio
        asyncio.get_event_loop().run_until_complete(self._iface.connect())

    def disconnect(self) -> None:
        import asyncio
        asyncio.get_event_loop().run_until_complete(self._iface.close())

    def is_connected(self) -> bool:
        return self._iface.is_connected

    def supports(self, command: str) -> bool:
        """Check if a command is supported by this adapter."""
        return command in self.get_capabilities().get("supported_commands", [])

    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if not self.supports(command):
            logger.warning(f"Command '{command}' not supported by PixhawkAdapter.")
            raise UnsupportedCommandError(f"Command '{command}' not supported by PixhawkAdapter.")
        # Map command strings to PixhawkInterface methods
        if command == "arm":
            import asyncio
            return asyncio.get_event_loop().run_until_complete(self._iface.arm(**(params or {})))
        elif command == "disarm":
            import asyncio
            return asyncio.get_event_loop().run_until_complete(self._iface.disarm(**(params or {})))
        elif command == "takeoff":
            import asyncio
            return asyncio.get_event_loop().run_until_complete(self._iface.takeoff(**(params or {})))
        elif command == "land":
            import asyncio
            return asyncio.get_event_loop().run_until_complete(self._iface.land(**(params or {})))
        elif command == "set_mode":
            import asyncio
            if params and "mode" in params:
                return asyncio.get_event_loop().run_until_complete(self._iface.set_mode(params["mode"]))
            else:
                raise UnsupportedCommandError("set_mode requires 'mode' parameter")
        elif command == "start_mission":
            import asyncio
            if params and "waypoints" in params:
                return asyncio.get_event_loop().run_until_complete(self._iface.start_mission(params["waypoints"]))
            else:
                raise UnsupportedCommandError("start_mission requires 'waypoints' parameter")
        elif command == "stop_mission":
            import asyncio
            return asyncio.get_event_loop().run_until_complete(self._iface.stop_mission())
        else:
            raise UnsupportedCommandError(f"Command '{command}' not supported by PixhawkAdapter.")

    def get_state(self) -> Dict[str, Any]:
        # Return the current state as a dictionary with safety flags
        state = self._iface.current_state.__dict__.copy()
        
        # Add safety flags for watchdog correctness
        state.update({
            "armed": self._is_armed(),
            "in_air": self._is_in_air(),
            "failsafe": self._is_failsafe(),
            "mission_state": self._mission_state
        })
        
        return state

    def _is_armed(self) -> bool:
        """Check if the vehicle is armed."""
        try:
            # Check if motors are armed based on Pixhawk state
            return getattr(self._iface.current_state, 'armed', False)
        except Exception as e:
            logger.warning(f"Error checking armed state: {e}")
            return False

    def _is_in_air(self) -> bool:
        """Check if the vehicle is in the air."""
        try:
            # Check altitude or flight mode to determine if in air
            altitude = getattr(self._iface.current_state, 'altitude', 0.0)
            return altitude > 1.0  # Consider in air if altitude > 1m
        except Exception as e:
            logger.warning(f"Error checking in_air state: {e}")
            return False

    def _is_failsafe(self) -> bool:
        """Check if the vehicle is in failsafe mode."""
        try:
            # Check for failsafe conditions
            return getattr(self._iface.current_state, 'failsafe', False)
        except Exception as e:
            logger.warning(f"Error checking failsafe state: {e}")
            return False

    def start_mission(self, mission_params: Optional[Dict[str, Any]] = None) -> bool:
        """Start a mission."""
        try:
            if self._mission_state["status"] == "running":
                logger.warning("Mission already running")
                return True  # Idempotent
            
            # Arm and take off if not already in air
            if not self._is_armed():
                self.send_command("arm")
            
            if not self._is_in_air():
                self.send_command("takeoff")
            
            # Set mission parameters
            self._mission_state.update({
                "status": "running",
                "mission_params": mission_params or {},
                "current_waypoint": 0
            })
            
            logger.info("Mission started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start mission: {e}")
            self._mission_state["status"] = "failed"
            return False

    def pause_mission(self) -> bool:
        """Pause the current mission."""
        try:
            if self._mission_state["status"] != "running":
                logger.warning("No mission running to pause")
                return True  # Idempotent
            
            # Set mode to loiter/hold
            self.send_command("set_mode", {"mode": "LOITER"})
            
            self._mission_state["status"] = "paused"
            logger.info("Mission paused successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause mission: {e}")
            return False

    def resume_mission(self) -> bool:
        """Resume the paused mission."""
        try:
            if self._mission_state["status"] != "paused":
                logger.warning("No mission paused to resume")
                return True  # Idempotent
            
            # Resume mission execution
            self.send_command("set_mode", {"mode": "AUTO"})
            
            self._mission_state["status"] = "running"
            logger.info("Mission resumed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume mission: {e}")
            return False

    def get_mission_state(self) -> Dict[str, Any]:
        """Get current mission state."""
        return self._mission_state.copy()

    def reset(self) -> None:
        # Reset state and statistics
        self._iface.current_state = self._iface.current_state.__class__()
        self._iface.performance_stats = {
            "control_loop_times": [],
            "planning_times": [],
            "total_commands_sent": 0,
            "planning_failures": 0,
            "control_frequency_achieved": 0.0,
        }
        self._mission_state = {
            "status": "idle",
            "current_waypoint": 0,
            "total_waypoints": 0,
            "mission_params": None
        }

    def emergency_stop(self) -> None:
        # Trigger failsafe
        import asyncio
        asyncio.get_event_loop().run_until_complete(self._iface._trigger_failsafe("manual emergency_stop"))
        self._mission_state["status"] = "failed"

    def get_capabilities(self) -> Dict[str, Any]:
        # Return hardware capabilities
        return {
            "max_velocity": self._iface.config.max_velocity,
            "max_acceleration": self._iface.config.max_acceleration,
            "max_altitude": self._iface.config.max_altitude,
            "safety_radius": self._iface.config.safety_radius,
            "max_thrust": self._iface.config.max_thrust,
            "supported_commands": [
                "arm", "disarm", "takeoff", "land", "set_mode", "start_mission", "stop_mission"
            ],
        }

    def update(self) -> None:
        # Poll sensors or refresh state (could be async in real system)
        pass 
