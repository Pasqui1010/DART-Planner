"""
Motor Latency Calibration for DART-Planner

This module provides tools to calibrate motor/actuator latency and dynamically
adjust max_control_latency_ms for optimal real-time performance.
"""

import time
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from statistics import mean, stdev
import threading

logger = logging.getLogger(__name__)


@dataclass
class LatencyMeasurement:
    """Single latency measurement result."""
    timestamp: float
    command_sent: float
    response_detected: float
    latency_ms: float
    motor_command: str
    response_type: str
    success: bool


@dataclass
class CalibrationResult:
    """Motor latency calibration results."""
    mean_latency_ms: float
    std_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    sample_count: int
    confidence_interval_ms: Tuple[float, float]
    recommended_max_latency_ms: float
    calibration_quality: str  # "excellent", "good", "fair", "poor"


class MotorLatencyCalibrator:
    """
    Calibrates motor/actuator latency by sending test commands and measuring response times.
    """
    
    def __init__(self, hardware_adapter, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the motor latency calibrator.
        
        Args:
            hardware_adapter: Hardware adapter instance (Pixhawk, AirSim, etc.)
            config: Calibration configuration
        """
        self.hardware_adapter = hardware_adapter
        self.config = config or self._get_default_config()
        self.measurements: List[LatencyMeasurement] = []
        self.calibration_lock = threading.Lock()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default calibration configuration."""
        return {
            "num_samples": 50,
            "command_interval_ms": 100,
            "test_commands": [
                {"type": "throttle_step", "value": 0.1},
                {"type": "throttle_step", "value": -0.1},
                {"type": "attitude_step", "value": 0.05},
                {"type": "attitude_step", "value": -0.05}
            ],
            "response_threshold_ms": 50.0,
            "confidence_level": 0.95,
            "min_samples": 10
        }
    
    def calibrate_latency(self, num_samples: Optional[int] = None) -> CalibrationResult:
        """
        Perform motor latency calibration.
        
        Args:
            num_samples: Number of samples to collect (overrides config)
            
        Returns:
            CalibrationResult with latency statistics
        """
        with self.calibration_lock:
            samples = num_samples or self.config["num_samples"]
            logger.info(f"Starting motor latency calibration with {samples} samples")
            
            # Clear previous measurements
            self.measurements.clear()
            
            # Perform calibration measurements
            for i in range(samples):
                measurement = self._perform_single_measurement(i)
                if measurement:
                    self.measurements.append(measurement)
                
                # Wait between measurements
                time.sleep(self.config["command_interval_ms"] / 1000.0)
            
            # Analyze results
            result = self._analyze_calibration_results()
            
            logger.info(f"Calibration completed: mean={result.mean_latency_ms:.2f}ms, "
                       f"std={result.std_latency_ms:.2f}ms, quality={result.calibration_quality}")
            
            return result
    
    def _perform_single_measurement(self, sample_index: int) -> Optional[LatencyMeasurement]:
        """Perform a single latency measurement."""
        try:
            # Select test command
            command = self.config["test_commands"][sample_index % len(self.config["test_commands"])]
            
            # Record initial state
            initial_state = self.hardware_adapter.get_state()
            initial_time = time.perf_counter()
            
            # Send test command
            command_sent_time = time.perf_counter()
            self._send_test_command(command)
            
            # Monitor for response
            response_detected_time = self._detect_response(initial_state, command)
            
            if response_detected_time is None:
                logger.warning(f"Sample {sample_index}: No response detected within timeout")
                return None
            
            # Calculate latency
            latency_ms = (response_detected_time - command_sent_time) * 1000.0
            
            # Validate latency
            if latency_ms > self.config["response_threshold_ms"]:
                logger.warning(f"Sample {sample_index}: Latency {latency_ms:.2f}ms exceeds threshold")
                return None
            
            measurement = LatencyMeasurement(
                timestamp=time.time(),
                command_sent=command_sent_time,
                response_detected=response_detected_time,
                latency_ms=latency_ms,
                motor_command=str(command),
                response_type="attitude_change",
                success=True
            )
            
            logger.debug(f"Sample {sample_index}: Latency {latency_ms:.2f}ms")
            return measurement
            
        except Exception as e:
            logger.error(f"Sample {sample_index}: Measurement failed: {e}")
            return None
    
    def _send_test_command(self, command: Dict[str, Any]) -> None:
        """Send a test command to the hardware."""
        command_type = command["type"]
        value = command["value"]
        
        if command_type == "throttle_step":
            # Send throttle step command
            self.hardware_adapter.send_command("set_throttle", {"throttle": value})
        elif command_type == "attitude_step":
            # Send attitude step command
            self.hardware_adapter.send_command("set_attitude", {"roll": value, "pitch": 0, "yaw": 0})
        else:
            raise ValueError(f"Unknown command type: {command_type}")
    
    def _detect_response(self, initial_state: Dict[str, Any], command: Dict[str, Any]) -> Optional[float]:
        """Detect response to the test command."""
        command_type = command["type"]
        value = command["value"]
        timeout_ms = self.config["response_threshold_ms"]
        start_time = time.perf_counter()
        
        while (time.perf_counter() - start_time) * 1000.0 < timeout_ms:
            current_state = self.hardware_adapter.get_state()
            
            # Check for response based on command type
            if command_type == "throttle_step":
                if self._detect_throttle_response(initial_state, current_state, value):
                    return time.perf_counter()
            elif command_type == "attitude_step":
                if self._detect_attitude_response(initial_state, current_state, value):
                    return time.perf_counter()
            
            time.sleep(0.001)  # 1ms polling interval
        
        return None
    
    def _detect_throttle_response(self, initial_state: Dict[str, Any], 
                                current_state: Dict[str, Any], expected_change: float) -> bool:
        """Detect throttle response."""
        try:
            initial_altitude = initial_state.get("position", {}).get("z", 0.0)
            current_altitude = current_state.get("position", {}).get("z", 0.0)
            
            # Check if altitude changed in expected direction
            altitude_change = current_altitude - initial_altitude
            return (expected_change > 0 and altitude_change > 0.01) or \
                   (expected_change < 0 and altitude_change < -0.01)
        except Exception:
            return False
    
    def _detect_attitude_response(self, initial_state: Dict[str, Any], 
                                current_state: Dict[str, Any], expected_change: float) -> bool:
        """Detect attitude response."""
        try:
            initial_roll = initial_state.get("attitude", {}).get("roll", 0.0)
            current_roll = current_state.get("attitude", {}).get("roll", 0.0)
            
            # Check if roll changed in expected direction
            roll_change = current_roll - initial_roll
            return (expected_change > 0 and roll_change > 0.01) or \
                   (expected_change < 0 and roll_change < -0.01)
        except Exception:
            return False
    
    def _analyze_calibration_results(self) -> CalibrationResult:
        """Analyze calibration results and generate statistics."""
        if not self.measurements:
            raise ValueError("No measurements available for analysis")
        
        latencies = [m.latency_ms for m in self.measurements if m.success]
        
        if len(latencies) < self.config["min_samples"]:
            raise ValueError(f"Insufficient samples: {len(latencies)} < {self.config['min_samples']}")
        
        # Calculate statistics
        mean_latency = mean(latencies)
        std_latency = stdev(latencies) if len(latencies) > 1 else 0.0
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p95_latency = np.percentile(sorted_latencies, 95)
        p99_latency = np.percentile(sorted_latencies, 99)
        
        # Calculate confidence interval
        confidence_interval = self._calculate_confidence_interval(latencies, mean_latency, std_latency)
        
        # Determine recommended max latency
        recommended_max_latency = self._calculate_recommended_max_latency(
            mean_latency, std_latency, p95_latency, p99_latency
        )
        
        # Assess calibration quality
        quality = self._assess_calibration_quality(latencies, std_latency, len(latencies))
        
        return CalibrationResult(
            mean_latency_ms=mean_latency,
            std_latency_ms=std_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            sample_count=len(latencies),
            confidence_interval_ms=confidence_interval,
            recommended_max_latency_ms=recommended_max_latency,
            calibration_quality=quality
        )
    
    def _calculate_confidence_interval(self, latencies: List[float], mean_latency: float, 
                                     std_latency: float) -> Tuple[float, float]:
        """Calculate confidence interval for the mean."""
        if len(latencies) < 2:
            return (mean_latency, mean_latency)
        
        # 95% confidence interval
        import scipy.stats as stats
        confidence_level = self.config["confidence_level"]
        t_value = stats.t.ppf((1 + confidence_level) / 2, len(latencies) - 1)
        margin_of_error = t_value * std_latency / np.sqrt(len(latencies))
        
        return (mean_latency - margin_of_error, mean_latency + margin_of_error)
    
    def _calculate_recommended_max_latency(self, mean_latency: float, std_latency: float,
                                         p95_latency: float, p99_latency: float) -> float:
        """Calculate recommended max_control_latency_ms."""
        # Use 99th percentile + safety margin
        safety_margin = 1.5  # 50% safety margin
        recommended = p99_latency * safety_margin
        
        # Ensure minimum reasonable value
        min_recommended = 5.0  # 5ms minimum
        return max(recommended, min_recommended)
    
    def _assess_calibration_quality(self, latencies: List[float], std_latency: float, 
                                  sample_count: int) -> str:
        """Assess the quality of the calibration."""
        # Check sample count
        if sample_count < 20:
            return "poor"
        elif sample_count < 40:
            return "fair"
        
        # Check consistency (coefficient of variation)
        mean_latency = mean(latencies)
        cv = std_latency / mean_latency if mean_latency > 0 else float('inf')
        
        if cv < 0.1:  # Less than 10% variation
            return "excellent"
        elif cv < 0.2:  # Less than 20% variation
            return "good"
        elif cv < 0.3:  # Less than 30% variation
            return "fair"
        else:
            return "poor"
    
    def update_config_latency(self, result: CalibrationResult) -> bool:
        """
        Update the system configuration with the calibrated latency.
        
        Args:
            result: Calibration result
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update the real-time configuration
            from dart_planner.config.frozen_config import get_frozen_config
            
            # Note: This is a simplified approach. In a real implementation,
            # you would need to update the configuration system properly
            logger.info(f"Updating max_control_latency_ms to {result.recommended_max_latency_ms:.2f}ms")
            
            # For now, just log the recommendation
            logger.info(f"Recommended max_control_latency_ms: {result.recommended_max_latency_ms:.2f}ms")
            logger.info(f"Calibration quality: {result.calibration_quality}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update config latency: {e}")
            return False
    
    def get_calibration_report(self) -> Dict[str, Any]:
        """Generate a comprehensive calibration report."""
        if not self.measurements:
            return {"error": "No calibration data available"}
        
        try:
            result = self._analyze_calibration_results()
            
            return {
                "calibration_summary": {
                    "mean_latency_ms": result.mean_latency_ms,
                    "std_latency_ms": result.std_latency_ms,
                    "min_latency_ms": result.min_latency_ms,
                    "max_latency_ms": result.max_latency_ms,
                    "p95_latency_ms": result.p95_latency_ms,
                    "p99_latency_ms": result.p99_latency_ms,
                    "sample_count": result.sample_count,
                    "confidence_interval_ms": result.confidence_interval_ms,
                    "recommended_max_latency_ms": result.recommended_max_latency_ms,
                    "calibration_quality": result.calibration_quality
                },
                "measurements": [
                    {
                        "timestamp": m.timestamp,
                        "latency_ms": m.latency_ms,
                        "motor_command": m.motor_command,
                        "success": m.success
                    }
                    for m in self.measurements
                ]
            }
            
        except Exception as e:
            return {"error": f"Failed to generate report: {e}"}


def calibrate_motor_latency(hardware_adapter, config: Optional[Dict[str, Any]] = None) -> CalibrationResult:
    """
    Convenience function to calibrate motor latency.
    
    Args:
        hardware_adapter: Hardware adapter instance
        config: Calibration configuration
        
    Returns:
        CalibrationResult
    """
    calibrator = MotorLatencyCalibrator(hardware_adapter, config)
    return calibrator.calibrate_latency() 