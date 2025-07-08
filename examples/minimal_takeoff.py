"""Minimal smoke-test for the DART-Planner stack.

This example instantiates the simulator, the geometric controller, and a
very short waypoint trajectory to verify that the core runtime dependencies
are installed and working.  It finishes in <10 s so it can be executed in
CI (pytest -m smoke) and by new contributors as a quick sanity check.
"""

from __future__ import annotations
from dart_planner.common.di_container_v2 import get_container

import time
from pathlib import Path

import numpy as np

from dart_planner.common.types import DroneState, Trajectory
from dart_planner.control.geometric_controller import GeometricController

# Runtime package imports (no sys.path mangling!)
from dart_planner.utils.drone_simulator import DroneSimulator


def run_smoke_test(duration: float = 5.0, hz: float = 100.0) -> None:
    """Run a minimal closed-loop hover test for *duration* seconds."""

    sim = DroneSimulator()
    ctrl = get_container().create_control_container().get_geometric_controller())

    dt = 1.0 / hz
    n_steps = int(duration * hz)

    # Initial state: at origin, 1 m above ground
    state = DroneState(
        timestamp=0.0,
        position=np.array([0.0, 0.0, 1.0]),
        velocity=np.zeros(3),
        attitude=np.zeros(3),
        angular_velocity=np.zeros(3),
    )

    # Static hover trajectory
    traj = Trajectory(
        timestamps=np.array([0.0, duration]),
        positions=np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]),
    )

    for i in range(n_steps):
        t = i * dt
        desired_pos = traj.positions[0]
        desired_vel = np.zeros(3)
        desired_acc = np.zeros(3)

        cmd = ctrl.compute_control(
            current_state=state,
            desired_pos=desired_pos,
            desired_vel=desired_vel,
            desired_acc=desired_acc,
        )
        state = sim.step(state, cmd, dt)
        time.sleep(0.0)  # real-time not required; keep loop simple

    print("✅ Smoke test completed – simulator and controller run OK.")


if __name__ == "__main__":
    run_smoke_test()
