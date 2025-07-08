"""
Motor Model Interface and Quadratic Implementation

This module provides physics-based motor modeling for accurate thrust and torque prediction.
Replaces linear approximations with quadratic models fitted to bench test data.
"""

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
import logging

from dart_planner.common.units import Q_, Quantity, ensure_units

logger = logging.getLogger(__name__)


class MotorType(Enum):
    """Supported motor types for different modeling approaches."""
    BRUSHLESS_DC = "brushless_dc"
    BRUSHED_DC = "brushed_dc"
    SERVO = "servo"


@dataclass
class MotorParameters:
    """Physical parameters for a single motor."""
    motor_id: int
    motor_type: MotorType = MotorType.BRUSHLESS_DC
    
    # Thrust model coefficients: thrust = a*PWM² + b*PWM + c (N)
    thrust_a: float = 0.0      # Quadratic coefficient (N/PWM²)
    thrust_b: float = 0.0      # Linear coefficient (N/PWM)
    thrust_c: float = 0.0      # Offset coefficient (N)
    
    # Torque model coefficient: torque = kQ * RPM² (N·m)
    torque_coefficient: float = 0.0  # kQ (N·m/RPM²)
    
    # PWM-RPM relationship: RPM = kRPM * PWM + RPM_offset
    rpm_coefficient: float = 0.0     # kRPM (RPM/PWM)
    rpm_offset: float = 0.0          # RPM_offset (RPM)
    
    # Operating limits
    pwm_min: float = 0.0       # Minimum PWM (normalized)
    pwm_max: float = 1.0       # Maximum PWM (normalized)
    pwm_idle: float = 0.1      # Idle PWM to keep motor spinning
    rpm_max: float = 10000.0   # Maximum RPM
    
    # Motor direction (1 for CCW, -1 for CW)
    direction: int = 1
    
    # Calibration metadata
    calibration_date: Optional[str] = None
    calibration_notes: Optional[str] = None
    
    def __post_init__(self):
        """Validate motor parameters."""
        if self.thrust_a < 0:
            raise ValueError(f"Motor {self.motor_id}: thrust_a must be non-negative")
        if self.torque_coefficient < 0:
            raise ValueError(f"Motor {self.motor_id}: torque_coefficient must be non-negative")
        if self.rpm_coefficient <= 0:
            raise ValueError(f"Motor {self.motor_id}: rpm_coefficient must be positive")
        if self.pwm_min >= self.pwm_max:
            raise ValueError(f"Motor {self.motor_id}: pwm_min must be less than pwm_max")
        if self.direction not in [-1, 1]:
            raise ValueError(f"Motor {self.motor_id}: direction must be ±1")


@dataclass
class BenchTestData:
    """Bench test data for motor calibration."""
    motor_id: int
    pwm_values: List[float] = field(default_factory=list)
    thrust_measurements: List[float] = field(default_factory=list)  # N
    torque_measurements: List[float] = field(default_factory=list)  # N·m
    rpm_measurements: List[float] = field(default_factory=list)     # RPM
    
    def validate(self) -> List[str]:
        """Validate bench test data."""
        errors = []
        
        if len(self.pwm_values) < 3:
            errors.append(f"Motor {self.motor_id}: Need at least 3 data points for quadratic fit")
        
        if len(self.pwm_values) != len(self.thrust_measurements):
            errors.append(f"Motor {self.motor_id}: PWM and thrust data lengths don't match")
        
        if len(self.pwm_values) != len(self.rpm_measurements):
            errors.append(f"Motor {self.motor_id}: PWM and RPM data lengths don't match")
        
        # Check for monotonic PWM values
        if not all(self.pwm_values[i] <= self.pwm_values[i+1] for i in range(len(self.pwm_values)-1)):
            errors.append(f"Motor {self.motor_id}: PWM values must be monotonically increasing")
        
        # Check for reasonable thrust values
        if any(t < 0 for t in self.thrust_measurements):
            errors.append(f"Motor {self.motor_id}: Thrust measurements must be non-negative")
        
        return errors


class MotorModel(ABC):
    """Abstract interface for motor modeling."""
    
    @abstractmethod
    def thrust_from_pwm(self, pwm: float, motor_id: int) -> float:
        """Convert PWM to thrust in Newtons."""
        pass
    
    @abstractmethod
    def torque_from_pwm(self, pwm: float, motor_id: int) -> float:
        """Convert PWM to torque in N·m."""
        pass
    
    @abstractmethod
    def pwm_from_thrust(self, thrust: float, motor_id: int) -> float:
        """Convert thrust to PWM (inverse of thrust_from_pwm)."""
        pass
    
    @abstractmethod
    def rpm_from_pwm(self, pwm: float, motor_id: int) -> float:
        """Convert PWM to RPM."""
        pass
    
    @abstractmethod
    def get_motor_parameters(self, motor_id: int) -> MotorParameters:
        """Get motor parameters for a specific motor."""
        pass
    
    @abstractmethod
    def validate_pwm(self, pwm: float, motor_id: int) -> bool:
        """Validate PWM value is within motor limits."""
        pass


class QuadraticMotorModel(MotorModel):
    """
    Quadratic motor model based on bench test data.
    
    Models:
    - Thrust: T = a*PWM² + b*PWM + c
    - Torque: τ = kQ * RPM²
    - RPM: RPM = kRPM * PWM + RPM_offset
    """
    
    def __init__(self, motor_parameters: Dict[int, MotorParameters]):
        """
        Initialize quadratic motor model.
        
        Args:
            motor_parameters: Dictionary mapping motor_id to parameters
        """
        self.motor_parameters = motor_parameters
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Validate all motor parameters
        for motor_id, params in motor_parameters.items():
            if motor_id != params.motor_id:
                raise ValueError(f"Motor ID mismatch: {motor_id} != {params.motor_id}")
        
        self.logger.info(f"Initialized quadratic motor model with {len(motor_parameters)} motors")
    
    def thrust_from_pwm(self, pwm: float, motor_id: int) -> float:
        """
        Convert PWM to thrust using quadratic model.
        
        Args:
            pwm: PWM value (0.0 to 1.0)
            motor_id: Motor identifier
            
        Returns:
            Thrust in Newtons
        """
        if motor_id not in self.motor_parameters:
            raise ValueError(f"Unknown motor ID: {motor_id}")
        
        params = self.motor_parameters[motor_id]
        
        if not self.validate_pwm(pwm, motor_id):
            pwm = np.clip(pwm, params.pwm_min, params.pwm_max)
        
        # Quadratic thrust model: T = a*PWM² + b*PWM + c
        thrust = (params.thrust_a * pwm**2 + 
                 params.thrust_b * pwm + 
                 params.thrust_c)
        
        return max(0.0, thrust)  # Thrust cannot be negative
    
    def torque_from_pwm(self, pwm: float, motor_id: int) -> float:
        """
        Convert PWM to torque using RPM-based model.
        
        Args:
            pwm: PWM value (0.0 to 1.0)
            motor_id: Motor identifier
            
        Returns:
            Torque in N·m
        """
        if motor_id not in self.motor_parameters:
            raise ValueError(f"Unknown motor ID: {motor_id}")
        
        params = self.motor_parameters[motor_id]
        
        if not self.validate_pwm(pwm, motor_id):
            pwm = np.clip(pwm, params.pwm_min, params.pwm_max)
        
        # Get RPM from PWM
        rpm = self.rpm_from_pwm(pwm, motor_id)
        
        # Torque model: τ = kQ * RPM²
        torque = params.torque_coefficient * rpm**2
        
        return max(0.0, torque)  # Torque cannot be negative
    
    def pwm_from_thrust(self, thrust: float, motor_id: int) -> float:
        """
        Convert thrust to PWM using inverse quadratic model.
        
        Args:
            thrust: Thrust in Newtons
            motor_id: Motor identifier
            
        Returns:
            PWM value (0.0 to 1.0)
        """
        if motor_id not in self.motor_parameters:
            raise ValueError(f"Unknown motor ID: {motor_id}")
        
        params = self.motor_parameters[motor_id]
        
        if thrust <= 0:
            return params.pwm_idle
        
        # Solve quadratic equation: a*PWM² + b*PWM + c = thrust
        # PWM = (-b ± √(b² - 4a(c-thrust))) / (2a)
        
        a, b, c = params.thrust_a, params.thrust_b, params.thrust_c
        
        if abs(a) < 1e-9:  # Linear case
            if abs(b) < 1e-9:
                return params.pwm_idle
            pwm = (thrust - c) / b
        else:
            # Quadratic case
            discriminant = b**2 - 4*a*(c - thrust)
            if discriminant < 0:
                # No real solution, use maximum PWM
                return params.pwm_max
            
            # Use positive root (PWM should be positive)
            pwm = (-b + np.sqrt(discriminant)) / (2*a)
        
        # Clip to valid range
        return np.clip(pwm, params.pwm_min, params.pwm_max)
    
    def rpm_from_pwm(self, pwm: float, motor_id: int) -> float:
        """
        Convert PWM to RPM using linear model.
        
        Args:
            pwm: PWM value (0.0 to 1.0)
            motor_id: Motor identifier
            
        Returns:
            RPM
        """
        if motor_id not in self.motor_parameters:
            raise ValueError(f"Unknown motor ID: {motor_id}")
        
        params = self.motor_parameters[motor_id]
        
        if not self.validate_pwm(pwm, motor_id):
            pwm = np.clip(pwm, params.pwm_min, params.pwm_max)
        
        # Linear RPM model: RPM = kRPM * PWM + RPM_offset
        rpm = params.rpm_coefficient * pwm + params.rpm_offset
        
        return max(0.0, rpm)  # RPM cannot be negative
    
    def get_motor_parameters(self, motor_id: int) -> MotorParameters:
        """Get motor parameters for a specific motor."""
        if motor_id not in self.motor_parameters:
            raise ValueError(f"Unknown motor ID: {motor_id}")
        return self.motor_parameters[motor_id]
    
    def validate_pwm(self, pwm: float, motor_id: int) -> bool:
        """Validate PWM value is within motor limits."""
        if motor_id not in self.motor_parameters:
            return False
        
        params = self.motor_parameters[motor_id]
        return params.pwm_min <= pwm <= params.pwm_max
    
    def get_model_summary(self) -> Dict[str, Any]:
        """Get summary of motor model parameters."""
        summary = {
            "model_type": "quadratic",
            "motor_count": len(self.motor_parameters),
            "motors": {}
        }
        
        for motor_id, params in self.motor_parameters.items():
            summary["motors"][motor_id] = {
                "type": params.motor_type.value,
                "thrust_model": f"T = {params.thrust_a:.3e}*PWM² + {params.thrust_b:.3e}*PWM + {params.thrust_c:.3e}",
                "torque_model": f"τ = {params.torque_coefficient:.3e}*RPM²",
                "rpm_model": f"RPM = {params.rpm_coefficient:.1f}*PWM + {params.rpm_offset:.1f}",
                "pwm_limits": [params.pwm_min, params.pwm_max],
                "direction": params.direction
            }
        
        return summary


def fit_quadratic_motor_model(bench_data: BenchTestData) -> MotorParameters:
    """
    Fit quadratic motor model to bench test data.
    
    Args:
        bench_data: Bench test data for motor calibration
        
    Returns:
        Fitted motor parameters
    """
    # Validate bench data
    errors = bench_data.validate()
    if errors:
        raise ValueError(f"Invalid bench data: {'; '.join(errors)}")
    
    # Convert to numpy arrays
    pwm = np.array(bench_data.pwm_values)
    thrust = np.array(bench_data.thrust_measurements)
    rpm = np.array(bench_data.rpm_measurements)
    
    # Fit quadratic thrust model: T = a*PWM² + b*PWM + c
    # Use polyfit for robust fitting
    thrust_coeffs = np.polyfit(pwm, thrust, 2)  # [a, b, c] in descending order
    thrust_a, thrust_b, thrust_c = thrust_coeffs[0], thrust_coeffs[1], thrust_coeffs[2]
    
    # Fit linear RPM model: RPM = kRPM * PWM + RPM_offset
    rpm_coeffs = np.polyfit(pwm, rpm, 1)  # [kRPM, RPM_offset]
    rpm_coefficient, rpm_offset = rpm_coeffs[0], rpm_coeffs[1]
    
    # Fit torque model: τ = kQ * RPM²
    # Use torque measurements if available, otherwise estimate from thrust
    if bench_data.torque_measurements:
        torque = np.array(bench_data.torque_measurements)
        # Fit τ = kQ * RPM²
        torque_coefficient = np.mean(torque / (rpm**2 + 1e-6))  # Avoid division by zero
    else:
        # Estimate torque from thrust using typical prop efficiency
        # This is a rough approximation - real torque data is preferred
        estimated_torque = thrust * 0.1  # Assume 10% of thrust as torque
        torque_coefficient = np.mean(estimated_torque / (rpm**2 + 1e-6))
    
    # Determine PWM limits from data
    pwm_min = np.min(pwm)
    pwm_max = np.max(pwm)
    pwm_idle = pwm_min + 0.1 * (pwm_max - pwm_min)  # 10% above minimum
    
    # Determine RPM limits
    rpm_max = np.max(rpm)
    
    return MotorParameters(
        motor_id=bench_data.motor_id,
        thrust_a=thrust_a,
        thrust_b=thrust_b,
        thrust_c=thrust_c,
        torque_coefficient=float(torque_coefficient),
        rpm_coefficient=rpm_coefficient,
        rpm_offset=rpm_offset,
        pwm_min=pwm_min,
        pwm_max=pwm_max,
        pwm_idle=pwm_idle,
        rpm_max=rpm_max,
        direction=1,  # Default to CCW, should be set based on motor specs
        calibration_date=None,  # Could be added to BenchTestData
        calibration_notes="Fitted from bench test data"
    )


def create_default_motor_model() -> QuadraticMotorModel:
    """
    Create a default motor model with typical hobby motor parameters.
    
    This provides reasonable defaults for testing and development.
    Real deployment should use bench-tested parameters.
    """
    # Example parameters for a typical 2204-2300KV motor with 5" prop
    default_params = {
        0: MotorParameters(
            motor_id=0,
            thrust_a=2.5,      # N/PWM²
            thrust_b=1.2,      # N/PWM  
            thrust_c=0.1,      # N
            torque_coefficient=1e-7,  # N·m/RPM²
            rpm_coefficient=8000,     # RPM/PWM
            rpm_offset=500,           # RPM
            direction=1
        ),
        1: MotorParameters(
            motor_id=1,
            thrust_a=2.5,
            thrust_b=1.2,
            thrust_c=0.1,
            torque_coefficient=1e-7,
            rpm_coefficient=8000,
            rpm_offset=500,
            direction=-1
        ),
        2: MotorParameters(
            motor_id=2,
            thrust_a=2.5,
            thrust_b=1.2,
            thrust_c=0.1,
            torque_coefficient=1e-7,
            rpm_coefficient=8000,
            rpm_offset=500,
            direction=1
        ),
        3: MotorParameters(
            motor_id=3,
            thrust_a=2.5,
            thrust_b=1.2,
            thrust_c=0.1,
            torque_coefficient=1e-7,
            rpm_coefficient=8000,
            rpm_offset=500,
            direction=-1
        )
    }
    
    return QuadraticMotorModel(default_params) 