"""
AirSim State Management

This module handles state retrieval and conversion from AirSim format
to DART-Planner's internal state representation.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import airsim
import numpy as np

from ..common.types import DroneState
from ..common.coordinate_frames import get_coordinate_frame_manager, WorldFrame
from ..common.units import Q_


@dataclass
class AirSimConfig:
    """Configuration for AirSim interface"""
    
    # Connection settings
    ip: str = "127.0.0.1"
    port: int = 41451
    timeout_value: float = 10.0
    
    # Vehicle settings
    vehicle_name: str = "Drone1"
    enable_api_control: bool = True
    
    # Control settings
    max_duration_s: float = 1.0
    drivetrain_type: int = airsim.DrivetrainType.MaxDegreeOfFreedom
    yaw_mode: airsim.YawMode = field(default_factory=lambda: airsim.YawMode(False, 0))
    
    # Safety settings
    safety_eval_timeout: float = 2.0
    max_velocity: float = 10.0
    max_acceleration: float = 5.0
    
    # State estimation settings
    use_gps: bool = False
    use_magnetometer: bool = True
    use_barometer: bool = True
    
    # Logging settings
    log_level: int = logging.INFO
    enable_trace_logging: bool = False


class AirSimStateManager:
    """Manages state retrieval and conversion from AirSim"""
    
    def __init__(self, config: AirSimConfig):
        self.config = config
        self._last_state: Optional[DroneState] = None
        self._error_count: int = 0
        
        # Initialize coordinate frame manager
        self._frame_manager = get_coordinate_frame_manager()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config.log_level)
        
        # Log coordinate frame information
        self.logger.info(f"AirSim State Manager initialized with coordinate frame: {self._frame_manager.world_frame.value}")
    
    def _quaternion_to_euler(self, quaternion: np.ndarray) -> np.ndarray:
        """
        Convert quaternion to euler angles (roll, pitch, yaw)
        
        Args:
            quaternion: Quaternion as [w, x, y, z]
            
        Returns:
            Euler angles as [roll, pitch, yaw] in radians
        """
        w, x, y, z = quaternion
        
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = np.copysign(np.pi / 2, sinp)  # Use 90 degrees if out of range
        else:
            pitch = np.arcsin(sinp)
        
        # Yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)
        
        return np.array([roll, pitch, yaw])
    
    def get_state(self, client: airsim.MultirotorClient) -> DroneState:
        """
        Get current drone state from AirSim
        
        Args:
            client: AirSim client instance
            
        Returns:
            DroneState object with position, velocity, orientation, etc.
        """
        if not client:
            from dart_planner.common.errors import HardwareError
            raise HardwareError("AirSim client not provided")
        
        try:
            # Get multirotor state
            state = client.getMultirotorState(self.config.vehicle_name)
            
            # Convert to DART-Planner format
            drone_state = self._convert_airsim_state(state)
            
            self._last_state = drone_state
            return drone_state
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get state: {e}")
            self._error_count += 1
            
            # Return last known state if available
            if self._last_state:
                self.logger.warning("⚠️ Using last known state")
                return self._last_state
            
            from dart_planner.common.errors import HardwareError
            raise HardwareError(f"Failed to get drone state: {e}")
    
    def _convert_airsim_state(self, airsim_state: airsim.MultirotorState) -> DroneState:
        """
        Convert AirSim state to DART-Planner DroneState
        
        Args:
            airsim_state: Raw AirSim state object
            
        Returns:
            Converted DroneState
        """
        # AirSim uses NED coordinates natively
        position_ned = np.array([
            airsim_state.kinematics_estimated.position.x_val,
            airsim_state.kinematics_estimated.position.y_val,
            airsim_state.kinematics_estimated.position.z_val
        ])
        
        velocity_ned = np.array([
            airsim_state.kinematics_estimated.linear_velocity.x_val,
            airsim_state.kinematics_estimated.linear_velocity.y_val,
            airsim_state.kinematics_estimated.linear_velocity.z_val
        ])
        
        angular_velocity_ned = np.array([
            airsim_state.kinematics_estimated.angular_velocity.x_val,
            airsim_state.kinematics_estimated.angular_velocity.y_val,
            airsim_state.kinematics_estimated.angular_velocity.z_val
        ])
        
        # Convert quaternion to roll, pitch, yaw (attitude)
        quaternion = np.array([
            airsim_state.kinematics_estimated.orientation.w_val,
            airsim_state.kinematics_estimated.orientation.x_val,
            airsim_state.kinematics_estimated.orientation.y_val,
            airsim_state.kinematics_estimated.orientation.z_val
        ])
        
        # Convert quaternion to euler angles (roll, pitch, yaw)
        attitude_ned = self._quaternion_to_euler(quaternion)
        
        # Convert to target coordinate frame if needed
        if self._frame_manager.world_frame == WorldFrame.ENU:
            # Convert NED to ENU
            position = self._frame_manager.transform_ned_to_enu(position_ned)
            velocity = self._frame_manager.transform_ned_to_enu(velocity_ned)
            angular_velocity = self._frame_manager.transform_ned_to_enu(angular_velocity_ned)
            # For attitude, we also need to convert the euler angles
            attitude = self._transform_attitude_ned_to_enu(attitude_ned)
        else:
            # Target frame is NED, no conversion needed
            position = position_ned
            velocity = velocity_ned
            angular_velocity = angular_velocity_ned
            attitude = attitude_ned
        
        # Create DroneState with proper units
        return DroneState(
            timestamp=time.time(),
            position=Q_(position, 'm'),
            velocity=Q_(velocity, 'm/s'),
            attitude=Q_(attitude, 'rad'),
            angular_velocity=Q_(angular_velocity, 'rad/s')
        )
    
    def _transform_attitude_ned_to_enu(self, attitude_ned: np.ndarray) -> np.ndarray:
        """
        Transform attitude from NED to ENU frame.
        
        Args:
            attitude_ned: Attitude in NED frame [roll, pitch, yaw]
            
        Returns:
            Attitude in ENU frame [roll, pitch, yaw]
        """
        roll_ned, pitch_ned, yaw_ned = attitude_ned
        
        # Convert NED attitude to ENU attitude
        # Roll: stays the same (rotation around forward axis)
        # Pitch: sign flip (pitch up in NED is pitch down in ENU)
        # Yaw: adjust for different heading reference
        roll_enu = roll_ned
        pitch_enu = -pitch_ned
        yaw_enu = yaw_ned + np.pi/2  # NED yaw (0=North) to ENU yaw (0=East)
        
        # Normalize yaw to [-pi, pi]
        yaw_enu = np.arctan2(np.sin(yaw_enu), np.cos(yaw_enu))
        
        return np.array([roll_enu, pitch_enu, yaw_enu])
    
    def get_last_state(self) -> Optional[DroneState]:
        """Get the last known state"""
        return self._last_state
    
    def get_error_count(self) -> int:
        """Get the number of state retrieval errors"""
        return self._error_count
    
    def reset_error_count(self) -> None:
        """Reset the error count"""
        self._error_count = 0


# Type aliases for clarity
AirSimState = airsim.MultirotorState
AirSimClient = airsim.MultirotorClient 
