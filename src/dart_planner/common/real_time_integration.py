"""
Real-Time Integration for DART-Planner

This module provides easy-to-use interfaces for integrating real-time scheduling
into the existing DART-Planner codebase with minimal changes.
"""

import asyncio
import time
from typing import Callable, Optional, Dict, Any, Union
from contextlib import asynccontextmanager

from dart_planner.common.real_time_scheduler import (
    RealTimeScheduler, RealTimeLoop, RealTimeTask, TaskPriority, TaskType,
    create_control_loop_task, create_planning_task, create_safety_task,
    run_periodic_task, run_with_deadline
)
from dart_planner.common.di_container_v2 import get_container
from dart_planner.config.frozen_config import get_frozen_config as get_config
from dart_planner.config.real_time_config import (
    get_real_time_config, get_control_loop_config, get_planning_loop_config,
    get_safety_loop_config, get_communication_config
)
from dart_planner.common.errors import RealTimeError, SchedulingError
from dart_planner.common.logging_config import get_logger

"""
Real-time Integration Utilities for DART-Planner

This module provides utilities for creating real-time loops that maintain
latency guarantees by using proper timing management instead of blocking sleeps.
"""

import asyncio
import time
import logging
from typing import Callable, Optional, Any
from contextlib import asynccontextmanager

from .timing_alignment import get_timing_manager, TimingConfig, TimingMode


class RealTimeLoop:
    """
    Real-time loop utility that maintains timing guarantees without blocking sleeps.
    
    This class provides a simple interface for creating real-time loops
    that automatically handle timing compensation and deadline monitoring.
    """
    
    def __init__(self, frequency_hz: float, name: str = "realtime_loop"):
        """Initialize a real-time loop."""
        self.frequency_hz = frequency_hz
        self.period_s = 1.0 / frequency_hz
        self.name = name
        self.running = False
        self.loop_count = 0
        self.missed_deadlines = 0
        self.execution_times = []
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        # Timing compensation
        self.clock_drift = 0.0
        self.jitter_compensation = 0.0
        
        # Performance monitoring
        self.start_time = time.perf_counter()
        self.last_iteration_time = self.start_time
    
    @asynccontextmanager
    async def run_loop(self):
        """Context manager for real-time loops."""
        self.running = True
        self.start_time = time.perf_counter()
        self.last_iteration_time = self.start_time
        
        self.logger.info(f"Starting real-time loop '{self.name}' at {self.frequency_hz}Hz")
        
        try:
            yield self
        finally:
            self.running = False
            self.logger.info(f"Stopped real-time loop '{self.name}'")
    
    async def iterate(self, func: Callable, *args, **kwargs) -> Any:
        """Execute one iteration of the real-time loop."""
        if not self.running:
            raise RealTimeError("Real-time loop is not running")
        
        iteration_start = time.perf_counter()
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # Run synchronous function in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)
            
            # Calculate execution time
            execution_time = (time.perf_counter() - iteration_start) * 1000.0
            self.execution_times.append(execution_time)
            
            # Check for deadline violation
            if execution_time > self.period_s * 1000.0:
                self.missed_deadlines += 1
                self.logger.warning(
                    f"Deadline violation: {execution_time:.2f}ms > {self.period_s*1000:.2f}ms"
                )
            
            # Calculate sleep time with compensation
            elapsed = time.perf_counter() - iteration_start
            sleep_time = max(0.0, self.period_s - elapsed)
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            
            self.loop_count += 1
            return result
            
        except Exception as e:
            self.logger.error(f"Error in real-time loop iteration: {e}")
            # Brief pause on error to prevent tight error loops
            await asyncio.sleep(0.001)
            raise
    
    def get_stats(self) -> dict:
        """Get performance statistics."""
        if not self.execution_times:
            return {
                "name": self.name,
                "frequency_hz": self.frequency_hz,
                "loop_count": self.loop_count,
                "missed_deadlines": self.missed_deadlines,
                "avg_execution_time_ms": 0.0,
                "max_execution_time_ms": 0.0,
                "success_rate": 1.0
            }
        
        avg_execution = sum(self.execution_times) / len(self.execution_times)
        max_execution = max(self.execution_times)
        success_rate = (self.loop_count - self.missed_deadlines) / max(self.loop_count, 1)
        
        return {
            "name": self.name,
            "frequency_hz": self.frequency_hz,
            "loop_count": self.loop_count,
            "missed_deadlines": self.missed_deadlines,
            "avg_execution_time_ms": avg_execution,
            "max_execution_time_ms": max_execution,
            "success_rate": success_rate
        }


async def run_realtime_loop(
    func: Callable,
    frequency_hz: float,
    duration: Optional[float] = None,
    name: str = "realtime_loop"
) -> RealTimeLoop:
    """
    Run a function in a real-time loop with proper timing management.
    
    Args:
        func: Function to execute in the loop
        frequency_hz: Target frequency in Hz
        duration: Optional duration to run (None = run indefinitely)
        name: Name for the loop
    
    Returns:
        RealTimeLoop instance with statistics
    """
    loop = RealTimeLoop(frequency_hz, name)
    
    async with loop.run_loop():
        start_time = time.perf_counter()
        
        while True:
            # Check duration limit
            if duration and (time.perf_counter() - start_time) > duration:
                break
            
            await loop.iterate(func)
    
    return loop


class TimingAwareLoop:
    """
    Loop that integrates with the TimingManager for coordinated timing.
    """
    
    def __init__(self, timing_config: TimingConfig, name: str = "timing_aware_loop"):
        self.timing_config = timing_config
        self.timing_manager = get_timing_manager(timing_config)
        self.name = name
        self.running = False
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @asynccontextmanager
    async def run_loop(self):
        """Context manager for timing-aware loops."""
        self.running = True
        self.logger.info(f"Starting timing-aware loop '{self.name}'")
        
        try:
            yield self
        finally:
            self.running = False
            self.logger.info(f"Stopped timing-aware loop '{self.name}'")
    
    async def iterate_with_timing(
        self,
        control_func: Callable,
        planning_func: Optional[Callable] = None,
        current_time: Optional[float] = None
    ) -> dict:
        """
        Execute one iteration with proper timing coordination.
        
        Args:
            control_func: Function to execute for control
            planning_func: Optional function to execute for planning
            current_time: Current time (uses time.time() if None)
        
        Returns:
            Dictionary with execution results
        """
        if not self.running:
            raise RealTimeError("Timing-aware loop is not running")
        
        if current_time is None:
            current_time = time.time()
        
        results = {}
        
        # Execute planning if needed
        if planning_func and self.timing_manager.should_plan(current_time):
            plan_start = time.perf_counter()
            if asyncio.iscoroutinefunction(planning_func):
                plan_result = await planning_func()
            else:
                plan_result = planning_func()
            plan_duration = time.perf_counter() - plan_start
            
            self.timing_manager.update_planning_timing(current_time, plan_duration)
            results["planning"] = plan_result
            results["planning_duration"] = plan_duration
        
        # Execute control if needed
        if self.timing_manager.should_control(current_time):
            control_start = time.perf_counter()
            if asyncio.iscoroutinefunction(control_func):
                control_result = await control_func()
            else:
                control_result = control_func()
            control_duration = time.perf_counter() - control_start
            
            self.timing_manager.update_control_timing(current_time)
            results["control"] = control_result
            results["control_duration"] = control_duration
        
        # Calculate sleep time
        sleep_time = self.timing_manager.control_dt
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        
        return results


def create_control_loop(
    control_func: Callable,
    frequency_hz: float = 1000.0,
    name: str = "control_loop"
) -> RealTimeLoop:
    """Create a control loop with proper real-time timing."""
    return RealTimeLoop(frequency_hz, name)


def create_planning_loop(
    planning_func: Callable,
    frequency_hz: float = 50.0,
    name: str = "planning_loop"
) -> RealTimeLoop:
    """Create a planning loop with proper real-time timing."""
    return RealTimeLoop(frequency_hz, name)


class RealTimeManager:
    """
    High-level real-time manager for DART-Planner.
    
    This class provides a simple interface for managing real-time tasks
    and integrating them with the existing codebase.
    """
    
    def __init__(self, config=None):
        """Initialize the real-time manager."""
        if config is None:
            config = get_config()
        
        self.config = config
        self.rt_config = get_real_time_config(config)
        self.scheduler = RealTimeScheduler(
            enable_rt_os=self.rt_config.scheduling.enable_rt_os
        )
        self.running = False
        self.tasks: Dict[str, RealTimeTask] = {}
        
        # Initialize task references as None - lazy creation
        self.control_task = None
        self.planning_task = None
        self.safety_task = None
        
        # Setup logging
        self.logger = get_logger(__name__)
    
    def _initialize_common_tasks(self):
        """Initialize common real-time tasks - now called lazily when functions are set."""
        # This method is kept for backward compatibility but no longer called in __init__
        pass
    
    def _control_loop_function(self):
        """Default control loop function."""
        # This will be overridden by the actual control system
        pass
    
    def _planning_loop_function(self):
        """Default planning loop function."""
        # This will be overridden by the actual planning system
        pass
    
    def _safety_loop_function(self):
        """Default safety loop function."""
        # This will be overridden by the actual safety system
        pass
    
    async def start(self):
        """Start the real-time manager."""
        if self.running:
            return
        
        self.logger.info("🚀 Starting Real-Time Manager")
        await self.scheduler.start()
        self.running = True
    
    async def stop(self):
        """Stop the real-time manager."""
        if not self.running:
            return
        
        self.logger.info("🛑 Stopping Real-Time Manager")
        await self.scheduler.stop()
        self.running = False
    
    def set_control_function(self, func: Callable):
        """Set the control loop function."""
        if self.control_task is None:
            # Create task lazily when function is first set
            control_config = get_control_loop_config(self.config)
            self.control_task = create_control_loop_task(
                control_func=func,
                frequency_hz=control_config['frequency_hz'],
                name="control_loop"
            )
            self.scheduler.add_task(self.control_task)
        else:
            self.control_task.func = func
    
    def set_planning_function(self, func: Callable):
        """Set the planning loop function."""
        if self.planning_task is None:
            # Create task lazily when function is first set
            planning_config = get_planning_loop_config(self.config)
            self.planning_task = create_planning_task(
                planning_func=func,
                frequency_hz=planning_config['frequency_hz'],
                name="planning_loop"
            )
            self.scheduler.add_task(self.planning_task)
        else:
            self.planning_task.func = func
    
    def set_safety_function(self, func: Callable):
        """Set the safety loop function."""
        if self.safety_task is None:
            # Create task lazily when function is first set
            safety_config = get_safety_loop_config(self.config)
            self.safety_task = create_safety_task(
                safety_func=func,
                name="safety_monitor"
            )
            self.scheduler.add_task(self.safety_task)
        else:
            self.safety_task.func = func
    
    def add_custom_task(self, task: RealTimeTask):
        """Add a custom real-time task."""
        self.scheduler.add_task(task)
        self.tasks[task.name] = task
    
    def remove_custom_task(self, task_name: str):
        """Remove a custom real-time task."""
        self.scheduler.remove_task(task_name)
        if task_name in self.tasks:
            del self.tasks[task_name]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get real-time statistics."""
        return {
            'scheduler_stats': self.scheduler.get_global_stats(),
            'task_stats': self.scheduler.get_all_stats(),
            'running': self.running
        }


# Global real-time manager instance
_rt_manager: Optional[RealTimeManager] = None


def get_real_time_manager() -> RealTimeManager:
    """Get the global real-time manager instance."""
    global _rt_manager
    if _rt_manager is None:
        _rt_manager = RealTimeManager()
    return _rt_manager


# Decorators for easy real-time integration
def real_time_task(
    frequency_hz: float = None,
    priority: TaskPriority = TaskPriority.MEDIUM,
    task_type: TaskType = TaskType.PERIODIC,
    deadline_ms: float = None,
    name: str = None
):
    """
    Decorator to make a function a real-time task.
    
    Args:
        frequency_hz: Task frequency (for periodic tasks)
        priority: Task priority
        task_type: Type of task
        deadline_ms: Task deadline
        name: Task name (defaults to function name)
    """
    def decorator(func: Callable) -> Callable:
        task_name = name or func.__name__
        
        # Determine deadline from frequency if not specified
        if deadline_ms is None and frequency_hz is not None:
            deadline_ms = 1000.0 / frequency_hz
        
        # Create real-time task
        task = RealTimeTask(
            name=task_name,
            func=func,
            priority=priority,
            task_type=task_type,
            period_ms=1000.0 / frequency_hz if frequency_hz else 0.0,
            deadline_ms=deadline_ms or 0.0
        )
        
        # Add to global manager
        manager = get_real_time_manager()
        manager.add_custom_task(task)
        
        return func
    
    return decorator


def control_loop_task(frequency_hz: float = None, name: str = None):
    """Decorator for control loop tasks."""
    if frequency_hz is None:
        frequency_hz = get_control_loop_config(get_config())['frequency_hz']
    
    return real_time_task(
        frequency_hz=frequency_hz,
        priority=TaskPriority.HIGH,
        task_type=TaskType.PERIODIC,
        deadline_ms=1000.0 / frequency_hz,
        name=name
    )


def planning_loop_task(frequency_hz: float = None, name: str = None):
    """Decorator for planning loop tasks."""
    if frequency_hz is None:
        frequency_hz = get_planning_loop_config(get_config())['frequency_hz']
    
    return real_time_task(
        frequency_hz=frequency_hz,
        priority=TaskPriority.MEDIUM,
        task_type=TaskType.PERIODIC,
        deadline_ms=1000.0 / frequency_hz * 2,  # 2x period for planning
        name=name
    )


def safety_task(name: str = None):
    """Decorator for safety tasks."""
    return real_time_task(
        priority=TaskPriority.CRITICAL,
        task_type=TaskType.APERIODIC,
        deadline_ms=10.0,  # 10ms deadline for safety
        name=name
    )


# Context managers for real-time loops
@asynccontextmanager
async def real_time_control_loop():
    """Context manager for real-time control loops."""
    config = get_control_loop_config(get_config())
    loop = RealTimeLoop(config['frequency_hz'], "control_loop")
    
    async with loop.run_loop():
        yield loop


@asynccontextmanager
async def real_time_planning_loop():
    """Context manager for real-time planning loops."""
    config = get_planning_loop_config(get_config())
    loop = RealTimeLoop(config['frequency_hz'], "planning_loop")
    
    async with loop.run_loop():
        yield loop


@asynccontextmanager
async def real_time_safety_loop():
    """Context manager for real-time safety loops."""
    config = get_safety_loop_config(get_config())
    loop = RealTimeLoop(config['frequency_hz'], "safety_loop")
    
    async with loop.run_loop():
        yield loop


# Utility functions for common real-time patterns
async def run_control_loop(control_func: Callable, duration: float = None):
    """Run a control loop with the specified function."""
    config = get_control_loop_config(get_config())
    
    async with real_time_control_loop() as loop:
        start_time = time.time()
        while True:
            if duration and (time.time() - start_time) > duration:
                break
            
            await loop.iterate(control_func)


async def run_planning_loop(planning_func: Callable, duration: float = None):
    """Run a planning loop with the specified function."""
    config = get_planning_loop_config(get_config())
    
    async with real_time_planning_loop() as loop:
        start_time = time.time()
        while True:
            if duration and (time.time() - start_time) > duration:
                break
            
            await loop.iterate(planning_func)


async def run_safety_loop(safety_func: Callable, duration: float = None):
    """Run a safety loop with the specified function."""
    config = get_safety_loop_config(get_config())
    
    async with real_time_safety_loop() as loop:
        start_time = time.time()
        while True:
            if duration and (time.time() - start_time) > duration:
                break
            
            await loop.iterate(safety_func)


# Integration with existing components
def integrate_with_controller(controller):
    """Integrate real-time scheduling with a controller."""
    manager = get_real_time_manager()
    
    def control_function():
        # This would call the actual controller update
        if hasattr(controller, 'update'):
            controller.update()
        elif hasattr(controller, 'compute_control'):
            controller.compute_control()
    
    manager.set_control_function(control_function)
    return manager


def integrate_with_planner(planner):
    """Integrate real-time scheduling with a planner."""
    manager = get_real_time_manager()
    
    def planning_function():
        # This would call the actual planner update
        if hasattr(planner, 'update'):
            planner.update()
        elif hasattr(planner, 'plan_trajectory'):
            # This would need current state and goal
            pass
    
    manager.set_planning_function(planning_function)
    return manager


def integrate_with_safety_system(safety_system):
    """Integrate real-time scheduling with a safety system."""
    manager = get_real_time_manager()
    
    def safety_function():
        # This would call the actual safety system check
        if hasattr(safety_system, 'check_safety'):
            safety_system.check_safety()
        elif hasattr(safety_system, 'update'):
            safety_system.update()
    
    manager.set_safety_function(safety_function)
    return manager


# Migration helpers for existing code
def migrate_sleep_to_async(func: Callable) -> Callable:
    """
    Migrate a function that uses time.sleep to use asyncio.sleep.
    
    This is a helper for migrating existing synchronous functions.
    """
    import inspect
    
    if inspect.iscoroutinefunction(func):
        return func  # Already async
    
    async def async_wrapper(*args, **kwargs):
        # Convert synchronous function to async
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    
    return async_wrapper


def create_real_time_wrapper(func: Callable, frequency_hz: float = None) -> Callable:
    """
    Create a real-time wrapper for an existing function.
    
    This allows existing functions to be easily integrated into the real-time system.
    """
    if frequency_hz is None:
        frequency_hz = get_control_loop_config(get_config())['frequency_hz']
    
    @real_time_task(frequency_hz=frequency_hz, name=f"{func.__name__}_rt")
    def real_time_wrapper():
        return func()
    
    return real_time_wrapper


# Performance monitoring helpers
def monitor_real_time_performance():
    """Monitor real-time performance and print statistics."""
    manager = get_real_time_manager()
    stats = manager.get_stats()
    
    print("📊 Real-Time Performance Statistics:")
    print(f"   Scheduler running: {stats['running']}")
    print(f"   Total cycles: {stats['scheduler_stats']['total_cycles']}")
    print(f"   Missed deadlines: {stats['scheduler_stats']['missed_deadlines']}")
    print(f"   Average cycle time: {stats['scheduler_stats']['average_cycle_time_ms']:.2f}ms")
    
    for task_name, task_stats in stats['task_stats'].items():
        if task_stats.total_executions > 0:
            print(f"   {task_name}:")
            print(f"     Success rate: {task_stats.success_rate*100:.1f}%")
            print(f"     Mean execution: {task_stats.mean_execution_time_ms:.2f}ms")
            print(f"     Max execution: {task_stats.max_execution_time_ms:.2f}ms")
            print(f"     Missed deadlines: {task_stats.missed_deadlines}")


# Bootstrap function for easy integration
async def bootstrap_real_time_system():
    """Bootstrap the real-time system with default configuration."""
    manager = get_real_time_manager()
    await manager.start()
    return manager 
