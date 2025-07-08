from __future__ import annotations

"""Pydantic schema for validating motor mixing configuration loaded from YAML.

This schema is intended for early-fail validation of user-supplied parameters
before constructing a :class:`~dart_planner.hardware.motor_mixer.MotorMixingConfig`.
It mirrors the dataclass fields and adds additional semantic checks.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError, validator

from .motor_mixer import QuadrotorLayout


class MotorMixingModel(BaseModel):
    """Schema for the *motor_mixing* section in ``hardware.yaml``."""

    layout: QuadrotorLayout = Field(
        description="Quadrotor frame layout: 'x', 'plus', or 'custom'",
        default=QuadrotorLayout.X_CONFIGURATION,
    )
    arm_length: float = Field(
        default=0.15,
        gt=0.0,
        description="Distance from centre of gravity to motor (m)",
    )

    motor_positions: List[List[float]] = Field(
        description="List of 4 [x,y,z] positions for motors (m)",
    )
    motor_directions: List[int] = Field(
        description="Spin directions: 1 for CCW, -1 for CW",
    )

    pwm_min: float = Field(0.0, ge=0.0, le=1.0)
    pwm_max: float = Field(1.0, ge=0.0, le=1.0)
    pwm_idle: float = Field(0.1, ge=0.0, le=1.0)
    pwm_scaling_factor: float = Field(2000.0, gt=0.0)

    thrust_coefficient: float = Field(1.0e-5, gt=0.0)
    torque_coefficient: float = Field(1.0e-7, gt=0.0)

    # Optional custom 4×4 matrix
    mixing_matrix: Optional[List[List[float]]] = None

    @validator("pwm_idle")
    def idle_between_limits(cls, v, values):  # noqa: N805
        pwm_min = values.get("pwm_min", 0.0)
        pwm_max = values.get("pwm_max", 1.0)
        if not pwm_min <= v <= pwm_max:
            raise ValueError("pwm_idle must lie between pwm_min and pwm_max")
        return v

    @validator("pwm_max")
    def min_less_than_max(cls, v, values):  # noqa: N805
        pwm_min = values.get("pwm_min", 0.0)
        if v <= pwm_min:
            raise ValueError("pwm_max must be greater than pwm_min")
        return v

    @validator("motor_directions")
    def directions_only_one_neg_one(cls, v):  # noqa: N805
        if any(direction not in (-1, 1) for direction in v):
            raise ValueError("motor_directions must be ±1 values")
        return v

    @validator("motor_positions")
    def motor_positions_shape(cls, v):  # noqa: N805
        if len(v) != 4 or any(len(row) != 3 for row in v):
            raise ValueError("motor_positions must be 4 items of length 3")
        return v

    @validator("mixing_matrix")
    def mixing_matrix_shape(cls, v):  # noqa: N805
        if v is not None:
            if len(v) != 4 or any(len(row) != 4 for row in v):
                raise ValueError("mixing_matrix must be 4x4 list")
        return v


__all__ = ["MotorMixingModel", "ValidationError"] 