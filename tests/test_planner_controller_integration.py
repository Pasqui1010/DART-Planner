"""
Simple integration test for planner-controller contract.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
from src.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
from src.control.geometric_controller import GeometricController
from src.common.types import DroneState, BodyRateCommand


def test_planner_controller_integration():
    """Test the complete planner-controller integration."""
    print("Testing planner-controller integration...")
    
    # Initialize components
    planner_config = SE3MPCConfig(
        prediction_horizon=4,
        dt=0.1,
        max_iterations=5,
        convergence_tolerance=1e-1,
    )
    planner = SE3MPCPlanner(planner_config)
    controller = GeometricController()
    
    # Create test state
    state = DroneState(
        timestamp=time.time(),
        position=np.array([0.0, 0.0, 1.0]),
        velocity=np.zeros(3),
        attitude=np.zeros(3),
        angular_velocity=np.zeros(3),
    )
    
    # Test goal
    goal = np.array([5.0, 3.0, 2.0])
    
    # Plan trajectory
    print("Planning trajectory...")
    trajectory = planner.plan_trajectory(state, goal)
    
    # Verify trajectory has all required fields
    assert trajectory.positions is not None, "Positions should not be None"
    assert trajectory.velocities is not None, "Velocities should not be None"
    assert trajectory.accelerations is not None, "Accelerations should not be None"
    assert trajectory.attitudes is not None, "Attitudes should not be None"
    assert trajectory.body_rates is not None, "Body rates should not be None"
    assert trajectory.thrusts is not None, "Thrusts should not be None"
    
    print(f"Trajectory created with {len(trajectory.timestamps)} steps")
    print(f"Positions shape: {trajectory.positions.shape}")
    print(f"Attitudes shape: {trajectory.attitudes.shape}")
    print(f"Body rates shape: {trajectory.body_rates.shape}")
    print(f"Thrusts shape: {trajectory.thrusts.shape}")
    
    # Test controller with trajectory
    print("Testing controller with trajectory...")
    for i in range(min(3, len(trajectory.timestamps))):
        t_current = trajectory.timestamps[i]
        
        # Test body-rate command
        body_rate_cmd = controller.compute_body_rate_from_trajectory(
            state, trajectory, t_current
        )
        
        assert isinstance(body_rate_cmd, BodyRateCommand), "Should return BodyRateCommand"
        assert 0.0 <= body_rate_cmd.thrust <= 1.0, "Thrust should be normalized (0-1)"
        assert body_rate_cmd.body_rates.shape == (3,), "Body rates should be 3D"
        
        print(f"Step {i}: Thrust={body_rate_cmd.thrust:.3f}, Body rates={body_rate_cmd.body_rates}")
    
    print("✅ Planner-controller integration test passed!")


if __name__ == "__main__":
    test_planner_controller_integration() 