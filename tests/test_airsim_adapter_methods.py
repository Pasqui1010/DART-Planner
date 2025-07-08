#!/usr/bin/env python3
"""
Quick test to verify all AirSimAdapter methods work without NotImplementedError
"""

import asyncio
import numpy as np
from dart_planner.hardware.airsim_adapter import AirSimAdapter
from dart_planner.common.types import ControlCommand


async def test_all_adapter_methods():
    """Test all AirSimAdapter methods to ensure no NotImplementedError"""
    
    print("🧪 Testing all AirSimAdapter methods...")
    
    # Create adapter
    adapter = AirSimAdapter()
    print("✅ Adapter created")
    
    # Test all methods
    methods_to_test = [
        ("connect", lambda: adapter.connect()),
        ("disconnect", lambda: adapter.disconnect()),
        ("takeoff", lambda: adapter.takeoff(altitude=2.0)),
        ("land", lambda: adapter.land()),
        ("pause", lambda: adapter.pause()),
        ("resume", lambda: adapter.resume()),
        ("emergency_land", lambda: adapter.emergency_land()),
        ("get_state", lambda: adapter.get_state()),
        ("send_control_command", lambda: adapter.send_control_command(
            ControlCommand(thrust=9.8, torque=np.array([0.1, 0.2, 0.3]))
        )),
        ("start_mission", lambda: adapter.start_mission([
            np.array([0.0, 0.0, -2.0]),
            np.array([10.0, 0.0, -2.0])
        ])),
    ]
    
    for method_name, method_call in methods_to_test:
        try:
            result = await method_call()
            print(f"✅ {method_name}: {result}")
        except NotImplementedError as e:
            print(f"❌ {method_name}: NotImplementedError - {e}")
            return False
        except Exception as e:
            print(f"⚠️ {method_name}: Other error - {e}")
            # This is okay, we're just checking for NotImplementedError
    
    print("🎉 All methods tested successfully!")
    return True


if __name__ == "__main__":
    asyncio.run(test_all_adapter_methods()) 
