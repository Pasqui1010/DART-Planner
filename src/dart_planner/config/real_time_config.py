"""
Real-Time Configuration for DART-Planner

This module extends the main configuration with real-time specific settings
for scheduling, timing, and performance requirements.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator

from dart_planner.config.settings import DARTPlannerConfig
from dart_planner.common.errors import ConfigurationError


class RealTimeSchedulingConfig(BaseModel):
    """Real-time scheduling configuration."""
    
    # Scheduler settings
    enable_rt_os: bool = Field(default=True, description="Enable real-time OS features")
    enable_priority_inheritance: bool = Field(default=True, description="Enable priority inheritance")
    enable_deadline_monitoring: bool = Field(default=True, description="Enable deadline monitoring")
    enable_timing_compensation: bool = Field(default=True, description="Enable timing compensation")
    
    # Performance requirements
    max_scheduling_latency_ms: float = Field(default=0.1, ge=0.01, le=1.0, description="Maximum scheduling latency")
    max_context_switch_ms: float = Field(default=0.01, ge=0.001, le=0.1, description="Maximum context switch time")
    max_interrupt_latency_ms: float = Field(default=0.05, ge=0.001, le=0.5, description="Maximum interrupt latency")
    
    # Timing compensation
    clock_drift_compensation_factor: float = Field(default=0.1, ge=0.0, le=1.0, description="Clock drift compensation factor")
    jitter_compensation_window: int = Field(default=100, ge=10, le=1000, description="Jitter compensation window size")
    timing_compensation_threshold_ms: float = Field(default=0.1, ge=0.01, le=1.0, description="Timing compensation threshold")


class TaskTimingConfig(BaseModel):
    """Task-specific timing configuration."""
    
    # Control loop timing
    control_loop_frequency_hz: float = Field(default=400.0, ge=100.0, le=1000.0, description="Control loop frequency")
    control_loop_deadline_ms: float = Field(default=2.0, ge=1.0, le=10.0, description="Control loop deadline")
    control_loop_jitter_ms: float = Field(default=0.1, ge=0.01, le=1.0, description="Control loop jitter tolerance")
    
    # Planning loop timing
    planning_loop_frequency_hz: float = Field(default=50.0, ge=10.0, le=200.0, description="Planning loop frequency")
    planning_loop_deadline_ms: float = Field(default=15.0, ge=5.0, le=100.0, description="Planning loop deadline")
    planning_loop_jitter_ms: float = Field(default=1.0, ge=0.1, le=10.0, description="Planning loop jitter tolerance")
    
    # Safety loop timing
    safety_loop_frequency_hz: float = Field(default=100.0, ge=50.0, le=500.0, description="Safety loop frequency")
    safety_loop_deadline_ms: float = Field(default=8.0, ge=1.0, le=50.0, description="Safety loop deadline")
    safety_loop_jitter_ms: float = Field(default=0.5, ge=0.01, le=5.0, description="Safety loop jitter tolerance")
    
    # Communication timing
    communication_frequency_hz: float = Field(default=10.0, ge=1.0, le=50.0, description="Communication frequency")
    communication_deadline_ms: float = Field(default=100.0, ge=10.0, le=500.0, description="Communication deadline")
    communication_jitter_ms: float = Field(default=5.0, ge=0.1, le=50.0, description="Communication jitter tolerance")
    
    # Telemetry timing
    telemetry_frequency_hz: float = Field(default=10.0, ge=1.0, le=50.0, description="Telemetry frequency")
    telemetry_deadline_ms: float = Field(default=100.0, ge=10.0, le=500.0, description="Telemetry deadline")
    telemetry_jitter_ms: float = Field(default=5.0, ge=0.1, le=50.0, description="Telemetry jitter tolerance")


class PerformanceMonitoringConfig(BaseModel):
    """Performance monitoring configuration."""
    
    # Monitoring settings
    enable_performance_monitoring: bool = Field(default=True, description="Enable performance monitoring")
    monitoring_frequency_hz: float = Field(default=10.0, ge=1.0, le=100.0, description="Performance monitoring frequency")
    stats_window_size: int = Field(default=1000, ge=100, le=10000, description="Statistics window size")
    
    # Alert thresholds
    deadline_violation_threshold: int = Field(default=5, ge=1, le=100, description="Deadline violation alert threshold")
    jitter_threshold_ms: float = Field(default=1.0, ge=0.1, le=10.0, description="Jitter alert threshold")
    execution_time_threshold_ms: float = Field(default=10.0, ge=1.0, le=100.0, description="Execution time alert threshold")
    
    # Logging
    enable_timing_logs: bool = Field(default=True, description="Enable timing logs")
    enable_performance_reports: bool = Field(default=True, description="Enable performance reports")
    log_performance_interval_s: float = Field(default=10.0, ge=1.0, le=60.0, description="Performance log interval")


class RealTimeConfig(BaseModel):
    """Complete real-time configuration."""
    
    # Component configurations
    scheduling: RealTimeSchedulingConfig = Field(default_factory=RealTimeSchedulingConfig)
    task_timing: TaskTimingConfig = Field(default_factory=TaskTimingConfig)
    performance_monitoring: PerformanceMonitoringConfig = Field(default_factory=PerformanceMonitoringConfig)
    
    # Custom real-time settings
    custom_rt_settings: Dict[str, Any] = Field(default_factory=dict, description="Custom real-time settings")
    
    @validator('task_timing')
    def validate_task_timing(cls, v):
        """Validate task timing constraints."""
        # Control loop deadline should be less than period
        control_period_ms = 1000.0 / v.control_loop_frequency_hz
        if v.control_loop_deadline_ms >= control_period_ms:
            raise ConfigurationError("Control loop deadline must be less than period")
        
        # Planning loop deadline should be less than period
        planning_period_ms = 1000.0 / v.planning_loop_frequency_hz
        if v.planning_loop_deadline_ms >= planning_period_ms:
            raise ConfigurationError("Planning loop deadline must be less than period")
        
        # Safety loop deadline should be less than period
        safety_period_ms = 1000.0 / v.safety_loop_frequency_hz
        if v.safety_loop_deadline_ms >= safety_period_ms:
            raise ConfigurationError("Safety loop deadline must be less than period")
        
        return v


def extend_config_with_real_time(config: DARTPlannerConfig) -> DARTPlannerConfig:
    """Extend the main configuration with real-time settings."""
    
    # Create real-time config with defaults
    rt_config = RealTimeConfig()
    
    # Override with environment variables
    rt_config = _load_rt_config_from_env(rt_config)
    
    # Add real-time config to main config
    config.custom_settings['real_time'] = rt_config.dict()
    
    return config


def _load_rt_config_from_env(rt_config: RealTimeConfig) -> RealTimeConfig:
    """Load real-time configuration from environment variables."""
    import os
    
    # Scheduling settings
    if os.getenv('DART_RT_ENABLE_OS'):
        rt_config.scheduling.enable_rt_os = os.getenv('DART_RT_ENABLE_OS').lower() == 'true'
    
    if os.getenv('DART_RT_MAX_SCHEDULING_LATENCY_MS'):
        rt_config.scheduling.max_scheduling_latency_ms = float(os.getenv('DART_RT_MAX_SCHEDULING_LATENCY_MS'))
    
    # Task timing settings
    if os.getenv('DART_RT_CONTROL_FREQUENCY_HZ'):
        rt_config.task_timing.control_loop_frequency_hz = float(os.getenv('DART_RT_CONTROL_FREQUENCY_HZ'))
    
    if os.getenv('DART_RT_CONTROL_DEADLINE_MS'):
        rt_config.task_timing.control_loop_deadline_ms = float(os.getenv('DART_RT_CONTROL_DEADLINE_MS'))
    
    if os.getenv('DART_RT_PLANNING_FREQUENCY_HZ'):
        rt_config.task_timing.planning_loop_frequency_hz = float(os.getenv('DART_RT_PLANNING_FREQUENCY_HZ'))
    
    if os.getenv('DART_RT_PLANNING_DEADLINE_MS'):
        rt_config.task_timing.planning_loop_deadline_ms = float(os.getenv('DART_RT_PLANNING_DEADLINE_MS'))
    
    if os.getenv('DART_RT_SAFETY_FREQUENCY_HZ'):
        rt_config.task_timing.safety_loop_frequency_hz = float(os.getenv('DART_RT_SAFETY_FREQUENCY_HZ'))
    
    if os.getenv('DART_RT_SAFETY_DEADLINE_MS'):
        rt_config.task_timing.safety_loop_deadline_ms = float(os.getenv('DART_RT_SAFETY_DEADLINE_MS'))
    
    # Performance monitoring settings
    if os.getenv('DART_RT_ENABLE_MONITORING'):
        rt_config.performance_monitoring.enable_performance_monitoring = os.getenv('DART_RT_ENABLE_MONITORING').lower() == 'true'
    
    if os.getenv('DART_RT_MONITORING_FREQUENCY_HZ'):
        rt_config.performance_monitoring.monitoring_frequency_hz = float(os.getenv('DART_RT_MONITORING_FREQUENCY_HZ'))
    
    return rt_config


def get_real_time_config(config: DARTPlannerConfig) -> RealTimeConfig:
    """Get real-time configuration from main config."""
    if 'real_time' not in config.custom_settings:
        # Extend config if not already done
        config = extend_config_with_real_time(config)
    
    rt_config_data = config.custom_settings['real_time']
    return RealTimeConfig(**rt_config_data)


def get_task_timing_config(config: DARTPlannerConfig) -> TaskTimingConfig:
    """Get task timing configuration."""
    rt_config = get_real_time_config(config)
    return rt_config.task_timing


def get_scheduling_config(config: DARTPlannerConfig) -> RealTimeSchedulingConfig:
    """Get scheduling configuration."""
    rt_config = get_real_time_config(config)
    return rt_config.scheduling


def get_performance_monitoring_config(config: DARTPlannerConfig) -> PerformanceMonitoringConfig:
    """Get performance monitoring configuration."""
    rt_config = get_real_time_config(config)
    return rt_config.performance_monitoring


# Convenience functions for common timing requirements
def get_control_loop_config(config: DARTPlannerConfig) -> Dict[str, Any]:
    """Get control loop timing configuration."""
    timing_config = get_task_timing_config(config)
    return {
        'frequency_hz': timing_config.control_loop_frequency_hz,
        'period_ms': 1000.0 / timing_config.control_loop_frequency_hz,
        'deadline_ms': timing_config.control_loop_deadline_ms,
        'jitter_ms': timing_config.control_loop_jitter_ms,
    }


def get_planning_loop_config(config: DARTPlannerConfig) -> Dict[str, Any]:
    """Get planning loop timing configuration."""
    timing_config = get_task_timing_config(config)
    return {
        'frequency_hz': timing_config.planning_loop_frequency_hz,
        'period_ms': 1000.0 / timing_config.planning_loop_frequency_hz,
        'deadline_ms': timing_config.planning_loop_deadline_ms,
        'jitter_ms': timing_config.planning_loop_jitter_ms,
    }


def get_safety_loop_config(config: DARTPlannerConfig) -> Dict[str, Any]:
    """Get safety loop timing configuration."""
    timing_config = get_task_timing_config(config)
    return {
        'frequency_hz': timing_config.safety_loop_frequency_hz,
        'period_ms': 1000.0 / timing_config.safety_loop_frequency_hz,
        'deadline_ms': timing_config.safety_loop_deadline_ms,
        'jitter_ms': timing_config.safety_loop_jitter_ms,
    }


def get_communication_config(config: DARTPlannerConfig) -> Dict[str, Any]:
    """Get communication timing configuration."""
    timing_config = get_task_timing_config(config)
    return {
        'frequency_hz': timing_config.communication_frequency_hz,
        'period_ms': 1000.0 / timing_config.communication_frequency_hz,
        'deadline_ms': timing_config.communication_deadline_ms,
        'jitter_ms': timing_config.communication_jitter_ms,
    } 
