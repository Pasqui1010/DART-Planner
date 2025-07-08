"""
AirSim Adapter implementing the HardwareInterface for DART-Planner.
"""

from dart_planner.common.interfaces import HardwareInterface
from dart_planner.common.errors import HardwareError
from typing import Any, Dict, Optional

# Import AirSim Python API if available
try:
    import airsim
except ImportError:
    airsim = None

class AirSimAdapter(HardwareInterface):
    """
    Adapter for AirSim simulation, implementing the common HardwareInterface.
    Wraps AirSim Python API and exposes a unified API for the planner.
    """
    def __init__(self, client: Optional[Any] = None):
        if airsim is None:
            raise ImportError("AirSim Python API is not installed.")
        self.client = client or airsim.MultirotorClient()
        self.connected = False

    def connect(self) -> None:
        self.client.confirmConnection()
        self.connected = True

    def disconnect(self) -> None:
        self.client.enableApiControl(False)
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Any:
        # Map command strings to AirSim API methods
        if command == "arm":
            return self.client.armDisarm(True)
        elif command == "disarm":
            return self.client.armDisarm(False)
        elif command == "takeoff":
            return self.client.takeoffAsync().join()
        elif command == "land":
            return self.client.landAsync().join()
        elif command == "moveToPosition":
            # Require explicit x, y, z, velocity in params
            if not params or not all(k in params for k in ("x", "y", "z", "velocity")):
                raise HardwareError("moveToPosition requires x, y, z, velocity params")
            return self.client.moveToPositionAsync(
                params["x"], params["y"], params["z"], params["velocity"]
            ).join()
        else:
            raise HardwareError(f"Command '{command}' not supported by AirSimAdapter.")

    def get_state(self) -> Dict[str, Any]:
        # Return the current state as a dictionary
        state = self.client.getMultirotorState()
        landed_state = None
        if airsim is not None:
            landed_state = state.landed_state == airsim.LandedState.Flying
        return {
            "position": state.kinematics_estimated.position,
            "velocity": state.kinematics_estimated.linear_velocity,
            "orientation": state.kinematics_estimated.orientation,
            "armed": landed_state,
        }

    def reset(self) -> None:
        self.client.reset()

    def emergency_stop(self) -> None:
        # Use the instance method for emergency stop if available
        if airsim is not None and hasattr(self.client, "emergencyStop"):
            self.client.emergencyStop(True)
        else:
            raise HardwareError("emergencyStop is not available in this AirSim client.")

    def get_capabilities(self) -> Dict[str, Any]:
        # Return simulation capabilities
        return {
            "max_velocity": 15.0,
            "max_acceleration": 10.0,
            "max_altitude": 50.0,
            "safety_radius": 100.0,
            "simulated": True,
            "supported_commands": [
                "arm", "disarm", "takeoff", "land", "moveToPosition"
            ],
        }

    def update(self) -> None:
        # Poll sensors or refresh state (no-op for AirSim)
        pass
