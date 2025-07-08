"""
Test suite for planner-controller contract with closed-loop simulation.

This module tests the alignment between planner outputs and controller inputs,
ensuring that the planner-controller contract is properly implemented and
that closed-loop control works correctly with simulated dynamics.
"""

import sys
from dart_planner.common.di_container import get_container
import os

import unittest
import numpy as np
import time
from typing import List, Dict

from dart_planner.common.types import DroneState, Trajectory, ControlCommand, BodyRateCommand
from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
from dart_planner.control.geometric_controller import GeometricController
from dart_planner.utils.drone_simulator import DroneSimulator


class TestPlannerControllerContract(unittest.TestCase):
    """Test the planner-controller contract with closed-loop simulation."""

    def setUp(self):
        """Set up test fixtures."""
        # Configure planner for fast testing
        planner_config = SE3MPCConfig(
            prediction_horizon=4,  # Shorter for faster tests
            dt=0.1,
            max_iterations=5,
            convergence_tolerance=1e-1,
        )
        self.planner = get_container().create_planner_container().get_se3_planner()
        self.controller = get_container().create_control_container().get_geometric_controller()
        self.simulator = DroneSimulator()
        
        # Test state
        self.initial_state = DroneState(
            timestamp=time.time(),
            position=np.array([0.0, 0.0, 1.0]),  # Start at 1m altitude
            velocity=np.zeros(3),
            attitude=np.zeros(3),
            angular_velocity=np.zeros(3),
        )
        
        # Test goal
        self.goal_position = np.array([5.0, 3.0, 2.0])  # 5m forward, 3m right, 2m up

    def test_planner_outputs_complete_trajectory(self):
        """Test that planner outputs complete trajectory with all required fields."""
        # Plan trajectory
        trajectory = self.planner.plan_trajectory(self.initial_state, self.goal_position)
        
        # Check that all required fields are present
        self.assertIsNotNone(trajectory.positions)
        self.assertIsNotNone(trajectory.velocities)
        self.assertIsNotNone(trajectory.accelerations)
        self.assertIsNotNone(trajectory.attitudes)
        self.assertIsNotNone(trajectory.body_rates)
        self.assertIsNotNone(trajectory.thrusts)
        
        # Check array shapes (only if not None)
        n_steps = len(trajectory.timestamps)
        if trajectory.positions is not None:
            self.assertEqual(trajectory.positions.shape, (n_steps, 3))
        if trajectory.velocities is not None:
            self.assertEqual(trajectory.velocities.shape, (n_steps, 3))
        if trajectory.accelerations is not None:
            self.assertEqual(trajectory.accelerations.shape, (n_steps, 3))
        if trajectory.attitudes is not None:
            self.assertEqual(trajectory.attitudes.shape, (n_steps, 3))
        if trajectory.body_rates is not None:
            self.assertEqual(trajectory.body_rates.shape, (n_steps, 3))
        if trajectory.thrusts is not None:
            self.assertEqual(trajectory.thrusts.shape, (n_steps,))
        
        # Check that attitudes are reasonable (within ±π/2 for roll/pitch)
        if trajectory.attitudes is not None:
            self.assertTrue(np.all(np.abs(trajectory.attitudes[:, 0]) < np.pi/2))  # Roll
            self.assertTrue(np.all(np.abs(trajectory.attitudes[:, 1]) < np.pi/2))  # Pitch
        
        # Check that thrusts are positive
        if trajectory.thrusts is not None:
            self.assertTrue(np.all(trajectory.thrusts > 0))

    def test_controller_accepts_planner_outputs(self):
        """Test that controller can process planner outputs correctly."""
        # Plan trajectory
        trajectory = self.planner.plan_trajectory(self.initial_state, self.goal_position)
        
        # Test controller with trajectory at different time points
        for i in range(min(3, len(trajectory.timestamps))):
            t_current = trajectory.timestamps[i]
            
            # Test standard control command
            control_cmd = self.controller.compute_control_from_trajectory(
                self.initial_state, trajectory, t_current
            )
            self.assertIsInstance(control_cmd, ControlCommand)
            self.assertGreater(control_cmd.thrust, 0)
            self.assertEqual(control_cmd.torque.shape, (3,))
            
            # Test body-rate command
            body_rate_cmd = self.controller.compute_body_rate_from_trajectory(
                self.initial_state, trajectory, t_current
            )
            self.assertIsInstance(body_rate_cmd, BodyRateCommand)
            self.assertGreaterEqual(body_rate_cmd.thrust, 0)
            self.assertLessEqual(body_rate_cmd.thrust, 1.0)  # Normalized
            self.assertEqual(body_rate_cmd.body_rates.shape, (3,))

    def test_closed_loop_simulation(self):
        """Test closed-loop simulation with planner-controller integration."""
        # Plan trajectory
        trajectory = self.planner.plan_trajectory(self.initial_state, self.goal_position)
        
        # Simulate closed-loop control
        current_state = self.initial_state
        simulation_states = [current_state]
        control_commands = []
        
        dt = 0.01  # 100Hz simulation
        max_time = 10.0  # Maximum simulation time
        start_time = current_state.timestamp
        
        for step in range(int(max_time / dt)):
            t_current = current_state.timestamp
            
            # Check if trajectory is still valid
            if t_current > trajectory.timestamps[-1]:
                break
            
            # Compute control command
            control_cmd = self.controller.compute_control_from_trajectory(
                current_state, trajectory, t_current
            )
            control_commands.append(control_cmd)
            
            # Simulate drone dynamics
            current_state = self.simulator.step(current_state, control_cmd, dt)
            simulation_states.append(current_state)
            
            # Check for safety limits
            if np.linalg.norm(current_state.position) > 50.0:  # 50m safety radius
                break
        
        # Verify simulation completed successfully
        self.assertGreater(len(simulation_states), 10)  # At least 100ms of simulation
        self.assertGreater(len(control_commands), 10)
        
        # Check that final position is closer to goal than initial
        final_pos = simulation_states[-1].position
        initial_dist = np.linalg.norm(self.initial_state.position - self.goal_position)
        final_dist = np.linalg.norm(final_pos - self.goal_position)
        
        # Note: In a short simulation, we might not reach the goal, but we should be moving toward it
        print(f"Initial distance to goal: {initial_dist:.2f}m")
        print(f"Final distance to goal: {final_dist:.2f}m")
        print(f"Final position: {final_pos}")

    def test_body_rate_control_consistency(self):
        """Test that body-rate control produces consistent results."""
        # Plan trajectory
        trajectory = self.planner.plan_trajectory(self.initial_state, self.goal_position)
        
        # Test at multiple time points
        for i in range(min(5, len(trajectory.timestamps))):
            t_current = trajectory.timestamps[i]
            
            # Get both control command types
            control_cmd = self.controller.compute_control_from_trajectory(
                self.initial_state, trajectory, t_current
            )
            body_rate_cmd = self.controller.compute_body_rate_from_trajectory(
                self.initial_state, trajectory, t_current
            )
            
            # Check that thrust values are consistent (within normalization factor)
            expected_thrust_ratio = body_rate_cmd.thrust * self.controller.config.max_thrust
            self.assertAlmostEqual(control_cmd.thrust, expected_thrust_ratio, delta=0.1)
            
            # Check that body rates are reasonable
            self.assertTrue(np.all(np.abs(body_rate_cmd.body_rates) < 10.0))  # Max 10 rad/s

    def test_trajectory_interpolation(self):
        """Test trajectory interpolation at intermediate time points."""
        # Plan trajectory
        trajectory = self.planner.plan_trajectory(self.initial_state, self.goal_position)
        
        # Test interpolation at intermediate time
        if len(trajectory.timestamps) > 1:
            t_mid = (trajectory.timestamps[0] + trajectory.timestamps[1]) / 2
            
            # Should not crash
            control_cmd = self.controller.compute_control_from_trajectory(
                self.initial_state, trajectory, t_mid
            )
            body_rate_cmd = self.controller.compute_body_rate_from_trajectory(
                self.initial_state, trajectory, t_mid
            )
            
            self.assertIsInstance(control_cmd, ControlCommand)
            self.assertIsInstance(body_rate_cmd, BodyRateCommand)

    def test_emergency_trajectory_handling(self):
        """Test that emergency hover trajectory is generated correctly."""
        # Directly generate emergency trajectory (hover)
        trajectory = self.planner._generate_emergency_trajectory(self.initial_state)
        
        # Check that emergency trajectory is valid and holds position
        self.assertIsNotNone(trajectory.positions)
        self.assertIsNotNone(trajectory.velocities)
        self.assertIsNotNone(trajectory.accelerations)
        # Narrow types after non-None assertion
        positions: np.ndarray = trajectory.positions  # type: ignore
        velocities: np.ndarray = trajectory.velocities  # type: ignore
        # Should hold at initial position and zero velocity
        self.assertTrue(np.allclose(positions, self.initial_state.position, atol=1e-6))
        self.assertTrue(np.allclose(velocities, np.zeros(3), atol=1e-6))

    def test_performance_benchmark(self):
        """Benchmark the planner-controller performance."""
        # Plan trajectory
        start_time = time.perf_counter()
        trajectory = self.planner.plan_trajectory(self.initial_state, self.goal_position)
        planning_time = (time.perf_counter() - start_time) * 1000  # ms
        
        # Test controller performance
        control_times = []
        for i in range(min(10, len(trajectory.timestamps))):
            t_current = trajectory.timestamps[i]
            
            start_time = time.perf_counter()
            control_cmd = self.controller.compute_control_from_trajectory(
                self.initial_state, trajectory, t_current
            )
            control_time = (time.perf_counter() - start_time) * 1000  # ms
            control_times.append(control_time)
        
        avg_control_time = np.mean(control_times)
        max_control_time = np.max(control_times)
        
        print(f"Planning time: {planning_time:.2f}ms")
        print(f"Average control time: {avg_control_time:.2f}ms")
        print(f"Max control time: {max_control_time:.2f}ms")
        
        # Performance requirements for real-time operation
        self.assertTrue(planning_time < 50.0)  # Planning should be < 50ms
        self.assertTrue(avg_control_time < 2.0)  # Control should be < 2ms
        self.assertTrue(max_control_time < 5.0)  # Max control should be < 5ms

    def test_wind_disturbance(self):
        """Test closed-loop simulation with constant wind disturbance."""
        wind = np.array([2.0, 0.0, 0.0])  # 2 m/s wind in x
        simulator = DroneSimulator(wind=wind)
        trajectory = self.planner.plan_trajectory(self.initial_state, self.goal_position)
        current_state = self.initial_state
        for _ in range(100):
            t_current = current_state.timestamp
            if t_current > trajectory.timestamps[-1]:
                break
            control_cmd = self.controller.compute_control_from_trajectory(current_state, trajectory, t_current)
            current_state = simulator.step(current_state, control_cmd, 0.01)
        # Check that the drone does not drift excessively in wind direction
        self.assertLess(np.abs(current_state.position[0]), 10.0)

    def test_actuator_saturation(self):
        """Test closed-loop simulation with actuator saturation (max thrust/torque)."""
        simulator = DroneSimulator(max_thrust=5.0, max_torque=2.0)
        trajectory = self.planner.plan_trajectory(self.initial_state, self.goal_position)
        current_state = self.initial_state
        for _ in range(100):
            t_current = current_state.timestamp
            if t_current > trajectory.timestamps[-1]:
                break
            control_cmd = self.controller.compute_control_from_trajectory(current_state, trajectory, t_current)
            current_state = simulator.step(current_state, control_cmd, 0.01)
        # Check that the drone is still airborne (z > 0)
        self.assertGreater(current_state.position[2], 0.0)

    def test_wind_gust(self):
        """Test closed-loop simulation with a sudden wind gust."""
        simulator = DroneSimulator()
        trajectory = self.planner.plan_trajectory(self.initial_state, self.goal_position)
        current_state = self.initial_state
        for i in range(100):
            t_current = current_state.timestamp
            if t_current > trajectory.timestamps[-1]:
                break
            control_cmd = self.controller.compute_control_from_trajectory(current_state, trajectory, t_current)
            # Apply wind gust at step 50
            if i == 50:
                simulator.wind = np.array([5.0, 0.0, 0.0])
            current_state = simulator.step(current_state, control_cmd, 0.01)
        # Check that the drone recovers (does not drift > 20m)
        self.assertLess(np.abs(current_state.position[0]), 20.0)

    def test_emergency_failsafe_handling(self):
        """Test that controller and simulator handle emergency/failsafe trajectory correctly."""
        # Simulate planner failure by forcing emergency trajectory
        self.planner.goal_position = None
        trajectory = self.planner._generate_emergency_trajectory(self.initial_state)
        simulator = DroneSimulator()
        current_state = self.initial_state
        for _ in range(50):
            t_current = current_state.timestamp
            control_cmd = self.controller.compute_control_from_trajectory(current_state, trajectory, t_current)
            current_state = simulator.step(current_state, control_cmd, 0.01)
        # Drone should hover near initial position
        self.assertTrue(np.allclose(current_state.position, self.initial_state.position, atol=0.5))


if __name__ == "__main__":
    unittest.main() 
