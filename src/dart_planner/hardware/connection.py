"""
AirSim Connection Management

This module handles connection establishment, initialization, and cleanup
for the AirSim interface.
"""

import asyncio
import logging
from typing import Optional

import airsim

from .state import AirSimConfig


class AirSimConnection:
    """Manages AirSim client connection and vehicle initialization"""
    
    def __init__(self, config: AirSimConfig):
        self.config = config
        self.client: Optional[airsim.MultirotorClient] = None
        self.connected: bool = False
        self.armed: bool = False
        self.api_control_enabled: bool = False
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config.log_level)
    
    async def connect(self) -> bool:
        """
        Connect to AirSim simulator
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to AirSim at {self.config.ip}:{self.config.port}")
            
            self.client = airsim.MultirotorClient(
                ip=self.config.ip,
                port=self.config.port,
                timeout_value=self.config.timeout_value
            )
            
            # Test connection with ping
            self.client.ping()
            self.connected = True
            
            # Get initial state
            await self._initialize_vehicle()
            
            self.logger.info("✅ AirSim connection established")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to AirSim: {e}")
            self.connected = False
            return False
    
    async def _initialize_vehicle(self) -> None:
        """Initialize vehicle settings and API control"""
        if not self.client:
            from dart_planner.common.errors import HardwareError
            raise HardwareError("Client not connected")
        
        try:
            # Enable API control
            if self.config.enable_api_control:
                self.client.enableApiControl(True, self.config.vehicle_name)
                self.api_control_enabled = True
                self.logger.info("✅ API control enabled")
            
            # Arm the vehicle
            self.client.armDisarm(True, self.config.vehicle_name)
            self.armed = True
            self.logger.info("✅ Vehicle armed")
            
            # Reset vehicle to known state
            self.client.reset()
            await asyncio.sleep(0.1)  # Brief pause for state reset
            
        except Exception as e:
            self.logger.error(f"❌ Vehicle initialization failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Safely disconnect from AirSim"""
        try:
            if self.client and self.connected:
                # Disable API control
                if self.api_control_enabled:
                    self.client.enableApiControl(False, self.config.vehicle_name)
                    self.api_control_enabled = False
                
                # Disarm
                if self.armed:
                    self.client.armDisarm(False, self.config.vehicle_name)
                    self.armed = False
                
                self.client = None
                self.connected = False
                
                self.logger.info("✅ AirSim disconnected safely")
                
        except Exception as e:
            self.logger.error(f"❌ Error during disconnect: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to AirSim"""
        return self.connected and self.client is not None
    
    def is_armed(self) -> bool:
        """Check if vehicle is armed"""
        return self.armed
    
    def is_api_control_enabled(self) -> bool:
        """Check if API control is enabled"""
        return self.api_control_enabled
    
    def get_client(self) -> Optional[airsim.MultirotorClient]:
        """Get the AirSim client instance"""
        return self.client 
