# Real-Time Scheduling System for DART-Planner

## Overview

The DART-Planner real-time scheduling system provides comprehensive support for real-time applications with the following key features:

1. **Replaces blocking sleep with async sleep** - Eliminates blocking `time.sleep()` calls that can cause timing jitter
2. **Implements proper real-time scheduling** - Priority-based scheduling with deadline monitoring
3. **Adds timing compensation** - Automatic compensation for clock drift and jitter
4. **Uses real-time operating system features** - Integration with RTOS capabilities when available
5. **Provides performance monitoring** - Real-time statistics and deadline violation detection

## Architecture

### Core Components

#### 1. RealTimeScheduler (`src/common/real_time_scheduler.py`)
The core scheduling engine that manages real-time tasks with:
- Priority-based preemptive scheduling
- Deadline monitoring and violation detection
- Timing compensation for jitter and drift
- Performance statistics collection

#### 2. RealTimeManager (`src/common/real_time_integration.py`)
High-level interface for managing real-time tasks and integrating with existing components.

#### 3. RealTimeConfig (`src/config/real_time_config.py`)
Configuration system for real-time parameters including:
- Task timing requirements
- Performance thresholds
- Scheduling policies

### Task Types and Priorities

```python
from src.common.real_time_scheduler import TaskPriority, TaskType

# Task Priorities (lower number = higher priority)
TaskPriority.CRITICAL    # Safety-critical tasks (emergency stop, collision avoidance)
TaskPriority.HIGH        # High-frequency control loops (400Hz+)
TaskPriority.MEDIUM      # Planning and state estimation (50Hz)
TaskPriority.LOW         # Communication and logging (10Hz)
TaskPriority.BACKGROUND  # Non-critical background tasks

# Task Types
TaskType.PERIODIC        # Fixed frequency tasks
TaskType.APERIODIC       # Event-driven tasks
TaskType.SPORADIC        # Tasks with minimum inter-arrival time
```

## Usage Patterns

### 1. Using Decorators (Simplest)

```python
from src.common.real_time_integration import control_loop_task, planning_loop_task, safety_task

@control_loop_task(frequency_hz=400.0, name="my_control")
def my_control_function():
    # This runs at 400Hz with high priority
    pass

@planning_loop_task(frequency_hz=50.0, name="my_planning")
def my_planning_function():
    # This runs at 50Hz with medium priority
    pass

@safety_task(name="my_safety")
def my_safety_function():
    # This runs with critical priority
    pass
```

### 2. Using Context Managers

```python
from src.common.real_time_integration import real_time_control_loop

async def my_control_loop():
    async with real_time_control_loop() as loop:
        while True:
            await loop.iterate(my_control_function)
```

### 3. Using Utility Functions

```python
from src.common.real_time_integration import run_control_loop

async def main():
    await run_control_loop(my_control_function, duration=10.0)
```

### 4. Manual Task Creation

```python
from src.common.real_time_scheduler import RealTimeTask, TaskPriority, TaskType

def my_function():
    pass

task = RealTimeTask(
    name="my_task",
    func=my_function,
    priority=TaskPriority.HIGH,
    task_type=TaskType.PERIODIC,
    period_ms=10.0,  # 100Hz
    deadline_ms=5.0,  # 5ms deadline
    execution_time_ms=1.0,
    jitter_ms=0.1
)

manager = get_real_time_manager()
manager.add_custom_task(task)
```

## Configuration

### Real-Time Configuration

The real-time system uses a hierarchical configuration system:

```python
from dart_planner.config.frozen_config import get_frozen_config as get_config
from src.config.real_time_config import get_real_time_config

config = get_config()
rt_config = get_real_time_config(config)

# Access specific configurations
control_config = rt_config.task_timing.control_loop_frequency_hz
planning_config = rt_config.task_timing.planning_loop_frequency_hz
safety_config = rt_config.task_timing.safety_loop_frequency_hz
```

### Environment Variables

You can override configuration using environment variables:

```bash
# Control loop settings
export DART_RT_CONTROL_FREQUENCY_HZ=400
export DART_RT_CONTROL_DEADLINE_MS=2.5

# Planning loop settings
export DART_RT_PLANNING_FREQUENCY_HZ=50
export DART_RT_PLANNING_DEADLINE_MS=20

# Safety loop settings
export DART_RT_SAFETY_FREQUENCY_HZ=100
export DART_RT_SAFETY_DEADLINE_MS=10

# Performance monitoring
export DART_RT_ENABLE_MONITORING=true
export DART_RT_MONITORING_FREQUENCY_HZ=10
```

## Integration with Existing Components

### Controller Integration

```python
from src.common.real_time_integration import integrate_with_controller

class MyController:
    def update(self):
        # Your control logic here
        pass

controller = MyController()
manager = integrate_with_controller(controller)
await manager.start()
```

### Planner Integration

```python
from src.common.real_time_integration import integrate_with_planner

class MyPlanner:
    def update(self):
        # Your planning logic here
        pass

planner = MyPlanner()
manager = integrate_with_planner(planner)
await manager.start()
```

### Safety System Integration

```python
from src.common.real_time_integration import integrate_with_safety_system

class MySafetySystem:
    def check_safety(self):
        # Your safety logic here
        pass

safety_system = MySafetySystem()
manager = integrate_with_safety_system(safety_system)
await manager.start()
```

## Performance Monitoring

### Real-Time Statistics

```python
from src.common.real_time_integration import monitor_real_time_performance

# Print current performance statistics
monitor_real_time_performance()

# Get detailed statistics
manager = get_real_time_manager()
stats = manager.get_stats()

print(f"Total cycles: {stats['scheduler_stats']['total_cycles']}")
print(f"Missed deadlines: {stats['scheduler_stats']['missed_deadlines']}")
print(f"Average cycle time: {stats['scheduler_stats']['average_cycle_time_ms']:.2f}ms")
```

### Task-Specific Statistics

```python
task_stats = manager.get_task_stats("control_loop")
print(f"Success rate: {task_stats.success_rate*100:.1f}%")
print(f"Mean execution time: {task_stats.mean_execution_time_ms:.2f}ms")
print(f"Max execution time: {task_stats.max_execution_time_ms:.2f}ms")
print(f"Missed deadlines: {task_stats.missed_deadlines}")
```

## Migration from Blocking Sleep

### Automatic Migration

The system includes a script to automatically replace blocking sleep calls:

```bash
# Dry run to see what would be changed
python scripts/simple_sleep_replacement.py --directory src --dry-run

# Apply changes
python scripts/simple_sleep_replacement.py --directory src
```

### Manual Migration

For manual migration, replace:

```python
# Old (blocking)
import time
time.sleep(0.01)

# New (async)
import asyncio
await asyncio.sleep(0.01)
```

### Function Migration

For functions that need to be made async:

```python
from src.common.real_time_integration import migrate_sleep_to_async

def my_sync_function():
    time.sleep(0.01)
    return "result"

# Convert to async
async_my_function = migrate_sleep_to_async(my_sync_function)
```

## Real-Time Operating System Integration

### Linux RT Support

The system automatically detects and uses Linux real-time features:

```bash
# Check if PREEMPT_RT kernel is available
cat /proc/version | grep preempt

# Set real-time priority (requires root)
sudo nice -n -80 python your_script.py
```

### Windows Support

Windows has limited real-time support, but the system will still provide:
- Priority-based scheduling
- Deadline monitoring
- Performance statistics

## Best Practices

### 1. Task Design

- Keep task execution times predictable
- Use appropriate priorities for different task types
- Set realistic deadlines based on worst-case execution time

### 2. Performance Monitoring

- Monitor deadline violations regularly
- Set up alerts for performance degradation
- Use performance statistics to optimize task scheduling

### 3. Error Handling

```python
from src.common.errors import RealTimeError, SchedulingError

try:
    await manager.start()
except RealTimeError as e:
    print(f"Real-time error: {e}")
except SchedulingError as e:
    print(f"Scheduling error: {e}")
```

### 4. Configuration Management

- Use environment variables for deployment-specific settings
- Validate configuration parameters
- Monitor configuration changes in production

## Example Applications

### Complete Real-Time System

```python
import asyncio
from src.common.real_time_integration import (
    get_real_time_manager, control_loop_task, planning_loop_task, safety_task
)

@control_loop_task(frequency_hz=400.0)
def control_loop():
    # High-frequency control logic
    pass

@planning_loop_task(frequency_hz=50.0)
def planning_loop():
    # Medium-frequency planning logic
    pass

@safety_task()
def safety_loop():
    # Critical safety checks
    pass

async def main():
    manager = get_real_time_manager()
    await manager.start()
    
    try:
        # Run for 60 seconds
        await asyncio.sleep(60.0)
    finally:
        await manager.stop()
        monitor_real_time_performance()

if __name__ == "__main__":
    asyncio.run(main())
```

### Performance Testing

```python
from src.common.real_time_integration import run_control_loop
import time

def performance_test_function():
    # Simulate variable workload
    workload = time.time() % 1.0
    time.sleep(workload * 0.005)  # 0-5ms

async def test_performance():
    await run_control_loop(performance_test_function, duration=30.0)
    monitor_real_time_performance()
```

## Troubleshooting

### Common Issues

1. **Deadline Violations**
   - Check task execution times
   - Adjust deadlines or optimize code
   - Monitor system load

2. **High Jitter**
   - Check for blocking operations
   - Use async alternatives
   - Monitor system interrupts

3. **Performance Degradation**
   - Check for memory leaks
   - Monitor CPU usage
   - Review task priorities

### Debugging Tools

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Get detailed task information
manager = get_real_time_manager()
for task_name, task in manager.scheduler.tasks.items():
    print(f"Task: {task_name}")
    print(f"  Priority: {task.priority}")
    print(f"  Type: {task.task_type}")
    print(f"  Period: {task.period_ms}ms")
    print(f"  Deadline: {task.deadline_ms}ms")
```

## Future Enhancements

1. **Multi-Core Support** - CPU affinity and load balancing
2. **Advanced Scheduling** - EDF, rate monotonic scheduling
3. **Real-Time Communication** - Zero-copy message passing
4. **Hardware Integration** - FPGA, GPU acceleration
5. **Distributed Real-Time** - Network real-time protocols

## Recent Improvements (2024)

- **Phase-Aligned Scheduling:** All periodic tasks use phase-aligned scheduling (`next_deadline += period`), eliminating cumulative drift.
- **Jitter Compensation Clamping:** Jitter/drift compensation is clamped to prevent negative sleep times, avoiding 100% CPU usage on timing anomalies.
- **Lazy Task Registration:** Tasks are only registered with the scheduler when a real callback is set, preventing CPU burn from placeholder or pass functions.
- **Thread/Concurrency Safety:**
    - All registration and resolution in the DI container is protected by a reentrant lock (`RLock`).
    - The DI container can be finalized to prevent further registration after startup, ensuring thread safety during async initialization.
- **Hardware Adapter Robustness:**
    - All hardware adapters raise `UnsupportedCommandError` for unsupported commands (never `NotImplementedError`).
    - All adapters expose a `get_capabilities()` API with a `supported_commands` field for introspection.
    - Mission logic should check `supported_commands` or catch `UnsupportedCommandError` to avoid task crashes.

## Conclusion

The DART-Planner real-time scheduling system provides a comprehensive solution for real-time applications with minimal changes to existing code. By using the provided decorators, context managers, and utility functions, you can easily integrate real-time capabilities into your applications while maintaining high performance and reliability. 