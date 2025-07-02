#!/usr/bin/env python3
"""
ArduCopter Settings Tester
Tests different ArduCopter configurations to find the problematic setting
"""

import json
import time
from pathlib import Path


def create_test_settings(test_name, settings_dict):
    """Create a test settings file"""
    settings_path = Path.home() / "Documents" / "AirSim" / "settings.json"

    with open(settings_path, "w") as f:
        json.dump(settings_dict, f, indent=2)

    print(f"✅ Created {test_name} settings")
    print(f"📄 Content:")
    print(json.dumps(settings_dict, indent=2))
    print(f"\n🧪 Test this configuration in AirSim")
    print(f"   Press Enter when you've tested it...")

    result = input().strip().lower()
    return result in ["y", "yes", "works", "ok", "good"]


def main():
    """Run incremental tests"""
    print("🧪 ArduCopter Configuration Tester")
    print("=" * 50)
    print("We'll test different configurations step by step")
    print("For each test, launch AirSim and press Play")
    print("Then come back here and tell me if it worked (y/n)")
    print()

    # Test 1: Basic ArduCopter (no network settings)
    test1 = {
        "SettingsVersion": 1.2,
        "SimMode": "Multirotor",
        "Vehicles": {"Copter": {"VehicleType": "ArduCopter"}},
    }

    if create_test_settings("Test 1: Basic ArduCopter", test1):
        print("✅ Basic ArduCopter works!")

        # Test 2: Add UseSerial setting
        test2 = {
            "SettingsVersion": 1.2,
            "SimMode": "Multirotor",
            "Vehicles": {"Copter": {"VehicleType": "ArduCopter", "UseSerial": False}},
        }

        if create_test_settings("Test 2: ArduCopter + UseSerial", test2):
            print("✅ UseSerial=false works!")

            # Test 3: Add localhost IP
            test3 = {
                "SettingsVersion": 1.2,
                "SimMode": "Multirotor",
                "Vehicles": {
                    "Copter": {
                        "VehicleType": "ArduCopter",
                        "UseSerial": False,
                        "LocalHostIp": "127.0.0.1",
                    }
                },
            }

            if create_test_settings("Test 3: ArduCopter + LocalHostIp", test3):
                print("✅ LocalHostIp works!")

                # Test 4: Add UDP IP
                test4 = {
                    "SettingsVersion": 1.2,
                    "SimMode": "Multirotor",
                    "Vehicles": {
                        "Copter": {
                            "VehicleType": "ArduCopter",
                            "UseSerial": False,
                            "LocalHostIp": "127.0.0.1",
                            "UdpIp": "127.0.0.1",
                        }
                    },
                }

                if create_test_settings("Test 4: ArduCopter + UdpIp", test4):
                    print("✅ UdpIp works!")

                    # Test 5: Add UdpPort
                    test5 = {
                        "SettingsVersion": 1.2,
                        "SimMode": "Multirotor",
                        "Vehicles": {
                            "Copter": {
                                "VehicleType": "ArduCopter",
                                "UseSerial": False,
                                "LocalHostIp": "127.0.0.1",
                                "UdpIp": "127.0.0.1",
                                "UdpPort": 9003,
                            }
                        },
                    }

                    if create_test_settings("Test 5: ArduCopter + UdpPort", test5):
                        print("✅ UdpPort works!")

                        # Test 6: Add ControlPort (full original config)
                        test6 = {
                            "SettingsVersion": 1.2,
                            "SimMode": "Multirotor",
                            "Vehicles": {
                                "Copter": {
                                    "VehicleType": "ArduCopter",
                                    "UseSerial": False,
                                    "LocalHostIp": "127.0.0.1",
                                    "UdpIp": "127.0.0.1",
                                    "UdpPort": 9003,
                                    "ControlPort": 9002,
                                }
                            },
                        }

                        if create_test_settings("Test 6: Full Original Config", test6):
                            print("🎉 All settings work! The issue was temporary.")
                        else:
                            print("❌ ControlPort causes the freeze!")
                            print(
                                "💡 Solution: Remove ControlPort or use a different port"
                            )

                            # Test alternative port
                            test6alt = test6.copy()
                            test6alt["Vehicles"]["Copter"]["ControlPort"] = 9004

                            if create_test_settings(
                                "Test 6-Alt: Different ControlPort", test6alt
                            ):
                                print("✅ Different ControlPort works!")
                            else:
                                print("❌ ControlPort setting itself is problematic")
                    else:
                        print("❌ UdpPort 9003 causes the freeze!")
                        print("💡 Try a different UDP port")
                else:
                    print("❌ UdpIp setting causes the freeze!")
            else:
                print("❌ LocalHostIp setting causes the freeze!")
        else:
            print("❌ UseSerial=false causes the freeze!")
            print("💡 Try UseSerial=true or remove this setting")
    else:
        print("❌ ArduCopter VehicleType itself causes the freeze!")
        print("💡 Your AirSim build might not support ArduCopter")
        print("   Try 'SimpleFlight' instead:")

        # Fallback test
        fallback = {
            "SettingsVersion": 1.2,
            "SimMode": "Multirotor",
            "Vehicles": {"Copter": {"VehicleType": "SimpleFlight"}},
        }

        if create_test_settings("Fallback: SimpleFlight", fallback):
            print("✅ SimpleFlight works!")
            print(
                "💡 Use SimpleFlight for now, or rebuild AirSim with ArduPilot support"
            )
        else:
            print("❌ Even SimpleFlight doesn't work - deeper plugin issue")


if __name__ == "__main__":
    main()
