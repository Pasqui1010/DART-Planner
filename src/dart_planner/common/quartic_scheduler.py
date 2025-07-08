"""
Quartic Cooperative Real-Time Scheduler

A high-precision cooperative real-time scheduler that replaces asyncio.sleep(dt)
for hard real-time tasks with precise timer-driven scheduling.

Features:
- Precise timer-based scheduling using high-resolution clocks
- Jitter analysis and histogram generation
- Cooperative multitasking with deadline monitoring
- Support for multiple task priorities and frequencies
- Real-time performance monitoring and statistics
- Integration with existing DART-Planner real-time infrastructure

Based on cutting-plane algorithms for real-time scheduling and modern
cooperative multitasking principles.
"""

import asyncio
import time
import threading
import platform
import warnings
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import deque, defaultdict
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .timing_utils import high_res_sleep
from .errors import RealTimeError, SchedulingError
from .real_time_config import TaskPriority, TaskType, RealTimeTask, TimingStats
from .logging_config import get_logger


@dataclass
class QuarticTask:
    """A task managed by the quartic scheduler."""
    name: str
    func: Callable
    frequency_hz: float
    priority: TaskPriority = TaskPriority.MEDIUM
    enabled: bool = True
    deadline_ms: Optional[float] = None
    
    # Timing tracking
    period_s: float = 0.0
    next_execution: float = 0.0
    last_execution: float = 0.0
    execution_count: int = 0
    missed_deadlines: int = 0
    
    # Performance monitoring
    execution_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    jitter_samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def __post_init__(self):
        """Initialize computed fields."""
        self.period_s = 1.0 / self.frequency_hz
        self.next_execution = time.perf_counter()
        self.last_execution = self.next_execution
        if self.deadline_ms is None:
            self.deadline_ms = self.period_s * 1000.0 * 0.8  # 80% of period as default deadline


@dataclass
class JitterAnalysis:
    """Analysis results for timing jitter."""
    mean_jitter_ms: float
    std_jitter_ms: float
    max_jitter_ms: float
    min_jitter_ms: float
    jitter_histogram: Dict[str, int] = field(default_factory=dict)
    samples_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'mean_jitter_ms': self.mean_jitter_ms,
            'std_jitter_ms': self.std_jitter_ms,
            'max_jitter_ms': self.max_jitter_ms,
            'min_jitter_ms': self.min_jitter_ms,
            'jitter_histogram': dict(self.jitter_histogram),
            'samples_count': self.samples_count
        }


class QuarticScheduler:
    """
    Cooperative real-time scheduler with precise timer-driven execution.
    
    This scheduler uses high-resolution timers and cooperative multitasking
    to provide precise timing for hard real-time tasks like 400 Hz control loops.
    """
    
    def __init__(self, enable_monitoring: bool = True, max_jitter_ms: float = 1.0):
        """
        Initialize the quartic scheduler.
        
        Args:
            enable_monitoring: Enable performance monitoring and jitter analysis
            max_jitter_ms: Maximum acceptable jitter in milliseconds
        """
        self.tasks: Dict[str, QuarticTask] = {}
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        self.enable_monitoring = enable_monitoring
        self.max_jitter_ms = max_jitter_ms
        
        # Timing and performance
        self.start_time = time.perf_counter()
        self.cycle_count = 0
        self.total_missed_deadlines = 0
        self.total_overruns = 0
        
        # Jitter analysis
        self.jitter_analysis: Dict[str, JitterAnalysis] = {}
        self.global_jitter_samples = deque(maxlen=10000)
        
        # Thread safety
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()
        
        # Logger
        self.logger = get_logger(__name__)
        
        # Platform-specific optimizations
        self._setup_platform_optimizations()
        
        # Overrun protection
        self.max_consecutive_overruns = 10
        self.consecutive_overrun_counts: Dict[str, int] = {}
    
    def _setup_platform_optimizations(self):
        """Setup platform-specific optimizations for precise timing."""
        system = platform.system().lower()
        
        if system == 'linux':
            # Try to set real-time priority
            try:
                import os
                os.sched_setscheduler(0, 1, os.sched_param(80))  # SCHED_FIFO, priority 80
                self.logger.info("Set Linux real-time scheduler (SCHED_FIFO)")
            except (OSError, PermissionError):
                self.logger.warning("Could not set real-time scheduler (requires root)")
        
        elif system == 'windows':
            # Set high priority on Windows
            try:
                import psutil
                process = psutil.Process()
                process.nice(psutil.HIGH_PRIORITY_CLASS)
                self.logger.info("Set Windows high priority class")
            except Exception:
                self.logger.warning("Could not set Windows high priority")
    
    def add_task(self, task: QuarticTask) -> None:
        """Add a task to the scheduler."""
        with self._lock:
            if task.name in self.tasks:
                raise SchedulingError(f"Task '{task.name}' already exists")
            
            self.tasks[task.name] = task
            self.logger.info(f"Added task '{task.name}' at {task.frequency_hz}Hz")
    
    def remove_task(self, task_name: str) -> None:
        """Remove a task from the scheduler."""
        with self._lock:
            if task_name in self.tasks:
                del self.tasks[task_name]
                self.logger.info(f"Removed task '{task_name}'")
    
    def enable_task(self, task_name: str) -> None:
        """Enable a task."""
        with self._lock:
            if task_name in self.tasks:
                self.tasks[task_name].enabled = True
                self.logger.info(f"Enabled task '{task_name}'")
    
    def disable_task(self, task_name: str) -> None:
        """Disable a task."""
        with self._lock:
            if task_name in self.tasks:
                self.tasks[task_name].enabled = False
                self.logger.info(f"Disabled task '{task_name}'")
    
    async def start(self) -> None:
        """Start the quartic scheduler."""
        if self.running:
            return
        
        self.running = True
        self.start_time = time.perf_counter()
        self._shutdown_event.clear()
        
        # Start the main scheduler loop
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        # Start monitoring if enabled
        if self.enable_monitoring:
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("Quartic scheduler started")
    
    async def stop(self) -> None:
        """Stop the quartic scheduler."""
        if not self.running:
            return
        
        self.running = False
        self._shutdown_event.set()
        
        # Cancel tasks
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Quartic scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop with precise timing."""
        while self.running and not self._shutdown_event.is_set():
            try:
                current_time = time.perf_counter()
                
                # Find the next task to execute
                next_task = self._find_next_task(current_time)
                
                if next_task:
                    # Execute the task
                    await self._execute_task(next_task, current_time)
                else:
                    # No tasks ready, sleep until next task
                    sleep_time = self._calculate_sleep_time(current_time)
                    if sleep_time > 0:
                        await high_res_sleep(sleep_time)
                
                self.cycle_count += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(0.001)  # Brief pause on error
    
    def _find_next_task(self, current_time: float) -> Optional[QuarticTask]:
        """Find the next task to execute based on priority and timing."""
        with self._lock:
            ready_tasks = []
            
            for task in self.tasks.values():
                if not task.enabled:
                    continue
                
                if current_time >= task.next_execution:
                    ready_tasks.append(task)
            
            if not ready_tasks:
                return None
            
            # Sort by priority (lower value = higher priority) and then by deadline
            ready_tasks.sort(
                key=lambda t: (t.priority.value, t.next_execution),
                reverse=False
            )
            
            return ready_tasks[0]
    
    async def _execute_task(self, task: QuarticTask, current_time: float) -> None:
        """Execute a task with precise timing measurement."""
        execution_start = time.perf_counter()
        
        try:
            # Execute the task
            if asyncio.iscoroutinefunction(task.func):
                await task.func()
            else:
                # Execute synchronous function directly to minimize overhead.
                # Users must ensure that such functions complete quickly to avoid
                # blocking the event loop. For long-running work, provide an async
                # wrapper or make the function itself awaitable.
                task.func()
            
            # Calculate execution time and jitter
            execution_time = (time.perf_counter() - execution_start) * 1000.0
            task.execution_times.append(execution_time)
            
            # Check for deadline violation
            if task.deadline_ms and execution_time > task.deadline_ms:
                task.missed_deadlines += 1
                self.total_missed_deadlines += 1
                self.logger.warning(
                    f"Deadline violation in task '{task.name}': "
                    f"{execution_time:.2f}ms > {task.deadline_ms:.2f}ms"
                )
            
            # Calculate jitter (deviation from expected execution time)
            expected_time = task.last_execution + task.period_s
            actual_time = execution_start  # Use actual execution start time
            jitter_ms = (actual_time - expected_time) * 1000.0
            
            task.jitter_samples.append(jitter_ms)
            self.global_jitter_samples.append(jitter_ms)
            
            # Update timing: preserve the original cadence to avoid drift.
            task.last_execution = current_time  # aligns with test expectations
            # Keep cadence without accumulating backlog.
            if task.next_execution + task.period_s <= current_time:
                # If we are already past the next slot (overrun), schedule from now.
                task.next_execution = current_time + task.period_s
            else:
                # Normal case: advance by exactly one period.
                task.next_execution = task.next_execution + task.period_s
            task.execution_count += 1
            
            # Check for overruns
            if execution_time > task.period_s * 1000.0:
                self.total_overruns += 1
                self.consecutive_overrun_counts[task.name] = self.consecutive_overrun_counts.get(task.name, 0) + 1
                
                # Log warning for first few overruns
                if self.consecutive_overrun_counts[task.name] <= 3:
                    self.logger.warning(
                        f"Task overrun in '{task.name}': "
                        f"{execution_time:.2f}ms > {task.period_s*1000:.2f}ms"
                    )
                
                # Temporarily disable task if it consistently overruns
                if self.consecutive_overrun_counts[task.name] >= self.max_consecutive_overruns:
                    self.logger.error(
                        f"Task '{task.name}' disabled due to {self.consecutive_overrun_counts[task.name]} "
                        f"consecutive overruns. Execution time: {execution_time:.2f}ms"
                    )
                    task.enabled = False
                    # Reset counter when task is disabled
                    self.consecutive_overrun_counts[task.name] = 0
            else:
                # Reset consecutive overrun counter on successful execution
                self.consecutive_overrun_counts[task.name] = 0
            
        except Exception as e:
            self.logger.error(f"Error executing task '{task.name}': {e}")
            # Don't update timing on error to prevent cascading failures
    
    def _calculate_sleep_time(self, current_time: float) -> float:
        """Calculate sleep time until next task execution."""
        with self._lock:
            if not self.tasks:
                return 0.001  # Default 1ms sleep
            
            # Find the earliest next execution time
            next_times = [
                task.next_execution - current_time
                for task in self.tasks.values()
                if task.enabled
            ]
            
            if not next_times:
                return 0.001
            
            min_sleep = min(next_times)
            # If any task is overdue (negative or zero sleep time), clamp to minimum sleep
            if min_sleep <= 0:
                return 0.0001  # Minimum 0.1ms sleep to yield control
            
            return max(0.0001, min_sleep)  # Minimum 0.1ms, maximum sleep time
    
    async def _monitoring_loop(self) -> None:
        """Monitoring loop for performance analysis."""
        while self.running and not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(1.0)  # Update every second
                
                # Update jitter analysis
                self._update_jitter_analysis()
                
                # Log performance statistics
                if self.cycle_count % 100 == 0:  # Log every 100 cycles
                    self._log_performance()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
    
    def _update_jitter_analysis(self) -> None:
        """Update jitter analysis for all tasks."""
        with self._lock:
            for task_name, task in self.tasks.items():
                if len(task.jitter_samples) < 10:
                    continue  # Need at least 10 samples
                
                jitter_array = np.array(list(task.jitter_samples))
                
                analysis = JitterAnalysis(
                    mean_jitter_ms=float(np.mean(jitter_array)),
                    std_jitter_ms=float(np.std(jitter_array)),
                    max_jitter_ms=float(np.max(jitter_array)),
                    min_jitter_ms=float(np.min(jitter_array)),
                    samples_count=len(jitter_array)
                )
                
                # Create histogram
                hist, bins = np.histogram(jitter_array, bins=20)
                for i, count in enumerate(hist):
                    bin_label = f"{bins[i]:.2f}-{bins[i+1]:.2f}"
                    analysis.jitter_histogram[bin_label] = int(count)
                
                self.jitter_analysis[task_name] = analysis
    
    def _log_performance(self) -> None:
        """Log performance statistics."""
        runtime = time.perf_counter() - self.start_time
        avg_frequency = self.cycle_count / runtime if runtime > 0 else 0
        
        self.logger.info(
            f"Quartic Scheduler Performance: "
            f"Cycles={self.cycle_count}, "
            f"AvgFreq={avg_frequency:.1f}Hz, "
            f"MissedDeadlines={self.total_missed_deadlines}, "
            f"Overruns={self.total_overruns}"
        )
    
    def get_task_stats(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific task."""
        with self._lock:
            if task_name not in self.tasks:
                return None
            
            task = self.tasks[task_name]
            runtime = time.perf_counter() - self.start_time
            
            stats = {
                'name': task.name,
                'frequency_hz': task.frequency_hz,
                'priority': task.priority.name,
                'enabled': task.enabled,
                'execution_count': task.execution_count,
                'missed_deadlines': task.missed_deadlines,
                'actual_frequency_hz': task.execution_count / runtime if runtime > 0 else 0,
                'deadline_ms': task.deadline_ms,
                'period_ms': task.period_s * 1000.0
            }
            
            # Add execution time statistics
            if task.execution_times:
                exec_times = list(task.execution_times)
                stats.update({
                    'mean_execution_time_ms': float(np.mean(exec_times)),
                    'max_execution_time_ms': float(np.max(exec_times)),
                    'min_execution_time_ms': float(np.min(exec_times)),
                    'std_execution_time_ms': float(np.std(exec_times))
                })
            
            # Add jitter analysis
            if task_name in self.jitter_analysis:
                stats['jitter_analysis'] = self.jitter_analysis[task_name].to_dict()
            
            return stats
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all tasks."""
        with self._lock:
            result = {}
            for task_name in self.tasks.keys():
                stats = self.get_task_stats(task_name)
                if stats:
                    result[task_name] = stats
            return result
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global scheduler statistics."""
        runtime = time.perf_counter() - self.start_time
        
        return {
            'runtime_s': runtime,
            'cycle_count': self.cycle_count,
            'total_missed_deadlines': self.total_missed_deadlines,
            'total_overruns': self.total_overruns,
            'average_frequency_hz': self.cycle_count / runtime if runtime > 0 else 0,
            'task_count': len(self.tasks),
            'enabled_task_count': sum(1 for t in self.tasks.values() if t.enabled)
        }
    
    def generate_jitter_histogram(self, task_name: Optional[str] = None, 
                                 save_path: Optional[str] = None) -> None:
        """
        Generate and optionally save jitter histogram.
        
        Args:
            task_name: Specific task to analyze (None for global)
            save_path: Path to save the histogram image
        """
        if task_name and task_name not in self.jitter_analysis:
            self.logger.warning(f"No jitter data available for task '{task_name}'")
            return
        
        if task_name:
            analysis = self.jitter_analysis[task_name]
            samples = list(self.tasks[task_name].jitter_samples)
            title = f"Jitter Histogram - {task_name}"
        else:
            # Global jitter analysis
            samples = list(self.global_jitter_samples)
            if not samples:
                self.logger.warning("No global jitter data available")
                return
            
            analysis = JitterAnalysis(
                mean_jitter_ms=float(np.mean(samples)),
                std_jitter_ms=float(np.std(samples)),
                max_jitter_ms=float(np.max(samples)),
                min_jitter_ms=float(np.min(samples)),
                samples_count=len(samples)
            )
            title = "Global Jitter Histogram"
        
        # Create histogram
        plt.figure(figsize=(12, 8))
        
        # Main histogram
        plt.subplot(2, 1, 1)
        plt.hist(samples, bins=50, alpha=0.7, edgecolor='black')
        plt.axvline(analysis.mean_jitter_ms, color='red', linestyle='--', 
                   label=f'Mean: {analysis.mean_jitter_ms:.3f}ms')
        plt.axvline(analysis.mean_jitter_ms + analysis.std_jitter_ms, color='orange', 
                   linestyle=':', label=f'+1σ: {analysis.mean_jitter_ms + analysis.std_jitter_ms:.3f}ms')
        plt.axvline(analysis.mean_jitter_ms - analysis.std_jitter_ms, color='orange', 
                   linestyle=':', label=f'-1σ: {analysis.mean_jitter_ms - analysis.std_jitter_ms:.3f}ms')
        plt.axvline(self.max_jitter_ms, color='red', linestyle='-', 
                   label=f'Max Acceptable: {self.max_jitter_ms:.3f}ms')
        
        plt.xlabel('Jitter (ms)')
        plt.ylabel('Frequency')
        plt.title(title)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Statistics table
        plt.subplot(2, 1, 2)
        plt.axis('off')
        
        stats_text = f"""
        Jitter Statistics:
        - Mean: {analysis.mean_jitter_ms:.3f} ms
        - Std Dev: {analysis.std_jitter_ms:.3f} ms
        - Max: {analysis.max_jitter_ms:.3f} ms
        - Min: {analysis.min_jitter_ms:.3f} ms
        - Samples: {analysis.samples_count}
        - Max Acceptable: {self.max_jitter_ms:.3f} ms
        """
        
        plt.text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Jitter histogram saved to {save_path}")
        
        plt.show()


# Convenience functions for common task creation
def create_control_task(func: Callable, frequency_hz: float = 400.0, 
                       name: str = "control_loop") -> QuarticTask:
    """Create a high-frequency control task."""
    return QuarticTask(
        name=name,
        func=func,
        frequency_hz=frequency_hz,
        priority=TaskPriority.HIGH,
        deadline_ms=1.0 / frequency_hz * 1000.0 * 0.8  # 80% of period
    )


def create_planning_task(func: Callable, frequency_hz: float = 50.0,
                        name: str = "planning_loop") -> QuarticTask:
    """Create a medium-frequency planning task."""
    return QuarticTask(
        name=name,
        func=func,
        frequency_hz=frequency_hz,
        priority=TaskPriority.MEDIUM,
        deadline_ms=1.0 / frequency_hz * 1000.0 * 0.9  # 90% of period
    )


def create_safety_task(func: Callable, frequency_hz: float = 100.0,
                      name: str = "safety_monitor") -> QuarticTask:
    """Create a safety monitoring task."""
    return QuarticTask(
        name=name,
        func=func,
        frequency_hz=frequency_hz,
        priority=TaskPriority.CRITICAL,
        deadline_ms=1.0 / frequency_hz * 1000.0 * 0.7  # 70% of period
    )


# Context manager for easy scheduler usage
@asynccontextmanager
async def quartic_scheduler_context(enable_monitoring: bool = True, 
                                   max_jitter_ms: float = 1.0):
    """Context manager for quartic scheduler."""
    scheduler = QuarticScheduler(enable_monitoring, max_jitter_ms)
    try:
        await scheduler.start()
        yield scheduler
    finally:
        await scheduler.stop() 