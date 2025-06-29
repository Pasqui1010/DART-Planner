import pickle

import zmq


class ZmqClient:
    def __init__(self, host="localhost", port="5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{host}:{port}")
        print(f"ZMQ Client connected to {host}:{port}")

    def send_state_and_receive_trajectory(self, state):
        """Sends the current drone state and waits for a trajectory in response."""
        try:
            # Send the state
            message = pickle.dumps(state)
            self.socket.send(message)

            # Wait for the reply (the trajectory)
            response_message = self.socket.recv()
            trajectory = pickle.loads(response_message)
            return trajectory
        except zmq.ZMQError as e:
            print(f"ZMQ communication failed: {e}")
            return None  # Indicate failure

    def close(self):
        self.socket.close()
        self.context.term()
