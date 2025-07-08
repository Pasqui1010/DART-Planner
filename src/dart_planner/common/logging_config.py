"""
Centralized logging configuration for DART-Planner.

This module provides a consistent logging setup across all components,
replacing print statements with proper structured logging.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from ..config.settings import get_config


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = False,
    format_string: Optional[str] = None
) -> None:
    """
    Setup centralized logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        enable_console: Enable console logging
        enable_file: Enable file logging
        format_string: Custom log format string
    """
    # Get configuration
    config = get_config()
    logging_config = config.logging
    
    # Use provided parameters or fall back to config
    level = level or logging_config.level
    log_file = log_file or logging_config.file
    enable_console = enable_console if enable_console is not None else logging_config.enable_console
    enable_file = enable_file if enable_file is not None else logging_config.enable_file
    format_string = format_string or logging_config.format
    
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
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
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
    logger.info(f"Logging configured - Level: {level}, Console: {enable_console}, File: {enable_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def configure_component_logging(component_name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Configure logging for a specific component.
    
    Args:
        component_name: Name of the component
        level: Optional override for log level
        
    Returns:
        Configured logger for the component
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
    
    return logger


# Initialize logging when module is imported
try:
    setup_logging()
except Exception:
    # Fallback to basic logging if config is not available
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ) 