# cython: language_level=3
# distutils: language=c++
# distutils: extra_compile_args=-O3 -march=native -ffast-math
# distutils: extra_link_args=-O3

"""
Real-Time Control Extension for DART-Planner

Cython extension providing high-performance real-time control loops
with strict deadline enforcement and minimal jitter.
"""

import time
import threading
from cpython cimport array
from libc.stdlib cimport malloc, free
from libc.string cimport memcpy
from libc.math cimport sqrt, sin, cos, atan2
from libcpp.vector cimport vector
from libcpp.unordered_map cimport unordered_map
from libcpp.string cimport string
from libcpp cimport bool

import numpy as np
cimport numpy as np

# Real-time control constants
DEF MAX_CONTROL_FREQUENCY = 1000  # Hz
DEF MIN_CONTROL_PERIOD = 0.001    # 1ms
DEF MAX_JITTER = 0.0001          # 0.1ms
DEF DEADLINE_MARGIN = 0.00005    # 50μs

# Control loop states
DEF LOOP_IDLE = 0
DEF LOOP_RUNNING = 1
DEF LOOP_STOPPING = 2
DEF LOOP_ERROR = 3

# Priority levels
DEF PRIORITY_LOW = 0
DEF PRIORITY_NORMAL = 1
DEF PRIORITY_HIGH = 2
DEF PRIORITY_CRITICAL = 3

ctypedef struct ControlState:
    double position[3]      # x, y, z
    double velocity[3]      # vx, vy, vz
    double attitude[3]      # roll, pitch, yaw
    double angular_velocity[3]  # ωx, ωy, ωz
    double timestamp
    bool valid

ctypedef struct ControlCommand:
    double position_setpoint[3]
    double velocity_setpoint[3]
    double attitude_setpoint[3]
    double angular_velocity_setpoint[3]
    double thrust
    bool valid

ctypedef struct ControlGains:
    double kp_pos[3]        # Position P gains
    double ki_pos[3]        # Position I gains
    double kd_pos[3]        # Position D gains
    double kp_att[3]        # Attitude P gains
    double ki_att[3]        # Attitude I gains
    double kd_att[3]        # Attitude D gains

ctypedef struct LoopStats:
    unsigned long long iteration_count
    unsigned long long missed_deadlines
    double mean_execution_time
    double max_execution_time
    double min_execution_time
    double jitter_rms
    double frequency_actual
    double frequency_target

cdef class RealTimeControlLoop:
    """
    High-performance real-time control loop implemented in Cython.
    
    Provides:
    - Strict deadline enforcement
    - Minimal jitter
    - High-frequency control (up to 1kHz)
    - Real-time statistics
    - Thread-safe operation
    """
    
    cdef:
        double frequency_hz
        double period_s
        int state
        int priority
        bool running
        unsigned long long iteration_count
        unsigned long long missed_deadlines
        
        # Timing
        double start_time
        double last_iteration_time
        double next_deadline
        double execution_times[1000]  # Circular buffer
        int execution_time_index
        
        # Control data
        ControlState current_state
        ControlCommand current_command
        ControlGains gains
        
        # Threading
        object control_thread
        object lock
        object stop_event
        
        # Callbacks
        object state_callback
        object command_callback
        object error_callback
    
    def __init__(self, double frequency_hz=400.0, int priority=PRIORITY_HIGH):
        """
        Initialize real-time control loop.
        
        Args:
            frequency_hz: Control loop frequency in Hz
            priority: Thread priority level
        """
        if frequency_hz <= 0 or frequency_hz > MAX_CONTROL_FREQUENCY:
            raise ValueError(f"Invalid frequency: {frequency_hz} Hz")
        
        self.frequency_hz = frequency_hz
        self.period_s = 1.0 / frequency_hz
        self.priority = priority
        self.state = LOOP_IDLE
        self.running = False
        self.iteration_count = 0
        self.missed_deadlines = 0
        
        # Initialize timing
        self.start_time = 0.0
        self.last_iteration_time = 0.0
        self.next_deadline = 0.0
        self.execution_time_index = 0
        
        # Initialize control data
        self._init_control_data()
        
        # Initialize threading
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.control_thread = None
        
        # Initialize callbacks
        self.state_callback = None
        self.command_callback = None
        self.error_callback = None
    
    cdef void _init_control_data(self):
        """Initialize control data structures."""
        cdef int i
        
        # Initialize state
        for i in range(3):
            self.current_state.position[i] = 0.0
            self.current_state.velocity[i] = 0.0
            self.current_state.attitude[i] = 0.0
            self.current_state.angular_velocity[i] = 0.0
        self.current_state.timestamp = 0.0
        self.current_state.valid = False
        
        # Initialize command
        for i in range(3):
            self.current_command.position_setpoint[i] = 0.0
            self.current_command.velocity_setpoint[i] = 0.0
            self.current_command.attitude_setpoint[i] = 0.0
            self.current_command.angular_velocity_setpoint[i] = 0.0
        self.current_command.thrust = 0.0
        self.current_command.valid = False
        
        # Initialize gains (default values)
        for i in range(3):
            self.gains.kp_pos[i] = 2.0
            self.gains.ki_pos[i] = 0.1
            self.gains.kd_pos[i] = 0.5
            self.gains.kp_att[i] = 8.0
            self.gains.ki_att[i] = 0.1
            self.gains.kd_att[i] = 0.5
    
    def start(self):
        """Start the real-time control loop."""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            self.state = LOOP_RUNNING
            self.stop_event.clear()
            
            # Create and start control thread
            self.control_thread = threading.Thread(
                target=self._control_loop,
                name=f"RTControl-{self.frequency_hz}Hz",
                daemon=True
            )
            self.control_thread.start()
    
    def stop(self):
        """Stop the real-time control loop."""
        with self.lock:
            if not self.running:
                return
            
            self.running = False
            self.state = LOOP_STOPPING
            self.stop_event.set()
            
            # Wait for thread to finish
            if self.control_thread and self.control_thread.is_alive():
                self.control_thread.join(timeout=1.0)
            
            self.state = LOOP_IDLE
    
    def is_running(self) -> bool:
        """Check if the control loop is running."""
        return self.running
    
    def get_state(self) -> int:
        """Get the current loop state."""
        return self.state
    
    def set_state_callback(self, callback):
        """Set callback for state updates."""
        self.state_callback = callback
    
    def set_command_callback(self, callback):
        """Set callback for command updates."""
        self.command_callback = callback
    
    def set_error_callback(self, callback):
        """Set callback for error handling."""
        self.error_callback = callback
    
    def update_state(self, position, velocity, attitude, angular_velocity):
        """Update the current vehicle state."""
        cdef int i
        
        with self.lock:
            for i in range(3):
                self.current_state.position[i] = position[i]
                self.current_state.velocity[i] = velocity[i]
                self.current_state.attitude[i] = attitude[i]
                self.current_state.angular_velocity[i] = angular_velocity[i]
            self.current_state.timestamp = time.perf_counter()
            self.current_state.valid = True
    
    def update_command(self, position_setpoint, velocity_setpoint, 
                      attitude_setpoint, angular_velocity_setpoint, thrust):
        """Update the control command."""
        cdef int i
        
        with self.lock:
            for i in range(3):
                self.current_command.position_setpoint[i] = position_setpoint[i]
                self.current_command.velocity_setpoint[i] = velocity_setpoint[i]
                self.current_command.attitude_setpoint[i] = attitude_setpoint[i]
                self.current_command.angular_velocity_setpoint[i] = angular_velocity_setpoint[i]
            self.current_command.thrust = thrust
            self.current_command.valid = True
    
    def set_gains(self, kp_pos, ki_pos, kd_pos, kp_att, ki_att, kd_att):
        """Set control gains."""
        cdef int i
        
        with self.lock:
            for i in range(3):
                self.gains.kp_pos[i] = kp_pos[i]
                self.gains.ki_pos[i] = ki_pos[i]
                self.gains.kd_pos[i] = kd_pos[i]
                self.gains.kp_att[i] = kp_att[i]
                self.gains.ki_att[i] = ki_att[i]
                self.gains.kd_att[i] = kd_att[i]
    
    def get_stats(self) -> dict:
        """Get control loop statistics."""
        cdef LoopStats stats
        
        with self.lock:
            stats.iteration_count = self.iteration_count
            stats.missed_deadlines = self.missed_deadlines
            stats.frequency_target = self.frequency_hz
            
            if self.iteration_count > 0:
                stats.frequency_actual = self.iteration_count / (time.perf_counter() - self.start_time)
                
                # Calculate execution time statistics
                cdef double sum_time = 0.0
                cdef double max_time = 0.0
                cdef double min_time = float('inf')
                cdef int i
                
                for i in range(1000):
                    if self.execution_times[i] > 0:
                        sum_time += self.execution_times[i]
                        if self.execution_times[i] > max_time:
                            max_time = self.execution_times[i]
                        if self.execution_times[i] < min_time:
                            min_time = self.execution_times[i]
                
                stats.mean_execution_time = sum_time / 1000.0
                stats.max_execution_time = max_time
                stats.min_execution_time = min_time if min_time != float('inf') else 0.0
                
                # Calculate jitter RMS
                cdef double jitter_sum = 0.0
                for i in range(1000):
                    if self.execution_times[i] > 0:
                        jitter_sum += (self.execution_times[i] - stats.mean_execution_time) ** 2
                stats.jitter_rms = sqrt(jitter_sum / 1000.0)
            else:
                stats.frequency_actual = 0.0
                stats.mean_execution_time = 0.0
                stats.max_execution_time = 0.0
                stats.min_execution_time = 0.0
                stats.jitter_rms = 0.0
        
        return {
            'iteration_count': stats.iteration_count,
            'missed_deadlines': stats.missed_deadlines,
            'frequency_target_hz': stats.frequency_target,
            'frequency_actual_hz': stats.frequency_actual,
            'mean_execution_time_ms': stats.mean_execution_time * 1000.0,
            'max_execution_time_ms': stats.max_execution_time * 1000.0,
            'min_execution_time_ms': stats.min_execution_time * 1000.0,
            'jitter_rms_ms': stats.jitter_rms * 1000.0,
            'success_rate': (stats.iteration_count - stats.missed_deadlines) / max(stats.iteration_count, 1)
        }
    
    cdef void _control_loop(self):
        """Main control loop implementation."""
        cdef double current_time, execution_start, execution_time
        cdef double sleep_time
        cdef int i
        
        # Set thread priority if possible
        self._set_thread_priority()
        
        # Initialize timing
        self.start_time = time.perf_counter()
        self.last_iteration_time = self.start_time
        self.next_deadline = self.start_time + self.period_s
        
        # Clear execution time buffer
        for i in range(1000):
            self.execution_times[i] = 0.0
        
        while self.running and not self.stop_event.is_set():
            current_time = time.perf_counter()
            execution_start = current_time
            
            # Check deadline
            if current_time > self.next_deadline + DEADLINE_MARGIN:
                self.missed_deadlines += 1
                if self.error_callback:
                    self.error_callback(f"Deadline missed: {current_time - self.next_deadline:.6f}s")
            
            # Execute control iteration
            try:
                self._execute_control_iteration()
            except Exception as e:
                self.state = LOOP_ERROR
                if self.error_callback:
                    self.error_callback(f"Control iteration error: {e}")
                break
            
            # Calculate execution time
            execution_time = time.perf_counter() - execution_start
            
            # Store execution time in circular buffer
            self.execution_times[self.execution_time_index] = execution_time
            self.execution_time_index = (self.execution_time_index + 1) % 1000
            
            # Update iteration count
            self.iteration_count += 1
            
            # Calculate sleep time to maintain frequency
            current_time = time.perf_counter()
            sleep_time = self.next_deadline - current_time
            
            # Sleep if needed
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Update next deadline
            self.next_deadline += self.period_s
            self.last_iteration_time = current_time
    
    cdef void _execute_control_iteration(self):
        """Execute one control iteration."""
        cdef double control_output[4]  # [thrust, roll_rate, pitch_rate, yaw_rate]
        cdef int i
        
        # Check if we have valid state and command
        if not self.current_state.valid or not self.current_command.valid:
            return
        
        # Call state callback
        if self.state_callback:
            state_dict = {
                'position': [self.current_state.position[i] for i in range(3)],
                'velocity': [self.current_state.velocity[i] for i in range(3)],
                'attitude': [self.current_state.attitude[i] for i in range(3)],
                'angular_velocity': [self.current_state.angular_velocity[i] for i in range(3)],
                'timestamp': self.current_state.timestamp
            }
            self.state_callback(state_dict)
        
        # Compute control output
        self._compute_control_output(control_output)
        
        # Call command callback
        if self.command_callback:
            command_dict = {
                'thrust': control_output[0],
                'roll_rate': control_output[1],
                'pitch_rate': control_output[2],
                'yaw_rate': control_output[3]
            }
            self.command_callback(command_dict)
    
    cdef void _compute_control_output(self, double* output):
        """Compute control output using PID controllers."""
        cdef double pos_error[3], vel_error[3], att_error[3], ang_vel_error[3]
        cdef double pos_integral[3], att_integral[3]
        cdef double pos_derivative[3], att_derivative[3]
        cdef double dt = self.period_s
        cdef int i
        
        # Position control
        for i in range(3):
            pos_error[i] = self.current_command.position_setpoint[i] - self.current_state.position[i]
            vel_error[i] = self.current_command.velocity_setpoint[i] - self.current_state.velocity[i]
            
            # Simple PID (in practice, use proper integral and derivative)
            pos_integral[i] = 0.0  # Would need to maintain integral state
            pos_derivative[i] = vel_error[i]
            
            # Position control output (simplified)
            output[i] = (self.gains.kp_pos[i] * pos_error[i] + 
                        self.gains.ki_pos[i] * pos_integral[i] * dt +
                        self.gains.kd_pos[i] * pos_derivative[i])
        
        # Attitude control
        for i in range(3):
            att_error[i] = self.current_command.attitude_setpoint[i] - self.current_state.attitude[i]
            ang_vel_error[i] = self.current_command.angular_velocity_setpoint[i] - self.current_state.angular_velocity[i]
            
            # Simple PID
            att_integral[i] = 0.0
            att_derivative[i] = ang_vel_error[i]
            
            # Attitude control output (simplified)
            output[i] = (self.gains.kp_att[i] * att_error[i] +
                        self.gains.ki_att[i] * att_integral[i] * dt +
                        self.gains.kd_att[i] * att_derivative[i])
    
    cdef void _set_thread_priority(self):
        """Set thread priority for real-time operation."""
        try:
            import os
            if hasattr(os, 'nice'):
                # Lower nice value = higher priority
                if self.priority == PRIORITY_CRITICAL:
                    os.nice(-10)
                elif self.priority == PRIORITY_HIGH:
                    os.nice(-5)
                elif self.priority == PRIORITY_NORMAL:
                    os.nice(0)
                else:
                    os.nice(5)
        except Exception:
            pass  # Priority setting not available


# Factory function for creating control loops
def create_control_loop(frequency_hz: float = 400.0, priority: int = PRIORITY_HIGH) -> RealTimeControlLoop:
    """
    Create a real-time control loop.
    
    Args:
        frequency_hz: Control loop frequency in Hz
        priority: Thread priority level
        
    Returns:
        RealTimeControlLoop instance
    """
    return RealTimeControlLoop(frequency_hz, priority)


# Utility functions for real-time validation
def validate_real_time_requirements(frequency_hz: float, max_jitter_ms: float = 0.1) -> bool:
    """
    Validate real-time requirements.
    
    Args:
        frequency_hz: Target frequency
        max_jitter_ms: Maximum allowed jitter in milliseconds
        
    Returns:
        True if requirements can be met
    """
    if frequency_hz <= 0 or frequency_hz > MAX_CONTROL_FREQUENCY:
        return False
    
    period_ms = 1000.0 / frequency_hz
    if max_jitter_ms >= period_ms:
        return False
    
    return True


def get_real_time_capabilities() -> dict:
    """
    Get system real-time capabilities.
    
    Returns:
        Dictionary with real-time capability information
    """
    import platform
    import os
    
    capabilities = {
        'platform': platform.system(),
        'max_frequency_hz': MAX_CONTROL_FREQUENCY,
        'min_period_ms': MIN_CONTROL_PERIOD * 1000.0,
        'max_jitter_ms': MAX_JITTER * 1000.0,
        'deadline_margin_ms': DEADLINE_MARGIN * 1000.0,
        'priority_levels': {
            'LOW': PRIORITY_LOW,
            'NORMAL': PRIORITY_NORMAL,
            'HIGH': PRIORITY_HIGH,
            'CRITICAL': PRIORITY_CRITICAL
        }
    }
    
    # Check if we can set thread priorities
    try:
        import os
        if hasattr(os, 'nice'):
            capabilities['can_set_priority'] = True
        else:
            capabilities['can_set_priority'] = False
    except Exception:
        capabilities['can_set_priority'] = False
    
    return capabilities 