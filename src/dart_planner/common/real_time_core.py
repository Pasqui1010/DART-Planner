"""
Real-Time Core Algorithms for DART-Planner

This module contains core algorithms and helper functions for real-time scheduling.
"""

import platform
import os
import time
import logging
import threading
from typing import Dict, Any, Optional
from collections import deque

# Platform-specific imports
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import ctypes
    from ctypes import wintypes
    WINDOWS_AVAILABLE = platform.system().lower() == 'windows'
except ImportError:
    WINDOWS_AVAILABLE = False

from .real_time_config import RealTimeTask, TimingStats, TaskType, TaskPriority, SchedulerConfig


def set_thread_priority(priority: int = 90) -> bool:
    """
    Set OS thread priority for real-time performance.
    
    Args:
        priority: Priority level (1-99 for Linux, 1-31 for Windows)
        
    Returns:
        True if successful, False otherwise
    """
    system = platform.system().lower()
    
    if system == 'linux':
        return _set_linux_thread_priority(priority)
    elif system == 'windows':
        return _set_windows_thread_priority(priority)
    else:
        logging.warning(f"Thread priority setting not supported on {system}")
        return False


def _set_linux_thread_priority(priority: int) -> bool:
    """Set Linux thread priority using SCHED_FIFO."""
    try:
        import os
        # Set scheduler policy to SCHED_FIFO (1) with priority
        os.sched_setscheduler(0, 1, os.sched_param(priority))
        logging.info(f"Set Linux thread priority to {priority} (SCHED_FIFO)")
        return True
    except (OSError, PermissionError) as e:
        logging.warning(f"Could not set Linux thread priority (requires root): {e}")
        return False
    except Exception as e:
        logging.warning(f"Unexpected error setting Linux thread priority: {e}")
        return False


def _set_windows_thread_priority(priority: int) -> bool:
    """Set Windows thread priority using REALTIME_PRIORITY_CLASS."""
    try:
        if not WINDOWS_AVAILABLE:
            return False
            
        # Map priority to Windows priority class
        if priority >= 90:
            win_priority = 0x00000100  # REALTIME_PRIORITY_CLASS
        elif priority >= 70:
            win_priority = 0x00008000  # HIGH_PRIORITY_CLASS
        elif priority >= 50:
            win_priority = 0x00004000  # ABOVE_NORMAL_PRIORITY_CLASS
        elif priority >= 30:
            win_priority = 0x00002000  # NORMAL_PRIORITY_CLASS
        else:
            win_priority = 0x00004000  # BELOW_NORMAL_PRIORITY_CLASS
        
        # Set process priority class
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetCurrentProcess()
        kernel32.SetPriorityClass(handle, win_priority)
        
        logging.info(f"Set Windows thread priority to {priority} (class: {win_priority})")
        return True
        
    except Exception as e:
        logging.warning(f"Could not set Windows thread priority: {e}")
        return False


def set_current_thread_priority(priority: int = 90) -> bool:
    """
    Set priority for the current thread only.
    
    Args:
        priority: Priority level (1-99 for Linux, 1-31 for Windows)
        
    Returns:
        True if successful, False otherwise
    """
    system = platform.system().lower()
    
    if system == 'linux':
        return _set_linux_current_thread_priority(priority)
    elif system == 'windows':
        return _set_windows_current_thread_priority(priority)
    else:
        logging.warning(f"Thread priority setting not supported on {system}")
        return False


def _set_linux_current_thread_priority(priority: int) -> bool:
    """Set Linux current thread priority using SCHED_FIFO."""
    try:
        import os
        # Set scheduler policy to SCHED_FIFO (1) with priority for current thread
        os.sched_setscheduler(0, 1, os.sched_param(priority))
        logging.info(f"Set Linux current thread priority to {priority} (SCHED_FIFO)")
        return True
    except (OSError, PermissionError) as e:
        logging.warning(f"Could not set Linux current thread priority (requires root): {e}")
        return False
    except Exception as e:
        logging.warning(f"Unexpected error setting Linux current thread priority: {e}")
        return False


def _set_windows_current_thread_priority(priority: int) -> bool:
    """Set Windows current thread priority."""
    try:
        if not WINDOWS_AVAILABLE:
            return False
            
        # Map priority to Windows thread priority
        if priority >= 90:
            win_priority = 31  # THREAD_PRIORITY_TIME_CRITICAL
        elif priority >= 70:
            win_priority = 15  # THREAD_PRIORITY_HIGHEST
        elif priority >= 50:
            win_priority = 2   # THREAD_PRIORITY_ABOVE_NORMAL
        elif priority >= 30:
            win_priority = 0   # THREAD_PRIORITY_NORMAL
        else:
            win_priority = -2  # THREAD_PRIORITY_BELOW_NORMAL
        
        # Set thread priority
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetCurrentThread()
        kernel32.SetThreadPriority(handle, win_priority)
        
        logging.info(f"Set Windows current thread priority to {priority} (level: {win_priority})")
        return True
        
    except Exception as e:
        logging.warning(f"Could not set Windows current thread priority: {e}")
        return False


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
    success = False
    
    # Set thread priority
    if config.rt_priority > 0:
        success = set_thread_priority(config.rt_priority)
        if not success:
            logging.warning("Failed to set thread priority, continuing with default priority")
    
    # Additional real-time setup
    if platform.system().lower() == 'linux':
        try:
            # Set process nice value as fallback
            os.nice(-config.rt_priority)
            success = True
        except (OSError, PermissionError) as e:
            logging.warning(f"Could not set process nice value (requires root): {e}")
        except Exception as e:
            logging.warning(f"Unexpected error setting process nice value: {e}")
    
    return success


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