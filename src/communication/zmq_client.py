"""
ZMQ Client for DART-Planner

Secure client for ZMQ communication with integrity checking.
"""

import time
import threading
from typing import Any, Optional, Dict, Callable
import zmq

from .secure_serializer import serialize, deserialize


class ZmqClient:
    """
    Secure ZMQ client for communication with DART-Planner services.
    
    Features:
    - Secure serialization (no pickle)
    - Message integrity verification
    - Automatic reconnection
    - Thread-safe operations
    """
    
    def __init__(self, server_address: str = "tcp://localhost:5555"):
        """
        Initialize ZMQ client.
        
        Args:
            server_address: ZMQ server address (default: tcp://localhost:5555)
        """
        self.server_address = server_address
        self.context = zmq.Context()
        self.socket: Optional[zmq.Socket] = None
        self.connected = False
        self._lock = threading.Lock()
        self._connect()
    
    def _connect(self):
        """Establish connection to ZMQ server."""
        try:
            if self.socket:
                self.socket.close()
            
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.server_address)
            self.connected = True
            print(f"✅ ZMQ client connected to {self.server_address}")
            
        except Exception as e:
            print(f"❌ ZMQ client connection failed: {e}")
            self.connected = False
    
    def send_request(self, data: Any, timeout: float = 5.0) -> Optional[Any]:
        """
        Send request and wait for response.
        
        Args:
            data: Data to send
            timeout: Request timeout in seconds
            
        Returns:
            Response data or None if failed
        """
        if not self.connected:
            self._connect()
            if not self.connected:
                return None
        
        with self._lock:
            try:
                if not self.socket:
                    return None
                
                # Serialize data securely
                message = serialize(data)
                
                # Send request
                self.socket.send(message)
                
                # Wait for response with timeout
                if self.socket.poll(int(timeout * 1000)) > 0:
                    response_message = self.socket.recv()
                    response_data = deserialize(response_message)
                    return response_data
                else:
                    print(f"⚠️ ZMQ request timeout after {timeout}s")
                    return None
                    
            except Exception as e:
                print(f"❌ ZMQ request failed: {e}")
                self.connected = False
                return None
    
    def send_async_request(self, data: Any, callback: Callable[[Optional[Any]], None], timeout: float = 5.0):
        """
        Send asynchronous request.
        
        Args:
            data: Data to send
            callback: Callback function to handle response
            timeout: Request timeout in seconds
        """
        def _async_request():
            response = self.send_request(data, timeout)
            callback(response)
        
        thread = threading.Thread(target=_async_request, daemon=True)
        thread.start()
    
    def close(self):
        """Close ZMQ connection."""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        self.connected = False
        print("🔌 ZMQ client disconnected")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Example usage
if __name__ == "__main__":
    client = ZmqClient()
    
    # Send test request
    test_data = {"command": "status", "timestamp": time.time()}
    response = client.send_request(test_data)
    
    if response:
        print(f"✅ Response received: {response}")
    else:
        print("❌ No response received")
    
    client.close()
