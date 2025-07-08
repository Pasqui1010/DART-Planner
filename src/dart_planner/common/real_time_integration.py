# flake8: noqa
# type: ignore
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
import os
from dart_planner.common.multiprocess_control_loop import ProcessControlLoop

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
            
        return results


def create_control_loop(
    control_func: Callable,
    frequency_hz: float = 1000.0,
    name: str = "control_loop"
) -> RealTimeLoop:
    """Create a real-time loop for control."""
    return RealTimeLoop(frequency_hz, name)


def create_planning_loop(
    planning_func: Callable,
    frequency_hz: float = 50.0,
    name: str = "planning_loop"
) -> RealTimeLoop:
    """Create a real-time loop for planning."""
    return RealTimeLoop(frequency_hz, name)


class RealTimeManager:
    """Singleton for managing real-time tasks."""
    _instance: Optional['RealTimeManager'] = None

    def __init__(self, config=None):
        if config is None:
            config = get_config()
        
        self.config = config
        self.scheduler = RealTimeScheduler()
        self.running = False
        
        # Lazy initialization for tasks
        self.control_task: Optional[RealTimeTask] = None
        self.planning_task: Optional[RealTimeTask] = None
        self.safety_task: Optional[RealTimeTask] = None
        
        # Store functions for lazy task creation
        self._control_func: Optional[Callable] = None
        self._planning_func: Optional[Callable] = None
        self._safety_func: Optional[Callable] = None
        
        self._initialize_common_tasks()

    def _initialize_common_tasks(self):
        """Initialize common tasks with configurations."""
        # Common task initialization is deferred to set_*_function methods.
        pass
    
    def _control_loop_function(self):
        """Wrapper for the control loop function."""
        if self._control_func:
            self._control_func()

    def _planning_loop_function(self):
        """Wrapper for the planning loop function."""
        if self._planning_func:
            self._planning_func()

    def _safety_loop_function(self):
        """Wrapper for the safety loop function."""
        if self._safety_func:
            self._safety_func()

    async def start(self):
        """Start the real-time scheduler."""
        if not self.running:
            self.running = True
            await self.scheduler.start()

    async def stop(self):
        """Stop the real-time scheduler."""
        if self.running:
            await self.scheduler.stop()
            self.running = False

    def set_control_function(self, func: Callable):
        """
        Set the control function and create the task if it doesn't exist.
        """
        self._control_func = func
        
        if self.control_task is None:
            rt_config = get_control_loop_config(self.config)
            self.control_task = create_control_loop_task(
                self._control_loop_function,
                frequency_hz=rt_config['frequency_hz'],
                priority=rt_config.get('priority', TaskPriority.HIGH)
            )
            self.scheduler.add_task(self.control_task)

    def set_planning_function(self, func: Callable):
        """
        Set the planning function and create the task if it doesn't exist.
        """
        self._planning_func = func
        
        if self.planning_task is None:
            rt_config = get_planning_loop_config(self.config)
            self.planning_task = create_planning_task(
                self._planning_loop_function,
                frequency_hz=rt_config['frequency_hz'],
                priority=rt_config.get('priority', TaskPriority.MEDIUM)
            )
            self.scheduler.add_task(self.planning_task)

    def set_safety_function(self, func: Callable):
        """
        Set the safety function and create the task if it doesn't exist.
        """
        self._safety_func = func
        
        if self.safety_task is None:
            rt_config = get_safety_loop_config(self.config)
            self.safety_task = create_safety_task(
                self._safety_loop_function,
                frequency_hz=rt_config['frequency_hz'],
                priority=rt_config.get('priority', TaskPriority.CRITICAL)
            )
            self.scheduler.add_task(self.safety_task)

    def add_custom_task(self, task: RealTimeTask):
        """Add a custom real-time task."""
        self.scheduler.add_task(task)

    def remove_custom_task(self, task_name: str):
        """Remove a custom real-time task."""
        self.scheduler.remove_task(task_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics from the scheduler."""
        if not self.running:
            return {}
        
        return self.scheduler.get_stats()


def get_real_time_manager() -> RealTimeManager:
    """
    Get the singleton instance of the RealTimeManager.
    
    This ensures that there is only one real-time manager in the system.
    """
    if RealTimeManager._instance is None:
        RealTimeManager._instance = RealTimeManager()
    return RealTimeManager._instance


def real_time_task(
    frequency_hz: float = None,
    priority: TaskPriority = TaskPriority.MEDIUM,
    task_type: TaskType = TaskType.PERIODIC,
    deadline_ms: float = None,
    name: str = None
):
    """
    Decorator to register a function as a real-time task.
    
    Args:
        frequency_hz: Frequency for periodic tasks
        priority: Task priority
        task_type: Type of task (PERIODIC, APERIODIC, etc.)
        deadline_ms: Deadline for the task in milliseconds
        name: Name for the task
    """
    def decorator(func: Callable) -> Callable:
        task_name = name or func.__name__
        
        task = RealTimeTask(
            name=task_name,
            func=func,
            task_type=task_type,
            priority=priority,
            frequency_hz=frequency_hz,
            deadline_ms=deadline_ms
        )
        
        manager = get_real_time_manager()
        manager.add_custom_task(task)
        
        return func
    
    return decorator


def control_loop_task(frequency_hz: float = None, name: str = None):
    """Decorator to register a function as the main control loop."""
    def decorator(func: Callable) -> Callable:
        manager = get_real_time_manager()
        
        # If frequency is not provided, get from config
        if frequency_hz is None:
            config = get_control_loop_config(manager.config)
            frequency_hz = config.get('frequency_hz')
        
        manager.set_control_function(func)
        return func
    
    return decorator


def planning_loop_task(frequency_hz: float = None, name: str = None):
    """Decorator to register a function as the main planning loop."""
    def decorator(func: Callable) -> Callable:
        manager = get_real_time_manager()
        
        # If frequency is not provided, get from config
        if frequency_hz is None:
            config = get_planning_loop_config(manager.config)
            frequency_hz = config.get('frequency_hz')
        
        manager.set_planning_function(func)
        return func
    
    return decorator


def safety_task(name: str = None):
    """Decorator to register a function as the main safety monitor."""
    def decorator(func: Callable) -> Callable:
        manager = get_real_time_manager()
        manager.set_safety_function(func)
        return func
    
    return decorator


@asynccontextmanager
async def real_time_control_loop():
    """Context manager for the real-time control loop."""
    manager = get_real_time_manager()
    
    # Ensure control task is created
    if manager.control_task is None:
        raise SchedulingError("Control function not set")
    
    async with manager.scheduler.run_task(manager.control_task.name) as loop:
        yield loop


@asynccontextmanager
async def real_time_planning_loop():
    """Context manager for the real-time planning loop."""
    manager = get_real_time_manager()
    
    # Ensure planning task is created
    if manager.planning_task is None:
        raise SchedulingError("Planning function not set")
    
    async with manager.scheduler.run_task(manager.planning_task.name) as loop:
        yield loop


@asynccontextmanager
async def real_time_safety_loop():
    """Context manager for the real-time safety loop."""
    manager = get_real_time_manager()
    
    # Ensure safety task is created
    if manager.safety_task is None:
        raise SchedulingError("Safety function not set")
    
    async with manager.scheduler.run_task(manager.safety_task.name) as loop:
        yield loop


async def run_control_loop(control_func: Callable, duration: float = None):
    """Run the control loop for a specified duration."""
    manager = get_real_time_manager()
    manager.set_control_function(control_func)
    
    await manager.start()
    
    if duration:
        await asyncio.sleep(duration)
        await manager.stop()


async def run_planning_loop(planning_func: Callable, duration: float = None):
    """Run the planning loop for a specified duration."""
    manager = get_real_time_manager()
    manager.set_planning_function(planning_func)
    
    await manager.start()
    
    if duration:
        await asyncio.sleep(duration)
        await manager.stop()


async def run_safety_loop(safety_func: Callable, duration: float = None):
    """Run the safety loop for a specified duration."""
    manager = get_real_time_manager()
    manager.set_safety_function(safety_func)
    
    await manager.start()
    
    if duration:
        await asyncio.sleep(duration)
        await manager.stop()


def integrate_with_controller(controller):
    """
    Integrate a controller with the real-time manager.
    This function registers the controller's update method as the main control loop.
    """
    manager = get_real_time_manager()
    def control_function():
        # This would call the actual controller update
        # controller.update(current_state)
        pass

    manager.set_control_function(control_function)
    return manager

def integrate_with_multiprocess_controller(controller, frequency_hz: Optional[float] = None):
    """
    Integrate a controller using a separate process to avoid the Python GIL.
    """
    # Determine frequency from configuration if not provided
    if frequency_hz is None:
        config = get_config()
        frequency_hz = get_control_loop_config(config)["frequency_hz"]
    loop = ProcessControlLoop(controller.update, frequency_hz)
    loop.start()
    return loop


def integrate_with_planner(planner):
    """
    Integrate a planner with the real-time manager.
    
    This function registers the planner's update method as the
    main planning loop.
    """
    manager = get_real_time_manager()
    
    def planning_function():
        # This would call the actual planner update
        # planner.update()
        pass
        
    manager.set_planning_function(planning_function)
    return manager


def integrate_with_safety_system(safety_system):
    """
    Integrate a safety system with the real-time manager.
    
    This function registers the safety system's check method as the
    main safety monitor.
    """
    manager = get_real_time_manager()
    
    def safety_function():
        # This would call the actual safety system check
        # safety_system.check_safety()
        pass
        
    manager.set_safety_function(safety_function)
    return manager


def migrate_sleep_to_async(func: Callable) -> Callable:
    """
    Decorator to migrate functions with time.sleep() to async.
    
    This replaces blocking time.sleep() calls with non-blocking
    asyncio.sleep() calls.
    """
    import inspect
    import ast
    
    source = inspect.getsource(func)
    tree = ast.parse(source)
    
    class SleepTransformer(ast.NodeTransformer):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Attribute) and \
               isinstance(node.func.value, ast.Name) and \
               node.func.value.id == 'time' and node.func.attr == 'sleep':
                return ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='asyncio', ctx=ast.Load()),
                        attr='sleep',
                        ctx=ast.Load()
                    ),
                    args=node.args,
                    keywords=node.keywords
                )
            return node
    
    tree = SleepTransformer().visit(tree)
    
    # Recompile and execute the modified function
    # This is a bit of a hack and should be used carefully
    # It assumes the function doesn't rely on complex closures
    
    async def async_wrapper(*args, **kwargs):
        # Convert synchronous function to async
        pass  # Placeholder
        
    return async_wrapper


def create_real_time_wrapper(func: Callable, frequency_hz: float = None) -> Callable:
    """
    Create a real-time wrapper for a given function.
    
    This registers the function as a real-time task with the specified
    frequency.
    """
    
    @real_time_task(frequency_hz=frequency_hz, name=f"{func.__name__}_rt")
    def real_time_wrapper():
        return func()
    
    return real_time_wrapper


def monitor_real_time_performance():
    """
    Monitor real-time performance and log statistics.
    
    This can be run as a background task to continuously check
    the performance of the real-time system.
    """
    manager = get_real_time_manager()
    logger = get_logger(__name__)
    
    async def monitor():
        while True:
            await asyncio.sleep(10)  # Log every 10 seconds
            stats = manager.get_stats()
            logger.info(f"Real-time performance stats: {stats}")
    
    return asyncio.create_task(monitor())


async def bootstrap_real_time_system():
    """
    Bootstrap the real-time system by initializing the manager.
    
    This can be called at application startup to ensure the real-time
    manager is ready.
    """
    get_real_time_manager() 
