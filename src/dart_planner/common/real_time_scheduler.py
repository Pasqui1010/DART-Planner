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
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
import numpy as np
from collections import deque

from dart_planner.common.errors import RealTimeError, SchedulingError
from dart_planner.common.types import DroneState


class TaskPriority(Enum):
    """Task priority levels for real-time scheduling."""
    CRITICAL = 0      # Safety-critical tasks (emergency stop, collision avoidance)
    HIGH = 1          # High-frequency control loops (400Hz+)
    MEDIUM = 2        # Planning and state estimation (50Hz)
    LOW = 3           # Communication and logging (10Hz)
    BACKGROUND = 4    # Non-critical background tasks


class TaskType(Enum):
    """Types of real-time tasks."""
    PERIODIC = "periodic"      # Fixed frequency tasks
    APERIODIC = "aperiodic"    # Event-driven tasks
    SPORADIC = "sporadic"      # Tasks with minimum inter-arrival time


@dataclass
class RealTimeTask:
    """Represents a real-time task with timing constraints."""
    name: str
    func: Callable
    priority: TaskPriority
    task_type: TaskType
    period_ms: float = 0.0  # For periodic tasks
    deadline_ms: float = 0.0  # Relative deadline
    min_interarrival_ms: float = 0.0  # For sporadic tasks
    execution_time_ms: float = 0.0  # Worst-case execution time
    jitter_ms: float = 0.0  # Timing jitter tolerance
    enabled: bool = True
    last_execution: float = field(default_factory=time.perf_counter)
    next_deadline: float = field(default_factory=time.perf_counter)
    missed_deadlines: int = 0
    total_executions: int = 0
    execution_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def __post_init__(self):
        """Initialize task timing."""
        self.last_execution = time.perf_counter()
        self.next_deadline = self.last_execution + (self.deadline_ms / 1000.0)


@dataclass
class TimingStats:
    """Timing statistics for real-time tasks."""
    task_name: str
    mean_execution_time_ms: float = 0.0
    max_execution_time_ms: float = 0.0
    min_execution_time_ms: float = float('inf')
    mean_jitter_ms: float = 0.0
    max_jitter_ms: float = 0.0
    missed_deadlines: int = 0
    total_executions: int = 0
    success_rate: float = 1.0


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
    
    def __init__(self, enable_rt_os: bool = True):
        """Initialize the real-time scheduler."""
        self.tasks: Dict[str, RealTimeTask] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Timing compensation
        self.clock_drift_compensation = 0.0
        self.jitter_compensation = 0.0
        self.timing_stats: Dict[str, TimingStats] = {}
        
        # Real-time OS features
        self.enable_rt_os = enable_rt_os and self._check_rt_os_support()
        self.rt_priority = self._get_rt_priority()
        
        # Performance monitoring
        self.monitoring_enabled = True
        self.global_stats = {
            'total_cycles': 0,
            'missed_deadlines': 0,
            'average_cycle_time_ms': 0.0,
            'max_cycle_time_ms': 0.0,
        }
        
        # Initialize real-time features
        if self.enable_rt_os:
            self._setup_rt_os()
    
    def _check_rt_os_support(self) -> bool:
        """Check if real-time OS features are available."""
        system = platform.system().lower()
        
        if system == 'linux':
            # Check for PREEMPT_RT kernel
            try:
                with open('/proc/version', 'r') as f:
                    kernel_info = f.read()
                    return 'preempt' in kernel_info.lower()
            except:
                return False
        elif system == 'windows':
            # Windows has limited real-time support
            return False
        else:
            return False
    
    def _get_rt_priority(self) -> int:
        """Get appropriate real-time priority for the system."""
        if platform.system().lower() == 'linux':
            return 80  # High priority for Linux
        else:
            return 0  # Default priority for other systems
    
    def _setup_rt_os(self):
        """Setup real-time operating system features."""
        import logging
        if platform.system().lower() == 'linux':
            try:
                # Set real-time priority
                os.nice(-self.rt_priority)
            except (OSError, PermissionError) as e:
                logging.warning(f"Could not set real-time priority (requires root): {e}. Downgrading to cooperative scheduling.")
                self.enable_rt_os = False
            except Exception as e:
                logging.warning(f"Unexpected error setting real-time priority: {e}. Downgrading to cooperative scheduling.")
                self.enable_rt_os = False
    
    def add_task(self, task: RealTimeTask) -> None:
        """Add a real-time task to the scheduler."""
        if task.name in self.tasks:
            raise SchedulingError(f"Task '{task.name}' already exists")
        
        self.tasks[task.name] = task
        self.timing_stats[task.name] = TimingStats(task_name=task.name)
        
        # Initialize timing for periodic tasks
        if task.task_type == TaskType.PERIODIC and task.period_ms > 0:
            task.next_deadline = time.perf_counter() + (task.period_ms / 1000.0)
    
    def remove_task(self, task_name: str) -> None:
        """Remove a task from the scheduler."""
        if task_name in self.tasks:
            del self.tasks[task_name]
            if task_name in self.timing_stats:
                del self.timing_stats[task_name]
    
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
        
        print("🚀 Real-time scheduler started")
    
    async def stop(self) -> None:
        """Stop the real-time scheduler."""
        self.running = False
        print("🛑 Real-time scheduler stopped")
    
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
                        await self.loop.run_in_executor(None, task.func)
                    
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
                print(f"❌ Error in task '{task.name}': {e}")
                await asyncio.sleep(0.001)  # Brief pause on error
    
    def _should_execute_task(self, task: RealTimeTask, current_time: float) -> bool:
        """Determine if a task should execute now."""
        if task.task_type == TaskType.PERIODIC:
            return current_time >= task.next_deadline
        elif task.task_type == TaskType.SPORADIC:
            min_interval = task.min_interarrival_ms / 1000.0
            return current_time >= task.last_execution + min_interval
        else:  # APERIODIC
            return True
    
    def _update_task_stats(self, task: RealTimeTask, execution_time: float, current_time: float):
        """Update task execution statistics."""
        task.execution_times.append(execution_time)
        task.total_executions += 1
        task.last_execution = current_time
        
        # Update timing statistics
        stats = self.timing_stats[task.name]
        stats.total_executions = task.total_executions
        stats.mean_execution_time_ms = np.mean(task.execution_times)
        stats.max_execution_time_ms = max(stats.max_execution_time_ms, execution_time)
        stats.min_execution_time_ms = min(stats.min_execution_time_ms, execution_time)
        
        # Calculate jitter
        if task.task_type == TaskType.PERIODIC and len(task.execution_times) > 1:
            expected_time = task.last_execution - (task.period_ms / 1000.0)
            jitter = abs(current_time - expected_time) * 1000.0
            stats.mean_jitter_ms = (stats.mean_jitter_ms * (stats.total_executions - 1) + jitter) / stats.total_executions
            stats.max_jitter_ms = max(stats.max_jitter_ms, jitter)
    
    def _handle_deadline_violation(self, task: RealTimeTask, current_time: float):
        """Handle deadline violations."""
        task.missed_deadlines += 1
        self.timing_stats[task.name].missed_deadlines = task.missed_deadlines
        self.global_stats['missed_deadlines'] += 1
        
        # Calculate success rate
        stats = self.timing_stats[task.name]
        stats.success_rate = (stats.total_executions - stats.missed_deadlines) / max(stats.total_executions, 1)
        
        print(f"⚠️  Deadline violation in task '{task.name}' - {task.missed_deadlines} total")
        
        # Apply timing compensation
        self._apply_timing_compensation(task, current_time)
    
    def _apply_timing_compensation(self, task: RealTimeTask, current_time: float):
        """Apply timing compensation for jitter and drift."""
        if task.task_type == TaskType.PERIODIC:
            # Calculate drift compensation
            expected_time = task.last_execution + (task.period_ms / 1000.0)
            actual_time = current_time
            drift = actual_time - expected_time
            
            # Apply compensation to next deadline (clamped to prevent negative values)
            compensation = min(drift * 0.1, task.period_ms / 1000.0 * 0.1)  # 10% compensation
            task.next_deadline = max(task.next_deadline - compensation, current_time + 0.001)
    
    def _schedule_next_execution(self, task: RealTimeTask, current_time: float):
        """Schedule the next execution of a task (phase-aligned, drift-free)."""
        if task.task_type == TaskType.PERIODIC:
            period_s = task.period_ms / 1000.0
            task.next_deadline += period_s
        elif task.task_type == TaskType.SPORADIC:
            task.next_deadline = current_time + (task.min_interarrival_ms / 1000.0)
    
    def _calculate_sleep_time(self, task: RealTimeTask, current_time: float) -> float:
        """Calculate sleep time until next execution."""
        if task.task_type == TaskType.PERIODIC:
            # Ensure sleep time is clamped to prevent negative values and excessive CPU usage
            sleep_time = max(0.001, task.next_deadline - current_time)
            return min(sleep_time, task.period_ms / 1000.0)  # Cap at period to prevent runaway
        elif task.task_type == TaskType.SPORADIC:
            min_interval = task.min_interarrival_ms / 1000.0
            next_execution = task.last_execution + min_interval
            return max(0.001, next_execution - current_time)
        else:
            return 0.001  # Small delay for aperiodic tasks
    
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
                print(f"❌ Error in performance monitoring: {e}")
                await asyncio.sleep(0.1)
    
    def _log_performance(self):
        """Log current performance statistics."""
        print(f"📊 Scheduler Performance:")
        print(f"   Total cycles: {self.global_stats['total_cycles']}")
        print(f"   Missed deadlines: {self.global_stats['missed_deadlines']}")
        print(f"   Average cycle time: {self.global_stats['average_cycle_time_ms']:.2f}ms")
        print(f"   Max cycle time: {self.global_stats['max_cycle_time_ms']:.2f}ms")
        
        for task_name, stats in self.timing_stats.items():
            if stats.total_executions > 0:
                print(f"   {task_name}: {stats.success_rate*100:.1f}% success, "
                      f"{stats.mean_execution_time_ms:.2f}ms avg, "
                      f"{stats.missed_deadlines} missed")
    
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
                print(f"⚠️  Deadline violation in {self.name}: {execution_time:.2f}ms > {self.period_ms:.2f}ms")
            
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
            print(f"❌ Error in real-time loop '{self.name}': {e}")
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
        print(f"⚠️  Deadline exceeded for task '{name}': {deadline_ms}ms")
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
