"""
Centralized logging configuration for DART-Planner.

This module provides a consistent logging setup across all components,
replacing print statements with proper structured logging.
"""

import logging
import logging.handlers
import sys
import json
import uuid
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Union
from contextlib import contextmanager
from dataclasses import dataclass, asdict

from ..config.frozen_config import get_frozen_config


@dataclass
class LogContext:
    """Context for structured logging with correlation IDs."""
    correlation_id: str
    component: str
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    extra_fields: Optional[Dict[str, Any]] = None


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logging."""
    
    def __init__(self, include_correlation_id: bool = True):
        super().__init__()
        self.include_correlation_id = include_correlation_id
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log data
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add correlation ID if available
        if self.include_correlation_id and hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = getattr(record, 'correlation_id')
        
        # Add component and operation if available
        if hasattr(record, 'component'):
            log_data['component'] = getattr(record, 'component')
        if hasattr(record, 'operation'):
            log_data['operation'] = getattr(record, 'operation')
        
        # Add extra fields
        if hasattr(record, 'extra_fields') and getattr(record, 'extra_fields'):
            log_data.update(getattr(record, 'extra_fields'))
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


class PerformanceLogger:
    """Performance logging with timing and metrics."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._timers: Dict[str, float] = {}
        self._counters: Dict[str, int] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def time_operation(self, operation: str, correlation_id: Optional[str] = None):
        """Context manager for timing operations."""
        start_time = time.time()
        timer_id = f"{operation}_{correlation_id or 'default'}"
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            with self._lock:
                self._timers[timer_id] = duration
                self._counters[timer_id] = self._counters.get(timer_id, 0) + 1
            
            self.logger.info(
                f"Operation completed",
                extra={
                    'operation': operation,
                    'duration_ms': duration * 1000,
                    'correlation_id': correlation_id
                }
            )
    
    def increment_counter(self, name: str, value: int = 1):
        """Increment a performance counter."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        with self._lock:
            return {
                'timers': self._timers.copy(),
                'counters': self._counters.copy()
            }


class StructuredLogger:
    """Enhanced logger with structured logging capabilities."""
    
    def __init__(self, name: str, correlation_id: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.performance = PerformanceLogger(self.logger)
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log with correlation ID and context."""
        extra = {
            'correlation_id': self.correlation_id,
            **kwargs
        }
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def log_operation(self, operation: str, message: str, **kwargs):
        """Log operation with structured context."""
        self._log_with_context(
            logging.INFO, 
            message, 
            operation=operation,
            **kwargs
        )
    
    def log_performance(self, metric: str, value: Union[int, float], unit: str = ""):
        """Log performance metric."""
        self._log_with_context(
            logging.INFO,
            f"Performance metric: {metric}",
            metric=metric,
            value=value,
            unit=unit
        )


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = False,
    format_string: Optional[str] = None,
    enable_structured: bool = False,
    enable_correlation_id: bool = True
) -> None:
    """
    Setup centralized logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        enable_console: Enable console logging
        enable_file: Enable file logging
        format_string: Custom log format string
        enable_structured: Enable structured JSON logging
        enable_correlation_id: Enable correlation IDs in logs
    """
    # Get configuration
    config = get_frozen_config()
    logging_config = config.logging
    
    # Use provided parameters or fall back to config
    level = level or logging_config.log_level
    log_file = log_file or logging_config.log_file
    enable_console = enable_console if enable_console is not None else logging_config.enable_console_logging
    enable_file = enable_file if enable_file is not None else logging_config.enable_file_logging
    format_string = format_string or logging_config.log_format
    enable_structured = enable_structured or logging_config.enable_structured_logging
    enable_correlation_id = enable_correlation_id or logging_config.log_correlation_id
    
    # Convert string level to logging constant
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    log_level = level_map.get(level.upper(), logging.INFO)
    
    # Create formatter
    if enable_structured:
        formatter = StructuredFormatter(include_correlation_id=enable_correlation_id)
    else:
        formatter = logging.Formatter(format_string)
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Setup handlers
    handlers = []
    
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    if enable_file and log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler for better log management
        max_bytes = logging_config.max_log_size_mb * 1024 * 1024
        backup_count = logging_config.backup_count
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    root_logger.setLevel(log_level)
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Set specific logger levels for noisy modules
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('numpy').setLevel(logging.WARNING)
    logging.getLogger('scipy').setLevel(logging.WARNING)
    logging.getLogger('cvxpy').setLevel(logging.WARNING)
    
    # Log the setup
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured",
        extra={
            'level': level,
            'console_enabled': enable_console,
            'file_enabled': enable_file,
            'structured_enabled': enable_structured,
            'correlation_id_enabled': enable_correlation_id
        }
    )


def configure_component_logging(component_name: str, level: Optional[str] = None) -> StructuredLogger:
    """
    Configure logging for a specific component.
    
    Args:
        component_name: Name of the component
        level: Optional override for log level
        
    Returns:
        Configured structured logger for the component
    """
    logger = logging.getLogger(f"dart_planner.{component_name}")
    
    if level:
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        logger.setLevel(level_map.get(level.upper(), logging.INFO))
    
    return StructuredLogger(f"dart_planner.{component_name}")


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger for the given name.
    
    Args:
        name: Logger name
        
    Returns:
        Structured logger instance
    """
    return StructuredLogger(name)


# Initialize logging when module is imported
try:
    setup_logging()
except Exception:
    # Fallback to basic logging if config is not available
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ) 