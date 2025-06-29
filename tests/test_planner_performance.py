import time
import numpy as np
from src.common.types import DroneState
from src.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig

MAX_MEAN_MS = 50.0
MAX_SINGLE_MS = 100.0


def test_se3_mpc_speed():
    """Ensure the planner meets real-time budget on CI runners."""
    cfg = SE3MPCConfig(prediction_horizon=6, dt=0.1)
    planner = SE3MPCPlanner(cfg)

    times = []
    state = DroneState(
        timestamp=0.0,
        position=np.zeros(3),
        velocity=np.zeros(3),
        attitude=np.zeros(3),
        angular_velocity=np.zeros(3),
    )

    for _ in range(100):
        goal = np.random.uniform(-5, 5, size=3)
        t0 = time.perf_counter()
        traj = planner.plan_trajectory(state, goal)
        dt = (time.perf_counter() - t0) * 1000
        times.append(dt)
        assert len(traj.positions) > 0

    mean_ms = sum(times) / len(times)
    assert mean_ms <= MAX_MEAN_MS, f"Mean planning time too high: {mean_ms:.1f} ms"
    assert (
        max(times) <= MAX_SINGLE_MS
    ), f"Single planning spike {max(times):.1f} ms exceeds {MAX_SINGLE_MS} ms"
