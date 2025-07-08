"""
Thread-safe state buffer for real-time control systems.

This module provides a thread-safe buffer system that prevents control loops
from consuming stale or mid-update estimator output. It uses a combination
of lock-free operations and proper synchronization to ensure data consistency.

Key features:
- Atomic state updates with versioning
- Lock-free reads for high-frequency control loops
- Configurable buffer size for different use cases
- Support for both DroneState and FastDroneState
- Integration with asyncio for communication layers
"""

import asyncio
import threading
import time
from typing import Optional, Generic, TypeVar, Dict, Any
from dataclasses import dataclass, field
from collections import deque
import numpy as np

from dart_planner.common.types import DroneState, FastDroneState

T = TypeVar('T', DroneState, FastDroneState)

@dataclass
class StateSnapshot(Generic[T]):
    """Atomic snapshot of state data with versioning."""
    state: Optional[T]  # <-- Make this Optional
    timestamp: float
    version: int
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

class ThreadSafeStateBuffer(Generic[T]):
    """
    Thread-safe state buffer with atomic updates and versioning.
    
    Provides lock-free reads for high-frequency control loops while ensuring
    atomic state updates from estimators. Uses double-buffering technique
    to prevent race conditions.
    """
    
    def __init__(self, buffer_size: int = 10, state_type: type = DroneState):
        self.buffer_size = buffer_size
        self.state_type = state_type
        
        # Double-buffered state storage
        self._current_buffer = 0
        self._buffers = [
            StateSnapshot[T](state=None, timestamp=0.0, version=0),
            StateSnapshot[T](state=None, timestamp=0.0, version=0)
        ]
        
        # Threading primitives
        self._update_lock = threading.RLock()
        self._version_counter = 0
        
        # Statistics
        self._stats = {
            'updates': 0,
            'reads': 0,
            'stale_reads': 0,
            'last_update_time': 0.0,
            'last_read_time': 0.0
        }
        
        # Async support
        self._update_event = asyncio.Event()
        self._subscribers: list[asyncio.Queue] = []
    
    def update_state(self, state: T, source: str = "unknown", 
                    metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Atomically update the state buffer.
        
        Args:
            state: New state data
            source: Source identifier for the update
            metadata: Optional metadata about the update
            
        Returns:
            Version number of the update
        """
        if not isinstance(state, self.state_type):
            raise TypeError(f"Expected {self.state_type}, got {type(state)}")
        
        with self._update_lock:
            # Increment version and switch buffers
            self._version_counter += 1
            self._current_buffer = 1 - self._current_buffer
            
            # Update the inactive buffer
            self._buffers[self._current_buffer] = StateSnapshot(
                state=state,
                timestamp=time.time(),
                version=self._version_counter,
                source=source,
                metadata=metadata or {}
            )
            
            # Update statistics
            self._stats['updates'] += 1
            self._stats['last_update_time'] = time.time()
            
            # Notify async subscribers
            self._notify_subscribers(state, self._version_counter)
            
            return self._version_counter
    
    def get_latest_state(self) -> Optional[StateSnapshot[T]]:
        """
        Get the latest state snapshot (lock-free read).
        
        Returns:
            Latest state snapshot or None if no state available
        """
        # Lock-free read from current buffer
        snapshot = self._buffers[self._current_buffer]
        
        if snapshot.state is None:
            return None
        
        self._stats['reads'] += 1
        self._stats['last_read_time'] = time.time()
        
        return snapshot
    
    def get_state_at_time(self, target_time: float, 
                         max_age: float = 0.1) -> Optional[StateSnapshot[T]]:
        """
        Get state closest to target time within max_age.
        
        Args:
            target_time: Target timestamp
            max_age: Maximum age of acceptable state (seconds)
            
        Returns:
            State snapshot or None if no suitable state found
        """
        snapshot = self.get_latest_state()
        if snapshot is None:
            return None
        
        age = abs(snapshot.timestamp - target_time)
        if age > max_age:
            self._stats['stale_reads'] += 1
            return None
        
        return snapshot
    
    def wait_for_update(self, timeout: float = 1.0) -> Optional[StateSnapshot[T]]:
        """
        Wait for next state update (blocking).
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            New state snapshot or None if timeout
        """
        start_time = time.time()
        initial_version = self._version_counter
        
        while time.time() - start_time < timeout:
            snapshot = self.get_latest_state()
            if snapshot and snapshot.version > initial_version:
                return snapshot
            time.sleep(0.001)  # 1ms sleep
        
        return None
    
    async def wait_for_update_async(self, timeout: float = 1.0) -> Optional[StateSnapshot[T]]:
        """
        Wait for next state update (async).
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            New state snapshot or None if timeout
        """
        try:
            await asyncio.wait_for(self._update_event.wait(), timeout=timeout)
            self._update_event.clear()
            return self.get_latest_state()
        except asyncio.TimeoutError:
            return None
    
    def subscribe(self, queue_size: int = 10) -> asyncio.Queue:
        """
        Subscribe to state updates via asyncio.Queue.
        
        Args:
            queue_size: Maximum queue size
            
        Returns:
            asyncio.Queue for receiving state updates
        """
        queue = asyncio.Queue(maxsize=queue_size)
        self._subscribers.append(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from state updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
    
    def _notify_subscribers(self, state: T, version: int):
        """Notify async subscribers of state updates."""
        if not self._subscribers:
            return
        
        # Create update event
        update_event = {
            'state': state,
            'version': version,
            'timestamp': time.time()
        }
        
        # Notify all subscribers (non-blocking)
        for queue in self._subscribers:
            try:
                queue.put_nowait(update_event)
            except asyncio.QueueFull:
                # Queue full, skip this subscriber
                pass
        
        # Set event for wait_for_update_async
        self._update_event.set()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get buffer statistics for monitoring."""
        return {
            'updates': self._stats['updates'],
            'reads': self._stats['reads'],
            'stale_reads': self._stats['stale_reads'],
            'current_version': self._version_counter,
            'last_update_time': self._stats['last_update_time'],
            'last_read_time': self._stats['last_read_time'],
            'subscriber_count': len(self._subscribers),
            'buffer_size': self.buffer_size
        }
    
    def reset(self):
        """Reset the buffer and statistics."""
        with self._update_lock:
            self._buffers = [
                StateSnapshot[T](state=None, timestamp=0.0, version=0),
                StateSnapshot[T](state=None, timestamp=0.0, version=0)
            ]
            self._version_counter = 0
            self._current_buffer = 0
            
            # Reset statistics
            self._stats = {
                'updates': 0,
                'reads': 0,
                'stale_reads': 0,
                'last_update_time': 0.0,
                'last_read_time': 0.0
            }
            
            # Clear subscribers
            self._subscribers.clear()
            self._update_event.clear()


class DroneStateBuffer(ThreadSafeStateBuffer[DroneState]):
    """Specialized state buffer for DroneState objects."""
    
    def __init__(self, buffer_size: int = 10):
        super().__init__(buffer_size, DroneState)
    
    def update_from_estimator(self, estimated_state, source: str = "estimator"):
        """Update state from estimator output."""
        if hasattr(estimated_state, 'pose') and hasattr(estimated_state, 'twist'):
            # Convert EstimatedState to DroneState
            drone_state = DroneState(
                timestamp=estimated_state.timestamp,
                position=estimated_state.pose.position,
                velocity=estimated_state.twist.linear,
                attitude=estimated_state.pose.orientation,
                angular_velocity=estimated_state.twist.angular
            )
            return self.update_state(drone_state, source)
        else:
            # Assume it's already a DroneState
            return self.update_state(estimated_state, source)


class FastDroneStateBuffer(ThreadSafeStateBuffer[FastDroneState]):
    """Specialized state buffer for FastDroneState objects (high-frequency control)."""
    
    def __init__(self, buffer_size: int = 5):  # Smaller buffer for high-frequency
        super().__init__(buffer_size, FastDroneState)
    
    def update_from_drone_state(self, drone_state: DroneState, source: str = "converter"):
        """Update from DroneState by converting to FastDroneState."""
        fast_state = drone_state.to_fast_state()
        return self.update_state(fast_state, source)


class StateManager:
    """
    High-level state manager coordinating multiple state buffers.
    
    Provides a unified interface for managing state across different
    components (estimators, controllers, planners).
    """
    
    def __init__(self):
        self._buffers: Dict[str, ThreadSafeStateBuffer] = {}
        self._lock = threading.RLock()
    
    def register_buffer(self, name: str, buffer: ThreadSafeStateBuffer):
        """Register a state buffer with a name."""
        with self._lock:
            self._buffers[name] = buffer
    
    def get_buffer(self, name: str) -> Optional[ThreadSafeStateBuffer]:
        """Get a registered buffer by name."""
        with self._lock:
            return self._buffers.get(name)
    
    def update_state(self, buffer_name: str, state, source: str = "unknown",
                    metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Update state in a specific buffer."""
        buffer = self.get_buffer(buffer_name)
        if buffer is None:
            return None
        return buffer.update_state(state, source, metadata)
    
    def get_latest_state(self, buffer_name: str) -> Optional[StateSnapshot]:
        """Get latest state from a specific buffer."""
        buffer = self.get_buffer(buffer_name)
        if buffer is None:
            return None
        return buffer.get_latest_state()
    
    def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics from all buffers."""
        with self._lock:
            return {name: buffer.get_statistics() 
                   for name, buffer in self._buffers.items()}
    
    def reset_all(self):
        """Reset all buffers."""
        with self._lock:
            for buffer in self._buffers.values():
                buffer.reset()


# Factory functions for common use cases
def create_drone_state_buffer(buffer_size: int = 10) -> DroneStateBuffer:
    """Create a DroneState buffer for general use."""
    return DroneStateBuffer(buffer_size)

def create_fast_state_buffer(buffer_size: int = 5) -> FastDroneStateBuffer:
    """Create a FastDroneState buffer for high-frequency control."""
    return FastDroneStateBuffer(buffer_size)

def create_state_manager() -> StateManager:
    """Create a state manager for coordinating multiple buffers."""
    return StateManager() 