import pickle
import time
import threading
from typing import Any, Dict, cast, Optional, Callable

import zmq
from .heartbeat import HeartbeatMonitor, HeartbeatConfig, HeartbeatMessage


class ZmqServer:
    def __init__(self, port: str = "5555", enable_heartbeat: bool = True, emergency_callback: Optional[Callable] = None) -> None:
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{port}")
        self.enable_heartbeat = enable_heartbeat
        self.sender_id = f"server_{port}"
        
        # Initialize heartbeat monitoring
        if enable_heartbeat:
            heartbeat_config = HeartbeatConfig(
                heartbeat_interval_ms=100,
                timeout_ms=500,
                emergency_callback=emergency_callback
            )
            self.heartbeat_monitor = HeartbeatMonitor(heartbeat_config)
            self.heartbeat_monitor.start_monitoring()
            
            # Start heartbeat sender thread
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_sender_loop, daemon=True)
            self._heartbeat_thread.start()
        else:
            self.heartbeat_monitor = None
            
        print(f"ZMQ Server listening on port {port} (heartbeat: {enable_heartbeat})")

    def receive_state(self) -> dict[str, Any] | None:
        """Blocks until a state message is received, then returns it."""
        try:
            message = self.socket.recv()
            data = pickle.loads(message)
            
            # Check if this is a heartbeat message
            if isinstance(data, dict) and data.get("type") == "heartbeat":
                if self.heartbeat_monitor:
                    self.heartbeat_monitor.heartbeat_received()
                # Send heartbeat response
                response = HeartbeatMessage(self.sender_id).to_dict()
                self.socket.send(pickle.dumps(response))
                return None  # Not a state message
                
            # Regular state message
            state = cast(Dict[str, Any], data)
            return state
        except zmq.ZMQError as e:
            print(f"Error receiving state: {e}")
            return None

    def _heartbeat_sender_loop(self):
        """Send periodic heartbeats to the client"""
        while self.enable_heartbeat and self.heartbeat_monitor:
            try:
                # Send heartbeat
                heartbeat_msg = HeartbeatMessage(self.sender_id)
                self.socket.send(pickle.dumps(heartbeat_msg.to_dict()))
                self.heartbeat_monitor.heartbeat_sent()
                
                # Wait for response
                response = self.socket.recv()
                response_data = pickle.loads(response)
                
                if isinstance(response_data, dict) and response_data.get("type") == "heartbeat":
                    self.heartbeat_monitor.heartbeat_received()
                    
            except zmq.ZMQError as e:
                print(f"Heartbeat send error: {e}")
                
            time.sleep(self.heartbeat_monitor.config.heartbeat_interval_ms / 1000.0)

    def send_trajectory(self, trajectory: object) -> None:
        """Sends a trajectory object to the connected client."""
        try:
            message = pickle.dumps(trajectory)
            self.socket.send(message)
        except zmq.ZMQError as e:
            print(f"Error sending trajectory: {e}")

    def close(self) -> None:
        # Stop heartbeat monitoring
        if self.heartbeat_monitor:
            self.heartbeat_monitor.stop_monitoring()
            
        self.socket.close()
        self.context.term()
