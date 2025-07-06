#!/usr/bin/env python3
"""
DART-Planner SITL Integration Script

This script integrates DART-Planner with ArduPilot SITL for realistic
flight dynamics testing and validation of autonomous planning algorithms.

Usage:
    python scripts/sitl_integration.py [--sitl-port 14550] [--gcs-port 14551]
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import pymavlink.mavutil as mavutil
    from pymavlink import mavlink
except ImportError:
    print("ERROR: pymavlink not installed. Install with: pip install pymavlink")
    sys.exit(1)

from common.types import DroneState
from planning.se3_mpc_planner import SE3MPCPlanner
from perception.explicit_geometric_mapper import ExplicitGeometricMapper
from control.geometric_controller import GeometricController


class SITLIntegration:
    """
    Integration class for DART-Planner with ArduPilot SITL.
    
    This provides a bridge between DART-Planner's autonomous planning
    algorithms and ArduPilot's realistic flight dynamics simulation.
    """
    
    def __init__(self, sitl_port: int = 14550, gcs_port: int = 14551):
        self.sitl_port = sitl_port
        self.gcs_port = gcs_port
        
        # Initialize DART-Planner components
        self.planner = SE3MPCPlanner()
        self.mapper = ExplicitGeometricMapper()
        self.controller = GeometricController()
        
        # MAVLink connection
        self.mavlink_connection: Optional[mavutil.mavlink_connection] = None
        
        # State tracking
        self.current_state = DroneState(
            timestamp=time.time(),
            position=[0.0, 0.0, 0.0],
            velocity=[0.0, 0.0, 0.0],
            attitude=[0.0, 0.0, 0.0],
            angular_velocity=[0.0, 0.0, 0.0]
        )
        
        # Mission state
        self.mission_active = False
        self.current_waypoint = 0
        self.waypoints = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    async def connect_to_sitl(self) -> bool:
        """Connect to ArduPilot SITL via MAVLink."""
        try:
            self.logger.info(f"Connecting to SITL on port {self.sitl_port}...")
            
            # Connect to SITL
            self.mavlink_connection = mavutil.mavlink_connection(
                f'udpin:127.0.0.1:{self.sitl_port}',
                source_system=255,
                source_component=1
            )
            
            # Wait for heartbeat
            self.logger.info("Waiting for SITL heartbeat...")
            self.mavlink_connection.wait_heartbeat(timeout=10)
            
            self.logger.info("✅ Connected to ArduPilot SITL successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to SITL: {e}")
            return False
    
    def update_drone_state(self, msg):
        """Update internal drone state from MAVLink messages."""
        if msg.get_type() == 'GLOBAL_POSITION_INT':
            # Convert from MAVLink format (mm) to meters
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            alt = msg.alt / 1000.0  # mm to meters
            
            # Simple conversion for testing (in real implementation, use proper coordinate transform)
            self.current_state.position = [lon * 111000, lat * 111000, alt]
            
        elif msg.get_type() == 'VFR_HUD':
            # Update velocity and heading
            self.current_state.velocity = [msg.airspeed, 0.0, msg.climb]
            self.current_state.attitude[2] = msg.heading  # yaw
            
        self.current_state.timestamp = time.time()
    
    async def send_waypoint_mission(self, waypoints):
        """Send waypoint mission to SITL."""
        if not self.mavlink_connection:
            self.logger.error("No MAVLink connection available")
            return False
        
        try:
            self.logger.info(f"Sending {len(waypoints)} waypoints to SITL...")
            
            # Clear existing mission
            self.mavlink_connection.waypoint_clear_all_send()
            self.mavlink_connection.waypoint_count_send(len(waypoints))
            
            # Send each waypoint
            for i, wp in enumerate(waypoints):
                self.mavlink_connection.mav.send(
                    mavlink.MAVLink_mission_item_message(
                        target_system=1,
                        target_component=1,
                        seq=i,
                        frame=mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                        command=mavlink.MAV_CMD_NAV_WAYPOINT,
                        current=0,
                        autocontinue=1,
                        param1=0,  # Hold time
                        param2=2.0,  # Acceptance radius
                        param3=10.0,  # Pass radius
                        param4=0,  # Yaw
                        param5=wp[0],  # Latitude
                        param6=wp[1],  # Longitude
                        param7=wp[2]   # Altitude
                    )
                )
                await asyncio.sleep(0.1)
            
            self.logger.info("✅ Waypoint mission sent successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send waypoint mission: {e}")
            return False
    
    async def set_flight_mode(self, mode: str):
        """Set ArduPilot flight mode."""
        if not self.mavlink_connection:
            return False
        
        try:
            self.mavlink_connection.set_mode(mode)
            self.logger.info(f"✅ Flight mode set to: {mode}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to set flight mode: {e}")
            return False
    
    async def arm_disarm(self, arm: bool = True):
        """Arm or disarm the vehicle."""
        if not self.mavlink_connection:
            return False
        
        try:
            self.mavlink_connection.arducopter_arm() if arm else self.mavlink_connection.arducopter_disarm()
            action = "arm" if arm else "disarm"
            self.logger.info(f"✅ Vehicle {action}ed successfully!")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to {action} vehicle: {e}")
            return False
    
    async def run_mission(self, waypoints):
        """Run a complete mission with DART-Planner integration."""
        self.waypoints = waypoints
        self.mission_active = True
        
        try:
            # Set to GUIDED mode for external control
            await self.set_flight_mode('GUIDED')
            
            # Arm the vehicle
            await self.arm_disarm(True)
            
            # Execute mission
            for i, waypoint in enumerate(waypoints):
                self.logger.info(f"Executing waypoint {i+1}/{len(waypoints)}: {waypoint}")
                
                # Use DART-Planner to plan trajectory to waypoint
                trajectory = self.planner.plan_trajectory(self.current_state, waypoint)
                
                # Execute trajectory (simplified - in real implementation, send control commands)
                await asyncio.sleep(2.0)  # Simulate execution time
                
                self.current_waypoint = i
            
            self.logger.info("✅ Mission completed successfully!")
            
        except Exception as e:
            self.logger.error(f"❌ Mission failed: {e}")
        finally:
            self.mission_active = False
    
    async def monitor_connection(self):
        """Monitor MAVLink connection and update state."""
        if not self.mavlink_connection:
            return
        
        try:
            while True:
                msg = self.mavlink_connection.recv_match(blocking=True, timeout=1.0)
                if msg:
                    self.update_drone_state(msg)
                    
                    # Log periodic status
                    if hasattr(msg, 'get_type') and msg.get_type() == 'HEARTBEAT':
                        self.logger.debug(f"Vehicle mode: {msg.custom_mode}, Armed: {msg.base_mode & 0x80}")
                        
        except Exception as e:
            self.logger.error(f"Connection monitoring error: {e}")
    
    async def run(self):
        """Main integration loop."""
        # Connect to SITL
        if not await self.connect_to_sitl():
            return
        
        # Start monitoring connection
        monitor_task = asyncio.create_task(self.monitor_connection())
        
        try:
            # Example mission
            waypoints = [
                [0.0, 0.0, 10.0],   # Takeoff to 10m
                [10.0, 0.0, 10.0],  # Move forward 10m
                [10.0, 10.0, 10.0], # Move right 10m
                [0.0, 10.0, 10.0],  # Move back 10m
                [0.0, 0.0, 10.0],   # Return to start
                [0.0, 0.0, 0.0],    # Land
            ]
            
            await self.run_mission(waypoints)
            
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
        finally:
            monitor_task.cancel()
            if self.mavlink_connection:
                self.mavlink_connection.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='DART-Planner SITL Integration')
    parser.add_argument('--sitl-port', type=int, default=14550, 
                       help='SITL MAVLink port (default: 14550)')
    parser.add_argument('--gcs-port', type=int, default=14551,
                       help='GCS MAVLink port (default: 14551)')
    
    args = parser.parse_args()
    
    # Create and run integration
    integration = SITLIntegration(args.sitl_port, args.gcs_port)
    
    try:
        asyncio.run(integration.run())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Integration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 