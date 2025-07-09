"""
Frozen Configuration System for DART-Planner

Provides immutable configuration objects with Pydantic validation
and startup validation to prevent runtime modification.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, FrozenSet
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager

from pydantic import BaseModel, Field, validator, root_validator, ValidationError, model_validator
from pydantic.generics import GenericModel

from dart_planner.common.errors import ConfigurationError
from dart_planner.common.coordinate_frames import WorldFrame


class FrozenBaseModel(BaseModel):
    """Base model for frozen configuration objects."""
    
    class Config:
        frozen = True  # Make all models immutable
        validate_assignment = True  # Validate on assignment
        extra = "forbid"  # Forbid extra fields
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: lambda v: str(v)
        }


class SecurityConfig(FrozenBaseModel):
    """Frozen security configuration."""
    
    enable_authentication: bool = Field(default=True, description="Enable authentication")
    enable_authorization: bool = Field(default=True, description="Enable authorization")
    jwt_secret_key: Optional[str] = Field(default=None, description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=30, description="JWT expiration in minutes")
    jwt_refresh_expiration_hours: int = Field(default=24, description="JWT refresh expiration in hours")
    bcrypt_rounds: int = Field(default=12, description="BCrypt rounds")
    max_login_attempts: int = Field(default=5, description="Maximum login attempts")
    lockout_duration_minutes: int = Field(default=15, description="Lockout duration in minutes")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    enable_csrf_protection: bool = Field(default=True, description="Enable CSRF protection")
    session_timeout_minutes: int = Field(default=60, description="Session timeout in minutes")
    
    @validator('jwt_secret_key')
    def validate_jwt_secret_key(cls, v):
        """Validate JWT secret key."""
        if v is None:
            # Try to get from environment
            v = os.getenv('DART_JWT_SECRET_KEY')
            if v is None:
                raise ValueError("JWT secret key must be provided via DART_JWT_SECRET_KEY environment variable")
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v
    
    @validator('jwt_expiration_minutes')
    def validate_jwt_expiration(cls, v):
        """Validate JWT expiration."""
        if v < 1 or v > 1440:  # 1 minute to 24 hours
            raise ValueError("JWT expiration must be between 1 and 1440 minutes")
        return v
    
    @validator('bcrypt_rounds')
    def validate_bcrypt_rounds(cls, v):
        """Validate BCrypt rounds."""
        if v < 10 or v > 20:
            raise ValueError("BCrypt rounds must be between 10 and 20")
        return v


class RealTimeConfig(FrozenBaseModel):
    """Frozen real-time configuration."""
    
    # Basic timing settings
    control_loop_frequency_hz: float = Field(default=400.0, ge=50.0, le=1000.0, description="Control loop frequency")
    planning_loop_frequency_hz: float = Field(default=25.0, ge=1.0, le=100.0, description="Planning loop frequency")
    safety_loop_frequency_hz: float = Field(default=100.0, ge=10.0, le=500.0, description="Safety loop frequency")
    max_control_latency_ms: float = Field(default=2.5, ge=0.1, le=10.0, description="Maximum control latency")
    max_planning_latency_ms: float = Field(default=40.0, ge=1.0, le=100.0, description="Maximum planning latency")
    max_safety_latency_ms: float = Field(default=10.0, ge=0.1, le=50.0, description="Maximum safety latency")
    enable_deadline_monitoring: bool = Field(default=True, description="Enable deadline monitoring")
    enable_jitter_compensation: bool = Field(default=True, description="Enable jitter compensation")
    max_jitter_ms: float = Field(default=0.1, ge=0.01, le=1.0, description="Maximum allowed jitter")
    enable_priority_scheduling: bool = Field(default=True, description="Enable priority scheduling")
    control_priority: int = Field(default=90, ge=1, le=99, description="Control loop priority")
    planning_priority: int = Field(default=70, ge=1, le=99, description="Planning loop priority")
    safety_priority: int = Field(default=95, ge=1, le=99, description="Safety loop priority")
    
    # Advanced scheduling settings
    enable_rt_os: bool = Field(default=True, description="Enable real-time OS features")
    enable_priority_inheritance: bool = Field(default=True, description="Enable priority inheritance")
    enable_timing_compensation: bool = Field(default=True, description="Enable timing compensation")
    max_scheduling_latency_ms: float = Field(default=0.1, ge=0.01, le=1.0, description="Maximum scheduling latency")
    max_context_switch_ms: float = Field(default=0.01, ge=0.001, le=0.1, description="Maximum context switch time")
    max_interrupt_latency_ms: float = Field(default=0.05, ge=0.001, le=0.5, description="Maximum interrupt latency")
    clock_drift_compensation_factor: float = Field(default=0.1, ge=0.0, le=1.0, description="Clock drift compensation factor")
    jitter_compensation_window: int = Field(default=100, ge=10, le=1000, description="Jitter compensation window size")
    timing_compensation_threshold_ms: float = Field(default=0.1, ge=0.01, le=1.0, description="Timing compensation threshold")
    
    # Task-specific timing
    control_loop_deadline_ms: float = Field(default=2.0, ge=1.0, le=10.0, description="Control loop deadline")
    control_loop_jitter_ms: float = Field(default=0.1, ge=0.01, le=1.0, description="Control loop jitter tolerance")
    planning_loop_deadline_ms: float = Field(default=15.0, ge=5.0, le=100.0, description="Planning loop deadline")
    planning_loop_jitter_ms: float = Field(default=1.0, ge=0.1, le=10.0, description="Planning loop jitter tolerance")
    safety_loop_deadline_ms: float = Field(default=8.0, ge=1.0, le=50.0, description="Safety loop deadline")
    safety_loop_jitter_ms: float = Field(default=0.5, ge=0.01, le=5.0, description="Safety loop jitter tolerance")
    
    # Communication timing
    communication_frequency_hz: float = Field(default=10.0, ge=1.0, le=50.0, description="Communication frequency")
    communication_deadline_ms: float = Field(default=100.0, ge=10.0, le=500.0, description="Communication deadline")
    communication_jitter_ms: float = Field(default=5.0, ge=0.1, le=50.0, description="Communication jitter tolerance")
    telemetry_frequency_hz: float = Field(default=10.0, ge=1.0, le=50.0, description="Telemetry frequency")
    telemetry_deadline_ms: float = Field(default=100.0, ge=10.0, le=500.0, description="Telemetry deadline")
    telemetry_jitter_ms: float = Field(default=5.0, ge=0.1, le=50.0, description="Telemetry jitter tolerance")
    
    # Performance monitoring
    enable_performance_monitoring: bool = Field(default=True, description="Enable performance monitoring")
    monitoring_frequency_hz: float = Field(default=10.0, ge=1.0, le=100.0, description="Performance monitoring frequency")
    stats_window_size: int = Field(default=1000, ge=100, le=10000, description="Statistics window size")
    deadline_violation_threshold: int = Field(default=5, ge=1, le=100, description="Deadline violation alert threshold")
    jitter_threshold_ms: float = Field(default=1.0, ge=0.1, le=10.0, description="Jitter alert threshold")
    execution_time_threshold_ms: float = Field(default=10.0, ge=1.0, le=100.0, description="Execution time alert threshold")
    enable_timing_logs: bool = Field(default=True, description="Enable timing logs")
    enable_performance_reports: bool = Field(default=True, description="Enable performance reports")
    log_performance_interval_s: float = Field(default=10.0, ge=1.0, le=60.0, description="Performance log interval")
    
    @validator('control_loop_frequency_hz', 'planning_loop_frequency_hz', 'safety_loop_frequency_hz')
    def validate_frequencies(cls, v, values):
        """Validate frequency relationships."""
        if 'control_loop_frequency_hz' in values and 'planning_loop_frequency_hz' in values:
            if values['control_loop_frequency_hz'] <= values['planning_loop_frequency_hz']:
                raise ValueError("Control loop frequency must be higher than planning loop frequency")
        return v
    
    @validator('control_loop_deadline_ms')
    def validate_control_deadline(cls, v, values):
        """Validate control loop deadline."""
        if 'control_loop_frequency_hz' in values:
            control_period_ms = 1000.0 / values['control_loop_frequency_hz']
            if v >= control_period_ms:
                raise ValueError("Control loop deadline must be less than period")
        return v
    
    @validator('planning_loop_deadline_ms')
    def validate_planning_deadline(cls, v, values):
        """Validate planning loop deadline."""
        if 'planning_loop_frequency_hz' in values:
            planning_period_ms = 1000.0 / values['planning_loop_frequency_hz']
            if v >= planning_period_ms:
                raise ValueError("Planning loop deadline must be less than period")
        return v
    
    @validator('safety_loop_deadline_ms')
    def validate_safety_deadline(cls, v, values):
        """Validate safety loop deadline."""
        if 'safety_loop_frequency_hz' in values:
            safety_period_ms = 1000.0 / values['safety_loop_frequency_hz']
            if v >= safety_period_ms:
                raise ValueError("Safety loop deadline must be less than period")
        return v


class HardwareConfig(FrozenBaseModel):
    """Frozen hardware configuration."""
    
    vehicle_type: str = Field(default="quadrotor", description="Vehicle type")
    max_velocity_mps: float = Field(default=15.0, ge=1.0, le=50.0, description="Maximum velocity")
    max_acceleration_mps2: float = Field(default=10.0, ge=1.0, le=30.0, description="Maximum acceleration")
    max_angular_velocity_radps: float = Field(default=3.0, ge=0.1, le=10.0, description="Maximum angular velocity")
    max_angular_acceleration_radps2: float = Field(default=5.0, ge=0.1, le=20.0, description="Maximum angular acceleration")
    max_altitude_m: float = Field(default=50.0, ge=1.0, le=200.0, description="Maximum altitude")
    safety_radius_m: float = Field(default=100.0, ge=10.0, le=1000.0, description="Safety radius")
    emergency_landing_altitude_m: float = Field(default=2.0, ge=0.1, le=10.0, description="Emergency landing altitude")
    enable_geofencing: bool = Field(default=True, description="Enable geofencing")
    geofence_polygon: Optional[List[List[float]]] = Field(default=None, description="Geofence polygon coordinates")
    enable_obstacle_avoidance: bool = Field(default=True, description="Enable obstacle avoidance")
    obstacle_safety_margin_m: float = Field(default=2.0, ge=0.1, le=10.0, description="Obstacle safety margin")
    
    @validator('geofence_polygon')
    def validate_geofence_polygon(cls, v):
        """Validate geofence polygon."""
        if v is not None:
            if len(v) < 3:
                raise ValueError("Geofence polygon must have at least 3 points")
            for point in v:
                if len(point) != 2:
                    raise ValueError("Geofence polygon points must have 2 coordinates")
        return v


class CommunicationConfig(FrozenBaseModel):
    """Frozen communication configuration."""
    
    zmq_bind_address: str = Field(default="tcp://*:5555", description="ZMQ bind address")
    zmq_connect_address: str = Field(default="tcp://localhost:5555", description="ZMQ connect address")
    enable_encryption: bool = Field(default=True, description="Enable communication encryption")
    encryption_key: Optional[str] = Field(default=None, description="Encryption key")
    heartbeat_interval_ms: int = Field(default=100, ge=10, le=1000, description="Heartbeat interval")
    heartbeat_timeout_ms: int = Field(default=500, ge=100, le=5000, description="Heartbeat timeout")
    max_message_size_bytes: int = Field(default=1048576, ge=1024, le=10485760, description="Maximum message size")
    enable_compression: bool = Field(default=True, description="Enable message compression")
    compression_level: int = Field(default=6, ge=1, le=9, description="Compression level")
    enable_reliability: bool = Field(default=True, description="Enable reliable communication")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Retry attempts")
    retry_delay_ms: int = Field(default=100, ge=10, le=1000, description="Retry delay")
    
    @validator('encryption_key')
    def validate_encryption_key(cls, v):
        """Validate encryption key."""
        if v is None:
            v = os.getenv('DART_ENCRYPTION_KEY')
            if v is None and os.getenv('DART_ENVIRONMENT') == 'production':
                raise ValueError("Encryption key must be provided in production")
        return v
    
    @validator('heartbeat_timeout_ms')
    def validate_heartbeat_timeout(cls, v, values):
        """Validate heartbeat timeout relative to interval."""
        if 'heartbeat_interval_ms' in values:
            if v <= values['heartbeat_interval_ms']:
                raise ValueError("Heartbeat timeout must be greater than heartbeat interval")
        return v


class LoggingConfig(FrozenBaseModel):
    """Frozen logging configuration."""
    
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    max_log_size_mb: int = Field(default=100, ge=1, le=1000, description="Maximum log file size")
    backup_count: int = Field(default=5, ge=0, le=20, description="Number of backup log files")
    enable_console_logging: bool = Field(default=True, description="Enable console logging")
    enable_file_logging: bool = Field(default=True, description="Enable file logging")
    enable_structured_logging: bool = Field(default=False, description="Enable structured logging")
    log_correlation_id: bool = Field(default=True, description="Include correlation IDs in logs")
    enable_performance_logging: bool = Field(default=True, description="Enable performance logging")
    performance_log_interval_s: int = Field(default=60, ge=10, le=3600, description="Performance log interval")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()


class SimulationConfig(FrozenBaseModel):
    """Frozen simulation configuration."""
    
    enable_airsim: bool = Field(default=False, description="Enable AirSim simulation")
    airsim_host: str = Field(default="localhost", description="AirSim host")
    airsim_port: int = Field(default=41451, ge=1024, le=65535, description="AirSim port")
    airsim_vehicle_name: str = Field(default="SimpleFlight", description="AirSim vehicle name")
    enable_sitl: bool = Field(default=False, description="Enable SITL simulation")
    sitl_host: str = Field(default="localhost", description="SITL host")
    sitl_port: int = Field(default=5760, ge=1024, le=65535, description="SITL port")
    enable_gazebo: bool = Field(default=False, description="Enable Gazebo simulation")
    gazebo_world_file: Optional[str] = Field(default=None, description="Gazebo world file")
    simulation_speed: float = Field(default=1.0, ge=0.1, le=10.0, description="Simulation speed multiplier")
    enable_physics: bool = Field(default=True, description="Enable physics simulation")
    enable_sensors: bool = Field(default=True, description="Enable sensor simulation")
    enable_actuators: bool = Field(default=True, description="Enable actuator simulation")
    
    @model_validator(mode="after")
    def validate_simulation_config(cls, values):
        """Validate simulation configuration."""
        enabled_sims = sum([
            getattr(values, 'enable_airsim', False),
            getattr(values, 'enable_sitl', False),
            getattr(values, 'enable_gazebo', False)
        ])
        
        if enabled_sims > 1:
            raise ValueError("Only one simulation environment can be enabled at a time")
        
        return values


class CoordinateFrameConfig(FrozenBaseModel):
    """Frozen coordinate frame configuration."""
    
    world_frame: WorldFrame = Field(default=WorldFrame.ENU, description="World coordinate frame convention")
    enforce_consistency: bool = Field(default=True, description="Enforce coordinate frame consistency")
    validate_transforms: bool = Field(default=True, description="Validate coordinate frame transformations")
    auto_detect_frame: bool = Field(default=False, description="Auto-detect frame from hardware interface")
    
    @validator('world_frame')
    def validate_world_frame(cls, v):
        """Validate world frame."""
        if isinstance(v, str):
            try:
                return WorldFrame(v)
            except ValueError:
                raise ValueError(f"Invalid world frame: {v}. Must be 'ENU' or 'NED'")
        return v
    
    @validator('auto_detect_frame')
    def validate_auto_detect_frame(cls, v, values):
        """Validate auto-detect frame setting."""
        if v and 'world_frame' in values:
            # When auto-detect is enabled, warn that manual frame setting might be overridden
            pass
        return v


class DARTPlannerFrozenConfig(FrozenBaseModel):
    """Main frozen configuration for DART-Planner."""
    
    # Environment
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    version: str = Field(default="1.0.0", description="DART-Planner version")
    
    # Component configurations
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    real_time: RealTimeConfig = Field(default_factory=RealTimeConfig)
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    communication: CommunicationConfig = Field(default_factory=CommunicationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    coordinate_frame: CoordinateFrameConfig = Field(default_factory=CoordinateFrameConfig)
    
    # Custom settings (immutable)
    custom_settings: FrozenSet[tuple] = Field(default_factory=frozenset, description="Custom settings")
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_environments = ['development', 'testing', 'staging', 'production']
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v
    
    @validator('custom_settings')
    def validate_custom_settings(cls, v):
        """Convert custom settings to frozen set."""
        if isinstance(v, dict):
            return frozenset(v.items())
        elif isinstance(v, (list, tuple)):
            return frozenset(v)
        return v
    
    @model_validator(mode="after")
    def validate_configuration(cls, values):
        """Validate overall configuration."""
        environment = getattr(values, 'environment', 'development')
        debug = getattr(values, 'debug', False)
        
        # Production validation
        if environment == 'production':
            if debug:
                raise ValueError("Debug mode cannot be enabled in production")
            
            security = getattr(values, 'security', None)
            if security and not security.jwt_secret_key:
                raise ValueError("JWT secret key must be set in production")
        
        return values


class ConfigurationManager:
    """Manages frozen configuration objects."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else None
        self._config: Optional[DARTPlannerFrozenConfig] = None
        self._frozen = False
    
    def load_config(self) -> DARTPlannerFrozenConfig:
        """Load and validate configuration."""
        if self._config is not None:
            return self._config
        
        # Load from file if provided
        config_data = {}
        if self.config_path and self.config_path.exists():
            config_data = self._load_from_file(self.config_path)
        
        # Override with environment variables
        config_data = self._load_from_env(config_data)
        
        # Create and validate configuration
        try:
            self._config = DARTPlannerFrozenConfig(**config_data)
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
        
        return self._config
    
    def _load_from_file(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            if config_path.suffix.lower() == '.json':
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif config_path.suffix.lower() in ['.yaml', '.yml']:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                raise ConfigurationError(f"Unsupported configuration file format: {config_path.suffix}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {config_path}: {e}")
    
    def _load_from_env(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_mappings = {
            'DART_ENVIRONMENT': 'environment',
            'DART_DEBUG': 'debug',
            'DART_VERSION': 'version',
            'DART_JWT_SECRET_KEY': ('security', 'jwt_secret_key'),
            'DART_JWT_ALGORITHM': ('security', 'jwt_algorithm'),
            'DART_JWT_EXPIRATION_MINUTES': ('security', 'jwt_expiration_minutes'),
            'DART_CONTROL_FREQUENCY_HZ': ('real_time', 'control_loop_frequency_hz'),
            'DART_PLANNING_FREQUENCY_HZ': ('real_time', 'planning_loop_frequency_hz'),
            'DART_SAFETY_FREQUENCY_HZ': ('real_time', 'safety_loop_frequency_hz'),
            'DART_MAX_CONTROL_LATENCY_MS': ('real_time', 'max_control_latency_ms'),
            'DART_MAX_PLANNING_LATENCY_MS': ('real_time', 'max_planning_latency_ms'),
            'DART_MAX_SAFETY_LATENCY_MS': ('real_time', 'max_safety_latency_ms'),
            'DART_ENABLE_DEADLINE_MONITORING': ('real_time', 'enable_deadline_monitoring'),
            'DART_ENABLE_JITTER_COMPENSATION': ('real_time', 'enable_jitter_compensation'),
            'DART_MAX_JITTER_MS': ('real_time', 'max_jitter_ms'),
            'DART_ENABLE_PRIORITY_SCHEDULING': ('real_time', 'enable_priority_scheduling'),
            'DART_CONTROL_PRIORITY': ('real_time', 'control_priority'),
            'DART_PLANNING_PRIORITY': ('real_time', 'planning_priority'),
            'DART_SAFETY_PRIORITY': ('real_time', 'safety_priority'),
            'DART_RT_ENABLE_OS': ('real_time', 'enable_rt_os'),
            'DART_RT_ENABLE_PRIORITY_INHERITANCE': ('real_time', 'enable_priority_inheritance'),
            'DART_RT_ENABLE_TIMING_COMPENSATION': ('real_time', 'enable_timing_compensation'),
            'DART_RT_MAX_SCHEDULING_LATENCY_MS': ('real_time', 'max_scheduling_latency_ms'),
            'DART_RT_MAX_CONTEXT_SWITCH_MS': ('real_time', 'max_context_switch_ms'),
            'DART_RT_MAX_INTERRUPT_LATENCY_MS': ('real_time', 'max_interrupt_latency_ms'),
            'DART_RT_CLOCK_DRIFT_COMPENSATION_FACTOR': ('real_time', 'clock_drift_compensation_factor'),
            'DART_RT_JITTER_COMPENSATION_WINDOW': ('real_time', 'jitter_compensation_window'),
            'DART_RT_TIMING_COMPENSATION_THRESHOLD_MS': ('real_time', 'timing_compensation_threshold_ms'),
            'DART_RT_CONTROL_DEADLINE_MS': ('real_time', 'control_loop_deadline_ms'),
            'DART_RT_CONTROL_JITTER_MS': ('real_time', 'control_loop_jitter_ms'),
            'DART_RT_PLANNING_DEADLINE_MS': ('real_time', 'planning_loop_deadline_ms'),
            'DART_RT_PLANNING_JITTER_MS': ('real_time', 'planning_loop_jitter_ms'),
            'DART_RT_SAFETY_DEADLINE_MS': ('real_time', 'safety_loop_deadline_ms'),
            'DART_RT_SAFETY_JITTER_MS': ('real_time', 'safety_loop_jitter_ms'),
            'DART_RT_COMMUNICATION_FREQUENCY_HZ': ('real_time', 'communication_frequency_hz'),
            'DART_RT_COMMUNICATION_DEADLINE_MS': ('real_time', 'communication_deadline_ms'),
            'DART_RT_COMMUNICATION_JITTER_MS': ('real_time', 'communication_jitter_ms'),
            'DART_RT_TELEMETRY_FREQUENCY_HZ': ('real_time', 'telemetry_frequency_hz'),
            'DART_RT_TELEMETRY_DEADLINE_MS': ('real_time', 'telemetry_deadline_ms'),
            'DART_RT_TELEMETRY_JITTER_MS': ('real_time', 'telemetry_jitter_ms'),
            'DART_RT_ENABLE_MONITORING': ('real_time', 'enable_performance_monitoring'),
            'DART_RT_MONITORING_FREQUENCY_HZ': ('real_time', 'monitoring_frequency_hz'),
            'DART_RT_STATS_WINDOW_SIZE': ('real_time', 'stats_window_size'),
            'DART_RT_DEADLINE_VIOLATION_THRESHOLD': ('real_time', 'deadline_violation_threshold'),
            'DART_RT_JITTER_THRESHOLD_MS': ('real_time', 'jitter_threshold_ms'),
            'DART_RT_EXECUTION_TIME_THRESHOLD_MS': ('real_time', 'execution_time_threshold_ms'),
            'DART_RT_ENABLE_TIMING_LOGS': ('real_time', 'enable_timing_logs'),
            'DART_RT_ENABLE_PERFORMANCE_REPORTS': ('real_time', 'enable_performance_reports'),
            'DART_RT_LOG_PERFORMANCE_INTERVAL_S': ('real_time', 'log_performance_interval_s'),
            'DART_MAX_VELOCITY_MPS': ('hardware', 'max_velocity_mps'),
            'DART_MAX_ALTITUDE_M': ('hardware', 'max_altitude_m'),
            'DART_ZMQ_BIND_ADDRESS': ('communication', 'zmq_bind_address'),
            'DART_LOG_LEVEL': ('logging', 'log_level'),
            'DART_WORLD_FRAME': ('coordinate_frame', 'world_frame'),
            'DART_ENFORCE_FRAME_CONSISTENCY': ('coordinate_frame', 'enforce_consistency'),
            'DART_VALIDATE_TRANSFORMS': ('coordinate_frame', 'validate_transforms'),
            'DART_AUTO_DETECT_FRAME': ('coordinate_frame', 'auto_detect_frame'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                if isinstance(config_path, str):
                    config_data[config_path] = self._convert_env_value(value)
                else:
                    # Nested path
                    section, key = config_path
                    if section not in config_data:
                        config_data[section] = {}
                    config_data[section][key] = self._convert_env_value(value)
        
        return config_data
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable value to appropriate type."""
        # Try to convert to boolean
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        # Try to convert to integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try to convert to float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def freeze_config(self) -> None:
        """Freeze the configuration to prevent further modification."""
        if self._config is None:
            self.load_config()
        
        self._frozen = True
    
    def is_frozen(self) -> bool:
        """Check if configuration is frozen."""
        return self._frozen
    
    def get_config(self) -> DARTPlannerFrozenConfig:
        """Get the frozen configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def validate_startup(self) -> bool:
        """Validate configuration at startup."""
        try:
            config = self.get_config()
            
            # Validate critical settings
            if config.environment == 'production':
                if config.debug:
                    raise ConfigurationError("Debug mode cannot be enabled in production")
                
                if not config.security.jwt_secret_key:
                    raise ConfigurationError("JWT secret key must be set in production")
            
            # Validate real-time requirements
            if not self._validate_real_time_requirements(config):
                return False
            
            # Validate hardware constraints
            if not self._validate_hardware_constraints(config):
                return False
            
            return True
            
        except Exception as e:
            raise ConfigurationError(f"Startup validation failed: {e}")
    
    def _validate_real_time_requirements(self, config: DARTPlannerFrozenConfig) -> bool:
        """Validate real-time requirements."""
        rt_config = config.real_time
        
        # Check frequency relationships
        if rt_config.control_loop_frequency_hz <= rt_config.planning_loop_frequency_hz:
            raise ConfigurationError("Control loop frequency must be higher than planning loop frequency")
        
        # Check latency requirements
        control_period_ms = 1000.0 / rt_config.control_loop_frequency_hz
        if rt_config.max_control_latency_ms >= control_period_ms:
            raise ConfigurationError("Control latency must be less than control loop period")
        
        return True
    
    def _validate_hardware_constraints(self, config: DARTPlannerFrozenConfig) -> bool:
        """Validate hardware constraints."""
        hw_config = config.hardware
        
        # Check velocity and acceleration relationships
        if hw_config.max_acceleration_mps2 > hw_config.max_velocity_mps:
            raise ConfigurationError("Maximum acceleration cannot exceed maximum velocity")
        
        # Check altitude constraints
        if hw_config.emergency_landing_altitude_m >= hw_config.max_altitude_m:
            raise ConfigurationError("Emergency landing altitude must be less than maximum altitude")
        
        return True


# Global configuration manager
_config_manager: Optional[ConfigurationManager] = None

def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager

def get_frozen_config() -> DARTPlannerFrozenConfig:
    """Get the frozen configuration."""
    return get_config_manager().get_config()

def freeze_configuration() -> None:
    """Freeze the global configuration."""
    get_config_manager().freeze_config()

def validate_startup_configuration() -> bool:
    """Validate configuration at startup."""
    return get_config_manager().validate_startup()


# Context manager for temporary configuration changes
@contextmanager
def temporary_config(config_updates: Dict[str, Any]):
    """Context manager for temporary configuration changes."""
    manager = get_config_manager()
    original_config = manager._config
    
    try:
        # Create new config with updates
        if original_config:
            config_dict = original_config.dict()
            config_dict.update(config_updates)
            manager._config = DARTPlannerFrozenConfig(**config_dict)
        
        yield manager._config
        
    finally:
        # Restore original config
        manager._config = original_config 