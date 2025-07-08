#!/usr/bin/env python3
"""
Minimal Takeoff Demo for DART-Planner

This script demonstrates a complete happy path using:
- VehicleIO factory pattern
- SE3MPCPlanner factory pattern  
- SimulatedAdapter for testing
- Full takeoff sequence

Usage:
    python -m dart_planner.minimal_takeoff [--mock] [--altitude 5.0]
"""

import asyncio
import argparse
import logging
import sys
import time
from typing import Optional

from .hardware.vehicle_io import VehicleIOFactory, VehicleIO
from .common.di_container import get_container
from .common.types import DroneState


class MinimalTakeoff:
    """Minimal takeoff demonstration using factory patterns."""
    
    def __init__(self, mock_mode: bool = True, target_altitude: float = 5.0):
        self.mock_mode = mock_mode
        self.target_altitude = target_altitude
        self.logger = logging.getLogger(__name__)
        self.vehicle_io: Optional[VehicleIO] = None
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def initialize(self) -> bool:
        """Initialize the system using factory patterns."""
        try:
            # Get DI container
            container = get_container()
            
            # Create vehicle I/O via factory
            if self.mock_mode:
                config = {
                    "adapter": "simulated",
                    "update_rate": 50.0,
                    "mock_mode": True
                }
                self.vehicle_io = VehicleIOFactory.create("simulated", config)
                self.logger.info("Created simulated vehicle I/O via factory")
            else:
                # For real hardware, would use different adapter
                config = {
                    "adapter": "pixhawk",
                    "connection": "/dev/ttyACM0",
                    "baudrate": 115200
                }
                self.vehicle_io = VehicleIOFactory.create("pixhawk", config)
                self.logger.info("Created Pixhawk vehicle I/O via factory")
            
            # Verify planner is available via factory
            planner_container = container.create_planner_container()
            planner = planner_container.get_se3_planner()
            if planner:
                self.logger.info("SE3MPCPlanner available via factory")
            else:
                self.logger.warning("SE3MPCPlanner not available via factory")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False
    
    async def connect_vehicle(self) -> bool:
        """Connect to the vehicle."""
        if not self.vehicle_io:
            self.logger.error("Vehicle I/O not initialized")
            return False
        
        try:
            connected = await self.vehicle_io.connect()
            if connected:
                self.logger.info("Successfully connected to vehicle")
                return True
            else:
                self.logger.error("Failed to connect to vehicle")
                return False
        except Exception as e:
            self.logger.error(f"Error connecting to vehicle: {e}")
            return False
    
    async def get_vehicle_status(self) -> None:
        """Get and display vehicle status."""
        if not self.vehicle_io:
            return
        
        try:
            status = self.vehicle_io.get_status()
            self.logger.info(f"Vehicle status: {status}")
            
            # Get current state
            state = await self.vehicle_io.get_state()
            if state:
                self.logger.info(f"Current position: {state.position}")
                self.logger.info(f"Current velocity: {state.velocity}")
                self.logger.info(f"Attitude: {state.attitude}")
                self.logger.info(f"Timestamp: {state.timestamp}")
            
        except Exception as e:
            self.logger.error(f"Error getting vehicle status: {e}")
    
    async def execute_takeoff_sequence(self) -> bool:
        """Execute the complete takeoff sequence."""
        if not self.vehicle_io:
            self.logger.error("Vehicle I/O not initialized")
            return False
        
        try:
            self.logger.info("Starting takeoff sequence...")
            
            # Step 1: Get initial status
            await self.get_vehicle_status()
            
            # Step 2: Arm the vehicle
            self.logger.info("Arming vehicle...")
            armed = await self.vehicle_io.arm()
            if not armed:
                self.logger.error("Failed to arm vehicle")
                return False
            self.logger.info("Vehicle armed successfully")
            
            # Step 3: Set to GUIDED mode
            self.logger.info("Setting to GUIDED mode...")
            mode_set = await self.vehicle_io.set_mode("GUIDED")
            if not mode_set:
                self.logger.warning("Failed to set GUIDED mode, continuing...")
            
            # Step 4: Execute takeoff
            self.logger.info(f"Executing takeoff to {self.target_altitude}m...")
            takeoff_success = await self.vehicle_io.takeoff(self.target_altitude)
            if not takeoff_success:
                self.logger.error("Failed to execute takeoff")
                return False
            
            # Step 5: Wait for takeoff completion
            self.logger.info("Waiting for takeoff completion...")
            await asyncio.sleep(2.0)  # Give time for takeoff
            
            # Step 6: Verify final position
            await self.get_vehicle_status()
            
            # Step 7: Hover for a moment
            self.logger.info("Hovering for 3 seconds...")
            await asyncio.sleep(3.0)
            
            # Step 8: Land
            self.logger.info("Executing landing...")
            land_success = await self.vehicle_io.land()
            if not land_success:
                self.logger.error("Failed to execute landing")
                return False
            
            # Step 9: Wait for landing completion
            self.logger.info("Waiting for landing completion...")
            await asyncio.sleep(2.0)
            
            # Step 10: Disarm
            self.logger.info("Disarming vehicle...")
            disarmed = await self.vehicle_io.disarm()
            if not disarmed:
                self.logger.warning("Failed to disarm vehicle")
            
            self.logger.info("Takeoff sequence completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during takeoff sequence: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.vehicle_io:
            try:
                await self.vehicle_io.disconnect()
                self.logger.info("Disconnected from vehicle")
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
    
    async def run(self) -> bool:
        """Run the complete minimal takeoff demonstration."""
        try:
            self.logger.info("Starting DART-Planner Minimal Takeoff Demo")
            self.logger.info(f"Mock mode: {self.mock_mode}")
            self.logger.info(f"Target altitude: {self.target_altitude}m")
            
            # Initialize
            if not await self.initialize():
                return False
            
            # Connect
            if not await self.connect_vehicle():
                return False
            
            # Execute takeoff sequence
            success = await self.execute_takeoff_sequence()
            
            # Cleanup
            await self.cleanup()
            
            return success
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            await self.cleanup()
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="DART-Planner Minimal Takeoff Demo")
    parser.add_argument("--mock", action="store_true", default=True,
                       help="Use mock/simulated vehicle (default: True)")
    parser.add_argument("--altitude", type=float, default=5.0,
                       help="Target takeoff altitude in meters (default: 5.0)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run demo
    demo = MinimalTakeoff(mock_mode=args.mock, target_altitude=args.altitude)
    
    # Run the demo
    success = asyncio.run(demo.run())
    
    if success:
        print("SUCCESS: Minimal takeoff demo completed successfully!")
        sys.exit(0)
    else:
        print("FAILED: Minimal takeoff demo failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 
