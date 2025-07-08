"""
Pixhawk Hardware Interface for DART-Planner
Real-time integration of optimized SE(3) MPC with flight hardware
"""

import asyncio
from src.common.di_container import get_container
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pymavlink import mavutil

from src.common.types import ControlCommand, DroneState, Trajectory, BodyRateCommand
from control.geometric_controller import GeometricController
from planning.se3_mpc_planner import SE3MPCConfig, SE3MPCPlanner


@dataclass
class HardwareConfig:
    """Configuration for hardware interface"""

    # Communication
    mavlink_connection: str = "/dev/ttyUSB0"  # Or "udp:127.0.0.1:14550" for SITL
    baud_rate: int = 921600

    # Control frequencies
    control_frequency: float = 400.0  # Hz - conservative from 479Hz simulation
    planning_frequency: float = 50.0  # Hz - high frequency planning
    telemetry_frequency: float = 10.0  # Hz - status reporting

    # Safety limits
    max_velocity: float = 15.0  # m/s
    max_acceleration: float = 10.0  # m/s^2
    max_altitude: float = 50.0  # m
    safety_radius: float = 100.0  # m from home
    max_thrust: float = 10.0 # N

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
        self.logger = logging.getLogger(__name__)

        # Import planner components
        from src.planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
        from src.control.geometric_controller import GeometricController

        # Initialize planner with hardware-optimized settings
        planner_config = SE3MPCConfig(
            prediction_horizon=6,  # From our optimization
            dt=0.125,
            max_iterations=15,
            convergence_tolerance=5e-2,
        )
        self.planner = SE3MPCPlanner(planner_config)
        self.controller = GeometricController()
        self.current_trajectory: Optional[Trajectory] = None

        # Hardware connection
        self.mavlink_connection: Optional[Any] = None
        self.is_connected = False
        self.is_armed = False
        self.target_system = 1
        self.target_component = 1

        # State tracking
        self.current_state = DroneState(timestamp=time.time())
        self.mission_active = False
        self.emergency_stop = False

        # Performance monitoring
        self.performance_stats = {
            "control_loop_times": [],
            "planning_times": [],
            "total_commands_sent": 0,
            "planning_failures": 0,
            "control_frequency_achieved": 0.0,
        }

        # Safety monitoring
        self.last_heartbeat = time.time()
        self.last_attitude_msg = time.time()
        self.failsafe_active = False

        self.logger.info(f"PixhawkInterface initialized:")
        self.logger.info(f"  Target control frequency: {self.config.control_frequency}Hz")
        self.logger.info(f"  Target planning frequency: {self.config.planning_frequency}Hz")
        self.logger.info(f"  Max planning time: {self.config.max_planning_time_ms}ms")

    @staticmethod
    def _euler_to_quaternion(roll: float, pitch: float, yaw: float) -> np.ndarray:
        """Convert euler angles to quaternion."""
        cy = np.cos(yaw * 0.5)
        sy = np.sin(yaw * 0.5)
        cp = np.cos(pitch * 0.5)
        sp = np.sin(pitch * 0.5)
        cr = np.cos(roll * 0.5)
        sr = np.sin(roll * 0.5)
        q = np.array([
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        ])
        return q

    async def connect(self) -> bool:
        """Establish connection to Pixhawk and wait for heartbeat."""
        try:
            print(f"Connecting to Pixhawk: {self.config.mavlink_connection}")
            self.mavlink_connection = mavutil.mavlink_connection(
                self.config.mavlink_connection, baud=self.config.baud_rate
            )

            # Wait for the first heartbeat
            print("Waiting for heartbeat...")
            if not self.mavlink_connection:
                print("❌ MAVLink connection object is None.")
                return False
            
            self.mavlink_connection.wait_heartbeat()
            self.target_system = self.mavlink_connection.target_system
            self.target_component = self.mavlink_connection.target_component
            print(f"✅ Heartbeat received! (system={self.target_system}, component={self.target_component})")

            self.is_connected = True
            self.last_heartbeat = time.time()
            await self._request_data_streams()
            return True

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.is_connected = False
            return False

    async def close(self):
        """Close the MAVLink connection."""
        if self.mavlink_connection:
            self.mavlink_connection.close()
            self.is_connected = False
            print("Pixhawk connection closed.")

    async def _request_data_streams(self):
        """Request high-frequency data streams from Pixhawk for attitude and position."""
        if not self.mavlink_connection:
            return
        
        for stream, frequency in [
            (mavutil.mavlink.MAV_DATA_STREAM_ATTITUDE, self.config.control_frequency),
            (mavutil.mavlink.MAV_DATA_STREAM_POSITION, self.config.control_frequency),
            (mavutil.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS, 2), # For battery, etc.
            (mavutil.mavlink.MAV_DATA_STREAM_RC_CHANNELS, 2), # For RC input
        ]:
            self.mavlink_connection.mav.request_data_stream_send(
                self.target_system,
                self.target_component,
                stream,
                int(frequency),
                1,  # Start stream
            )
            await asyncio.sleep(0.01)
        print("Requested data streams.")

    async def set_mode(self, mode: str) -> bool:
        """Set the flight mode of the vehicle (e.g., 'OFFBOARD', 'STABILIZE')."""
        if not self.mavlink_connection: return False
        try:
            mode_id = self.mavlink_connection.mode_mapping()[mode]
            self.mavlink_connection.mav.set_mode_send(
                self.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                mode_id)
            
            # Wait for acknowledgement
            ack_msg = self.mavlink_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
            if ack_msg and ack_msg.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                print(f"✅ Mode set to {mode}")
                return True
            else:
                print(f"❌ Failed to set mode to {mode}")
                return False
        except Exception as e:
            print(f"❌ Error setting mode: {e}")
            return False

    async def arm(self, force: bool = False) -> bool:
        """Arm the vehicle."""
        if not self.mavlink_connection: return False
        if self.is_armed:
            print("Vehicle is already armed.")
            return True
            
        print("Arming vehicle...")
        self.mavlink_connection.mav.command_long_send(
            self.target_system, self.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1, 21196 if force else 0, 0, 0, 0, 0, 0) # 21196 is magic number for force arm
        
        # Wait for acknowledgement
        ack_msg = self.mavlink_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
        if ack_msg and ack_msg.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print("✅ Vehicle armed")
            self.is_armed = True
            return True
        else:
            print("❌ Arming failed")
            return False

    async def disarm(self) -> bool:
        """Disarm the vehicle."""
        if not self.mavlink_connection: return False
        if not self.is_armed:
            print("Vehicle is already disarmed.")
            return True

        print("Disarming vehicle...")
        self.mavlink_connection.mav.command_long_send(
            self.target_system, self.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 0, 0, 0, 0, 0, 0, 0)

        # Wait for acknowledgement
        ack_msg = self.mavlink_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
        if ack_msg and ack_msg.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print("✅ Vehicle disarmed")
            self.is_armed = False
            return True
        else:
            print("❌ Disarming failed")
            return False

    async def takeoff(self, altitude: float) -> bool:
        """Command the vehicle to takeoff to a specific altitude."""
        if not self.mavlink_connection or not self.is_armed:
            print("❌ Cannot takeoff: Vehicle not connected or not armed.")
            return False

        print(f"Commanding takeoff to {altitude}m...")
        self.mavlink_connection.mav.command_long_send(
            self.target_system, self.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0, 0, 0, 0, 0, self.current_state.position[0], self.current_state.position[1], altitude)

        ack_msg = self.mavlink_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
        if ack_msg and ack_msg.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print("✅ Takeoff command accepted.")
            return True
        else:
            print("❌ Takeoff command failed.")
            return False

    async def land(self) -> bool:
        """Command the vehicle to land."""
        if not self.mavlink_connection: return False
        print("Commanding vehicle to land...")
        self.mavlink_connection.mav.command_long_send(
            self.target_system, self.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0, 0, 0, 0, 0, 0, 0, 0)
        
        ack_msg = self.mavlink_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
        if ack_msg and ack_msg.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print("✅ Land command accepted.")
            return True
        else:
            print("❌ Land command failed.")
            return False

    async def start_mission(self, waypoints: np.ndarray) -> bool:
        """Start autonomous mission execution"""
        if not self.is_connected:
            print("❌ Not connected to Pixhawk")
            return False

        print(f"🚀 Starting mission with {len(waypoints)} waypoints")
        self.emergency_stop = False

        # Set first waypoint as goal
        if len(waypoints) > 0:
            self.planner.set_goal(waypoints[-1]) # Set final waypoint as goal
            self.mission_active = True

            # Start control loops
            self.mission_task = asyncio.gather(
                self._control_loop(),
                self._planning_loop(),
                self._telemetry_loop(),
                self._safety_monitor_loop(),
            )
            await self.mission_task
        return True
    
    async def stop_mission(self):
        """Stops the current mission and lands the vehicle."""
        print("Stopping mission...")
        self.mission_active = False
        self.emergency_stop = True
        if self.mission_task:
            self.mission_task.cancel()
        await self.land()


    async def _control_loop(self):
        """High-frequency control loop (400Hz target)"""
        dt = 1.0 / self.config.control_frequency

        while self.mission_active and not self.emergency_stop:
            loop_start = time.perf_counter()

            try:
                if not self.current_trajectory or not self.is_armed:
                    await asyncio.sleep(dt)
                    continue
                
                # Use the geometric controller to compute body-rate commands
                body_rate_cmd = self.controller.compute_body_rate_from_trajectory(
                    self.current_state, self.current_trajectory, time.time()
                )

                # Send body-rate command to Pixhawk
                await self._send_body_rate_target(body_rate_cmd)

                # Performance tracking
                loop_time = (time.perf_counter() - loop_start) * 1000  # ms
                self.performance_stats["control_loop_times"].append(loop_time)
                self.performance_stats["total_commands_sent"] += 1

                # Maintain frequency
                elapsed = time.perf_counter() - loop_start
                if elapsed < dt:
                    await asyncio.sleep(dt - elapsed)

            except Exception as e:
                print(f"❌ Control loop error: {e}")
                await asyncio.sleep(dt)


    async def _planning_loop(self):
        """High-frequency planning loop (50Hz target)"""
        dt = 1.0 / self.config.planning_frequency
        while self.mission_active and not self.emergency_stop:
            loop_start = time.perf_counter()

            try:
                if self.planner.goal_position is None:
                    await asyncio.sleep(dt)
                    continue

                # Update planner with current state and generate new trajectory
                self.current_trajectory = self.planner.plan_trajectory(
                    self.current_state, self.planner.goal_position
                )

                plan_time = (time.perf_counter() - loop_start) * 1000
                self.performance_stats["planning_times"].append(plan_time)
                if plan_time > self.config.max_planning_time_ms:
                    print(f"⚠️ Planning time exceeded: {plan_time:.2f}ms")

            except Exception as e:
                print(f"❌ Planning failure: {e}")
                self.performance_stats["planning_failures"] += 1

            # Maintain frequency
            elapsed = time.perf_counter() - loop_start
            if elapsed < dt:
                await asyncio.sleep(dt - elapsed)

    async def _update_state(self):
        """Update drone state from incoming MAVLink messages."""
        if not self.mavlink_connection:
            return

        while True:
            msg = self.mavlink_connection.recv_match(
                type=["ATTITUDE", "GLOBAL_POSITION_INT", "VFR_HUD", "HEARTBEAT"],
                blocking=False,
            )
            if not msg:
                break

            msg_type = msg.get_type()
            self.current_state.timestamp = time.time()
            if msg_type == "ATTITUDE":
                self.current_state.attitude = np.array([msg.roll, msg.pitch, msg.yaw])
                self.current_state.angular_velocity = np.array([msg.rollspeed, msg.pitchspeed, msg.yawspeed])
                self.last_attitude_msg = time.time()
            elif msg_type == "GLOBAL_POSITION_INT":
                self.current_state.position = np.array([msg.lat / 1e7, msg.lon / 1e7, msg.alt / 1e3])
                self.current_state.velocity = np.array([msg.vx / 100.0, msg.vy / 100.0, msg.vz / 100.0])
            elif msg_type == "HEARTBEAT":
                self.last_heartbeat = time.time()
                self.is_armed = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0

    async def _send_attitude_target(self, q: np.ndarray, thrust: float):
        """Send attitude target command to Pixhawk."""
        if not self.mavlink_connection or not self.is_armed:
            return

        try:
            # Bitmask to use attitude quaternion and thrust, ignore rates
            type_mask = (
                (1 << 0) | # ignore body roll rate
                (1 << 1) | # ignore body pitch rate
                (1 << 2)   # ignore body yaw rate
            )

            self.mavlink_connection.mav.set_attitude_target_send(
                int(time.time() * 1000),  # time_boot_ms
                self.target_system,
                self.target_component,
                type_mask,
                q,  # quaternion
                0,  # body roll rate
                0,  # body pitch rate
                0,  # body yaw rate
                thrust,  # thrust
                0 # thrust-body-set is not supported in ardupilot
            )
        except Exception as e:
            print(f"⚠️ Attitude command failed ({e}); sending position hold fallback")
            await self._send_position_target_hold()

    async def _send_position_target_hold(self):
        """Fallback: hold current position using SET_POSITION_TARGET_LOCAL_NED."""
        if not self.mavlink_connection or not self.is_armed:
            return
        try:
            # Prepare position target in local NED (North-East-Down)
            x, y, z = self.current_state.position  # assuming local frame
            vx, vy, vz = 0.0, 0.0, 0.0
            ax, ay, az = 0.0, 0.0, 0.0
            yaw = self.current_state.attitude[2]
            yaw_rate = 0.0

            # Bitmask: ignore velocity, accel, yaw rate (only position + yaw)
            type_mask = (
                mavutil.mavlink.POSITION_TARGET_TYPEMASK_VEL_IGNORE |
                mavutil.mavlink.POSITION_TARGET_TYPEMASK_ACC_IGNORE |
                mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_RATE_IGNORE
            )

            self.mavlink_connection.mav.set_position_target_local_ned_send(
                int(time.time() * 1000),
                self.target_system,
                self.target_component,
                mavutil.mavlink.MAV_FRAME_LOCAL_NED,
                type_mask,
                x, y, z,
                vx, vy, vz,
                ax, ay, az,
                yaw,
                yaw_rate,
            )
        except Exception as ex:
            print(f"❌ Fallback position command failed: {ex}")

    async def _send_control_command(self, command: ControlCommand):
        """(DEPRECATED) Send low-level control command to Pixhawk."""
        # This method is not used with the MPC planner which provides attitude targets.
        # Kept for compatibility or future use with other controllers.
        pass

    async def _send_body_rate_target(self, body_rate_cmd: BodyRateCommand):
        """Send body-rate target command to Pixhawk."""
        if not self.mavlink_connection or not self.is_armed:
            return

        try:
            # Bitmask to use body rates, ignore thrust
            type_mask = (
                (1 << 0) | # ignore body roll rate
                (1 << 1) | # ignore body pitch rate
                (1 << 2)   # ignore body yaw rate
            )

            self.mavlink_connection.mav.set_attitude_target_send(
                int(time.time() * 1000),  # time_boot_ms
                self.target_system,
                self.target_component,
                type_mask,
                np.array([0, 0, 0, 0]), # quaternion (identity)
                body_rate_cmd.body_rates[0],  # roll rate
                body_rate_cmd.body_rates[1],  # pitch rate
                body_rate_cmd.body_rates[2],  # yaw rate
                body_rate_cmd.thrust,  # thrust
                0 # thrust-body-set is not supported in ardupilot
            )
        except Exception as e:
            print(f"⚠️ Body-rate command failed ({e}); sending position hold fallback")
            await self._send_position_target_hold()

    async def _telemetry_loop(self):
        """Send telemetry data and print status"""
        while self.mission_active and not self.emergency_stop:
            try:
                # Update state from pixhawk
                await self._update_state()

                avg_plan_time = np.mean(self.performance_stats["planning_times"][-50:]) if self.performance_stats["planning_times"] else 0
                avg_ctrl_time = np.mean(self.performance_stats["control_loop_times"][-50:]) if self.performance_stats["control_loop_times"] else 0
                
                print(
                    f"POS: {self.current_state.position[0]:.2f}, {self.current_state.position[1]:.2f}, {self.current_state.position[2]:.2f}m | "
                    f"ATT: {np.rad2deg(self.current_state.attitude[0]):.1f}, {np.rad2deg(self.current_state.attitude[1]):.1f}, {np.rad2deg(self.current_state.attitude[2]):.1f}deg | "
                    f"ARM: {self.is_armed} | "
                    f"PLAN: {avg_plan_time:.1f}ms | CTRL: {avg_ctrl_time:.1f}ms"
                )

                await asyncio.sleep(1.0 / self.config.telemetry_frequency)
            except Exception as e:
                print(f"❌ Telemetry loop error: {e}")
                await asyncio.sleep(1)

    async def _safety_monitor_loop(self):
        """Monitor safety conditions and trigger failsafe if necessary"""
        while self.mission_active and not self.emergency_stop:
            try:
                await self._check_safety_conditions()
                
                # Check for heartbeat timeout using centralized config
                from src.config.settings import get_config
                central_config = get_config()
                
                if time.time() - self.last_heartbeat > central_config.communication.heartbeat.mavlink_timeout_s:
                    await self._trigger_failsafe("Heartbeat lost")
                
                # New watchdog: attitude or heartbeat gap >300 ms
                if time.time() - max(self.last_heartbeat, self.last_attitude_msg) > 0.3:
                    await self._trigger_failsafe("Telemetry timeout >300 ms")

                await asyncio.sleep(1) # Check every second
            except Exception as e:
                print(f"❌ Safety monitor error: {e}")

    async def _check_safety_conditions(self):
        """Check for violation of safety limits."""
        if np.linalg.norm(self.current_state.velocity) > self.config.max_velocity:
            await self._trigger_failsafe(f"Velocity exceeded limit: {np.linalg.norm(self.current_state.velocity):.1f}m/s")
        
        if self.current_state.position[2] > self.config.max_altitude:
            await self._trigger_failsafe(f"Altitude exceeded limit: {self.current_state.position[2]:.1f}m")

    async def _trigger_failsafe(self, reason: str):
        """Trigger emergency failsafe"""
        if not self.failsafe_active:
            print(f"�� FAILSAFE TRIGGERED: {reason} 🚨")
            self.failsafe_active = True
            self.emergency_stop = True
            await self.land()

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        report = {}
        if self.performance_stats["planning_times"]:
            report["avg_planning_time_ms"] = np.mean(self.performance_stats["planning_times"])
            report["max_planning_time_ms"] = np.max(self.performance_stats["planning_times"])
            report["p95_planning_time_ms"] = np.percentile(self.performance_stats["planning_times"], 95)
        
        if self.performance_stats["control_loop_times"]:
            report["avg_control_loop_time_ms"] = np.mean(self.performance_stats["control_loop_times"])
            report["max_control_loop_time_ms"] = np.max(self.performance_stats["control_loop_times"])

        if self.performance_stats["control_loop_times"]:
            total_duration = (len(self.performance_stats["control_loop_times"]) * (1/self.config.control_frequency))
            if total_duration > 0:
                report["achieved_control_frequency_hz"] = len(self.performance_stats["control_loop_times"]) / total_duration

        report["total_commands_sent"] = self.performance_stats["total_commands_sent"]
        report["planning_failures"] = self.performance_stats["planning_failures"]
        return report

    async def get_current_mode(self) -> str:
        """Get the current flight mode of the vehicle."""
        if not self.mavlink_connection:
            return "DISCONNECTED"
        try:
            msg = self.mavlink_connection.recv_match(
                type='HEARTBEAT',
                blocking=True,
                timeout=1.0,
            )
            if msg:
                return self.mavlink_connection.mode_mapping().get(msg.custom_mode, "UNKNOWN")
            return "NO_HEARTBEAT"
        except Exception as e:
            print(f"Error getting current mode: {e}")
            return "ERROR"


async def main():
    """Demonstrates basic instantiation of the PixhawkInterface."""
    print("PixhawkInterface class can be instantiated.")
    # This main function is intentionally simple.
    # For a full mission execution example, see examples/run_pixhawk_mission.py
    interface = PixhawkInterface()
    print(f"Initialized with config for: {interface.config.mavlink_connection}")


if __name__ == "__main__":
    asyncio.run(main())
