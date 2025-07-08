"""
Units and Dimensional Analysis for DART-Planner

This module provides a unified units system using Pint for dimensional analysis.
All physical quantities should use this module to prevent unit conversion errors.

Key features:
- Singleton UnitRegistry for consistent units across the codebase
- Integration with Pydantic for type validation
- Common drone-specific units (N, m/s, rad/s, etc.)
- Performance-optimized for hot loops
"""

from functools import lru_cache
from typing import Union, Optional, Any
import numpy as np
from pint import UnitRegistry, Quantity
from pint.errors import DimensionalityError

# Global unit registry singleton
_UREG: Optional[UnitRegistry] = None


def get_ureg() -> UnitRegistry:
    """Get the global unit registry singleton."""
    global _UREG
    if _UREG is None:
        _UREG = UnitRegistry()
        # Enable matplotlib integration for plotting
        _UREG.setup_matplotlib(True)
        
        # Add drone-specific units if not already defined
        if 'N' not in _UREG:
            _UREG.define('N = newton')
        if 'rad/s' not in _UREG:
            _UREG.define('rad/s = radian / second')
        if 'deg/s' not in _UREG:
            _UREG.define('deg/s = degree / second')
        if 'g' not in _UREG:
            _UREG.define('g = 9.80665 m/s^2')
    
    return _UREG


def Q_(value: Union[float, int, str, np.ndarray], unit: Optional[str] = None) -> Quantity:
    """
    Create a Quantity with proper units.
    
    Args:
        value: The numerical value(s)
        unit: The unit string (e.g., 'm/s', 'rad', 'N')
    
    Returns:
        Pint Quantity object
        
    Examples:
        >>> Q_(1.5, 'm/s')  # 1.5 meter per second
        >>> Q_([1, 2, 3], 'rad')  # numpy array with radians
        >>> Q_('10 N')  # Parse from string
    """
    ureg = get_ureg()
    if unit is not None:
        return ureg.Quantity(value, unit)
    elif isinstance(value, str):
        return ureg.Quantity(value)
    else:
        raise ValueError("Must provide unit when value is not a string")


def to_float(q: Any) -> Union[float, np.ndarray]:
    """
    Convert a Quantity (or subclass) to float/array, stripping units.
    Accepts pint.Quantity, pint.PlainQuantity, or compatible types.
    """
    if hasattr(q, 'magnitude'):
        return q.magnitude
    return q


def ensure_units(value: Any, expected_unit: str, context: str = "") -> Quantity:
    """
    Ensure a value has the expected units, converting if necessary.
    
    Args:
        value: The value to check/convert
        expected_unit: The expected unit string
        context: Context for error messages
        
    Returns:
        Quantity with correct units
        
    Raises:
        DimensionalityError: If conversion is impossible
        ValueError: If value is not a Quantity or convertible
    """
    if isinstance(value, Quantity):
        try:
            return value.to(expected_unit)
        except DimensionalityError as e:
            raise DimensionalityError(
                f"Unit mismatch in {context}: cannot convert {value} to {expected_unit}"
            ) from e
    elif isinstance(value, (int, float, np.ndarray)):
        # Assume dimensionless or same units as expected
        return Q_(value, expected_unit)
    else:
        raise ValueError(f"Expected Quantity or number, got {type(value)} in {context}")


def angular_velocity_to_rad_s(value: Union[Quantity, float], unit: str = "deg/s") -> float:
    """
    Convert angular velocity to rad/s, handling common units.
    
    Args:
        value: Angular velocity value
        unit: Unit of the input value (default: deg/s)
        
    Returns:
        Angular velocity in rad/s as float
    """
    if isinstance(value, (int, float)):
        q = Q_(value, unit)
    else:
        q = value
    
    return q.to('rad/s').magnitude


def angular_velocity_to_deg_s(value: Union[Quantity, float], unit: str = "rad/s") -> float:
    """
    Convert angular velocity to deg/s, handling common units.
    
    Args:
        value: Angular velocity value
        unit: Unit of the input value (default: rad/s)
        
    Returns:
        Angular velocity in deg/s as float
    """
    if isinstance(value, (int, float)):
        q = Q_(value, unit)
    else:
        q = value
    
    return q.to('deg/s').magnitude


# Common unit constants for drone applications
GRAVITY = Q_(9.80665, 'm/s^2')
DEG_TO_RAD = Q_(np.pi / 180, 'rad/deg')
RAD_TO_DEG = Q_(180 / np.pi, 'deg/rad')

# Type aliases for common quantities
AngularVelocity = Quantity  # rad/s or deg/s
LinearVelocity = Quantity   # m/s
Force = Quantity            # N
Mass = Quantity             # kg
Length = Quantity           # m
Time = Quantity             # s 