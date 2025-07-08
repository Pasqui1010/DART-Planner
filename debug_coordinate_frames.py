#!/usr/bin/env python3
"""
Debug script to reproduce the coordinate frame thread-local bug.
"""

import threading
import numpy as np
from dart_planner.common.coordinate_frames import (
    WorldFrame, CoordinateFrameManager, CoordinateFrameConfig,
    get_coordinate_frame_manager, set_coordinate_frame_manager,
    clear_thread_local_manager, get_gravity_vector, get_up_vector,
    validate_gravity_and_axis_signs, get_frame_info
)

def test_thread_local_bug():
    """Test the thread-local coordinate frame bug."""
    results = {}
    lock = threading.Lock()
    
    def worker(frame_type, thread_id):
        """Worker function that sets up a coordinate frame and gets gravity."""
        config = CoordinateFrameConfig(world_frame=frame_type)
        manager = CoordinateFrameManager(config)
        set_coordinate_frame_manager(manager, use_thread_local=True)
        
        # Test both the manager method and the global helper function
        gravity_manager = get_coordinate_frame_manager().get_gravity_vector()
        gravity_global = get_gravity_vector()
        
        with lock:
            results[thread_id] = {
                'manager': gravity_manager,
                'global': gravity_global,
                'frame_type': frame_type.value
            }
            print(f"Thread {thread_id} ({frame_type.value}):")
            print(f"  Manager gravity: {gravity_manager}")
            print(f"  Global gravity:  {gravity_global}")
    
    # Clear any existing thread-local state
    clear_thread_local_manager()
    
    # Create threads with different coordinate frames
    thread1 = threading.Thread(target=worker, args=(WorldFrame.ENU, 1))
    thread2 = threading.Thread(target=worker, args=(WorldFrame.NED, 2))
    
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    
    # Check results
    expected_enu = np.array([0, 0, -9.80665])
    expected_ned = np.array([0, 0, 9.80665])
    
    print(f"\nResults:")
    for thread_id, result in results.items():
        manager_correct = np.allclose(result['manager'], expected_enu if result['frame_type'] == 'ENU' else expected_ned)
        global_correct = np.allclose(result['global'], expected_enu if result['frame_type'] == 'ENU' else expected_ned)
        
        print(f"Thread {thread_id} ({result['frame_type']}):")
        print(f"  Manager: {'✓' if manager_correct else '✗'}")
        print(f"  Global:  {'✓' if global_correct else '✗'}")
    
    # Test global helper functions in main thread
    print(f"\nTesting global helpers in main thread:")
    clear_thread_local_manager()
    
    # Set up ENU frame
    enu_config = CoordinateFrameConfig(world_frame=WorldFrame.ENU)
    enu_manager = CoordinateFrameManager(enu_config)
    set_coordinate_frame_manager(enu_manager, use_thread_local=True)
    
    main_gravity = get_gravity_vector()
    main_up = get_up_vector()
    main_validation = validate_gravity_and_axis_signs()
    main_info = get_frame_info()
    
    print(f"Main thread gravity: {main_gravity}")
    print(f"Main thread up vector: {main_up}")
    print(f"Main thread validation: {main_validation.is_valid}")
    print(f"Main thread frame: {main_info['world_frame']}")
    
    return True

if __name__ == "__main__":
    print("Testing coordinate frame thread-local bug...")
    success = test_thread_local_bug()
    if not success:
        print("\n❌ BUG CONFIRMED: Thread-local coordinate frame context is broken!")
    else:
        print("\n✅ No bug detected in this test.") 