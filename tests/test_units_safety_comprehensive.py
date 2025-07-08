"""
Comprehensive units safety tests for DART-Planner.

This test suite validates the units system integration and ensures
all physical quantities are properly handled with units.
"""

import pytest
import numpy as np
from dart_planner.common.units import (
    Q_, to_float, ensure_units, angular_velocity_to_rad_s,
    angular_velocity_to_deg_s, GRAVITY, DEG_TO_RAD, RAD_TO_DEG
)


class TestUnitsSafety:
    """Test units safety and validation."""
    
    def test_gravity_constant(self):
        """Test that gravity constant has correct units."""
        assert GRAVITY.units == 'meter / second ** 2'
        assert abs(to_float(GRAVITY) - 9.80665) < 1e-6
    
    def test_angular_conversion_constants(self):
        """Test angular conversion constants."""
        assert DEG_TO_RAD.units == 'radian / degree'
        assert RAD_TO_DEG.units == 'degree / radian'
        
        # Test conversion
        test_deg = Q_(90, 'degree')
        test_rad = test_deg * DEG_TO_RAD
        assert abs(to_float(test_rad) - np.pi/2) < 1e-6
    
    def test_angular_velocity_conversions(self):
        """Test angular velocity unit conversions."""
        # Test deg/s to rad/s
        deg_per_s = 180.0
        rad_per_s = angular_velocity_to_rad_s(deg_per_s, 'deg/s')
        assert abs(rad_per_s - np.pi) < 1e-6
        
        # Test rad/s to deg/s
        rad_per_s = np.pi
        deg_per_s = angular_velocity_to_deg_s(rad_per_s, 'rad/s')
        assert abs(deg_per_s - 180.0) < 1e-6
    
    def test_ensure_units_validation(self):
        """Test ensure_units function validation."""
        # Valid conversion
        velocity = Q_(10, 'm/s')
        result = ensure_units(velocity, 'm/s', 'test')
        assert result.units == 'meter / second'
        assert to_float(result) == 10.0
        
        # Invalid conversion should raise error
        with pytest.raises(Exception):
            ensure_units(velocity, 'N', 'test')
    
    def test_to_float_function(self):
        """Test to_float utility function."""
        # Test with Quantity
        q = Q_(5.5, 'm')
        assert to_float(q) == 5.5
        
        # Test with numpy array
        arr = Q_([1, 2, 3], 'rad')
        result = to_float(arr)
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, [1, 2, 3])
        
        # Test with regular number
        assert to_float(42) == 42


class TestUnitsIntegration:
    """Test units integration with other components."""
    
    def test_units_with_numpy(self):
        """Test units work correctly with numpy arrays."""
        positions = Q_([[1, 2, 3], [4, 5, 6]], 'm')
        velocities = Q_([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]], 'm/s')
        
        # Test array operations
        assert positions.shape == (2, 3)
        assert velocities.shape == (2, 3)
        
        # Test magnitude extraction
        pos_mag = to_float(positions)
        vel_mag = to_float(velocities)
        
        assert pos_mag.shape == (2, 3)
        assert vel_mag.shape == (2, 3)
    
    def test_units_consistency(self):
        """Test that units are consistent across the system."""
        # Test that all physical constants have correct units
        assert GRAVITY.units == 'meter / second ** 2'
        assert DEG_TO_RAD.units == 'radian / degree'
        assert RAD_TO_DEG.units == 'degree / radian'
        
        # Test that conversions are reversible
        test_value = 45.0
        deg_to_rad = angular_velocity_to_rad_s(test_value, 'deg/s')
        rad_to_deg = angular_velocity_to_deg_s(deg_to_rad, 'rad/s')
        assert abs(rad_to_deg - test_value) < 1e-6


if __name__ == "__main__":
    pytest.main([__file__]) 