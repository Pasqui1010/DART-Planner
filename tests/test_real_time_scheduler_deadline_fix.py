"""
Regression tests for real-time scheduler deadline accounting fix.

This test suite verifies that the missed deadline counting bug has been fixed
and that global statistics are calculated correctly.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from dart_planner.common.real_time_scheduler import RealTimeScheduler
from dart_planner.common.real_time_config import (
    RealTimeTask, TaskType, TaskPriority, SchedulerConfig
)


class TestDeadlineAccountingFix:
    """Test cases for the deadline accounting fix."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a scheduler instance for testing."""
        config = SchedulerConfig(
            enable_rt_os=False,  # Disable RT OS for testing
            monitoring_enabled=False  # Disable monitoring for cleaner tests
        )
        return RealTimeScheduler(config)
    
    @pytest.fixture
    def slow_task_func(self):
        """Create a task function that simulates slow execution."""
        def slow_task():
            time.sleep(0.1)  # Simulate 100ms execution time
        return slow_task
    
    @pytest.fixture
    def fast_task_func(self):
        """Create a task function that executes quickly."""
        def fast_task():
            pass  # No delay
        return fast_task
    
    def test_initial_stats_are_zero(self, scheduler):
        """Test that initial statistics are properly zeroed."""
        assert scheduler.global_stats['missed_deadlines'] == 0
        assert len(scheduler.previous_stats) == 0
        assert len(scheduler.timing_stats) == 0
    
    def test_add_task_initializes_previous_stats(self, scheduler, fast_task_func):
        """Test that adding a task initializes previous_stats correctly."""
        task = RealTimeTask(
            name="test_task",
            func=fast_task_func,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,  # 20Hz
            deadline_ms=25.0  # 25ms deadline
        )
        
        scheduler.add_task(task)
        
        assert "test_task" in scheduler.previous_stats
        assert scheduler.previous_stats["test_task"].missed_deadlines == 0
        assert scheduler.previous_stats["test_task"].total_executions == 0
    
    def test_remove_task_cleans_up_previous_stats(self, scheduler, fast_task_func):
        """Test that removing a task cleans up previous_stats."""
        task = RealTimeTask(
            name="test_task",
            func=fast_task_func,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,
            deadline_ms=25.0
        )
        
        scheduler.add_task(task)
        assert "test_task" in scheduler.previous_stats
        
        scheduler.remove_task("test_task")
        assert "test_task" not in scheduler.previous_stats
    
    def test_single_deadline_violation_accounting(self, scheduler, slow_task_func):
        """Test that a single deadline violation is counted correctly."""
        task = RealTimeTask(
            name="slow_task",
            func=slow_task_func,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,  # 20Hz
            deadline_ms=25.0  # 25ms deadline (will be violated by 100ms execution)
        )
        
        scheduler.add_task(task)
        
        # Simulate task execution that violates deadline
        current_time = time.perf_counter()
        execution_time = 0.1  # 100ms execution time
        
        # Update stats (this should trigger deadline violation detection)
        scheduler._update_task_stats(task, execution_time, current_time)
        
        # Check that global stats only incremented by 1
        assert scheduler.global_stats['missed_deadlines'] == 1
        assert scheduler.timing_stats["slow_task"].missed_deadlines == 1
    
    def test_multiple_deadline_violations_accounting(self, scheduler, slow_task_func):
        """Test that multiple deadline violations are counted correctly without double-counting."""
        task = RealTimeTask(
            name="slow_task",
            func=slow_task_func,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,
            deadline_ms=25.0
        )
        
        scheduler.add_task(task)
        
        # Simulate multiple executions with deadline violations
        for i in range(3):
            current_time = time.perf_counter()
            execution_time = 0.1  # 100ms execution time
            
            # Manually increment task's missed deadlines to simulate violation
            task.missed_deadlines = i + 1
            
            # Update stats
            scheduler._update_task_stats(task, execution_time, current_time)
        
        # Check that global stats equals the final missed deadline count
        assert scheduler.global_stats['missed_deadlines'] == 3
        assert scheduler.timing_stats["slow_task"].missed_deadlines == 3
    
    def test_no_double_counting_on_repeated_updates(self, scheduler, fast_task_func):
        """Test that repeated updates don't double-count missed deadlines."""
        task = RealTimeTask(
            name="test_task",
            func=fast_task_func,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,
            deadline_ms=25.0
        )
        
        scheduler.add_task(task)
        
        # Set a fixed number of missed deadlines
        task.missed_deadlines = 5
        
        # Update stats multiple times with the same missed deadline count
        for _ in range(10):
            current_time = time.perf_counter()
            execution_time = 0.001  # 1ms execution time
            
            scheduler._update_task_stats(task, execution_time, current_time)
        
        # Global stats should only reflect the actual missed deadlines (5), not 5 * 10
        assert scheduler.global_stats['missed_deadlines'] == 5
        assert scheduler.timing_stats["test_task"].missed_deadlines == 5
    
    def test_deadline_violation_handling_does_not_double_count(self, scheduler, slow_task_func):
        """Test that _handle_deadline_violation doesn't double-count with _update_task_stats."""
        task = RealTimeTask(
            name="slow_task",
            func=slow_task_func,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,
            deadline_ms=25.0
        )
        
        scheduler.add_task(task)
        
        # Simulate deadline violation
        current_time = time.perf_counter()
        execution_time = 0.1  # 100ms execution time
        
        # Handle deadline violation
        scheduler._handle_deadline_violation(task, current_time)
        
        # Update stats
        scheduler._update_task_stats(task, execution_time, current_time)
        
        # Should only count 1 missed deadline, not 2
        assert scheduler.global_stats['missed_deadlines'] == 1
    
    @pytest.mark.asyncio
    async def test_integration_with_real_task_execution(self, scheduler):
        """Test the fix with actual task execution."""
        execution_count = 0
        missed_deadlines = 0
        
        def test_task():
            nonlocal execution_count
            execution_count += 1
            
            # Simulate slow execution every 3rd time
            if execution_count % 3 == 0:
                time.sleep(0.1)  # 100ms delay
                nonlocal missed_deadlines
                missed_deadlines += 1
        
        task = RealTimeTask(
            name="integration_test_task",
            func=test_task,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,  # 20Hz
            deadline_ms=25.0  # 25ms deadline
        )
        
        scheduler.add_task(task)
        
        # Run the task multiple times
        for _ in range(9):  # 9 executions, should have 3 missed deadlines
            current_time = time.perf_counter()
            
            # Execute task
            task.func()
            
            # Simulate deadline violation detection
            if execution_count % 3 == 0:
                task.missed_deadlines += 1
            
            # Update stats
            execution_time = 0.1 if execution_count % 3 == 0 else 0.001
            scheduler._update_task_stats(task, execution_time, current_time)
        
        # Verify correct counting
        expected_missed_deadlines = 3  # Every 3rd execution
        assert scheduler.global_stats['missed_deadlines'] == expected_missed_deadlines
        assert scheduler.timing_stats["integration_test_task"].missed_deadlines == expected_missed_deadlines
    
    def test_edge_case_zero_missed_deadlines(self, scheduler, fast_task_func):
        """Test edge case where task has no missed deadlines."""
        task = RealTimeTask(
            name="perfect_task",
            func=fast_task_func,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,
            deadline_ms=25.0
        )
        
        scheduler.add_task(task)
        
        # Ensure task has no missed deadlines
        task.missed_deadlines = 0
        
        # Update stats multiple times
        for _ in range(5):
            current_time = time.perf_counter()
            execution_time = 0.001
            
            scheduler._update_task_stats(task, execution_time, current_time)
        
        # Global stats should remain at 0
        assert scheduler.global_stats['missed_deadlines'] == 0
        assert scheduler.timing_stats["perfect_task"].missed_deadlines == 0
    
    def test_multiple_tasks_deadline_accounting(self, scheduler, slow_task_func, fast_task_func):
        """Test deadline accounting with multiple tasks."""
        # Create two tasks
        slow_task = RealTimeTask(
            name="slow_task",
            func=slow_task_func,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,
            deadline_ms=25.0
        )
        
        fast_task = RealTimeTask(
            name="fast_task",
            func=fast_task_func,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,
            deadline_ms=25.0
        )
        
        scheduler.add_task(slow_task)
        scheduler.add_task(fast_task)
        
        # Simulate executions
        slow_task.missed_deadlines = 2
        fast_task.missed_deadlines = 1
        
        current_time = time.perf_counter()
        scheduler._update_task_stats(slow_task, 0.1, current_time)
        scheduler._update_task_stats(fast_task, 0.001, current_time)
        
        # Global stats should be sum of both tasks
        assert scheduler.global_stats['missed_deadlines'] == 3
        assert scheduler.timing_stats["slow_task"].missed_deadlines == 2
        assert scheduler.timing_stats["fast_task"].missed_deadlines == 1


class TestDeadlineAccountingRegression:
    """Regression tests to ensure the fix doesn't break existing functionality."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a scheduler instance for testing."""
        config = SchedulerConfig(
            enable_rt_os=False,
            monitoring_enabled=False
        )
        return RealTimeScheduler(config)
    
    def test_original_bug_scenario(self, scheduler):
        """Test the exact scenario that would have caused the original bug."""
        def dummy_task():
            pass
        
        task = RealTimeTask(
            name="bug_test_task",
            func=dummy_task,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,
            deadline_ms=25.0
        )
        
        scheduler.add_task(task)
        
        # Simulate the original bug scenario
        task.missed_deadlines = 5
        
        # Multiple updates with the same missed deadline count
        for _ in range(3):
            current_time = time.perf_counter()
            execution_time = 0.001
            
            # This would have caused the bug: adding 5 each time
            scheduler._update_task_stats(task, execution_time, current_time)
        
        # With the fix: should only count 5 total, not 15
        assert scheduler.global_stats['missed_deadlines'] == 5, \
            f"Expected 5 missed deadlines, got {scheduler.global_stats['missed_deadlines']}"
    
    def test_backward_compatibility(self, scheduler):
        """Test that the fix maintains backward compatibility."""
        def dummy_task():
            pass
        
        task = RealTimeTask(
            name="compat_test_task",
            func=dummy_task,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=50.0,
            deadline_ms=25.0
        )
        
        scheduler.add_task(task)
        
        # Test that basic functionality still works
        assert task.name in scheduler.tasks
        assert task.name in scheduler.timing_stats
        assert task.name in scheduler.previous_stats
        
        # Test that stats are accessible
        stats = scheduler.get_task_stats(task.name)
        assert stats is not None
        assert stats.task_name == task.name
        
        # Test that global stats are accessible
        global_stats = scheduler.get_global_stats()
        assert 'missed_deadlines' in global_stats
        assert global_stats['missed_deadlines'] == 0 