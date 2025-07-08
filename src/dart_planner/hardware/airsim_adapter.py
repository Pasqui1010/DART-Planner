"""
AirSim Adapter implementing the HardwareInterface for DART-Planner.
"""

from dart_planner.common.interfaces import HardwareInterface
from dart_planner.common.errors import HardwareError
from typing import Any, Dict, Optional
import logging

# Import AirSim Python API if available
try:
    import airsim
except ImportError:
    airsim = None

logger = logging.getLogger(__name__)

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
        self._mission_state = {
            "status": "idle",  # idle, running, paused, completed, failed
            "current_waypoint": 0,
            "total_waypoints": 0,
            "mission_params": None
        }

    def connect(self) -> None:
        self.client.confirmConnection()
        self.connected = True

    def disconnect(self) -> None:
        self.client.enableApiControl(False)
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def supports(self, command: str) -> bool:
        """Check if a command is supported by this adapter."""
        return command in self.get_capabilities().get("supported_commands", [])

    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if not self.supports(command):
            logger.warning(f"Command '{command}' not supported by AirSimAdapter.")
            raise HardwareError(f"Command '{command}' not supported by AirSimAdapter.")
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
        # Return the current state as a dictionary with safety flags
        state = self.client.getMultirotorState()
        landed_state = None
        if airsim is not None:
            landed_state = state.landed_state == airsim.LandedState.Flying
        
        # Add safety flags for watchdog correctness
        return {
            "position": state.kinematics_estimated.position,
            "velocity": state.kinematics_estimated.linear_velocity,
            "orientation": state.kinematics_estimated.orientation,
            "armed": self._is_armed(),
            "in_air": self._is_in_air(),
            "failsafe": self._is_failsafe(),
            "mission_state": self._mission_state
        }

    def _is_armed(self) -> bool:
        """Check if the vehicle is armed."""
        try:
            if airsim is None:
                return False
            state = self.client.getMultirotorState()
            return state.landed_state != airsim.LandedState.Landed
        except Exception as e:
            logger.warning(f"Error checking armed state: {e}")
            return False

    def _is_in_air(self) -> bool:
        """Check if the vehicle is in the air."""
        try:
            if airsim is None:
                return False
            state = self.client.getMultirotorState()
            return state.landed_state == airsim.LandedState.Flying
        except Exception as e:
            logger.warning(f"Error checking in_air state: {e}")
            return False

    def _is_failsafe(self) -> bool:
        """Check if the vehicle is in failsafe mode."""
        try:
            # AirSim doesn't have explicit failsafe, but we can check for error conditions
            state = self.client.getMultirotorState()
            # Check for extreme velocities or positions that might indicate a problem
            velocity = state.kinematics_estimated.linear_velocity
            speed = (velocity.x_val**2 + velocity.y_val**2 + velocity.z_val**2)**0.5
            return speed > 50.0  # Arbitrary threshold for simulation
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
            
            # In AirSim, we can hover in place
            current_pos = self.client.getMultirotorState().kinematics_estimated.position
            self.client.moveToPositionAsync(
                current_pos.x_val, current_pos.y_val, current_pos.z_val, 1.0
            )
            
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
            
            # Resume mission execution (in a real implementation, this would resume waypoint following)
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
        self.client.reset()
        self._mission_state = {
            "status": "idle",
            "current_waypoint": 0,
            "total_waypoints": 0,
            "mission_params": None
        }

    def emergency_stop(self) -> None:
        # Use the instance method for emergency stop if available
        if airsim is not None and hasattr(self.client, "emergencyStop"):
            self.client.emergencyStop(True)
        else:
            raise HardwareError("emergencyStop is not available in this AirSim client.")
        self._mission_state["status"] = "failed"

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
