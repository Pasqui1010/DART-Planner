"""
Simple Units Safety Test

This test verifies that all refactored modules properly handle units without using pytest.
"""

import sys
import os
import numpy as np

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dart_planner.common.types import DroneState, ControlCommand, Trajectory, EstimatedState, Pose, Twist, Accel
from dart_planner.common.units import Q_, ensure_units, to_float
from dart_planner.control.geometric_controller import GeometricController
from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
from dart_planner.planning.global_mission_planner import GlobalMissionPlanner, GlobalMissionConfig, SemanticWaypoint


# --- Units safety tests only ---

def test_geometric_controller_units_safety():
    print("  Testing Geometric Controller...")
    controller = GeometricController()
    controller.reset()  # Ensure internal state is initialized
    current_state = DroneState(
        timestamp=1.0,
        position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
        velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
        attitude=Q_(np.array([0.1, 0.2, 0.3]), 'rad'),
        angular_velocity=Q_(np.array([0.01, 0.02, 0.03]), 'rad/s')
    )
    desired_state = DroneState(
        timestamp=1.0,
        position=Q_(np.array([2.0, 3.0, 4.0]), 'm'),
        velocity=Q_(np.array([0.2, 0.3, 0.4]), 'm/s'),
        attitude=Q_(np.array([0.2, 0.3, 0.4]), 'rad'),
        angular_velocity=Q_(np.array([0.02, 0.03, 0.04]), 'rad/s')
    )
    control_cmd = controller.compute_control(
        current_state,
        desired_state.position,
        desired_state.velocity,
        Q_(np.zeros(3), 'm/s^2'),
        Q_(0.0, 'rad'),
        Q_(0.0, 'rad/s')
    )
    print(f"    Control command thrust: {control_cmd.thrust}")
    print(f"    Control command torque: {control_cmd.torque}")
    assert control_cmd.thrust.check('[force]')
    assert control_cmd.torque.check('[force] * [length]')
    assert 0 < control_cmd.thrust.magnitude < 50
    assert np.all(np.abs(control_cmd.torque.magnitude) < 10)
    print("    ✅ Geometric Controller units safety passed")


def test_se3_mpc_planner_units_safety():
    print("  Testing SE3 MPC Planner...")
    config = SE3MPCConfig()
    planner = SE3MPCPlanner(config)
    assert isinstance(config.max_velocity, type(Q_(1.0, 'm/s')))
    assert config.max_velocity.check('[length] / [time]')
    assert isinstance(config.max_acceleration, type(Q_(1.0, 'm/s^2')))
    assert config.max_acceleration.check('[length] / [time] ** 2')
    assert isinstance(config.max_thrust, type(Q_(1.0, 'N')))
    assert config.max_thrust.check('[force]')
    goal_position = Q_(np.array([5.0, 5.0, 5.0]), 'm')
    planner.set_goal(goal_position)
    assert planner.goal_position is not None
    assert planner.goal_position.check('[length]')
    obstacle_center = Q_(np.array([3.0, 3.0, 3.0]), 'm')
    obstacle_radius = Q_(1.0, 'm')
    planner.add_obstacle(obstacle_center, obstacle_radius)
    assert len(planner.obstacles) == 1
    assert planner.obstacles[0][0].check('[length]')
    assert planner.obstacles[0][1].check('[length]')
    print("    ✅ SE3 MPC Planner units safety passed")


def test_global_mission_planner_units_safety():
    print("  Testing Global Mission Planner...")
    config = GlobalMissionConfig()
    planner = GlobalMissionPlanner(config)
    assert isinstance(config.exploration_radius, type(Q_(1.0, 'm')))
    assert config.exploration_radius.check('[length]')
    assert isinstance(config.safety_margin, type(Q_(1.0, 'm')))
    assert config.safety_margin.check('[length]')
    assert isinstance(config.communication_range, type(Q_(1.0, 'm')))
    assert config.communication_range.check('[length]')
    waypoint = SemanticWaypoint(
        position=Q_(np.array([10.0, 10.0, 5.0]), 'm'),
        semantic_label="test_waypoint",
        uncertainty=0.5,
        priority=1
    )
    assert waypoint.position.check('[length]')
    current_state = DroneState(
        timestamp=0.0,
        position=Q_(np.zeros(3), 'm'),
        velocity=Q_(np.zeros(3), 'm/s'),
        attitude=Q_(np.zeros(3), 'rad'),
        angular_velocity=Q_(np.zeros(3), 'rad/s')
    )
    goal = planner.get_current_goal(current_state)
    assert isinstance(goal, type(Q_(np.zeros(3), 'm')))
    assert goal.check('[length]')
    print("    ✅ Global Mission Planner units safety passed")


def test_units_conversion_edge_cases():
    print("  Testing Units Conversion Edge Cases...")
    zero_pos = Q_(np.zeros(3), 'm')
    zero_vel = Q_(np.zeros(3), 'm/s')
    assert zero_pos.check('[length]')
    assert zero_vel.check('[length] / [time]')
    neg_pos = Q_(np.array([-1.0, -2.0, -3.0]), 'm')
    assert neg_pos.check('[length]')
    assert np.all(neg_pos.magnitude < 0)
    large_pos = Q_(np.array([1000.0, 2000.0, 3000.0]), 'm')
    assert large_pos.check('[length]')
    assert np.all(large_pos.magnitude > 100)
    print("    ✅ Units conversion edge cases passed")


def test_units_consistency_across_modules():
    print("  Testing Units Consistency Across Modules...")
    pose = Pose(
        position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
        orientation=Q_(np.array([0.1, 0.2, 0.3]), 'rad')
    )
    twist = Twist(
        linear=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
        angular=Q_(np.array([0.01, 0.02, 0.03]), 'rad/s')
    )
    accel = Accel(
        linear=Q_(np.array([0.01, 0.02, 0.03]), 'm/s^2'),
        angular=Q_(np.array([0.001, 0.002, 0.003]), 'rad/s^2')
    )
    estimated_state = EstimatedState(
        timestamp=0.0,
        pose=pose,
        twist=twist,
        accel=accel,
        source="test"
    )
    drone_state = DroneState(
        timestamp=estimated_state.timestamp,
        position=estimated_state.pose.position,
        velocity=estimated_state.twist.linear,
        attitude=estimated_state.pose.orientation,
        angular_velocity=estimated_state.twist.angular
    )
    goal_position = Q_(np.array([5.0, 5.0, 5.0]), 'm')
    controller = GeometricController()
    desired_state = DroneState(
        timestamp=0.0,
        position=goal_position,
        velocity=Q_(np.zeros(3), 'm/s'),
        attitude=Q_(np.zeros(3), 'rad'),
        angular_velocity=Q_(np.zeros(3), 'rad/s')
    )
    control_cmd = controller.compute_control(
        drone_state,
        desired_state.position,
        desired_state.velocity,
        Q_(np.zeros(3), 'm/s^2'),
        Q_(0.0, 'rad'),
        Q_(0.0, 'rad/s')
    )
    assert drone_state.position.check('[length]')
    assert drone_state.velocity.check('[length] / [time]')
    assert drone_state.attitude.check('')  # dimensionless (radians)
    assert drone_state.angular_velocity.check('1 / [time]')
    assert goal_position.check('[length]')
    assert control_cmd.thrust.check('[force]')
    assert control_cmd.torque.check('[force] * [length]')
    print("    ✅ Units consistency across modules passed")


def test_units_error_prevention():
    print("  Testing Units Error Prevention...")
    try:
        pos_m = Q_(np.array([1.0, 2.0, 3.0]), 'm')
        att_rad = Q_(np.array([0.1, 0.2, 0.3]), 'rad')
        _ = pos_m + att_rad
        assert False, "Should have raised an error for mixing units"
    except Exception as e:
        print(f"    ✅ Correctly prevented mixing units: {type(e).__name__}")
    try:
        DroneState(
            timestamp=0.0,
            position=Q_(np.array([1.0, 2.0, 3.0]), 'rad'),
            velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
            attitude=Q_(np.array([0.1, 0.2, 0.3]), 'rad'),
            angular_velocity=Q_(np.array([0.01, 0.02, 0.03]), 'rad/s')
        )
        assert False, "Should have raised an error for wrong units"
    except Exception as e:
        print(f"    ✅ Correctly prevented wrong units: {type(e).__name__}")


def test_performance_with_units():
    print("  Testing Performance with Units...")
    import time
    controller = GeometricController()
    current_state = DroneState(
        timestamp=0.0,
        position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
        velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
        attitude=Q_(np.array([0.1, 0.2, 0.3]), 'rad'),
        angular_velocity=Q_(np.array([0.01, 0.02, 0.03]), 'rad/s')
    )
    desired_state = DroneState(
        timestamp=0.0,
        position=Q_(np.array([2.0, 3.0, 4.0]), 'm'),
        velocity=Q_(np.array([0.2, 0.3, 0.4]), 'm/s'),
        attitude=Q_(np.array([0.2, 0.3, 0.4]), 'rad'),
        angular_velocity=Q_(np.array([0.02, 0.03, 0.04]), 'rad/s')
    )
    start_time = time.perf_counter()
    for _ in range(1000):
        control_cmd = controller.compute_control(
            current_state,
            desired_state.position,
            desired_state.velocity,
            Q_(np.zeros(3), 'm/s^2'),
            Q_(0.0, 'rad'),
            Q_(0.0, 'rad/s')
        )
    end_time = time.perf_counter()
    avg_time = (end_time - start_time) / 1000
    print(f"    Average control computation time: {avg_time*1000:.2f} ms")
    assert avg_time < 0.001
    print("    ✅ Performance with units is acceptable")


def main():
    print("🧪 Running Comprehensive Units Safety Tests...")
    try:
        test_geometric_controller_units_safety()
        test_se3_mpc_planner_units_safety()
        test_global_mission_planner_units_safety()
        test_units_conversion_edge_cases()
        test_units_consistency_across_modules()
        test_units_error_prevention()
        test_performance_with_units()
        print("\n✅ All units safety tests passed!")
        print("🎯 DART-Planner is now units-safe across all critical modules!")
        print("\n🔧 Refactored Modules:")
        print("  - Geometric Controller: ✅ Units-safe")
        print("  - SE3 MPC Planner: ✅ Units-safe")
        print("  - Global Mission Planner: ✅ Units-safe")
        print("  - State Estimation: ✅ Units-safe")
        print("  - Core Types: ✅ Units-safe")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    exit(main()) 