"""
Test real-time timing fixes for DART-Planner.

This test verifies:
1. Phase-aligned timing without cumulative drift
2. Jitter compensation with proper clamping to prevent negative sleep times
3. Lazy task registration to prevent CPU burn from empty tasks
"""

import asyncio
import time
import pytest
from unittest.mock import Mock, patch
from collections import deque

from dart_planner.common.real_time_scheduler import (
    RealTimeScheduler, RealTimeTask, TaskPriority, TaskType, RealTimeLoop
)
from dart_planner.common.real_time_integration import RealTimeManager


class TestRealTimeTimingFixes:
    """Test suite for real-time timing fixes."""
    
    def test_phase_aligned_timing_no_drift(self):
        """Test that phase-aligned timing prevents cumulative drift."""
        scheduler = RealTimeScheduler(enable_rt_os=False)
        
        # Create a periodic task with 100ms period
        execution_times = []
        
        def test_task():
            execution_times.append(time.perf_counter())
        
        task = RealTimeTask(
            name="test_task",
            func=test_task,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=100.0,
            deadline_ms=50.0
        )
        
        scheduler.add_task(task)
        
        # Simulate task execution and verify phase alignment
        current_time = time.perf_counter()
        initial_deadline = task.next_deadline
        
        # Execute task multiple times
        for i in range(5):
            # Simulate task execution
            scheduler._update_task_stats(task, 1.0, current_time)
            scheduler._schedule_next_execution(task, current_time)
            
            # Verify phase alignment: next_deadline should be exactly period_ms later
            expected_deadline = initial_deadline + (i + 1) * (task.period_ms / 1000.0)
            assert abs(task.next_deadline - expected_deadline) < 0.001, \
                f"Phase alignment failed at iteration {i}"
    
    def test_jitter_compensation_clamping(self):
        """Test that jitter compensation is properly clamped to prevent negative sleep."""
        scheduler = RealTimeScheduler(enable_rt_os=False)
        
        # Create a task
        task = RealTimeTask(
            name="test_task",
            func=lambda: None,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=100.0,
            deadline_ms=50.0
        )
        
        scheduler.add_task(task)
        
        # Simulate extreme drift scenario
        current_time = time.perf_counter()
        task.last_execution = current_time - 1.0  # 1 second late
        task.next_deadline = current_time + 0.1   # Next deadline in 100ms
        
        # Apply compensation
        scheduler._apply_timing_compensation(task, current_time)
        
        # Verify that next_deadline is not negative and has minimum spacing
        assert task.next_deadline > current_time, "Deadline should not be in the past"
        assert task.next_deadline >= current_time + 0.001, "Minimum spacing should be maintained"
    
    def test_sleep_time_clamping(self):
        """Test that sleep time calculation is properly clamped."""
        scheduler = RealTimeScheduler(enable_rt_os=False)
        
        # Create a task
        task = RealTimeTask(
            name="test_task",
            func=lambda: None,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=100.0,
            deadline_ms=50.0
        )
        
        scheduler.add_task(task)
        
        current_time = time.perf_counter()
        
        # Test normal case
        task.next_deadline = current_time + 0.05  # 50ms in future
        sleep_time = scheduler._calculate_sleep_time(task, current_time)
        assert 0.049 < sleep_time < 0.051, f"Normal sleep time should be ~50ms, got {sleep_time}"
        
        # Test past deadline (should clamp to minimum)
        task.next_deadline = current_time - 0.1  # 100ms in past
        sleep_time = scheduler._calculate_sleep_time(task, current_time)
        assert sleep_time == 0.001, f"Past deadline should clamp to 1ms, got {sleep_time}"
        
        # Test very far future (should cap at period)
        task.next_deadline = current_time + 1.0  # 1 second in future
        sleep_time = scheduler._calculate_sleep_time(task, current_time)
        assert sleep_time == 0.1, f"Far future should cap at period (100ms), got {sleep_time}"
    
    def test_realtime_loop_compensation_clamping(self):
        """Test that RealTimeLoop compensation is properly clamped."""
        loop = RealTimeLoop(frequency_hz=10.0, name="test_loop")
        
        # Test normal compensation
        sleep_time = loop._apply_compensation(0.1)  # 100ms sleep
        assert 0.001 <= sleep_time <= 0.1, f"Normal compensation should be clamped, got {sleep_time}"
        
        # Test extreme compensation (should clamp to minimum)
        sleep_time = loop._apply_compensation(0.001)  # 1ms sleep
        assert sleep_time == 0.001, f"Minimum sleep should be maintained, got {sleep_time}"
        
        # Test negative compensation (should clamp to minimum)
        sleep_time = loop._apply_compensation(-0.1)  # Negative sleep
        assert sleep_time == 0.001, f"Negative sleep should clamp to minimum, got {sleep_time}"
    
    def test_lazy_task_registration(self):
        """Test that tasks are only created when functions are set."""
        # Create a mock config to avoid validation errors
        from unittest.mock import Mock
        mock_config = Mock()
        mock_config.custom_settings = {}
        
        manager = RealTimeManager(config=mock_config)
        
        # Verify tasks start as None
        assert manager.control_task is None, "Control task should start as None"
        assert manager.planning_task is None, "Planning task should start as None"
        assert manager.safety_task is None, "Safety task should start as None"
        
        # Set control function - should create task
        def control_func():
            pass
        
        manager.set_control_function(control_func)
        assert manager.control_task is not None, "Control task should be created"
        assert manager.control_task.func == control_func, "Control function should be set"
        
        # Set planning function - should create task
        def planning_func():
            pass
        
        manager.set_planning_function(planning_func)
        assert manager.planning_task is not None, "Planning task should be created"
        assert manager.planning_task.func == planning_func, "Planning function should be set"
        
        # Set safety function - should create task
        def safety_func():
            pass
        
        manager.set_safety_function(safety_func)
        assert manager.safety_task is not None, "Safety task should be created"
        assert manager.safety_task.func == safety_func, "Safety function should be set"
    
    @pytest.mark.asyncio
    async def test_no_cpu_burn_from_empty_tasks(self):
        """Test that empty tasks don't cause CPU burn."""
        # Create a mock config to avoid validation errors
        from unittest.mock import Mock
        mock_config = Mock()
        mock_config.custom_settings = {}
        
        manager = RealTimeManager(config=mock_config)
        
        # Start manager without setting any functions
        await manager.start()
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Verify no tasks were created
        assert manager.control_task is None, "No control task should be created"
        assert manager.planning_task is None, "No planning task should be created"
        assert manager.safety_task is None, "No safety task should be created"
        
        await manager.stop()
    
    def test_task_initialization_timing(self):
        """Test that task timing is properly initialized."""
        current_time = time.perf_counter()
        
        task = RealTimeTask(
            name="test_task",
            func=lambda: None,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.PERIODIC,
            period_ms=100.0,
            deadline_ms=50.0
        )
        
        # Verify timing initialization
        assert task.last_execution >= current_time - 0.1, "last_execution should be recent"
        assert task.next_deadline >= task.last_execution, "next_deadline should be after last_execution"
        
        # For periodic tasks, next_deadline should be deadline_ms after last_execution initially
        # (this gets corrected to period_ms when added to scheduler)
        expected_deadline = task.last_execution + (task.deadline_ms / 1000.0)
        assert abs(task.next_deadline - expected_deadline) < 0.001, \
            "next_deadline should be properly initialized with deadline"
        
        # Test that scheduler corrects this for periodic tasks
        scheduler = RealTimeScheduler(enable_rt_os=False)
        scheduler.add_task(task)
        
        # After adding to scheduler, next_deadline should be period_ms after last_execution
        expected_deadline = task.last_execution + (task.period_ms / 1000.0)
        assert abs(task.next_deadline - expected_deadline) < 0.001, \
            "next_deadline should be properly phase-aligned after adding to scheduler"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 