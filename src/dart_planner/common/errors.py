"""
DART-Planner Exception Hierarchy

Defines a consistent set of exception types for all major error domains in the system.
"""

class DARTPlannerError(Exception):
    """Base exception for all DART-Planner errors."""
    pass

class ConfigurationError(DARTPlannerError):
    """Raised for configuration-related errors."""
    pass

class DependencyError(DARTPlannerError):
    """Raised for dependency injection or resolution errors."""
    pass

class CommunicationError(DARTPlannerError):
    """Raised for communication (network, IPC, etc.) errors."""
    pass

class ControlError(DARTPlannerError):
    """Raised for control system errors."""
    pass

class PlanningError(DARTPlannerError):
    """Raised for planning algorithm errors."""
    pass

class HardwareError(DARTPlannerError):
    """Raised for hardware interface errors."""
    pass

class ValidationError(DARTPlannerError):
    """Raised for input or data validation errors."""
    pass

class SecurityError(DARTPlannerError):
    """Raised for authentication, authorization, or cryptographic errors."""
    pass

class RealTimeError(DARTPlannerError):
    """Raised for real-time system errors."""
    pass

class SchedulingError(DARTPlannerError):
    """Raised for task scheduling errors."""
    pass

class TimingError(DARTPlannerError):
    """Raised for timing and deadline violation errors."""
    pass

class UnsupportedCommandError(HardwareError):
    """Raised when a hardware command is not supported by the adapter."""
    pass 
