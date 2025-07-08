"""
Transport-delay compensation buffer for estimator-controller communication.

This module provides a latency buffer to compensate for communication delays
between state estimation and control action, which is critical for stability
in real-time control systems.

References:
- Control Global: "Deadtime compensation opportunities and realities"
- Standard practice: 20-30ms typical delay compensation
"""

import time
from collections import deque
from typing import Optional, Any, Generic, TypeVar
import numpy as np

T = TypeVar('T')

class LatencyBuffer(Generic[T]):
    """
    FIFO buffer for transport-delay compensation in control loops.
    
    Compensates for communication/processing delays between estimator and controller
    by providing delayed state information that accounts for the transport delay.
    This is essential for maintaining stability in real-time control systems.
    
    Args:
        delay_s: Transport delay to compensate for (seconds)
        dt: Control loop period (seconds)
        max_buffer_size: Maximum buffer size to prevent memory issues
    """
    
    def __init__(self, delay_s: float, dt: float, max_buffer_size: int = 1000):
        self.delay_s = delay_s
        self.dt = dt
        self.max_buffer_size = max_buffer_size
        
        # Calculate required buffer size
        self.required_size = max(1, int(round(delay_s / dt)))
        self.buffer_size = min(self.required_size, max_buffer_size)
        
        # Initialize buffer with timestamps and data
        # Use deque with maxlen to automatically maintain buffer size
        self.buffer = deque(maxlen=self.buffer_size)
        self.last_output: Optional[T] = None
        self.last_timestamp: float = 0.0
        
        # Statistics
        self.total_samples = 0
        self.missed_samples = 0
        self.actual_delay_s = 0.0
        
    def push(self, data: T, timestamp: Optional[float] = None) -> T:
        """
        Push new data into the buffer and return delayed data.
        
        Args:
            data: Current state/measurement data
            timestamp: Current timestamp (uses time.time() if None)
            
        Returns:
            Delayed data from delay_s ago, or current data if buffer not full
        """
        if timestamp is None:
            timestamp = time.time()
        
        if len(self.buffer) < self.buffer_size:
            # Buffer not full yet, just append
            self.buffer.append((timestamp, data))
            self.total_samples += 1
            self.missed_samples += 1
            return data
        else:
            # Buffer full: pop oldest, append new, return popped
            delayed_timestamp, delayed_data = self.buffer.popleft()
            self.buffer.append((timestamp, data))
            self.total_samples += 1
            self.last_output = delayed_data
            self.last_timestamp = delayed_timestamp
            self.actual_delay_s = timestamp - delayed_timestamp
            return delayed_data
    
    def get_delayed_data(self) -> Optional[T]:
        """Get the most recent delayed data without pushing new data."""
        return self.last_output
    
    def get_actual_delay(self) -> float:
        """Get the actual delay achieved (may differ from requested delay)."""
        return self.actual_delay_s
    
    def get_statistics(self) -> dict:
        """Get buffer statistics for monitoring and debugging."""
        return {
            'requested_delay_s': self.delay_s,
            'actual_delay_s': self.actual_delay_s,
            'buffer_size': len(self.buffer),
            'required_size': self.required_size,
            'total_samples': self.total_samples,
            'missed_samples': self.missed_samples,
            'fill_percentage': len(self.buffer) / self.buffer_size * 100 if self.buffer_size > 0 else 0
        }
    
    def reset(self):
        """Reset the buffer and statistics."""
        self.buffer.clear()
        self.last_output = None
        self.last_timestamp = 0.0
        self.total_samples = 0
        self.missed_samples = 0
        self.actual_delay_s = 0.0
    
    def is_ready(self) -> bool:
        """Check if buffer is full and ready to provide delayed data."""
        return len(self.buffer) >= self.buffer_size


class DroneStateLatencyBuffer(LatencyBuffer):
    """
    Specialized latency buffer for DroneState objects.
    
    Provides type-safe transport-delay compensation for drone state estimation
    with additional validation and safety checks.
    """
    
    def __init__(self, delay_s: float, dt: float, max_buffer_size: int = 1000):
        super().__init__(delay_s, dt, max_buffer_size)
        
    def push(self, state, timestamp: Optional[float] = None):
        """
        Push drone state and return delayed state.
        
        Args:
            state: DroneState object
            timestamp: Current timestamp
            
        Returns:
            Delayed DroneState or current state if buffer not ready
        """
        # Validate state has required attributes
        if not hasattr(state, 'position') or not hasattr(state, 'velocity'):
            raise ValueError("State must have position and velocity attributes")
            
        return super().push(state, timestamp)


def create_latency_buffer(delay_ms: float, dt_ms: float, state_type: str = "generic") -> LatencyBuffer:
    """
    Factory function to create appropriate latency buffer.
    
    Args:
        delay_ms: Transport delay in milliseconds
        dt_ms: Control loop period in milliseconds
        state_type: Type of state data ("drone_state", "generic")
        
    Returns:
        Configured latency buffer
    """
    delay_s = delay_ms / 1000.0
    dt_s = dt_ms / 1000.0
    
    if state_type == "drone_state":
        return DroneStateLatencyBuffer(delay_s, dt_s)
    else:
        return LatencyBuffer(delay_s, dt_s) 