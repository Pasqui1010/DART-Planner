import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

import numpy as np
from pint import Quantity

from dart_planner.common.types import ControlCommand, DroneState, BodyRateCommand, FastDroneState
from dart_planner.common.logging_config import get_logger
from dart_planner.common.units import Q_, to_float
from .control_config import get_controller_config, ControllerTuningProfile
from dart_planner.common.vehicle_params import get_params, get_control_constants
from dart_planner.common.coordinate_frames import get_coordinate_frame_manager, validate_frame_consistent_operation

@dataclass
class GeometricControllerConfig:
    """Configuration for geometric controller gains (units-aware)"""
    # Position control gains (PID)
    kp_pos: np.ndarray = field(default_factory=lambda: np.array([10.0, 10.0, 12.0]))
    ki_pos: np.ndarray = field(default_factory=lambda: np.array([0.5, 0.5, 1.0]))
    kd_pos: np.ndarray = field(default_factory=lambda: np.array([6.0, 6.0, 8.0]))
    # Attitude control gains (PD)
    kp_att: np.ndarray = field(default_factory=lambda: np.array([12.0, 12.0, 5.0]))
    kd_att: np.ndarray = field(default_factory=lambda: np.array([4.0, 4.0, 2.0]))
    # Physical inertia diagonal (kg·m²)
    inertia: np.ndarray = field(default_factory=lambda: np.array(get_params().inertia))
    # Per-axis torque limits (N·m)
    max_torque_xyz: np.ndarray = field(default_factory=lambda: np.array([5.0, 5.0, 2.5]))
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
        
        # Update integral error
        self.integral_vel_error += vel_error * dt
        integral_magnitude = np.linalg.norm(self.integral_vel_error)
        if integral_magnitude > self.config.max_integral_pos:
            self.integral_vel_error *= (self.config.max_integral_pos / integral_magnitude)
        
        # Compute desired acceleration (PID + feedforward)
        acc_pid = (
            self.config.kp_pos * pos_error +
            self.config.kd_pos * vel_error +
            self.config.ki_pos * self.integral_vel_error
        )
        acc_des = desired_acc + acc_pid
        
        # Compute thrust vector in world frame
        thrust_vector_world = acc_des + self._fast_gravity_vector
        thrust_magnitude = np.linalg.norm(thrust_vector_world)
        
        # Validate frame consistency
        validate_frame_consistent_operation("fast_control_gravity", self._fast_gravity_vector)
        
        # Apply thrust limits
        thrust_magnitude = np.clip(thrust_magnitude, self._fast_min_thrust, self.config.max_thrust)
        
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
        
        # Desired rotation matrix
        yaw_vector = np.array([np.cos(yaw_des), np.sin(yaw_des), 0])
        b3_des_normalized = b3_des / np.linalg.norm(b3_des)
        
        b1_des = np.cross(yaw_vector, b3_des_normalized)
        b1_des_norm = np.linalg.norm(b1_des)
        if b1_des_norm > 1e-6:
            b1_des = b1_des / b1_des_norm
        else:
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
        
        # Apply torque limits
        torque = np.clip(torque, -self.config.max_torque_xyz, self.config.max_torque_xyz)
        
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
            self._update_integral_error(vel_error, float(dt))
            acc_des = self._compute_desired_acceleration(pos_error, vel_error, desired_acc_arr)
            thrust_vector_world = acc_des + self._gravity_vector
            thrust_magnitude = float(np.linalg.norm(thrust_vector_world))
            
            # Validate frame consistency
            validate_frame_consistent_operation("control_gravity", self._gravity_vector)
            
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

    def _update_integral_error(self, vel_error: np.ndarray, dt: float):
        """Integrate velocity error (m s⁻¹) over time ⇒ metres."""
        self.integral_vel_error += vel_error * dt
        max_integral = self.config.max_integral_pos
        mag = float(np.linalg.norm(self.integral_vel_error))
        if mag > max_integral:
            self.integral_vel_error *= (max_integral / mag)
        # Anti-windup: if integral grows despite large error, apply decay
        if mag > max_integral * 0.8:
            self.integral_vel_error *= 0.99

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
        yaw_vector = np.array([np.cos(yaw_des), np.sin(yaw_des), 0])
        b3_des_normalized = b3_des / np.linalg.norm(b3_des)
        b1_des = np.cross(yaw_vector, b3_des_normalized)
        b1_des_norm = np.linalg.norm(b1_des)
        if b1_des_norm > 1e-6:
            b1_des = b1_des / b1_des_norm
        else:
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

        # Clamp torque per-axis using limits from config
        torque_limits = self.config.max_torque_xyz
        torque = np.clip(torque, -torque_limits, torque_limits)
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
        if not self.failsafe_active:
            self.logger.warning(f"⚠️  FAILSAFE ACTIVATED: {reason}")
        self.failsafe_active = True
        return ControlCommand(thrust=Q_(self.last_valid_thrust, 'N'), torque=Q_(np.zeros(3), 'N*m'))

    def get_performance_metrics(self) -> dict:
        if not self.position_errors:
            return {}
        return {
            "mean_position_error": np.mean(self.position_errors),
            "max_position_error": np.max(self.position_errors),
            "mean_velocity_error": np.mean(self.velocity_errors),
            "failsafe_activations": self.failsafe_count,
            "total_samples": len(self.position_errors),
        }

    def reset(self):
        self.last_time = None
        self.integral_vel_error = np.zeros(3)
        self.position_errors = []
        self.velocity_errors = []
        self.control_outputs = []
        self.failsafe_active = False
        self.failsafe_count = 0
        self.last_valid_thrust = self.config.mass * self.config.gravity
        self.logger.info("🔄 Controller reset completed")

def _to_ndarray(val):
    from pint import Quantity  # local import to avoid global cost
    if isinstance(val, Quantity):
        return val.to_base_units().magnitude
    return np.asarray(val)
