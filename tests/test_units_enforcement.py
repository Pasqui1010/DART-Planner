"""
Unit tests for the units system and enforcement.

These tests demonstrate the critical unit conversion issues in the codebase
and verify that the units system prevents them.
"""

import pytest
import numpy as np
from pint.errors import DimensionalityError

from dart_planner.common.units import Q_, to_float, ensure_units, angular_velocity_to_rad_s, angular_velocity_to_deg_s
from dart_planner.control.geometric_controller import GeometricController, GeometricControllerConfig
from dart_planner.common.types import DroneState


class TestUnitsSystem:
    """Test the basic units system functionality."""
    
    def test_basic_quantity_creation(self):
        """Test creating quantities with units."""
        # Test basic creation
        pos = Q_(1.5, 'm')
        vel = Q_(10.0, 'm/s')
        force = Q_(20.0, 'N')
        
        assert pos.magnitude == 1.5
        assert pos.units == 'meter'
        assert vel.magnitude == 10.0
        assert vel.units == 'meter / second'
        assert force.magnitude == 20.0
        assert force.units == 'newton'
    
    def test_unit_conversion(self):
        """Test automatic unit conversion."""
        # Convert degrees to radians
        angle_deg = Q_(90, 'deg')
        angle_rad = angle_deg.to('rad')
        
        assert np.isclose(angle_rad.magnitude, np.pi/2, atol=1e-6)
        
        # Convert angular velocity
        omega_deg_s = Q_(180, 'deg/s')
        omega_rad_s = omega_deg_s.to('rad/s')
        
        assert np.isclose(omega_rad_s.magnitude, np.pi, atol=1e-6)
    
    def test_angular_velocity_helpers(self):
        """Test the angular velocity helper functions."""
        # Test deg/s to rad/s conversion
        omega_deg = 180.0  # deg/s
        omega_rad = angular_velocity_to_rad_s(omega_deg, 'deg/s')
        assert np.isclose(omega_rad, np.pi, atol=1e-6)
        
        # Test rad/s to deg/s conversion
        omega_rad = np.pi  # rad/s
        omega_deg = angular_velocity_to_deg_s(omega_rad, 'rad/s')
        assert np.isclose(omega_deg, 180.0, atol=1e-6)
    
    def test_ensure_units(self):
        """Test the ensure_units function."""
        # Test with correct units
        pos = Q_(1.0, 'm')
        result = ensure_units(pos, 'm', 'position')
        assert result == pos
        
        # Test with wrong units (should raise error)
        with pytest.raises(DimensionalityError):
            ensure_units(pos, 'N', 'force')
        
        # Test with float (should assume correct units)
        result = ensure_units(1.5, 'm', 'position')
        assert result.magnitude == 1.5
        assert result.units == 'meter'


class TestControllerUnitsIssue:
    """Test the critical units issue in the geometric controller."""
    
    def test_euler_angle_units_issue(self):
        """
        Demonstrate the critical units issue in geometric controller.
        
        The controller assumes Euler angles are in radians, but if they're
        passed in degrees, it will produce completely wrong results.
        """
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
        
        # Compute rotation matrices
        R_rad = controller._euler_to_rotation_matrix(state_rad.attitude)
        R_deg = controller._euler_to_rotation_matrix(state_deg.attitude)
        
        # These should be VERY different due to the unit mismatch
        # The degrees version will be completely wrong
        diff = np.linalg.norm(R_rad - R_deg)
        
        # The difference should be significant (not just numerical precision)
        assert diff > 0.1, f"Rotation matrices should be very different, got diff={diff}"
        
        # Verify the radians version is reasonable (identity for small angles)
        # For small angles, the rotation matrix should be close to identity
        identity_diff = np.linalg.norm(R_rad - np.eye(3))
        assert identity_diff < 0.5, f"Radians rotation should be close to identity, got diff={identity_diff}"
        
        # The degrees version should be very different from identity
        deg_identity_diff = np.linalg.norm(R_deg - np.eye(3))
        assert deg_identity_diff > 0.5, f"Degrees rotation should be far from identity, got diff={deg_identity_diff}"
    
    def test_controller_with_units(self):
        """Test that the controller works correctly with proper units."""
        # This test would be implemented once we add units to the controller
        # For now, it demonstrates what the test would look like
        
        # Create a controller that expects quantities with units
        # controller = GeometricControllerWithUnits()
        
        # Create state with proper units
        # state = DroneStateWithUnits(
        #     position=Q_([0.0, 0.0, 0.0], 'm'),
        #     attitude=Q_([0.1, 0.2, 0.3], 'rad'),  # Explicitly in radians
        #     ...
        # )
        
        # This should work correctly
        # control_cmd = controller.compute_control(state, ...)
        
        # If someone accidentally passes degrees, it should raise an error
        # with pytest.raises(DimensionalityError):
        #     state_wrong = DroneStateWithUnits(
        #         attitude=Q_([5.7, 11.5, 17.2], 'deg'),  # Wrong units
        #         ...
        #     )
        #     controller.compute_control(state_wrong, ...)
        
        pass  # Placeholder for now


class TestUnitsPerformance:
    """Test that units don't significantly impact performance."""
    
    def test_units_overhead(self):
        """Test that units add minimal overhead."""
        import time
        
        # Test without units
        start = time.perf_counter()
        for _ in range(1000):
            result = np.sin(0.1) * np.cos(0.2)
        time_without_units = time.perf_counter() - start
        
        # Test with units
        start = time.perf_counter()
        for _ in range(1000):
            angle = Q_(0.1, 'rad')
            result = np.sin(angle.magnitude) * np.cos(Q_(0.2, 'rad').magnitude)
        time_with_units = time.perf_counter() - start
        
        # Overhead should be less than 10x
        overhead_ratio = time_with_units / time_without_units
        assert overhead_ratio < 10.0, f"Units overhead too high: {overhead_ratio}x"
        
        # In practice, this should be much lower (2-3x)
        print(f"Units overhead ratio: {overhead_ratio:.2f}x")


class TestUnitsIntegration:
    """Test integration with existing code."""
    
    def test_units_with_numpy(self):
        """Test that units work well with numpy arrays."""
        # Create arrays with units
        positions = Q_(np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]), 'm')
        velocities = Q_(np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]), 'm/s')
        
        # Basic operations should work
        assert positions.shape == (2, 3)
        assert velocities.shape == (2, 3)
        
        # Unit conversions should work on arrays
        positions_cm = positions.to('cm')
        assert np.allclose(positions_cm.magnitude, positions.magnitude * 100)
    
    def test_units_with_pydantic(self):
        """Test that units work with Pydantic models."""
        # This would test integration with Pydantic for config validation
        # For now, just verify the imports work
        try:
            from pint_pydantic import PintQuantity
            assert PintQuantity is not None
        except ImportError:
            pytest.skip("pint-pydantic not available")


if __name__ == "__main__":
    # Run the critical units issue test
    test = TestControllerUnitsIssue()
    test.test_euler_angle_units_issue()
    print("✅ Units issue demonstration completed") 