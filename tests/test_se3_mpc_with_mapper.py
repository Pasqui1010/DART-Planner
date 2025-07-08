import numpy as np
from dart_planner.common.di_container_v2 import get_container

from dart_planner.common.types import DroneState
from dart_planner.perception.explicit_geometric_mapper import ExplicitGeometricMapper
from dart_planner.planning.se3_mpc_planner import SE3MPCConfig, SE3MPCPlanner


def test_se3_mpc_with_live_mapping():
    """Integration test: SE3 MPC plans while map is updated with simulated LiDAR."""
            planner = get_container().create_planner_container().get_se3_planner()
    mapper = ExplicitGeometricMapper(resolution=0.5, max_range=40.0)

    # Start state
    state = DroneState(
        timestamp=0.0,
        position=np.array([0.0, 0.0, 2.0]),
        velocity=np.zeros(3),
        attitude=np.zeros(3),
        angular_velocity=np.zeros(3),
    )
    goal = np.array([10.0, 0.0, 5.0])

    for _ in range(5):
        # Simulate sensor update
        observations = mapper.simulate_lidar_scan(state, num_rays=180)
        mapper.update_map(observations)

        # Refresh obstacle list for planner (simple sample)
        grid, occ = mapper.get_local_occupancy_grid(state.position, size=15.0)
        occupied = grid[occ > 0.6]
        planner.clear_obstacles()
        for p in occupied[:: max(1, len(occupied) // 10)]:
            planner.add_obstacle(p, radius=1.0)

        traj = planner.plan_trajectory(state, goal)
        assert traj is not None and len(traj.positions) > 0

        # Advance fake state (move towards first waypoint)
        step = traj.positions[1] - state.position
        state.position += 0.3 * step  # move partially toward
        state.timestamp += planner.config.dt
