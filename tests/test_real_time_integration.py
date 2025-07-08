"""
Tests for real-time integration module.

This module tests the lazy task registration and real-time integration features.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from dart_planner.common.real_time_integration import (
    RealTimeManager, get_real_time_manager,
    integrate_with_controller, integrate_with_planner, integrate_with_safety_system
)
from dart_planner.common.real_time_scheduler import RealTimeScheduler


class TestRealTimeManager:
    """Test RealTimeManager lazy task registration."""
    
    def test_initialization_no_tasks_added(self):
        """Test that no tasks are added to scheduler on initialization."""
        manager = RealTimeManager()
        
        # Verify tasks are None initially
        assert manager.control_task is None
        assert manager.planning_task is None
        assert manager.safety_task is None
        
        # Verify no tasks in scheduler
        assert len(manager.scheduler.tasks) == 0
    
    def test_set_control_function_creates_task(self):
        """Test that setting control function creates and adds task."""
        manager = RealTimeManager()
        
        # Initially no tasks
        assert len(manager.scheduler.tasks) == 0
        
        # Set control function
        mock_control_func = Mock()
        manager.set_control_function(mock_control_func)
        
        # Verify task was created and added
        assert manager.control_task is not None
        assert manager.control_task.func == mock_control_func
        assert "control_loop" in manager.scheduler.tasks
        assert len(manager.scheduler.tasks) == 1
    
    def test_set_planning_function_creates_task(self):
        """Test that setting planning function creates and adds task."""
        manager = RealTimeManager()
        
        # Initially no tasks
        assert len(manager.scheduler.tasks) == 0
        
        # Set planning function
        mock_planning_func = Mock()
        manager.set_planning_function(mock_planning_func)
        
        # Verify task was created and added
        assert manager.planning_task is not None
        assert manager.planning_task.func == mock_planning_func
        assert "planning_loop" in manager.scheduler.tasks
        assert len(manager.scheduler.tasks) == 1
    
    def test_set_safety_function_creates_task(self):
        """Test that setting safety function creates and adds task."""
        manager = RealTimeManager()
        
        # Initially no tasks
        assert len(manager.scheduler.tasks) == 0
        
        # Set safety function
        mock_safety_func = Mock()
        manager.set_safety_function(mock_safety_func)
        
        # Verify task was created and added
        assert manager.safety_task is not None
        assert manager.safety_task.func == mock_safety_func
        assert "safety_monitor" in manager.scheduler.tasks
        assert len(manager.scheduler.tasks) == 1
    
    def test_multiple_functions_add_multiple_tasks(self):
        """Test that setting multiple functions adds multiple tasks."""
        manager = RealTimeManager()
        
        # Set all three functions
        manager.set_control_function(Mock())
        manager.set_planning_function(Mock())
        manager.set_safety_function(Mock())
        
        # Verify all tasks were added
        assert len(manager.scheduler.tasks) == 3
        assert "control_loop" in manager.scheduler.tasks
        assert "planning_loop" in manager.scheduler.tasks
        assert "safety_monitor" in manager.scheduler.tasks
    
    def test_update_existing_task_function(self):
        """Test that updating existing task function doesn't create new task."""
        manager = RealTimeManager()
        
        # Set initial function
        mock_func1 = Mock()
        manager.set_control_function(mock_func1)
        
        initial_task_count = len(manager.scheduler.tasks)
        
        # Update function
        mock_func2 = Mock()
        manager.set_control_function(mock_func2)
        
        # Verify task count didn't change
        assert len(manager.scheduler.tasks) == initial_task_count
        assert manager.control_task is not None
        assert manager.control_task.func == mock_func2
    
    def test_global_manager_singleton(self):
        """Test that get_real_time_manager returns singleton."""
        manager1 = get_real_time_manager()
        manager2 = get_real_time_manager()
        
        assert manager1 is manager2
    
    @pytest.mark.asyncio
    async def test_start_stop_without_tasks(self):
        """Test that manager can start/stop without any tasks."""
        manager = RealTimeManager()
        
        # Should not raise any exceptions
        await manager.start()
        assert manager.running is True
        
        await manager.stop()
        assert manager.running is False
    
    @pytest.mark.asyncio
    async def test_start_stop_with_tasks(self):
        """Test that manager can start/stop with tasks."""
        manager = RealTimeManager()
        
        # Add a task
        manager.set_control_function(Mock())
        
        # Should not raise any exceptions
        await manager.start()
        assert manager.running is True
        
        await manager.stop()
        assert manager.running is False


class TestRealTimeIntegration:
    """Test real-time integration utilities."""
    
    def test_integrate_with_controller(self):
        """Test controller integration."""
        mock_controller = Mock()
        mock_controller.update = Mock()
        
        manager = integrate_with_controller(mock_controller)
        
        # Verify control function was set
        assert manager.control_task is not None
        assert "control_loop" in manager.scheduler.tasks
    
    def test_integrate_with_planner(self):
        """Test planner integration."""
        mock_planner = Mock()
        mock_planner.update = Mock()
        
        manager = integrate_with_planner(mock_planner)
        
        # Verify planning function was set
        assert manager.planning_task is not None
        assert "planning_loop" in manager.scheduler.tasks
    
    def test_integrate_with_safety_system(self):
        """Test safety system integration."""
        mock_safety = Mock()
        mock_safety.check_safety = Mock()
        
        manager = integrate_with_safety_system(mock_safety)
        
        # Verify safety function was set
        assert manager.safety_task is not None
        assert "safety_monitor" in manager.scheduler.tasks 