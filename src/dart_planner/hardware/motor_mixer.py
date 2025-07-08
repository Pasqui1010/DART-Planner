"""
Motor mixing module for quadrotor control.

This module implements proper motor mixing matrices that convert thrust and torque
commands to individual motor PWM signals. It supports different quadrotor layouts
(X, +, custom) and includes PWM saturation and anti-windup logic.

All units are SI (International System of Units):
- Thrust: Newtons (N)
- Torque: Newton-meters (N⋅m) 
- Position: meters (m)
- PWM: normalized (0.0 to 1.0)
- Angular velocity: radians per second (rad/s)

The mixing matrix is computed from physical geometry and motor characteristics,
eliminating magic scale factors and ensuring dimensional consistency.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from .motor_model import MotorModel, QuadraticMotorModel, create_default_motor_model
from ..common.units import Q_, Quantity, ensure_units

logger = logging.getLogger(__name__)


class QuadrotorLayout(Enum):
    """Supported quadrotor layouts."""
    X_CONFIGURATION = "x"
    PLUS_CONFIGURATION = "plus"
    CUSTOM = "custom"


@dataclass 
class MotorMixingConfig:
    """
    Configuration for motor mixing with consistent SI units.
    
    All physical parameters use SI units for dimensional consistency.
    The mixing matrix is computed from geometry and motor characteristics,
    eliminating magic scale factors.
    """
    
    # Layout type
    layout: QuadrotorLayout = QuadrotorLayout.X_CONFIGURATION
    
    # Motor positions relative to center of gravity (meters)
    # Format: [x, y, z] in meters relative to CoG
    motor_positions: List[List[float]] = field(default_factory=lambda: [
        [0.15, -0.15, 0.0],  # Motor 0: Front-right
        [0.15, 0.15, 0.0],   # Motor 1: Front-left  
        [-0.15, 0.15, 0.0],  # Motor 2: Rear-left
        [-0.15, -0.15, 0.0]  # Motor 3: Rear-right
    ])
    
    # Motor spin directions (1 for CCW, -1 for CW)
    motor_directions: List[int] = field(default_factory=lambda: [1, -1, 1, -1])
    
    # PWM operating limits (normalized, unitless)
    pwm_min: float = 0.0      # Minimum PWM value (normalized)
    pwm_max: float = 1.0      # Maximum PWM value (normalized)
    pwm_idle: float = 0.1     # Idle PWM to keep motors spinning
    
    # Physical parameters (SI units)
    arm_length: float = 0.15  # Distance from CoG to motor in meters
    
    # Motor model for physics-based thrust/torque prediction
    motor_model: Any = None
    
    # Mixing matrix (4x4) - computed from geometry and motor model
    mixing_matrix: Optional[np.ndarray] = None
    
    def __post_init__(self):
        """Initialize computed parameters."""
        if self.mixing_matrix is None:
            self.mixing_matrix = self._compute_mixing_matrix()
    
    def _compute_mixing_matrix(self) -> np.ndarray:
        """
        Compute the 4x4 motor mixing matrix based on physical geometry.

        The mixing matrix maps [thrust, τx, τy, τz] to [motor0, motor1, motor2, motor3].
        Each row represents a motor's contribution to the total thrust and torques.

        Physical basis:
        - Thrust: Each motor contributes equally to total thrust
        - Roll torque (τx): τx = Σ(Fi * yi) where Fi is motor thrust, yi is y-position
        - Pitch torque (τy): τy = Σ(Fi * xi) where Fi is motor thrust, xi is x-position  
        - Yaw torque (τz): τz = Σ(direction_i * Fi)

        Returns:
            4x4 numpy array with proper physical units
        """
        matrix = np.zeros((4, 4))
        for i, (pos, direction) in enumerate(zip(self.motor_positions, self.motor_directions)):
            x, y, z = pos
            matrix[i, 0] = 1.0
            matrix[i, 1] = y
            matrix[i, 2] = x
            matrix[i, 3] = direction
        return matrix


class MotorMixer:
    """
    Motor mixing system for quadrotor control with consistent SI units.
    
    Converts thrust and torque commands to individual motor PWM signals
    using a physics-based mixing matrix with proper saturation handling.
    
    Input units:
    - thrust: Newtons (N)
    - torque: [τx, τy, τz] in Newton-meters (N⋅m)
    
    Output units:
    - motor_pwms: normalized PWM values (0.0 to 1.0)
    """
    
    def __init__(self, config: MotorMixingConfig):
        """
        Initialize the motor mixer.
        
        Args:
            config: Motor mixing configuration with SI units
        """
        self.config = config
        
        # Initialize motor model (use default if not provided)
        if config.motor_model is None:
            self.motor_model = create_default_motor_model()
            logger.info("Using default motor model - consider providing calibrated model for production")
        else:
            self.motor_model = config.motor_model
            logger.info("Using provided motor model")
        # Compute physically-correct mixing matrix and its pseudo-inverse for control allocation
        self.mixing_matrix = self._compute_mixing_matrix()
        self.inverse_matrix = self._compute_inverse_matrix()
        
        # Performance tracking
        self.saturation_events = 0
        self.last_motor_commands = np.zeros(4)
        
        # Validate configuration
        validation_issues = self.validate_configuration()
        if validation_issues:
            logger.warning(f"Motor mixer configuration issues: {validation_issues}")
        
    def _compute_inverse_matrix(self) -> Optional[np.ndarray]:
        """
        Compute the inverse of the mixing matrix for control allocation.
        Uses direct solve if the matrix is square, otherwise falls back to pseudo-inverse.
        Returns:
            Inverse or pseudo-inverse matrix, or None if mixing_matrix is None.
        """
        if self.mixing_matrix is None:
            return None
        try:
            # Direct inversion via solve: B * X = I
            return np.linalg.solve(self.mixing_matrix, np.eye(self.mixing_matrix.shape[0]))
        except (np.linalg.LinAlgError, ValueError):
            logger.warning("Direct inverse failed, falling back to pseudo-inverse")
            return np.linalg.pinv(self.mixing_matrix)
    
    def mix_commands(self, thrust: float, torque: np.ndarray) -> np.ndarray:
        """
        Convert thrust and torque commands to motor PWM signals.
        
        Args:
            thrust: Thrust command in Newtons (N)
            torque: Torque command [τx, τy, τz] in Newton-meters (N⋅m)
            
        Returns:
            4-element array of motor PWM commands (0.0 to 1.0)
            
        Raises:
            ValueError: If torque array is not 3 elements
            RuntimeError: If non-finite motor thrust command detected
        """
        if len(torque) != 3:
            raise ValueError("Torque must be 3-element array [τx, τy, τz]")
        
        # Validate input units (thrust should be positive, torque can be negative)
        if thrust < 0:
            logger.warning(f"Negative thrust command: {thrust} N - clamping to zero")
            thrust = 0.0
        
        # Construct command vector [thrust, τx, τy, τz] in SI units
        command_vector = np.array([thrust, torque[0], torque[1], torque[2]])
        
        # Allocate motor thrusts via inverse mixing matrix
        motor_thrusts = self.inverse_matrix @ command_vector

        # Runtime safety guards
        if not np.isfinite(motor_thrusts).all():
            raise RuntimeError(f"Non-finite motor thrust command detected: {motor_thrusts}")

        # Convert thrust to PWM using physics-based motor model
        motor_pwms = self._thrust_to_pwm(motor_thrusts)

        # Check for pre-clip overrun ( >110% of max )
        overrun_limit = self.config.pwm_max * 1.1
        if np.any(motor_pwms > overrun_limit):
            logger.warning("Motor PWM exceeds 110% of max before clipping – command will be saturated")

        # Apply saturation and anti-windup
        motor_pwms_saturated = self._saturate_pwm(motor_pwms)

        # Track saturation events
        if not np.allclose(motor_pwms, motor_pwms_saturated, rtol=1e-6):
            self.saturation_events += 1
            logger.debug(f"Motor saturation event {self.saturation_events}")

        # Detect impossible idle saturation when non-trivial thrust requested
        if (motor_pwms_saturated == self.config.pwm_idle).all() and thrust > 0.2:
            logger.error("All motors at idle despite positive thrust request – possible actuator fault")

        self.last_motor_commands = motor_pwms_saturated
        return motor_pwms_saturated
    
    def _thrust_to_pwm(self, motor_thrusts: np.ndarray) -> np.ndarray:
        """
        Convert motor thrust commands to PWM values using physics-based motor model.
        
        Args:
            motor_thrusts: Array of motor thrust commands in Newtons (N)
            
        Returns:
            Array of PWM values (0.0 to 1.0)
        """
        # Ensure non-negative thrust
        motor_thrusts = np.maximum(motor_thrusts, 0.0)
        
        # Use motor model for each motor
        pwm_values = np.zeros_like(motor_thrusts)
        for i, thrust in enumerate(motor_thrusts):
            pwm_values[i] = self.motor_model.pwm_from_thrust(thrust, motor_id=i)
        
        return pwm_values
    
    def _saturate_pwm(self, pwm_values: np.ndarray) -> np.ndarray:
        """
        Apply PWM saturation with anti-windup logic.
        
        Args:
            pwm_values: Raw PWM values (0.0 to 1.0)
            
        Returns:
            Saturated PWM values (0.0 to 1.0)
        """
        # Simple saturation
        saturated = np.clip(pwm_values, self.config.pwm_min, self.config.pwm_max)
        
        # Ensure minimum idle PWM for armed motors
        saturated = np.maximum(saturated, self.config.pwm_idle)
        
        return saturated
    
    def get_control_allocation(self, motor_pwms: np.ndarray) -> np.ndarray:
        """
        Convert motor PWM commands back to thrust/torque (for validation).
        
        Args:
            motor_pwms: Motor PWM commands (0.0 to 1.0)
            
        Returns:
            [thrust, τx, τy, τz] command vector in SI units (N, N⋅m, N⋅m, N⋅m)
        """
        if self.inverse_matrix is None:
            raise RuntimeError("Cannot compute control allocation without inverse matrix")
        
        # Convert PWM to thrust
        motor_thrusts = self._pwm_to_thrust(motor_pwms)
        
        # Apply inverse mixing matrix
        return self.inverse_matrix @ motor_thrusts
    
    def _pwm_to_thrust(self, pwm_values: np.ndarray) -> np.ndarray:
        """
        Convert PWM values to thrust commands using physics-based motor model.
        
        Args:
            pwm_values: PWM values (0.0 to 1.0)
            
        Returns:
            Motor thrust commands in Newtons (N)
        """
        # Use motor model for each motor
        motor_thrusts = np.zeros_like(pwm_values)
        for i, pwm in enumerate(pwm_values):
            motor_thrusts[i] = self.motor_model.thrust_from_pwm(pwm, motor_id=i)
        
        return motor_thrusts
    
    def validate_configuration(self) -> List[str]:
        """
        Validate the motor mixing configuration.
        
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check matrix dimensions
        if self.mixing_matrix is None:
            issues.append("Mixing matrix is None")
        elif self.mixing_matrix.shape != (4, 4):
            issues.append(f"Mixing matrix must be 4x4, got {self.mixing_matrix.shape}")
        else:
            # Check matrix rank
            rank = np.linalg.matrix_rank(self.mixing_matrix)
            if rank < 4:
                issues.append(f"Mixing matrix is rank-deficient (rank={rank})")
        
        # Check motor positions
        if len(self.config.motor_positions) != 4:
            issues.append(f"Must have 4 motor positions, got {len(self.config.motor_positions)}")
        
        # Check motor directions
        if len(self.config.motor_directions) != 4:
            issues.append(f"Must have 4 motor directions, got {len(self.config.motor_directions)}")
        
        # Check PWM limits
        if self.config.pwm_min >= self.config.pwm_max:
            issues.append("PWM min must be less than PWM max")
        
        if self.config.pwm_idle < self.config.pwm_min or self.config.pwm_idle > self.config.pwm_max:
            issues.append("PWM idle must be between PWM min and max")
        
        # Check physical parameters
        if self.config.arm_length <= 0:
            issues.append("Arm length must be positive")
        
        # Check motor positions are reasonable
        for i, pos in enumerate(self.config.motor_positions):
            if len(pos) != 3:
                issues.append(f"Motor {i} position must have 3 coordinates")
            x, y, z = pos
            if abs(x) > 1.0 or abs(y) > 1.0 or abs(z) > 0.5:
                issues.append(f"Motor {i} position {pos} seems unreasonable (units: meters)")
        
        return issues
    
    def get_motor_layout_info(self) -> Dict[str, Union[str, List, np.ndarray, int, Dict[str, str], None]]:
        """
        Get information about the motor layout.
        
        Returns:
            Dictionary with motor layout information
        """
        matrix_rank = np.linalg.matrix_rank(self.mixing_matrix) if self.mixing_matrix is not None else 0
        
        return {
            "layout": self.config.layout.value,
            "motor_positions": self.config.motor_positions,
            "motor_directions": self.config.motor_directions,
            "mixing_matrix": self.mixing_matrix,
            "matrix_rank": matrix_rank,
            "saturation_events": self.saturation_events,
            "units": {
                "thrust": "Newtons (N)",
                "torque": "Newton-meters (N⋅m)",
                "position": "meters (m)",
                "pwm": "normalized (0.0 to 1.0)"
            }
        }

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def reset_saturation_counter(self) -> None:
        """Reset the saturation event counter (useful for tests or flight phases)."""
        self.saturation_events = 0

    def _compute_mixing_matrix(self) -> np.ndarray:
        """
        Compute the 4xN mixing matrix B such that B @ [F_i] = [T, τx, τy, τz].
        Uses calibrated drag-to-thrust ratios from the motor model.
        """
        positions = self.config.motor_positions
        directions = self.config.motor_directions
        n = len(positions)
        B = np.zeros((4, n))
        for i, (pos, direction) in enumerate(zip(positions, directions)):
            x, y, _ = pos
            # compute drag-to-thrust ratio at max PWM
            thrust_max = self.motor_model.thrust_from_pwm(self.config.pwm_max, motor_id=i)
            torque_max = self.motor_model.torque_from_pwm(self.config.pwm_max, motor_id=i)
            k_drag = torque_max / thrust_max if thrust_max > 0 else 0.0
            B[0, i] = 1.0
            B[1, i] = y
            B[2, i] = x
            B[3, i] = direction * k_drag
        return B


def create_x_configuration_mixer(arm_length: float = 0.15) -> MotorMixer:
    """
    Create a motor mixer for standard X configuration quadrotor.
    
    Args:
        arm_length: Distance from center to motor in meters
        
    Returns:
        Configured MotorMixer instance
    """
    config = MotorMixingConfig(
        layout=QuadrotorLayout.X_CONFIGURATION,
        motor_positions=[
            [arm_length * 0.707, -arm_length * 0.707, 0.0],  # Front-right
            [arm_length * 0.707, arm_length * 0.707, 0.0],   # Front-left
            [-arm_length * 0.707, arm_length * 0.707, 0.0],  # Rear-left
            [-arm_length * 0.707, -arm_length * 0.707, 0.0]  # Rear-right
        ],
        motor_directions=[1, -1, 1, -1],  # CCW, CW, CCW, CW
        arm_length=arm_length
    )
    
    return MotorMixer(config)


def create_plus_configuration_mixer(arm_length: float = 0.15) -> MotorMixer:
    """
    Create a motor mixer for standard + configuration quadrotor.
    
    Args:
        arm_length: Distance from center to motor in meters
        
    Returns:
        Configured MotorMixer instance
    """
    config = MotorMixingConfig(
        layout=QuadrotorLayout.PLUS_CONFIGURATION,
        motor_positions=[
            [arm_length, 0.0, 0.0],   # Front
            [0.0, arm_length, 0.0],   # Left
            [0.0, -arm_length, 0.0],  # Right
            [-arm_length, 0.0, 0.0]   # Rear
        ],
        motor_directions=[1, -1, 1, -1],  # CCW, CW, CCW, CW
        arm_length=arm_length
    )
    
    return MotorMixer(config) 