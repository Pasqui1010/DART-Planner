"""Additional safety tests for the motor mixing module."""

import numpy as np
import pytest

from dart_planner.hardware.motor_mixer import MotorMixer, MotorMixingConfig, QuadrotorLayout
from dart_planner.hardware.motor_mixing_schema import MotorMixingModel, ValidationError


class TestMotorMixingSafety:
    """Safety-centric tests covering runtime guards and schema validation."""

    def test_non_finite_detection(self):
        """Mixer should raise if commanded thrust/torque produce NaN values."""
        mixer = MotorMixer(MotorMixingConfig())

        # Passing NaN thrust should lead to non-finite motor_thrusts and raise RuntimeError
        with pytest.raises(RuntimeError, match="Non-finite"):
            mixer.mix_commands(float("nan"), np.zeros(3))

    def test_config_schema_typo(self):
        """Schema should reject unknown/misspelled fields."""
        bad_config = {
            "layout": "x",
            "motor_directions": [1, -1, 1, -1],
            "motor_positions": [[0.1, -0.1, 0.0]] * 4,
            # Intentional typo: pwmIdel instead of pwm_idle
            "pwmIdel": 0.1,
        }

        with pytest.raises(ValidationError):
            MotorMixingModel.model_validate(bad_config)  # type: ignore[arg-type] 