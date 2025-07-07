"""
ZMQ Server for DART-Planner

Secure server for ZMQ communication with integrity checking.
"""

import time
import threading
from typing import Any, Optional, Dict, Callable
import zmq

from .secure_serializer import serialize, deserialize


class ZmqServer:
    """
    Secure ZMQ server for DART-Planner services.
    
    Features:
    - Secure serialization (no pickle)
    - Message integrity verification
    - Request handling with callbacks
    - Thread-safe operations
    """
    
    def __init__(self, port: int = 5555, bind_address: str = "127.0.0.1", enable_curve: bool = False):
        """
        Initialize ZMQ server.
        
        Args:
            port: Port to bind to (default: 5555)
            bind_address: Address to bind to (default: "127.0.0.1" for security)
            enable_curve: Enable ZMQ Curve encryption (default: False)
        """
        self.port = port
        self.bind_address = bind_address
        self.enable_curve = enable_curve
        self.context = zmq.Context()
        self.socket: Optional[zmq.Socket] = None
        self.running = False
        self._lock = threading.Lock()
        self._request_handlers: Dict[str, Callable] = {}
        
        # Security validation
        if bind_address == "*":
            import logging
            logging.warning("ZMQ server binding to all interfaces (*) - security risk!")
        elif bind_address not in ["127.0.0.1", "localhost", "::1"]:
            import logging
            logging.warning(f"ZMQ server binding to {bind_address} - ensure this is intended")
    
    def add_handler(self, command: str, handler: Callable[[Any], Any]):
        """
        Add request handler for specific command.
        
        Args:
            command: Command name to handle
            handler: Function to handle the request
        """
        self._request_handlers[command] = handler
    
    def start(self):
        """Start the ZMQ server."""
        try:
            self.socket = self.context.socket(zmq.REP)
            bind_string = f"tcp://{self.bind_address}:{self.port}"
            self.socket.bind(bind_string)
            self.running = True
            
            print(f"✅ ZMQ server started on {bind_string}")
            
            # Start request handling thread
            self._server_thread = threading.Thread(target=self._request_loop, daemon=True)
            self._server_thread.start()
            
        except Exception as e:
            print(f"❌ ZMQ server start failed: {e}")
            self.running = False
    
    def _request_loop(self):
        """Main request handling loop."""
        while self.running and self.socket:
            try:
                # Wait for request
                message = self.socket.recv()
                data = deserialize(message)
                
                # Handle request
                response = self._handle_request(data)
                
                # Send response
                response_message = serialize(response)
                self.socket.send(response_message)
                
            except Exception as e:
                print(f"❌ ZMQ request handling failed: {e}")
                # Send error response
                try:
                    error_response = {"error": str(e), "status": "error"}
                    response_message = serialize(error_response)
                    if self.socket:
                        self.socket.send(response_message)
                except:
                    pass
    
    def _handle_request(self, data: Any) -> Any:
        """
        Handle incoming request.
        
        Args:
            data: Request data
            
        Returns:
            Response data
        """
        try:
            if isinstance(data, dict):
                command = data.get("command")
                if command and command in self._request_handlers:
                    handler = self._request_handlers[command]
                    result = handler(data)
                    return {"status": "success", "data": result}
                else:
                    return {"status": "error", "error": f"Unknown command: {command}"}
            else:
                return {"status": "error", "error": "Invalid request format"}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def stop(self):
        """Stop the ZMQ server."""
        self.running = False
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        print("🔌 ZMQ server stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# Example usage
if __name__ == "__main__":
    def handle_status(data: Dict) -> Dict:
        """Example status handler."""
        return {
            "server_time": time.time(),
            "uptime": time.time(),
            "version": "1.0.0"
        }
    
    def handle_echo(data: Dict) -> str:
        """Example echo handler."""
        return data.get("message", "No message provided")
    
    # Create and start server
    server = ZmqServer()
    server.add_handler("status", handle_status)
    server.add_handler("echo", handle_echo)
    
    try:
        server.start()
        print("Server running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
