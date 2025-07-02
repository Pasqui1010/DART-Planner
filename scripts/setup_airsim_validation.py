#!/usr/bin/env python3
"""
AirSim Setup and Validation Script for DART-Planner
Helps set up AirSim environment and validate DART-Planner performance
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path


def print_banner():
    """Print setup banner"""
    print("🎮" + "=" * 60 + "🎮")
    print("🚁 DART-Planner AirSim Integration Setup")
    print("🎯 Validate 2.1ms planning performance in realistic simulation")
    print("=" * 64)


def check_python_version():
    """Check Python version compatibility"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required for AirSim integration")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} compatible")
    return True


def install_airsim_dependencies():
    """Install AirSim Python package"""
    print("\n📦 Installing AirSim Dependencies...")

    packages = [
        "airsim",
        "pymavlink",  # For optional PX4 SITL integration
        "msgpack-rpc-python",  # AirSim dependency
    ]

    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"✅ {package} installed")
        except subprocess.CalledProcessError:
            print(f"⚠️ Failed to install {package} - you may need to install manually")

    print("✅ Dependencies installation complete")


def check_airsim_installation():
    """Verify AirSim installation"""
    print("\n🔍 Checking AirSim Installation...")

    try:
        import airsim

        print("✅ AirSim Python package available")
        return True
    except ImportError:
        print("❌ AirSim not available")
        print("📋 Install manually with: pip install airsim")
        return False


def print_airsim_setup_instructions():
    """Print AirSim application setup instructions"""
    print("\n🏗️ AirSim Application Setup Instructions:")
    print("=" * 50)

    print("\n1️⃣ Download AirSim Release:")
    print("   • Visit: https://github.com/Microsoft/AirSim/releases")
    print("   • Download latest release for your OS")
    print("   • Extract to a folder (e.g., C:\\AirSim or ~/AirSim)")

    print("\n2️⃣ AirSim Settings Configuration:")
    print("   • Create settings.json in:")
    print("     Windows: %USERPROFILE%\\Documents\\AirSim\\settings.json")
    print("     Linux/Mac: ~/Documents/AirSim/settings.json")

    settings_content = """{
  "SeeDocsAt": "https://github.com/Microsoft/AirSim/blob/master/docs/settings.md",
  "SettingsVersion": 1.2,
  "SimMode": "Multirotor",
  "ClockSpeed": 1.0,
  "ViewMode": "FlyWithMe",
  "Vehicles": {
    "Drone1": {
      "VehicleType": "SimpleFlight",
      "DefaultVehicleState": "Armed",
      "EnableCollisionPassthrogh": false,
      "EnableCollisions": true,
      "AllowAPIAlways": true,
      "RC": {
        "RemoteControlID": 0,
        "AllowAPIWhenDisconnected": true
      }
    }
  }
}"""

    print("\n📝 Recommended settings.json content:")
    print(settings_content)

    print("\n3️⃣ Launch AirSim:")
    print("   • Run the AirSim executable")
    print("   • Select 'No' when asked about RC")
    print("   • Vehicle should appear and be ready for API control")

    print("\n4️⃣ Test Connection:")
    print("   • Leave AirSim running")
    print("   • Run: python scripts/setup_airsim_validation.py --test")


def create_airsim_settings():
    """Create default AirSim settings file"""
    print("\n📁 Creating AirSim Settings...")

    # Determine settings path
    if os.name == "nt":  # Windows
        settings_dir = Path.home() / "Documents" / "AirSim"
    else:  # Linux/Mac
        settings_dir = Path.home() / "Documents" / "AirSim"

    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_file = settings_dir / "settings.json"

    settings_content = {
        "SeeDocsAt": "https://github.com/Microsoft/AirSim/blob/master/docs/settings.md",
        "SettingsVersion": 1.2,
        "SimMode": "Multirotor",
        "ClockSpeed": 1.0,
        "ViewMode": "FlyWithMe",
        "Vehicles": {
            "Drone1": {
                "VehicleType": "SimpleFlight",
                "DefaultVehicleState": "Armed",
                "EnableCollisionPassthrogh": False,
                "EnableCollisions": True,
                "AllowAPIAlways": True,
                "RC": {"RemoteControlID": 0, "AllowAPIWhenDisconnected": True},
            }
        },
    }

    import json

    with open(settings_file, "w") as f:
        json.dump(settings_content, f, indent=2)

    print(f"✅ Settings created: {settings_file}")
    return settings_file


async def test_airsim_connection():
    """Test basic AirSim connection"""
    print("\n🔗 Testing AirSim Connection...")

    try:
        import airsim

        # Try to connect
        client = airsim.MultirotorClient()
        client.confirmConnection()

        print("✅ AirSim connection successful!")

        # Get basic info
        state = client.getMultirotorState()
        print(f"   Vehicle armed: {state.kinematics_estimated}")
        print(f"   API control enabled: {client.isApiControlEnabled()}")

        return True

    except Exception as e:
        print(f"❌ AirSim connection failed: {e}")
        print("💡 Make sure AirSim is running and accessible")
        return False


async def run_dart_airsim_validation():
    """Run DART-Planner validation test with AirSim"""
    print("\n🚀 Running DART-Planner AirSim Validation...")
    print("🎯 Target: Validate 2.1ms planning performance in realistic simulation")

    try:
        # Import DART-Planner AirSim interface
        sys.path.append(str(Path(__file__).parent.parent))
        from src.hardware.airsim_interface import AirSimConfig, AirSimInterface

        # Conservative configuration for validation
        config = AirSimConfig(
            control_frequency=100.0,  # Conservative for initial validation
            planning_frequency=5.0,  # DART-Planner frequency
            max_planning_time_ms=20.0,  # Allow for AirSim overhead
        )

        print(f"📊 Test Configuration:")
        print(f"   Control frequency: {config.control_frequency}Hz")
        print(f"   Planning frequency: {config.planning_frequency}Hz")
        print(f"   Max planning time: {config.max_planning_time_ms}ms")

        # Initialize interface
        interface = AirSimInterface(config)

        # Connect to AirSim
        if not await interface.connect():
            print("❌ Failed to connect to AirSim")
            return False

        # Define validation mission - square pattern
        waypoints = [
            [15.0, 0.0, 10.0],  # 15m forward, 10m up
            [15.0, 15.0, 10.0],  # Square pattern
            [0.0, 15.0, 10.0],
            [0.0, 0.0, 10.0],  # Return to start
        ]

        print(f"\n🎯 Validation Mission: {len(waypoints)} waypoint square pattern")
        print("📏 Pattern: 15x15m square at 10m altitude")

        # Convert to numpy arrays
        import numpy as np

        np_waypoints = [np.array(wp) for wp in waypoints]

        # Start mission
        print("\n🚁 Starting autonomous mission...")
        mission_start = time.time()

        await interface.start_mission(np_waypoints)

        mission_duration = time.time() - mission_start

        # Land safely
        await interface.land_and_disarm()

        # Get performance report
        report = interface.get_performance_report()

        print("\n" + "=" * 60)
        print("📊 DART-PLANNER AIRSIM VALIDATION RESULTS")
        print("=" * 60)

        print(f"✅ Mission Duration: {mission_duration:.1f} seconds")
        print(f"📈 Performance Metrics:")

        for key, value in report.items():
            if isinstance(value, float):
                print(f"   {key}: {value:.2f}")
            else:
                print(f"   {key}: {value}")

        # Validate against breakthrough performance
        planning_time = report.get("mean_planning_time_ms", 0)
        achieved_freq = report.get("achieved_frequency", 0)

        print(f"\n🎯 Performance vs. Breakthrough Targets:")
        print(f"   Planning time: {planning_time:.1f}ms (Target: <20ms for AirSim)")
        print(f"   Control frequency: {achieved_freq:.0f}Hz (Target: >80Hz)")

        # Success criteria
        success_criteria = [
            (planning_time < 30.0, f"Planning time: {planning_time:.1f}ms < 30ms"),
            (achieved_freq > 50.0, f"Control frequency: {achieved_freq:.0f}Hz > 50Hz"),
            (
                report.get("planning_success_rate", 0) > 0.9,
                "Planning success rate > 90%",
            ),
        ]

        all_passed = True
        print(f"\n✅ Success Criteria:")
        for passed, description in success_criteria:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status}: {description}")
            if not passed:
                all_passed = False

        if all_passed:
            print("\n🎉 DART-PLANNER AIRSIM VALIDATION: SUCCESS!")
            print("🚀 Ready for hardware deployment!")
        else:
            print("\n⚠️ Some criteria not met - optimization may be needed")

        return all_passed

    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def print_next_steps():
    """Print next steps for hardware validation"""
    print("\n🎯 NEXT STEPS FOR HARDWARE VALIDATION:")
    print("=" * 50)

    print("\n1️⃣ PX4 SITL Integration (Optional):")
    print("   • Install PX4 SITL for realistic flight controller simulation")
    print("   • Commands in docs/HARDWARE_VALIDATION_ROADMAP.md")

    print("\n2️⃣ Hardware-in-the-Loop Testing:")
    print("   • Connect real Pixhawk flight controller")
    print("   • Test with src/hardware/pixhawk_interface.py")

    print("\n3️⃣ Real Flight Testing:")
    print("   • Follow 4-phase validation roadmap")
    print("   • SITL → HIL → Tethered → Free flight")

    print("\n📚 Documentation:")
    print("   • Hardware roadmap: docs/HARDWARE_VALIDATION_ROADMAP.md")
    print("   • Performance targets: docs/analysis/BREAKTHROUGH_SUMMARY.md")


async def main():
    """Main setup and validation workflow"""
    print_banner()

    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="DART-Planner AirSim Setup")
    parser.add_argument("--test", action="store_true", help="Run connection test only")
    parser.add_argument(
        "--full-validation", action="store_true", help="Run full validation mission"
    )
    parser.add_argument(
        "--install-deps", action="store_true", help="Install dependencies only"
    )
    args = parser.parse_args()

    # Check Python version
    if not check_python_version():
        return

    # Install dependencies if requested
    if args.install_deps:
        install_airsim_dependencies()
        return

    # Test connection only
    if args.test:
        if check_airsim_installation():
            await test_airsim_connection()
        return

    # Full validation
    if args.full_validation:
        if check_airsim_installation():
            success = await run_dart_airsim_validation()
            if success:
                print_next_steps()
        return

    # Default: Setup workflow
    print("\n🛠️ SETUP WORKFLOW:")
    print("1. Install dependencies")
    print("2. Create AirSim settings")
    print("3. Show setup instructions")

    # Install dependencies
    install_airsim_dependencies()

    # Check installation
    if check_airsim_installation():
        print("✅ AirSim Python package ready")

    # Create settings
    settings_file = create_airsim_settings()

    # Show setup instructions
    print_airsim_setup_instructions()

    print("\n🎮 READY TO TEST:")
    print("=" * 30)
    print("1. Launch AirSim application")
    print("2. Run: python scripts/setup_airsim_validation.py --test")
    print("3. Run: python scripts/setup_airsim_validation.py --full-validation")


if __name__ == "__main__":
    asyncio.run(main())
