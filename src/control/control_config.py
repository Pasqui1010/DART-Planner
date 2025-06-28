from dataclasses import dataclass, field
import numpy as np
from typing import Optional

@dataclass
class PIDGains:
    Kp: float
    Ki: float
    Kd: float
    integral_limit: float

@dataclass
class ControlConfig:
    pos_x: PIDGains
    pos_y: PIDGains
    pos_z: PIDGains
    roll: PIDGains
    pitch: PIDGains
    yaw_rate: PIDGains

# --- Validated Gains from Structured Testing (Final) ---
# These gains were determined by systematically testing the control components
# in an isolated environment before integration.
# Phase 1: Validated Feedforward model.
# Phase 2: Validated Feedback stability and responsiveness.
# Phase 3: These integrated gains provide high-precision tracking.
default_control_config = ControlConfig(
    # --- Position Gains (Final Tuning) ---
    # Increased P-gain for better responsiveness, and added a small I-gain
    # to eliminate any final steady-state error.
    pos_x = PIDGains(Kp=0.8, Ki=0.15, Kd=0.1, integral_limit=0.4),
    pos_y = PIDGains(Kp=0.8, Ki=0.15, Kd=0.1, integral_limit=0.4),
    pos_z = PIDGains(Kp=1.5, Ki=0.25, Kd=0.15, integral_limit=0.8),
    
    # --- Attitude Gains (Validated & Stable) ---
    roll = PIDGains(Kp=0.15, Ki=0.01, Kd=0.04, integral_limit=0.2),
    pitch = PIDGains(Kp=0.15, Ki=0.01, Kd=0.04, integral_limit=0.2),
    yaw_rate = PIDGains(Kp=0.15, Ki=0.0, Kd=0.01, integral_limit=0.2)
) 