import os
import re
import sys

import matplotlib.pyplot as plt
import numpy as np

# Add the project root to the Python path

from dart_planner.common.types import ControlCommand, DroneState, Trajectory
from dart_planner.control.control_config import ControllerTuningProfile, get_controller_config
from dart_planner.control.onboard_controller import OnboardController
from dart_planner.utils.drone_simulator import DroneSimulator
from dart_planner.common.units import Q_


def create_test_trajectory(duration=10.0, dt=0.01) -> Trajectory:
    """Creates a simple trajectory for testing: accelerate up, hold, decelerate."""
    timestamps = np.arange(0, duration, dt)
    positions = []
    velocities = []
    accelerations = []

    for t in timestamps:
        if t < 2.0:  # Accelerate up
            accel = np.array([0, 0, 1.0])
            pos = 0.5 * accel * t**2
            vel = accel * t
        elif t < 8.0:  # Hold constant velocity
            t_hold = t - 2.0
            accel = np.array([0, 0, 0])
            pos = np.array([0, 0, 2.0]) + np.array([0, 0, 2.0]) * t_hold
            vel = np.array([0, 0, 2.0])
        else:  # Decelerate to a stop
            t_decel = t - 8.0
            accel = np.array([0, 0, -1.0])
            pos = (
                np.array([0, 0, 14.0])
                + np.array([0, 0, 2.0]) * t_decel
                + 0.5 * accel * t_decel**2
            )
            vel = np.array([0, 0, 2.0]) + accel * t_decel

        positions.append(pos)
        velocities.append(vel)
        accelerations.append(accel)

    return Trajectory(
        timestamps=np.array(timestamps),
        positions=Q_(np.array(positions), 'm'),
        velocities=Q_(np.array(velocities), 'm/s'),
        accelerations=Q_(np.array(accelerations), 'm/s^2'),
    )


def plot_results(log):
    """Plots the results of the controller test."""
    timestamps = [item["timestamp"] for item in log]

    fig, axs = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle("Controller Dynamics Test", fontsize=16)

    # Position plots
    for i, (axis, color) in enumerate(zip(["X", "Y", "Z"], ["r", "g", "b"])):
        axs[i, 0].plot(
            timestamps,
            [item["actual_pos"][i] for item in log],
            f"{color}-",
            label=f"Actual {axis}",
        )
        axs[i, 0].plot(
            timestamps,
            [item["target_pos"][i] for item in log],
            f"{color}--",
            label=f"Target {axis}",
        )
        axs[i, 0].set_ylabel(f"Position {axis} (m)")
        axs[i, 0].legend()
        axs[i, 0].grid(True)

    # Velocity plots
    for i, (axis, color) in enumerate(zip(["X", "Y", "Z"], ["r", "g", "b"])):
        axs[i, 1].plot(
            timestamps,
            [item["actual_vel"][i] for item in log],
            f"{color}-",
            label=f"Actual {axis} Vel",
        )
        axs[i, 1].plot(
            timestamps,
            [item["target_vel"][i] for item in log],
            f"{color}--",
            label=f"Target {axis} Vel",
        )
        axs[i, 1].set_ylabel(f"Velocity {axis} (m/s)")
        axs[i, 1].legend()
        axs[i, 1].grid(True)

    for ax in axs.flat:
        ax.set_xlabel("Time (s)")

    plt.tight_layout(rect=(0, 0, 1, 0.96))

    # Save the figure
    if not os.path.exists("test_results"):
        os.makedirs("test_results")
    filepath = os.path.join("test_results", "controller_dynamics_test.png")
    plt.savefig(filepath)
    print(f"Plot saved to {filepath}")
    plt.show()


def run_feedforward_test():
    """Runs the isolated controller test for the feedforward component."""
    print("--- Running Feedforward Validation Test ---")

    controller = OnboardController()
    # Disable feedback to isolate feedforward
    controller.pos_x_pid.Kp = 0.0
    controller.pos_x_pid.Ki = 0.0
    controller.pos_y_pid.Kp = 0.0
    controller.pos_y_pid.Ki = 0.0
    controller.pos_z_pid.Kp = 0.0
    controller.pos_z_pid.Ki = 0.0

    print("Gains: P=0, I=0. Testing FEEDFORWARD ONLY.")

    simulator = DroneSimulator()

    duration = 10.0
    dt = 0.01
    trajectory = create_test_trajectory(duration, dt)

    log = []
    current_state = DroneState(
        timestamp=0,
        position=Q_(np.zeros(3), 'm'),
        velocity=Q_(np.zeros(3), 'm/s'),
        attitude=Q_(np.zeros(3), 'rad'),
        angular_velocity=Q_(np.zeros(3), 'rad/s'),
    )

    for t_np in np.arange(0, duration, dt):
        t = float(t_np)
        current_state.timestamp = t

        cmd, target_pos = controller.compute_control_command(current_state, trajectory)
        current_state = simulator.step(current_state, cmd, dt)

        target_vel = Q_(np.zeros(3), 'm/s')
        interp_idx = np.searchsorted(trajectory.timestamps, t)
        if (
            interp_idx < len(trajectory.timestamps)
            and trajectory.velocities is not None
        ):
            target_vel = trajectory.velocities[interp_idx]

        log.append(
            {
                "timestamp": t,
                "actual_pos": current_state.position,
                "target_pos": target_pos,
                "actual_vel": current_state.velocity,
                "target_vel": target_vel,
            }
        )

    plot_results(log)


def run_feedback_test():
    """Runs the isolated controller test for the feedback component."""
    print("--- Running Feedback Validation Test (Disturbance Rejection) ---")

    controller = OnboardController()
    # Use only P and D gains for feedback. No feedforward.
    controller.pos_x_pid.Kp = 0.5
    controller.pos_x_pid.Ki = 0.0
    controller.pos_y_pid.Kp = 0.5
    controller.pos_y_pid.Ki = 0.0
    controller.pos_z_pid.Kp = 1.0
    controller.pos_z_pid.Ki = 0.0

    print(
        f"Gains: Kp=[{controller.pos_x_pid.Kp}, {controller.pos_y_pid.Kp}, {controller.pos_z_pid.Kp}], Ki=0"
    )

    simulator = DroneSimulator()

    duration = 10.0
    dt = 0.01

    # Target is to hover at a specific point
    target_hover_pos = Q_(np.array([0, 0, 5.0]), 'm')
    hover_trajectory = Trajectory(
        timestamps=np.array([0, duration]),
        positions=Q_(np.stack([np.array([0, 0, 5.0]), np.array([0, 0, 5.0])]), 'm'),
        velocities=Q_(np.stack([np.zeros(3), np.zeros(3)]), 'm/s'),
        accelerations=Q_(np.stack([np.zeros(3), np.zeros(3)]), 'm/s^2'),
    )

    log = []
    current_state = DroneState(
        timestamp=0,
        position=Q_(np.zeros(3), 'm'),
        velocity=Q_(np.zeros(3), 'm/s'),
        attitude=Q_(np.zeros(3), 'rad'),
        angular_velocity=Q_(np.zeros(3), 'rad/s'),
    )
    disturbance_applied = False

    for t_np in np.arange(0, duration, dt):
        t = float(t_np)
        current_state.timestamp = t

        # Apply a disturbance mid-flight
        if t > 4.0 and not disturbance_applied:
            print("Applying disturbance!")
            current_state.velocity = Q_(current_state.velocity.magnitude + np.array([2.0, -2.0, 3.0]), 'm/s')
            disturbance_applied = True

        cmd, target_pos = controller.compute_control_command(
            current_state, hover_trajectory
        )
        current_state = simulator.step(current_state, cmd, dt)

        log.append(
            {
                "timestamp": t,
                "actual_pos": current_state.position,
                "target_pos": target_pos,
                "actual_vel": current_state.velocity,
                "target_vel": Q_(np.zeros(3), 'm/s'),
            }
        )

    plot_results(log)


def run_integrated_test():
    """
    Runs an integrated test to validate the combined feedforward and feedback control.
    This is Phase 2 of our diagnostic plan.
    """
    print("--- Running Integrated Feedforward + Feedback Test ---")

    controller = OnboardController()

    print(
        f"Gains: Kp=[{controller.pos_x_pid.Kp}, {controller.pos_y_pid.Kp}, {controller.pos_z_pid.Kp}], "
        f"Ki=[{controller.pos_x_pid.Ki}, {controller.pos_y_pid.Ki}, {controller.pos_z_pid.Ki}]"
    )

    simulator = DroneSimulator()

    duration = 10.0
    dt = 0.01
    trajectory = create_test_trajectory(duration, dt)

    log = []
    current_state = DroneState(
        timestamp=0,
        position=Q_(np.zeros(3), 'm'),
        velocity=Q_(np.zeros(3), 'm/s'),
        attitude=Q_(np.zeros(3), 'rad'),
        angular_velocity=Q_(np.zeros(3), 'rad/s'),
    )

    for t_np in np.arange(0, duration, dt):
        t = float(t_np)
        current_state.timestamp = t

        cmd, target_pos = controller.compute_control_command(current_state, trajectory)
        current_state = simulator.step(current_state, cmd, dt)

        target_vel = Q_(np.zeros(3), 'm/s')
        interp_idx = np.searchsorted(trajectory.timestamps, t)
        if (
            interp_idx < len(trajectory.timestamps)
            and trajectory.velocities is not None
        ):
            target_vel = trajectory.velocities[interp_idx]

        log.append(
            {
                "timestamp": t,
                "actual_pos": current_state.position,
                "target_pos": target_pos,
                "actual_vel": current_state.velocity,
                "target_vel": target_vel,
            }
        )

    plot_results(log)


def run_attitude_test():
    """
    Tests the inner-loop attitude controller's ability to track a step command.
    This is the first and most critical step in cascade tuning.
    """
    print("--- Running Inner-Loop Attitude Control Test ---")

    # Manually load gains to ensure we get the latest version
    controller = OnboardController()

    # Disable the outer position loop entirely
    controller.pos_x_pid.Kp = 0.0
    controller.pos_x_pid.Ki = 0.0
    controller.pos_x_pid.Kd = 0.0
    controller.pos_y_pid.Kp = 0.0
    controller.pos_y_pid.Ki = 0.0
    controller.pos_y_pid.Kd = 0.0
    controller.pos_z_pid.Kp = 0.0
    controller.pos_z_pid.Ki = 0.0
    controller.pos_z_pid.Kd = 0.0

    simulator = DroneSimulator()
    print(
        f"Controller using Attitude Gains: Kp={controller.roll_pid.Kp}, Ki={controller.roll_pid.Ki}, Kd={controller.roll_pid.Kd}"
    )

    duration = 5.0
    dt = 0.01

    log = []
    current_state = DroneState(
        timestamp=0,
        position=Q_(np.zeros(3), 'm'),
        velocity=Q_(np.zeros(3), 'm/s'),
        attitude=Q_(np.zeros(3), 'rad'),
        angular_velocity=Q_(np.zeros(3), 'rad/s'),
    )

    # We will manually override the desired attitude to test the inner loop
    desired_roll_step = Q_(np.deg2rad(10), 'rad')  # 10 degrees
    desired_pitch_step = Q_(np.deg2rad(-5), 'rad')  # -5 degrees

    for t_np in np.arange(0, duration, dt):
        t = float(t_np)
        current_state.timestamp = t

        # Determine the target attitude based on time
        target_roll = desired_roll_step if t > 1.0 else Q_(0.0, 'rad')
        target_pitch = desired_pitch_step if t > 2.0 else Q_(0.0, 'rad')
        target_yaw_rate = Q_(0.0, 'rad/s')

        # Use our new testable interface to get the torque
        torque = controller._compute_torque(
            target_roll.magnitude, target_pitch.magnitude, target_yaw_rate.magnitude, current_state, dt
        )

        # We need a thrust command to stay airborne, otherwise it just falls.
        # Let's command a thrust that counters gravity.
        thrust = controller.mass * controller.g

        command = ControlCommand(thrust=Q_(thrust, 'N'), torque=Q_(torque, 'N*m'))
        current_state = simulator.step(current_state, command, dt)

        log.append(
            {
                "timestamp": t,
                "actual_roll": current_state.attitude[0],
                "target_roll": target_roll,
                "actual_pitch": current_state.attitude[1],
                "target_pitch": target_pitch,
            }
        )

    # Plotting function needs to be adapted for attitude
    plot_attitude_results(log)


def plot_attitude_results(log):
    """Plots the results of the attitude controller test."""
    timestamps = [item["timestamp"] for item in log]

    fig, axs = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle("Attitude Controller Step Response", fontsize=16)

    # Roll plot
    axs[0].plot(
        timestamps,
        np.rad2deg([item["actual_roll"] for item in log]),
        "r-",
        label="Actual Roll",
    )
    axs[0].plot(
        timestamps,
        np.rad2deg([item["target_roll"] for item in log]),
        "r--",
        label="Target Roll",
    )
    axs[0].set_ylabel("Roll Angle (deg)")
    axs[0].legend()
    axs[0].grid(True)

    # Pitch plot
    axs[1].plot(
        timestamps,
        np.rad2deg([item["actual_pitch"] for item in log]),
        "g-",
        label="Actual Pitch",
    )
    axs[1].plot(
        timestamps,
        np.rad2deg([item["target_pitch"] for item in log]),
        "g--",
        label="Target Pitch",
    )
    axs[1].set_ylabel("Pitch Angle (deg)")
    axs[1].set_xlabel("Time (s)")
    axs[1].legend()
    axs[1].grid(True)

    plt.tight_layout(rect=(0, 0, 1, 0.96))

    filepath = os.path.join("test_results", "attitude_step_test.png")
    plt.savefig(filepath)
    print(f"Plot saved to {filepath}")
    plt.show()


if __name__ == "__main__":
    # run_feedforward_test()
    # run_feedback_test()
    run_integrated_test()
    # run_attitude_test()
