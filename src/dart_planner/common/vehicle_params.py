"""Global vehicle parameters (mass, inertia, drag).

Parameters are loaded from YAML (config/hardware.yaml by default) so that
controllers and planners share a single source of truth and can be updated at
runtime if payload changes.
"""
from __future__ import annotations

import os
import yaml
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np

_DEFAULT_YAML = Path(__file__).resolve().parent.parent.parent / "config" / "hardware.yaml"

@dataclass
class VehicleParams:
    mass: float = 1.0                # kg
    gravity: float = 9.80665         # m/s²
    inertia: tuple[float, float, float] = (0.02, 0.02, 0.04)  # kg·m² diagonal Ix,Iy,Iz
    drag_coeff: tuple[float, float, float] = (0.0, 0.0, 0.0)  # N/(m/s) simplistic linear drag

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VehicleParams":
        return cls(
            mass=float(data.get("mass", cls.mass)),
            gravity=float(data.get("gravity", cls.gravity)),
            inertia=tuple(data.get("inertia", cls.inertia)),
            drag_coeff=tuple(data.get("drag_coeff", cls.drag_coeff)),
        )

    @property
    def inertia_matrix(self) -> np.ndarray:
        """Return inertia as a 3x3 diagonal matrix (kg·m²)."""
        return np.diag(self.inertia)

    @property
    def inertia_array(self) -> np.ndarray:
        """Return inertia as a 3-element array (kg·m²) for efficient computation."""
        return np.array(self.inertia)


# Singleton instance
_params: VehicleParams = VehicleParams()


def load_params(yaml_path: Optional[str | Path] = None) -> VehicleParams:
    """Load parameters from YAML; overrides existing values."""
    global _params
    path = Path(yaml_path) if yaml_path else _DEFAULT_YAML
    if not path.exists():
        return _params

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _params = VehicleParams.from_dict(data)
    return _params


def get_params() -> VehicleParams:
    """Return current vehicle parameters."""
    return _params


# Pre-computed constants for high-frequency control loops (no unit conversions)
def get_control_constants() -> dict:
    """Return pre-computed constants for control loops to avoid unit conversions."""
    params = get_params()
    return {
        'mass': params.mass,                    # kg
        'gravity': params.gravity,              # m/s²
        'inertia': params.inertia_array,        # kg·m² (3-element array)
        'inertia_matrix': params.inertia_matrix, # kg·m² (3x3 matrix)
        'drag_coeff': np.array(params.drag_coeff), # N/(m/s)
    }


def load_hardware_params(yaml_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """
    Load hardware parameters from a YAML file (default: config/hardware.yaml).
    Returns a dict with keys: arm_length, max_motor_thrust, max_propeller_drag_torque, num_arms, geometry, etc.
    """
    path = Path(yaml_path) if yaml_path else _DEFAULT_YAML
    if not path.is_file():
        # Raise an error to make configuration issues explicit.
        raise FileNotFoundError(f"Hardware configuration file not found at: {path}")

    with path.open("r", encoding="utf-8") as f:
        params = yaml.safe_load(f) or {}

    # The hardware config might be nested under a 'vehicle' key.
    # Handle this legacy format gracefully.
    if 'vehicle' in params and isinstance(params['vehicle'], dict):
        return params['vehicle']
        
    return params

def compute_max_torque_xyz(params: Dict[str, Any]) -> np.ndarray:
    """
    Compute per-axis max torque based on hardware config.
    Args:
        params: dict with keys arm_length, max_motor_thrust, max_propeller_drag_torque
    Returns:
        np.array([roll_max, pitch_max, yaw_max]) in Nm
    """
    # If hardware params are empty (e.g., during tests or config errors),
    # return a safe, non-zero default to avoid KeyErrors.
    if not all(k in params for k in ['arm_length', 'max_motor_thrust', 'max_propeller_drag_torque']):
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Hardware parameters for torque calculation not found. Using safe defaults.")
        # Default to safe, small torque limits to prevent crashes.
        return np.array([0.5, 0.5, 0.05]) # [roll_max, pitch_max, yaw_max] in Nm

    L = params['arm_length']
    Fmax = params['max_motor_thrust']
    Qmax = params['max_propeller_drag_torque']
    # For quad: roll/pitch = L * Fmax, yaw = 2 * Qmax
    roll_pitch = L * Fmax
    yaw = 2 * Qmax
    return np.array([roll_pitch, roll_pitch, yaw])

def load_transport_delay_config(yaml_path=None):
    """
    Load transport delay configuration from hardware.yaml.
    
    Returns:
        dict with keys: delay_ms, control_loop_period_ms, enabled, max_buffer_size
    """
    params = load_hardware_params(yaml_path)
    transport_delay = params.get('transport_delay', {})
    
    # Default values if not specified
    defaults = {
        'delay_ms': 25.0,
        'control_loop_period_ms': 5.0,
        'enabled': True,
        'max_buffer_size': 1000
    }
    
    # Merge with defaults
    config = defaults.copy()
    config.update(transport_delay)
    
    return config

def create_transport_delay_buffer(yaml_path=None):
    """
    Create a transport delay buffer based on hardware.yaml configuration.
    
    Args:
        yaml_path: Optional path to hardware.yaml file
        
    Returns:
        DroneStateLatencyBuffer if enabled, None if disabled
    """
    from dart_planner.utils.latency_buffer import DroneStateLatencyBuffer
    
    config = load_transport_delay_config(yaml_path)
    
    if not config['enabled']:
        return None
        
    delay_s = config['delay_ms'] / 1000.0
    dt_s = config['control_loop_period_ms'] / 1000.0
    max_buffer_size = config['max_buffer_size']
    
    return DroneStateLatencyBuffer(delay_s, dt_s, max_buffer_size)

# Load defaults on import
load_params() 