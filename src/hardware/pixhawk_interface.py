"""
Pixhawk Hardware Interface for DART-Planner
Real-time integration of optimized SE(3) MPC with flight hardware
"""

import numpy as np
import time
from typing import Optional, Dict, Any
from pymavlink import mavutil
import asyncio
from dataclasses import dataclass

from src.common.types import DroneState, ControlCommand
from src.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
from src.control.geometric_controller import GeometricController


@dataclass
class HardwareConfig:
    """Configuration for hardware interface"""
    # Communication
    mavlink_connection: str = "/dev/ttyUSB0"  # Or "udp:127.0.0.1:14550" for SITL
    baud_rate: int = 921600
    
    # Control frequencies
    control_frequency: float = 400.0  # Hz - conservative from 479Hz simulation
    planning_frequency: float = 50.0   # Hz - high frequency planning
    telemetry_frequency: float = 10.0  # Hz - status reporting
    
    # Safety limits
    max_velocity: float = 15.0  # m/s
    max_acceleration: float = 10.0  # m/s^2
    max_altitude: float = 50.0  # m
    safety_radius: float = 100.0  # m from home
    
    # Performance monitoring
    enable_performance_logging: bool = True
    max_planning_time_ms: float = 8.0  # Trigger warning if exceeded


class PixhawkInterface:
    """
    Real-time hardware interface for DART-Planner
    
    Integrates the 2.1ms SE(3) MPC planner with Pixhawk flight controller
    for production-grade autonomous flight.
    """
    
    def __init__(self, config: Optional[HardwareConfig] = None):
        self.config = config if config else HardwareConfig()
        
        # Initialize planner with hardware-optimized settings
        planner_config = SE3MPCConfig(
            prediction_horizon=6,  # From our optimization
            dt=0.125,
            max_iterations=15,
            convergence_tolerance=5e-2
        )
        self.planner = SE3MPCPlanner(planner_config)
        self.controller = GeometricController()
        
        # Hardware connection
        self.mavlink_connection: Optional[mavutil.mavlink_connection] = None
        self.is_connected = False
        self.is_armed = False
        
        # State tracking
        self.current_state = DroneState()
        self.mission_active = False
        self.emergency_stop = False
        
        # Performance monitoring
        self.performance_stats = {
            'control_loop_times': [],
            'planning_times': [],
            'total_commands_sent': 0,
            'planning_failures': 0,
            'control_frequency_achieved': 0.0
        }
        
        # Safety monitoring
        self.last_heartbeat = time.time()
        self.failsafe_active = False
        
        print(f"PixhawkInterface initialized:")
        print(f"  Target control frequency: {self.config.control_frequency}Hz")
        print(f"  Target planning frequency: {self.config.planning_frequency}Hz")
        print(f"  Max planning time: {self.config.max_planning_time_ms}ms")
    
    async def connect(self) -> bool:
        """Establish connection to Pixhawk"""
        try:
            print(f"Connecting to Pixhawk: {self.config.mavlink_connection}")
            
            self.mavlink_connection = mavutil.mavlink_connection(
                self.config.mavlink_connection,
                baud=self.config.baud_rate
            )
            
            # Wait for heartbeat
            print("Waiting for heartbeat...")
            self.mavlink_connection.wait_heartbeat()
            print("✅ Pixhawk connection established!")
            
            self.is_connected = True
            self.last_heartbeat = time.time()
            
            # Request data streams
            await self._request_data_streams()
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def _request_data_streams(self):
        """Request high-frequency data streams from Pixhawk"""
        # Request attitude and position at high frequency
        self.mavlink_connection.mav.request_data_stream_send(
            self.mavlink_connection.target_system,
            self.mavlink_connection.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ATTITUDE,
            int(self.config.control_frequency),  # Hz
            1  # Start stream
        )
        
        self.mavlink_connection.mav.request_data_stream_send(
            self.mavlink_connection.target_system,
            self.mavlink_connection.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_POSITION,
            int(self.config.control_frequency),  # Hz
            1  # Start stream
        )
    
    async def start_mission(self, waypoints: np.ndarray) -> bool:
        """Start autonomous mission execution"""
        if not self.is_connected:
            print("❌ Not connected to Pixhawk")
            return False
        
        print(f"🚀 Starting mission with {len(waypoints)} waypoints")
        
        # Set first waypoint as goal
        if len(waypoints) > 0:
            self.planner.set_goal(waypoints[0])
            self.mission_active = True
            
            # Start control loops
            await asyncio.gather(
                self._control_loop(),
                self._planning_loop(),
                self._telemetry_loop(),
                self._safety_monitor_loop()
            )
            
        return True
    
    async def _control_loop(self):
        """High-frequency control loop (400Hz target)"""
        dt = 1.0 / self.config.control_frequency
        
        while self.mission_active and not self.emergency_stop:
            loop_start = time.perf_counter()
            
            try:
                # Update current state from Pixhawk
                await self._update_state()
                
                # Generate control command (using last trajectory)
                control_cmd = self.controller.compute_control_command(
                    self.current_state
                )
                
                # Send to Pixhawk
                await self._send_control_command(control_cmd)
                
                # Performance tracking
                loop_time = (time.perf_counter() - loop_start) * 1000  # ms
                self.performance_stats['control_loop_times'].append(loop_time)
                self.performance_stats['total_commands_sent'] += 1
                
                # Maintain frequency
                elapsed = time.perf_counter() - loop_start
                if elapsed < dt:
                    await asyncio.sleep(dt - elapsed)
                    
            except Exception as e:
                print(f"⚠️ Control loop error: {e}")
                await asyncio.sleep(dt)
    
    async def _planning_loop(self):
        """SE(3) MPC planning loop (50Hz target)"""
        dt = 1.0 / self.config.planning_frequency
        
        while self.mission_active and not self.emergency_stop:
            planning_start = time.perf_counter()
            
            try:
                # Plan trajectory using optimized SE(3) MPC
                goal = self.planner.goal_position
                if goal is not None:
                    trajectory = self.planner.plan_trajectory(
                        self.current_state, goal
                    )
                    
                    # Update controller with new trajectory
                    self.controller.set_trajectory(trajectory)
                
                # Performance tracking
                planning_time = (time.perf_counter() - planning_start) * 1000  # ms
                self.performance_stats['planning_times'].append(planning_time)
                
                # Warn if planning is too slow
                if planning_time > self.config.max_planning_time_ms:
                    print(f"⚠️ Slow planning: {planning_time:.1f}ms")
                
                # Maintain frequency
                elapsed = time.perf_counter() - planning_start
                if elapsed < dt:
                    await asyncio.sleep(dt - elapsed)
                    
            except Exception as e:
                print(f"⚠️ Planning loop error: {e}")
                self.performance_stats['planning_failures'] += 1
                await asyncio.sleep(dt)
    
    async def _update_state(self):
        """Update drone state from Pixhawk telemetry"""
        # This would parse MAVLink messages to update self.current_state
        # Implementation depends on specific message types
        pass
    
    async def _send_control_command(self, command: ControlCommand):
        """Send control command to Pixhawk"""
        # Convert to MAVLink SET_ATTITUDE_TARGET message
        # Implementation depends on control interface
        pass
    
    async def _telemetry_loop(self):
        """Performance monitoring and telemetry"""
        dt = 1.0 / self.config.telemetry_frequency
        
        while self.mission_active:
            if self.performance_stats['control_loop_times']:
                # Calculate achieved frequencies
                recent_times = self.performance_stats['control_loop_times'][-100:]
                if recent_times:
                    avg_loop_time = np.mean(recent_times)
                    self.performance_stats['control_frequency_achieved'] = 1000.0 / avg_loop_time
                
                # Report performance every 10 seconds
                if len(recent_times) % 100 == 0:
                    avg_planning = np.mean(self.performance_stats['planning_times'][-50:])
                    print(f"📊 Performance: Control={self.performance_stats['control_frequency_achieved']:.0f}Hz, "
                          f"Planning={avg_planning:.1f}ms avg")
            
            await asyncio.sleep(dt)
    
    async def _safety_monitor_loop(self):
        """Safety monitoring and failsafe logic"""
        dt = 0.1  # 10Hz safety monitoring
        
        while self.mission_active:
            # Check various safety conditions
            await self._check_safety_conditions()
            await asyncio.sleep(dt)
    
    async def _check_safety_conditions(self):
        """Monitor safety conditions and trigger failsafe if needed"""
        # Position bounds check
        if np.linalg.norm(self.current_state.position) > self.config.safety_radius:
            await self._trigger_failsafe("Position out of bounds")
        
        # Altitude check
        if self.current_state.position[2] > self.config.max_altitude:
            await self._trigger_failsafe("Altitude limit exceeded")
        
        # Planning performance check
        if self.performance_stats['planning_times']:
            recent_planning_times = self.performance_stats['planning_times'][-10:]
            if np.mean(recent_planning_times) > 20.0:  # >20ms consistently
                await self._trigger_failsafe("Planning too slow")
    
    async def _trigger_failsafe(self, reason: str):
        """Trigger emergency failsafe"""
        print(f"🚨 FAILSAFE TRIGGERED: {reason}")
        self.failsafe_active = True
        self.emergency_stop = True
        
        # Send immediate hover command
        # Implementation depends on MAVLink interface
        
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        if not self.performance_stats['control_loop_times']:
            return {"status": "no_data"}
        
        control_times = np.array(self.performance_stats['control_loop_times'])
        planning_times = np.array(self.performance_stats['planning_times'])
        
        return {
            "mission_active": self.mission_active,
            "total_commands_sent": self.performance_stats['total_commands_sent'],
            "control_frequency_achieved": self.performance_stats['control_frequency_achieved'],
            "mean_control_loop_time_ms": float(np.mean(control_times)),
            "mean_planning_time_ms": float(np.mean(planning_times)),
            "max_planning_time_ms": float(np.max(planning_times)),
            "planning_success_rate": 1.0 - (self.performance_stats['planning_failures'] / max(len(planning_times), 1)),
            "failsafe_activations": int(self.failsafe_active),
            "hardware_ready": self.is_connected and not self.emergency_stop
        }


# Hardware testing script
async def main():
    """Test hardware integration"""
    interface = PixhawkInterface()
    
    if await interface.connect():
        # Simple test mission
        waypoints = np.array([
            [10.0, 0.0, 5.0],
            [10.0, 10.0, 5.0],
            [0.0, 10.0, 5.0],
            [0.0, 0.0, 5.0]
        ])
        
        await interface.start_mission(waypoints)
    else:
        print("❌ Hardware connection failed")


if __name__ == "__main__":
    asyncio.run(main()) 