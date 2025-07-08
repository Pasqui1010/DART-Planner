"""
Timing Alignment Module for DART-Planner

This module handles synchronization between different system components
with different operating frequencies, particularly between the planner
and controller.
"""

import time
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

import numpy as np
import threading
import contextvars

from .types import Trajectory


class TimingMode(Enum):
    """Timing synchronization modes."""
    PLANNER_DRIVEN = "planner_driven"  # Controller waits for planner
    CONTROLLER_DRIVEN = "controller_driven"  # Planner throttled to controller
    ADAPTIVE = "adaptive"  # Automatically adjust based on performance


@dataclass
class TimingConfig:
    """Configuration for timing alignment."""
    control_frequency: float = 400.0  # Hz
    planning_frequency: float = 50.0  # Hz
    mode: TimingMode = TimingMode.ADAPTIVE
    max_planning_latency: float = 0.1  # seconds
    min_planning_interval: float = 0.01  # seconds
    enable_throttling: bool = True
    enable_interpolation: bool = True


class TimingManager:
    """
    Manages timing synchronization between planner and controller.
    
    This class ensures that:
    1. Planner dt is set to 1/control_frequency by default
    2. Controller is throttled when planner outputs slower
    3. Smooth interpolation between planner outputs
    """
    
    def __init__(self, config: TimingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Calculate derived timing parameters
        self.control_dt = 1.0 / config.control_frequency
        self.planning_dt = 1.0 / config.planning_frequency
        
        # Timing state
        self.last_plan_time = 0.0
        self.last_control_time = 0.0
        self.planning_latency = 0.0
        self.control_skips = 0
        self.interpolation_factor = 1.0
        
        # Performance tracking
        self.planning_times = []
        self.control_times = []
        self.throttling_events = 0
        
        self.logger.info(f"Timing manager initialized:")
        self.logger.info(f"  Control frequency: {config.control_frequency} Hz (dt={self.control_dt:.3f}s)")
        self.logger.info(f"  Planning frequency: {config.planning_frequency} Hz (dt={self.planning_dt:.3f}s)")
        self.logger.info(f"  Mode: {config.mode.value}")
    
    def get_planner_dt(self) -> float:
        """Get the recommended planner time step based on control frequency."""
        return self.control_dt
    
    def should_plan(self, current_time: float) -> bool:
        """Determine if a new plan should be generated."""
        if not self.config.enable_throttling:
            return True
        
        time_since_last_plan = current_time - self.last_plan_time
        
        # Check if enough time has passed for planning
        if time_since_last_plan < self.config.min_planning_interval:
            return False
        
        # Check if planning latency is acceptable
        if self.planning_latency > self.config.max_planning_latency:
            self.throttling_events += 1
            self.logger.warning(f"Planning throttled due to high latency: {self.planning_latency:.3f}s")
            return False
        
        # Update last plan time to prevent immediate re-planning
        self.last_plan_time = current_time
        return True
    
    def should_control(self, current_time: float) -> bool:
        """Determine if control should be executed."""
        if not self.config.enable_throttling:
            return True
        
        time_since_last_control = current_time - self.last_control_time
        
        # Always allow control at the specified frequency
        if time_since_last_control >= self.control_dt:
            # Update last control time to prevent immediate re-execution
            self.last_control_time = current_time
            return True
        
        return False
    
    def update_planning_timing(self, planning_time: float, planning_duration: float):
        """Update timing information after planning."""
        self.last_plan_time = planning_time
        self.planning_latency = planning_duration
        self.planning_times.append(planning_duration)
        
        # Keep only recent planning times for statistics
        if len(self.planning_times) > 100:
            self.planning_times = self.planning_times[-100:]
    
    def update_control_timing(self, control_time: float):
        """Update timing information after control execution using elapsed time deltas."""
        # Calculate delta since last control; use control_dt if this is first update
        if self.last_control_time:
            delta = control_time - self.last_control_time
        else:
            delta = self.control_dt
        # Update last control timestamp
        self.last_control_time = control_time
        # Record duration delta
        self.control_times.append(delta)
        # Keep only recent control deltas for statistics
        if len(self.control_times) > 1000:
            self.control_times = self.control_times[-1000:]
    
    def interpolate_trajectory(self, trajectory: Optional['Trajectory'], target_time: float) -> Optional[np.ndarray]:
        """
        Interpolate trajectory to get state at target time.
        
        Args:
            trajectory: The trajectory to interpolate
            target_time: Target time for interpolation
            
        Returns:
            Interpolated state (position, velocity, attitude) or None if not possible
        """
        if not self.config.enable_interpolation or trajectory is None:
            return None
        
        if len(trajectory.timestamps) == 0:
            return None
        
        # Find the two trajectory points to interpolate between
        timestamps = trajectory.timestamps
        
        # Handle edge cases
        if target_time <= timestamps[0]:
            return np.concatenate([
                trajectory.positions[0],
                trajectory.velocities[0] if trajectory.velocities is not None else np.zeros(3),
                trajectory.attitudes[0] if trajectory.attitudes is not None else np.zeros(3)
            ])
        
        if target_time >= timestamps[-1]:
            return np.concatenate([
                trajectory.positions[-1],
                trajectory.velocities[-1] if trajectory.velocities is not None else np.zeros(3),
                trajectory.attitudes[-1] if trajectory.attitudes is not None else np.zeros(3)
            ])
        
        # Find interpolation interval
        for i in range(len(timestamps) - 1):
            if timestamps[i] <= target_time <= timestamps[i + 1]:
                # Linear interpolation
                alpha = (target_time - timestamps[i]) / (timestamps[i + 1] - timestamps[i])
                
                # Interpolate position
                pos = (1 - alpha) * trajectory.positions[i] + alpha * trajectory.positions[i + 1]
                
                # Interpolate velocity if available
                if trajectory.velocities is not None:
                    vel = (1 - alpha) * trajectory.velocities[i] + alpha * trajectory.velocities[i + 1]
                else:
                    vel = np.zeros(3)
                
                # Interpolate attitude if available
                if trajectory.attitudes is not None:
                    # For attitudes, use SLERP (Spherical Linear Interpolation) for quaternions
                    # or simple linear interpolation for Euler angles
                    if len(trajectory.attitudes[i]) == 4:  # Quaternion
                        # Simple linear interpolation for quaternions (not ideal but fast)
                        att = (1 - alpha) * trajectory.attitudes[i] + alpha * trajectory.attitudes[i + 1]
                        # Normalize
                        att = att / np.linalg.norm(att)
                    else:  # Euler angles
                        att = (1 - alpha) * trajectory.attitudes[i] + alpha * trajectory.attitudes[i + 1]
                else:
                    att = np.zeros(3)
                
                return np.concatenate([pos, vel, att])
        
        return None
    
    def get_timing_stats(self) -> Dict[str, Any]:
        """Get timing performance statistics."""
        if not self.planning_times:
            return {}
        
        return {
            "avg_planning_time": np.mean(self.planning_times),
            "max_planning_time": np.max(self.planning_times),
            "planning_frequency": 1.0 / np.mean(self.planning_times) if self.planning_times else 0.0,
            "throttling_events": self.throttling_events,
            "control_dt": self.control_dt,
            "planning_dt": self.planning_dt,
            "last_planning_latency": self.planning_latency,
            "timing_mode": self.config.mode.value,
        }
    
    def reset_stats(self):
        """Reset timing statistics."""
        self.planning_times.clear()
        self.control_times.clear()
        self.throttling_events = 0
        self.planning_latency = 0.0


class ControllerThrottler:
    """
    Throttles controller execution based on planner performance.
    
    This ensures the controller doesn't run faster than the planner
    can provide new trajectories, while maintaining smooth operation.
    """
    
    def __init__(self, timing_manager: TimingManager):
        self.timing_manager = timing_manager
        self.logger = logging.getLogger(__name__)
        self.current_trajectory = None
        self.last_control_state = None
        
    def should_execute_control(self, current_time: float) -> bool:
        """Determine if control should be executed."""
        return self.timing_manager.should_control(current_time)
    
    def get_control_state(self, current_time: float) -> Optional[np.ndarray]:
        """
        Get the current control state by interpolating the trajectory.
        
        Args:
            current_time: Current time for interpolation
            
        Returns:
            Interpolated state or None if no trajectory available
        """
        if self.current_trajectory is None:
            return None
        
        return self.timing_manager.interpolate_trajectory(self.current_trajectory, current_time)
    
    def update_trajectory(self, trajectory: 'Trajectory'):
        """Update the current trajectory for interpolation."""
        self.current_trajectory = trajectory
    
    def get_throttling_info(self) -> Dict[str, Any]:
        """Get information about throttling status."""
        return {
            "has_trajectory": self.current_trajectory is not None,
            "trajectory_length": len(self.current_trajectory.timestamps) if self.current_trajectory else 0,
            "timing_stats": self.timing_manager.get_timing_stats(),
        }


# Global timing manager instance
# _timing_manager: Optional[TimingManager] = None
_timing_manager_ctx: contextvars.ContextVar = contextvars.ContextVar("_timing_manager_ctx", default=None)
_timing_manager_lock = threading.Lock()

def get_timing_manager(config: Optional[TimingConfig] = None) -> TimingManager:
    """Get the global timing manager instance."""
    manager = _timing_manager_ctx.get()
    if manager is None:
        with _timing_manager_lock:
            manager = _timing_manager_ctx.get()
            if manager is None:
                if config is None:
                    # Create default config from frozen config
                    from ..config.frozen_config import get_frozen_config
                    system_config = get_frozen_config()
                    config = TimingConfig(
                        control_frequency=system_config.real_time.control_loop_frequency_hz,
                        planning_frequency=system_config.real_time.planning_loop_frequency_hz,
                        max_planning_latency=system_config.real_time.max_planning_latency_ms / 1000.0,  # Convert ms to s
                        min_planning_interval=1.0 / system_config.real_time.planning_loop_frequency_hz,  # Convert frequency to interval
                        enable_throttling=True,  # Default to True for safety
                        enable_interpolation=True,  # Default to True for smooth operation
                    )
                manager = TimingManager(config)
                _timing_manager_ctx.set(manager)
    return manager

def reset_timing_manager():
    """Reset the global timing manager."""
    _timing_manager_ctx.set(None) 