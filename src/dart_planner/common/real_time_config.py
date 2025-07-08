"""
Real-Time Configuration for DART-Planner

This module contains configuration classes and enums for the real-time scheduling system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
from collections import deque
import time


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


@dataclass
class SchedulerConfig:
    """Configuration for the real-time scheduler."""
    enable_rt_os: bool = True
    monitoring_enabled: bool = True
    rt_priority: int = 80  # Default real-time priority
    max_task_history: int = 100  # Maximum execution time history per task
    performance_log_interval: float = 60.0  # Seconds between performance logs 