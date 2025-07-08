"""
Simulated Vehicle I/O implementation for DART-Planner.

This module provides a concrete implementation of VehicleIO that uses
SimulatedAdapter for testing and development without real hardware.
"""

import asyncio
import logging
import time
import numpy as np
from typing import Optional, Dict, Any

from .vehicle_io import VehicleIO, VehicleIOFactory
from .simulated_adapter import SimulatedAdapter
from ..common.types import DroneState, Trajectory, ControlCommand
from ..common.di_container import get_container
from ..common.timing_alignment import ControllerThrottler, get_timing_manager


class SimulatedVehicleIO(VehicleIO):
    """
    Simulated vehicle I/O implementation using SimulatedAdapter.
    
    This provides a fully functional vehicle interface for testing,
    development, and CI without requiring real hardware or AirSim.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize simulated vehicle I/O."""
        super().__init__(config)
        self.adapter = SimulatedAdapter()
        self.current_trajectory: Optional[Trajectory] = None
        self.trajectory_index = 0
        self.update_rate = config.get('update_rate', 50.0)  # Hz
        self.simulation_time = 0.0
        
        # Initialize timing management
        timing_manager = get_timing_manager()
        self.controller_throttler = ControllerThrottler(timing_manager)
        
        # Get planner via factory pattern
        try:
            container = get_container()
            planner_container = container.create_planner_container()
            self.planner = planner_container.get_se3_planner()
            self.logger.info("SE3MPCPlanner initialized via factory")
        except Exception as e:
            self.logger.warning(f"Could not initialize planner via factory: {e}")
            self.planner = None
    
    async def connect(self) -> bool:
        """Connect to simulated vehicle."""
        try:
            self.adapter.connect()
            self.connected = True
            self.logger.info("Connected to simulated vehicle")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to simulated vehicle: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from simulated vehicle."""
        try:
            self.adapter.disconnect()
            self.connected = False
            self.logger.info("Disconnected from simulated vehicle")
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
    
    async def get_state(self) -> Optional[DroneState]:
        """Get current simulated vehicle state."""
        if not self.connected:
            return None
        
        try:
            adapter_state = self.adapter.get_state()
            
            # Convert adapter state to DroneState
            drone_state = DroneState(
                timestamp=time.time(),
                position=np.array(adapter_state["position"]),
                velocity=np.array(adapter_state["velocity"]),
                attitude=np.array(adapter_state["orientation"])  # Use attitude instead of orientation
            )
            
            self.last_state = drone_state
            self.last_heartbeat = time.time()
            return drone_state
            
        except Exception as e:
            self.logger.error(f"Failed to get simulated state: {e}")
            return None
    
    async def send_trajectory(self, trajectory: Trajectory) -> bool:
        """Send trajectory to simulated vehicle."""
        if not self.connected:
            self.logger.error("Cannot send trajectory: not connected")
            return False
        
        try:
            self.current_trajectory = trajectory
            self.trajectory_index = 0
            
            # Update controller throttler with new trajectory
            self.controller_throttler.update_trajectory(trajectory)
            
            self.logger.info(f"Received trajectory with {len(trajectory.positions)} waypoints")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send trajectory: {e}")
            return False
    
    async def send_control_command(self, command: Dict[str, Any]) -> bool:
        """Send control command to simulated vehicle."""
        if not self.connected:
            return False
        
        try:
            # Convert control command to adapter command
            if "position" in command:
                pos = command["position"]
                result = self.adapter.send_command("moveToPosition", {
                    "x": pos[0], "y": pos[1], "z": pos[2]
                })
                return result
            else:
                self.logger.warning(f"Unsupported control command: {command}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to send control command: {e}")
            return False
    
    async def arm(self) -> bool:
        """Arm the simulated vehicle."""
        if not self.connected:
            return False
        
        try:
            result = self.adapter.send_command("arm")
            self.logger.info("Simulated vehicle armed")
            return result
        except Exception as e:
            self.logger.error(f"Failed to arm simulated vehicle: {e}")
            return False
    
    async def disarm(self) -> bool:
        """Disarm the simulated vehicle."""
        if not self.connected:
            return False
        
        try:
            result = self.adapter.send_command("disarm")
            self.logger.info("Simulated vehicle disarmed")
            return result
        except Exception as e:
            self.logger.error(f"Failed to disarm simulated vehicle: {e}")
            return False
    
    async def takeoff(self, target_altitude: float) -> bool:
        """Execute takeoff to target altitude."""
        if not self.connected:
            return False
        
        try:
            # Use planner to generate takeoff trajectory if available
            if self.planner and self.last_state:
                goal = {
                    "position": np.array([0.0, 0.0, target_altitude]),
                    "velocity": np.array([0.0, 0.0, 0.0]),
                    "orientation": np.array([1.0, 0.0, 0.0, 0.0])
                }
                
                takeoff_trajectory = self.planner.plan_trajectory(self.last_state, goal)
                if takeoff_trajectory:
                    await self.send_trajectory(takeoff_trajectory)
                    self.logger.info(f"Generated takeoff trajectory to {target_altitude}m")
                    return True
            
            # Fallback to simple takeoff command
            result = self.adapter.send_command("takeoff")
            self.logger.info(f"Simulated vehicle takeoff to {target_altitude}m")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute takeoff: {e}")
            return False
    
    async def land(self) -> bool:
        """Execute landing."""
        if not self.connected:
            return False
        
        try:
            result = self.adapter.send_command("land")
            self.logger.info("Simulated vehicle landing")
            return result
        except Exception as e:
            self.logger.error(f"Failed to execute landing: {e}")
            return False
    
    async def set_mode(self, mode: str) -> bool:
        """Set vehicle flight mode."""
        if not self.connected:
            return False
        
        try:
            # Simulate mode changes
            self.logger.info(f"Simulated vehicle mode set to: {mode}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set mode: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get vehicle status information."""
        if not self.connected:
            return {"connected": False}
        
        try:
            adapter_state = self.adapter.get_state()
            capabilities = self.adapter.get_capabilities()
            
            return {
                "connected": self.connected,
                "armed": adapter_state["armed"],
                "position": adapter_state["position"],
                "velocity": adapter_state["velocity"],
                "capabilities": capabilities,
                "trajectory_active": self.current_trajectory is not None,
                "trajectory_progress": self.trajectory_index if self.current_trajectory else 0,
                "planner_available": self.planner is not None,
                "last_heartbeat": self.last_heartbeat,
            }
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return {"connected": False, "error": str(e)}
    
    async def emergency_stop(self) -> bool:
        """Execute emergency stop procedure."""
        if not self.connected:
            return False
        
        try:
            self.adapter.emergency_stop()
            self.current_trajectory = None
            self.trajectory_index = 0
            self.logger.warning("Emergency stop executed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to execute emergency stop: {e}")
            return False
    
    def is_armed(self) -> bool:
        """Check if vehicle is armed."""
        if not self.connected:
            return False
        
        try:
            adapter_state = self.adapter.get_state()
            return adapter_state["armed"]
        except Exception:
            return False
    
    async def update_simulation(self, dt: float) -> None:
        """Update simulation state."""
        if not self.connected or not self.current_trajectory:
            return
        
        # Check if we should execute control based on timing
        current_time = time.time()
        if not self.controller_throttler.should_execute_control(current_time):
            return
        
        # Update timing manager
        timing_manager = get_timing_manager()
        timing_manager.update_control_timing(current_time)
        
        try:
            # Get interpolated control state from trajectory
            control_state = self.controller_throttler.get_control_state(current_time)
            
            if control_state is not None:
                # Extract position, velocity, attitude from control state
                position = control_state[:3]
                velocity = control_state[3:6]
                attitude = control_state[6:9]  # Assuming 3D attitude (roll, pitch, yaw)
                
                # Update adapter state using moveToPosition command
                self.adapter.send_command("moveToPosition", {
                    "x": position[0],
                    "y": position[1], 
                    "z": position[2]
                })
                
                # Note: SimulatedAdapter doesn't support direct velocity/attitude updates
                # In a real implementation, this would update the full state
            else:
                # Fallback to simple trajectory following simulation
                if self.trajectory_index < len(self.current_trajectory.positions):
                    target_pos = self.current_trajectory.positions[self.trajectory_index]
                    
                    # Move towards target position
                    current_state = self.adapter.get_state()
                    current_pos = np.array(current_state["position"])
                    
                    # Simple linear interpolation
                    direction = target_pos - current_pos
                    distance = np.linalg.norm(direction)
                    
                    if distance < 0.1:  # Close enough to waypoint
                        self.trajectory_index += 1
                    else:
                        # Move towards target
                        step_size = 0.1  # 10cm per update
                    if distance > step_size:
                        direction = direction / distance * step_size
                    
                    new_pos = current_pos + direction
                    self.adapter.send_command("moveToPosition", {
                        "x": new_pos[0], "y": new_pos[1], "z": new_pos[2]
                    })
            
            self.simulation_time += dt
            
        except Exception as e:
            self.logger.error(f"Error updating simulation: {e}")


# Register with factory
VehicleIOFactory.register("simulated", SimulatedVehicleIO) 
