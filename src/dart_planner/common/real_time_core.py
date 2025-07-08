"""
Real-Time Core Algorithms for DART-Planner

This module contains core algorithms and helper functions for real-time scheduling.
"""

import platform
import os
import time
import logging
from typing import Dict, Any, Optional
from collections import deque

from .real_time_config import RealTimeTask, TimingStats, TaskType, TaskPriority, SchedulerConfig


def check_rt_os_support() -> bool:
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


def get_rt_priority() -> int:
    """Get appropriate real-time priority for the system."""
    if platform.system().lower() == 'linux':
        return 80  # High priority for Linux
    else:
        return 0  # Default priority for other systems


def setup_rt_os(config: SchedulerConfig) -> bool:
    """Setup real-time operating system features."""
    if platform.system().lower() == 'linux':
        try:
            # Set real-time priority
            os.nice(-config.rt_priority)
            return True
        except (OSError, PermissionError) as e:
            logging.warning(f"Could not set real-time priority (requires root): {e}. Downgrading to cooperative scheduling.")
            return False
        except Exception as e:
            logging.warning(f"Unexpected error setting real-time priority: {e}. Downgrading to cooperative scheduling.")
            return False
    return False


def should_execute_task(task: RealTimeTask, current_time: float) -> bool:
    """Determine if a task should execute based on timing constraints."""
    if not task.enabled:
        return False
    
    if task.task_type == TaskType.PERIODIC:
        return current_time >= task.next_deadline
    elif task.task_type == TaskType.SPORADIC:
        time_since_last = current_time - task.last_execution
        return time_since_last >= (task.min_interarrival_ms / 1000.0)
    else:  # APERIODIC
        return True


def update_task_stats(task: RealTimeTask, execution_time: float, current_time: float) -> TimingStats:
    """Update timing statistics for a task."""
    stats = TimingStats(task_name=task.name)
    
    # Update execution time history
    task.execution_times.append(execution_time)
    task.total_executions += 1
    
    # Calculate statistics
    if task.execution_times:
        execution_times = list(task.execution_times)
        stats.mean_execution_time_ms = sum(execution_times) / len(execution_times) * 1000.0
        stats.max_execution_time_ms = max(execution_times) * 1000.0
        stats.min_execution_time_ms = min(execution_times) * 1000.0
    
    # Calculate jitter
    if task.task_type == TaskType.PERIODIC and task.period_ms > 0:
        expected_time = task.last_execution + (task.period_ms / 1000.0)
        actual_time = current_time
        jitter = abs(actual_time - expected_time)
        stats.mean_jitter_ms = jitter * 1000.0
        stats.max_jitter_ms = max(stats.max_jitter_ms, jitter * 1000.0)
    
    # Update missed deadlines
    stats.missed_deadlines = task.missed_deadlines
    stats.total_executions = task.total_executions
    stats.success_rate = 1.0 - (task.missed_deadlines / max(task.total_executions, 1))
    
    return stats


def handle_deadline_violation(task: RealTimeTask, current_time: float) -> None:
    """Handle deadline violation for a task."""
    task.missed_deadlines += 1
    logging.warning(f"Deadline violation for task '{task.name}' at {current_time:.6f}")
    
    # For critical tasks, log more details
    if task.priority.value <= 1:  # CRITICAL or HIGH
        logging.error(f"Critical deadline violation: {task.name} missed deadline by "
                     f"{(current_time - task.next_deadline) * 1000:.2f}ms")


def apply_timing_compensation(task: RealTimeTask, current_time: float, 
                            clock_drift: float, jitter_compensation: float) -> float:
    """Apply timing compensation to reduce jitter and drift."""
    if task.task_type != TaskType.PERIODIC:
        return 0.0
    
    # Calculate compensation based on drift and jitter
    compensation = clock_drift + jitter_compensation
    
    # Limit compensation to prevent over-correction
    max_compensation = task.period_ms * 0.1  # Max 10% of period
    compensation = max(-max_compensation, min(max_compensation, compensation))
    
    return compensation


def schedule_next_execution(task: RealTimeTask, current_time: float) -> None:
    """Schedule the next execution time for a task."""
    if task.task_type == TaskType.PERIODIC and task.period_ms > 0:
        task.next_deadline = current_time + (task.period_ms / 1000.0)
    else:
        task.next_deadline = current_time + (task.deadline_ms / 1000.0)


def calculate_sleep_time(task: RealTimeTask, current_time: float) -> float:
    """Calculate sleep time until next task execution."""
    if task.task_type == TaskType.PERIODIC:
        return max(0.0, task.next_deadline - current_time)
    else:
        return 0.0  # Non-periodic tasks don't sleep


def create_task_factory(priority: TaskPriority, task_type: TaskType, **kwargs):
    """Factory function to create task creation helpers."""
    def create_task(func, name: str, **task_kwargs) -> RealTimeTask:
        return RealTimeTask(
            name=name,
            func=func,
            priority=priority,
            task_type=task_type,
            **task_kwargs
        )
    return create_task 