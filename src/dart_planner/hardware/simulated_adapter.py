"""
Simulated Adapter implementing the HardwareInterface for DART-Planner.
"""

from dart_planner.common.interfaces import HardwareInterface
from dart_planner.common.errors import HardwareError
from typing import Any, Dict, Optional

class SimulatedAdapter(HardwareInterface):
    """
    Adapter for pure software simulation or mock hardware, implementing the common HardwareInterface.
    Useful for testing, CI, and development without real hardware or AirSim.
    """
    def __init__(self):
        self.connected = False
        self.state = {
            "position": (0.0, 0.0, 0.0),
            "velocity": (0.0, 0.0, 0.0),
            "orientation": (1.0, 0.0, 0.0, 0.0),
            "armed": False,
        }
        self.capabilities = {
            "max_velocity": 10.0,
            "max_acceleration": 5.0,
            "max_altitude": 20.0,
            "safety_radius": 50.0,
            "simulated": True,
        }

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if command == "arm":
            self.state["armed"] = True
            return True
        elif command == "disarm":
            self.state["armed"] = False
            return True
        elif command == "takeoff":
            self.state["position"] = (0.0, 0.0, 2.0)
            return True
        elif command == "land":
            self.state["position"] = (0.0, 0.0, 0.0)
            return True
        elif command == "moveToPosition":
            if params and all(k in params for k in ("x", "y", "z")):
                self.state["position"] = (params["x"], params["y"], params["z"])
                return True
            else:
                raise HardwareError("moveToPosition requires x, y, z params")
        else:
            raise HardwareError(f"Command '{command}' not supported by SimulatedAdapter.")

    def get_state(self) -> Dict[str, Any]:
        return self.state.copy()

    def reset(self) -> None:
        self.state = {
            "position": (0.0, 0.0, 0.0),
            "velocity": (0.0, 0.0, 0.0),
            "orientation": (1.0, 0.0, 0.0, 0.0),
            "armed": False,
        }

    def emergency_stop(self) -> None:
        self.state["velocity"] = (0.0, 0.0, 0.0)
        self.state["armed"] = False

    def get_capabilities(self) -> Dict[str, Any]:
        caps = self.capabilities.copy()
        caps["supported_commands"] = [
            "arm", "disarm", "takeoff", "land", "moveToPosition"
        ]
        return caps

    def update(self) -> None:
        # Simulate periodic update (no-op for now)
        pass 
