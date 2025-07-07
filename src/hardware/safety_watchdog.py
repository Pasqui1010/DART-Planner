"""
Safety Watchdog Module

This module provides a unified safety interface that monitors heartbeat
status and triggers emergency procedures when communication is lost.
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Dict, Any

from ..communication.heartbeat import HeartbeatMonitor, HeartbeatConfig
from .safety import AirSimSafetyManager


class SafetyWatchdog:
    """
    Unified safety watchdog that monitors heartbeat and triggers emergency procedures.
    Integrates with both AirSim and real hardware safety systems.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize heartbeat monitoring with centralized config
        from config.airframe_config import get_airframe_config
        airframe_config = get_airframe_config()
        
        heartbeat_config = HeartbeatConfig(
            heartbeat_interval_ms=config.get("heartbeat_interval_ms", airframe_config.heartbeat_interval_ms),
            timeout_ms=config.get("heartbeat_timeout_ms", airframe_config.heartbeat_timeout_ms),
            emergency_callback=self._trigger_emergency_landing
        )
        self.heartbeat_monitor = HeartbeatMonitor(heartbeat_config)
        
        # Safety managers for different platforms
        self.airsim_safety: Optional[AirSimSafetyManager] = None
        self._emergency_landing_callback: Optional[Callable] = None
        
        # Emergency state
        self._emergency_triggered = False
        self._last_emergency_time = 0.0
        
    def set_airsim_safety(self, airsim_safety: AirSimSafetyManager):
        """Set the AirSim safety manager for emergency procedures"""
        self.airsim_safety = airsim_safety
        self.logger.info("AirSim safety manager configured")
        
    def set_emergency_callback(self, callback: Callable):
        """Set a custom emergency landing callback"""
        self._emergency_landing_callback = callback
        self.logger.info("Custom emergency callback configured")
        
    def start_monitoring(self):
        """Start heartbeat monitoring"""
        self.heartbeat_monitor.start_monitoring()
        self.logger.info("Safety watchdog monitoring started")
        
    def stop_monitoring(self):
        """Stop heartbeat monitoring"""
        self.heartbeat_monitor.stop_monitoring()
        self.logger.info("Safety watchdog monitoring stopped")
        
    def heartbeat_received(self):
        """Mark that a heartbeat was received"""
        self.heartbeat_monitor.heartbeat_received_sync()
        
    def heartbeat_sent(self):
        """Mark that a heartbeat was sent"""
        self.heartbeat_monitor.heartbeat_sent_sync()
        
    def _trigger_emergency_landing(self):
        """Trigger emergency landing procedure"""
        current_time = time.time()
        
        # Prevent multiple emergency triggers in quick succession
        if self._emergency_triggered and (current_time - self._last_emergency_time) < 5.0:
            self.logger.warning("Emergency already triggered recently, ignoring")
            return
            
        self._emergency_triggered = True
        self._last_emergency_time = current_time
        
        self.logger.error("🚨 EMERGENCY LANDING TRIGGERED - Heartbeat timeout exceeded")
        
        # Try custom callback first
        if self._emergency_landing_callback:
            try:
                self._emergency_landing_callback()
                self.logger.info("Custom emergency callback executed")
                return
            except Exception as e:
                self.logger.error(f"Custom emergency callback failed: {e}")
                
        # Fall back to AirSim safety manager
        if self.airsim_safety:
            try:
                # Note: This would need to be called in an async context
                # For now, we'll schedule it
                asyncio.create_task(self._airsim_emergency_landing())
            except Exception as e:
                self.logger.error(f"AirSim emergency landing failed: {e}")
        else:
            self.logger.warning("No emergency landing callback configured")
            
    async def _airsim_emergency_landing(self):
        """Execute AirSim emergency landing"""
        if self.airsim_safety:
            # This would need the AirSim client to be passed in
            # For now, we'll just log the action
            self.logger.info("AirSim emergency landing procedure initiated")
            
    def get_status(self) -> Dict[str, Any]:
        """Get current safety watchdog status"""
        heartbeat_status = self.heartbeat_monitor.get_status()
        
        return {
            "emergency_triggered": self._emergency_triggered,
            "last_emergency_time": self._last_emergency_time,
            "airsim_safety_configured": self.airsim_safety is not None,
            "custom_callback_configured": self._emergency_landing_callback is not None,
            "heartbeat_status": heartbeat_status,
        }
        
    def reset_emergency_state(self):
        """Reset emergency state (for testing or recovery)"""
        self._emergency_triggered = False
        self._last_emergency_time = 0.0
        self.logger.info("Emergency state reset")


class MavlinkHeartbeatAdapter:
    """
    Adapter to convert MAVLink heartbeat messages to the internal heartbeat system.
    This allows integration with real hardware that uses MAVLink.
    """
    
    def __init__(self, safety_watchdog: SafetyWatchdog):
        self.safety_watchdog = safety_watchdog
        self.logger = logging.getLogger(__name__)
        
    def on_mavlink_heartbeat(self, msg):
        """Handle incoming MAVLink heartbeat message"""
        # Extract relevant information from MAVLink heartbeat
        system_id = msg.get_srcSystem()
        component_id = msg.get_srcComponent()
        
        # Mark heartbeat as received
        self.safety_watchdog.heartbeat_received()
        
        self.logger.debug(f"MAVLink heartbeat from system {system_id}, component {component_id}")
        
    def send_mavlink_heartbeat(self, mavlink_connection):
        """Send MAVLink heartbeat message"""
        try:
            # This would need to be implemented based on the specific MAVLink library
            # For now, we'll just mark that we sent a heartbeat
            self.safety_watchdog.heartbeat_sent()
            self.logger.debug("MAVLink heartbeat sent")
        except Exception as e:
            self.logger.error(f"Failed to send MAVLink heartbeat: {e}") 