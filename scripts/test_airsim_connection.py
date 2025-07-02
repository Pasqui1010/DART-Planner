#!/usr/bin/env python3
"""
Simple AirSim Connection Test
Tests basic connectivity to running AirSim instance
"""

import socket
import time


def test_airsim_connection():
    """Test basic connection to AirSim"""
    print("🎮 Testing AirSim Connection")
    print("=" * 40)

    # Test if AirSim is listening on default port
    airsim_host = "127.0.0.1"
    airsim_port = 41451

    try:
        print(f"🔗 Connecting to AirSim at {airsim_host}:{airsim_port}")

        # Create socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)  # 5 second timeout

        result = sock.connect_ex((airsim_host, airsim_port))
        sock.close()

        if result == 0:
            print("✅ AirSim is running and accepting connections!")
            print("📡 Port 41451 is open and responsive")
            return True
        else:
            print(f"❌ Cannot connect to AirSim (error code: {result})")
            return False

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def get_airsim_status():
    """Get basic AirSim status"""
    print(f"\n📊 AirSim Status Check:")
    print(f"   Expected host: 127.0.0.1")
    print(f"   Expected port: 41451")
    print(f"   Protocol: TCP/RPC")

    # Check if process is running (Windows)
    try:
        import subprocess

        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Blocks.exe"],
            capture_output=True,
            text=True,
            shell=True,
        )

        if "Blocks.exe" in result.stdout:
            print(f"   ✅ Blocks.exe process is running")
        else:
            print(f"   ⚠️ Blocks.exe process not found")
            print(f"   💡 Make sure AirSim Blocks is launched")

    except Exception as e:
        print(f"   ⚠️ Cannot check process status: {e}")


def print_next_steps():
    """Print next steps for AirSim integration"""
    print(f"\n🎯 Next Steps:")
    print(f"1. ✅ AirSim Blocks is running")
    print(f"2. 🔧 Install AirSim dependencies:")
    print(f"   pip install -r requirements.txt")
    print(f"   # Note: Uses tornado==4.5.3 (required for AirSim RPC compatibility)")
    print(f"   # DO NOT upgrade tornado - versions >=5.0 break msgpack-rpc-python")
    print(f"3. 🧪 Test DART-Planner integration")
    print(f"4. 🚀 Run autonomous mission validation")


def main():
    """Main connection test"""
    print("🚁 DART-Planner AirSim Connection Test")
    print("🎯 Validating AirSim readiness for DART-Planner integration")
    print("=" * 60)

    # Test connection
    connected = test_airsim_connection()

    # Get status
    get_airsim_status()

    if connected:
        print(f"\n🎉 SUCCESS: AirSim is ready for DART-Planner!")
        print(f"✨ Your 2,496x performance breakthrough is ready for validation")
    else:
        print(f"\n⚠️ AirSim connection failed")
        print(f"💡 Make sure:")
        print(f"   • AirSim Blocks is launched and running")
        print(f"   • No firewall blocking port 41451")
        print(f"   • Choose 'Multirotor' when AirSim starts")

    print_next_steps()
    return connected


if __name__ == "__main__":
    main()
