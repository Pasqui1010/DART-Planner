#!/usr/bin/env python3
"""
Unit Tests for DART-Planner SITL Components

These tests validate individual components in isolation before integration testing.
Tests are designed to run quickly and catch regressions in core functionality.
"""

import sys
from dart_planner.common.di_container_v2 import get_container
import time
import unittest
from pathlib import Path

import numpy as np
import pytest

# Add src to path for imports

from dart_planner.common.types import ControlCommand, DroneState, Trajectory
from dart_planner.control.geometric_controller import GeometricController, GeometricControllerConfig
from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig


class TestSE3MPCPlanner(unittest.TestCase):
    """Unit tests for SE(3) MPC Planner"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.config = SE3MPCConfig()
        self.config.max_iterations = 5  # Reduced for faster tests
        self.planner = get_container().create_planner_container().get_se3_planner()
        
        # Standard test state
        self.test_state = DroneState(
            timestamp=time.time(),
            position=np.array([0.0, 0.0, -5.0]),
            velocity=np.array([0.0, 0.0, 0.0]),
            attitude=np.array([1.0, 0.0, 0.0, 0.0]),
            angular_velocity=np.array([0.0, 0.0, 0.0])
        )
    
    def test_planner_initialization(self):
        """Test planner initializes correctly"""
        self.assertIsNotNone(self.planner)
        self.assertEqual(self.planner.config.prediction_horizon, 6)
        self.assertEqual(self.planner.mass, 1.5)
        self.assertAlmostEqual(self.planner.hover_thrust, 1.5 * 9.81, places=2)
    
    def test_goal_setting(self):
        """Test goal position setting"""
        goal = np.array([10.0, 5.0, -8.0])
        self.planner.set_goal(goal)
        np.testing.assert_array_equal(self.planner.goal_position, goal)
    
    def test_obstacle_management(self):
        """Test obstacle addition and clearing"""
        # Add obstacle
        center = np.array([5.0, 0.0, -5.0])
        radius = 2.0
        self.planner.add_obstacle(center, radius)
        self.assertEqual(len(self.planner.obstacles), 1)
        
        # Clear obstacles
        self.planner.clear_obstacles()
        self.assertEqual(len(self.planner.obstacles), 0)
    
    def test_basic_trajectory_planning(self):
        """Test basic trajectory planning functionality"""
        goal = np.array([5.0, 0.0, -5.0])
        
        start_time = time.perf_counter()
        trajectory = self.planner.plan_trajectory(self.test_state, goal)
        planning_time = (time.perf_counter() - start_time) * 1000  # ms
        
        # Verify trajectory structure
        self.assertIsInstance(trajectory, Trajectory)
        self.assertGreater(len(trajectory.positions), 0)
        self.assertGreater(len(trajectory.velocities), 0)
        self.assertGreater(len(trajectory.accelerations), 0)
        
        # Verify planning time is reasonable
        self.assertLess(planning_time, 100.0)  # Should be under 100ms
        
        # Verify trajectory starts at current position
        np.testing.assert_array_almost_equal(
            trajectory.positions[0], self.test_state.position, decimal=1
        )
    
    def test_planning_performance_target(self):
        """Test planning meets performance targets"""
        goal = np.array([10.0, 10.0, -10.0])
        
        # Test multiple planning iterations
        planning_times = []
        for _ in range(5):
            start_time = time.perf_counter()
            trajectory = self.planner.plan_trajectory(self.test_state, goal)
            planning_time = (time.perf_counter() - start_time) * 1000  # ms
            planning_times.append(planning_time)
        
        avg_planning_time = np.mean(planning_times)
        max_planning_time = np.max(planning_times)
        
        # Performance assertions
        self.assertLess(avg_planning_time, 50.0, "Average planning time exceeds 50ms")
        self.assertLess(max_planning_time, 100.0, "Maximum planning time exceeds 100ms")
    
    def test_emergency_trajectory_generation(self):
        """Test emergency trajectory generation"""
        # This should not raise an exception
        emergency_traj = self.planner._generate_emergency_trajectory(self.test_state)
        
        self.assertIsInstance(emergency_traj, Trajectory)
        self.assertGreater(len(emergency_traj.positions), 0)
        
        # Emergency trajectory should maintain current position
        np.testing.assert_array_almost_equal(
            emergency_traj.positions[0], self.test_state.position, decimal=1
        )
    
    def test_performance_stats(self):
        """Test performance statistics tracking"""
        # Run a few planning iterations
        goal = np.array([5.0, 5.0, -5.0])
        for _ in range(3):
            self.planner.plan_trajectory(self.test_state, goal)
        
        stats = self.planner.get_performance_stats()
        
        self.assertIn('total_plans', stats)
        self.assertIn('avg_planning_time_ms', stats)
        self.assertIn('success_rate', stats)
        self.assertEqual(stats['total_plans'], 3)


class TestGeometricController(unittest.TestCase):
    """Unit tests for Geometric Controller"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.config = GeometricControllerConfig()
        self.controller = get_container().create_control_container().get_geometric_controller()
        
        # Standard test state
        self.test_state = DroneState(
            timestamp=time.time(),
            position=np.array([0.0, 0.0, -5.0]),
            velocity=np.array([0.0, 0.0, 0.0]),
            attitude=np.array([1.0, 0.0, 0.0, 0.0]),
            angular_velocity=np.array([0.0, 0.0, 0.0])
        )
    
    def test_controller_initialization(self):
        """Test controller initializes correctly"""
        self.assertIsNotNone(self.controller)
        self.assertEqual(self.controller.config.mass, 1.0)
        self.assertEqual(self.controller.config.gravity, 9.81)
        np.testing.assert_array_equal(self.controller.integral_pos_error, np.zeros(3))
    
    def test_hover_control_command(self):
        """Test control command for hover scenario"""
        # Hover at current position
        desired_pos = self.test_state.position.copy()
        desired_vel = np.array([0.0, 0.0, 0.0])
        desired_acc = np.array([0.0, 0.0, 0.0])
        
        control_cmd = self.controller.compute_control(
            self.test_state, desired_pos, desired_vel, desired_acc
        )
        
        self.assertIsInstance(control_cmd, ControlCommand)
        
        # Thrust should be close to hover thrust
        expected_hover_thrust = self.config.mass * self.config.gravity
        self.assertAlmostEqual(control_cmd.thrust, expected_hover_thrust, delta=2.0)
        
        # Torques should be small for hover
        self.assertLess(np.linalg.norm(control_cmd.torque), 1.0)
    
    def test_position_tracking_control(self):
        """Test control command for position tracking"""
        # Command to move up 2 meters
        desired_pos = self.test_state.position + np.array([0.0, 0.0, 2.0])
        desired_vel = np.array([0.0, 0.0, 1.0])
        desired_acc = np.array([0.0, 0.0, 0.0])
        
        control_cmd = self.controller.compute_control(
            self.test_state, desired_pos, desired_vel, desired_acc
        )
        
        # Thrust should be higher than hover for upward motion
        expected_hover_thrust = self.config.mass * self.config.gravity
        self.assertGreater(control_cmd.thrust, expected_hover_thrust)
        
        # Should be within reasonable limits
        self.assertLess(control_cmd.thrust, self.config.max_thrust)
        self.assertGreater(control_cmd.thrust, self.config.min_thrust)
    
    def test_control_computation_time(self):
        """Test control computation meets timing requirements"""
        desired_pos = np.array([1.0, 1.0, -4.0])
        desired_vel = np.array([0.5, 0.5, 0.0])
        desired_acc = np.array([0.0, 0.0, 0.0])
        
        # Test multiple control computations
        computation_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            control_cmd = self.controller.compute_control(
                self.test_state, desired_pos, desired_vel, desired_acc
            )
            computation_time = (time.perf_counter() - start_time) * 1000  # ms
            computation_times.append(computation_time)
        
        avg_computation_time = np.mean(computation_times)
        max_computation_time = np.max(computation_times)
        
        # Control should be very fast (target: 1kHz = 1ms)
        self.assertLess(avg_computation_time, 5.0, "Average control time exceeds 5ms")
        self.assertLess(max_computation_time, 10.0, "Maximum control time exceeds 10ms")
    
    def test_thrust_limits(self):
        """Test thrust limiting functionality"""
        # Command extreme acceleration
        desired_pos = self.test_state.position + np.array([0.0, 0.0, 100.0])
        desired_vel = np.array([0.0, 0.0, 50.0])
        desired_acc = np.array([0.0, 0.0, 100.0])
        
        control_cmd = self.controller.compute_control(
            self.test_state, desired_pos, desired_vel, desired_acc
        )
        
        # Thrust should be limited
        self.assertLessEqual(control_cmd.thrust, self.config.max_thrust)
        self.assertGreaterEqual(control_cmd.thrust, self.config.min_thrust)
    
    def test_tilt_angle_constraint(self):
        """Test tilt angle constraint enforcement"""
        # Command extreme lateral acceleration
        desired_pos = self.test_state.position + np.array([100.0, 0.0, 0.0])
        desired_vel = np.array([50.0, 0.0, 0.0])
        desired_acc = np.array([100.0, 0.0, 0.0])
        
        control_cmd = self.controller.compute_control(
            self.test_state, desired_pos, desired_vel, desired_acc
        )
        
        # Should not crash and should produce reasonable output
        self.assertIsInstance(control_cmd, ControlCommand)
        self.assertGreater(control_cmd.thrust, 0.0)
        self.assertLess(control_cmd.thrust, self.config.max_thrust)
    
    def test_performance_metrics(self):
        """Test performance metrics collection"""
        # Run a few control iterations
        desired_pos = np.array([2.0, 2.0, -3.0])
        desired_vel = np.array([0.0, 0.0, 0.0])
        desired_acc = np.array([0.0, 0.0, 0.0])
        
        for _ in range(5):
            self.controller.compute_control(
                self.test_state, desired_pos, desired_vel, desired_acc
            )
        
        metrics = self.controller.get_performance_metrics()
        
        self.assertIn('avg_position_error', metrics)
        self.assertIn('avg_velocity_error', metrics)
        self.assertIn('control_count', metrics)
        self.assertEqual(metrics['control_count'], 5)
    
    def test_failsafe_behavior(self):
        """Test failsafe behavior under invalid conditions"""
        # Test with invalid dt
        self.controller.last_time = time.time() + 1.0  # Future time
        
        control_cmd = self.controller.compute_control(
            self.test_state, 
            np.array([0.0, 0.0, -5.0]),
            np.array([0.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 0.0])
        )
        
        # Should return failsafe command
        self.assertIsInstance(control_cmd, ControlCommand)
        self.assertGreater(control_cmd.thrust, 0.0)  # Should maintain some thrust


class TestDroneState(unittest.TestCase):
    """Unit tests for DroneState data structure"""
    
    def test_drone_state_creation(self):
        """Test DroneState creation and basic properties"""
        state = DroneState(
            timestamp=time.time(),
            position=np.array([1.0, 2.0, -3.0]),
            velocity=np.array([0.5, 0.0, -0.1]),
            attitude=np.array([1.0, 0.0, 0.0, 0.0]),
            angular_velocity=np.array([0.0, 0.0, 0.1])
        )
        
        self.assertIsInstance(state, DroneState)
        self.assertEqual(len(state.position), 3)
        self.assertEqual(len(state.velocity), 3)
        self.assertEqual(len(state.attitude), 4)  # Quaternion
        self.assertEqual(len(state.angular_velocity), 3)
    
    def test_drone_state_validation(self):
        """Test DroneState input validation"""
        # Test with valid inputs
        state = DroneState(
            timestamp=time.time(),
            position=np.array([0.0, 0.0, 0.0]),
            velocity=np.array([0.0, 0.0, 0.0]),
            attitude=np.array([1.0, 0.0, 0.0, 0.0]),
            angular_velocity=np.array([0.0, 0.0, 0.0])
        )
        
        # Basic validation - should not raise exceptions
        self.assertIsNotNone(state.position)
        self.assertIsNotNone(state.velocity)
        self.assertIsNotNone(state.attitude)
        self.assertIsNotNone(state.angular_velocity)


class TestTrajectory(unittest.TestCase):
    """Unit tests for Trajectory data structure"""
    
    def test_trajectory_creation(self):
        """Test Trajectory creation"""
        positions = [np.array([i, 0.0, -5.0]) for i in range(5)]
        velocities = [np.array([1.0, 0.0, 0.0]) for _ in range(5)]
        accelerations = [np.array([0.0, 0.0, 0.0]) for _ in range(5)]
        timestamps = [i * 0.1 for i in range(5)]
        
        trajectory = Trajectory(
            positions=positions,
            velocities=velocities,
            accelerations=accelerations,
            timestamps=timestamps
        )
        
        self.assertIsInstance(trajectory, Trajectory)
        self.assertEqual(len(trajectory.positions), 5)
        self.assertEqual(len(trajectory.velocities), 5)
        self.assertEqual(len(trajectory.accelerations), 5)
        self.assertEqual(len(trajectory.timestamps), 5)


# Pytest compatibility
@pytest.mark.unit
class TestSITLComponents:
    """Pytest-style tests for SITL components"""
    
    def test_planner_performance_benchmark(self):
        """Benchmark planner performance"""
        planner = get_container().create_planner_container().get_se3_planner()
        state = DroneState(
            timestamp=time.time(),
            position=np.array([0.0, 0.0, -5.0]),
            velocity=np.array([0.0, 0.0, 0.0]),
            attitude=np.array([1.0, 0.0, 0.0, 0.0]),
            angular_velocity=np.array([0.0, 0.0, 0.0])
        )
        
        # Benchmark planning time
        goal = np.array([10.0, 10.0, -10.0])
        start_time = time.perf_counter()
        trajectory = planner.plan_trajectory(state, goal)
        planning_time = (time.perf_counter() - start_time) * 1000  # ms
        
        # Performance assertion
        assert planning_time < 100.0, f"Planning time {planning_time}ms exceeds 100ms"
        assert len(trajectory.positions) > 0, "Trajectory should have positions"
    
    def test_controller_frequency_benchmark(self):
        """Benchmark controller computation frequency"""
        controller = get_container().create_control_container().get_geometric_controller()
        state = DroneState(
            timestamp=time.time(),
            position=np.array([0.0, 0.0, -5.0]),
            velocity=np.array([0.0, 0.0, 0.0]),
            attitude=np.array([1.0, 0.0, 0.0, 0.0]),
            angular_velocity=np.array([0.0, 0.0, 0.0])
        )
        
        # Test sustained control frequency
        num_iterations = 100
        start_time = time.perf_counter()
        
        for _ in range(num_iterations):
            control_cmd = controller.compute_control(
                state,
                np.array([1.0, 1.0, -4.0]),
                np.array([0.0, 0.0, 0.0]),
                np.array([0.0, 0.0, 0.0])
            )
        
        total_time = time.perf_counter() - start_time
        avg_time_per_iteration = (total_time / num_iterations) * 1000  # ms
        achieved_frequency = 1.0 / (total_time / num_iterations)  # Hz
        
        # Performance assertions
        assert avg_time_per_iteration < 5.0, f"Control computation {avg_time_per_iteration}ms exceeds 5ms"
        assert achieved_frequency > 200.0, f"Control frequency {achieved_frequency}Hz below 200Hz"


if __name__ == '__main__':
    # Run unittest suite
    unittest.main(verbosity=2) 
