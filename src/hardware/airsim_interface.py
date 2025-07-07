"""
AirSim Interface for DART-Planner

This module provides a comprehensive interface to Microsoft AirSim for
drone simulation and hardware-in-the-loop testing.

The interface is now organized into sub-modules:
- connection.py: Connection management and initialization
- state.py: State retrieval and conversion
- safety.py: Safety monitoring and emergency procedures
- metrics.py: Performance metrics and logging
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Union, Any, Callable

import airsim
import numpy as np
import numpy.typing as npt

from src.common.types import DroneState, ControlCommand

from .connection import AirSimConnection
from .state import AirSimConfig, AirSimStateManager
from .safety import AirSimSafetyManager
from .metrics import AirSimMetricsManager


class AirSimDroneInterface:
    """
    Comprehensive AirSim interface for drone control and simulation
    
    Features:
    - Async/await API for non-blocking operations
    - Comprehensive error handling and recovery
    - State estimation from multiple sensors
    - Safety monitoring and failsafes
    - Performance metrics and logging
    """
    
    def __init__(self, config: Optional[AirSimConfig] = None):
        self.config = config or AirSimConfig()
        
        # Initialize sub-modules
        self.connection = AirSimConnection(self.config)
        self.state_manager = AirSimStateManager(self.config)
        self.safety_manager = AirSimSafetyManager(self.config)
        self.metrics_manager = AirSimMetricsManager(self.config)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config.log_level)
    
    async def connect(self) -> bool:
        """
        Connect to AirSim simulator
        
        Returns:
            True if connection successful, False otherwise
        """
        return await self.connection.connect()
    
    async def disconnect(self) -> None:
        """Safely disconnect from AirSim"""
        await self.connection.disconnect()
    
    async def get_state(self) -> DroneState:
        """
        Get current drone state from AirSim
        
        Returns:
            DroneState object with position, velocity, orientation, etc.
        """
        if not self.connection.is_connected():
            raise RuntimeError("Not connected to AirSim")
        
        try:
            client = self.connection.get_client()
            if not client:
                raise RuntimeError("AirSim client not available")
            
            # Get state from state manager
            drone_state = self.state_manager.get_state(client)
            
            # Track state for metrics
            self.metrics_manager.track_state(drone_state)
            
            # Perform safety checks
            await self.safety_manager.monitor_safety(drone_state, client)
            
            return drone_state
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get state: {e}")
            self.metrics_manager.track_error()
            
            # Return last known state if available
            last_state = self.state_manager.get_last_state()
            if last_state:
                self.logger.warning("⚠️ Using last known state")
                return last_state
            
            raise RuntimeError(f"Failed to get drone state: {e}")
    
    async def send_control_command(self, command: ControlCommand) -> bool:
        """
        Send control command to AirSim
        
        Args:
            command: ControlCommand with thrust and torque
            
        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.connection.is_connected():
            self.logger.error("❌ Not connected to AirSim")
            return False
        
        if not self.connection.is_api_control_enabled():
            self.logger.error("❌ API control not enabled")
            return False
        
        try:
            # Track control command for metrics
            self.metrics_manager.track_control_command(command)
            
            # Convert DART control command to AirSim format
            await self._send_thrust_torque_command(command.thrust, command.torque)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send control command: {e}")
            self.metrics_manager.track_error()
            return False
    
    async def _send_thrust_torque_command(self, thrust: float, torque: npt.NDArray[np.float64]) -> None:
        """
        Send thrust and torque command to AirSim using moveByMotorPWMsAsync
        
        Args:
            thrust: Thrust magnitude in Newtons
            torque: Torque vector [roll, pitch, yaw] in N⋅m
        """
        client = self.connection.get_client()
        if not client:
            raise RuntimeError("AirSim client not available")
        
        # Convert thrust and torque to motor PWM values
        # This is a simplified mapping - in practice, you'd use the drone's
        # motor configuration and dynamics model
        
        # Normalize thrust to PWM range (0.0 to 1.0)
        thrust_normalized = np.clip(thrust / self.config.max_acceleration, 0.0, 1.0)
        
        # Simple 4-motor mapping (X configuration)
        # This assumes a symmetric quadrotor in X configuration
        base_pwm = thrust_normalized
        
        # Add torque corrections (simplified)
        roll_correction = torque[0] * 0.1   # Roll torque
        pitch_correction = torque[1] * 0.1  # Pitch torque  
        yaw_correction = torque[2] * 0.05   # Yaw torque
        
        # Motor PWM assignments for X configuration
        # Motor layout:  1   0
        #               \ X /
        #                X
        #               / X \
        #              2   3
        
        pwm_front_right = np.clip(base_pwm + pitch_correction + roll_correction + yaw_correction, 0.0, 1.0)  # Motor 0
        pwm_front_left = np.clip(base_pwm + pitch_correction - roll_correction - yaw_correction, 0.0, 1.0)   # Motor 1
        pwm_rear_left = np.clip(base_pwm - pitch_correction - roll_correction + yaw_correction, 0.0, 1.0)    # Motor 2
        pwm_rear_right = np.clip(base_pwm - pitch_correction + roll_correction - yaw_correction, 0.0, 1.0)   # Motor 3
        
        # Send to AirSim
        await asyncio.wait_for(
            asyncio.create_task(
                asyncio.to_thread(
                    client.moveByMotorPWMsAsync,
                    float(pwm_front_right),
                    float(pwm_front_left), 
                    float(pwm_rear_left),
                    float(pwm_rear_right),
                    self.config.max_duration_s,
                    self.config.vehicle_name
                )
            ),
            timeout=self.config.safety_eval_timeout
        )
    
    async def takeoff(self, altitude: float = 2.0) -> bool:
        """
        Takeoff to specified altitude
        
        Args:
            altitude: Target altitude in meters (positive up)
            
        Returns:
            True if takeoff successful, False otherwise
        """
        client = self.connection.get_client()
        if not client:
            self.logger.error("❌ Not connected to AirSim")
            return False
        
        return await self.safety_manager.takeoff(client, altitude)
    
    async def land(self) -> bool:
        """
        Land the drone safely
        
        Returns:
            True if landing successful, False otherwise
        """
        client = self.connection.get_client()
        if not client:
            self.logger.error("❌ Not connected to AirSim")
            return False
        
        return await self.safety_manager._perform_landing(client)
    
    async def emergency_land(self) -> None:
        """Emergency landing procedure"""
        client = self.connection.get_client()
        if not client:
            self.logger.error("❌ Not connected to AirSim")
            return
        
        await self.safety_manager.emergency_land(client)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the interface
        
        Returns:
            Dictionary containing performance metrics
        """
        base_metrics = self.metrics_manager.get_performance_metrics()
        
        # Add connection and safety metrics
        base_metrics.update({
            "connected": self.connection.is_connected(),
            "api_control_enabled": self.connection.is_api_control_enabled(),
            "armed": self.connection.is_armed(),
            "safety_violations": self.safety_manager.get_safety_violations(),
            "state_errors": self.state_manager.get_error_count()
        })
        
        return base_metrics
    
    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self.metrics_manager.reset_metrics()
        self.safety_manager.reset_safety_violations()
        self.state_manager.reset_error_count()
    
    # Convenience properties for backward compatibility
    @property
    def connected(self) -> bool:
        """Check if connected to AirSim"""
        return self.connection.is_connected()
    
    @property
    def armed(self) -> bool:
        """Check if vehicle is armed"""
        return self.connection.is_armed()
    
    @property
    def api_control_enabled(self) -> bool:
        """Check if API control is enabled"""
        return self.connection.is_api_control_enabled()

    async def start_mission(self, waypoints: List[np.ndarray]) -> bool:
        """
        Start an autonomous mission with given waypoints
        
        Args:
            waypoints: List of waypoint positions as numpy arrays
            
        Returns:
            True if mission started successfully, False otherwise
        """
        client = self.connection.get_client()
        if not client:
            self.logger.error("❌ Not connected to AirSim")
            return False
        
        try:
            self.logger.info(f"🚀 Starting mission with {len(waypoints)} waypoints")
            
            # For now, implement a simple waypoint following mission
            # In a full implementation, this would integrate with the planner
            for i, waypoint in enumerate(waypoints):
                self.logger.info(f"📍 Flying to waypoint {i+1}: {waypoint}")
                
                # Use AirSim's moveToPositionAsync for waypoint navigation
                await asyncio.wait_for(
                    asyncio.create_task(
                        asyncio.to_thread(
                            client.moveToPositionAsync,
                            float(waypoint[0]),
                            float(waypoint[1]), 
                            float(waypoint[2]),
                            5.0,  # velocity in m/s
                            drivetrain=self.config.drivetrain_type,
                            yaw_mode=self.config.yaw_mode,
                            vehicle_name=self.config.vehicle_name
                        )
                    ),
                    timeout=self.config.safety_eval_timeout
                )
            
            self.logger.info("✅ Mission completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Mission failed: {e}")
            return False

    async def pause(self) -> bool:
        """
        Pause the current mission
        
        Returns:
            True if paused successfully, False otherwise
        """
        client = self.connection.get_client()
        if not client:
            self.logger.error("❌ Not connected to AirSim")
            return False
        
        try:
            self.logger.info("⏸️ Pausing mission")
            # For now, just hover in place
            await asyncio.wait_for(
                asyncio.create_task(
                    asyncio.to_thread(
                        client.hoverAsync,
                        vehicle_name=self.config.vehicle_name
                    )
                ),
                timeout=self.config.safety_eval_timeout
            )
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to pause mission: {e}")
            return False

    async def resume(self) -> bool:
        """
        Resume the paused mission
        
        Returns:
            True if resumed successfully, False otherwise
        """
        client = self.connection.get_client()
        if not client:
            self.logger.error("❌ Not connected to AirSim")
            return False
        
        try:
            self.logger.info("▶️ Resuming mission")
            # Mission resumption logic would go here
            # For now, just return success
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to resume mission: {e}")
            return False


# Type aliases for clarity
AirSimState = airsim.MultirotorState
AirSimClient = airsim.MultirotorClient
