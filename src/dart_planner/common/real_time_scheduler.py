"""
Real-Time Scheduling System for DART-Planner

This module provides a comprehensive real-time scheduling system that:
1. Replaces blocking sleep with async sleep
2. Implements proper real-time scheduling with priority management
3. Adds timing compensation for jitter and drift
4. Uses real-time operating system features when available
5. Provides deadline monitoring and missed deadline recovery
"""

import asyncio
import time
import threading
import platform
import os
import signal
from typing import Callable, Optional, Dict, List, Any, Union
from contextlib import asynccontextmanager
import numpy as np
from collections import deque

from dart_planner.common.errors import RealTimeError, SchedulingError
from dart_planner.common.types import DroneState
from .real_time_config import (
    TaskPriority, TaskType, RealTimeTask, TimingStats, SchedulerConfig
)
from .real_time_core import (
    check_rt_os_support, get_rt_priority, setup_rt_os,
    should_execute_task, update_task_stats, handle_deadline_violation,
    apply_timing_compensation, schedule_next_execution, calculate_sleep_time
)
from .logging_config import get_logger


class RealTimeScheduler:
    """
    Real-time scheduler with priority-based scheduling and timing compensation.
    
    Features:
    - Priority-based preemptive scheduling
    - Timing compensation for jitter and drift
    - Deadline monitoring and missed deadline recovery
    - Real-time operating system integration
    - Performance monitoring and statistics
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        """Initialize the real-time scheduler."""
        self.config = config or SchedulerConfig()
        self.tasks: Dict[str, RealTimeTask] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Timing compensation
        self.clock_drift_compensation = 0.0
        self.jitter_compensation = 0.0
        self.timing_stats: Dict[str, TimingStats] = {}
        
        # Track previous stats to calculate increments correctly
        self.previous_stats: Dict[str, TimingStats] = {}
        
        # Real-time OS features
        self.enable_rt_os = self.config.enable_rt_os and check_rt_os_support()
        self.rt_priority = get_rt_priority()
        
        # Performance monitoring
        self.monitoring_enabled = self.config.monitoring_enabled
        self.global_stats = {
            'total_cycles': 0,
            'missed_deadlines': 0,
            'average_cycle_time_ms': 0.0,
            'max_cycle_time_ms': 0.0,
        }
        
        # Initialize real-time features
        if self.enable_rt_os:
            setup_rt_os(self.config)
        
        # Initialize logger
        self.logger = get_logger(__name__)
    

    
    def add_task(self, task: RealTimeTask) -> None:
        """Add a real-time task to the scheduler."""
        if task.name in self.tasks:
            raise SchedulingError(f"Task '{task.name}' already exists")
        
        self.tasks[task.name] = task
        self.timing_stats[task.name] = TimingStats(task_name=task.name)
        self.previous_stats[task.name] = TimingStats(task_name=task.name)
        
        # Initialize timing for periodic tasks
        if task.task_type == TaskType.PERIODIC and task.period_ms > 0:
            task.next_deadline = time.perf_counter() + (task.period_ms / 1000.0)
    
    def remove_task(self, task_name: str) -> None:
        """Remove a task from the scheduler."""
        if task_name in self.tasks:
            del self.tasks[task_name]
            if task_name in self.timing_stats:
                del self.timing_stats[task_name]
            if task_name in self.previous_stats:
                del self.previous_stats[task_name]
    
    def enable_task(self, task_name: str) -> None:
        """Enable a task."""
        if task_name in self.tasks:
            self.tasks[task_name].enabled = True
    
    def disable_task(self, task_name: str) -> None:
        """Disable a task."""
        if task_name in self.tasks:
            self.tasks[task_name].enabled = False
    
    async def start(self) -> None:
        """Start the real-time scheduler."""
        if self.running:
            return
        
        self.running = True
        self.loop = asyncio.get_event_loop()
        
        # Start monitoring task
        asyncio.create_task(self._monitor_performance())
        
        # Start all enabled tasks
        for task in self.tasks.values():
            if task.enabled:
                asyncio.create_task(self._run_task(task))
        
        self.logger.info("Real-time scheduler started")
    
    async def stop(self) -> None:
        """Stop the real-time scheduler."""
        self.running = False
        self.logger.info("Real-time scheduler stopped")
    
    async def _run_task(self, task: RealTimeTask) -> None:
        """Run a single real-time task."""
        while self.running and task.enabled:
            try:
                current_time = time.perf_counter()
                
                # Check if it's time to execute
                if self._should_execute_task(task, current_time):
                    # Execute task with timing measurement
                    execution_start = time.perf_counter()
                    
                    if asyncio.iscoroutinefunction(task.func):
                        await task.func()
                    else:
                        # Run synchronous function in thread pool
                        if self.loop:
                            await self.loop.run_in_executor(None, task.func)
                        else:
                            task.func()
                    
                    execution_time = (time.perf_counter() - execution_start) * 1000.0
                    
                    # Update task statistics
                    self._update_task_stats(task, execution_time, current_time)
                    
                    # Check for deadline violations
                    if current_time > task.next_deadline:
                        self._handle_deadline_violation(task, current_time)
                    
                    # Schedule next execution
                    self._schedule_next_execution(task, current_time)
                
                # Sleep until next execution or deadline
                sleep_time = self._calculate_sleep_time(task, current_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Error in task '{task.name}'", error=str(e))
                await asyncio.sleep(0.001)  # Brief pause on error
    
    def _should_execute_task(self, task: RealTimeTask, current_time: float) -> bool:
        """Determine if a task should execute now."""
        return should_execute_task(task, current_time)
    
    def _update_task_stats(self, task: RealTimeTask, execution_time: float, current_time: float):
        """Update task execution statistics."""
        task.last_execution = current_time
        stats = update_task_stats(task, execution_time, current_time)
        
        # Get previous stats for this task
        previous_stats = self.previous_stats.get(task.name, TimingStats(task_name=task.name))
        
        # Calculate the increment in missed deadlines
        missed_deadlines_increment = stats.missed_deadlines - previous_stats.missed_deadlines
        
        # Only add the increment to global stats (fix for the accounting bug)
        if missed_deadlines_increment > 0:
            self.global_stats['missed_deadlines'] += missed_deadlines_increment
        
        # Store current stats as previous for next update
        self.previous_stats[task.name] = stats
        self.timing_stats[task.name] = stats
    
    def _handle_deadline_violation(self, task: RealTimeTask, current_time: float):
        """Handle deadline violations."""
        handle_deadline_violation(task, current_time)
        # Note: Global stats increment is now handled in _update_task_stats to avoid double-counting
        self.timing_stats[task.name].missed_deadlines = task.missed_deadlines
        
        # Apply timing compensation
        self._apply_timing_compensation(task, current_time)
    
    def _apply_timing_compensation(self, task: RealTimeTask, current_time: float):
        """Apply timing compensation for jitter and drift."""
        compensation = apply_timing_compensation(task, current_time, 
                                               self.clock_drift_compensation, 
                                               self.jitter_compensation)
        if compensation != 0.0:
            task.next_deadline = max(task.next_deadline - compensation, current_time + 0.001)
    
    def _schedule_next_execution(self, task: RealTimeTask, current_time: float):
        """Schedule the next execution of a task (phase-aligned, drift-free)."""
        schedule_next_execution(task, current_time)
    
    def _calculate_sleep_time(self, task: RealTimeTask, current_time: float) -> float:
        """Calculate sleep time until next execution."""
        sleep_time = calculate_sleep_time(task, current_time)
        return max(0.001, sleep_time)  # Ensure minimum sleep time
    
    async def _monitor_performance(self):
        """Monitor overall scheduler performance."""
        while self.running:
            try:
                # Update global statistics
                self.global_stats['total_cycles'] += 1
                
                # Calculate average cycle time
                if self.timing_stats:
                    avg_cycle_times = [stats.mean_execution_time_ms for stats in self.timing_stats.values()]
                    self.global_stats['average_cycle_time_ms'] = np.mean(avg_cycle_times)
                    self.global_stats['max_cycle_time_ms'] = max(avg_cycle_times)
                
                # Log performance every 10 seconds
                if self.global_stats['total_cycles'] % 1000 == 0:
                    self._log_performance()
                
                await asyncio.sleep(0.01)  # 100Hz monitoring
                
            except Exception as e:
                self.logger.error("Error in performance monitoring", error=str(e))
                await asyncio.sleep(0.1)
    
    def _log_performance(self):
        """Log current performance statistics."""
        self.logger.info(
            "Scheduler performance statistics",
            total_cycles=self.global_stats['total_cycles'],
            missed_deadlines=self.global_stats['missed_deadlines'],
            average_cycle_time_ms=self.global_stats['average_cycle_time_ms'],
            max_cycle_time_ms=self.global_stats['max_cycle_time_ms']
        )
        
        for task_name, stats in self.timing_stats.items():
            if stats.total_executions > 0:
                self.logger.info(
                    f"Task performance: {task_name}",
                    task_name=task_name,
                    success_rate_percent=stats.success_rate*100,
                    mean_execution_time_ms=stats.mean_execution_time_ms,
                    missed_deadlines=stats.missed_deadlines
                )
    
    def get_task_stats(self, task_name: str) -> Optional[TimingStats]:
        """Get statistics for a specific task."""
        return self.timing_stats.get(task_name)
    
    def get_all_stats(self) -> Dict[str, TimingStats]:
        """Get statistics for all tasks."""
        return self.timing_stats.copy()
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global scheduler statistics."""
        return self.global_stats.copy()


class RealTimeLoop:
    """
    High-level interface for real-time loops with automatic timing management.
    
    This class provides a simple interface for creating real-time loops
    that automatically handle timing compensation and deadline monitoring.
    """
    
    def __init__(self, frequency_hz: float, name: str = "realtime_loop"):
        """Initialize a real-time loop."""
        self.frequency_hz = frequency_hz
        self.period_ms = 1000.0 / frequency_hz
        self.name = name
        self.running = False
        self.loop_count = 0
        self.missed_deadlines = 0
        self.execution_times = deque(maxlen=1000)
        
        # Timing compensation
        self.clock_drift = 0.0
        self.jitter_compensation = 0.0
        
        # Performance monitoring
        self.start_time = time.perf_counter()
        self.last_iteration_time = self.start_time
        
        # Initialize logger
        self.logger = get_logger(f"{__name__}.{name}")
    
    @asynccontextmanager
    async def real_time_loop(self):
        """Context manager for real-time loops."""
        self.running = True
        self.start_time = time.perf_counter()
        self.last_iteration_time = self.start_time
        
        try:
            yield self
        finally:
            self.running = False
    
    async def iterate(self, func: Callable) -> None:
        """Execute one iteration of the real-time loop."""
        if not self.running:
            raise RealTimeError("Real-time loop is not running")
        
        iteration_start = time.perf_counter()
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                # Run synchronous function in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, func)
            
            # Calculate execution time
            execution_time = (time.perf_counter() - iteration_start) * 1000.0
            self.execution_times.append(execution_time)
            
            # Check for deadline violation
            if execution_time > self.period_ms:
                self.missed_deadlines += 1
                self.logger.warning(
                    f"Deadline violation in {self.name}",
                    execution_time_ms=execution_time,
                    period_ms=self.period_ms
                )
            
            # Calculate sleep time with compensation
            elapsed = time.perf_counter() - iteration_start
            sleep_time = max(0.0, (self.period_ms / 1000.0) - elapsed)
            
            # Apply timing compensation
            sleep_time = self._apply_compensation(sleep_time)
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            
            self.loop_count += 1
            self.last_iteration_time = time.perf_counter()
            
        except Exception as e:
            self.logger.error(f"Error in real-time loop '{self.name}'", error=str(e))
            await asyncio.sleep(0.001)  # Brief pause on error
    
    def _apply_compensation(self, sleep_time: float) -> float:
        """Apply timing compensation for jitter and drift."""
        # Calculate drift compensation
        expected_time = self.start_time + (self.loop_count * self.period_ms / 1000.0)
        actual_time = time.perf_counter()
        drift = actual_time - expected_time
        
        # Apply compensation (10% of drift) with proper clamping
        compensation = drift * 0.1
        sleep_time = max(0.001, sleep_time - compensation)  # Ensure minimum 1ms sleep
        
        # Cap compensation to prevent runaway timing
        return min(sleep_time, self.period_ms / 1000.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get loop statistics."""
        if not self.execution_times:
            return {}
        
        return {
            'name': self.name,
            'frequency_hz': self.frequency_hz,
            'period_ms': self.period_ms,
            'loop_count': self.loop_count,
            'missed_deadlines': self.missed_deadlines,
            'success_rate': (self.loop_count - self.missed_deadlines) / max(self.loop_count, 1),
            'mean_execution_time_ms': np.mean(self.execution_times),
            'max_execution_time_ms': max(self.execution_times),
            'min_execution_time_ms': min(self.execution_times),
            'actual_frequency_hz': self.loop_count / ((time.perf_counter() - self.start_time) if self.start_time else 1.0),
        }


# Convenience functions for common real-time patterns
async def run_periodic_task(
    func: Callable,
    frequency_hz: float,
    name: str = "periodic_task",
    priority: TaskPriority = TaskPriority.MEDIUM
) -> None:
    """Run a function at a fixed frequency."""
    loop = RealTimeLoop(frequency_hz, name)
    
    async with loop.real_time_loop():
        while loop.running:
            await loop.iterate(func)


async def run_with_deadline(
    func: Callable,
    deadline_ms: float,
    name: str = "deadline_task"
) -> bool:
    """Run a function with a deadline constraint."""
    start_time = time.perf_counter()
    
    try:
        if asyncio.iscoroutinefunction(func):
            await asyncio.wait_for(func(), timeout=deadline_ms / 1000.0)
        else:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, func),
                timeout=deadline_ms / 1000.0
            )
        return True
    except asyncio.TimeoutError:
        logger = get_logger(__name__)
        logger.warning(f"Deadline exceeded for task '{name}'", deadline_ms=deadline_ms)
        return False


def create_control_loop_task(
    control_func: Callable,
    frequency_hz: float = 400.0,
    name: str = "control_loop"
) -> RealTimeTask:
    """Create a high-priority control loop task."""
    return RealTimeTask(
        name=name,
        func=control_func,
        priority=TaskPriority.HIGH,
        task_type=TaskType.PERIODIC,
        period_ms=1000.0 / frequency_hz,
        deadline_ms=1000.0 / frequency_hz,  # Same as period for control loops
        execution_time_ms=1.0,  # Conservative estimate
        jitter_ms=0.1  # 0.1ms jitter tolerance
    )


def create_planning_task(
    planning_func: Callable,
    frequency_hz: float = 50.0,
    name: str = "planning_loop"
) -> RealTimeTask:
    """Create a medium-priority planning task."""
    return RealTimeTask(
        name=name,
        func=planning_func,
        priority=TaskPriority.MEDIUM,
        task_type=TaskType.PERIODIC,
        period_ms=1000.0 / frequency_hz,
        deadline_ms=1000.0 / frequency_hz * 2,  # 2x period for planning
        execution_time_ms=10.0,  # Conservative estimate
        jitter_ms=1.0  # 1ms jitter tolerance
    )


def create_safety_task(
    safety_func: Callable,
    name: str = "safety_monitor"
) -> RealTimeTask:
    """Create a critical-priority safety task."""
    return RealTimeTask(
        name=name,
        func=safety_func,
        priority=TaskPriority.CRITICAL,
        task_type=TaskType.APERIODIC,
        deadline_ms=10.0,  # 10ms deadline for safety
        execution_time_ms=1.0,
        jitter_ms=0.1
    ) 
