"""Global vehicle parameters (mass, inertia, drag).

Parameters are loaded from YAML (config/hardware.yaml by default) so that
controllers and planners share a single source of truth and can be updated at
runtime if payload changes.
"""
from __future__ import annotations

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


# Load defaults on import
load_params() 