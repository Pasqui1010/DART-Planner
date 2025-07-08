"""
Motor mixing module for quadrotor control.

This module implements proper motor mixing matrices that convert thrust and torque
commands to individual motor PWM signals. It supports different quadrotor layouts
(X, +, custom) and includes PWM saturation and anti-windup logic.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QuadrotorLayout(Enum):
    """Supported quadrotor layouts."""
    X_CONFIGURATION = "x"
    PLUS_CONFIGURATION = "plus"
    CUSTOM = "custom"


@dataclass 
class MotorMixingConfig:
    """Configuration for motor mixing."""
    
    # Layout type
    layout: QuadrotorLayout = QuadrotorLayout.X_CONFIGURATION
    
    # Motor positions (front-right, front-left, rear-left, rear-right)
    # Format: [x, y, z] in meters relative to CoG
    motor_positions: List[List[float]] = field(default_factory=lambda: [
        [0.15, -0.15, 0.0],  # Motor 0: Front-right
        [0.15, 0.15, 0.0],   # Motor 1: Front-left  
        [-0.15, 0.15, 0.0],  # Motor 2: Rear-left
        [-0.15, -0.15, 0.0]  # Motor 3: Rear-right
    ])
    
    # Motor spin directions (1 for CCW, -1 for CW)
    motor_directions: List[int] = field(default_factory=lambda: [1, -1, 1, -1])
    
    # PWM limits
    pwm_min: float = 0.0      # Minimum PWM value (normalized)
    pwm_max: float = 1.0      # Maximum PWM value (normalized)
    pwm_idle: float = 0.1     # Idle PWM to keep motors spinning
    # Scaling factor for linear thrust↔PWM mapping (PWM = thrust * factor)
    pwm_scaling_factor: float = 2000.0
    
    # Physical parameters
    thrust_coefficient: float = 1.0e-5   # Thrust coefficient (N/(rad/s)^2)
    torque_coefficient: float = 1.0e-7   # Torque coefficient (N⋅m/(rad/s)^2)
    arm_length: float = 0.15             # Arm length in meters
    
    # Mixing matrix (4x4) - will be computed if not provided
    mixing_matrix: Optional[np.ndarray] = None
    
    def __post_init__(self):
        """Initialize computed parameters."""
        if self.mixing_matrix is None:
            self.mixing_matrix = self._compute_mixing_matrix()
    
    def _compute_mixing_matrix(self) -> np.ndarray:
        """
        Compute the 4x4 motor mixing matrix based on layout and parameters.
        
        The mixing matrix maps [thrust, τx, τy, τz] to [motor0, motor1, motor2, motor3].
        For each motor i, the thrust contribution is:
        - Thrust: kt (thrust coefficient)
        - Roll torque: kt * arm_length * sin(motor_angle)
        - Pitch torque: kt * arm_length * cos(motor_angle)
        - Yaw torque: kq * motor_direction (drag torque)
        
        Returns:
            4x4 numpy array where each row represents a motor's contribution
        """
        matrix = np.zeros((4, 4))
        
        for i, (pos, direction) in enumerate(zip(self.motor_positions, self.motor_directions)):
            x, y, z = pos
            
            # Thrust contribution (all motors contribute equally)
            matrix[i, 0] = self.thrust_coefficient
            
            # Roll torque (τx) - depends on y-position
            matrix[i, 1] = self.thrust_coefficient * y
            
            # Pitch torque (τy) - depends on x-position  
            matrix[i, 2] = self.thrust_coefficient * x
            
            # Yaw torque (τz) - depends on motor direction and drag
            matrix[i, 3] = self.torque_coefficient * direction
            
        return matrix


class MotorMixer:
    """
    Motor mixing system for quadrotor control.
    
    Converts thrust and torque commands to individual motor PWM signals
    using a configurable mixing matrix with proper saturation handling.
    """
    
    def __init__(self, config: MotorMixingConfig):
        """
        Initialize the motor mixer.
        
        Args:
            config: Motor mixing configuration
        """
        self.config = config
        self.mixing_matrix = config.mixing_matrix
        self.inverse_matrix = self._compute_inverse_matrix()
        
        # Performance tracking
        self.saturation_events = 0
        self.last_motor_commands = np.zeros(4)
        
    def _compute_inverse_matrix(self) -> Optional[np.ndarray]:
        """
        Compute the pseudo-inverse of the mixing matrix for control allocation.
        
        Returns:
            4x4 pseudo-inverse matrix or None if not computable
        """
        try:
            # Use Moore-Penrose pseudo-inverse for over-determined system
            return np.linalg.pinv(self.mixing_matrix)
        except np.linalg.LinAlgError:
            logger.warning("Cannot compute inverse mixing matrix - using transpose")
            return self.mixing_matrix.T
    
    def mix_commands(self, thrust: float, torque: np.ndarray) -> np.ndarray:
        """
        Convert thrust and torque commands to motor PWM signals.
        
        Args:
            thrust: Thrust command in Newtons
            torque: Torque command [τx, τy, τz] in N⋅m
            
        Returns:
            4-element array of motor PWM commands (0.0 to 1.0)
        """
        if len(torque) != 3:
            raise ValueError("Torque must be 3-element array [τx, τy, τz]")
        
        # Construct command vector [thrust, τx, τy, τz]
        command_vector = np.array([thrust, torque[0], torque[1], torque[2]])
        
        # Apply mixing matrix to get motor thrusts
        motor_thrusts = self.mixing_matrix @ command_vector

        # Runtime safety guards
        if not np.isfinite(motor_thrusts).all():
            raise RuntimeError("Non-finite motor thrust command detected")

        # Convert thrust to PWM (simplified model)
        # In reality, this would use motor characteristics and prop curves
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
        Convert motor thrust commands to PWM values.
        
        Uses simplified linear relationship for easier tuning.
        In practice, this would use motor characterization data.
        
        Args:
            motor_thrusts: Array of motor thrust commands in N
            
        Returns:
            Array of PWM values (0.0 to 1.0)
        """
        # Ensure non-negative thrust
        motor_thrusts = np.maximum(motor_thrusts, 0.0)
        
        # Simple linear conversion using configurable scaling factor
        pwm_values = motor_thrusts * self.config.pwm_scaling_factor
        
        return pwm_values
    
    def _saturate_pwm(self, pwm_values: np.ndarray) -> np.ndarray:
        """
        Apply PWM saturation with anti-windup logic.
        
        Args:
            pwm_values: Raw PWM values
            
        Returns:
            Saturated PWM values
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
            motor_pwms: Motor PWM commands
            
        Returns:
            [thrust, τx, τy, τz] command vector
        """
        if self.inverse_matrix is None:
            raise RuntimeError("Cannot compute control allocation without inverse matrix")
        
        # Convert PWM to thrust
        motor_thrusts = self._pwm_to_thrust(motor_pwms)
        
        # Apply inverse mixing matrix
        return self.inverse_matrix @ motor_thrusts
    
    def _pwm_to_thrust(self, pwm_values: np.ndarray) -> np.ndarray:
        """
        Convert PWM values to thrust commands (inverse of _thrust_to_pwm).
        
        Args:
            pwm_values: PWM values (0.0 to 1.0)
            
        Returns:
            Motor thrust commands in N
        """
        # Inverse of the linear mapping in _thrust_to_pwm
        motor_thrusts = pwm_values / self.config.pwm_scaling_factor
        
        return motor_thrusts
    
    def validate_configuration(self) -> List[str]:
        """
        Validate the motor mixing configuration.
        
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check matrix dimensions
        if self.mixing_matrix.shape != (4, 4):
            issues.append(f"Mixing matrix must be 4x4, got {self.mixing_matrix.shape}")
        
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
        
        return issues
    
    def get_motor_layout_info(self) -> Dict[str, Union[str, List, np.ndarray]]:
        """
        Get information about the motor layout.
        
        Returns:
            Dictionary with motor layout information
        """
        return {
            "layout": self.config.layout.value,
            "motor_positions": self.config.motor_positions,
            "motor_directions": self.config.motor_directions,
            "mixing_matrix": self.mixing_matrix,
            "matrix_rank": np.linalg.matrix_rank(self.mixing_matrix),
            "saturation_events": self.saturation_events
        }

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def reset_saturation_counter(self) -> None:
        """Reset the saturation event counter (useful for tests or flight phases)."""
        self.saturation_events = 0


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