"""
Airframe configuration management for DART-Planner.

This module handles loading and managing airframe-specific parameters
from the airframes.yaml configuration file.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
import numpy as np

# Define project root (assuming this file is in dart_planner/config/)
project_root = Path(__file__).parent.parent.parent


@dataclass
class AirframeConfig:
    """Configuration for a specific airframe."""
    
    # Basic information
    name: str
    type: str  # quadcopter, hexacopter, fixed_wing, vtol
    
    # Physical parameters
    mass: float  # kg
    arm_length: Optional[float] = None  # m (for multirotors)
    propeller_diameter: Optional[float] = None  # m (for multirotors)
    wingspan: Optional[float] = None  # m (for fixed-wing)
    wing_area: Optional[float] = None  # m² (for fixed-wing)
    
    # Motor and propeller limits
    max_thrust: float = 15.0  # N per motor
    max_rpm: float = 8000.0  # RPM
    max_power: float = 200.0  # W per motor
    max_vertical_thrust: Optional[float] = None  # N (for VTOL)
    max_horizontal_thrust: Optional[float] = None  # N (for VTOL)
    
    # Flight envelope
    max_velocity: float = 15.0  # m/s
    min_velocity: Optional[float] = None  # m/s (for fixed-wing)
    max_acceleration: float = 8.0  # m/s²
    max_angular_velocity: float = 3.0  # rad/s
    max_angular_acceleration: float = 6.0  # rad/s²
    
    # Safety limits
    max_altitude: float = 120.0  # m
    min_altitude: float = 0.5  # m
    max_distance: float = 1000.0  # m
    
    # Control parameters
    control_frequency: float = 100.0  # Hz
    position_kp: Union[List[float], np.ndarray] = field(default_factory=lambda: [2.0, 2.0, 2.0])
    velocity_kp: Union[List[float], np.ndarray] = field(default_factory=lambda: [1.5, 1.5, 1.5])
    attitude_kp: Union[List[float], np.ndarray] = field(default_factory=lambda: [8.0, 8.0, 8.0])
    attitude_kd: Union[List[float], np.ndarray] = field(default_factory=lambda: [2.0, 2.0, 2.0])
    
    # Communication and safety parameters
    heartbeat_interval_ms: int = 100  # ms
    heartbeat_timeout_ms: int = 500  # ms - centralized timeout for all components
    mavlink_heartbeat_timeout_s: float = 5.0  # seconds - for MAVLink compatibility
    
    def __post_init__(self):
        """Convert lists to numpy arrays for easier computation."""
        if isinstance(self.position_kp, list):
            self.position_kp = np.array(self.position_kp)
        if isinstance(self.velocity_kp, list):
            self.velocity_kp = np.array(self.velocity_kp)
        if isinstance(self.attitude_kp, list):
            self.attitude_kp = np.array(self.attitude_kp)
        if isinstance(self.attitude_kd, list):
            self.attitude_kd = np.array(self.attitude_kd)
    
    def get_total_thrust(self) -> float:
        """Get total maximum thrust based on airframe type."""
        if self.type == "quadcopter":
            return self.max_thrust * 4
        elif self.type == "hexacopter":
            return self.max_thrust * 6
        elif self.type == "fixed_wing":
            return self.max_thrust
        elif self.type == "vtol":
            return self.max_vertical_thrust or (self.max_thrust * 4)
        else:
            return self.max_thrust * 4  # Default to quadcopter
    
    def get_thrust_to_weight_ratio(self) -> float:
        """Calculate thrust-to-weight ratio."""
        total_thrust = self.get_total_thrust()
        weight = self.mass * 9.81  # N
        return total_thrust / weight
    
    def validate_config(self) -> List[str]:
        """Validate the airframe configuration and return any issues."""
        issues = []
        
        # Check basic parameters
        if self.mass <= 0:
            issues.append("Mass must be positive")
        
        if self.max_velocity <= 0:
            issues.append("Max velocity must be positive")
        
        if self.max_acceleration <= 0:
            issues.append("Max acceleration must be positive")
        
        # Check thrust-to-weight ratio
        ttw_ratio = self.get_thrust_to_weight_ratio()
        if ttw_ratio < 1.2:
            issues.append(f"Thrust-to-weight ratio too low: {ttw_ratio:.2f} (should be >= 1.2)")
        elif ttw_ratio > 10.0:
            issues.append(f"Thrust-to-weight ratio too high: {ttw_ratio:.2f} (should be <= 10.0)")
        
        # Type-specific checks
        if self.type in ["quadcopter", "hexacopter"]:
            if not self.arm_length or self.arm_length <= 0:
                issues.append("Arm length must be positive for multirotors")
            if not self.propeller_diameter or self.propeller_diameter <= 0:
                issues.append("Propeller diameter must be positive for multirotors")
        
        elif self.type == "fixed_wing":
            if not self.wingspan or self.wingspan <= 0:
                issues.append("Wingspan must be positive for fixed-wing")
            if not self.wing_area or self.wing_area <= 0:
                issues.append("Wing area must be positive for fixed-wing")
            if not self.min_velocity or self.min_velocity <= 0:
                issues.append("Min velocity (stall speed) must be positive for fixed-wing")
        
        elif self.type == "vtol":
            if not self.max_vertical_thrust or self.max_vertical_thrust <= 0:
                issues.append("Max vertical thrust must be positive for VTOL")
            if not self.max_horizontal_thrust or self.max_horizontal_thrust <= 0:
                issues.append("Max horizontal thrust must be positive for VTOL")
        
        return issues


class AirframeConfigManager:
    """Manager for loading and accessing airframe configurations."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize the airframe config manager."""
        if config_path is None:
            # Default to config/airframes.yaml relative to project root
            config_path = project_root / "config" / "airframes.yaml"
        
        self.config_path = Path(config_path)
        self._configs: Dict[str, AirframeConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load all airframe configurations from the YAML file."""
        if not self.config_path.exists():
            # Create a default config if file doesn't exist
            default_config = self._create_config('default', {})
            self._configs['default'] = default_config
            return
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Ensure data is a dictionary
        if not isinstance(data, dict):
            # Create a default config if data is not a dictionary
            default_config = self._create_config('default', {})
            self._configs['default'] = default_config
            return
        
        # Load default config first
        if 'default' in data:
            default_config = self._create_config('default', data['default'])
            self._configs['default'] = default_config
        
        # Load other configs
        for name, config_data in data.items():
            if name == 'default':
                continue
            
            # Ensure config_data is a dictionary
            if not isinstance(config_data, dict):
                continue
            
            # Handle inheritance
            if 'extends' in config_data:
                base_name = config_data['extends']
                if base_name not in self._configs:
                    from dart_planner.common.errors import ConfigurationError
                    raise ConfigurationError(f"Base config '{base_name}' not found for '{name}'")
                
                base_config = self._configs[base_name]
                # Merge base config with current config
                merged_data = self._merge_configs(base_config, config_data)
                config = self._create_config(name, merged_data)
            else:
                config = self._create_config(name, config_data)
            
            self._configs[name] = config
    
    def _merge_configs(self, base_config: AirframeConfig, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge base config with new data."""
        # Convert base config to dict
        base_data = {
            'name': base_config.name,
            'type': base_config.type,
            'mass': base_config.mass,
            'arm_length': base_config.arm_length,
            'propeller_diameter': base_config.propeller_diameter,
            'wingspan': base_config.wingspan,
            'wing_area': base_config.wing_area,
            'max_thrust': base_config.max_thrust,
            'max_rpm': base_config.max_rpm,
            'max_power': base_config.max_power,
            'max_vertical_thrust': base_config.max_vertical_thrust,
            'max_horizontal_thrust': base_config.max_horizontal_thrust,
            'max_velocity': base_config.max_velocity,
            'min_velocity': base_config.min_velocity,
            'max_acceleration': base_config.max_acceleration,
            'max_angular_velocity': base_config.max_angular_velocity,
            'max_angular_acceleration': base_config.max_angular_acceleration,
            'max_altitude': base_config.max_altitude,
            'min_altitude': base_config.min_altitude,
            'max_distance': base_config.max_distance,
            'control_frequency': base_config.control_frequency,
            'position_kp': list(base_config.position_kp),
            'velocity_kp': list(base_config.velocity_kp),
            'attitude_kp': list(base_config.attitude_kp),
            'attitude_kd': list(base_config.attitude_kd),
        }
        
        # Update with new data
        base_data.update(new_data)
        return base_data
    
    def _create_config(self, name: str, data: Dict[str, Any]) -> AirframeConfig:
        """Create an AirframeConfig from dictionary data."""
        return AirframeConfig(
            name=data.get('name', name),
            type=data.get('type', 'quadcopter'),
            mass=data.get('mass', 1.5),
            arm_length=data.get('arm_length'),
            propeller_diameter=data.get('propeller_diameter'),
            wingspan=data.get('wingspan'),
            wing_area=data.get('wing_area'),
            max_thrust=data.get('max_thrust', 15.0),
            max_rpm=data.get('max_rpm', 8000.0),
            max_power=data.get('max_power', 200.0),
            max_vertical_thrust=data.get('max_vertical_thrust'),
            max_horizontal_thrust=data.get('max_horizontal_thrust'),
            max_velocity=data.get('max_velocity', 15.0),
            min_velocity=data.get('min_velocity'),
            max_acceleration=data.get('max_acceleration', 8.0),
            max_angular_velocity=data.get('max_angular_velocity', 3.0),
            max_angular_acceleration=data.get('max_angular_acceleration', 6.0),
            max_altitude=data.get('max_altitude', 120.0),
            min_altitude=data.get('min_altitude', 0.5),
            max_distance=data.get('max_distance', 1000.0),
            control_frequency=data.get('control_frequency', 100.0),
            position_kp=data.get('position_kp', [2.0, 2.0, 2.0]),
            velocity_kp=data.get('velocity_kp', [1.5, 1.5, 1.5]),
            attitude_kp=data.get('attitude_kp', [8.0, 8.0, 8.0]),
            attitude_kd=data.get('attitude_kd', [2.0, 2.0, 2.0]),
        )
    
    def get_config(self, name: str) -> AirframeConfig:
        """Get airframe configuration by name."""
        if name not in self._configs:
            from dart_planner.common.errors import ConfigurationError
            raise ConfigurationError(f"Airframe config '{name}' not found. Available: {list(self._configs.keys())}")
        return self._configs[name]
    
    def get_default_config(self) -> AirframeConfig:
        """Get the default airframe configuration."""
        return self.get_config('default')
    
    def list_configs(self) -> List[str]:
        """List all available airframe configurations."""
        return list(self._configs.keys())
    
    def validate_config(self, name: str) -> List[str]:
        """Validate a specific airframe configuration."""
        config = self.get_config(name)
        return config.validate_config()
    
    def validate_all_configs(self) -> Dict[str, List[str]]:
        """Validate all airframe configurations."""
        results = {}
        for name in self._configs:
            results[name] = self.validate_config(name)
        return results


# Global instance for easy access
airframe_manager = AirframeConfigManager()


def get_airframe_config(name: str = "default") -> AirframeConfig:
    """Get airframe configuration by name."""
    return airframe_manager.get_config(name)


def list_airframe_configs() -> List[str]:
    """List all available airframe configurations."""
    return airframe_manager.list_configs() 
