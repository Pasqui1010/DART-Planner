#!/usr/bin/env python3
"""
SimpleFlight Configuration Tester
Tests the SimpleFlight vehicle configuration with AirSim
"""

import os
import sys
import time

import airsim


def test_simpleflight_connection():
    """Test connection to AirSim with SimpleFlight vehicle."""
    print("🧪 Testing SimpleFlight Configuration")
    print("=" * 50)

    try:
        # Connect to AirSim
        print("🔌 Connecting to AirSim...")
        client = airsim.MultirotorClient()
        client.confirmConnection()
        print("✅ Connected to AirSim successfully!")

        # Check vehicle state
        print("\n📊 Vehicle Information:")
        state = client.getMultirotorState()
        print(f"   • Position: {state.kinematics_estimated.position}")
        print(f"   • Orientation: {state.kinematics_estimated.orientation}")
        print(f"   • Linear Velocity: {state.kinematics_estimated.linear_velocity}")
        print(f"   • Angular Velocity: {state.kinematics_estimated.angular_velocity}")

        # Check if vehicle is armed
        print(f"\n🔧 Vehicle Status:")
        print(f"   • Armed: {client.isApiControlEnabled()}")
        print(f"   • API Control: {client.isApiControlEnabled()}")

        # Test basic control
        print("\n🎮 Testing Basic Control:")

        # Enable API control
        print("   • Enabling API control...")
        client.enableApiControl(True)
        print("   ✅ API control enabled")

        # Arm the vehicle
        print("   • Arming vehicle...")
        client.armDisarm(True)
        print("   ✅ Vehicle armed")

        # Takeoff
        print("   • Taking off...")
        client.takeoffAsync().join()
        print("   ✅ Takeoff completed")

        # Hover for a moment
        print("   • Hovering for 3 seconds...")
        time.sleep(3)

        # Land
        print("   • Landing...")
        client.landAsync().join()
        print("   ✅ Landing completed")

        # Disarm
        print("   • Disarming vehicle...")
        client.armDisarm(False)
        print("   ✅ Vehicle disarmed")

        print("\n🎉 SimpleFlight configuration test completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


def test_sensor_data():
    """Test sensor data availability."""
    print("\n📡 Testing Sensor Data")
    print("=" * 30)

    try:
        client = airsim.MultirotorClient()

        # Test camera data
        print("📷 Testing camera data...")
        responses = client.simGetImages(
            [
                airsim.ImageRequest("0", airsim.ImageType.Scene),
                airsim.ImageRequest("1", airsim.ImageType.DepthVis),
            ]
        )
        print(f"   ✅ Received {len(responses)} camera images")

        # Test IMU data
        print("📊 Testing IMU data...")
        imu_data = client.getImuData()
        print(
            f"   ✅ IMU data: {imu_data.angular_velocity}, {imu_data.linear_acceleration}"
        )

        # Test GPS data
        print("📍 Testing GPS data...")
        gps_data = client.getGpsData()
        print(f"   ✅ GPS data: {gps_data.gnss.geo_point}")

        print("🎉 Sensor data test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Sensor test failed: {e}")
        return False


def main():
    """Main test function."""
    print("🚁 DART-Planner SimpleFlight Configuration Test")
    print("=" * 60)

    # Test basic connection and control
    if not test_simpleflight_connection():
        print("\n❌ Basic test failed. Check your AirSim configuration.")
        sys.exit(1)

    # Test sensor data
    if not test_sensor_data():
        print("\n⚠️  Sensor test failed, but basic functionality works.")

    print("\n✅ All tests completed!")
    print("\n💡 Next steps:")
    print("   • Run your DART-Planner algorithms")
    print("   • Test trajectory planning and execution")
    print("   • Validate control performance")


if __name__ == "__main__":
    main()
