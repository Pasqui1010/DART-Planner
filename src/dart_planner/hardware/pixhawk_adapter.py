"""
Pixhawk Adapter implementing the HardwareInterface for DART-Planner.
"""

from dart_planner.common.interfaces import HardwareInterface
from typing import Any, Dict, Optional
from dart_planner.hardware.pixhawk_interface import PixhawkInterface, HardwareConfig
from dart_planner.common.errors import UnsupportedCommandError

class PixhawkAdapter(HardwareInterface):
    """
    Adapter for Pixhawk hardware, implementing the common HardwareInterface.
    Wraps PixhawkInterface and exposes a unified API for the planner.
    """
    def __init__(self, config: Optional[HardwareConfig] = None):
        self._iface = PixhawkInterface(config)

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
            import logging
            logging.getLogger(__name__).warning(f"Command '{command}' not supported by PixhawkAdapter.")
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
            return asyncio.get_event_loop().run_until_complete(self._iface.set_mode(params["mode"]))
        elif command == "start_mission":
            import asyncio
            return asyncio.get_event_loop().run_until_complete(self._iface.start_mission(params["waypoints"]))
        elif command == "stop_mission":
            import asyncio
            return asyncio.get_event_loop().run_until_complete(self._iface.stop_mission())
        else:
            raise UnsupportedCommandError(f"Command '{command}' not supported by PixhawkAdapter.")

    def get_state(self) -> Dict[str, Any]:
        # Return the current state as a dictionary
        return self._iface.current_state.__dict__

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

    def emergency_stop(self) -> None:
        # Trigger failsafe
        import asyncio
        asyncio.get_event_loop().run_until_complete(self._iface._trigger_failsafe("manual emergency_stop"))

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
