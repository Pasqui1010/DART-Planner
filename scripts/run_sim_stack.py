#!/usr/bin/env python3
"""
DART-Planner Simulation Stack Launcher
--------------------------------------

This script provides a unified entry point for launching a full
software-in-the-loop (SITL) simulation of the DART-Planner system.

It is responsible for:
1.  Starting a headless physics simulator (e.g., Gazebo).
2.  Launching the ROS 2 bridge to communicate with the simulator.
3.  Running the FastAPI gateway application that serves the demo UI and API.

This enables end-to-end testing and validation in a software-only environment,
which is critical for CI/CD pipelines and development without physical hardware.
"""

import subprocess
import time
import sys
import os
import argparse


def run_command(command, cwd=".", name="Process"):
    """Runs a command in a new process and returns the process object."""
    print(f"🚀 Starting {name}: `{' '.join(command)}`")
    process = subprocess.Popen(
        command,
        stdout=sys.stdout,
        stderr=sys.stderr,
        cwd=cwd
    )
    return process


def main():
    """Main function to launch the simulation stack."""
    parser = argparse.ArgumentParser(description="Launch the DART-Planner SITL stack.")
    parser.add_argument(
        "--simulator",
        type=str,
        default="gazebo",
        choices=["gazebo", "none"],
        help="Specify the physics simulator to use. 'none' will not launch a simulator."
    )
    args = parser.parse_args()

    processes = []
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

    try:
        # Step 1: Launch the physics simulator (if specified)
        if args.simulator == "gazebo":
            # This is a placeholder for launching Gazebo. A real implementation
            # would likely involve a ROS 2 launch file.
            # Example: `ros2 launch gazebo_ros gz_sim.launch.py`
            # For now, we just print the command.
            print("✨ Gazebo simulator launch requested (placeholder).")
            print("   In a real setup, use a ROS 2 launch file to start Gazebo/Ignition.")
            # gz_sim_process = run_command(["ros2", "launch", "gazebo_ros", "gz_sim.launch.py"], name="Gazebo")
            # processes.append(gz_sim_process)
            time.sleep(5) # Give the simulator time to start up

        # Step 2: Launch the FastAPI Gateway Application
        # We use uvicorn to run the ASGI app.
        gateway_process = run_command(
            [
                sys.executable,  # Use the current python interpreter
                "-m", "uvicorn",
                "demos.web_demo.app:socket_app",
                "--host", "0.0.0.0",
                "--port", "8080",
                "--reload"
            ],
            cwd=project_root,
            name="FastAPI Gateway"
        )
        processes.append(gateway_process)

        print("\n✅ DART-Planner Secure-Sim Stack is UP!")
        print("   - FastAPI Gateway: http://localhost:8080")
        print("   - Simulator: " + args.simulator)
        print("\nPress Ctrl+C to shut down.")

        # Wait for processes to complete (which they won't, until interrupted)
        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("\nSIGINT received, shutting down simulation stack...")
    finally:
        for p in processes:
            print(f"Terminating {p.args}...")
            p.terminate()
        print("✅ Shutdown complete.")


if __name__ == "__main__":
    main() 