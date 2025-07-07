"""
Secure Serializer for ZMQ Communication

This module provides secure serialization alternatives to pickle
for ZMQ message passing in DART-Planner.
"""

import json
import base64
import hashlib
import hmac
import os
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class SecureMessage:
    """Secure message wrapper with integrity checking."""
    data: Any
    signature: str
    timestamp: float
    message_id: str


class SecureSerializer:
    """
    Secure serializer that replaces pickle for ZMQ communication.
    
    Features:
    - JSON-based serialization (no code execution)
    - HMAC signature verification
    - Timestamp validation
    - Message ID tracking
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """Initialize serializer with optional secret key."""
        self.secret_key = secret_key or os.getenv("DART_ZMQ_SECRET", "default_zmq_secret")
        self._message_counter = 0
    
    def _generate_message_id(self) -> str:
        """Generate unique message ID."""
        self._message_counter += 1
        return f"msg_{self._message_counter}_{os.getpid()}"
    
    def _sign_data(self, data: str, timestamp: float, message_id: str) -> str:
        """Create HMAC signature for data integrity."""
        message = f"{data}:{timestamp}:{message_id}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _verify_signature(self, data: str, timestamp: float, message_id: str, signature: str) -> bool:
        """Verify HMAC signature."""
        expected_signature = self._sign_data(data, timestamp, message_id)
        return hmac.compare_digest(signature, expected_signature)
    
    def serialize(self, obj: Any) -> bytes:
        """
        Securely serialize an object to bytes.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Serialized bytes with integrity protection
        """
        import time
        
        # Convert numpy arrays to lists for JSON serialization
        if isinstance(obj, np.ndarray):
            obj = obj.tolist()
        elif isinstance(obj, dict):
            obj = self._convert_numpy_in_dict(obj)
        
        # Create secure message
        timestamp = time.time()
        message_id = self._generate_message_id()
        
        # Serialize data to JSON
        data_json = json.dumps(obj, default=self._json_serializer)
        
        # Create signature
        signature = self._sign_data(data_json, timestamp, message_id)
        
        # Create secure message
        secure_msg = SecureMessage(
            data=obj,
            signature=signature,
            timestamp=timestamp,
            message_id=message_id
        )
        
        # Serialize to JSON and encode to bytes
        return json.dumps(asdict(secure_msg), default=self._json_serializer).encode('utf-8')
    
    def deserialize(self, data: bytes) -> Any:
        """
        Securely deserialize bytes to object.
        
        Args:
            data: Serialized bytes
            
        Returns:
            Deserialized object
            
        Raises:
            ValueError: If signature verification fails
            ValueError: If message is too old
        """
        import time
        
        # Decode and parse JSON
        try:
            msg_dict = json.loads(data.decode('utf-8'))
            secure_msg = SecureMessage(**msg_dict)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid message format: {e}")
        
        # Check message age (reject messages older than 5 minutes)
        current_time = time.time()
        if current_time - secure_msg.timestamp > 300:  # 5 minutes
            raise ValueError("Message too old")
        
        # Verify signature
        data_json = json.dumps(secure_msg.data, default=self._json_serializer)
        if not self._verify_signature(data_json, secure_msg.timestamp, secure_msg.message_id, secure_msg.signature):
            raise ValueError("Message signature verification failed")
        
        # Convert back numpy arrays if needed
        result = self._restore_numpy_arrays(secure_msg.data)
        return result
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for numpy arrays and other types."""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _convert_numpy_in_dict(self, obj: Dict) -> Dict:
        """Convert numpy arrays in dictionary to lists."""
        result = {}
        for key, value in obj.items():
            if isinstance(value, np.ndarray):
                result[key] = value.tolist()
            elif isinstance(value, dict):
                result[key] = self._convert_numpy_in_dict(value)
            elif isinstance(value, list):
                result[key] = self._convert_numpy_in_list(value)
            else:
                result[key] = value
        return result
    
    def _convert_numpy_in_list(self, obj: list) -> list:
        """Convert numpy arrays in list to lists."""
        result = []
        for item in obj:
            if isinstance(item, np.ndarray):
                result.append(item.tolist())
            elif isinstance(item, dict):
                result.append(self._convert_numpy_in_dict(item))
            elif isinstance(item, list):
                result.append(self._convert_numpy_in_list(item))
            else:
                result.append(item)
        return result
    
    def _restore_numpy_arrays(self, obj: Any) -> Any:
        """Restore numpy arrays from lists if they were originally arrays."""
        if isinstance(obj, list):
            # Check if this looks like a numpy array (list of numbers)
            if all(isinstance(x, (int, float)) for x in obj):
                return np.array(obj)
            else:
                return [self._restore_numpy_arrays(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._restore_numpy_arrays(value) for key, value in obj.items()}
        else:
            return obj


# Global serializer instance
_serializer = SecureSerializer()


def serialize(obj: Any) -> bytes:
    """Serialize object using secure serializer."""
    return _serializer.serialize(obj)


def deserialize(data: bytes) -> Any:
    """Deserialize bytes using secure serializer."""
    return _serializer.deserialize(data)


def set_secret_key(secret_key: str) -> None:
    """Set secret key for the global serializer."""
    global _serializer
    _serializer = SecureSerializer(secret_key) 