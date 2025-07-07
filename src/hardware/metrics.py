"""
AirSim Metrics and Performance Tracking

This module handles performance metrics, logging, and control command
tracking for the AirSim interface.
"""

import logging
import time
from typing import Dict, List, Optional, Any

import numpy as np
import numpy.typing as npt

from src.common.types import ControlCommand, DroneState


class AirSimMetricsManager:
    """Manages performance metrics and logging for AirSim interface"""
    
    def __init__(self, config):
        self.config = config
        self._control_times: List[float] = []
        self._command_count: int = 0
        self._error_count: int = 0
        self._control_frequency: float = 0.0
        self._last_control_time: float = 0.0
        self._last_command: Optional[ControlCommand] = None
        self._last_state: Optional[DroneState] = None
        
        # Limit history to avoid unbounded memory growth in long missions
        self._MAX_HISTORY = 5000
        
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
    
    def track_control_command(self, command: ControlCommand) -> None:
        """
        Track control command for performance metrics
        
        Args:
            command: Control command that was sent
        """
        current_time = time.time()
        
        # Track control timing
        if self._last_control_time > 0:
            dt = current_time - self._last_control_time
            self._control_times.append(dt)
            if len(self._control_times) > self._MAX_HISTORY:
                # Drop oldest entry to keep memory usage bounded
                self._control_times.pop(0)
            
            # Calculate frequency over last 50 commands
            if len(self._control_times) > 50:
                self._control_times.pop(0)
                self._control_frequency = float(1.0 / np.mean(self._control_times))
        
        self._last_control_time = current_time
        self._last_command = command
        self._command_count += 1
        
        if self.config.enable_trace_logging:
            self.logger.debug(
                f"Control command sent: thrust={command.thrust:.3f}, "
                f"torque=[{command.torque[0]:.3f}, {command.torque[1]:.3f}, {command.torque[2]:.3f}]"
            )
    
    def track_state(self, state: DroneState) -> None:
        """
        Track drone state for metrics
        
        Args:
            state: Current drone state
        """
        self._last_state = state
    
    def track_error(self) -> None:
        """Track an error occurrence"""
        self._error_count += 1
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the interface
        
        Returns:
            Dictionary containing performance metrics
        """
        return {
            "commands_sent": self._command_count,
            "errors": self._error_count,
            "control_frequency_hz": self._control_frequency,
            "last_command": {
                "thrust": self._last_command.thrust if self._last_command else None,
                "torque": self._last_command.torque.tolist() if self._last_command else None
            } if self._last_command else None,
            "last_state": {
                "position": self._last_state.position.tolist() if self._last_state else None,
                "velocity": self._last_state.velocity.tolist() if self._last_state else None
            } if self._last_state else None,
            "control_timing": {
                "mean_interval_ms": np.mean(self._control_times) * 1000 if self._control_times else None,
                "std_interval_ms": np.std(self._control_times) * 1000 if self._control_times else None,
                "min_interval_ms": np.min(self._control_times) * 1000 if self._control_times else None,
                "max_interval_ms": np.max(self._control_times) * 1000 if self._control_times else None
            }
        }
    
    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self._command_count = 0
        self._error_count = 0
        self._control_times.clear()
        self._control_frequency = 0.0
        self._last_control_time = 0.0
    
    def get_command_count(self) -> int:
        """Get the number of commands sent"""
        return self._command_count
    
    def get_error_count(self) -> int:
        """Get the number of errors"""
        return self._error_count
    
    def get_control_frequency(self) -> float:
        """Get the current control frequency in Hz"""
        return self._control_frequency
    
    def get_last_command(self) -> Optional[ControlCommand]:
        """Get the last command sent"""
        return self._last_command
    
    def get_last_state(self) -> Optional[DroneState]:
        """Get the last state received"""
        return self._last_state 