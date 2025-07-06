"""
AirSim Safety Management

This module handles safety monitoring, violation detection, and emergency
procedures for the AirSim interface.
"""

import asyncio
import logging
import time
from typing import Optional

import airsim
import numpy as np

from common.types import DroneState


class AirSimSafetyManager:
    """Manages safety monitoring and emergency procedures"""
    
    def __init__(self, config):
        self.config = config
        self._safety_violations: int = 0
        self._last_safety_check: float = 0.0
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config.log_level)
    
    async def monitor_safety(self, state: DroneState, client: airsim.MultirotorClient) -> None:
        """
        Monitor safety conditions and trigger failsafes if needed
        
        Args:
            state: Current drone state
            client: AirSim client for emergency commands
        """
        current_time = time.time()
        
        # Check velocity limits
        velocity_mag = np.linalg.norm(state.velocity)
        if velocity_mag > self.config.max_velocity:
            self._safety_violations += 1
            self.logger.warning(
                f"⚠️ Velocity limit exceeded: {velocity_mag:.2f} > {self.config.max_velocity:.2f} m/s"
            )
        
        # Check altitude (negative Z in NED)
        altitude = -state.position[2]
        if altitude < -1.0:  # Below ground
            self._safety_violations += 1
            self.logger.warning(f"⚠️ Below ground level: altitude={altitude:.2f}m")
        
        if altitude > 100.0:  # Too high
            self._safety_violations += 1
            self.logger.warning(f"⚠️ Altitude too high: {altitude:.2f}m")
        
        # Check for excessive safety violations
        if self._safety_violations > 10:
            self.logger.error("❌ Too many safety violations - initiating emergency landing")
            await self.emergency_land(client)
        
        self._last_safety_check = current_time
    
    async def emergency_land(self, client: airsim.MultirotorClient) -> None:
        """Emergency landing procedure"""
        self.logger.error("🚨 EMERGENCY LANDING INITIATED")
        
        try:
            # Disable API control to let AirSim's safety systems take over
            client.enableApiControl(False, self.config.vehicle_name)
            
            # Force landing
            await self._perform_landing(client)
            
        except Exception as e:
            self.logger.error(f"❌ Emergency landing failed: {e}")
    
    async def _perform_landing(self, client: airsim.MultirotorClient) -> bool:
        """
        Perform landing procedure
        
        Args:
            client: AirSim client instance
            
        Returns:
            True if landing successful, False otherwise
        """
        try:
            self.logger.info("🛬 Landing...")
            
            await asyncio.wait_for(
                asyncio.create_task(
                    asyncio.to_thread(
                        client.landAsync,
                        timeout_sec=15,
                        vehicle_name=self.config.vehicle_name
                    )
                ),
                timeout=20.0
            )
            
            # Wait for landing to complete
            await asyncio.sleep(2.0)
            
            self.logger.info("✅ Landing successful")
            return True
                
        except asyncio.TimeoutError:
            self.logger.error("❌ Landing timeout")
            return False
        except Exception as e:
            self.logger.error(f"❌ Landing failed: {e}")
            return False
    
    async def takeoff(self, client: airsim.MultirotorClient, altitude: float = 2.0) -> bool:
        """
        Takeoff to specified altitude
        
        Args:
            client: AirSim client instance
            altitude: Target altitude in meters (positive up)
            
        Returns:
            True if takeoff successful, False otherwise
        """
        try:
            self.logger.info(f"🚁 Taking off to {altitude}m altitude")
            
            # Use AirSim's takeoff command
            await asyncio.wait_for(
                asyncio.create_task(
                    asyncio.to_thread(
                        client.takeoffAsync,
                        timeout_sec=20,
                        vehicle_name=self.config.vehicle_name
                    )
                ),
                timeout=25.0
            )
            
            # Move to desired altitude
            await asyncio.wait_for(
                asyncio.create_task(
                    asyncio.to_thread(
                        client.moveToZAsync,
                        -altitude,  # Negative because NED coordinates
                        velocity=2.0,
                        timeout_sec=10.0,
                        vehicle_name=self.config.vehicle_name
                    )
                ),
                timeout=15.0
            )
            
            self.logger.info(f"✅ Takeoff successful: {altitude:.2f}m")
            return True
                
        except asyncio.TimeoutError:
            self.logger.error("❌ Takeoff timeout")
            return False
        except Exception as e:
            self.logger.error(f"❌ Takeoff failed: {e}")
            return False
    
    def get_safety_violations(self) -> int:
        """Get the number of safety violations"""
        return self._safety_violations
    
    def reset_safety_violations(self) -> None:
        """Reset the safety violation count"""
        self._safety_violations = 0
    
    def get_last_safety_check(self) -> float:
        """Get the timestamp of the last safety check"""
        return self._last_safety_check 