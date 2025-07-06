"""
AirSim Interface for DART-Planner

This module provides a comprehensive interface to Microsoft AirSim for
drone simulation and hardware-in-the-loop testing.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field

import airsim
import numpy as np
import numpy.typing as npt

from common.types import DroneState, ControlCommand


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
    drivetrain_type: airsim.DrivetrainType = airsim.DrivetrainType.MaxDegreeOfFreedom
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
        self.client: Optional[airsim.MultirotorClient] = None
        self.connected: bool = False
        self.armed: bool = False
        self.api_control_enabled: bool = False
        
        # State tracking
        self._last_state: Optional[DroneState] = None
        self._last_command: Optional[ControlCommand] = None
        self._command_count: int = 0
        self._error_count: int = 0
        
        # Performance metrics
        self._control_frequency: float = 0.0
        self._last_control_time: float = 0.0
        self._control_times: List[float] = []
        
        # Safety monitoring
        self._safety_violations: int = 0
        self._last_safety_check: float = 0.0
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config.log_level)
        
        if self.config.enable_trace_logging:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    async def connect(self) -> bool:
        """
        Connect to AirSim simulator
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to AirSim at {self.config.ip}:{self.config.port}")
            
            self.client = airsim.MultirotorClient(
                ip=self.config.ip,
                port=self.config.port,
                timeout_value=self.config.timeout_value
            )
            
            # Test connection with ping
            self.client.ping()
            self.connected = True
            
            # Get initial state
            await self._initialize_vehicle()
            
            self.logger.info("✅ AirSim connection established")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to AirSim: {e}")
            self.connected = False
            return False
    
    async def _initialize_vehicle(self) -> None:
        """Initialize vehicle settings and API control"""
        if not self.client:
            raise RuntimeError("Client not connected")
        
        try:
            # Enable API control
            if self.config.enable_api_control:
                self.client.enableApiControl(True, self.config.vehicle_name)
                self.api_control_enabled = True
                self.logger.info("✅ API control enabled")
            
            # Arm the vehicle
            self.client.armDisarm(True, self.config.vehicle_name)
            self.armed = True
            self.logger.info("✅ Vehicle armed")
            
            # Reset vehicle to known state
            self.client.reset()
            await asyncio.sleep(0.1)  # Brief pause for state reset
            
            # Confirm initial state
            state = await self.get_state()
            self.logger.info(f"✅ Initial state: pos={state.position}, vel={state.velocity}")
            
        except Exception as e:
            self.logger.error(f"❌ Vehicle initialization failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Safely disconnect from AirSim"""
        try:
            if self.client and self.connected:
                # Land if still flying
                current_state = await self.get_state()
                if current_state.position[2] < -0.5:  # If above ground
                    await self.land()
                
                # Disable API control
                if self.api_control_enabled:
                    self.client.enableApiControl(False, self.config.vehicle_name)
                    self.api_control_enabled = False
                
                # Disarm
                if self.armed:
                    self.client.armDisarm(False, self.config.vehicle_name)
                    self.armed = False
                
                self.client = None
                self.connected = False
                
                self.logger.info("✅ AirSim disconnected safely")
                
        except Exception as e:
            self.logger.error(f"❌ Error during disconnect: {e}")
    
    async def get_state(self) -> DroneState:
        """
        Get current drone state from AirSim
        
        Returns:
            DroneState object with position, velocity, orientation, etc.
        """
        if not self.client or not self.connected:
            raise RuntimeError("Not connected to AirSim")
        
        try:
            # Get multirotor state
            state = self.client.getMultirotorState(self.config.vehicle_name)
            
            # Convert to NED coordinates (AirSim uses NED)
            position = np.array([
                state.kinematics_estimated.position.x_val,
                state.kinematics_estimated.position.y_val,
                state.kinematics_estimated.position.z_val
            ])
            
            velocity = np.array([
                state.kinematics_estimated.linear_velocity.x_val,
                state.kinematics_estimated.linear_velocity.y_val,
                state.kinematics_estimated.linear_velocity.z_val
            ])
            
            # Convert quaternion (w, x, y, z) to numpy array
            orientation = np.array([
                state.kinematics_estimated.orientation.w_val,
                state.kinematics_estimated.orientation.x_val,
                state.kinematics_estimated.orientation.y_val,
                state.kinematics_estimated.orientation.z_val
            ])
            
            angular_velocity = np.array([
                state.kinematics_estimated.angular_velocity.x_val,
                state.kinematics_estimated.angular_velocity.y_val,
                state.kinematics_estimated.angular_velocity.z_val
            ])
            
            # Create DroneState
            drone_state = DroneState(
                timestamp=time.time(),
                position=position,
                velocity=velocity,
                orientation=orientation,
                angular_velocity=angular_velocity
            )
            
            self._last_state = drone_state
            
            # Perform safety checks
            await self._safety_monitor(drone_state)
            
            return drone_state
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get state: {e}")
            self._error_count += 1
            
            # Return last known state if available
            if self._last_state:
                self.logger.warning("⚠️ Using last known state")
                return self._last_state
            
            raise RuntimeError(f"Failed to get drone state: {e}")
    
    async def send_control_command(self, command: ControlCommand) -> bool:
        """
        Send control command to AirSim
        
        Args:
            command: ControlCommand with thrust and torque
            
        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.client or not self.connected:
            self.logger.error("❌ Not connected to AirSim")
            return False
        
        if not self.api_control_enabled:
            self.logger.error("❌ API control not enabled")
            return False
        
        try:
            # Track control performance
            current_time = time.time()
            if self._last_control_time > 0:
                dt = current_time - self._last_control_time
                self._control_times.append(dt)
                
                # Calculate frequency over last 50 commands
                if len(self._control_times) > 50:
                    self._control_times.pop(0)
                    self._control_frequency = 1.0 / np.mean(self._control_times)
            
            self._last_control_time = current_time
            
            # Convert DART control command to AirSim format
            # Note: AirSim uses body frame torques (roll, pitch, yaw moments)
            await self._send_thrust_torque_command(command.thrust, command.torque)
            
            self._last_command = command
            self._command_count += 1
            
            if self.config.enable_trace_logging:
                self.logger.debug(
                    f"Control command sent: thrust={command.thrust:.3f}, "
                    f"torque=[{command.torque[0]:.3f}, {command.torque[1]:.3f}, {command.torque[2]:.3f}]"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send control command: {e}")
            self._error_count += 1
            return False
    
    async def _send_thrust_torque_command(self, thrust: float, torque: npt.NDArray[np.float64]) -> None:
        """
        Send thrust and torque command to AirSim using moveByMotorPWMsAsync
        
        Args:
            thrust: Thrust magnitude in Newtons
            torque: Torque vector [roll, pitch, yaw] in N⋅m
        """
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
                    self.client.moveByMotorPWMsAsync,
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
    
    async def _safety_monitor(self, state: DroneState) -> None:
        """
        Monitor safety conditions and trigger failsafes if needed
        
        Args:
            state: Current drone state
        """
        current_time = time.time()
        
        # Check velocity limits
        velocity_mag = np.linalg.norm(state.velocity)
        if velocity_mag > self.config.max_velocity:
            self._safety_violations += 1
            self.logger.warning(
                f"⚠️ Velocity limit exceeded: {velocity_mag:.2f} > {self.config.max_velocity:.2f} m/s"
            )
        
        # Check altitude (negative Z in NED)
        altitude = -state.position[2]
        if altitude < -1.0:  # Below ground
            self._safety_violations += 1
            self.logger.warning(f"⚠️ Below ground level: altitude={altitude:.2f}m")
        
        if altitude > 100.0:  # Too high
            self._safety_violations += 1
            self.logger.warning(f"⚠️ Altitude too high: {altitude:.2f}m")
        
        # Check for excessive safety violations
        if self._safety_violations > 10:
            self.logger.error("❌ Too many safety violations - initiating emergency landing")
            await self.emergency_land()
        
        self._last_safety_check = current_time
    
    async def takeoff(self, altitude: float = 2.0) -> bool:
        """
        Takeoff to specified altitude
        
        Args:
            altitude: Target altitude in meters (positive up)
            
        Returns:
            True if takeoff successful, False otherwise
        """
        try:
            self.logger.info(f"🚁 Taking off to {altitude}m altitude")
            
            # Use AirSim's takeoff command
            await asyncio.wait_for(
                asyncio.create_task(
                    asyncio.to_thread(
                        self.client.takeoffAsync,
                        timeout_sec=20.0,
                        vehicle_name=self.config.vehicle_name
                    )
                ),
                timeout=25.0
            )
            
            # Move to desired altitude
            await asyncio.wait_for(
                asyncio.create_task(
                    asyncio.to_thread(
                        self.client.moveToZAsync,
                        -altitude,  # Negative because NED coordinates
                        velocity=2.0,
                        timeout_sec=10.0,
                        vehicle_name=self.config.vehicle_name
                    )
                ),
                timeout=15.0
            )
            
            # Verify we reached target altitude
            state = await self.get_state()
            actual_altitude = -state.position[2]
            
            if abs(actual_altitude - altitude) < 0.5:
                self.logger.info(f"✅ Takeoff successful: {actual_altitude:.2f}m")
                return True
            else:
                self.logger.warning(f"⚠️ Takeoff altitude error: {actual_altitude:.2f}m vs {altitude:.2f}m target")
                return False
                
        except asyncio.TimeoutError:
            self.logger.error("❌ Takeoff timeout")
            return False
        except Exception as e:
            self.logger.error(f"❌ Takeoff failed: {e}")
            return False
    
    async def land(self) -> bool:
        """
        Land the drone safely
        
        Returns:
            True if landing successful, False otherwise
        """
        try:
            self.logger.info("🛬 Landing...")
            
            await asyncio.wait_for(
                asyncio.create_task(
                    asyncio.to_thread(
                        self.client.landAsync,
                        timeout_sec=15.0,
                        vehicle_name=self.config.vehicle_name
                    )
                ),
                timeout=20.0
            )
            
            # Wait for landing to complete
            await asyncio.sleep(2.0)
            
            state = await self.get_state()
            altitude = -state.position[2]
            
            if altitude < 0.3:  # Close to ground
                self.logger.info("✅ Landing successful")
                return True
            else:
                self.logger.warning(f"⚠️ Landing incomplete: altitude={altitude:.2f}m")
                return False
                
        except asyncio.TimeoutError:
            self.logger.error("❌ Landing timeout")
            return False
        except Exception as e:
            self.logger.error(f"❌ Landing failed: {e}")
            return False
    
    async def emergency_land(self) -> None:
        """Emergency landing procedure"""
        self.logger.error("🚨 EMERGENCY LANDING INITIATED")
        
        try:
            # Disable API control to let AirSim's safety systems take over
            if self.api_control_enabled:
                self.client.enableApiControl(False, self.config.vehicle_name)
                self.api_control_enabled = False
            
            # Force landing
            await self.land()
            
        except Exception as e:
            self.logger.error(f"❌ Emergency landing failed: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the interface
        
        Returns:
            Dictionary containing performance metrics
        """
        return {
            "connected": self.connected,
            "commands_sent": self._command_count,
            "errors": self._error_count,
            "control_frequency_hz": self._control_frequency,
            "safety_violations": self._safety_violations,
            "api_control_enabled": self.api_control_enabled,
            "armed": self.armed,
            "last_command": {
                "thrust": self._last_command.thrust if self._last_command else None,
                "torque": self._last_command.torque.tolist() if self._last_command else None
            } if self._last_command else None,
            "last_state": {
                "position": self._last_state.position.tolist() if self._last_state else None,
                "velocity": self._last_state.velocity.tolist() if self._last_state else None
            } if self._last_state else None
        }
    
    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self._command_count = 0
        self._error_count = 0
        self._safety_violations = 0
        self._control_times.clear()
        self._control_frequency = 0.0


# Type aliases for clarity
AirSimState = airsim.MultirotorState
AirSimClient = airsim.MultirotorClient
