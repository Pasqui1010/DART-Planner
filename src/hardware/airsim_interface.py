"""
AirSim Integration Interface for DART-Planner
Connects optimized SE(3) MPC planner with AirSim realistic simulation
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.common.types import ControlCommand, DroneState
from src.control.geometric_controller import GeometricController
from src.planning.se3_mpc_planner import SE3MPCConfig, SE3MPCPlanner

try:
    import airsim

    AIRSIM_AVAILABLE = True
except ImportError:
    AIRSIM_AVAILABLE = False
    print("⚠️ AirSim not available. Install with: pip install airsim")

try:
    from pymavlink import mavutil

    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False
    print("⚠️ MAVLink not available. Install with: pip install pymavlink")


@dataclass
class AirSimConfig:
    """Configuration for AirSim integration"""

    # AirSim connection
    airsim_ip: str = "127.0.0.1"
    airsim_port: int = 41451

    # Control frequencies - conservative from 479Hz simulation success
    control_frequency: float = 200.0  # Hz - realistic for AirSim
    planning_frequency: float = 10.0  # Hz - DART-Planner frequency
    telemetry_frequency: float = 5.0  # Hz - status reporting

    # Performance monitoring
    max_planning_time_ms: float = 15.0  # Conservative for AirSim
    enable_performance_logging: bool = True

    # Safety limits
    max_velocity: float = 15.0  # m/s
    max_altitude: float = 50.0  # m
    waypoint_tolerance: float = 2.0  # m


class AirSimInterface:
    """
    DART-Planner integration with AirSim simulation

    Validates the optimized SE(3) MPC planner in realistic physics simulation
    before hardware deployment.
    """

    def __init__(self, config: Optional[AirSimConfig] = None):
        if not AIRSIM_AVAILABLE:
            raise ImportError("AirSim not available. Install with: pip install airsim")

        self.config = config if config else AirSimConfig()

        # Initialize DART-Planner with optimized settings
        planner_config = SE3MPCConfig(
            prediction_horizon=6,  # From breakthrough optimization
            dt=0.15,  # Slightly longer for AirSim physics
            max_iterations=20,
            convergence_tolerance=1e-2,
        )
        self.planner = SE3MPCPlanner(planner_config)
        self.controller = GeometricController()

        # AirSim client
        self.airsim_client = None
        self.is_connected = False

        # Mission state
        self.current_state = DroneState(timestamp=time.time())
        self.mission_waypoints: List[np.ndarray] = []
        self.current_waypoint_index = 0
        self.mission_active = False

        # Performance tracking
        self.performance_stats = {
            "control_loop_times": [],
            "planning_times": [],
            "total_planning_calls": 0,
            "planning_failures": 0,
            "achieved_frequency": 0.0,
        }

        print(f"🎮 DART-Planner AirSim Interface initialized")
        print(f"   Control frequency: {self.config.control_frequency}Hz")
        print(f"   Planning frequency: {self.config.planning_frequency}Hz")

    async def connect(self) -> bool:
        """Connect to AirSim"""
        try:
            print(f"🔗 Connecting to AirSim at {self.config.airsim_ip}")

            self.airsim_client = airsim.MultirotorClient(
                ip=self.config.airsim_ip, port=self.config.airsim_port
            )
            self.airsim_client.confirmConnection()
            self.airsim_client.enableApiControl(True)

            print("✅ AirSim connected successfully!")
            self.is_connected = True

            # Initialize vehicle
            await self._initialize_vehicle()

            return True

        except Exception as e:
            print(f"❌ AirSim connection failed: {e}")
            return False

    async def _initialize_vehicle(self):
        """Initialize AirSim vehicle"""
        if not self.airsim_client:
            return

        print("🚁 Initializing vehicle...")

        # Reset and arm
        self.airsim_client.reset()
        await asyncio.sleep(1)

        self.airsim_client.armDisarm(True)
        await asyncio.sleep(1)

        # Takeoff
        print("🛫 Taking off...")
        self.airsim_client.takeoffAsync().join()
        await asyncio.sleep(3)

        print("✅ Vehicle ready for DART-Planner mission")

    async def start_mission(self, waypoints: List[np.ndarray]) -> bool:
        """Start DART-Planner autonomous mission"""
        if not self.is_connected:
            print("❌ Not connected to AirSim")
            return False

        # Convert waypoints to AirSim NED coordinates
        self.mission_waypoints = []
        for wp in waypoints:
            # Convert from ENU to NED (AirSim coordinate system)
            ned_wp = np.array([wp[0], wp[1], -abs(wp[2])])  # Negative Z for altitude
            self.mission_waypoints.append(ned_wp)

        self.current_waypoint_index = 0
        self.mission_active = True

        print(f"🚀 Starting DART-Planner mission: {len(waypoints)} waypoints")

        # Set first goal
        if self.mission_waypoints:
            self.planner.set_goal(self.mission_waypoints[0])

        # Start control loops
        await asyncio.gather(
            self._dart_control_loop(),
            self._mission_manager(),
            self._performance_monitor(),
        )

        return True

    async def _dart_control_loop(self):
        """Main DART-Planner control loop"""
        dt = 1.0 / self.config.control_frequency

        while self.mission_active:
            loop_start = time.perf_counter()

            try:
                # Update state from AirSim
                self._update_state()

                # DART-Planner trajectory optimization
                if self.planner.goal_position is not None:
                    planning_start = time.perf_counter()

                    trajectory = self.planner.plan_trajectory(
                        self.current_state, self.planner.goal_position
                    )

                    planning_time = (time.perf_counter() - planning_start) * 1000
                    self.performance_stats["planning_times"].append(planning_time)
                    self.performance_stats["total_planning_calls"] += 1

                    if planning_time > self.config.max_planning_time_ms:
                        print(f"⚠️ Slow planning: {planning_time:.1f}ms")

                    # Send trajectory to AirSim
                    await self._execute_trajectory(trajectory)

                # Track performance
                loop_time = (time.perf_counter() - loop_start) * 1000
                self.performance_stats["control_loop_times"].append(loop_time)

                # Maintain frequency
                elapsed = time.perf_counter() - loop_start
                if elapsed < dt:
                    await asyncio.sleep(dt - elapsed)

            except Exception as e:
                print(f"⚠️ Control loop error: {e}")
                self.performance_stats["planning_failures"] += 1
                await asyncio.sleep(dt)

    def _update_state(self):
        """Update drone state from AirSim"""
        if not self.airsim_client:
            return

        state = self.airsim_client.getMultirotorState()
        kinematics = state.kinematics_estimated

        # Convert NED to ENU coordinates
        position = np.array(
            [
                kinematics.position.x_val,
                kinematics.position.y_val,
                -kinematics.position.z_val,  # Convert NED to ENU
            ]
        )

        velocity = np.array(
            [
                kinematics.linear_velocity.x_val,
                kinematics.linear_velocity.y_val,
                -kinematics.linear_velocity.z_val,
            ]
        )

        # Convert quaternion to Euler
        q = kinematics.orientation
        attitude = self._quat_to_euler(q.w_val, q.x_val, q.y_val, q.z_val)

        self.current_state = DroneState(
            timestamp=time.time(),
            position=position,
            velocity=velocity,
            attitude=attitude,
            angular_velocity=np.array(
                [
                    kinematics.angular_velocity.x_val,
                    kinematics.angular_velocity.y_val,
                    kinematics.angular_velocity.z_val,
                ]
            ),
        )

    async def _execute_trajectory(self, trajectory):
        """Execute DART-Planner trajectory in AirSim"""
        if not self.airsim_client or len(trajectory.positions) < 2:
            return

        # Get immediate target from trajectory
        target_pos = trajectory.positions[1]  # Next position
        target_vel = (
            trajectory.velocities[1] if len(trajectory.velocities) > 1 else np.zeros(3)
        )

        # Use velocity control for smooth motion
        self.airsim_client.moveByVelocityAsync(
            target_vel[0],
            target_vel[1],
            target_vel[2],
            1.0 / self.config.planning_frequency,
        )

    async def _mission_manager(self):
        """Manage waypoint progression"""
        while self.mission_active:
            if (
                self.current_waypoint_index < len(self.mission_waypoints)
                and self.planner.goal_position is not None
            ):
                # Check if reached current waypoint
                distance = np.linalg.norm(
                    self.current_state.position - self.planner.goal_position
                )

                if distance < self.config.waypoint_tolerance:
                    print(
                        f"✅ Waypoint {self.current_waypoint_index + 1}/{len(self.mission_waypoints)} reached"
                    )
                    self.current_waypoint_index += 1

                    if self.current_waypoint_index < len(self.mission_waypoints):
                        next_goal = self.mission_waypoints[self.current_waypoint_index]
                        self.planner.set_goal(next_goal)
                        print(f"🎯 Next: {next_goal}")
                    else:
                        print("🏁 Mission complete!")
                        self.mission_active = False

            await asyncio.sleep(1.0)

    async def _performance_monitor(self):
        """Monitor DART-Planner performance in AirSim"""
        dt = 1.0 / self.config.telemetry_frequency

        while self.mission_active:
            if self.performance_stats["control_loop_times"]:
                recent_times = self.performance_stats["control_loop_times"][-50:]
                avg_time = np.mean(recent_times)
                self.performance_stats["achieved_frequency"] = 1000.0 / avg_time

                if len(recent_times) == 50:  # Report every 50 cycles
                    avg_planning = np.mean(
                        self.performance_stats["planning_times"][-20:]
                    )

                    print(
                        f"📊 DART Performance: {self.performance_stats['achieved_frequency']:.0f}Hz, "
                        f"Planning: {avg_planning:.1f}ms, Pos: {self.current_state.position}"
                    )

            await asyncio.sleep(dt)

    def _quat_to_euler(self, w, x, y, z) -> np.ndarray:
        """Convert quaternion to Euler angles"""
        # Roll
        sinr = 2 * (w * x + y * z)
        cosr = 1 - 2 * (x * x + y * y)
        roll = np.arctan2(sinr, cosr)

        # Pitch
        sinp = 2 * (w * y - z * x)
        pitch = np.arcsin(np.clip(sinp, -1, 1))

        # Yaw
        siny = 2 * (w * z + x * y)
        cosy = 1 - 2 * (y * y + z * z)
        yaw = np.arctan2(siny, cosy)

        return np.array([roll, pitch, yaw])

    async def land_and_disarm(self):
        """Safe mission completion"""
        if self.airsim_client:
            print("🛬 Landing...")
            self.airsim_client.landAsync().join()
            await asyncio.sleep(3)

            self.airsim_client.armDisarm(False)
            self.airsim_client.enableApiControl(False)

        self.mission_active = False
        print("✅ Mission completed")

    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance metrics"""
        if not self.performance_stats["control_loop_times"]:
            return {"status": "no_data"}

        return {
            "mission_active": self.mission_active,
            "waypoint_progress": f"{self.current_waypoint_index}/{len(self.mission_waypoints)}",
            "achieved_frequency": self.performance_stats["achieved_frequency"],
            "mean_planning_time_ms": float(
                np.mean(self.performance_stats["planning_times"])
            ),
            "planning_success_rate": 1.0
            - (
                self.performance_stats["planning_failures"]
                / max(self.performance_stats["total_planning_calls"], 1)
            ),
            "current_position": self.current_state.position.tolist(),
            "connected": self.is_connected,
        }


# Test function
async def test_dart_airsim():
    """Test DART-Planner with AirSim"""
    print("🎮 DART-Planner AirSim Validation Test")
    print("=" * 50)

    config = AirSimConfig(
        control_frequency=100.0,  # Conservative for initial test
        planning_frequency=5.0,
    )

    interface = AirSimInterface(config)

    if await interface.connect():
        # Test mission: square pattern at 10m altitude
        waypoints = [
            np.array([20.0, 0.0, 10.0]),
            np.array([20.0, 20.0, 10.0]),
            np.array([0.0, 20.0, 10.0]),
            np.array([0.0, 0.0, 10.0]),
        ]

        await interface.start_mission(waypoints)
        await interface.land_and_disarm()

        # Performance report
        report = interface.get_performance_report()
        print("\n📊 DART-Planner AirSim Performance:")
        for key, value in report.items():
            print(f"   {key}: {value}")
    else:
        print("❌ AirSim connection failed")


if __name__ == "__main__":
    asyncio.run(test_dart_airsim())
