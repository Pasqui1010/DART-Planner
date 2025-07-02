#!/usr/bin/env python3
"""
SimpleFlight Interface for DART-Planner SITL Testing
"""

import asyncio

import airsim
import numpy as np


class SimpleFLightInterface:
    """
    SimpleFlight interface for DART-Planner testing
    Uses AirSim API instead of MAVLink
    """

    def __init__(self):
        self.client = None
        self.is_connected = False
        self.mission_active = False

    async def connect(self) -> bool:
        """Connect to AirSim SimpleFlight"""
        try:
            self.client = airsim.MultirotorClient()
            self.client.confirmConnection()
            self.client.enableApiControl(True)
            self.client.armDisarm(True)

            print("Connected to SimpleFlight via AirSim API")
            self.is_connected = True
            return True

        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    async def takeoff(self, altitude: float = 5.0):
        """Takeoff to specified altitude"""
        if not self.is_connected:
            return False

        print(f"Taking off to {altitude}m...")
        self.client.takeoffAsync().join()
        self.client.moveToZAsync(-altitude, 3).join()  # NED coordinates
        print("Takeoff complete")
        return True

    async def goto_position(self, position: np.ndarray, velocity: float = 5.0):
        """Fly to specified position"""
        if not self.is_connected:
            return False

        x, y, z = position
        print(f"Flying to ({x:.1f}, {y:.1f}, {z:.1f})")

        # AirSim uses NED coordinates (Z is negative for altitude)
        self.client.moveToPositionAsync(x, y, -z, velocity).join()
        print("Position reached")
        return True

    async def run_square_mission(self, size: float = 10.0, altitude: float = 5.0):
        """Run a simple square mission for testing"""
        if not await self.takeoff(altitude):
            return False

        # Square waypoints
        waypoints = [
            np.array([size, 0, altitude]),
            np.array([size, size, altitude]),
            np.array([0, size, altitude]),
            np.array([0, 0, altitude]),
        ]

        for i, wp in enumerate(waypoints):
            print(f"Waypoint {i+1}/4")
            await self.goto_position(wp)
            await asyncio.sleep(2)  # Pause at each waypoint

        print("Mission complete - landing")
        self.client.landAsync().join()
        return True


async def main():
    """Test SimpleFlight interface"""
    interface = SimpleFLightInterface()

    if await interface.connect():
        await interface.run_square_mission()
    else:
        print("Failed to connect to SimpleFlight")


if __name__ == "__main__":
    asyncio.run(main())
