# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Improved Three-Layer Cloud Architecture with SE(3) MPC

This implements the audit's recommendation to replace DIAL-MPC with
a controller specifically designed for aerial robotics.
"""

import asyncio
import time
from typing import Optional

import numpy as np

from common.types import DroneState, Trajectory
from communication.zmq_server import ZmqServer
from perception.explicit_geometric_mapper import ExplicitGeometricMapper
from planning.global_mission_planner import GlobalMissionConfig, GlobalMissionPlanner
from planning.se3_mpc_planner import SE3MPCConfig, SE3MPCPlanner


class ImprovedThreeLayerCloudController:
    """
    Improved Three-Layer Cloud Architecture

    This addresses the audit's critical flaws:

    Layer 2: SE(3) MPC Trajectory Optimizer (10Hz) [FIXED]
    ├─ Proper aerial robotics formulation (not legged robots)
    ├─ Proven SE(3) geometric constraints
    ├─ Computationally efficient optimization
    └─ Industry-standard approach
    """

    def __init__(self, port: int = 5555):
        # Initialize communication
        self.server = ZmqServer(str(port))

        # SE(3) MPC - proper controller for aerial robotics
        self.se3_mpc = SE3MPCPlanner(
            SE3MPCConfig(
                prediction_horizon=20,
                dt=0.1,
                max_velocity=8.0,
                max_acceleration=4.0,
                position_weight=100.0,
                velocity_weight=10.0,
                obstacle_weight=1000.0,
                safety_margin=1.5,
            )
        )

        # Explicit geometric mapper - replaces neural oracle
        self.geometric_mapper = ExplicitGeometricMapper(resolution=0.2, max_range=50.0)

        # System state
        self.current_drone_state: Optional[DroneState] = None
        self.planning_stats = {"se3_mpc_plans": 0, "planning_failures": 0}

        print("Improved Cloud Controller Initialized")
        print("   SE(3) MPC (FIXED - no longer DIAL-MPC)")
        print("   Explicit Geometric Mapping")

    async def run_planning_loop(self):
        """Main planning loop with SE(3) MPC."""
        print("Starting improved planning loop...")

        # Add some obstacles for demonstration
        self.geometric_mapper.add_obstacle(np.array([15.0, 5.0, 5.0]), 2.0)
        self.geometric_mapper.add_obstacle(np.array([25.0, 15.0, 7.0]), 1.5)

        while True:
            try:
                # Receive current state from edge
                state_data = self.server.receive_state()
                if state_data:
                    self.current_drone_state = self._parse_state(state_data)

                    # Execute SE(3) MPC planning
                    trajectory = await self._execute_se3_planning()

                    if trajectory and self._validate_trajectory_safety(trajectory):
                        self.server.send_trajectory(trajectory)
                        self.planning_stats["se3_mpc_plans"] += 1

                        if self.planning_stats["se3_mpc_plans"] % 10 == 0:
                            stats = self.se3_mpc.get_performance_stats()
                            print(
                                f"SE(3) MPC: {stats.get('mean_planning_time_ms', 0):.1f}ms avg"
                            )

                await asyncio.sleep(0.1)  # 10Hz

            except Exception as e:
                print(f"Planning error: {e}")
                self.planning_stats["planning_failures"] += 1
                await asyncio.sleep(0.1)

    async def _execute_se3_planning(self) -> Optional[Trajectory]:
        """Execute SE(3) MPC trajectory planning."""
        if not self.current_drone_state:
            return None

        # Simple goal: move forward and up
        goal_position = self.current_drone_state.position + np.array([10.0, 5.0, 2.0])

        try:
            trajectory = self.se3_mpc.plan_trajectory(
                self.current_drone_state, goal_position
            )
            return trajectory
        except Exception as e:
            print(f"SE(3) MPC planning failed: {e}")
            return None

    def _validate_trajectory_safety(self, trajectory: Trajectory) -> bool:
        """Validate trajectory safety using explicit geometric mapping."""
        if trajectory.positions is None or len(trajectory.positions) == 0:
            return False

        is_safe, _ = self.geometric_mapper.is_trajectory_safe(
            trajectory.positions, safety_margin=1.5, threshold=0.6
        )

        return is_safe

    def _parse_state(self, state_data: dict) -> DroneState:
        """Parse state data from edge node."""
        return DroneState(
            timestamp=state_data.get("timestamp", time.time()),
            position=np.array(state_data.get("position", [0, 0, 0])),
            velocity=np.array(state_data.get("velocity", [0, 0, 0])),
            attitude=np.array(state_data.get("attitude", [0, 0, 0])),
            angular_velocity=np.array(state_data.get("angular_velocity", [0, 0, 0])),
        )


async def main():
    """Run the improved cloud controller."""
    controller = ImprovedThreeLayerCloudController()
    await controller.run_planning_loop()


if __name__ == "__main__":
    asyncio.run(main())
