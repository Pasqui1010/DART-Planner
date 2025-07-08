"""
Unit tests for the Quartic Scheduler.

Tests the cooperative real-time scheduler with precise timers,
jitter analysis, and performance monitoring.
"""

import pytest
import asyncio
import time
import numpy as np
from unittest.mock import Mock, patch
from pathlib import Path

from dart_planner.common.quartic_scheduler import (
    QuarticScheduler, QuarticTask, JitterAnalysis,
    create_control_task, create_planning_task, create_safety_task,
    quartic_scheduler_context
)
from dart_planner.common.real_time_config import TaskPriority
from dart_planner.common.errors import SchedulingError


class TestQuarticTask:
    """Test QuarticTask functionality."""
    
    def test_task_initialization(self):
        """Test QuarticTask initialization and computed fields."""
        def mock_func():
            pass
        
        task = QuarticTask(
            name="test_task",
            func=mock_func,
            frequency_hz=100.0,
            priority=TaskPriority.HIGH
        )
        
        assert task.name == "test_task"
        assert task.func == mock_func
        assert task.frequency_hz == 100.0
        assert task.priority == TaskPriority.HIGH
        assert task.enabled is True
        assert task.period_s == 0.01  # 1/100
        assert task.execution_count == 0
        assert task.missed_deadlines == 0
        assert task.deadline_ms == 8.0  # 80% of 10ms period
    
    def test_task_custom_deadline(self):
        """Test QuarticTask with custom deadline."""
        def mock_func():
            pass
        
        task = QuarticTask(
            name="test_task",
            func=mock_func,
            frequency_hz=50.0,
            deadline_ms=15.0
        )
        
        assert task.deadline_ms == 15.0
        assert task.period_s == 0.02  # 1/50


class TestJitterAnalysis:
    """Test JitterAnalysis functionality."""
    
    def test_jitter_analysis_creation(self):
        """Test JitterAnalysis initialization."""
        analysis = JitterAnalysis(
            mean_jitter_ms=1.5,
            std_jitter_ms=0.3,
            max_jitter_ms=2.1,
            min_jitter_ms=0.9,
            samples_count=100
        )
        
        assert analysis.mean_jitter_ms == 1.5
        assert analysis.std_jitter_ms == 0.3
        assert analysis.max_jitter_ms == 2.1
        assert analysis.min_jitter_ms == 0.9
        assert analysis.samples_count == 100
        assert analysis.jitter_histogram == {}
    
    def test_jitter_analysis_to_dict(self):
        """Test JitterAnalysis serialization."""
        analysis = JitterAnalysis(
            mean_jitter_ms=1.5,
            std_jitter_ms=0.3,
            max_jitter_ms=2.1,
            min_jitter_ms=0.9,
            samples_count=100
        )
        analysis.jitter_histogram = {"0-1": 50, "1-2": 30, "2-3": 20}
        
        result = analysis.to_dict()
        
        assert result['mean_jitter_ms'] == 1.5
        assert result['std_jitter_ms'] == 0.3
        assert result['max_jitter_ms'] == 2.1
        assert result['min_jitter_ms'] == 0.9
        assert result['samples_count'] == 100
        assert result['jitter_histogram'] == {"0-1": 50, "1-2": 30, "2-3": 20}


class TestQuarticScheduler:
    """Test QuarticScheduler functionality."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a QuarticScheduler instance for testing."""
        return QuarticScheduler(enable_monitoring=False)
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock task for testing."""
        def mock_func():
            time.sleep(0.001)  # Simulate 1ms work
        
        return QuarticTask(
            name="test_task",
            func=mock_func,
            frequency_hz=100.0,
            priority=TaskPriority.MEDIUM
        )
    
    def test_scheduler_initialization(self, scheduler):
        """Test QuarticScheduler initialization."""
        assert scheduler.tasks == {}
        assert scheduler.running is False
        assert scheduler.enable_monitoring is False
        assert scheduler.max_jitter_ms == 1.0
        assert scheduler.cycle_count == 0
        assert scheduler.total_missed_deadlines == 0
        assert scheduler.total_overruns == 0
    
    def test_add_task(self, scheduler, mock_task):
        """Test adding tasks to scheduler."""
        scheduler.add_task(mock_task)
        
        assert "test_task" in scheduler.tasks
        assert scheduler.tasks["test_task"] == mock_task
    
    def test_add_duplicate_task(self, scheduler, mock_task):
        """Test adding duplicate task raises error."""
        scheduler.add_task(mock_task)
        
        with pytest.raises(SchedulingError, match="Task 'test_task' already exists"):
            scheduler.add_task(mock_task)
    
    def test_remove_task(self, scheduler, mock_task):
        """Test removing tasks from scheduler."""
        scheduler.add_task(mock_task)
        scheduler.remove_task("test_task")
        
        assert "test_task" not in scheduler.tasks
    
    def test_enable_disable_task(self, scheduler, mock_task):
        """Test enabling and disabling tasks."""
        scheduler.add_task(mock_task)
        
        # Initially enabled
        assert scheduler.tasks["test_task"].enabled is True
        
        # Disable
        scheduler.disable_task("test_task")
        assert scheduler.tasks["test_task"].enabled is False
        
        # Enable
        scheduler.enable_task("test_task")
        assert scheduler.tasks["test_task"].enabled is True
    
    def test_find_next_task_empty(self, scheduler):
        """Test finding next task when no tasks are available."""
        current_time = time.perf_counter()
        next_task = scheduler._find_next_task(current_time)
        
        assert next_task is None
    
    def test_find_next_task_disabled(self, scheduler, mock_task):
        """Test finding next task when all tasks are disabled."""
        mock_task.enabled = False
        scheduler.add_task(mock_task)
        
        current_time = time.perf_counter()
        next_task = scheduler._find_next_task(current_time)
        
        assert next_task is None
    
    def test_find_next_task_not_ready(self, scheduler, mock_task):
        """Test finding next task when no tasks are ready to execute."""
        scheduler.add_task(mock_task)
        
        # Set next execution far in the future
        mock_task.next_execution = time.perf_counter() + 1.0
        
        current_time = time.perf_counter()
        next_task = scheduler._find_next_task(current_time)
        
        assert next_task is None
    
    def test_find_next_task_ready(self, scheduler, mock_task):
        """Test finding next task when tasks are ready to execute."""
        scheduler.add_task(mock_task)
        
        # Set next execution in the past
        mock_task.next_execution = time.perf_counter() - 0.1
        
        current_time = time.perf_counter()
        next_task = scheduler._find_next_task(current_time)
        
        assert next_task == mock_task
    
    def test_find_next_task_priority_order(self, scheduler):
        """Test that tasks are selected by priority order."""
        def mock_func1():
            pass
        
        def mock_func2():
            pass
        
        task1 = QuarticTask(
            name="low_priority",
            func=mock_func1,
            frequency_hz=100.0,
            priority=TaskPriority.LOW
        )
        
        task2 = QuarticTask(
            name="high_priority",
            func=mock_func2,
            frequency_hz=100.0,
            priority=TaskPriority.HIGH
        )
        
        scheduler.add_task(task1)
        scheduler.add_task(task2)
        
        # Set both tasks ready
        task1.next_execution = time.perf_counter() - 0.1
        task2.next_execution = time.perf_counter() - 0.1
        
        current_time = time.perf_counter()
        next_task = scheduler._find_next_task(current_time)
        
        # High priority task should be selected
        assert next_task == task2
    
    @pytest.mark.asyncio
    async def test_execute_task_sync(self, scheduler, mock_task):
        """Test executing a synchronous task."""
        scheduler.add_task(mock_task)
        current_time = time.perf_counter()
        
        await scheduler._execute_task(mock_task, current_time)
        
        assert mock_task.execution_count == 1
        assert len(mock_task.execution_times) == 1
        assert len(mock_task.jitter_samples) == 1
        assert mock_task.last_execution == current_time
        assert mock_task.next_execution > current_time
    
    @pytest.mark.asyncio
    async def test_execute_task_async(self, scheduler):
        """Test executing an asynchronous task."""
        async def async_func():
            await asyncio.sleep(0.001)
        
        task = QuarticTask(
            name="async_task",
            func=async_func,
            frequency_hz=100.0
        )
        
        scheduler.add_task(task)
        current_time = time.perf_counter()
        
        await scheduler._execute_task(task, current_time)
        
        assert task.execution_count == 1
        assert len(task.execution_times) == 1
        assert len(task.jitter_samples) == 1
    
    @pytest.mark.asyncio
    async def test_execute_task_deadline_violation(self, scheduler):
        """Test deadline violation detection."""
        def slow_func():
            time.sleep(0.02)  # 20ms execution time
        
        task = QuarticTask(
            name="slow_task",
            func=slow_func,
            frequency_hz=100.0,
            deadline_ms=10.0  # 10ms deadline
        )
        
        scheduler.add_task(task)
        current_time = time.perf_counter()
        
        await scheduler._execute_task(task, current_time)
        
        assert task.missed_deadlines == 1
        assert scheduler.total_missed_deadlines == 1
    
    def test_calculate_sleep_time_no_tasks(self, scheduler):
        """Test sleep time calculation with no tasks."""
        current_time = time.perf_counter()
        sleep_time = scheduler._calculate_sleep_time(current_time)
        
        assert sleep_time == 0.001  # Default minimum sleep
    
    def test_calculate_sleep_time_with_tasks(self, scheduler, mock_task):
        """Test sleep time calculation with tasks."""
        scheduler.add_task(mock_task)
        
        # Set next execution in the future
        mock_task.next_execution = time.perf_counter() + 0.05
        
        current_time = time.perf_counter()
        sleep_time = scheduler._calculate_sleep_time(current_time)
        
        assert 0.049 < sleep_time < 0.051  # Should be approximately 50ms
    
    def test_calculate_sleep_time_past_deadline(self, scheduler, mock_task):
        """Test sleep time calculation when deadline is in the past."""
        scheduler.add_task(mock_task)
        
        # Set next execution in the past
        mock_task.next_execution = time.perf_counter() - 0.1
        
        current_time = time.perf_counter()
        sleep_time = scheduler._calculate_sleep_time(current_time)
        
        assert sleep_time == 0.0001  # Minimum sleep time
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test scheduler start and stop functionality."""
        assert scheduler.running is False
        
        # Start scheduler
        await scheduler.start()
        assert scheduler.running is True
        assert scheduler.scheduler_task is not None
        
        # Stop scheduler
        await scheduler.stop()
        assert scheduler.running is False
    
    @pytest.mark.asyncio
    async def test_scheduler_with_tasks(self, scheduler, mock_task):
        """Test scheduler running with tasks."""
        scheduler.add_task(mock_task)
        
        await scheduler.start()
        
        # Let it run for a short time
        await asyncio.sleep(0.1)
        
        await scheduler.stop()
        
        # Check that task was executed
        assert mock_task.execution_count > 0
        assert len(mock_task.execution_times) > 0
    
    def test_get_task_stats_nonexistent(self, scheduler):
        """Test getting stats for nonexistent task."""
        stats = scheduler.get_task_stats("nonexistent")
        assert stats is None
    
    def test_get_task_stats_existing(self, scheduler, mock_task):
        """Test getting stats for existing task."""
        scheduler.add_task(mock_task)
        
        stats = scheduler.get_task_stats("test_task")
        
        assert stats is not None
        assert stats['name'] == "test_task"
        assert stats['frequency_hz'] == 100.0
        assert stats['priority'] == "MEDIUM"
        assert stats['enabled'] is True
        assert stats['execution_count'] == 0
        assert stats['missed_deadlines'] == 0
    
    def test_get_all_stats(self, scheduler, mock_task):
        """Test getting stats for all tasks."""
        scheduler.add_task(mock_task)
        
        all_stats = scheduler.get_all_stats()
        
        assert "test_task" in all_stats
        assert all_stats["test_task"]["name"] == "test_task"
    
    def test_get_global_stats(self, scheduler):
        """Test getting global scheduler stats."""
        global_stats = scheduler.get_global_stats()
        
        assert 'runtime_s' in global_stats
        assert 'cycle_count' in global_stats
        assert 'total_missed_deadlines' in global_stats
        assert 'total_overruns' in global_stats
        assert 'task_count' in global_stats
        assert 'enabled_task_count' in global_stats
    
    @pytest.mark.asyncio
    async def test_scheduler_context_manager(self):
        """Test scheduler context manager."""
        async with quartic_scheduler_context() as scheduler:
            assert scheduler.running is True
            assert scheduler.scheduler_task is not None
        
        assert scheduler.running is False


class TestTaskFactories:
    """Test task factory functions."""
    
    def test_create_control_task(self):
        """Test control task creation."""
        def control_func():
            pass
        
        task = create_control_task(control_func, frequency_hz=400.0, name="test_control")
        
        assert task.name == "test_control"
        assert task.func == control_func
        assert task.frequency_hz == 400.0
        assert task.priority == TaskPriority.HIGH
        assert task.deadline_ms == 2.0  # 80% of 2.5ms period
    
    def test_create_planning_task(self):
        """Test planning task creation."""
        def planning_func():
            pass
        
        task = create_planning_task(planning_func, frequency_hz=50.0, name="test_planning")
        
        assert task.name == "test_planning"
        assert task.func == planning_func
        assert task.frequency_hz == 50.0
        assert task.priority == TaskPriority.MEDIUM
        assert task.deadline_ms == 18.0  # 90% of 20ms period
    
    def test_create_safety_task(self):
        """Test safety task creation."""
        def safety_func():
            pass
        
        task = create_safety_task(safety_func, frequency_hz=100.0, name="test_safety")
        
        assert task.name == "test_safety"
        assert task.func == safety_func
        assert task.frequency_hz == 100.0
        assert task.priority == TaskPriority.CRITICAL
        assert task.deadline_ms == 7.0  # 70% of 10ms period


class TestJitterAnalysis:
    """Test jitter analysis functionality."""
    
    @pytest.mark.asyncio
    async def test_jitter_analysis_with_monitoring(self):
        """Test jitter analysis with monitoring enabled."""
        async with quartic_scheduler_context(enable_monitoring=True) as scheduler:
            def test_func():
                time.sleep(0.001)  # 1ms work
            
            task = QuarticTask(
                name="jitter_test",
                func=test_func,
                frequency_hz=100.0
            )
            
            scheduler.add_task(task)
            
            # Run for a short time to collect data
            await asyncio.sleep(0.2)
            
            # Check that jitter analysis was performed
            stats = scheduler.get_task_stats("jitter_test")
            assert stats is not None
            
            if 'jitter_analysis' in stats:
                jitter_data = stats['jitter_analysis']
                assert 'mean_jitter_ms' in jitter_data
                assert 'std_jitter_ms' in jitter_data
                assert 'max_jitter_ms' in jitter_data
                assert 'min_jitter_ms' in jitter_data
                assert 'samples_count' in jitter_data
    
    def test_generate_jitter_histogram_no_data(self):
        """Test jitter histogram generation with no data."""
        scheduler = QuarticScheduler(enable_monitoring=False)
        
        # Should not raise an error when no data is available
        scheduler.generate_jitter_histogram()
    
    @pytest.mark.asyncio
    async def test_generate_jitter_histogram_with_data(self):
        """Test jitter histogram generation with data."""
        async with quartic_scheduler_context(enable_monitoring=True) as scheduler:
            def test_func():
                time.sleep(0.001)
            
            task = QuarticTask(
                name="histogram_test",
                func=test_func,
                frequency_hz=100.0
            )
            
            scheduler.add_task(task)
            
            # Run for a short time to collect data
            await asyncio.sleep(0.1)
            
            # Generate histogram (should not raise an error)
            scheduler.generate_jitter_histogram(task_name="histogram_test")


class TestPerformanceValidation:
    """Test performance validation and accuracy."""
    
    @pytest.mark.asyncio
    async def test_frequency_accuracy(self):
        """Test that the scheduler maintains accurate frequency."""
        async with quartic_scheduler_context() as scheduler:
            execution_count = 0
            
            def counting_func():
                nonlocal execution_count
                execution_count += 1
            
            task = QuarticTask(
                name="frequency_test",
                func=counting_func,
                frequency_hz=50.0  # 50Hz = 20ms period
            )
            
            scheduler.add_task(task)
            
            # Run for 1 second
            await asyncio.sleep(1.0)
            
            # Check frequency accuracy (allow 10% tolerance)
            expected_executions = 50
            actual_executions = execution_count
            frequency_error = abs(actual_executions - expected_executions) / expected_executions
            
            assert frequency_error < 0.1, f"Frequency error {frequency_error:.2%} exceeds 10% tolerance"
            assert actual_executions > 0, "No executions occurred"
    
    @pytest.mark.asyncio
    async def test_deadline_monitoring(self):
        """Test deadline monitoring and violation detection."""
        async with quartic_scheduler_context() as scheduler:
            def slow_func():
                time.sleep(0.015)  # 15ms execution time
            
            task = QuarticTask(
                name="deadline_test",
                func=slow_func,
                frequency_hz=100.0,
                deadline_ms=10.0  # 10ms deadline
            )
            
            scheduler.add_task(task)
            
            # Run for a short time
            await asyncio.sleep(0.1)
            
            # Check that deadline violations were detected
            stats = scheduler.get_task_stats("deadline_test")
            assert stats is not None
            assert stats['missed_deadlines'] > 0
            assert scheduler.total_missed_deadlines > 0
    
    @pytest.mark.asyncio
    async def test_multiple_tasks_coordination(self):
        """Test coordination between multiple tasks."""
        async with quartic_scheduler_context() as scheduler:
            control_count = 0
            planning_count = 0
            
            def control_func():
                nonlocal control_count
                control_count += 1
            
            def planning_func():
                nonlocal planning_count
                planning_count += 1
            
            control_task = QuarticTask(
                name="control",
                func=control_func,
                frequency_hz=100.0,
                priority=TaskPriority.HIGH
            )
            
            planning_task = QuarticTask(
                name="planning",
                func=planning_func,
                frequency_hz=20.0,
                priority=TaskPriority.MEDIUM
            )
            
            scheduler.add_task(control_task)
            scheduler.add_task(planning_task)
            
            # Run for 1 second
            await asyncio.sleep(1.0)
            
            # Check that both tasks executed
            assert control_count > 0, "Control task did not execute"
            assert planning_count > 0, "Planning task did not execute"
            
            # Control should execute more frequently than planning
            assert control_count > planning_count, "Control task should execute more frequently than planning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 