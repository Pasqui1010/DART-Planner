"""
Python wrapper for real-time control extension with thread-safe state management.

This module provides a high-level interface to the Cython real-time control
extension while integrating with the new thread-safe state buffer system.
"""

import time
import threading
from typing import Optional, Callable, Dict, Any
import numpy as np

from dart_planner.common.state_buffer import (
    ThreadSafeStateBuffer, 
    DroneStateBuffer, 
    FastDroneStateBuffer,
    StateSnapshot
)
from dart_planner.common.types import DroneState, FastDroneState, ControlCommand
from dart_planner.control.rt_control_extension import RealTimeControlLoop

class RealTimeControlWrapper:
    """
    High-level wrapper for real-time control with thread-safe state management.
    
    Integrates the Cython real-time control loop with the new state buffer
    system to prevent stale or mid-update state consumption.
    """
    
    def __init__(self, 
                 frequency_hz: float = 1000.0,
                 priority: int = 0,
                 state_buffer: Optional[ThreadSafeStateBuffer] = None,
                 use_fast_state: bool = True):
        """
        Initialize the real-time control wrapper.
        
        Args:
            frequency_hz: Control loop frequency in Hz
            priority: Thread priority level
            state_buffer: Optional state buffer (creates default if None)
            use_fast_state: Whether to use FastDroneState for high performance
        """
        self.frequency_hz = frequency_hz
        self.priority = priority
        self.use_fast_state = use_fast_state
        
        # Initialize state buffer
        if state_buffer is None:
            if use_fast_state:
                self.state_buffer = FastDroneStateBuffer()
            else:
                self.state_buffer = DroneStateBuffer()
        else:
            self.state_buffer = state_buffer
        
        # Initialize the Cython control loop
        self.control_loop = RealTimeControlLoop(frequency_hz, priority)
        
        # Set up callbacks
        self.control_loop.set_state_callback(self._on_state_update)
        self.control_loop.set_command_callback(self._on_command_update)
        self.control_loop.set_error_callback(self._on_error)
        
        # Control state
        self.running = False
        self.lock = threading.RLock()
        
        # Callbacks
        self.state_update_callback: Optional[Callable] = None
        self.command_update_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        # Statistics
        self._stats = {
            'control_iterations': 0,
            'state_updates': 0,
            'command_updates': 0,
            'errors': 0,
            'last_state_time': 0.0,
            'last_command_time': 0.0
        }
    
    def start(self):
        """Start the real-time control loop."""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            self.control_loop.start()
    
    def stop(self):
        """Stop the real-time control loop."""
        with self.lock:
            if not self.running:
                return
            
            self.running = False
            self.control_loop.stop()
    
    def is_running(self) -> bool:
        """Check if the control loop is running."""
        return self.running and self.control_loop.is_running()
    
    def update_state(self, state: DroneState, source: str = "external"):
        """
        Update the current vehicle state.
        
        Args:
            state: New drone state
            source: Source identifier for the update
        """
        if not isinstance(state, DroneState):
            raise TypeError(f"Expected DroneState, got {type(state)}")
        
        # Update the state buffer
        version = self.state_buffer.update_state(state, source)
        
        # Convert to format expected by Cython control loop
        if self.use_fast_state:
            fast_state = state.to_fast_state()
            position = fast_state.position
            velocity = fast_state.velocity
            attitude = fast_state.attitude
            angular_velocity = fast_state.angular_velocity
        else:
            position = state.position.to('m').magnitude
            velocity = state.velocity.to('m/s').magnitude
            attitude = state.attitude.to('rad').magnitude
            angular_velocity = state.angular_velocity.to('rad/s').magnitude
        
        # Update the Cython control loop
        self.control_loop.update_state(position, velocity, attitude, angular_velocity)
        
        self._stats['state_updates'] += 1
        self._stats['last_state_time'] = time.time()
        
        return version
    
    def update_command(self, 
                      position_setpoint: np.ndarray,
                      velocity_setpoint: np.ndarray,
                      attitude_setpoint: np.ndarray,
                      angular_velocity_setpoint: np.ndarray,
                      thrust: float):
        """
        Update the control command.
        
        Args:
            position_setpoint: Desired position (m)
            velocity_setpoint: Desired velocity (m/s)
            attitude_setpoint: Desired attitude (rad)
            angular_velocity_setpoint: Desired angular velocity (rad/s)
            thrust: Desired thrust (N)
        """
        self.control_loop.update_command(
            position_setpoint,
            velocity_setpoint,
            attitude_setpoint,
            angular_velocity_setpoint,
            thrust
        )
        
        self._stats['command_updates'] += 1
        self._stats['last_command_time'] = time.time()
    
    def get_latest_state(self) -> Optional[StateSnapshot]:
        """Get the latest state snapshot."""
        return self.state_buffer.get_latest_state()
    
    def get_state_at_time(self, target_time: float, max_age: float = 0.1) -> Optional[StateSnapshot]:
        """Get state closest to target time within max_age."""
        return self.state_buffer.get_state_at_time(target_time, max_age)
    
    def wait_for_state_update(self, timeout: float = 1.0) -> Optional[StateSnapshot]:
        """Wait for next state update."""
        return self.state_buffer.wait_for_update(timeout)
    
    async def wait_for_state_update_async(self, timeout: float = 1.0) -> Optional[StateSnapshot]:
        """Wait for next state update (async)."""
        return await self.state_buffer.wait_for_update_async(timeout)
    
    def set_state_update_callback(self, callback: Callable[[DroneState], None]):
        """Set callback for state updates."""
        self.state_update_callback = callback
    
    def set_command_update_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback for command updates."""
        self.command_update_callback = callback
    
    def set_error_callback(self, callback: Callable[[str], None]):
        """Set callback for error handling."""
        self.error_callback = callback
    
    def get_control_stats(self) -> Dict[str, Any]:
        """Get control loop statistics."""
        return self.control_loop.get_stats()
    
    def get_state_buffer_stats(self) -> Dict[str, Any]:
        """Get state buffer statistics."""
        return self.state_buffer.get_statistics()
    
    def get_combined_stats(self) -> Dict[str, Any]:
        """Get combined statistics from control loop and state buffer."""
        control_stats = self.get_control_stats()
        buffer_stats = self.get_state_buffer_stats()
        
        return {
            'control_loop': control_stats,
            'state_buffer': buffer_stats,
            'wrapper': self._stats,
            'running': self.is_running(),
            'frequency_hz': self.frequency_hz
        }
    
    def _on_state_update(self, state_dict: Dict[str, Any]):
        """Callback for state updates from control loop."""
        self._stats['control_iterations'] += 1
        
        if self.state_update_callback:
            # Convert back to DroneState if needed
            if self.use_fast_state:
                # Convert from FastDroneState back to DroneState
                from dart_planner.common.units import Q_
                
                state = DroneState(
                    timestamp=state_dict['timestamp'],
                    position=Q_(np.array(state_dict['position']), 'm'),
                    velocity=Q_(np.array(state_dict['velocity']), 'm/s'),
                    attitude=Q_(np.array(state_dict['attitude']), 'rad'),
                    angular_velocity=Q_(np.array(state_dict['angular_velocity']), 'rad/s')
                )
            else:
                # Already in DroneState format
                state = DroneState(
                    timestamp=state_dict['timestamp'],
                    position=Q_(np.array(state_dict['position']), 'm'),
                    velocity=Q_(np.array(state_dict['velocity']), 'm/s'),
                    attitude=Q_(np.array(state_dict['attitude']), 'rad'),
                    angular_velocity=Q_(np.array(state_dict['angular_velocity']), 'rad/s')
                )
            
            self.state_update_callback(state)
    
    def _on_command_update(self, command_dict: Dict[str, Any]):
        """Callback for command updates from control loop."""
        if self.command_update_callback:
            self.command_update_callback(command_dict)
    
    def _on_error(self, error_msg: str):
        """Callback for error handling."""
        self._stats['errors'] += 1
        
        if self.error_callback:
            self.error_callback(error_msg)


class StateEstimatorController:
    """
    High-level integration between state estimator and controller.
    
    Provides a clean interface for connecting state estimators to
    real-time controllers with proper thread-safe state management.
    """
    
    def __init__(self, 
                 estimator,
                 controller: RealTimeControlWrapper,
                 update_frequency_hz: float = 100.0):
        """
        Initialize the estimator-controller integration.
        
        Args:
            estimator: State estimator object with update() and get_latest() methods
            controller: Real-time control wrapper
            update_frequency_hz: Frequency for estimator updates
        """
        self.estimator = estimator
        self.controller = controller
        self.update_frequency_hz = update_frequency_hz
        self.update_period = 1.0 / update_frequency_hz
        
        # Threading
        self.running = False
        self.estimator_thread = None
        self.lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'estimator_updates': 0,
            'controller_updates': 0,
            'last_estimator_update': 0.0,
            'last_controller_update': 0.0
        }
    
    def start(self):
        """Start the estimator-controller integration."""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            
            # Start controller
            self.controller.start()
            
            # Start estimator thread
            self.estimator_thread = threading.Thread(
                target=self._estimator_loop,
                name="Estimator-Controller",
                daemon=True
            )
            self.estimator_thread.start()
    
    def stop(self):
        """Stop the estimator-controller integration."""
        with self.lock:
            if not self.running:
                return
            
            self.running = False
            
            # Stop controller
            self.controller.stop()
            
            # Wait for estimator thread
            if self.estimator_thread and self.estimator_thread.is_alive():
                self.estimator_thread.join(timeout=1.0)
    
    def is_running(self) -> bool:
        """Check if the integration is running."""
        return self.running and self.controller.is_running()
    
    def _estimator_loop(self):
        """Main estimator update loop."""
        last_update_time = 0.0
        
        while self.running:
            current_time = time.time()
            
            # Check if it's time for an update
            if current_time - last_update_time >= self.update_period:
                try:
                    # Update estimator
                    self.estimator.update()
                    
                    # Get latest state
                    estimated_state = self.estimator.get_latest()
                    
                    if estimated_state is not None:
                        # Convert to DroneState if needed
                        if hasattr(estimated_state, 'pose') and hasattr(estimated_state, 'twist'):
                            # It's an EstimatedState, convert to DroneState
                            from dart_planner.common.types import DroneState
                            drone_state = DroneState(
                                timestamp=estimated_state.timestamp,
                                position=estimated_state.pose.position,
                                velocity=estimated_state.twist.linear,
                                attitude=estimated_state.pose.orientation,
                                angular_velocity=estimated_state.twist.angular
                            )
                        else:
                            # Assume it's already a DroneState
                            drone_state = estimated_state
                        
                        # Update controller state
                        self.controller.update_state(drone_state, "estimator")
                        
                        self._stats['estimator_updates'] += 1
                        self._stats['last_estimator_update'] = current_time
                    
                    last_update_time = current_time
                    
                except Exception as e:
                    # Log error but continue
                    print(f"Estimator update error: {e}")
            
            # Sleep to maintain frequency
            time.sleep(0.001)  # 1ms sleep
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get combined statistics."""
        controller_stats = self.controller.get_combined_stats()
        
        return {
            'estimator_controller': self._stats,
            'controller': controller_stats,
            'running': self.is_running(),
            'update_frequency_hz': self.update_frequency_hz
        }


# Factory functions
def create_rt_control_wrapper(frequency_hz: float = 1000.0,
                            use_fast_state: bool = True) -> RealTimeControlWrapper:
    """Create a real-time control wrapper with default settings."""
    return RealTimeControlWrapper(frequency_hz=frequency_hz, use_fast_state=use_fast_state)

def create_estimator_controller(estimator,
                              frequency_hz: float = 1000.0,
                              estimator_frequency_hz: float = 100.0) -> StateEstimatorController:
    """Create an estimator-controller integration."""
    controller = create_rt_control_wrapper(frequency_hz)
    return StateEstimatorController(estimator, controller, estimator_frequency_hz) 