import numpy as np
from src.common.types import DroneState, ControlCommand
from src.utils.drone_simulator import DroneSimulator, SimulatorConfig
from src.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
from src.perception.explicit_geometric_mapper import ExplicitGeometricMapper

NUM_RUNS = 20  # keep light for CI (<30 s)
SIM_DURATION = 5.0  # seconds per run
DT = 0.15

def run_single(seed: int) -> bool:
    np.random.seed(seed)
    planner = SE3MPCPlanner(SE3MPCConfig(prediction_horizon=6, dt=DT))
    mapper = ExplicitGeometricMapper(resolution=0.5, max_range=40.0)

    sim_cfg = SimulatorConfig(
        wind_mean=0.0,
        wind_std=np.random.uniform(0.0, 1.5),
        sensor_noise_std=np.random.uniform(0.0, 0.05),
        drag_coefficient=0.05,
    )
    simulator = DroneSimulator(config=sim_cfg)

    state = DroneState(
        timestamp=0.0,
        position=np.array([0.0, 0.0, 2.0]),
        velocity=np.zeros(3),
        attitude=np.zeros(3),
        angular_velocity=np.zeros(3)
    )
    goal = np.array([8.0, 0.0, 5.0])

    steps = int(SIM_DURATION / DT)
    for _ in range(steps):
        obs = mapper.simulate_lidar_scan(state, num_rays=120)
        mapper.update_map(obs)

        grid, occ = mapper.get_local_occupancy_grid(state.position, size=15.0)
        occupied = grid[occ > 0.6]
        planner.clear_obstacles()
        for p in occupied[::max(1, len(occupied)//8)]:
            planner.add_obstacle(p, 1.0)

        traj = planner.plan_trajectory(state, goal)
        assert len(traj.positions) > 0
        next_pos = traj.positions[1]

        # Simple proportional pilot to follow plan
        desired_vel = (next_pos - state.position)
        command = ControlCommand(thrust=float(simulator.mass * sim_cfg.gravity), torque=np.zeros(3))
        state = simulator.step(state, command, DT)

    # Metric: distance to goal < 2 m
    return bool(np.linalg.norm(state.position - goal) < 2.0)


def test_monte_carlo_runs():
    successes = sum(run_single(i) for i in range(NUM_RUNS))
    success_rate = successes / NUM_RUNS
    # Expect at least 80% success in default CI conditions
    assert success_rate >= 0.8, f"Monte Carlo success rate too low: {success_rate*100:.0f}%" 