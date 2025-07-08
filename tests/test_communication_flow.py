# Run this module in its own xdist group so network resources are isolated
import pytest
from dart_planner.common.di_container_v2 import get_container

pytestmark = pytest.mark.xdist_group("comm")

import threading
import time

import numpy as np

from dart_planner.cloud.main_improved import main_improved as cloud_main
from dart_planner.common.types import DroneState
from dart_planner.communication.zmq_client import ZmqClient
from dart_planner.edge.main_improved import main_improved as edge_main


def run_cloud_server():
    """Wrapper to run the cloud server main loop."""
    try:
        cloud_main()
    except Exception as e:
        print(f"Cloud server failed: {e}")


@pytest.fixture(scope="module")
def cloud_server_thread():
    """Fixture to run the cloud server in a background thread."""
    server_thread = threading.Thread(target=run_cloud_server, daemon=True)
    server_thread.start()
    print("Waiting for cloud server to initialize...")
    time.sleep(2)  # Give the server a moment to start up
    yield
    # No cleanup needed as it's a daemon thread


def test_edge_to_cloud_communication(cloud_server_thread):
    """
    An integration test to verify basic communication between edge and cloud.
    - Starts the cloud server.
    - The edge client sends one state message.
    - Verifies that a trajectory is received in response.
    """
    print("--- Starting Integration Test ---")

    # 1. Initialize Edge Components
    client = get_container().create_communication_container().get_zmq_client()
    initial_state = DroneState(
        timestamp=time.time(), position=np.array([0.0, 0.0, 0.0])
    )

    # 2. Perform one communication cycle
    print("Edge: Sending state to cloud...")
    trajectory = client.send_state_and_receive_trajectory(initial_state)
    print("Edge: Received response from cloud.")

    # 3. Assert the result
    assert trajectory is not None
    assert hasattr(trajectory, "timestamps")
    assert hasattr(trajectory, "positions")
    assert isinstance(trajectory.positions, np.ndarray)
    assert trajectory.positions.shape[0] > 0

    print(
        f"Edge: Successfully received trajectory with {trajectory.positions.shape[0]} waypoints."
    )

    # 4. Clean up
    client.close()
    print("--- Integration Test Finished ---")
