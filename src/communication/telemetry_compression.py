"""
Telemetry Compression System for DART-Planner

Provides efficient compression and serialization of telemetry data for:
- WebSocket binary transmission
- HTTP gzip compression
- Bandwidth optimization
- Real-time performance
"""

import gzip
import json
import struct
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Tuple
import numpy as np


class CompressionType(Enum):
    """Supported compression types"""
    NONE = "none"
    GZIP = "gzip"
    BINARY = "binary"
    BINARY_GZIP = "binary_gzip"


@dataclass
class TelemetryPacket:
    """Optimized telemetry packet structure"""
    timestamp: float
    packet_type: str
    data: Union[Dict[str, Any], bytes]
    compression: CompressionType = CompressionType.NONE
    sequence_id: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp,
            "packet_type": self.packet_type,
            "data": self.data if isinstance(self.data, dict) else self.data.hex(),
            "compression": self.compression.value,
            "sequence_id": self.sequence_id
        }


class TelemetryCompressor:
    """
    High-performance telemetry compression and serialization
    
    Features:
    - Gzip compression for HTTP responses
    - Binary serialization for WebSocket efficiency
    - Configurable compression levels
    - Automatic format detection
    """
    
    def __init__(self, compression_level: int = 6, enable_binary: bool = True):
        """
        Initialize telemetry compressor
        
        Args:
            compression_level: Gzip compression level (1-9, higher = smaller but slower)
            enable_binary: Enable binary serialization for WebSocket
        """
        self.compression_level = max(1, min(9, compression_level))
        self.enable_binary = enable_binary
        self.sequence_counter = 0
        
        # Pre-allocated buffers for performance
        self._gzip_buffer = bytearray(4096)
        self._binary_buffer = bytearray(2048)
        
        # Binary format definitions
        self._binary_formats = {
            'position': '3f',      # 3 floats (x, y, z)
            'velocity': '3f',      # 3 floats (vx, vy, vz)
            'attitude': '3f',      # 3 floats (roll, pitch, yaw)
            'timestamp': 'd',      # 1 double
            'battery': '2f',       # 2 floats (voltage, remaining)
            'gps': '3d',           # 3 doubles (lat, lon, alt)
            'status': 'B',         # 1 byte (status code)
        }
        
        print(f"🚀 TelemetryCompressor initialized (level={compression_level}, binary={enable_binary})")
    
    def compress_telemetry(self, 
                          telemetry_data: Dict[str, Any], 
                          compression_type: CompressionType = CompressionType.GZIP,
                          packet_type: str = "telemetry") -> TelemetryPacket:
        """
        Compress telemetry data for efficient transmission
        
        Args:
            telemetry_data: Raw telemetry data dictionary
            compression_type: Type of compression to apply
            packet_type: Type of telemetry packet
            
        Returns:
            Compressed telemetry packet
        """
        self.sequence_counter += 1
        timestamp = time.time()
        
        if compression_type == CompressionType.NONE:
            return TelemetryPacket(
                timestamp=timestamp,
                packet_type=packet_type,
                data=telemetry_data,
                compression=compression_type,
                sequence_id=self.sequence_counter
            )
        
        elif compression_type == CompressionType.GZIP:
            compressed_data = self._compress_gzip(telemetry_data)
            return TelemetryPacket(
                timestamp=timestamp,
                packet_type=packet_type,
                data=compressed_data,
                compression=compression_type,
                sequence_id=self.sequence_counter
            )
        
        elif compression_type == CompressionType.BINARY:
            binary_data = self._serialize_binary(telemetry_data)
            return TelemetryPacket(
                timestamp=timestamp,
                packet_type=packet_type,
                data=binary_data,
                compression=compression_type,
                sequence_id=self.sequence_counter
            )
        
        elif compression_type == CompressionType.BINARY_GZIP:
            binary_data = self._serialize_binary(telemetry_data)
            compressed_binary = self._compress_gzip_bytes(binary_data)
            return TelemetryPacket(
                timestamp=timestamp,
                packet_type=packet_type,
                data=compressed_binary,
                compression=compression_type,
                sequence_id=self.sequence_counter
            )
        
        else:
            raise ValueError(f"Unsupported compression type: {compression_type}")
    
    def decompress_telemetry(self, packet: TelemetryPacket) -> Dict[str, Any]:
        """
        Decompress telemetry packet back to original data
        
        Args:
            packet: Compressed telemetry packet
            
        Returns:
            Decompressed telemetry data
        """
        if packet.compression == CompressionType.NONE:
            return packet.data if isinstance(packet.data, dict) else {}
        
        elif packet.compression == CompressionType.GZIP:
            return self._decompress_gzip(packet.data)
        
        elif packet.compression == CompressionType.BINARY:
            return self._deserialize_binary(packet.data)
        
        elif packet.compression == CompressionType.BINARY_GZIP:
            decompressed_binary = self._decompress_gzip_bytes(packet.data)
            return self._deserialize_binary(decompressed_binary)
        
        else:
            raise ValueError(f"Unsupported compression type: {packet.compression}")
    
    def _compress_gzip(self, data: Dict[str, Any]) -> bytes:
        """Compress dictionary data using gzip"""
        json_str = json.dumps(data, separators=(',', ':'))  # Compact JSON
        return gzip.compress(json_str.encode('utf-8'), compresslevel=self.compression_level)
    
    def _decompress_gzip(self, compressed_data: bytes) -> Dict[str, Any]:
        """Decompress gzip data back to dictionary"""
        json_str = gzip.decompress(compressed_data).decode('utf-8')
        return json.loads(json_str)
    
    def _compress_gzip_bytes(self, data: bytes) -> bytes:
        """Compress binary data using gzip"""
        return gzip.compress(data, compresslevel=self.compression_level)
    
    def _decompress_gzip_bytes(self, compressed_data: bytes) -> bytes:
        """Decompress gzip binary data"""
        return gzip.decompress(compressed_data)
    
    def _serialize_binary(self, data: Dict[str, Any]) -> bytes:
        """Serialize telemetry data to compact binary format"""
        binary_parts = []
        
        # Header: packet type length + packet type
        packet_type_bytes = data.get('packet_type', 'telemetry').encode('utf-8')
        binary_parts.append(struct.pack('B', len(packet_type_bytes)))
        binary_parts.append(packet_type_bytes)
        
        # Timestamp
        timestamp = data.get('timestamp', time.time())
        binary_parts.append(struct.pack('d', timestamp))
        
        # Position data (if available)
        if 'position' in data:
            pos = data['position']
            if isinstance(pos, (list, tuple, np.ndarray)):
                binary_parts.append(struct.pack('3f', float(pos[0]), float(pos[1]), float(pos[2])))
            elif isinstance(pos, dict):
                binary_parts.append(struct.pack('3f', pos.get('x', 0.0), pos.get('y', 0.0), pos.get('z', 0.0)))
        
        # Velocity data (if available)
        if 'velocity' in data:
            vel = data['velocity']
            if isinstance(vel, (list, tuple, np.ndarray)):
                binary_parts.append(struct.pack('3f', float(vel[0]), float(vel[1]), float(vel[2])))
            elif isinstance(vel, dict):
                binary_parts.append(struct.pack('3f', vel.get('x', 0.0), vel.get('y', 0.0), vel.get('z', 0.0)))
        
        # Attitude data (if available)
        if 'attitude' in data:
            att = data['attitude']
            if isinstance(att, (list, tuple, np.ndarray)):
                binary_parts.append(struct.pack('3f', float(att[0]), float(att[1]), float(att[2])))
            elif isinstance(att, dict):
                binary_parts.append(struct.pack('3f', att.get('roll', 0.0), att.get('pitch', 0.0), att.get('yaw', 0.0)))
        
        # Battery data (if available)
        if 'battery_voltage' in data or 'battery_remaining' in data:
            voltage = data.get('battery_voltage', 0.0)
            remaining = data.get('battery_remaining', 0.0)
            binary_parts.append(struct.pack('2f', voltage, remaining))
        
        # GPS data (if available)
        if 'gps' in data:
            gps = data['gps']
            if isinstance(gps, dict):
                lat = gps.get('latitude', 0.0)
                lon = gps.get('longitude', 0.0)
                alt = gps.get('altitude', 0.0)
                binary_parts.append(struct.pack('3d', lat, lon, alt))
        
        # System status (if available)
        if 'system_status' in data:
            status_code = self._encode_status(data['system_status'])
            binary_parts.append(struct.pack('B', status_code))
        
        # Performance metrics (if available)
        if 'performance' in data:
            perf = data['performance']
            if isinstance(perf, dict):
                planning_time = perf.get('avg_planning_time_ms', 0.0)
                operation_time = perf.get('autonomous_operation_time_s', 0.0)
                binary_parts.append(struct.pack('2f', planning_time, operation_time))
        
        return b''.join(binary_parts)
    
    def _deserialize_binary(self, binary_data: bytes) -> Dict[str, Any]:
        """Deserialize binary data back to dictionary"""
        data = {}
        offset = 0
        
        # Read packet type
        if len(binary_data) > offset:
            type_len = struct.unpack('B', binary_data[offset:offset+1])[0]
            offset += 1
            if len(binary_data) >= offset + type_len:
                packet_type = binary_data[offset:offset+type_len].decode('utf-8')
                data['packet_type'] = packet_type
                offset += type_len
        
        # Read timestamp
        if len(binary_data) >= offset + 8:
            timestamp = struct.unpack('d', binary_data[offset:offset+8])[0]
            data['timestamp'] = timestamp
            offset += 8
        
        # Read position (if present)
        if len(binary_data) >= offset + 12:
            x, y, z = struct.unpack('3f', binary_data[offset:offset+12])
            data['position'] = {'x': x, 'y': y, 'z': z}
            offset += 12
        
        # Read velocity (if present)
        if len(binary_data) >= offset + 12:
            vx, vy, vz = struct.unpack('3f', binary_data[offset:offset+12])
            data['velocity'] = {'x': vx, 'y': vy, 'z': vz}
            offset += 12
        
        # Read attitude (if present)
        if len(binary_data) >= offset + 12:
            roll, pitch, yaw = struct.unpack('3f', binary_data[offset:offset+12])
            data['attitude'] = {'roll': roll, 'pitch': pitch, 'yaw': yaw}
            offset += 12
        
        # Read battery (if present)
        if len(binary_data) >= offset + 8:
            voltage, remaining = struct.unpack('2f', binary_data[offset:offset+8])
            data['battery_voltage'] = voltage
            data['battery_remaining'] = remaining
            offset += 8
        
        # Read GPS (if present)
        if len(binary_data) >= offset + 24:
            lat, lon, alt = struct.unpack('3d', binary_data[offset:offset+24])
            data['gps'] = {'latitude': lat, 'longitude': lon, 'altitude': alt}
            offset += 24
        
        # Read status (if present)
        if len(binary_data) >= offset + 1:
            status_code = struct.unpack('B', binary_data[offset:offset+1])[0]
            data['system_status'] = self._decode_status(status_code)
            offset += 1
        
        # Read performance (if present)
        if len(binary_data) >= offset + 8:
            planning_time, operation_time = struct.unpack('2f', binary_data[offset:offset+8])
            data['performance'] = {
                'avg_planning_time_ms': planning_time,
                'autonomous_operation_time_s': operation_time
            }
        
        return data
    
    def _encode_status(self, status: str) -> int:
        """Encode system status string to byte code"""
        status_codes = {
            'idle': 0,
            'arming': 1,
            'armed': 2,
            'takeoff': 3,
            'mission': 4,
            'landing': 5,
            'emergency': 6,
            'error': 7
        }
        return status_codes.get(status.lower(), 0)
    
    def _decode_status(self, status_code: int) -> str:
        """Decode byte code back to system status string"""
        status_strings = {
            0: 'idle',
            1: 'arming',
            2: 'armed',
            3: 'takeoff',
            4: 'mission',
            5: 'landing',
            6: 'emergency',
            7: 'error'
        }
        return status_strings.get(status_code, 'unknown')
    
    def get_compression_stats(self, original_data: Dict[str, Any], compressed_packet: TelemetryPacket) -> Dict[str, Any]:
        """Get compression statistics"""
        original_size = len(json.dumps(original_data, separators=(',', ':')).encode('utf-8'))
        compressed_size = len(compressed_packet.data) if isinstance(compressed_packet.data, bytes) else len(json.dumps(compressed_packet.data, separators=(',', ':')).encode('utf-8'))
        
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        return {
            'original_size_bytes': original_size,
            'compressed_size_bytes': compressed_size,
            'compression_ratio_percent': round(compression_ratio, 2),
            'compression_type': compressed_packet.compression.value,
            'packet_type': compressed_packet.packet_type
        }


class WebSocketTelemetryManager:
    """
    WebSocket-specific telemetry manager with binary support
    """
    
    def __init__(self, compressor: Optional[TelemetryCompressor] = None):
        self.compressor = compressor or TelemetryCompressor(enable_binary=True)
        self.client_preferences = {}  # Track client compression preferences
    
    def set_client_preference(self, client_id: str, compression_type: CompressionType):
        """Set compression preference for specific client"""
        self.client_preferences[client_id] = compression_type
    
    def prepare_websocket_telemetry(self, 
                                  telemetry_data: Dict[str, Any], 
                                  client_id: Optional[str] = None,
                                  force_binary: bool = False) -> Union[Dict[str, Any], bytes]:
        """
        Prepare telemetry for WebSocket transmission
        
        Args:
            telemetry_data: Raw telemetry data
            client_id: Client identifier for preference lookup
            force_binary: Force binary format regardless of client preference
            
        Returns:
            Telemetry data ready for WebSocket transmission
        """
        if force_binary or (client_id and self.client_preferences.get(client_id) == CompressionType.BINARY):
            # Use binary format for maximum efficiency
            packet = self.compressor.compress_telemetry(
                telemetry_data, 
                CompressionType.BINARY
            )
            return packet.data
        
        elif client_id and self.client_preferences.get(client_id) == CompressionType.BINARY_GZIP:
            # Use compressed binary for bandwidth optimization
            packet = self.compressor.compress_telemetry(
                telemetry_data, 
                CompressionType.BINARY_GZIP
            )
            return packet.data
        
        else:
            # Use JSON format for compatibility
            packet = self.compressor.compress_telemetry(
                telemetry_data, 
                CompressionType.NONE
            )
            return packet.to_dict()
    
    def handle_websocket_message(self, message: Union[str, bytes], client_id: str) -> Dict[str, Any]:
        """
        Handle incoming WebSocket message and detect compression format
        
        Args:
            message: Incoming WebSocket message
            client_id: Client identifier
            
        Returns:
            Decoded message data
        """
        if isinstance(message, bytes):
            # Binary message - try to decompress
            try:
                packet = TelemetryPacket(
                    timestamp=time.time(),
                    packet_type="unknown",
                    data=message,
                    compression=CompressionType.BINARY
                )
                return self.compressor.decompress_telemetry(packet)
            except Exception:
                # Fallback to raw binary data
                return {"raw_binary": message.hex()}
        
        elif isinstance(message, str):
            # JSON message
            try:
                data = json.loads(message)
                if isinstance(data, dict) and 'compression' in data:
                    # Structured packet with compression info
                    packet = TelemetryPacket(**data)
                    return self.compressor.decompress_telemetry(packet)
                else:
                    # Plain JSON data
                    return data
            except json.JSONDecodeError:
                return {"error": "Invalid JSON format"}
        
        else:
            return {"error": "Unsupported message type"}


# Convenience functions for common use cases

def compress_telemetry_gzip(telemetry_data: Dict[str, Any]) -> bytes:
    """Quick gzip compression for HTTP responses"""
    compressor = TelemetryCompressor()
    packet = compressor.compress_telemetry(telemetry_data, CompressionType.GZIP)
    return packet.data

def compress_telemetry_binary(telemetry_data: Dict[str, Any]) -> bytes:
    """Quick binary serialization for WebSocket"""
    compressor = TelemetryCompressor()
    packet = compressor.compress_telemetry(telemetry_data, CompressionType.BINARY)
    return packet.data

def decompress_telemetry_gzip(compressed_data: bytes) -> Dict[str, Any]:
    """Quick gzip decompression"""
    compressor = TelemetryCompressor()
    packet = TelemetryPacket(
        timestamp=time.time(),
        packet_type="telemetry",
        data=compressed_data,
        compression=CompressionType.GZIP
    )
    return compressor.decompress_telemetry(packet) 