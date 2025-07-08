"""
Unit tests for motor model interface and quadratic implementation.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from dart_planner.hardware.motor_model import (
    MotorModel, QuadraticMotorModel, MotorParameters, MotorType,
    BenchTestData, fit_quadratic_motor_model, create_default_motor_model
)


class TestMotorParameters:
    """Test MotorParameters dataclass."""
    
    def test_valid_parameters(self):
        """Test valid motor parameters."""
        params = MotorParameters(
            motor_id=0,
            thrust_a=2.5,
            thrust_b=1.2,
            thrust_c=0.1,
            torque_coefficient=1e-7,
            rpm_coefficient=8000,
            rpm_offset=500,
            direction=1
        )
        
        assert params.motor_id == 0
        assert params.thrust_a == 2.5
        assert params.direction == 1
    
    def test_invalid_thrust_a(self):
        """Test validation of negative thrust_a."""
        with pytest.raises(ValueError, match="thrust_a must be non-negative"):
            MotorParameters(motor_id=0, thrust_a=-1.0)
    
    def test_invalid_torque_coefficient(self):
        """Test validation of negative torque coefficient."""
        with pytest.raises(ValueError, match="torque_coefficient must be non-negative"):
            MotorParameters(motor_id=0, torque_coefficient=-1e-7)
    
    def test_invalid_rpm_coefficient(self):
        """Test validation of non-positive RPM coefficient."""
        with pytest.raises(ValueError, match="rpm_coefficient must be positive"):
            MotorParameters(motor_id=0, rpm_coefficient=0.0)
    
    def test_invalid_pwm_limits(self):
        """Test validation of PWM limits."""
        with pytest.raises(ValueError, match="pwm_min must be less than pwm_max"):
            MotorParameters(motor_id=0, pwm_min=1.0, pwm_max=0.5)
    
    def test_invalid_direction(self):
        """Test validation of motor direction."""
        with pytest.raises(ValueError, match="direction must be ±1"):
            MotorParameters(motor_id=0, direction=0)


class TestBenchTestData:
    """Test BenchTestData validation."""
    
    def test_valid_data(self):
        """Test valid bench test data."""
        data = BenchTestData(
            motor_id=0,
            pwm_values=[0.1, 0.3, 0.5, 0.7, 0.9],
            thrust_measurements=[0.5, 1.2, 2.1, 3.2, 4.5],
            rpm_measurements=[1000.0, 2500.0, 4000.0, 5500.0, 7000.0]
        )
        
        errors = data.validate()
        assert len(errors) == 0
    
    def test_insufficient_data_points(self):
        """Test validation with insufficient data points."""
        data = BenchTestData(
            motor_id=0,
            pwm_values=[0.1, 0.3],
            thrust_measurements=[0.5, 1.2],
            rpm_measurements=[1000.0, 2500.0]
        )
        
        errors = data.validate()
        assert any("Need at least 3 data points" in error for error in errors)
    
    def test_mismatched_lengths(self):
        """Test validation with mismatched data lengths."""
        data = BenchTestData(
            motor_id=0,
            pwm_values=[0.1, 0.3, 0.5],
            thrust_measurements=[0.5, 1.2],  # Missing one
            rpm_measurements=[1000, 2500, 4000]
        )
        
        errors = data.validate()
        assert any("PWM and thrust data lengths don't match" in error for error in errors)
    
    def test_non_monotonic_pwm(self):
        """Test validation with non-monotonic PWM values."""
        data = BenchTestData(
            motor_id=0,
            pwm_values=[0.1, 0.5, 0.3, 0.7, 0.9],  # Not monotonic
            thrust_measurements=[0.5, 1.2, 2.1, 3.2, 4.5],
            rpm_measurements=[1000.0, 2500.0, 4000.0, 5500.0, 7000.0]
        )
        
        errors = data.validate()
        assert any("PWM values must be monotonically increasing" in error for error in errors)
    
    def test_negative_thrust(self):
        """Test validation with negative thrust measurements."""
        data = BenchTestData(
            motor_id=0,
            pwm_values=[0.1, 0.3, 0.5],
            thrust_measurements=[0.5, -0.1, 2.1],  # Negative value
            rpm_measurements=[1000, 2500, 4000]
        )
        
        errors = data.validate()
        assert any("Thrust measurements must be non-negative" in error for error in errors)


class TestQuadraticMotorModel:
    """Test QuadraticMotorModel implementation."""
    
    @pytest.fixture
    def motor_params(self):
        """Create test motor parameters."""
        return {
            0: MotorParameters(
                motor_id=0,
                thrust_a=2.5,
                thrust_b=1.2,
                thrust_c=0.1,
                torque_coefficient=1e-7,
                rpm_coefficient=8000,
                rpm_offset=500,
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
            )
        }
    
    @pytest.fixture
    def motor_model(self, motor_params):
        """Create test motor model."""
        return QuadraticMotorModel(motor_params)
    
    def test_thrust_from_pwm(self, motor_model):
        """Test thrust calculation from PWM."""
        # Test at PWM = 0.5
        thrust = motor_model.thrust_from_pwm(0.5, motor_id=0)
        expected = 2.5 * 0.5**2 + 1.2 * 0.5 + 0.1
        assert np.isclose(thrust, expected, rtol=1e-6)
        
        # Test at PWM = 0.0
        thrust = motor_model.thrust_from_pwm(0.0, motor_id=0)
        expected = 0.1  # Just the offset
        assert np.isclose(thrust, expected, rtol=1e-6)
        
        # Test negative thrust handling
        thrust = motor_model.thrust_from_pwm(-0.1, motor_id=0)
        assert thrust >= 0.0
    
    def test_torque_from_pwm(self, motor_model):
        """Test torque calculation from PWM."""
        # Test at PWM = 0.5
        torque = motor_model.torque_from_pwm(0.5, motor_id=0)
        rpm = 8000 * 0.5 + 500  # 4500 RPM
        expected = 1e-7 * rpm**2
        assert np.isclose(torque, expected, rtol=1e-6)
        
        # Test negative torque handling
        torque = motor_model.torque_from_pwm(-0.1, motor_id=0)
        assert torque >= 0.0
    
    def test_pwm_from_thrust(self, motor_model):
        """Test PWM calculation from thrust."""
        # Test inverse relationship
        pwm = 0.5
        thrust = motor_model.thrust_from_pwm(pwm, motor_id=0)
        pwm_calculated = motor_model.pwm_from_thrust(thrust, motor_id=0)
        assert np.isclose(pwm, pwm_calculated, rtol=1e-3)
        
        # Test zero thrust
        pwm = motor_model.pwm_from_thrust(0.0, motor_id=0)
        assert pwm == motor_model.get_motor_parameters(0).pwm_idle
        
        # Test negative thrust
        pwm = motor_model.pwm_from_thrust(-1.0, motor_id=0)
        assert pwm == motor_model.get_motor_parameters(0).pwm_idle
    
    def test_rpm_from_pwm(self, motor_model):
        """Test RPM calculation from PWM."""
        # Test linear relationship
        rpm = motor_model.rpm_from_pwm(0.5, motor_id=0)
        expected = 8000 * 0.5 + 500  # 4500 RPM
        assert np.isclose(rpm, expected, rtol=1e-6)
        
        # Test negative RPM handling
        rpm = motor_model.rpm_from_pwm(-0.1, motor_id=0)
        assert rpm >= 0.0
    
    def test_unknown_motor_id(self, motor_model):
        """Test handling of unknown motor ID."""
        with pytest.raises(ValueError, match="Unknown motor ID: 99"):
            motor_model.thrust_from_pwm(0.5, motor_id=99)
    
    def test_pwm_validation(self, motor_model):
        """Test PWM validation."""
        # Valid PWM
        assert motor_model.validate_pwm(0.5, motor_id=0)
        
        # Invalid PWM
        assert not motor_model.validate_pwm(1.5, motor_id=0)
        assert not motor_model.validate_pwm(-0.1, motor_id=0)
    
    def test_get_motor_parameters(self, motor_model):
        """Test getting motor parameters."""
        params = motor_model.get_motor_parameters(0)
        assert params.motor_id == 0
        assert params.thrust_a == 2.5
    
    def test_get_model_summary(self, motor_model):
        """Test model summary generation."""
        summary = motor_model.get_model_summary()
        
        assert summary["model_type"] == "quadratic"
        assert summary["motor_count"] == 2
        assert "motors" in summary
        assert "0" in summary["motors"]
        assert "1" in summary["motors"]


class TestFitQuadraticMotorModel:
    """Test quadratic model fitting from bench data."""
    
    def test_fit_quadratic_model(self):
        """Test fitting quadratic model to bench data."""
        # Create synthetic bench data
        pwm_values = [0.1, 0.3, 0.5, 0.7, 0.9]
        thrust_measurements = [0.5, 1.2, 2.1, 3.2, 4.5]
        rpm_measurements = [1000.0, 2500.0, 4000.0, 5500.0, 7000.0]
        
        bench_data = BenchTestData(
            motor_id=0,
            pwm_values=pwm_values,
            thrust_measurements=thrust_measurements,
            rpm_measurements=rpm_measurements
        )
        
        # Fit model
        params = fit_quadratic_motor_model(bench_data)
        
        # Verify parameters
        assert params.motor_id == 0
        assert params.thrust_a > 0  # Should be positive for quadratic fit
        assert params.rpm_coefficient > 0
        assert params.pwm_min == 0.1
        assert params.pwm_max == 0.9
    
    def test_fit_with_torque_data(self):
        """Test fitting with torque measurements."""
        pwm_values = [0.1, 0.3, 0.5, 0.7, 0.9]
        thrust_measurements = [0.5, 1.2, 2.1, 3.2, 4.5]
        rpm_measurements = [1000.0, 2500.0, 4000.0, 5500.0, 7000.0]
        torque_measurements = [0.01, 0.05, 0.12, 0.22, 0.35]
        
        bench_data = BenchTestData(
            motor_id=0,
            pwm_values=pwm_values,
            thrust_measurements=thrust_measurements,
            rpm_measurements=rpm_measurements,
            torque_measurements=torque_measurements
        )
        
        params = fit_quadratic_motor_model(bench_data)
        assert params.torque_coefficient > 0
    
    def test_fit_invalid_data(self):
        """Test fitting with invalid bench data."""
        bench_data = BenchTestData(
            motor_id=0,
            pwm_values=[0.1, 0.3],  # Insufficient points
            thrust_measurements=[0.5, 1.2],
            rpm_measurements=[1000, 2500]
        )
        
        with pytest.raises(ValueError, match="Invalid bench data"):
            fit_quadratic_motor_model(bench_data)


class TestCreateDefaultMotorModel:
    """Test default motor model creation."""
    
    def test_create_default_model(self):
        """Test creating default motor model."""
        model = create_default_motor_model()
        
        # Verify it's a QuadraticMotorModel
        assert isinstance(model, QuadraticMotorModel)
        
        # Verify it has 4 motors
        assert len(model.motor_parameters) == 4
        
        # Verify motor IDs
        for motor_id in range(4):
            assert motor_id in model.motor_parameters
        
        # Verify alternating directions
        assert model.motor_parameters[0].direction == 1
        assert model.motor_parameters[1].direction == -1
        assert model.motor_parameters[2].direction == 1
        assert model.motor_parameters[3].direction == -1
    
    def test_default_model_thrust_calculation(self):
        """Test thrust calculation with default model."""
        model = create_default_motor_model()
        
        # Test thrust at PWM = 0.5
        thrust = model.thrust_from_pwm(0.5, motor_id=0)
        expected = 2.5 * 0.5**2 + 1.2 * 0.5 + 0.1
        assert np.isclose(thrust, expected, rtol=1e-6)


class TestMotorModelIntegration:
    """Test integration between motor model and motor mixer."""
    
    def test_motor_model_with_mixer(self):
        """Test motor model integration with motor mixer."""
        from dart_planner.hardware.motor_mixer import MotorMixingConfig, MotorMixer
        
        # Create motor model
        motor_model = create_default_motor_model()
        
        # Create mixer config with motor model
        config = MotorMixingConfig(motor_model=motor_model)
        
        # Create mixer
        mixer = MotorMixer(config)
        
        # Test mixing with motor model
        thrust = 10.0  # N
        torque = np.array([0.1, 0.1, 0.05])  # N·m
        
        motor_pwms = mixer.mix_commands(thrust, torque)
        
        # Verify output
        assert len(motor_pwms) == 4
        assert np.all(motor_pwms >= 0.0)
        assert np.all(motor_pwms <= 1.0)
        
        # Verify control allocation (round-trip)
        allocated = mixer.get_control_allocation(motor_pwms)
        assert len(allocated) == 4  # [thrust, τx, τy, τz]
        assert allocated[0] > 0  # Should have positive thrust


class TestMotorModelEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_linear_case(self):
        """Test motor model with linear thrust (a=0)."""
        params = {
            0: MotorParameters(
                motor_id=0,
                thrust_a=0.0,  # Linear case
                thrust_b=2.0,
                thrust_c=0.1,
                torque_coefficient=1e-7,
                rpm_coefficient=8000,
                rpm_offset=500,
                direction=1
            )
        }
        
        model = QuadraticMotorModel(params)
        
        # Test thrust calculation
        thrust = model.thrust_from_pwm(0.5, motor_id=0)
        expected = 2.0 * 0.5 + 0.1
        assert np.isclose(thrust, expected, rtol=1e-6)
        
        # Test PWM calculation
        pwm = model.pwm_from_thrust(thrust, motor_id=0)
        assert np.isclose(pwm, 0.5, rtol=1e-3)
    
    def test_zero_coefficients(self):
        """Test motor model with zero coefficients."""
        params = {
            0: MotorParameters(
                motor_id=0,
                thrust_a=0.0,
                thrust_b=0.0,  # Zero coefficients
                thrust_c=0.1,
                torque_coefficient=1e-7,
                rpm_coefficient=8000,
                rpm_offset=500,
                direction=1
            )
        }
        
        model = QuadraticMotorModel(params)
        
        # Should return idle PWM for any thrust
        pwm = model.pwm_from_thrust(10.0, motor_id=0)
        assert pwm == params[0].pwm_idle
    
    def test_pwm_clipping(self):
        """Test PWM clipping behavior."""
        params = {
            0: MotorParameters(
                motor_id=0,
                thrust_a=2.5,
                thrust_b=1.2,
                thrust_c=0.1,
                torque_coefficient=1e-7,
                rpm_coefficient=8000,
                rpm_offset=500,
                pwm_min=0.1,
                pwm_max=0.9,
                direction=1
            )
        }
        
        model = QuadraticMotorModel(params)
        
        # Test thrust calculation with out-of-bounds PWM
        thrust = model.thrust_from_pwm(1.5, motor_id=0)  # Above max
        assert thrust > 0  # Should still work
        
        # Test PWM calculation with very high thrust
        pwm = model.pwm_from_thrust(1000.0, motor_id=0)
        assert pwm == params[0].pwm_max  # Should clip to max 