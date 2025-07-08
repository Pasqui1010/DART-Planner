"""
Secure Hardware Interface for DART-Planner

Provides secure communication with drone hardware including MAVLink,
AirSim, and other interfaces with authentication and input validation.
"""

import time
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from enum import Enum

import numpy as np

# Import security components
import sys
import os
from security import (
    AuthManager, AuthLevel, ValidationError,
    InputValidator, SecureCredentialManager,
    validate_control_command
)

# Hardware interface imports
from dart_planner.hardware.connection import ConnectionManager
from dart_planner.hardware.safety import SafetyMonitor
from dart_planner.hardware.state import StateEstimator


class HardwareInterfaceError(Exception):
    """Custom exception for hardware interface errors"""
    pass


class ConnectionState(Enum):
    """Hardware connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


@dataclass
class HardwareCommand:
    """Validated hardware command structure"""
    command_type: str
    parameters: Dict[str, Any]
    timestamp: float
    user_id: str
    auth_level: str
    priority: int = 5


class SecureHardwareInterface:
    """
    Secure hardware interface with authentication and validation
    
    Provides secure communication with drone hardware while validating
    all inputs and maintaining audit logs of commands for safety.
    """
    
    def __init__(self, interface_type: str = "mavlink", 
                 credential_manager: Optional[SecureCredentialManager] = None):
        self.interface_type = interface_type
        self.connection_state = ConnectionState.DISCONNECTED
        
        # Security components
        self.credential_manager = credential_manager or SecureCredentialManager()
        self.input_validator = InputValidator()
        self.auth_manager = AuthManager()
        
        # Hardware components
        self.connection_manager = ConnectionManager(interface_type)
        self.safety_monitor = SafetyMonitor()
        self.state_estimator = StateEstimator()
        
        # Command logging for audit trail
        self.command_log: List[HardwareCommand] = []
        self.max_log_size = 1000
        
        # Safety limits
        self.safety_enabled = True
        self.emergency_stop_engaged = False
        
        # Setup logging
        self.logger = logging.getLogger(f"SecureHardwareInterface.{interface_type}")
        
    def authenticate_hardware_connection(self, user_session) -> bool:
        """
        Authenticate hardware connection using stored credentials
        
        Args:
            user_session: Authenticated user session
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            if not user_session:
                self.logger.error("No user session provided for hardware authentication")
                return False
            
            # Check permission for hardware access
            if not self.auth_manager.check_permission(user_session, "sensor_access"):
                self.logger.error(f"User {user_session.user_id} lacks hardware access permission")
                return False
            
            # Get hardware credentials
            connection_string = self.credential_manager.get_credential(f"{self.interface_type}_connection")
            if not connection_string:
                self.logger.error(f"No connection credentials found for {self.interface_type}")
                return False
            
            # Attempt hardware connection
            self.connection_state = ConnectionState.CONNECTING
            success = self.connection_manager.connect(connection_string)
            
            if success:
                self.connection_state = ConnectionState.AUTHENTICATED
                self.logger.info(f"Hardware authentication successful for user {user_session.user_id}")
                return True
            else:
                self.connection_state = ConnectionState.ERROR
                self.logger.error("Hardware connection failed")
                return False
                
        except Exception as e:
            self.connection_state = ConnectionState.ERROR
            self.logger.error(f"Hardware authentication error: {e}")
            return False
    
    def send_secure_command(self, command_data: Dict[str, Any], 
                           user_session) -> bool:
        """
        Send validated command to hardware with security checks
        
        Args:
            command_data: Command data dictionary
            user_session: Authenticated user session
            
        Returns:
            True if command sent successfully, False otherwise
        """
        try:
            # Verify connection state
            if self.connection_state != ConnectionState.AUTHENTICATED:
                from dart_planner.common.errors import HardwareError
                raise HardwareError("Hardware not authenticated")
            
            # Emergency stop check
            if self.emergency_stop_engaged:
                self.logger.warning("Emergency stop engaged - command rejected")
                return False
            
            # Validate command structure
            validated_command = validate_control_command(command_data)
            
            # Check user permissions based on command type
            required_permission = self._get_required_permission(validated_command["type"])
            if not self.auth_manager.check_permission(user_session, required_permission):
                from dart_planner.common.errors import HardwareError
                raise HardwareError(
                    f"User {user_session.user_id} lacks permission: {required_permission}"
                )
            
            # Safety checks
            if self.safety_enabled:
                safety_result = self.safety_monitor.validate_command(validated_command)
                if not safety_result.is_safe:
                    from dart_planner.common.errors import HardwareError
                    raise HardwareError(f"Safety violation: {safety_result.reason}")
            
            # Create hardware command
            hw_command = HardwareCommand(
                command_type=validated_command["type"],
                parameters=validated_command,
                timestamp=time.time(),
                user_id=user_session.user_id,
                auth_level=user_session.auth_level.value,
                priority=validated_command.get("priority", 5)
            )
            
            # Send command to hardware
            success = self.connection_manager.send_command(hw_command)
            
            if success:
                # Log successful command
                self._log_command(hw_command, "SENT")
                self.logger.info(f"Command {hw_command.command_type} sent successfully")
                return True
            else:
                self._log_command(hw_command, "FAILED")
                self.logger.error(f"Failed to send command {hw_command.command_type}")
                return False
                
        except ValidationError as e:
            self.logger.error(f"Command validation failed: {e.message}")
            return False
        except HardwareInterfaceError as e:
            self.logger.error(f"Hardware interface error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending command: {e}")
            return False
    
    def get_secure_telemetry(self, user_session) -> Optional[Dict[str, Any]]:
        """
        Get telemetry data with user permission checks
        
        Args:
            user_session: Authenticated user session
            
        Returns:
            Telemetry data dictionary or None if access denied
        """
        try:
            # Check sensor access permission
            if not self.auth_manager.check_permission(user_session, "sensor_access"):
                self.logger.warning(f"User {user_session.user_id} denied telemetry access")
                return None
            
            # Get raw telemetry from hardware
            raw_telemetry = self.connection_manager.get_telemetry()
            if not raw_telemetry:
                return None
            
            # Validate and sanitize telemetry data
            validated_telemetry = self._validate_telemetry(raw_telemetry)
            
            # Add metadata
            validated_telemetry.update({
                "timestamp": time.time(),
                "interface_type": self.interface_type,
                "connection_state": self.connection_state.value,
                "user_id": user_session.user_id
            })
            
            return validated_telemetry
            
        except Exception as e:
            self.logger.error(f"Error getting telemetry: {e}")
            return None
    
    def emergency_stop(self, user_session) -> bool:
        """
        Engage emergency stop with immediate effect
        
        Args:
            user_session: Authenticated user session
            
        Returns:
            True if emergency stop engaged successfully
        """
        try:
            # Emergency stop can be triggered by any authenticated user
            if not user_session:
                self.logger.error("Unauthenticated emergency stop attempt")
                return False
            
            self.emergency_stop_engaged = True
            
            # Send emergency stop command to hardware
            emergency_command = {
                "type": "emergency_stop",
                "timestamp": time.time(),
                "priority": 10  # Highest priority
            }
            
            success = self.connection_manager.send_emergency_stop()
            
            # Log emergency stop
            hw_command = HardwareCommand(
                command_type="emergency_stop",
                parameters=emergency_command,
                timestamp=time.time(),
                user_id=user_session.user_id,
                auth_level=user_session.auth_level.value,
                priority=10
            )
            
            self._log_command(hw_command, "EMERGENCY_STOP")
            
            if success:
                self.logger.critical(f"Emergency stop engaged by user {user_session.user_id}")
                return True
            else:
                self.logger.critical("Emergency stop command failed!")
                return False
                
        except Exception as e:
            self.logger.critical(f"Emergency stop error: {e}")
            return False
    
    def disengage_emergency_stop(self, user_session) -> bool:
        """
        Disengage emergency stop (requires PILOT level access)
        
        Args:
            user_session: Authenticated user session
            
        Returns:
            True if emergency stop disengaged successfully
        """
        try:
            # Only PILOT or ADMIN can disengage emergency stop
            if user_session.auth_level not in [AuthLevel.PILOT, AuthLevel.ADMIN]:
                self.logger.error(f"User {user_session.user_id} cannot disengage emergency stop")
                return False
            
            self.emergency_stop_engaged = False
            
            # Send disengage command to hardware
            success = self.connection_manager.disengage_emergency_stop()
            
            # Log disengage action
            hw_command = HardwareCommand(
                command_type="disengage_emergency_stop",
                parameters={"timestamp": time.time()},
                timestamp=time.time(),
                user_id=user_session.user_id,
                auth_level=user_session.auth_level.value,
                priority=10
            )
            
            self._log_command(hw_command, "EMERGENCY_DISENGAGE")
            
            if success:
                self.logger.warning(f"Emergency stop disengaged by {user_session.user_id}")
                return True
            else:
                self.logger.error("Failed to disengage emergency stop")
                return False
                
        except Exception as e:
            self.logger.error(f"Error disengaging emergency stop: {e}")
            return False
    
    def get_command_audit_log(self, user_session, 
                             limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        Get command audit log (requires ADMIN access)
        
        Args:
            user_session: Authenticated user session
            limit: Maximum number of log entries to return
            
        Returns:
            List of command log entries or None if access denied
        """
        try:
            # Only ADMIN can access audit logs
            if user_session.auth_level != AuthLevel.ADMIN:
                self.logger.warning(f"User {user_session.user_id} denied audit log access")
                return None
            
            # Return recent commands
            recent_commands = self.command_log[-limit:]
            
            # Convert to serializable format
            log_entries = []
            for cmd in recent_commands:
                log_entries.append({
                    "command_type": cmd.command_type,
                    "timestamp": cmd.timestamp,
                    "user_id": cmd.user_id,
                    "auth_level": cmd.auth_level,
                    "priority": cmd.priority,
                    "parameters": cmd.parameters
                })
            
            return log_entries
            
        except Exception as e:
            self.logger.error(f"Error getting audit log: {e}")
            return None
    
    def _get_required_permission(self, command_type: str) -> str:
        """Map command types to required permissions"""
        permission_map = {
            "takeoff": "flight_control",
            "land": "flight_control", 
            "position": "flight_control",
            "velocity": "flight_control",
            "attitude": "flight_control",
            "arm": "flight_control",
            "disarm": "flight_control",
            "emergency_stop": "emergency_stop",  # Available to all authenticated users
            "set_mode": "flight_control",
            "upload_mission": "mission_planning",
            "start_mission": "flight_control",
            "pause_mission": "flight_control"
        }
        
        return permission_map.get(command_type, "flight_control")
    
    def _validate_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize telemetry data"""
        validated = {}
        
        # Validate position data if present
        if "position" in telemetry:
            try:
                validated["position"] = self.input_validator.validate_coordinate(
                    telemetry["position"], "position"
                )
            except ValidationError:
                self.logger.warning("Invalid position data in telemetry")
        
        # Validate velocity data if present
        if "velocity" in telemetry:
            try:
                validated["velocity"] = self.input_validator.validate_coordinate(
                    telemetry["velocity"], "velocity"
                )
            except ValidationError:
                self.logger.warning("Invalid velocity data in telemetry")
        
        # Validate attitude data if present
        if "attitude" in telemetry:
            try:
                validated["attitude"] = self.input_validator.validate_attitude(
                    telemetry["attitude"]
                )
            except ValidationError:
                self.logger.warning("Invalid attitude data in telemetry")
        
        # Copy other safe fields
        safe_fields = [
            "battery_voltage", "battery_remaining", "gps_fix", "gps_satellites",
            "armed", "mode", "system_status", "heading", "airspeed", "groundspeed"
        ]
        
        for field in safe_fields:
            if field in telemetry:
                # Basic type checking
                if isinstance(telemetry[field], (int, float, str, bool)):
                    validated[field] = telemetry[field]
        
        return validated
    
    def _log_command(self, command: HardwareCommand, status: str) -> None:
        """Log command with status for audit trail"""
        # Add status to command copy
        log_entry = {
            "command": command,
            "status": status,
            "logged_at": time.time()
        }
        
        self.command_log.append(log_entry)
        
        # Maintain log size limit
        if len(self.command_log) > self.max_log_size:
            self.command_log = self.command_log[-self.max_log_size//2:]
    
    def disconnect(self) -> bool:
        """Safely disconnect from hardware"""
        try:
            success = self.connection_manager.disconnect()
            if success:
                self.connection_state = ConnectionState.DISCONNECTED
                self.logger.info("Hardware interface disconnected safely")
            return success
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
            return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and health metrics"""
        return {
            "interface_type": self.interface_type,
            "connection_state": self.connection_state.value,
            "emergency_stop_engaged": self.emergency_stop_engaged,
            "safety_enabled": self.safety_enabled,
            "command_log_size": len(self.command_log),
            "connection_health": self.connection_manager.get_health_status(),
            "last_telemetry": self.connection_manager.get_last_telemetry_time()
        }


# Factory function for creating secure hardware interfaces
def create_secure_interface(interface_type: str, 
                          credential_manager: Optional[SecureCredentialManager] = None,
                          auth_manager: Optional[AuthManager] = None) -> SecureHardwareInterface:
    """
    Factory function to create secure hardware interfaces
    
    Args:
        interface_type: Type of hardware interface (mavlink, airsim, etc.)
        credential_manager: Optional credential manager instance
        auth_manager: Optional authentication manager instance
        
    Returns:
        Configured SecureHardwareInterface instance
    """
    interface = SecureHardwareInterface(interface_type, credential_manager)
    
    if auth_manager:
        interface.auth_manager = auth_manager
    
    # Setup interface-specific configurations
    if interface_type == "mavlink":
        # MAVLink specific setup
        interface.connection_manager.set_protocol_params({
            "baudrate": 57600,
            "timeout": 5.0,
            "heartbeat_interval": 1.0
        })
    elif interface_type == "airsim":
        # AirSim specific setup
        interface.connection_manager.set_protocol_params({
            "ip": "127.0.0.1",
            "port": 41451,
            "timeout": 10.0
        })
    
    return interface 
