"""
Centralized Configuration Management for DART-Planner

This module provides a single source of truth for all configuration,
using Pydantic for type safety and validation.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from pydantic import BaseModel, Field, validator
import yaml


class HeartbeatConfig(BaseModel):
    """Heartbeat configuration with validation."""
    interval_ms: int = Field(default=100, ge=10, le=1000, description="Heartbeat interval in milliseconds")
    timeout_ms: int = Field(default=500, ge=100, le=5000, description="Heartbeat timeout in milliseconds")
    mavlink_timeout_s: float = Field(default=5.0, ge=1.0, le=30.0, description="MAVLink heartbeat timeout in seconds")


class CommunicationConfig(BaseModel):
    """Communication configuration."""
    zmq_port: int = Field(default=5555, ge=1024, le=65535)
    zmq_host: str = Field(default="localhost")
    enable_heartbeat: bool = Field(default=True)
    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)


class SafetyConfig(BaseModel):
    """Safety configuration."""
    max_velocity: float = Field(default=15.0, ge=1.0, le=50.0, description="Maximum velocity in m/s")
    max_acceleration: float = Field(default=10.0, ge=1.0, le=30.0, description="Maximum acceleration in m/s²")
    max_altitude: float = Field(default=50.0, ge=1.0, le=200.0, description="Maximum altitude in meters")
    safety_radius: float = Field(default=100.0, ge=10.0, le=1000.0, description="Safety radius from home in meters")
    emergency_landing_altitude: float = Field(default=2.0, ge=0.5, le=10.0, description="Emergency landing altitude in meters")


class PlanningConfig(BaseModel):
    """Planning configuration."""
    prediction_horizon: int = Field(default=8, ge=4, le=20, description="MPC prediction horizon")
    dt: float = Field(default=0.1, ge=0.05, le=0.2, description="Time step in seconds")
    max_iterations: int = Field(default=15, ge=5, le=50, description="Maximum optimization iterations")
    convergence_tolerance: float = Field(default=5e-2, ge=1e-3, le=1e-1, description="Optimization convergence tolerance")
    position_weight: float = Field(default=100.0, ge=1.0, le=1000.0, description="Position tracking weight")
    velocity_weight: float = Field(default=10.0, ge=0.1, le=100.0, description="Velocity tracking weight")
    obstacle_weight: float = Field(default=1000.0, ge=100.0, le=10000.0, description="Obstacle avoidance weight")
    safety_margin: float = Field(default=1.5, ge=0.5, le=5.0, description="Safety margin in meters")


class HardwareConfig(BaseModel):
    """Hardware configuration."""
    mavlink_connection: str = Field(default="/dev/ttyUSB0", description="MAVLink connection string")
    baud_rate: int = Field(default=921600, description="Serial baud rate")
    control_frequency: float = Field(default=400.0, ge=50.0, le=1000.0, description="Control loop frequency in Hz")
    planning_frequency: float = Field(default=50.0, ge=10.0, le=200.0, description="Planning loop frequency in Hz")
    telemetry_frequency: float = Field(default=10.0, ge=1.0, le=50.0, description="Telemetry frequency in Hz")


class SimulationConfig(BaseModel):
    """Simulation configuration."""
    use_airsim: bool = Field(default=True, description="Use AirSim for simulation")
    airsim_host: str = Field(default="localhost", description="AirSim host address")
    airsim_port: int = Field(default=41451, description="AirSim port")
    enable_visualization: bool = Field(default=True, description="Enable simulation visualization")
    simulation_speed: float = Field(default=1.0, ge=0.1, le=10.0, description="Simulation speed multiplier")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    file: Optional[str] = Field(default=None, description="Log file path")
    enable_console: bool = Field(default=True, description="Enable console logging")
    enable_file: bool = Field(default=False, description="Enable file logging")


class SecurityConfig(BaseModel):
    """Security configuration."""
    enable_authentication: bool = Field(default=True, description="Enable authentication")
    secret_key: str = Field(default="", description="Secret key for JWT tokens")
    token_expiry_hours: int = Field(default=24, description="Token expiry time in hours")
    enable_ssl: bool = Field(default=False, description="Enable SSL/TLS")
    ssl_cert_file: Optional[str] = Field(default=None, description="SSL certificate file path")
    ssl_key_file: Optional[str] = Field(default=None, description="SSL private key file path")


class DARTPlannerConfig(BaseModel):
    """Main configuration class for DART-Planner."""
    
    # Environment
    environment: str = Field(default="development", description="Environment (development, production, testing)")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Component configurations
    communication: CommunicationConfig = Field(default_factory=CommunicationConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    planning: PlanningConfig = Field(default_factory=PlanningConfig)
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Custom settings
    custom_settings: Dict[str, Any] = Field(default_factory=dict, description="Custom settings")
    
    @validator('security')
    def validate_secret_key(cls, v):
        """Validate that secret key is set in production."""
        if v.enable_authentication and not v.secret_key and os.getenv('DART_ENVIRONMENT') == 'production':
            raise ValueError("Secret key must be set when authentication is enabled in production")
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment setting."""
        if v not in ['development', 'production', 'testing']:
            raise ValueError("Environment must be one of: development, production, testing")
        return v
    
    def get_heartbeat_config(self) -> HeartbeatConfig:
        """Get heartbeat configuration."""
        return self.communication.heartbeat
    
    def get_planning_config_dict(self) -> Dict[str, Any]:
        """Get planning configuration as dictionary."""
        return self.planning.dict()
    
    def get_hardware_config_dict(self) -> Dict[str, Any]:
        """Get hardware configuration as dictionary."""
        return self.hardware.dict()
    
    def get_safety_config_dict(self) -> Dict[str, Any]:
        """Get safety configuration as dictionary."""
        return self.safety.dict()


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager."""
        if config_path is None:
            # Default to config/defaults.yaml relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = str(project_root / "config" / "defaults.yaml")
        
        self.config_path = Path(config_path)
        self._config: Optional[DARTPlannerConfig] = None
    
    def load_config(self) -> DARTPlannerConfig:
        """Load configuration from file."""
        if self._config is not None:
            return self._config
        
        # Load from YAML file if it exists
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
        else:
            config_data = {}
        
        # Override with environment variables
        config_data = self._load_from_env(config_data)
        
        # Create and validate configuration
        self._config = DARTPlannerConfig(**config_data)
        return self._config
    
    def _load_from_env(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_mappings = {
            'DART_ENVIRONMENT': 'environment',
            'DART_DEBUG': 'debug',
            'DART_ZMQ_PORT': 'communication.zmq_port',
            'DART_ZMQ_HOST': 'communication.zmq_host',
            'DART_HEARTBEAT_INTERVAL_MS': 'communication.heartbeat.interval_ms',
            'DART_HEARTBEAT_TIMEOUT_MS': 'communication.heartbeat.timeout_ms',
            'DART_MAX_VELOCITY': 'safety.max_velocity',
            'DART_MAX_ACCELERATION': 'safety.max_acceleration',
            'DART_MAX_ALTITUDE': 'safety.max_altitude',
            'DART_PREDICTION_HORIZON': 'planning.prediction_horizon',
            'DART_DT': 'planning.dt',
            'DART_MAVLINK_CONNECTION': 'hardware.mavlink_connection',
            'DART_CONTROL_FREQUENCY': 'hardware.control_frequency',
            'DART_PLANNING_FREQUENCY': 'planning.planning_frequency',
            'DART_LOG_LEVEL': 'logging.level',
            'DART_SECRET_KEY': 'security.secret_key',
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert to appropriate type
                if env_var in ['DART_DEBUG', 'DART_ENABLE_HEARTBEAT', 'DART_ENABLE_AUTHENTICATION']:
                    env_value = env_value.lower() in ['true', '1', 'yes', 'on']
                elif env_var in ['DART_ZMQ_PORT', 'DART_HEARTBEAT_INTERVAL_MS', 'DART_HEARTBEAT_TIMEOUT_MS', 
                               'DART_PREDICTION_HORIZON', 'DART_MAX_ITERATIONS']:
                    env_value = int(env_value)
                elif env_var in ['DART_MAX_VELOCITY', 'DART_MAX_ACCELERATION', 'DART_MAX_ALTITUDE', 
                               'DART_DT', 'DART_CONTROL_FREQUENCY', 'DART_PLANNING_FREQUENCY']:
                    env_value = float(env_value)
                
                # Set nested config value
                keys = config_path.split('.')
                current = config_data
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[keys[-1]] = env_value
        
        return config_data
    
    def save_config(self, config: DARTPlannerConfig, path: Optional[str] = None) -> None:
        """Save configuration to file."""
        save_path = Path(path) if path else self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(config.dict(), f, default_flow_style=False, indent=2)
    
    def get_config(self) -> DARTPlannerConfig:
        """Get current configuration, loading if necessary."""
        if self._config is None:
            return self.load_config()
        return self._config


# Global configuration instance
_config_manager = ConfigManager()
get_config = _config_manager.get_config
load_config = _config_manager.load_config
save_config = _config_manager.save_config 