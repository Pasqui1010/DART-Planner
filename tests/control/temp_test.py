import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import numpy as np
import pytest
from dart_planner.control.geometric_controller import GeometricController, GeometricControllerConfig
from dart_planner.common.types import DroneState
from dart_planner.common.units import Q_


def create_dummy_state(timestamp: float = 0.0) -> DroneState:
    """Return a neutral drone state at the origin, zero velocity."""
    return DroneState(
        timestamp=timestamp,
        position=np.zeros(3),
        velocity=np.zeros(3),
        attitude=np.zeros(3),
        angular_velocity=np.zeros(3),
    )


@pytest.fixture
def controller() -> GeometricController:
    cfg = GeometricControllerConfig()
    # Use raw config (no tuning profile) to simplify numeric expectations
    return GeometricController(cfg, tuning_profile=None)


def test_acceleration_matches_desired(controller):
    """With zero tracking error the controller should produce acceleration equal to desired_acc."""
    state = create_dummy_state()
    desired_acc = Q_(np.array([0.0, 0.0, 1.5]), "m/s^2")

    cmd = controller.compute_control(
        state,
        desired_pos=Q_(state.position, "m"),
        desired_vel=Q_(state.velocity, "m/s"),
        desired_acc=desired_acc,
    )

    # Convert thrust back to acceleration (F = m a)
    # Note: The controller is designed to output the thrust required to counteract gravity *plus* achieve the desired acceleration.
    # Therefore, to verify the desired acceleration, we must subtract the gravity component from the thrust-derived acceleration.
    # acc_out = (Total Thrust / mass) - g
    acc_out = (cmd.thrust.to("N").magnitude / controller.config.mass) - controller.config.gravity

    # We are checking the acceleration in the Z direction, so we only need to compare the Z component.
    # The desired acceleration is [0, 0, 1.5], so we compare the third element of acc_out.
    assert np.allclose(acc_out[2], desired_acc.magnitude[2], atol=1e-2)


def test_torque_coriolis_term(controller):
    """Non-zero angular velocity should introduce inertia-dependent torque (coriolis term)."""
    state = create_dummy_state()
    state.angular_velocity = np.array([1.0, 0.5, -0.2])

    cmd = controller.compute_control(
        state,
        desired_pos=Q_(state.position, "m"),
        desired_vel=Q_(state.velocity, "m/s"),
        desired_acc=Q_(np.zeros(3), "m/s^2"),
    )
    torque = cmd.torque.to("N*m").magnitude

    # Expect at least one component dominated by coriolis term to be non-zero
    assert np.linalg.norm(torque) > 0.0
