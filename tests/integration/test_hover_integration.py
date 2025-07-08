import numpy as np
import pytest

from dart_planner.common.types import DroneState
from dart_planner.common.units import Q_
from dart_planner.control.geometric_controller import GeometricController, GeometricControllerConfig
from dart_planner.hardware.motor_mixer import create_x_configuration_mixer


def test_hover_integration():
    """
    Golden integration test: a hover command through the controller and mixer
    should result in total thrust approximately equal to the drone's weight (mass * gravity).
    """
    # Set up hover state at 1m altitude
    position = Q_(np.array([0.0, 0.0, 1.0]), 'm')
    velocity = Q_(np.zeros(3), 'm/s')
    attitude = Q_(np.zeros(3), 'rad')
    angular_velocity = Q_(np.zeros(3), 'rad/s')
    # Timestamp yields dt=0.001 on first call
    state = DroneState(
        timestamp=0.001,
        position=position,
        velocity=velocity,
        attitude=attitude,
        angular_velocity=angular_velocity
    )

    # Initialize controller with default configuration
    config = GeometricControllerConfig()
    controller = GeometricController(config=config, tuning_profile=None)

    # Execute compute_control for hover: desired same as current
    control_cmd = controller.compute_control(
        state,
        desired_pos=position,
        desired_vel=velocity,
        desired_acc=Q_(np.zeros(3), 'm/s^2'),
        desired_yaw=0.0,
        desired_yaw_rate=0.0
    )

    # Extract thrust magnitude (float) and torque vector (numpy)
    thrust_cmd = float(control_cmd.thrust.to('N').magnitude)
    torque_cmd = control_cmd.torque.to('N*m').magnitude

    # Expected weight
    expected_weight = config.mass * config.gravity

    # Controller should command weight within 1%
    assert thrust_cmd == pytest.approx(expected_weight, rel=1e-2)
    # Torque should be near zero
    assert np.allclose(torque_cmd, np.zeros(3), atol=1e-3)

    # Pass command through motor mixer and recover
    mixer = create_x_configuration_mixer(arm_length=config.mass * 0 + 0.15)
    pwms = mixer.mix_commands(thrust_cmd, torque_cmd)
    recovered = mixer.get_control_allocation(pwms)

    # Recovered thrust should equal commanded thrust within 1%
    recovered_thrust = recovered[0]
    assert recovered_thrust == pytest.approx(expected_weight, rel=1e-2)
    # Recovered torques should be near zero
    assert np.allclose(recovered[1:], np.zeros(3), atol=1e-3) 