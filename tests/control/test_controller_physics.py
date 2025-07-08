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
    acc_out = cmd.thrust.to("N").magnitude / controller.config.mass - np.array([0.0, 0.0, controller.config.gravity])
    assert np.allclose(acc_out, desired_acc.magnitude, atol=1e-2)


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