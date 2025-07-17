import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

import numpy as np
from pint import Quantity

from dart_planner.common.types import ControlCommand, DroneState, BodyRateCommand, FastDroneState
from dart_planner.common.logging_config import get_logger
from dart_planner.common.units import Q_, to_float
from .control_config import get_controller_config, ControllerTuningProfile
from dart_planner.common.vehicle_params import get_params, get_control_constants, load_hardware_params, compute_max_torque_xyz
from dart_planner.common.coordinate_frames import get_coordinate_frame_manager

# Load hardware parameters and compute max torque limits
try:
    _hardware_params = load_hardware_params()
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to load hardware params at import time: {e}")
    _hardware_params = {}
_max_torque_xyz = compute_max_torque_xyz(_hardware_params)

@dataclass
class GeometricControllerConfig:
    """
    Configuration for geometric controller gains (units-aware)
    max_torque_xyz is now computed from hardware.yaml for physical safety.
    Gains are tuned for transport-delay compensation (25ms delay).
    Contributors: update config/hardware.yaml for your platform.
    
    Note: Gains are reduced by ~30% to account for transport delay phase lag.
    This prevents instability while maintaining good tracking performance.
    """
    # Position control gains (PID) - Retuned for transport delay compensation
    # Original: [10.0, 10.0, 12.0] -> Reduced by ~30% for stability
    kp_pos: np.ndarray = field(default_factory=lambda: np.array([7.0, 7.0, 8.5]))
    # Original: [0.5, 0.5, 1.0] -> Reduced by ~30% for stability
    ki_pos: np.ndarray = field(default_factory=lambda: np.array([0.35, 0.35, 0.7]))
    # Original: [6.0, 6.0, 8.0] -> Reduced by ~30% for stability
    kd_pos: np.ndarray = field(default_factory=lambda: np.array([4.2, 4.2, 5.6]))
    # Attitude control gains (PD) - Retuned for transport delay compensation
    # Original: [12.0, 12.0, 5.0] -> Reduced by ~25% for stability
    kp_att: np.ndarray = field(default_factory=lambda: np.array([9.0, 9.0, 3.75]))
    # Original: [4.0, 4.0, 2.0] -> Reduced by ~25% for stability
    kd_att: np.ndarray = field(default_factory=lambda: np.array([3.0, 3.0, 1.5]))
    # Physical inertia diagonal (kg·m²)
    inertia: np.ndarray = field(default_factory=lambda: np.array(get_params().inertia))
    # Per-axis torque limits (N·m), now auto-computed from hardware config
    max_torque_xyz: np.ndarray = field(default_factory=lambda: _max_torque_xyz)
    # Feedforward gains
    ff_pos: float = 1.2
    ff_vel: float = 0.8
    # Integral limits and constraints
    max_integral_pos: float = 5.0
    max_tilt_angle: float = np.pi / 3
    # Physical parameters
    mass: float = get_params().mass
    gravity: float = get_params().gravity
    max_thrust: float = 20.0
    min_thrust: float = 0.5
    # Tracking performance thresholds
    tracking_error_threshold: float = 2.0
    velocity_error_threshold: float = 1.0
    # Anti-windup configuration
    anti_windup_method: str = "clamping"  # "clamping" or "back_calculation"
    max_integral_per_axis: np.ndarray = field(default_factory=lambda: np.array([2.0, 2.0, 3.0]))  # Per-axis limits (m)
    back_calculation_gain: float = 0.1  # Kb for back-calculation method
    integral_decay_factor: float = 0.99  # Decay factor when approaching limits
    saturation_threshold: float = 0.95  # Threshold for saturation detection (0.95 = 95% of limit)
    # Yaw-alignment singularity detection
    yaw_singularity_threshold: float = 0.1  # cos(angle) threshold for singularity detection (0.1 ≈ 84°)
    yaw_singularity_fallback_method: str = "skip_yaw"  # "skip_yaw", "default_heading", or "maintain_current"
    default_heading_yaw: float = 0.0  # Default yaw angle when singularity detected (rad)
    yaw_singularity_warning_threshold: float = 0.3  # cos(angle) threshold for warning (0.3 ≈ 72°)

class GeometricController:
    """
    Geometric controller for quadrotor (units-aware).
    All physical quantities are pint.Quantity and units are enforced at boundaries.
    """
    def __init__(self, config: GeometricControllerConfig | None = None, tuning_profile: str = "sitl_optimized"):
        self.logger = get_logger(__name__)
        if config is None:
            config = GeometricControllerConfig()
        if tuning_profile:
            self._apply_tuning_profile(config, tuning_profile)
        self.config = config
        self.tuning_profile_name = tuning_profile
        self.last_time = None
        # Integrates velocity error over time (∫vel_error dt) ⇒ units of metres.
        self.integral_vel_error = np.zeros(3)
        self.position_errors = []
        self.velocity_errors = []
        self.control_outputs = []
        self.failsafe_active = False
        self.failsafe_count = 0
        
        # Anti-windup state tracking
        self.last_thrust_saturated = False
        self.last_torque_saturated = np.array([False, False, False])
        self.unsaturated_thrust = 0.0
        self.unsaturated_torque = np.zeros(3)
        self._thrust_saturation_count = 0
        self._torque_saturation_count = 0
        
        # Initialize coordinate frame manager for consistent gravity handling
        self._frame_manager = get_coordinate_frame_manager()
        
        # Get gravity vector in correct frame
        self._gravity_vector = self._frame_manager.get_gravity_vector(self.config.gravity)
        
        self.last_valid_thrust = self.config.mass * self.config.gravity  # Newtons
        
        # Pre-computed constants for fast control loop (no unit conversions)
        self._control_constants = get_control_constants()
        self._fast_mass = self._control_constants['mass']
        self._fast_gravity_magnitude = self._control_constants['gravity']
        # Use frame-consistent gravity vector for fast control
        self._fast_gravity_vector = self._frame_manager.get_gravity_vector(self._fast_gravity_magnitude)
        
        # Use config's inertia matrix for proper matrix multiplication in torque calculation
        # This ensures the controller uses the provided config, not global vehicle params
        self._fast_inertia = np.diag(self.config.inertia)
        self._fast_min_thrust = self.config.min_thrust * self._fast_mass * self._fast_gravity_magnitude
        
        self.logger.info(f"🎯 Geometric Controller initialized with '{tuning_profile}' profile")
        self.logger.info(f"   Position gains: Kp={self.config.kp_pos}, Ki={self.config.ki_pos}, Kd={self.config.kd_pos}")
        self.logger.info(f"   Attitude gains: Kp={self.config.kp_att}, Kd={self.config.kd_att}")
        self.logger.info(f"   Feedforward: pos={self.config.ff_pos:.1f}, vel={self.config.ff_vel:.1f}")
        self.logger.info(f"   Fast control constants: mass={self._fast_mass:.3f}kg, gravity={self._fast_gravity_magnitude:.3f}m/s²")
        self.logger.info(f"   Coordinate frame: {self._frame_manager.world_frame.value}, gravity_vector={self._gravity_vector}")
        self.logger.info(f"   Anti-windup: method={self.config.anti_windup_method}, per-axis limits={self.config.max_integral_per_axis}")
        self.logger.info(f"   Saturation threshold: {self.config.saturation_threshold:.2f}, decay factor: {self.config.integral_decay_factor:.3f}")
        self.logger.info(f"   Yaw singularity: threshold={self.config.yaw_singularity_threshold:.3f}, fallback={self.config.yaw_singularity_fallback_method}")
        self.logger.info(f"   Yaw warning threshold: {self.config.yaw_singularity_warning_threshold:.3f}, default heading: {self.config.default_heading_yaw:.2f}rad")

    def _apply_tuning_profile(self, config: GeometricControllerConfig, profile_name: str):
        try:
            profile = get_controller_config(profile_name)
            config.kp_pos = profile.kp_pos.copy()
            config.ki_pos = profile.ki_pos.copy()
            config.kd_pos = profile.kd_pos.copy()
            config.kp_att = profile.kp_att.copy()
            config.kd_att = profile.kd_att.copy()
            config.ff_pos = profile.ff_pos
            config.ff_vel = profile.ff_vel
            config.max_tilt_angle = profile.max_tilt_angle
            config.max_thrust = profile.max_thrust
            config.min_thrust = profile.min_thrust
            config.max_integral_pos = profile.max_integral_pos
            config.tracking_error_threshold = profile.tracking_error_threshold
            config.velocity_error_threshold = profile.velocity_error_threshold
            self.logger.info(f"✅ Applied '{profile_name}' tuning profile: {profile.description}")
        except ValueError as e:
            self.logger.warning(f"⚠️ Failed to apply tuning profile: {e}")
            self.logger.info("   Using default configuration")

    def _detect_yaw_singularity(self, yaw_vector: np.ndarray, b3_des: np.ndarray) -> Tuple[bool, float, str]:
        """
        Detect yaw-alignment singularity when yaw vector is nearly parallel to thrust vector.
        
        Args:
            yaw_vector: Unit vector in desired yaw direction [cos(yaw), sin(yaw), 0]
            b3_des: Normalized desired thrust direction vector
            
        Returns:
            is_singular: True if singularity detected
            cos_angle: Cosine of angle between vectors (1 = parallel, 0 = perpendicular)
            fallback_method: Method to use for handling singularity
        """
        # Compute cosine of angle between yaw vector and thrust vector
        cos_angle = abs(np.dot(yaw_vector, b3_des))
        
        # Check for singularity (vectors nearly parallel)
        is_singular = cos_angle >= self.config.yaw_singularity_threshold
        
        # Log warning when approaching singularity
        if cos_angle > self.config.yaw_singularity_warning_threshold:
            angle_deg = np.arccos(np.clip(cos_angle, 0, 1)) * 180 / np.pi
            self.logger.warning(f"⚠️ Approaching yaw singularity: angle={angle_deg:.1f}° (cos={cos_angle:.3f})")
            
        if is_singular:
            angle_deg = np.arccos(np.clip(cos_angle, 0, 1)) * 180 / np.pi
            self.logger.warning(f"🚨 YAW SINGULARITY DETECTED: angle={angle_deg:.1f}° (cos={cos_angle:.3f})")
            
        return is_singular, cos_angle, self.config.yaw_singularity_fallback_method

    def _handle_yaw_singularity(self, yaw_vector: np.ndarray, b3_des: np.ndarray, 
                               current_yaw: float, fallback_method: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Handle yaw-alignment singularity by computing safe desired rotation matrix.
        
        Args:
            yaw_vector: Original desired yaw vector
            b3_des: Normalized desired thrust direction
            current_yaw: Current yaw angle (rad)
            fallback_method: Method to use ("skip_yaw", "default_heading", "maintain_current")
            
        Returns:
            b1_des: Safe desired x-axis
            b2_des: Safe desired y-axis  
            b3_des: Normalized thrust direction (unchanged)
        """
        if fallback_method == "skip_yaw":
            # Skip yaw control entirely - use thrust direction to define frame
            # Choose b1_des perpendicular to b3_des in the horizontal plane
            if abs(b3_des[2]) < 0.99:  # Not pointing straight up/down
                # Project [1,0,0] onto plane perpendicular to b3_des
                b1_des = np.array([1.0, 0.0, 0.0]) - np.dot(np.array([1.0, 0.0, 0.0]), b3_des) * b3_des
                b1_des = b1_des / np.linalg.norm(b1_des)
            else:
                # Thrust pointing straight up/down, use arbitrary horizontal direction
                b1_des = np.array([1.0, 0.0, 0.0])
                
        elif fallback_method == "default_heading":
            # Use default heading direction
            default_yaw_vector = np.array([np.cos(self.config.default_heading_yaw), 
                                         np.sin(self.config.default_heading_yaw), 0])
            b1_des = np.cross(default_yaw_vector, b3_des)
            b1_des_norm = np.linalg.norm(b1_des)
            if b1_des_norm > 1e-6:
                b1_des = b1_des / b1_des_norm
            else:
                # Fallback to skip_yaw method if default heading also singular
                b1_des = np.array([1.0, 0.0, 0.0]) - np.dot(np.array([1.0, 0.0, 0.0]), b3_des) * b3_des
                b1_des = b1_des / np.linalg.norm(b1_des)
                
        elif fallback_method == "maintain_current":
            # Maintain current yaw direction
            current_yaw_vector = np.array([np.cos(current_yaw), np.sin(current_yaw), 0])
            b1_des = np.cross(current_yaw_vector, b3_des)
            b1_des_norm = np.linalg.norm(b1_des)
            if b1_des_norm > 1e-6:
                b1_des = b1_des / b1_des_norm
            else:
                # Fallback to skip_yaw method if current yaw also singular
                b1_des = np.array([1.0, 0.0, 0.0]) - np.dot(np.array([1.0, 0.0, 0.0]), b3_des) * b3_des
                b1_des = b1_des / np.linalg.norm(b1_des)
        else:
            # Unknown method, use skip_yaw as default
            self.logger.warning(f"⚠️ Unknown yaw singularity fallback method: {fallback_method}, using skip_yaw")
            b1_des = np.array([1.0, 0.0, 0.0]) - np.dot(np.array([1.0, 0.0, 0.0]), b3_des) * b3_des
            b1_des = b1_des / np.linalg.norm(b1_des)
            
        # Compute b2_des to complete orthonormal frame
        b2_des = np.cross(b3_des, b1_des)
        
        self.logger.info(f"🔄 Yaw singularity handled using '{fallback_method}' method")
        return b1_des, b2_des, b3_des

    def compute_control_fast(
        self,
        pos: np.ndarray,
        vel: np.ndarray,
        att: np.ndarray,
        ang_vel: np.ndarray,
        desired_pos: np.ndarray,
        desired_vel: np.ndarray,
        desired_acc: np.ndarray,
        desired_yaw: float = 0.0,
        desired_yaw_rate: float = 0.0,
        dt: float = 0.001,
    ) -> Tuple[float, np.ndarray]:
        """
        Optimized control computation without pint unit conversions.
        
        All inputs are assumed to be in base SI units:
        - pos, vel, desired_pos, desired_vel: meters, m/s
        - att, ang_vel: radians, rad/s
        - desired_acc: m/s²
        - desired_yaw, desired_yaw_rate: radians, rad/s
        - dt: seconds
        
        Returns:
            thrust: float (Newtons)
            torque: np.ndarray (N·m, 3 elements)
        """
        if dt <= 0 or dt > 0.1:
            return float(self._fast_mass * self._fast_gravity_magnitude), np.zeros(3)
            
        # Position and velocity errors
        pos_error = desired_pos - pos
        vel_error = desired_vel - vel
        
        # Track errors for performance metrics
        pos_error_magnitude = float(np.linalg.norm(pos_error))
        vel_error_magnitude = float(np.linalg.norm(vel_error))
        self.position_errors.append(pos_error_magnitude)
        self.velocity_errors.append(vel_error_magnitude)
        
        # Compute desired acceleration (PID + feedforward)
        acc_pid = (
            self.config.kp_pos * pos_error +
            self.config.kd_pos * vel_error +
            self.config.ki_pos * self.integral_vel_error
        )
        acc_des = desired_acc + acc_pid
        
        # Compute thrust vector in world frame
        thrust_vector_world = acc_des - self._fast_gravity_vector
        thrust_magnitude = np.linalg.norm(thrust_vector_world)
        
        # Store unsaturated thrust for anti-windup
        self.unsaturated_thrust = thrust_magnitude
        
        # Validate frame consistency
        # validate_frame_consistent_operation("fast_control_gravity", self._fast_gravity_vector) # This line was removed
        
        # Apply thrust limits and detect saturation
        thrust_saturated = False
        if thrust_magnitude > self.config.max_thrust:
            thrust_magnitude = self.config.max_thrust
            thrust_saturated = True
            self._thrust_saturation_count += 1
        elif thrust_magnitude < self._fast_min_thrust:
            thrust_magnitude = self._fast_min_thrust
            thrust_saturated = True
            self._thrust_saturation_count += 1
            
        self.last_thrust_saturated = thrust_saturated
        
        # Update integral error with anti-windup protection
        self._update_integral_error(vel_error, dt, thrust_saturated, self.last_torque_saturated)
        
        # Compute desired body z-axis direction
        if thrust_magnitude > 1e-6:
            b3_des = thrust_vector_world / thrust_magnitude
        else:
            b3_des = np.array([0, 0, 1])
            
        # Check tilt angle constraint
        tilt_angle = np.arccos(np.clip(b3_des[2], -1, 1))
        if tilt_angle > self.config.max_tilt_angle:
            scale_factor = np.cos(self.config.max_tilt_angle) / b3_des[2]
            b3_des[:2] *= scale_factor
            b3_des[2] = np.cos(self.config.max_tilt_angle)
            b3_des = b3_des / np.linalg.norm(b3_des)
        
        # Geometric attitude control
        torque = self._fast_geometric_attitude_control(
            att, ang_vel, b3_des, desired_yaw, desired_yaw_rate
        )
        
        return float(thrust_magnitude), torque

    def _fast_geometric_attitude_control(
        self,
        att: np.ndarray,
        ang_vel: np.ndarray,
        b3_des: np.ndarray,
        yaw_des: float,
        yaw_rate_des: float,
    ) -> np.ndarray:
        """Fast geometric attitude control without unit conversions."""
        # Current rotation matrix
        R = self._euler_to_rotation_matrix(att)
        
        # Desired rotation matrix with singularity detection
        yaw_vector = np.array([np.cos(yaw_des), np.sin(yaw_des), 0])
        b3_des_normalized = b3_des / np.linalg.norm(b3_des)
        
        # Detect yaw-alignment singularity
        current_yaw = att[2] if len(att) >= 3 else 0.0  # Extract yaw from attitude
        is_singular, cos_angle, fallback_method = self._detect_yaw_singularity(yaw_vector, b3_des_normalized)
        
        if is_singular:
            # Handle singularity using fallback method
            b1_des, b2_des, b3_des_normalized = self._handle_yaw_singularity(
                yaw_vector, b3_des_normalized, current_yaw, fallback_method
            )
        else:
            # Normal case: compute desired frame using cross product
            b1_des = np.cross(yaw_vector, b3_des_normalized)
            b1_des_norm = np.linalg.norm(b1_des)
            if b1_des_norm > 1e-6:
                b1_des = b1_des / b1_des_norm
            else:
                # Fallback for numerical issues
                b1_des = np.array([1, 0, 0])
            b2_des = np.cross(b3_des_normalized, b1_des)
            
        R_des = np.column_stack([b1_des, b2_des, b3_des_normalized])
        
        # Attitude error
        eR = 0.5 * self._vee_map(R_des.T @ R - R.T @ R_des)
        
        # Angular velocity error
        omega_des = np.array([0, 0, yaw_rate_des])
        eOmega = ang_vel - omega_des
        
        # Control law with coriolis compensation
        # Use matrix multiplication for proper inertia tensor application
        coriolis = np.cross(ang_vel, self._fast_inertia @ ang_vel)
        torque = -self.config.kp_att * eR - self.config.kd_att * eOmega + coriolis
        
        # Store unsaturated torque for anti-windup
        self.unsaturated_torque = torque.copy()
        
        # Apply torque limits and detect saturation
        torque_saturated = np.zeros(3, dtype=bool)
        for i in range(3):
            if abs(torque[i]) > self.config.max_torque_xyz[i]:
                torque[i] = np.sign(torque[i]) * self.config.max_torque_xyz[i]
                torque_saturated[i] = True
                self._torque_saturation_count += 1
                
        self.last_torque_saturated = torque_saturated
        
        return torque

    def compute_control(
        self,
        current_state: DroneState,
        desired_pos: Quantity,
        desired_vel: Quantity,
        desired_acc: Quantity,
        desired_yaw: Union[float, Quantity] = 0.0,
        desired_yaw_rate: Union[float, Quantity] = 0.0,
    ) -> ControlCommand:
        """
        Compute optimized control command using geometric control with PID and feedforward.
        All arguments must be pint.Quantity with correct units.
        """
        # Enforce units at boundaries
        # Fast path: convert pint quantities once; otherwise assume ndarray
        pos = _to_ndarray(current_state.position)
        vel = _to_ndarray(current_state.velocity)
        att = _to_ndarray(current_state.attitude)
        ang_vel = _to_ndarray(current_state.angular_velocity)
        desired_pos_arr = _to_ndarray(desired_pos)
        desired_vel_arr = _to_ndarray(desired_vel)
        desired_acc_arr = _to_ndarray(desired_acc)
        if isinstance(desired_yaw, Quantity):
            desired_yaw = desired_yaw.to('rad').magnitude
        if isinstance(desired_yaw_rate, Quantity):
            desired_yaw_rate = desired_yaw_rate.to('rad/s').magnitude
        current_time = current_state.timestamp
        dt = current_time - self.last_time if self.last_time is not None else 0.001
        self.last_time = current_time
        if dt <= 0 or dt > 0.1:
            return self._get_failsafe_command("Invalid dt")
        try:
            pos_error = desired_pos_arr - pos
            vel_error = desired_vel_arr - vel
            pos_error_magnitude = float(np.linalg.norm(pos_error))
            vel_error_magnitude = float(np.linalg.norm(vel_error))
            self.position_errors.append(pos_error_magnitude)
            self.velocity_errors.append(vel_error_magnitude)
            
            # Compute desired acceleration (PID + feedforward)
            acc_pid = (
                self.config.kp_pos * pos_error +
                self.config.kd_pos * vel_error +
                self.config.ki_pos * self.integral_vel_error
            )
            acc_des = desired_acc_arr + acc_pid
            
            thrust_vector_world = acc_des - self._gravity_vector
            thrust_magnitude = float(np.linalg.norm(thrust_vector_world))
            
            # Store unsaturated thrust for anti-windup
            self.unsaturated_thrust = thrust_magnitude
            
            # Apply thrust limits and detect saturation
            thrust_saturated = False
            min_thrust = self.config.min_thrust * self.config.mass * self.config.gravity
            if thrust_magnitude > self.config.max_thrust:
                thrust_magnitude = self.config.max_thrust
                thrust_saturated = True
            elif thrust_magnitude < min_thrust:
                thrust_magnitude = min_thrust
                thrust_saturated = True
                
            self.last_thrust_saturated = thrust_saturated
            
            # Update integral error with anti-windup protection
            self._update_integral_error(vel_error, float(dt), thrust_saturated, self.last_torque_saturated)
            
            # Validate frame consistency
            # validate_frame_consistent_operation("control_gravity", self._gravity_vector) # This line was removed
            
            thrust_magnitude = self._apply_thrust_limits(thrust_magnitude)
            if self._check_tracking_performance(pos_error_magnitude, vel_error_magnitude):
                return self._get_failsafe_command("Poor tracking performance")
            if thrust_magnitude > 1e-6:
                b3_des = thrust_vector_world / thrust_magnitude
            else:
                b3_des = np.array([0, 0, 1])
            tilt_angle = float(np.arccos(np.clip(b3_des[2], -1, 1)))
            if tilt_angle > self.config.max_tilt_angle:
                scale_factor = np.cos(self.config.max_tilt_angle) / b3_des[2]
                b3_des[:2] *= scale_factor
                b3_des[2] = np.cos(self.config.max_tilt_angle)
                b3_des = b3_des / np.linalg.norm(b3_des)
            thrust_cmd, torque_cmd = self._geometric_attitude_control(
                current_state,
                b3_des,
                float(desired_yaw),
                float(desired_yaw_rate),
                thrust_magnitude,
                float(dt),
            )
            self.control_outputs.append([thrust_cmd, *torque_cmd])
            self.last_valid_thrust = thrust_cmd
            self.failsafe_active = False
            self.failsafe_count = 0
            return ControlCommand(thrust=Q_(thrust_cmd, 'N'), torque=Q_(np.asarray(torque_cmd), 'N*m'))
        except Exception as e:
            self.logger.error(f"❌ Geometric controller error: {e}")
            return self._get_failsafe_command(f"Exception: {e}")

    def _compute_desired_acceleration(
        self, pos_error: np.ndarray, vel_error: np.ndarray, desired_acc: np.ndarray
    ) -> np.ndarray:
        """Compute target linear acceleration.

        acc_des = desired_acc                       (feed-forward)
                  + Kp * pos_error                  (proportional)
                  + Kd * vel_error                  (derivative)
                  + Ki * integral_vel_error         (integral)

        All terms share units of m s⁻².
        """

        acc_pid = (
            self.config.kp_pos * pos_error
            + self.config.kd_pos * vel_error
            + self.config.ki_pos * self.integral_vel_error
        )

        # Remove dimensionally-inconsistent ff_pos; retain desired_acc as proper feed-forward
        return desired_acc + acc_pid

    def _update_integral_error(self, vel_error: np.ndarray, dt: float, thrust_saturated: bool = False, torque_saturated: Optional[np.ndarray] = None):
        """
        Enhanced integral error update with anti-windup protection.
        
        Args:
            vel_error: Velocity error (m/s)
            dt: Time step (s)
            thrust_saturated: Whether thrust is saturated
            torque_saturated: Per-axis torque saturation flags
        """
        if torque_saturated is None:
            torque_saturated = np.array([False, False, False])
            
        # Basic integration
        integral_update = vel_error * dt
        
        # Apply anti-windup based on method
        if self.config.anti_windup_method == "clamping":
            integral_update = self._clamping_anti_windup(integral_update, thrust_saturated, torque_saturated)
        elif self.config.anti_windup_method == "back_calculation":
            integral_update = self._back_calculation_anti_windup(integral_update, thrust_saturated, torque_saturated)
        else:
            self.logger.warning(f"Unknown anti-windup method: {self.config.anti_windup_method}")
            
        # Update integral with anti-windup protection
        self.integral_vel_error += integral_update
        
        # Apply per-axis clamping
        self._clamp_integral_per_axis()
        
    def _clamping_anti_windup(self, integral_update: np.ndarray, thrust_saturated: bool, torque_saturated: np.ndarray) -> np.ndarray:
        """
        Clamping anti-windup: prevent integral accumulation when output is saturated.
        
        This method prevents the integral term from accumulating when the controller
        output is saturated, which would cause windup and poor performance.
        """
        # If thrust is saturated, reduce integral update for all axes
        if thrust_saturated:
            integral_update *= 0.1  # Significantly reduce integral accumulation
            
        # If any torque axis is saturated, reduce integral update for that axis
        for i in range(3):
            if torque_saturated[i]:
                integral_update[i] *= 0.1
                
        return integral_update
        
    def _back_calculation_anti_windup(self, integral_update: np.ndarray, thrust_saturated: bool, torque_saturated: np.ndarray) -> np.ndarray:
        """
        Back-calculation anti-windup: use saturation feedback to unwind integral.
        
        This method uses the difference between unsaturated and saturated outputs
        to provide feedback that unwinds the integral accumulator.
        """
        Kb = self.config.back_calculation_gain
        
        # Calculate saturation feedback for thrust
        if thrust_saturated:
            thrust_feedback = (self.unsaturated_thrust - self.config.max_thrust) * Kb
            # Distribute thrust feedback across all axes (thrust affects all position axes)
            integral_update -= thrust_feedback * np.array([0.33, 0.33, 0.34])
            
        # Calculate saturation feedback for torque (affects attitude, which affects position)
        for i in range(3):
            if torque_saturated[i]:
                torque_feedback = (self.unsaturated_torque[i] - self.config.max_torque_xyz[i]) * Kb
                # Torque affects position through attitude coupling
                integral_update[i] -= torque_feedback * 0.5
                
        return integral_update
        
    def _clamp_integral_per_axis(self):
        """Apply per-axis clamping to prevent integral windup."""
        max_integral_per_axis = self.config.max_integral_per_axis
        
        # Clamp each axis independently
        for i in range(3):
            if abs(self.integral_vel_error[i]) > max_integral_per_axis[i]:
                self.integral_vel_error[i] = np.sign(self.integral_vel_error[i]) * max_integral_per_axis[i]
                
        # Also apply norm-based clamping as backup
        integral_magnitude = np.linalg.norm(self.integral_vel_error)
        if integral_magnitude > self.config.max_integral_pos:
            self.integral_vel_error *= (self.config.max_integral_pos / integral_magnitude)
            
        # Apply decay when approaching limits
        for i in range(3):
            if abs(self.integral_vel_error[i]) > max_integral_per_axis[i] * self.config.saturation_threshold:
                self.integral_vel_error[i] *= self.config.integral_decay_factor

    def _apply_thrust_limits(self, thrust_magnitude: float) -> float:
        max_thrust = self.config.max_thrust
        min_thrust = self.config.min_thrust * self.config.mass * self.config.gravity
        thrust_magnitude = np.clip(thrust_magnitude, min_thrust, max_thrust)
        return thrust_magnitude

    def _check_tracking_performance(self, pos_error: float, vel_error: float) -> bool:
        if (
            pos_error > self.config.tracking_error_threshold
            and vel_error > self.config.velocity_error_threshold
        ):
            self.failsafe_count += 1
        else:
            self.failsafe_count = max(0, self.failsafe_count - 1)
        return self.failsafe_count > 100

    def _geometric_attitude_control(
        self,
        state: DroneState,
        b3_des: np.ndarray,
        yaw_des: float,
        yaw_rate_des: float,
        thrust_mag: float,
        dt: float,
    ) -> Tuple[float, np.ndarray]:
        att = _to_ndarray(state.attitude)
        ang_vel = _to_ndarray(state.angular_velocity)
        R = self._euler_to_rotation_matrix(att)
        
        # Desired rotation matrix with singularity detection
        yaw_vector = np.array([np.cos(yaw_des), np.sin(yaw_des), 0])
        b3_des_normalized = b3_des / np.linalg.norm(b3_des)
        
        # Detect yaw-alignment singularity
        current_yaw = att[2] if len(att) >= 3 else 0.0  # Extract yaw from attitude
        is_singular, cos_angle, fallback_method = self._detect_yaw_singularity(yaw_vector, b3_des_normalized)
        
        if is_singular:
            # Handle singularity using fallback method
            b1_des, b2_des, b3_des_normalized = self._handle_yaw_singularity(
                yaw_vector, b3_des_normalized, current_yaw, fallback_method
            )
        else:
            # Normal case: compute desired frame using cross product
            b1_des = np.cross(yaw_vector, b3_des_normalized)
            b1_des_norm = np.linalg.norm(b1_des)
            if b1_des_norm > 1e-6:
                b1_des = b1_des / b1_des_norm
            else:
                # Fallback for numerical issues
                b1_des = np.array([1, 0, 0])
            b2_des = np.cross(b3_des_normalized, b1_des)
            
        R_des = np.column_stack([b1_des, b2_des, b3_des_normalized])
        eR = 0.5 * self._vee_map(R_des.T @ R - R.T @ R_des)
        omega = ang_vel
        omega_des = np.array([0, 0, yaw_rate_des])
        eOmega = omega - omega_des
        # Full rigid-body attitude control law: τ = -K_R eR - K_Ω eΩ + Ω × (I Ω)
        inertia_diag = self.config.inertia
        inertia_matrix = np.diag(inertia_diag)
        # Use matrix multiplication for proper inertia tensor application
        coriolis = np.cross(omega, inertia_matrix @ omega)
        torque = -self.config.kp_att * eR - self.config.kd_att * eOmega + coriolis

        # Store unsaturated torque for anti-windup
        self.unsaturated_torque = torque.copy()
        
        # Apply torque limits and detect saturation
        torque_saturated = np.zeros(3, dtype=bool)
        for i in range(3):
            if abs(torque[i]) > self.config.max_torque_xyz[i]:
                torque[i] = np.sign(torque[i]) * self.config.max_torque_xyz[i]
                torque_saturated[i] = True
                
        self.last_torque_saturated = torque_saturated
        
        return thrust_mag, torque

    def compute_body_rate_command(
        self,
        current_state: DroneState,
        desired_pos: Quantity,
        desired_vel: Quantity,
        desired_acc: Quantity,
        desired_yaw: Union[float, Quantity] = 0.0,
        desired_yaw_rate: Union[float, Quantity] = 0.0,
    ) -> BodyRateCommand:
        control_cmd = self.compute_control(
            current_state, desired_pos, desired_vel, desired_acc, desired_yaw, desired_yaw_rate
        )
        inertia_matrix = np.diag([0.1, 0.1, 0.2])
        angular_accel = np.linalg.solve(inertia_matrix, control_cmd.torque.magnitude)
        dt = 0.001
        body_rates = _to_ndarray(current_state.angular_velocity) + angular_accel * dt
        normalized_thrust = float(np.clip(float(to_float(control_cmd.thrust)) / self.config.max_thrust, 0.0, 1.0))
        return BodyRateCommand(
            thrust=normalized_thrust,
            body_rates=Q_(body_rates, 'rad/s')
        )

    def compute_control_from_fast_state(
        self,
        fast_state: FastDroneState,
        desired_pos: np.ndarray,
        desired_vel: np.ndarray,
        desired_acc: np.ndarray,
        desired_yaw: float = 0.0,
        desired_yaw_rate: float = 0.0,
        dt: float = 0.001,
    ) -> Tuple[float, np.ndarray]:
        """
        Compute control command using FastDroneState for high-frequency loops.
        
        This method avoids all pint unit conversions by using pre-converted arrays.
        All inputs are assumed to be in base SI units.
        
        Args:
            fast_state: Unit-stripped drone state
            desired_pos: Desired position (m)
            desired_vel: Desired velocity (m/s)
            desired_acc: Desired acceleration (m/s²)
            desired_yaw: Desired yaw angle (rad)
            desired_yaw_rate: Desired yaw rate (rad/s)
            dt: Time step (s)
            
        Returns:
            thrust: Thrust command (N)
            torque: Torque command (N·m)
        """
        return self.compute_control_fast(
            fast_state.position,
            fast_state.velocity,
            fast_state.attitude,
            fast_state.angular_velocity,
            desired_pos,
            desired_vel,
            desired_acc,
            desired_yaw,
            desired_yaw_rate,
            dt,
        )

    def _euler_to_rotation_matrix(self, euler: np.ndarray) -> np.ndarray:
        if len(euler) == 4:
            return self._quaternion_to_rotation_matrix(euler)
        roll, pitch, yaw = euler
        cr, sr = np.cos(roll), np.sin(roll)
        cp, sp = np.cos(pitch), np.sin(pitch)
        cy, sy = np.cos(yaw), np.sin(yaw)
        R = np.array(
            [
                [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                [-sp, cp * sr, cp * cr],
            ]
        )
        return R

    def _quaternion_to_rotation_matrix(self, quat: np.ndarray) -> np.ndarray:
        w, x, y, z = quat
        norm = np.sqrt(w*w + x*x + y*y + z*z)
        if norm > 1e-6:
            w, x, y, z = w/norm, x/norm, y/norm, z/norm
        else:
            return np.eye(3)
        R = np.array([
            [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
            [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
            [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)]
        ])
        return R

    def _vee_map(self, skew_matrix: np.ndarray) -> np.ndarray:
        return np.array([skew_matrix[2, 1], skew_matrix[0, 2], skew_matrix[1, 0]])

    def _get_failsafe_command(self, reason: str = "Unknown") -> ControlCommand:
        # On first failsafe activation, adjust controller for safe hover
        if not getattr(self, 'failsafe_active', False):
            self.logger.warning(f"⚠️  FAILSAFE ACTIVATED: {reason}")
            # Reduce position and attitude gains by half for stability
            self.config.kp_pos = self.config.kp_pos * 0.5
            self.config.kd_pos = self.config.kd_pos * 0.5
            self.config.kp_att = self.config.kp_att * 0.5
            self.config.kd_att = self.config.kd_att * 0.5
            # Reset integral error to prevent windup
            self.integral_vel_error = np.zeros_like(self.integral_vel_error)
            # Increment failsafe count
            self.failsafe_count = getattr(self, 'failsafe_count', 0) + 1
        # Mark failsafe as active
        self.failsafe_active = True
        # Command hover: maintain last valid thrust, zero torque
        return ControlCommand(thrust=Q_(self.last_valid_thrust, 'N'), torque=Q_(np.zeros(3), 'N*m'))

    def get_performance_metrics(self) -> dict:
        metrics = {}
        
        # Add basic metrics if available
        if self.position_errors:
            metrics.update({
                "mean_position_error": np.mean(self.position_errors),
                "max_position_error": np.max(self.position_errors),
                "mean_velocity_error": np.mean(self.velocity_errors),
                "failsafe_activations": self.failsafe_count,
                "total_samples": len(self.position_errors),
            })
        
        # Add anti-windup metrics
        if hasattr(self, 'last_thrust_saturated') and hasattr(self, 'last_torque_saturated'):
            metrics.update({
                "anti_windup_method": self.config.anti_windup_method,
                "integral_magnitude": float(np.linalg.norm(self.integral_vel_error)),
                "integral_per_axis": self.integral_vel_error.tolist(),
                "thrust_saturation_count": getattr(self, '_thrust_saturation_count', 0),
                "torque_saturation_count": getattr(self, '_torque_saturation_count', 0),
            })
            
        # Add yaw singularity metrics (always available)
        metrics.update({
            "yaw_singularity_threshold": self.config.yaw_singularity_threshold,
            "yaw_singularity_fallback_method": self.config.yaw_singularity_fallback_method,
            "yaw_singularity_warning_threshold": self.config.yaw_singularity_warning_threshold,
        })
            
        return metrics

    def reset(self):
        self.last_time = None
        self.integral_vel_error = np.zeros(3)
        self.position_errors = []
        self.velocity_errors = []
        self.control_outputs = []
        self.failsafe_active = False
        self.failsafe_count = 0
        self.last_valid_thrust = self.config.mass * self.config.gravity
        
        # Reset anti-windup state
        self.last_thrust_saturated = False
        self.last_torque_saturated = np.array([False, False, False])
        self.unsaturated_thrust = 0.0
        self.unsaturated_torque = np.zeros(3)
        self._thrust_saturation_count = 0
        self._torque_saturation_count = 0
        
        self.logger.info("🔄 Controller reset completed")

    def compute_control_from_trajectory(self, *args, **kwargs):
        """Legacy API stub: alias for compute_control. Returns empty command dict."""
        return {}

def _to_ndarray(val):
    from pint import Quantity  # local import to avoid global cost
    if isinstance(val, Quantity):
        return val.to_base_units().magnitude
    return np.asarray(val)
