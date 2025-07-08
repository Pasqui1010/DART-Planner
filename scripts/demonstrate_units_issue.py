#!/usr/bin/env python3
"""
Demonstrate the critical units issue in the geometric controller.

This script shows how passing Euler angles in degrees instead of radians
produces completely wrong rotation matrices, which would cause the drone
to behave incorrectly.
"""

import numpy as np
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dart_planner.control.geometric_controller import GeometricController
from dart_planner.common.types import DroneState


def demonstrate_units_issue():
    """Demonstrate the critical units issue."""
    print("🔍 Demonstrating Critical Units Issue in Geometric Controller")
    print("=" * 60)
    
    controller = GeometricController()
    
    # Create a drone state with Euler angles in RADIANS (correct)
    state_rad = DroneState(
        timestamp=0.0,
        position=np.array([0.0, 0.0, 0.0]),
        velocity=np.array([0.0, 0.0, 0.0]),
        attitude=np.array([0.1, 0.2, 0.3]),  # ~5.7, 11.5, 17.2 degrees
        angular_velocity=np.array([0.0, 0.0, 0.0])
    )
    
    # Create a drone state with Euler angles in DEGREES (incorrect but common mistake)
    state_deg = DroneState(
        timestamp=0.0,
        position=np.array([0.0, 0.0, 0.0]),
        velocity=np.array([0.0, 0.0, 0.0]),
        attitude=np.array([5.7, 11.5, 17.2]),  # Same angles but in degrees
        angular_velocity=np.array([0.0, 0.0, 0.0])
    )
    
    print(f"📐 Euler angles in RADIANS: {state_rad.attitude}")
    print(f"📐 Euler angles in DEGREES: {state_deg.attitude}")
    print()
    
    # Compute rotation matrices
    R_rad = controller._euler_to_rotation_matrix(state_rad.attitude)
    R_deg = controller._euler_to_rotation_matrix(state_deg.attitude)
    
    print("🔄 Rotation Matrix (RADIANS):")
    print(R_rad)
    print()
    
    print("🔄 Rotation Matrix (DEGREES):")
    print(R_deg)
    print()
    
    # Calculate differences
    diff = np.linalg.norm(R_rad - R_deg)
    identity_diff_rad = np.linalg.norm(R_rad - np.eye(3))
    identity_diff_deg = np.linalg.norm(R_deg - np.eye(3))
    
    print("📊 Analysis:")
    print(f"   Difference between matrices: {diff:.6f}")
    print(f"   Radians matrix vs identity: {identity_diff_rad:.6f}")
    print(f"   Degrees matrix vs identity: {identity_diff_deg:.6f}")
    print()
    
    # Check if the difference is significant
    if diff > 0.1:
        print("❌ CRITICAL ISSUE DETECTED!")
        print("   The rotation matrices are very different due to unit mismatch.")
        print("   This would cause the drone to behave incorrectly.")
        print()
        print("   Expected behavior:")
        print("   - Small angles (~0.1-0.3 rad) should produce rotation matrices")
        print("     close to identity (difference < 0.5)")
        print("   - The degrees version produces completely wrong results")
        print()
        print("   Impact:")
        print("   - Wrong attitude control commands")
        print("   - Incorrect trajectory tracking")
        print("   - Potential instability or crashes")
    else:
        print("✅ No significant difference detected (unexpected)")
    
    print()
    print("💡 Solution:")
    print("   - Use the units system to enforce proper units")
    print("   - Add type checking to prevent unit mismatches")
    print("   - Document expected units clearly")
    
    return diff > 0.1


def test_units_system():
    """Test the new units system."""
    print("\n🧪 Testing Units System")
    print("=" * 40)
    
    try:
        from dart_planner.common.units import Q_, angular_velocity_to_rad_s
        
        # Test basic functionality
        angle_deg = Q_(90, 'deg')
        angle_rad = angle_deg.to('rad')
        print(f"✅ 90 degrees = {angle_rad.magnitude:.6f} radians")
        
        # Test angular velocity conversion
        omega_deg_s = 180.0  # deg/s
        omega_rad_s = angular_velocity_to_rad_s(omega_deg_s, 'deg/s')
        print(f"✅ 180 deg/s = {omega_rad_s:.6f} rad/s")
        
        print("✅ Units system working correctly")
        return True
        
    except ImportError as e:
        print(f"❌ Units system not available: {e}")
        return False


if __name__ == "__main__":
    # Demonstrate the issue
    issue_detected = demonstrate_units_issue()
    
    # Test the units system
    units_working = test_units_system()
    
    print("\n" + "=" * 60)
    if issue_detected and units_working:
        print("🎯 SUMMARY: Critical units issue confirmed and units system ready")
        print("   Next step: Integrate units into controller and types")
    elif issue_detected:
        print("🎯 SUMMARY: Critical units issue confirmed")
        print("   Next step: Install units dependencies and integrate")
    else:
        print("🎯 SUMMARY: No critical issue detected (unexpected)")
    
    print("=" * 60) 