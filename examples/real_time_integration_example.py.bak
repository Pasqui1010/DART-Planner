#!/usr/bin/env python3
"""
Real-Time Integration Example for DART-Planner

This example demonstrates how to integrate the new real-time scheduling system
with the existing DART-Planner codebase.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
import time
import numpy as np
from typing import Dict, Any

from dart_planner.common.real_time_integration import (
    RealTimeManager, get_real_time_manager,
    real_time_task, control_loop_task, planning_loop_task, safety_task,
    real_time_control_loop, real_time_planning_loop, real_time_safety_loop,
    run_control_loop, run_planning_loop, run_safety_loop,
    integrate_with_controller, integrate_with_planner, integrate_with_safety_system,
    monitor_real_time_performance, bootstrap_real_time_system
)
from dart_planner.common.real_time_scheduler import TaskPriority, TaskType
from dart_planner.common.di_container import get_container
from dart_planner.config.settings import get_config
from dart_planner.common.types import DroneState


class ExampleController:
    """Example controller for demonstration."""
    
    def __init__(self):
        self.last_update = time.time()
        self.update_count = 0
    
    def update(self):
        """Update the controller."""
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        self.update_count += 1
        
        # Simulate control computation
        time.sleep(0.001)  # 1ms control computation
        
        if self.update_count % 100 == 0:
            print(f"Controller update {self.update_count}, dt: {dt*1000:.2f}ms")


class ExamplePlanner:
    """Example planner for demonstration."""
    
    def __init__(self):
        self.last_update = time.time()
        self.update_count = 0
    
    def update(self):
        """Update the planner."""
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        self.update_count += 1
        
        # Simulate planning computation
        time.sleep(0.005)  # 5ms planning computation
        
        if self.update_count % 20 == 0:
            print(f"Planner update {self.update_count}, dt: {dt*1000:.2f}ms")


class ExampleSafetySystem:
    """Example safety system for demonstration."""
    
    def __init__(self):
        self.last_check = time.time()
        self.check_count = 0
    
    def check_safety(self):
        """Check safety conditions."""
        current_time = time.time()
        dt = current_time - self.last_check
        self.last_check = current_time
        self.check_count += 1
        
        # Simulate safety check
        time.sleep(0.0005)  # 0.5ms safety check
        
        if self.check_count % 50 == 0:
            print(f"Safety check {self.check_count}, dt: {dt*1000:.2f}ms")


# Example 1: Using decorators for real-time tasks
@control_loop_task(frequency_hz=400.0, name="example_control")
def example_control_task():
    """Example control task using decorator."""
    # This function will be automatically scheduled as a real-time task
    print("Control task executed")


@planning_loop_task(frequency_hz=50.0, name="example_planning")
def example_planning_task():
    """Example planning task using decorator."""
    # This function will be automatically scheduled as a real-time task
    print("Planning task executed")


@safety_task(name="example_safety")
def example_safety_task():
    """Example safety task using decorator."""
    # This function will be automatically scheduled as a real-time task
    print("Safety task executed")


# Example 2: Using context managers for real-time loops
async def example_context_manager_usage():
    """Demonstrate using context managers for real-time loops."""
    print("\n=== Context Manager Example ===")
    
    # Control loop with context manager
    async with real_time_control_loop() as control_loop:
        for i in range(10):
            await control_loop.iterate(lambda: print(f"Control iteration {i}"))
    
    # Planning loop with context manager
    async with real_time_planning_loop() as planning_loop:
        for i in range(5):
            await planning_loop.iterate(lambda: print(f"Planning iteration {i}"))
    
    # Safety loop with context manager
    async with real_time_safety_loop() as safety_loop:
        for i in range(20):
            await safety_loop.iterate(lambda: print(f"Safety iteration {i}"))


# Example 3: Using utility functions for real-time loops
async def example_utility_functions():
    """Demonstrate using utility functions for real-time loops."""
    print("\n=== Utility Functions Example ===")
    
    # Run control loop for 2 seconds
    await run_control_loop(
        lambda: print("Control function executed"),
        duration=2.0
    )
    
    # Run planning loop for 1 second
    await run_planning_loop(
        lambda: print("Planning function executed"),
        duration=1.0
    )
    
    # Run safety loop for 3 seconds
    await run_safety_loop(
        lambda: print("Safety function executed"),
        duration=3.0
    )


# Example 4: Integrating with existing components
async def example_component_integration():
    """Demonstrate integrating with existing components."""
    print("\n=== Component Integration Example ===")
    
    # Create example components
    controller = ExampleController()
    planner = ExamplePlanner()
    safety_system = ExampleSafetySystem()
    
    # Integrate with real-time manager
    manager = get_real_time_manager()
    integrate_with_controller(controller)
    integrate_with_planner(planner)
    integrate_with_safety_system(safety_system)
    
    # Start the real-time system
    await manager.start()
    
    # Run for 5 seconds
    await asyncio.sleep(5.0)
    
    # Stop the system
    await manager.stop()
    
    # Print statistics
    stats = manager.get_stats()
    print(f"Controller updates: {controller.update_count}")
    print(f"Planner updates: {planner.update_count}")
    print(f"Safety checks: {safety_system.check_count}")


# Example 5: Custom real-time task creation
async def example_custom_tasks():
    """Demonstrate creating custom real-time tasks."""
    print("\n=== Custom Tasks Example ===")
    
    from dart_planner.common.real_time_scheduler import RealTimeTask
    
    # Create custom task
    def custom_function():
        print("Custom real-time task executed")
    
    custom_task = RealTimeTask(
        name="custom_task",
        func=custom_function,
        priority=TaskPriority.MEDIUM,
        task_type=TaskType.PERIODIC,
        period_ms=100.0,  # 10Hz
        deadline_ms=50.0,  # 50ms deadline
        execution_time_ms=1.0,
        jitter_ms=0.1
    )
    
    # Add to manager
    manager = get_real_time_manager()
    manager.add_custom_task(custom_task)
    
    # Start and run for 2 seconds
    await manager.start()
    await asyncio.sleep(2.0)
    await manager.stop()


# Example 6: Performance monitoring
async def example_performance_monitoring():
    """Demonstrate performance monitoring."""
    print("\n=== Performance Monitoring Example ===")
    
    # Create a task that sometimes exceeds its deadline
    def variable_duration_task():
        # Simulate variable execution time
        execution_time = np.random.exponential(0.002)  # 2ms average
        time.sleep(execution_time)
    
    # Create task with tight deadline
    from dart_planner.common.real_time_scheduler import RealTimeTask
    
    performance_task = RealTimeTask(
        name="performance_test",
        func=variable_duration_task,
        priority=TaskPriority.HIGH,
        task_type=TaskType.PERIODIC,
        period_ms=10.0,  # 100Hz
        deadline_ms=5.0,  # 5ms deadline
        execution_time_ms=2.0,
        jitter_ms=0.1
    )
    
    # Add to manager and run
    manager = get_real_time_manager()
    manager.add_custom_task(performance_task)
    
    await manager.start()
    await asyncio.sleep(5.0)  # Run for 5 seconds
    
    # Monitor performance
    monitor_real_time_performance()
    
    await manager.stop()


# Example 7: Real-time configuration
def example_configuration():
    """Demonstrate real-time configuration."""
    print("\n=== Configuration Example ===")
    
    config = get_config()
    
    # Get real-time configuration
    from dart_planner.config.real_time_config import (
        get_control_loop_config, get_planning_loop_config,
        get_safety_loop_config, get_communication_config
    )
    
    control_config = get_control_loop_config(config)
    planning_config = get_planning_loop_config(config)
    safety_config = get_safety_loop_config(config)
    comm_config = get_communication_config(config)
    
    print("Control Loop Configuration:")
    for key, value in control_config.items():
        print(f"  {key}: {value}")
    
    print("\nPlanning Loop Configuration:")
    for key, value in planning_config.items():
        print(f"  {key}: {value}")
    
    print("\nSafety Loop Configuration:")
    for key, value in safety_config.items():
        print(f"  {key}: {value}")
    
    print("\nCommunication Configuration:")
    for key, value in comm_config.items():
        print(f"  {key}: {value}")


async def main():
    """Main function to run all examples."""
    print("🚀 Real-Time Integration Examples for DART-Planner")
    print("=" * 60)
    
    # Example 1: Configuration
    example_configuration()
    
    # Example 2: Context managers
    await example_context_manager_usage()
    
    # Example 3: Utility functions
    await example_utility_functions()
    
    # Example 4: Component integration
    await example_component_integration()
    
    # Example 5: Custom tasks
    await example_custom_tasks()
    
    # Example 6: Performance monitoring
    await example_performance_monitoring()
    
    print("\n✅ All examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main()) 
