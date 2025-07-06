#!/usr/bin/env python3
"""test_full_airsim_api.py
Run a quick integration test that exercises key AirSim multirotor APIs.
Usage:
    python scripts/test_full_airsim_api.py [--ip 127.0.0.1] [--port 41451]
Requirements:
    * AirSim application running (Blocks or custom environment)
    * `pip install airsim` (dependency instructions in docs)
"""

import argparse
import os
import sys
import time
from pathlib import Path

try:
    import airsim  # noqa: E402
except ImportError as exc:
    print(
        "❌ AirSim Python package not found.\n   • Install with: pip install airsim\n   • If dependency issues: see docs/implementation/AIRSIM_NEXT_STEPS_SUMMARY.md"
    )
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Full AirSim API smoke test")
    parser.add_argument("--ip", default="127.0.0.1", help="AirSim server IP address")
    parser.add_argument("--port", type=int, default=41451, help="AirSim RPC port")
    parser.add_argument(
        "--alt", type=float, default=10.0, help="Takeoff altitude (meters, positive)"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("🎮============================================================🎮")
    print("🚁 DART-Planner: Full AirSim API Validation")
    print("🔗 Connecting to AirSim @ {}:{}".format(args.ip, args.port))

    client = airsim.MultirotorClient(ip=args.ip, port=args.port)
    try:
        client.confirmConnection()
    except Exception as exc:
        print(f"❌ Failed to connect: {exc}")
        sys.exit(1)

    print("✅ Connection established!")

    # Enable API control and arm
    client.enableApiControl(True)
    client.armDisarm(True)

    # Take off
    print("🚀 Taking off…")
    client.takeoffAsync(timeout_sec=15).join()
    state = client.getMultirotorState()
    z = state.kinematics_estimated.position.z_val
    print(f"   Current altitude: {abs(z):.1f} m")

    # Climb to target altitude (note: AirSim NED coordinate => -z is up)
    target_z = -abs(args.alt)
    print(f"📍 Ascending to {-target_z:.1f} m…")
    client.moveToPositionAsync(0, 0, target_z, 2).join()

    # Fly in a small square
    print("📐 Flying 20 m square…")
    square_coords = [(20, 0), (20, 20), (0, 20), (0, 0)]
    for idx, (x, y) in enumerate(square_coords, 1):
        print(f"   ➜ Leg {idx}: ({x}, {y}, {abs(target_z):.1f})")
        client.moveToPositionAsync(x, y, target_z, 5).join()

    # Capture an RGB image from front camera
    print("📷 Capturing image from front camera…")
    img_data = client.simGetImage("0", airsim.ImageType.Scene)
    if img_data is not None:
        img_path = Path.cwd() / "airsim_rgb_test.png"
        with open(img_path, "wb") as fp:
            fp.write(img_data)
        print(f"   ✅ Image saved: {img_path}")
    else:
        print("   ⚠️ Failed to capture image")

    # Return home and land
    print("🏠 Returning home and landing…")
    client.goHomeAsync(timeout_sec=120).join()
    client.landAsync(timeout_sec=30).join()

    # Disarm and release control
    client.armDisarm(False)
    client.enableApiControl(False)

    print("🎉 Full AirSim API validation completed successfully!")


if __name__ == "__main__":
    main()
