import pickle
import time
from typing import Any, Dict, cast

import zmq


class ZmqServer:
    def __init__(self, port: str = "5555") -> None:
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{port}")
        print(f"ZMQ Server listening on port {port}")

    def receive_state(self) -> dict[str, Any] | None:
        """Blocks until a state message is received, then returns it."""
        try:
            message = self.socket.recv()
            state = cast(Dict[str, Any], pickle.loads(message))
            return state
        except zmq.ZMQError as e:
            print(f"Error receiving state: {e}")
            return None

    def send_trajectory(self, trajectory: object) -> None:
        """Sends a trajectory object to the connected client."""
        try:
            message = pickle.dumps(trajectory)
            self.socket.send(message)
        except zmq.ZMQError as e:
            print(f"Error sending trajectory: {e}")

    def close(self) -> None:
        self.socket.close()
        self.context.term()
