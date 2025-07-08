import asyncio
import logging
import time
from typing import Callable, Optional
from dataclasses import dataclass

@dataclass
class HeartbeatConfig:
    """Configuration for heartbeat monitoring"""
    heartbeat_interval_ms: int = 100  # Send heartbeat every 100ms
    timeout_ms: int = 500  # Trigger emergency after 500ms without heartbeat
    emergency_callback: Optional[Callable] = None
    
    @classmethod
    def from_central_config(cls):
        """Create HeartbeatConfig from centralized configuration."""
        from dart_planner.config.settings import get_config
        config = get_config()
        heartbeat_config = config.get_heartbeat_config()
        return cls(
            heartbeat_interval_ms=heartbeat_config.interval_ms,
            timeout_ms=heartbeat_config.timeout_ms
        )

class HeartbeatMonitor:
    """
    Asyncio-compatible heartbeat monitor for communication links.
    Monitors heartbeat loss and triggers emergency procedures.
    """
    
    def __init__(self, config: HeartbeatConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._last_heartbeat_received = time.time()
        self._last_heartbeat_sent = time.time()
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
    def start_monitoring(self):
        """Start the heartbeat monitoring task"""
        if self._monitoring:
            return
            
        self._monitoring = True
        # Create task in the current event loop
        try:
            loop = asyncio.get_running_loop()
            self._monitor_task = loop.create_task(self._monitor_loop())
        except RuntimeError:
            # No event loop running, create a new one
            self._monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info(f"🔔 Heartbeat monitoring started (timeout: {self.config.timeout_ms}ms)")
        
    def stop_monitoring(self):
        """Stop the heartbeat monitoring task"""
        self._monitoring = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        self.logger.info("🔔 Heartbeat monitoring stopped")
        
    async def heartbeat_received(self):
        """Mark that a heartbeat was received"""
        async with self._lock:
            self._last_heartbeat_received = time.time()
            
    async def heartbeat_sent(self):
        """Mark that a heartbeat was sent"""
        async with self._lock:
            self._last_heartbeat_sent = time.time()
            
    def heartbeat_received_sync(self):
        """Synchronous version for compatibility"""
        self._last_heartbeat_received = time.time()
            
    def heartbeat_sent_sync(self):
        """Synchronous version for compatibility"""
        self._last_heartbeat_sent = time.time()
            
    async def _monitor_loop(self):
        """Main monitoring loop - runs as asyncio task"""
        while self._monitoring:
            current_time = time.time()
            
            async with self._lock:
                time_since_last_heartbeat = (current_time - self._last_heartbeat_received) * 1000
                
            if time_since_last_heartbeat > self.config.timeout_ms:
                self.logger.error(f"🚨 HEARTBEAT LOST! {time_since_last_heartbeat:.1f}ms since last heartbeat")
                self._trigger_emergency()
                break
                
            await asyncio.sleep(0.01)  # Check every 10ms
            
    def _trigger_emergency(self):
        """Trigger emergency procedure"""
        self.logger.critical("🚨 EMERGENCY: Heartbeat timeout exceeded - triggering emergency landing")
        if self.config.emergency_callback:
            try:
                self.config.emergency_callback()
            except Exception as e:
                self.logger.error(f"❌ Emergency callback failed: {e}")
        else:
            self.logger.warning("⚠️ No emergency callback configured")
            
    def get_status(self) -> dict:
        """Get current heartbeat status"""
        current_time = time.time()
        return {
            "monitoring": self._monitoring,
            "time_since_last_received_ms": (current_time - self._last_heartbeat_received) * 1000,
            "time_since_last_sent_ms": (current_time - self._last_heartbeat_sent) * 1000,
            "timeout_ms": self.config.timeout_ms,
        }

class HeartbeatMessage:
    """Standard heartbeat message format"""
    
    def __init__(self, sender_id: str, timestamp: Optional[float] = None):
        self.sender_id = sender_id
        self.timestamp = timestamp or time.time()
        
    def to_dict(self):
        return {
            "type": "heartbeat",
            "sender_id": self.sender_id,
            "timestamp": self.timestamp,
        }
        
    @classmethod
    def from_dict(cls, data: dict):
        if data.get("type") != "heartbeat":
            from dart_planner.common.errors import CommunicationError
            raise CommunicationError("Not a heartbeat message")
        return cls(
            sender_id=data["sender_id"],
            timestamp=data["timestamp"]
        ) 
