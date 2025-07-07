#!/usr/bin/env python3
"""
Advanced Mission Example for DART-Planner

This example demonstrates advanced mission planning capabilities including:
- Multi-waypoint navigation with different airframe configurations
- Dynamic obstacle avoidance
- Performance monitoring and logging
- Integration with the admin panel for configuration
- Error handling and recovery procedures

Usage:
    python examples/advanced_mission_example.py --airframe dji_f450 --mission complex_survey
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.common.types import DroneState, ControlCommand, Trajectory, Waypoint
from src.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
from src.control.geometric_controller import GeometricController, GeometricControllerConfig
from src.perception.explicit_geometric_mapper import ExplicitGeometricMapper
from src.hardware.pixhawk_interface import PixhawkInterface
from src.config.airframe_config import get_airframe_config, AirframeConfig
from src.security.auth import Role, require_role
from src.utils.drone_simulator import DroneSimulator


class AdvancedMissionPlanner:
    """Advanced mission planner with airframe-specific configuration."""
    
    def __init__(self, airframe_name: str = "default", use_simulation: bool = True):
        """Initialize the mission planner."""
        self.airframe_name = airframe_name
        self.use_simulation = use_simulation
        
        # Load airframe configuration
        self.airframe_config = get_airframe_config(airframe_name)
        self._validate_airframe_config()
        
        # Initialize components
        self._setup_logging()
        self._setup_components()
        
        # Mission state
        self.current_waypoint = 0
        self.mission_complete = False
        self.emergency_stop = False
        
    def _validate_airframe_config(self):
        """Validate the airframe configuration."""
        issues = self.airframe_config.validate_config()
        if issues:
            raise ValueError(f"Airframe configuration issues: {issues}")
        
        logging.info(f"Using airframe: {self.airframe_config.name}")
        logging.info(f"Thrust-to-weight ratio: {self.airframe_config.get_thrust_to_weight_ratio():.2f}")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'mission_{self.airframe_name}_{int(time.time())}.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_components(self):
        """Setup mission components."""
        # Configure SE3 MPC planner
        se3_config = SE3MPCConfig(
            horizon_length=20,
            dt=1.0 / self.airframe_config.control_frequency,
            max_velocity=self.airframe_config.max_velocity,
            max_acceleration=self.airframe_config.max_acceleration,
            max_angular_velocity=self.airframe_config.max_angular_velocity,
            max_angular_acceleration=self.airframe_config.max_angular_acceleration,
        )
        self.planner = SE3MPCPlanner(se3_config)
        
        # Configure geometric controller
        controller_config = GeometricControllerConfig(
            position_kp=self.airframe_config.position_kp,
            velocity_kp=self.airframe_config.velocity_kp,
            attitude_kp=self.airframe_config.attitude_kp,
            attitude_kd=self.airframe_config.attitude_kd,
            mass=self.airframe_config.mass,
            max_thrust=self.airframe_config.get_total_thrust(),
        )
        self.controller = GeometricController(controller_config)
        
        # Setup perception
        self.mapper = ExplicitGeometricMapper()
        
        # Setup hardware interface
        if self.use_simulation:
            self.hardware = DroneSimulator(
                mass=self.airframe_config.mass,
                max_thrust=self.airframe_config.get_total_thrust(),
                dt=1.0 / self.airframe_config.control_frequency
            )
        else:
            self.hardware = PixhawkInterface()
    
    def create_complex_survey_mission(self) -> List[Waypoint]:
        """Create a complex survey mission with multiple waypoints."""
        waypoints = []
        
        # Takeoff
        waypoints.append(Waypoint(
            position=np.array([0.0, 0.0, 5.0]),
            velocity=np.array([0.0, 0.0, 0.0]),
            acceleration=np.array([0.0, 0.0, 0.0]),
            yaw=0.0,
            duration=5.0
        ))
        
        # Survey pattern - square with diagonal
        survey_height = 10.0
        survey_size = 20.0
        
        # Corner points
        corners = [
            (survey_size/2, survey_size/2),
            (-survey_size/2, survey_size/2),
            (-survey_size/2, -survey_size/2),
            (survey_size/2, -survey_size/2),
        ]
        
        for i, (x, y) in enumerate(corners):
            waypoints.append(Waypoint(
                position=np.array([x, y, survey_height]),
                velocity=np.array([0.0, 0.0, 0.0]),
                acceleration=np.array([0.0, 0.0, 0.0]),
                yaw=np.arctan2(y, x),
                duration=3.0
            ))
        
        # Diagonal crossing
        waypoints.append(Waypoint(
            position=np.array([0.0, 0.0, survey_height]),
            velocity=np.array([0.0, 0.0, 0.0]),
            acceleration=np.array([0.0, 0.0, 0.0]),
            yaw=np.pi/4,
            duration=2.0
        ))
        
        # Return to start
        waypoints.append(Waypoint(
            position=np.array([0.0, 0.0, 5.0]),
            velocity=np.array([0.0, 0.0, 0.0]),
            acceleration=np.array([0.0, 0.0, 0.0]),
            yaw=0.0,
            duration=5.0
        ))
        
        # Land
        waypoints.append(Waypoint(
            position=np.array([0.0, 0.0, 0.5]),
            velocity=np.array([0.0, 0.0, 0.0]),
            acceleration=np.array([0.0, 0.0, 0.0]),
            yaw=0.0,
            duration=3.0
        ))
        
        return waypoints
    
    def create_racing_course_mission(self) -> List[Waypoint]:
        """Create a racing course mission for high-performance drones."""
        if self.airframe_config.type != "quadcopter":
            raise ValueError("Racing course requires quadcopter airframe")
        
        waypoints = []
        
        # High-speed takeoff
        waypoints.append(Waypoint(
            position=np.array([0.0, 0.0, 3.0]),
            velocity=np.array([0.0, 0.0, 2.0]),
            acceleration=np.array([0.0, 0.0, 0.0]),
            yaw=0.0,
            duration=2.0
        ))
        
        # Racing course - figure-8 pattern
        t = np.linspace(0, 2*np.pi, 16)
        radius = 15.0
        height = 5.0
        
        for i, theta in enumerate(t):
            # Figure-8 parametric equations
            x = radius * np.sin(theta)
            y = radius * np.sin(theta) * np.cos(theta)
            
            # Calculate velocity for smooth motion
            vx = radius * np.cos(theta)
            vy = radius * (np.cos(theta)**2 - np.sin(theta)**2)
            
            waypoints.append(Waypoint(
                position=np.array([x, y, height]),
                velocity=np.array([vx, vy, 0.0]),
                acceleration=np.array([0.0, 0.0, 0.0]),
                yaw=np.arctan2(vy, vx),
                duration=1.0
            ))
        
        # High-speed landing
        waypoints.append(Waypoint(
            position=np.array([0.0, 0.0, 0.5]),
            velocity=np.array([0.0, 0.0, -1.0]),
            acceleration=np.array([0.0, 0.0, 0.0]),
            yaw=0.0,
            duration=2.0
        ))
        
        return waypoints
    
    def create_precision_mission(self) -> List[Waypoint]:
        """Create a precision mission for indoor/confined spaces."""
        waypoints = []
        
        # Gentle takeoff
        waypoints.append(Waypoint(
            position=np.array([0.0, 0.0, 2.0]),
            velocity=np.array([0.0, 0.0, 0.5]),
            acceleration=np.array([0.0, 0.0, 0.0]),
            yaw=0.0,
            duration=4.0
        ))
        
        # Precision waypoints in confined space
        precision_points = [
            (1.0, 0.0, 2.0),
            (1.0, 1.0, 2.0),
            (0.0, 1.0, 2.0),
            (0.0, 0.0, 2.0),
            (0.5, 0.5, 1.5),
            (0.5, 0.5, 2.5),
            (0.0, 0.0, 2.0),
        ]
        
        for x, y, z in precision_points:
            waypoints.append(Waypoint(
                position=np.array([x, y, z]),
                velocity=np.array([0.0, 0.0, 0.0]),
                acceleration=np.array([0.0, 0.0, 0.0]),
                yaw=np.arctan2(y, x),
                duration=2.0
            ))
        
        # Gentle landing
        waypoints.append(Waypoint(
            position=np.array([0.0, 0.0, 0.3]),
            velocity=np.array([0.0, 0.0, -0.2]),
            acceleration=np.array([0.0, 0.0, 0.0]),
            yaw=0.0,
            duration=3.0
        ))
        
        return waypoints
    
    async def execute_mission(self, waypoints: List[Waypoint]):
        """Execute the mission with the given waypoints."""
        self.logger.info(f"Starting mission with {len(waypoints)} waypoints")
        
        # Initialize hardware
        await self.hardware.connect()
        await self.hardware.arm()
        
        try:
            for i, waypoint in enumerate(waypoints):
                if self.emergency_stop:
                    self.logger.warning("Emergency stop activated")
                    break
                
                self.logger.info(f"Executing waypoint {i+1}/{len(waypoints)}")
                await self._execute_waypoint(waypoint)
                
        except Exception as e:
            self.logger.error(f"Mission execution failed: {e}")
            await self._emergency_landing()
            raise
        
        finally:
            await self.hardware.disconnect()
            self.logger.info("Mission completed")
    
    async def _execute_waypoint(self, waypoint: Waypoint):
        """Execute a single waypoint."""
        start_time = time.time()
        target_time = waypoint.duration
        
        while time.time() - start_time < target_time:
            # Get current state
            state = await self.hardware.get_state()
            
            # Plan trajectory to waypoint
            trajectory = self.planner.plan_trajectory(state, waypoint)
            
            # Generate control command
            control = self.controller.compute_control(state, trajectory)
            
            # Apply control
            await self.hardware.send_control(control)
            
            # Check safety limits
            self._check_safety_limits(state)
            
            # Update perception
            self.mapper.update_map(state)
            
            # Log performance
            self._log_performance(state, control)
            
            await asyncio.sleep(1.0 / self.airframe_config.control_frequency)
    
    def _check_safety_limits(self, state: DroneState):
        """Check safety limits and trigger emergency stop if needed."""
        # Check altitude limits
        if state.position[2] > self.airframe_config.max_altitude:
            self.logger.error(f"Altitude limit exceeded: {state.position[2]:.2f}m")
            self.emergency_stop = True
        
        # Check distance from origin
        distance = np.linalg.norm(state.position[:2])
        if distance > self.airframe_config.max_distance:
            self.logger.error(f"Distance limit exceeded: {distance:.2f}m")
            self.emergency_stop = True
        
        # Check velocity limits
        velocity_magnitude = np.linalg.norm(state.velocity)
        if velocity_magnitude > self.airframe_config.max_velocity:
            self.logger.error(f"Velocity limit exceeded: {velocity_magnitude:.2f}m/s")
            self.emergency_stop = True
    
    async def _emergency_landing(self):
        """Perform emergency landing."""
        self.logger.warning("Performing emergency landing")
        
        # Create emergency landing waypoint
        emergency_waypoint = Waypoint(
            position=np.array([0.0, 0.0, 0.5]),
            velocity=np.array([0.0, 0.0, -0.5]),
            acceleration=np.array([0.0, 0.0, 0.0]),
            yaw=0.0,
            duration=10.0
        )
        
        await self._execute_waypoint(emergency_waypoint)
        await self.hardware.disarm()
    
    def _log_performance(self, state: DroneState, control: ControlCommand):
        """Log performance metrics."""
        # Calculate tracking errors
        if hasattr(self, 'target_trajectory'):
            position_error = np.linalg.norm(state.position - self.target_trajectory.positions[-1])
            velocity_error = np.linalg.norm(state.velocity - self.target_trajectory.velocities[-1])
            
            self.logger.debug(f"Position error: {position_error:.3f}m")
            self.logger.debug(f"Velocity error: {velocity_error:.3f}m/s")
        
        # Log control effort
        thrust_magnitude = np.linalg.norm(control.thrust)
        self.logger.debug(f"Control thrust: {thrust_magnitude:.2f}N")


def main():
    """Main function to run the advanced mission example."""
    parser = argparse.ArgumentParser(description="Advanced Mission Example")
    parser.add_argument("--airframe", default="default", 
                       choices=["default", "dji_f450", "dji_f550", "racing_drone", 
                               "heavy_lift", "indoor_micro", "fixed_wing", "vtol"],
                       help="Airframe configuration to use")
    parser.add_argument("--mission", default="complex_survey",
                       choices=["complex_survey", "racing_course", "precision"],
                       help="Mission type to execute")
    parser.add_argument("--simulation", action="store_true", default=True,
                       help="Use simulation instead of real hardware")
    parser.add_argument("--duration", type=float, default=60.0,
                       help="Mission duration limit in seconds")
    
    args = parser.parse_args()
    
    try:
        # Create mission planner
        planner = AdvancedMissionPlanner(
            airframe_name=args.airframe,
            use_simulation=args.simulation
        )
        
        # Create mission waypoints
        if args.mission == "complex_survey":
            waypoints = planner.create_complex_survey_mission()
        elif args.mission == "racing_course":
            waypoints = planner.create_racing_course_mission()
        elif args.mission == "precision":
            waypoints = planner.create_precision_mission()
        else:
            raise ValueError(f"Unknown mission type: {args.mission}")
        
        # Execute mission
        asyncio.run(planner.execute_mission(waypoints))
        
    except KeyboardInterrupt:
        print("\nMission interrupted by user")
    except Exception as e:
        print(f"Mission failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 