"""
Input Validation System for DART-Planner

Provides comprehensive validation for user inputs, trajectory data,
control commands, and sensor data to prevent injection attacks and
ensure system safety.
"""

import re
import math
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

import numpy as np

# This import is causing a circular dependency.
# from security.auth import UserSession, AuthLevel


class ValidationError(Exception):
    """Custom exception for input validation failures"""
    def __init__(self, message: str, field: str = "", value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(f"Validation error in {field}: {message}")


class InputType(Enum):
    """Supported input types for validation"""
    COORDINATE = "coordinate"
    WAYPOINT = "waypoint"
    TRAJECTORY = "trajectory"
    VELOCITY = "velocity"
    ACCELERATION = "acceleration"
    ATTITUDE = "attitude"
    CONTROL_COMMAND = "control_command"
    SENSOR_DATA = "sensor_data"
    MISSION_PARAM = "mission_param"


@dataclass
class ValidationRule:
    """Single validation rule definition"""
    field_name: str
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    custom_validator: Optional[Callable] = None
    error_message: str = ""


@dataclass
class SafetyLimits:
    """Safety limits for drone operations"""
    # Spatial limits (meters)
    max_altitude: float = 120.0  # AGL limit
    min_altitude: float = 0.5    # Ground clearance
    max_range: float = 1000.0    # Max distance from home
    
    # Velocity limits (m/s)
    max_horizontal_velocity: float = 15.0
    max_vertical_velocity: float = 10.0
    max_angular_velocity: float = math.radians(180)  # rad/s
    
    # Acceleration limits (m/s²)
    max_horizontal_acceleration: float = 5.0
    max_vertical_acceleration: float = 3.0
    
    # Attitude limits (radians)
    max_roll: float = math.radians(45)
    max_pitch: float = math.radians(45)
    max_yaw_rate: float = math.radians(90)
    
    # Mission limits
    max_waypoints: int = 100
    max_mission_duration: float = 3600.0  # seconds
    
    # Geofencing (can be updated dynamically)
    geofence_center: Tuple[float, float] = (0.0, 0.0)  # lat, lon
    geofence_radius: float = 500.0  # meters


class InputValidator:
    """
    Validates and sanitizes all external inputs to the DART system.
    """
    def __init__(self, safety_limits: Optional[SafetyLimits] = None):
        if safety_limits:
            self.limits = safety_limits
        else:
            # Load from central config
            from src.config import get_safety_limits  # local import to avoid cycles

            cfg_limits = get_safety_limits()
            if cfg_limits:
                self.limits = SafetyLimits(**cfg_limits)
            else:
                self.limits = SafetyLimits()
        self.validation_rules = self._create_validation_rules()
        
        # Regex patterns for common validations - OPTIMIZED: Pre-compile patterns
        self._pattern_strings = {
            'coordinate': r'^[-+]?([0-9]*\.?[0-9]+)$',
            'identifier': r'^[a-zA-Z][a-zA-Z0-9_-]{0,63}$',
            'filename': r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,255}$',
            'ipv4': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
            'safe_string': r'^[a-zA-Z0-9\s._-]{1,256}$'
        }
        
        # OPTIMIZATION: Cache compiled regex patterns for better performance
        self._compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE if name in ['identifier', 'filename'] else 0)
            for name, pattern in self._pattern_strings.items()
        }
        
        # OPTIMIZATION: Cache SQL injection patterns as compiled regex
        self._sql_injection_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in [
                r'\bunion\b', r'\bselect\b', r'\binsert\b', r'\bupdate\b', 
                r'\bdelete\b', r'\bdrop\b', r'\bcreate\b', r'\balter\b', 
                r'\bexec\b', r'\bexecute\b', r'--', r';', r'/\*', r'\*/'
            ]
        ]
        
        # OPTIMIZATION: Cache dangerous characters as set for O(1) lookup
        self._dangerous_chars = {'<', '>', '"', "'", '&', '\x00', '\n', '\r', '\t'}
    
    def _create_validation_rules(self) -> Dict[str, List[ValidationRule]]:
        """Create validation rules for different input types"""
        return {
            InputType.COORDINATE.value: [
                ValidationRule("x", min_value=-self.limits.max_range, 
                             max_value=self.limits.max_range),
                ValidationRule("y", min_value=-self.limits.max_range, 
                             max_value=self.limits.max_range),
                ValidationRule("z", min_value=self.limits.min_altitude, 
                             max_value=self.limits.max_altitude)
            ],
            InputType.VELOCITY.value: [
                ValidationRule("vx", min_value=-self.limits.max_horizontal_velocity,
                             max_value=self.limits.max_horizontal_velocity),
                ValidationRule("vy", min_value=-self.limits.max_horizontal_velocity,
                             max_value=self.limits.max_horizontal_velocity),
                ValidationRule("vz", min_value=-self.limits.max_vertical_velocity,
                             max_value=self.limits.max_vertical_velocity)
            ],
            InputType.ATTITUDE.value: [
                ValidationRule("roll", min_value=-self.limits.max_roll,
                             max_value=self.limits.max_roll),
                ValidationRule("pitch", min_value=-self.limits.max_pitch,
                             max_value=self.limits.max_pitch),
                ValidationRule("yaw", min_value=-math.pi, max_value=math.pi)
            ]
        }
    
    def validate_coordinate(self, coord: Dict[str, float], 
                          coord_type: str = "position") -> Dict[str, float]:
        """
        Validate 3D coordinate data
        
        Args:
            coord: Dictionary with x, y, z coordinates
            coord_type: Type of coordinate (position, velocity, etc.)
            
        Returns:
            Validated and sanitized coordinate dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(coord, dict):
            raise ValidationError("Coordinate must be a dictionary", "coordinate")
        
        required_fields = ['x', 'y', 'z']
        validated_coord = {}
        
        for field in required_fields:
            if field not in coord:
                raise ValidationError(f"Missing required field: {field}", field)
            
            value = coord[field]
            
            # Type validation
            if not isinstance(value, (int, float)):
                raise ValidationError(f"Field must be numeric", field, value)
            
            # Range validation based on coordinate type
            if coord_type == "position":
                if field in ['x', 'y']:
                    if abs(value) > self.limits.max_range:
                        raise ValidationError(
                            f"Coordinate exceeds safety range: {self.limits.max_range}m",
                            field, value
                        )
                elif field == 'z':
                    if value < self.limits.min_altitude or value > self.limits.max_altitude:
                        raise ValidationError(
                            f"Altitude outside safe range: {self.limits.min_altitude}-{self.limits.max_altitude}m",
                            field, value
                        )
            
            # Check for NaN/Inf
            if not math.isfinite(value):
                raise ValidationError("Coordinate contains invalid value (NaN/Inf)", field, value)
            
            validated_coord[field] = float(value)
        
        return validated_coord
    
    def validate_waypoint(self, waypoint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate waypoint data structure
        
        Args:
            waypoint: Waypoint dictionary with position, velocity, etc.
            
        Returns:
            Validated waypoint dictionary
        """
        if not isinstance(waypoint, dict):
            raise ValidationError("Waypoint must be a dictionary", "waypoint")
        
        validated_wp = {}
        
        # Validate position (required)
        if 'position' not in waypoint:
            raise ValidationError("Waypoint missing required position", "position")
        
        validated_wp['position'] = self.validate_coordinate(
            waypoint['position'], "position"
        )
        
        # Validate velocity (optional)
        if 'velocity' in waypoint:
            validated_wp['velocity'] = self.validate_coordinate(
                waypoint['velocity'], "velocity"
            )
            
            # Check velocity magnitude
            vel = validated_wp['velocity']
            h_vel = math.sqrt(vel['x']**2 + vel['y']**2)
            if h_vel > self.limits.max_horizontal_velocity:
                raise ValidationError(
                    f"Horizontal velocity exceeds limit: {self.limits.max_horizontal_velocity} m/s",
                    "velocity"
                )
        
        # Validate attitude (optional)
        if 'attitude' in waypoint:
            validated_wp['attitude'] = self.validate_attitude(waypoint['attitude'])
        
        # Validate timing (optional)
        if 'timestamp' in waypoint:
            timestamp = waypoint['timestamp']
            if not isinstance(timestamp, (int, float)) or timestamp < 0:
                raise ValidationError("Invalid timestamp", "timestamp", timestamp)
            validated_wp['timestamp'] = float(timestamp)
        
        # Validate waypoint ID (optional)
        if 'id' in waypoint:
            wp_id = waypoint['id']
            if not self._validate_string(wp_id, 'identifier'):
                raise ValidationError("Invalid waypoint ID format", "id", wp_id)
            validated_wp['id'] = str(wp_id)
        
        return validated_wp
    
    def validate_trajectory(self, trajectory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate complete trajectory
        
        Args:
            trajectory: List of waypoint dictionaries
            
        Returns:
            Validated trajectory list
        """
        if not isinstance(trajectory, list):
            raise ValidationError("Trajectory must be a list", "trajectory")
        
        if len(trajectory) == 0:
            raise ValidationError("Trajectory cannot be empty", "trajectory")
        
        if len(trajectory) > self.limits.max_waypoints:
            raise ValidationError(
                f"Trajectory exceeds maximum waypoints: {self.limits.max_waypoints}",
                "trajectory"
            )
        
        validated_trajectory = []
        
        for i, waypoint in enumerate(trajectory):
            try:
                validated_wp = self.validate_waypoint(waypoint)
                validated_trajectory.append(validated_wp)
            except ValidationError as e:
                raise ValidationError(f"Waypoint {i}: {e.message}", f"waypoint_{i}")
        
        # Validate trajectory continuity
        self._validate_trajectory_continuity(validated_trajectory)
        
        return validated_trajectory
    
    def validate_control_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate control command structure
        
        Args:
            command: Control command dictionary
            
        Returns:
            Validated control command
        """
        if not isinstance(command, dict):
            raise ValidationError("Control command must be a dictionary", "command")
        
        validated_cmd = {}
        
        # Validate command type
        if 'type' not in command:
            raise ValidationError("Control command missing type", "type")
        
        cmd_type = command['type']
        valid_types = ['position', 'velocity', 'attitude', 'emergency_stop', 'takeoff', 'land']
        
        if cmd_type not in valid_types:
            raise ValidationError(f"Invalid command type: {cmd_type}", "type")
        
        validated_cmd['type'] = cmd_type
        
        # Validate command-specific data
        if cmd_type in ['position', 'velocity']:
            if 'target' not in command:
                raise ValidationError(f"{cmd_type} command missing target", "target")
            
            validated_cmd['target'] = self.validate_coordinate(
                command['target'], cmd_type
            )
        
        elif cmd_type == 'attitude':
            if 'target' not in command:
                raise ValidationError("Attitude command missing target", "target")
            
            validated_cmd['target'] = self.validate_attitude(command['target'])
        
        # Validate timestamp
        if 'timestamp' in command:
            validated_cmd['timestamp'] = self._validate_timestamp(command['timestamp'])
        
        # Validate priority
        if 'priority' in command:
            priority = command['priority']
            if not isinstance(priority, int) or priority < 0 or priority > 10:
                raise ValidationError("Priority must be integer 0-10", "priority", priority)
            validated_cmd['priority'] = priority
        
        return validated_cmd
    
    def validate_attitude(self, attitude: Dict[str, float]) -> Dict[str, float]:
        """Validate attitude (roll, pitch, yaw) data"""
        if not isinstance(attitude, dict):
            raise ValidationError("Attitude must be a dictionary", "attitude")
        
        required_fields = ['roll', 'pitch', 'yaw']
        validated_attitude = {}
        
        for field in required_fields:
            if field not in attitude:
                raise ValidationError(f"Attitude missing {field}", field)
            
            value = attitude[field]
            
            if not isinstance(value, (int, float)):
                raise ValidationError(f"Attitude {field} must be numeric", field, value)
            
            if not math.isfinite(value):
                raise ValidationError(f"Attitude {field} contains invalid value", field, value)
            
            # Normalize angles and check limits
            normalized_value = self._normalize_angle(value)
            
            if field in ['roll', 'pitch']:
                limit = self.limits.max_roll if field == 'roll' else self.limits.max_pitch
                if abs(normalized_value) > limit:
                    raise ValidationError(
                        f"{field.capitalize()} exceeds safety limit: ±{math.degrees(limit)}°",
                        field, value
                    )
            
            validated_attitude[field] = normalized_value
        
        return validated_attitude
    
    def validate_sensor_data(self, sensor_data: Dict[str, Any], 
                           sensor_type: str) -> Dict[str, Any]:
        """Validate sensor data based on sensor type"""
        if not isinstance(sensor_data, dict):
            raise ValidationError("Sensor data must be a dictionary", "sensor_data")
        
        validated_data = {}
        
        if sensor_type == "imu":
            # Validate IMU data
            required_fields = ['accelerometer', 'gyroscope']
            for field in required_fields:
                if field not in sensor_data:
                    raise ValidationError(f"IMU data missing {field}", field)
                
                validated_data[field] = self.validate_coordinate(
                    sensor_data[field], field
                )
            
            # Optional magnetometer
            if 'magnetometer' in sensor_data:
                validated_data['magnetometer'] = self.validate_coordinate(
                    sensor_data['magnetometer'], "magnetometer"
                )
        
        elif sensor_type == "gps":
            # Validate GPS data
            required_fields = ['latitude', 'longitude', 'altitude']
            for field in required_fields:
                if field not in sensor_data:
                    raise ValidationError(f"GPS data missing {field}", field)
                
                value = sensor_data[field]
                if not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValidationError(f"Invalid GPS {field}", field, value)
                
                # Basic GPS coordinate validation
                if field == 'latitude' and (value < -90 or value > 90):
                    raise ValidationError("Latitude out of range [-90, 90]", field, value)
                elif field == 'longitude' and (value < -180 or value > 180):
                    raise ValidationError("Longitude out of range [-180, 180]", field, value)
                
                validated_data[field] = float(value)
        
        # Validate timestamp
        if 'timestamp' in sensor_data:
            validated_data['timestamp'] = self._validate_timestamp(sensor_data['timestamp'])
        
        return validated_data
    
    def _validate_trajectory_continuity(self, trajectory: List[Dict[str, Any]]) -> None:
        """Validate that trajectory is physically feasible"""
        if len(trajectory) < 2:
            return
        
        for i in range(1, len(trajectory)):
            prev_wp = trajectory[i-1]
            curr_wp = trajectory[i]
            
            # Calculate distance between waypoints
            prev_pos = prev_wp['position']
            curr_pos = curr_wp['position']
            
            distance = math.sqrt(
                (curr_pos['x'] - prev_pos['x'])**2 +
                (curr_pos['y'] - prev_pos['y'])**2 +
                (curr_pos['z'] - prev_pos['z'])**2
            )
            
            # Check if waypoints are too far apart (basic sanity check)
            max_segment_distance = 100.0  # meters
            if distance > max_segment_distance:
                raise ValidationError(
                    f"Waypoint segment too long: {distance:.1f}m > {max_segment_distance}m",
                    f"trajectory_segment_{i}"
                )
    
    def _validate_string(self, value: str, pattern_name: str) -> bool:
        """Validate string against regex pattern - OPTIMIZED with cached patterns"""
        if not isinstance(value, str):
            return False
        
        if pattern_name not in self._compiled_patterns:
            return False
        
        # OPTIMIZATION: Use pre-compiled pattern for better performance
        compiled_pattern = self._compiled_patterns[pattern_name]
        return compiled_pattern.match(value) is not None
    
    def _validate_timestamp(self, timestamp: Any) -> float:
        """Validate timestamp value"""
        if not isinstance(timestamp, (int, float)):
            raise ValidationError("Timestamp must be numeric", "timestamp", timestamp)
        
        if timestamp < 0:
            raise ValidationError("Timestamp cannot be negative", "timestamp", timestamp)
        
        if not math.isfinite(timestamp):
            raise ValidationError("Timestamp contains invalid value", "timestamp", timestamp)
        
        return float(timestamp)
    
    def _normalize_angle(self, angle: float) -> float:
        """Normalize angle to [-π, π] range"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    def sanitize_string_input(self, input_str: str) -> str:
        """
        Sanitize string input for safety - OPTIMIZED with cached patterns
        
        Args:
            input_str: Input string to sanitize
            
        Returns:
            Sanitized string
        """
        if not isinstance(input_str, str):
            raise ValidationError("Input must be a string", "string_input")
        
        # Truncate to max length
        sanitized = input_str
        
        # OPTIMIZATION: Use set for O(1) character lookup instead of list iteration
        sanitized = ''.join(char for char in sanitized if char not in self._dangerous_chars)
        
        # OPTIMIZATION: Use pre-compiled SQL injection patterns
        sanitized_lower = sanitized.lower()
        for pattern in self._sql_injection_patterns:
            if pattern.search(sanitized_lower):
                raise ValidationError(
                    f"Input contains potentially dangerous pattern: {pattern.pattern}",
                    "string_input"
                )
        
        return sanitized.strip()

    def validate_generic(self, data: dict) -> Dict[str, Any]:
        """Validate arbitrary JSON payloads - OPTIMIZED with cached patterns.

        The function attempts to infer the payload type based on its structure
        and then dispatches to the specialised validator. **It always returns a
        dictionary** so that callers can rely on a consistent type.

        Return structure:
            {"type": <str>, "payload": <validated_data>}

        Examples:
            • Trajectory payload → {"type": "trajectory", "payload": [<waypoints>]}  
            • Waypoint payload → {"type": "waypoint", "payload": {…}}  
            • Unknown payload  → {"type": "sanitised", "payload": {…}}
        """

        if not isinstance(data, dict):
            raise ValidationError("Top-level payload must be a JSON object.")

        # Trajectory: expects a list under 'waypoints'
        if "waypoints" in data and isinstance(data["waypoints"], list):
            # The payload for trajectory validation is the entire dictionary
            validated_traj = self.validate_trajectory(data["waypoints"])
            return {"type": "trajectory", "payload": validated_traj}

        # Single waypoint
        if {"position", "velocity"}.issubset(data.keys()):
            validated_wp = self.validate_waypoint(data)
            return {"type": "waypoint", "payload": validated_wp}

        # Low-level control command
        if {"thrust", "torque"}.issubset(data.keys()): # Corrected to check for 'torque' based on ControlCommand type
            validated_cmd = self.validate_control_command(data)
            return {"type": "control_command", "payload": validated_cmd}

        # Fallback – sanitise all string values - OPTIMIZED with cached patterns
        sanitised = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitised[key] = self.sanitize_string_input(value)
            else:
                sanitised[key] = value
        return {"type": "sanitised", "payload": sanitised}


# Convenience validation functions for common use cases

def validate_waypoint(waypoint_data: dict, safety_limits: Optional[SafetyLimits] = None) -> dict:
    """Convenience function to validate a single waypoint."""
    return InputValidator(safety_limits).validate_waypoint(waypoint_data)


def validate_trajectory(trajectory_data: List[Dict[str, Any]], safety_limits: Optional[SafetyLimits] = None) -> List[Dict[str, Any]]:
    """Convenience function to validate a full trajectory."""
    # This function now takes the list of waypoints directly.
    return InputValidator(safety_limits).validate_trajectory(trajectory_data)


def validate_control_command(command_data: dict, safety_limits: Optional[SafetyLimits] = None) -> dict:
    """Convenience function to validate a low-level control command."""
    return InputValidator(safety_limits).validate_control_command(command_data) 