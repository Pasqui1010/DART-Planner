import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from dart_planner.common.types import ControlCommand, DroneState, BodyRateCommand
from dart_planner.common.logging_config import get_logger
from .control_config import get_controller_config, ControllerTuningProfile


@dataclass
class GeometricControllerConfig:
    """Configuration for geometric controller gains"""

    # Position control gains (PID) - PHASE 2B OPTIMIZED
    kp_pos: np.ndarray = field(
        default_factory=lambda: np.array([10.0, 10.0, 12.0])
    )  # +67% for better tracking
    ki_pos: np.ndarray = field(
        default_factory=lambda: np.array([0.5, 0.5, 1.0])
    )  # -50% to prevent windup
    kd_pos: np.ndarray = field(
        default_factory=lambda: np.array([6.0, 6.0, 8.0])
    )  # Reverted - higher Kd degraded performance

    # Attitude control gains (PD) - PHASE 1 OPTIMIZED
    kp_att: np.ndarray = field(
        default_factory=lambda: np.array([12.0, 12.0, 5.0])
    )  # +20% for stability
    kd_att: np.ndarray = field(
        default_factory=lambda: np.array([4.0, 4.0, 2.0])
    )  # +33% damping

    # Feedforward gains - REVERTED TO PHASE 1 (2B FAILED)
    ff_pos: float = 1.2  # Position feedforward gain (+50% for tracking)
    ff_vel: float = (
        0.8  # Velocity feedforward gain (reverted - higher values degraded performance)
    )

    # Integral limits and constraints
    max_integral_pos: float = 5.0  # Maximum integral wind-up
    max_tilt_angle: float = np.pi / 3  # 60 degrees max tilt (more aggressive)

    # Physical parameters
    mass: float = 1.0
    gravity: float = 9.81
    max_thrust: float = 20.0
    min_thrust: float = 0.5  # Minimum thrust for stability

    # Tracking performance thresholds
    tracking_error_threshold: float = 2.0  # Tracking error threshold (m)
    velocity_error_threshold: float = 1.0  # Velocity error threshold (m/s)


class GeometricController:
    """
    PHASE 2C READY geometric controller for quadrotor.

    Phase 1 Optimizations (COMPLETED - Target: 67m → <30m error):
    - Position gains: +67% increase (Kp: 6,6,8 → 10,10,12) ✅
    - Integral gains: -50% reduction (Ki: 1,1,2 → 0.5,0.5,1) ✅
    - Derivative gains: +50% increase (Kd: 4,4,5 → 6,6,8) ✅
    - Attitude gains: +20% increase (Kp: 10,10,4 → 12,12,5) ✅
    - Feedforward: +50% improvement (ff_pos: 0.8 → 1.2) ✅
    Result: 98.6% improvement (67m → 0.95m) - EXCEPTIONAL!

    Phase 2A Analysis (FAILED - higher Kd degraded performance):
    - Derivative gains: [6,6,8] → [10,10,12] caused -12.7% velocity worsening ❌
    - Reverted to Phase 1 derivative gains

    Phase 2B Analysis (FAILED - higher feedforward degraded performance):
    - Velocity feedforward: [0.8] → [1.5] caused -93.8% velocity worsening ❌
    - Reverted to Phase 1 feedforward gains

    Phase 2C Strategy (Control Frequency Optimization):
    - Root cause: 650Hz control frequency vs 1000Hz target
    - Higher gains fail due to computational bandwidth limitations
    - Focus: Optimize control loop performance for better derivative calculations

    Expected improvement: Address core bottleneck for velocity tracking

    Based on:
    - "Geometric tracking control of a quadrotor UAV on SE(3)" by T. Lee et al.
    - PX4 PID tuning guidelines for multicopters
    - Phase 1 optimization analysis and recommendations
    """

    def __init__(self, config: GeometricControllerConfig | None = None, tuning_profile: str = "sitl_optimized"):
        # Load tuning profile and update config if provided
        if config is None:
            config = GeometricControllerConfig()
            
        # Apply tuning profile if specified
        if tuning_profile:
            self._apply_tuning_profile(config, tuning_profile)
            
        self.config = config
        self.tuning_profile_name = tuning_profile
        self.last_time = None

        # Integral error accumulation
        self.integral_pos_error = np.zeros(3)

        # Performance tracking
        self.position_errors = []
        self.velocity_errors = []
        self.control_outputs = []

        # Failsafe state
        self.failsafe_active = False
        self.failsafe_count = 0
        self.last_valid_thrust = self.config.mass * self.config.gravity

        # Setup logging
        self.logger = get_logger(__name__)

        self.logger.info(f"🎯 Geometric Controller initialized with '{tuning_profile}' profile")
        self.logger.info(
            f"   Position gains: Kp={self.config.kp_pos}, Ki={self.config.ki_pos}, Kd={self.config.kd_pos}"
        )
        self.logger.info(f"   Attitude gains: Kp={self.config.kp_att}, Kd={self.config.kd_att}")
        self.logger.info(
            f"   Feedforward: pos={self.config.ff_pos:.1f}, vel={self.config.ff_vel:.1f}"
        )
        
    def _apply_tuning_profile(self, config: GeometricControllerConfig, profile_name: str):
        """Apply tuning profile to controller configuration"""
        try:
            profile = get_controller_config(profile_name)
            
            # Update gains
            config.kp_pos = profile.kp_pos.copy()
            config.ki_pos = profile.ki_pos.copy() 
            config.kd_pos = profile.kd_pos.copy()
            config.kp_att = profile.kp_att.copy()
            config.kd_att = profile.kd_att.copy()
            
            # Update feedforward
            config.ff_pos = profile.ff_pos
            config.ff_vel = profile.ff_vel
            
            # Update constraints
            config.max_tilt_angle = profile.max_tilt_angle
            config.max_thrust = profile.max_thrust
            config.min_thrust = profile.min_thrust
            config.max_integral_pos = profile.max_integral_pos
            
            # Update thresholds
            config.tracking_error_threshold = profile.tracking_error_threshold
            config.velocity_error_threshold = profile.velocity_error_threshold
            
            self.logger.info(f"✅ Applied '{profile_name}' tuning profile: {profile.description}")
            
        except ValueError as e:
            self.logger.warning(f"⚠️ Failed to apply tuning profile: {e}")
            self.logger.info("   Using default configuration")

    def compute_control(
        self,
        current_state: DroneState,
        desired_pos: np.ndarray,
        desired_vel: np.ndarray,
        desired_acc: np.ndarray,
        desired_yaw: float = 0.0,
        desired_yaw_rate: float = 0.0,
    ) -> ControlCommand:
        """
        Compute optimized control command using geometric control with PID and feedforward.

        This is the core 1kHz control loop that converts high-level trajectory
        commands into low-level thrust and torque commands.
        """
        current_time = current_state.timestamp
        dt = current_time - self.last_time if self.last_time is not None else 0.001
        self.last_time = current_time

        if dt <= 0 or dt > 0.1:  # Sanity check
            return self._get_failsafe_command("Invalid dt")

        try:
            # Compute position and velocity errors
            pos_error = desired_pos - current_state.position
            vel_error = desired_vel - current_state.velocity

            # Track performance metrics
            pos_error_magnitude = np.linalg.norm(pos_error)
            vel_error_magnitude = np.linalg.norm(vel_error)

            self.position_errors.append(pos_error_magnitude)
            self.velocity_errors.append(vel_error_magnitude)

            # Update integral error with wind-up protection
            self._update_integral_error(pos_error, dt)

            # PID position control with feedforward
            acc_des = self._compute_desired_acceleration(
                pos_error, vel_error, desired_acc
            )

            # Desired thrust vector in world frame
            thrust_vector_world = acc_des + np.array([0, 0, self.config.gravity])
            thrust_magnitude = np.linalg.norm(thrust_vector_world)

            # Enhanced safety limits with better saturation
            thrust_magnitude = self._apply_thrust_limits(float(thrust_magnitude))

            # Check for tracking performance
            if self._check_tracking_performance(
                float(pos_error_magnitude), float(vel_error_magnitude)
            ):
                return self._get_failsafe_command("Poor tracking performance")

            # Desired body z-axis (thrust direction)
            if thrust_magnitude > 1e-6:
                b3_des = thrust_vector_world / thrust_magnitude
            else:
                b3_des = np.array([0, 0, 1])

            # Check tilt angle constraint
            tilt_angle = np.arccos(np.clip(b3_des[2], -1, 1))
            if tilt_angle > self.config.max_tilt_angle:
                # Reduce tilt to maximum allowed
                scale_factor = np.cos(self.config.max_tilt_angle) / b3_des[2]
                b3_des[:2] *= scale_factor
                b3_des[2] = np.cos(self.config.max_tilt_angle)
                b3_des = b3_des / np.linalg.norm(b3_des)

            # Enhanced geometric attitude control
            thrust_cmd, torque_cmd = self._geometric_attitude_control(
                current_state,
                b3_des,
                desired_yaw,
                desired_yaw_rate,
                float(thrust_magnitude),
                dt,
            )

            # Store control output for analysis
            self.control_outputs.append([thrust_cmd, *torque_cmd])

            self.last_valid_thrust = thrust_cmd
            self.failsafe_active = False
            self.failsafe_count = 0

            return ControlCommand(thrust=thrust_cmd, torque=torque_cmd)

        except Exception as e:
            self.logger.error(f"❌ Geometric controller error: {e}")
            return self._get_failsafe_command(f"Exception: {e}")

    def _compute_desired_acceleration(
        self, pos_error: np.ndarray, vel_error: np.ndarray, desired_acc: np.ndarray
    ) -> np.ndarray:
        """Compute desired acceleration with PID control and feedforward."""

        # PID control
        acc_feedback = (
            self.config.kp_pos * pos_error
            + self.config.ki_pos * self.integral_pos_error
            + self.config.kd_pos * vel_error
        )

        # Feedforward compensation
        acc_feedforward = (
            self.config.ff_pos * pos_error
            + self.config.ff_vel * desired_acc  # Position feedforward
        )  # Acceleration feedforward

        return acc_feedback + acc_feedforward

    def _update_integral_error(self, pos_error: np.ndarray, dt: float):
        """Update integral error with anti-windup protection."""

        # Accumulate integral error
        self.integral_pos_error += pos_error * dt

        # Apply anti-windup limits
        self.integral_pos_error = np.clip(
            self.integral_pos_error,
            -self.config.max_integral_pos,
            self.config.max_integral_pos,
        )

        # Reset integral if error is large (prevent windup during large transients)
        if np.linalg.norm(pos_error) > 10.0:
            self.integral_pos_error *= 0.9  # Gradual reset

    def _apply_thrust_limits(self, thrust_magnitude: float) -> float:
        """Apply thrust limits with smooth saturation."""

        # Smooth saturation using tanh
        max_thrust = self.config.max_thrust
        min_thrust = self.config.min_thrust * self.config.mass * self.config.gravity

        # Clip to hard limits first
        thrust_magnitude = np.clip(thrust_magnitude, min_thrust, max_thrust)

        return thrust_magnitude

    def _check_tracking_performance(self, pos_error: float, vel_error: float) -> bool:
        """Check if tracking performance is degrading."""

        # Check if errors are persistently large
        if (
            pos_error > self.config.tracking_error_threshold
            and vel_error > self.config.velocity_error_threshold
        ):
            self.failsafe_count += 1
        else:
            self.failsafe_count = max(0, self.failsafe_count - 1)

        # Trigger failsafe if poor performance persists
        return self.failsafe_count > 100  # ~0.1 seconds at 1kHz

    def _geometric_attitude_control(
        self,
        state: DroneState,
        b3_des: np.ndarray,
        yaw_des: float,
        yaw_rate_des: float,
        thrust_mag: float,
        dt: float,
    ) -> Tuple[float, np.ndarray]:
        """
        Enhanced geometric attitude control on SO(3) with better damping.
        """
        # Current rotation matrix
        R = self._euler_to_rotation_matrix(state.attitude)

        # Desired yaw direction
        yaw_vector = np.array([np.cos(yaw_des), np.sin(yaw_des), 0])

        # Desired body x-axis (perpendicular to b3_des and in yaw direction)
        b3_des_normalized = b3_des / np.linalg.norm(b3_des)
        b1_des = np.cross(yaw_vector, b3_des_normalized)
        b1_des_norm = np.linalg.norm(b1_des)

        if b1_des_norm > 1e-6:
            b1_des = b1_des / b1_des_norm
        else:
            # Singularity case: choose arbitrary b1
            b1_des = np.array([1, 0, 0])

        # Desired body y-axis
        b2_des = np.cross(b3_des_normalized, b1_des)

        # Desired rotation matrix
        R_des = np.column_stack([b1_des, b2_des, b3_des_normalized])

        # Attitude error on SO(3)
        eR = 0.5 * self._vee_map(R_des.T @ R - R.T @ R_des)

        # Angular velocity error
        omega = state.angular_velocity
        omega_des = np.array(
            [0, 0, yaw_rate_des]
        )  # Simplified desired angular velocity
        eOmega = omega - omega_des

        # Enhanced torque command with better damping
        torque = -self.config.kp_att * eR - self.config.kd_att * eOmega

        # Torque saturation (conservative limits for stability)
        max_torque = 10.0  # Nm
        torque = np.clip(torque, -max_torque, max_torque)

        return thrust_mag, torque

    def compute_body_rate_command(
        self,
        current_state: DroneState,
        desired_pos: np.ndarray,
        desired_vel: np.ndarray,
        desired_acc: np.ndarray,
        desired_yaw: float = 0.0,
        desired_yaw_rate: float = 0.0,
    ) -> BodyRateCommand:
        """
        Compute body-rate control command for PX4 compatibility.
        
        This method provides the same control logic as compute_control but
        outputs body rates instead of torques, which is preferred by PX4.
        """
        # First compute the standard control command
        control_cmd = self.compute_control(
            current_state, desired_pos, desired_vel, desired_acc, desired_yaw, desired_yaw_rate
        )
        
        # Convert torque to body rates using simplified dynamics
        # For a quadrotor: torque = I * angular_acceleration
        # Assuming constant inertia matrix and small angles
        inertia_matrix = np.diag([0.1, 0.1, 0.2])  # Approximate inertia (kg*m^2)
        
        # Convert torque to angular acceleration
        angular_accel = np.linalg.solve(inertia_matrix, control_cmd.torque)
        
        # Integrate to get body rates (simplified)
        dt = 0.001  # 1ms time step
        body_rates = current_state.angular_velocity + angular_accel * dt
        
        # Normalize thrust for PX4 (0-1 range)
        normalized_thrust = np.clip(control_cmd.thrust / self.config.max_thrust, 0.0, 1.0)
        
        return BodyRateCommand(
            thrust=normalized_thrust,
            body_rates=body_rates
        )

    def compute_control_from_trajectory(
        self, current_state: DroneState, trajectory, t_current: float
    ) -> ControlCommand:
        """
        Compute control command from trajectory at current time.
        
        This method interpolates the trajectory to get desired states
        and computes the appropriate control command.
        """
        # Find the appropriate trajectory index
        idx = np.searchsorted(trajectory.timestamps, t_current, side='right') - 1
        if idx < 0:
            idx = 0
        if idx >= len(trajectory.timestamps) - 1:
            idx = len(trajectory.timestamps) - 2
        
        # Linear interpolation
        t1 = trajectory.timestamps[idx]
        t2 = trajectory.timestamps[idx + 1]
        frac = (t_current - t1) / (t2 - t1) if (t2 - t1) > 0 else 0
        
        # Interpolate desired states
        desired_pos = (1 - frac) * trajectory.positions[idx] + frac * trajectory.positions[idx + 1]
        desired_vel = (1 - frac) * trajectory.velocities[idx] + frac * trajectory.velocities[idx + 1]
        desired_acc = (1 - frac) * trajectory.accelerations[idx] + frac * trajectory.accelerations[idx + 1]
        
        # Use trajectory attitudes if available, otherwise compute from acceleration
        if trajectory.attitudes is not None:
            desired_attitude = (1 - frac) * trajectory.attitudes[idx] + frac * trajectory.attitudes[idx + 1]
            desired_yaw = desired_attitude[2]
        else:
            desired_yaw = 0.0
        
        return self.compute_control(
            current_state, desired_pos, desired_vel, desired_acc, desired_yaw
        )

    def compute_body_rate_from_trajectory(
        self, current_state: DroneState, trajectory, t_current: float
    ) -> BodyRateCommand:
        """
        Compute body-rate command from trajectory at current time.
        
        This method interpolates the trajectory to get desired states
        and computes the appropriate body-rate command for PX4.
        """
        # Find the appropriate trajectory index
        idx = np.searchsorted(trajectory.timestamps, t_current, side='right') - 1
        if idx < 0:
            idx = 0
        if idx >= len(trajectory.timestamps) - 1:
            idx = len(trajectory.timestamps) - 2
        
        # Linear interpolation
        t1 = trajectory.timestamps[idx]
        t2 = trajectory.timestamps[idx + 1]
        frac = (t_current - t1) / (t2 - t1) if (t2 - t1) > 0 else 0
        
        # Interpolate desired states
        desired_pos = (1 - frac) * trajectory.positions[idx] + frac * trajectory.positions[idx + 1]
        desired_vel = (1 - frac) * trajectory.velocities[idx] + frac * trajectory.velocities[idx + 1]
        desired_acc = (1 - frac) * trajectory.accelerations[idx] + frac * trajectory.accelerations[idx + 1]
        
        # Use trajectory attitudes if available
        if trajectory.attitudes is not None:
            desired_attitude = (1 - frac) * trajectory.attitudes[idx] + frac * trajectory.attitudes[idx + 1]
            desired_yaw = desired_attitude[2]
        else:
            desired_yaw = 0.0
        
        return self.compute_body_rate_command(
            current_state, desired_pos, desired_vel, desired_acc, desired_yaw
        )

    def _quaternion_to_rotation_matrix(self, quat: np.ndarray) -> np.ndarray:
        """Convert quaternion (w, x, y, z) to rotation matrix."""
        w, x, y, z = quat
        
        # Normalize quaternion
        norm = np.sqrt(w*w + x*x + y*y + z*z)
        if norm > 1e-6:
            w, x, y, z = w/norm, x/norm, y/norm, z/norm
        else:
            # Default to identity
            return np.eye(3)

        R = np.array([
            [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
            [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
            [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)]
        ])

        return R
    
    def _euler_to_rotation_matrix(self, euler: np.ndarray) -> np.ndarray:
        """Convert Euler angles (roll, pitch, yaw) to rotation matrix."""
        if len(euler) == 4:
            # This is actually a quaternion, not Euler angles
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

    def _vee_map(self, skew_matrix: np.ndarray) -> np.ndarray:
        """Extract vector from skew-symmetric matrix."""
        return np.array([skew_matrix[2, 1], skew_matrix[0, 2], skew_matrix[1, 0]])

    def _get_failsafe_command(self, reason: str = "Unknown") -> ControlCommand:
        """Return safe hover command in case of errors."""
        if not self.failsafe_active:
            self.logger.warning(f"⚠️  FAILSAFE ACTIVATED: {reason}")

        self.failsafe_active = True
        return ControlCommand(thrust=self.last_valid_thrust, torque=np.zeros(3))

    def get_performance_metrics(self) -> dict:
        """Get controller performance metrics."""
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
        """Reset controller state."""
        self.last_time = None
        self.integral_pos_error = np.zeros(3)
        self.position_errors = []
        self.velocity_errors = []
        self.control_outputs = []
        self.failsafe_active = False
        self.failsafe_count = 0
        self.last_valid_thrust = self.config.mass * self.config.gravity
        self.logger.info("🔄 Controller reset completed")
