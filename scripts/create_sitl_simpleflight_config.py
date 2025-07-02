#!/usr/bin/env python3
"""
Create SimpleFlight configuration for DART-Planner SITL testing
"""

import json
from pathlib import Path


def create_simpleflight_config():
    """Create optimized SimpleFlight config for DART-Planner"""

    # SimpleFlight configuration optimized for DART-Planner
    config = {
        "SettingsVersion": 1.2,
        "SimMode": "Multirotor",
        "LogMessagesVisible": True,
        "Vehicles": {
            "Copter": {
                "VehicleType": "SimpleFlight",
                "EnableApiControl": True,
                "AllowApiAlways": True,
                "RC": {"RemoteControlID": 0, "AllowAPIWhenDisconnected": True},
            }
        },
        "Recording": {"RecordOnMove": False, "RecordInterval": 0.05},
    }

    settings_path = Path.home() / "Documents" / "AirSim" / "settings.json"

    # Backup existing
    if settings_path.exists():
        backup_path = settings_path.with_suffix(".json.backup")
        settings_path.rename(backup_path)
        print(f"📋 Backed up existing settings to: {backup_path}")

    # Write new config
    with open(settings_path, "w") as f:
        json.dump(config, f, indent=2)

    print("✅ Created SimpleFlight configuration for DART-Planner")
    print(f"📄 Location: {settings_path}")
    print("\n🚁 Configuration details:")
    print("   • Vehicle Type: SimpleFlight (built-in)")
    print("   • API Control: Always enabled")
    print("   • Remote Control: Allows API when disconnected")
    print("   • Recording: Optimized for performance")

    print("\n🧪 Test this configuration:")
    print("   1. Launch AirSim Blocks")
    print("   2. Press Play")
    print("   3. Should work without freezing!")

    return config


def create_dart_simpleflight_interface():
    """Create DART-Planner interface for SimpleFlight"""

    interface_code = '''#!/usr/bin/env python3
"""
SimpleFlight Interface for DART-Planner SITL Testing
"""

import asyncio
import numpy as np
import airsim
from src.hardware.pixhawk_interface import PixhawkInterface, HardwareConfig

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
            
            print("✅ Connected to SimpleFlight via AirSim API")
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def takeoff(self, altitude: float = 5.0):
        """Takeoff to specified altitude"""
        if not self.is_connected:
            return False
            
        print(f"🚀 Taking off to {altitude}m...")
        self.client.takeoffAsync().join()
        self.client.moveToZAsync(-altitude, 3).join()  # NED coordinates
        print("✅ Takeoff complete")
        return True
    
    async def goto_position(self, position: np.ndarray, velocity: float = 5.0):
        """Fly to specified position"""
        if not self.is_connected:
            return False
            
        x, y, z = position
        print(f"🎯 Flying to ({x:.1f}, {y:.1f}, {z:.1f})")
        
        # AirSim uses NED coordinates (Z is negative for altitude)
        self.client.moveToPositionAsync(x, y, -z, velocity).join()
        print("✅ Position reached")
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
            np.array([0, 0, altitude])
        ]
        
        for i, wp in enumerate(waypoints):
            print(f"📍 Waypoint {i+1}/4")
            await self.goto_position(wp)
            await asyncio.sleep(2)  # Pause at each waypoint
        
        print("🏁 Mission complete - landing")
        self.client.landAsync().join()
        return True

async def main():
    """Test SimpleFlight interface"""
    interface = SimpleFLightInterface()
    
    if await interface.connect():
        await interface.run_square_mission()
    else:
        print("❌ Failed to connect to SimpleFlight")

if __name__ == "__main__":
    asyncio.run(main())
'''

    interface_path = Path("scripts") / "test_simpleflight_interface.py"
    with open(interface_path, "w") as f:
        f.write(interface_code)

    print(f"✅ Created SimpleFlight interface: {interface_path}")
    return interface_path


if __name__ == "__main__":
    print("🔧 Setting up SimpleFlight for DART-Planner SITL testing")
    print("=" * 60)

    # Create config
    config = create_simpleflight_config()

    # Create interface
    interface_path = create_dart_simpleflight_interface()

    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    print("1. Test AirSim with new SimpleFlight config")
    print("2. If it works, run the test interface:")
    print(f"   python {interface_path}")
    print("3. This will validate DART-Planner can control the drone")
    print("\n💡 SimpleFlight vs ArduCopter:")
    print("   • SimpleFlight: Built-in, works immediately")
    print("   • ArduCopter: Requires rebuilding AirSim with ArduPilot support")
    print("   • For SITL testing, SimpleFlight is often sufficient")
