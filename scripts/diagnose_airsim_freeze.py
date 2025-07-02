#!/usr/bin/env python3
"""
AirSim Freeze Diagnostic Tool
Helps identify why AirSim freezes when pressing Play
"""

import json
import os
import socket
import subprocess
import sys
from pathlib import Path


def check_json_syntax():
    """Check if settings.json has valid syntax"""
    print("🔍 Checking settings.json syntax...")

    settings_path = Path.home() / "Documents" / "AirSim" / "settings.json"

    if not settings_path.exists():
        print("❌ settings.json not found at:", settings_path)
        return False

    try:
        with open(settings_path, "r") as f:
            content = f.read()
            print(f"📄 File size: {len(content)} bytes")

        # Try to parse JSON
        with open(settings_path, "r") as f:
            data = json.load(f)
            print("✅ JSON syntax is valid")

        # Check for common issues
        if "Vehicles" in data:
            print(f"🚁 Found {len(data['Vehicles'])} vehicle(s)")
            for name, vehicle in data["Vehicles"].items():
                print(f"   - {name}: {vehicle.get('VehicleType', 'Unknown')}")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ JSON syntax error: {e}")
        print(f"   Line {e.lineno}, Column {e.colno}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False


def check_ports():
    """Check if required ports are available"""
    print("\n🔍 Checking port availability...")

    ports = [14550, 9003, 9002]
    issues = []

    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(("127.0.0.1", port))
                print(f"✅ Port {port} is available")
        except OSError as e:
            print(f"❌ Port {port} is in use: {e}")
            issues.append(port)

    if issues:
        print(f"\n💡 To free up ports, try:")
        print(f'   netstat -ano | findstr ":{issues[0]}"')
        print(f"   Then kill the process using that port")

    return len(issues) == 0


def check_processes():
    """Check for conflicting processes"""
    print("\n🔍 Checking for conflicting processes...")

    try:
        # Check for SITL processes
        result = subprocess.run(
            ["tasklist"], capture_output=True, text=True, shell=True
        )
        processes = result.stdout.lower()

        conflicts = []
        if "ardupilot" in processes or "sitl" in processes:
            conflicts.append("ArduPilot SITL")
        if "mavproxy" in processes:
            conflicts.append("MAVProxy")
        if "qgroundcontrol" in processes:
            conflicts.append("QGroundControl")

        if conflicts:
            print(f"⚠️  Found potentially conflicting processes: {', '.join(conflicts)}")
            print("   Consider closing these before starting AirSim")
        else:
            print("✅ No obvious conflicting processes found")

    except Exception as e:
        print(f"❌ Error checking processes: {e}")


def create_minimal_settings():
    """Create a minimal settings.json for testing"""
    print("\n🔧 Creating minimal settings.json for testing...")

    settings_path = Path.home() / "Documents" / "AirSim"
    settings_path.mkdir(exist_ok=True)

    backup_path = settings_path / "settings.json.backup"
    original_path = settings_path / "settings.json"

    # Backup existing file
    if original_path.exists():
        import shutil

        shutil.copy2(original_path, backup_path)
        print(f"📋 Backed up original to: {backup_path}")

    # Create minimal settings
    minimal_settings = {"SettingsVersion": 1.2, "SimMode": "Multirotor"}

    with open(original_path, "w") as f:
        json.dump(minimal_settings, f, indent=2)

    print(f"✅ Created minimal settings.json")
    print(f"   Try running AirSim now")
    print(f"   If it works, the issue was in your original settings")


def main():
    """Run all diagnostics"""
    print("🚁 AirSim Freeze Diagnostic Tool")
    print("=" * 50)

    # Check JSON syntax
    json_ok = check_json_syntax()

    # Check ports
    ports_ok = check_ports()

    # Check processes
    check_processes()

    print("\n" + "=" * 50)
    print("📊 DIAGNOSIS SUMMARY:")

    if json_ok and ports_ok:
        print("✅ JSON and ports look good")
        print("💡 The issue might be:")
        print("   - Plugin compilation problems")
        print("   - UE4.27 compatibility issues")
        print("   - Missing dependencies")
        print("\n🔧 Next steps:")
        print("   1. Check Unreal Output Log for errors")
        print("   2. Try rebuilding AirSim plugin")
        print("   3. Test with minimal settings (run with --minimal)")
    elif not json_ok:
        print("❌ JSON syntax issues found - fix these first!")
    elif not ports_ok:
        print("❌ Port conflicts found - close conflicting processes!")

    # Offer to create minimal settings
    if "--minimal" in sys.argv:
        create_minimal_settings()


if __name__ == "__main__":
    main()
