"""
Control Configuration for DART-Planner

This module provides configuration classes for different control scenarios,
allowing easy switching between parameter sets for different flight conditions.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class ControllerTuningProfile:
    """Single controller tuning profile for specific conditions"""
    
    name: str
    description: str
    
    # Position control gains (PID)
    kp_pos: np.ndarray
    ki_pos: np.ndarray  
    kd_pos: np.ndarray
    
    # Attitude control gains (PD)
    kp_att: np.ndarray
    kd_att: np.ndarray
    
    # Feedforward gains
    ff_pos: float
    ff_vel: float
    
    # Physical constraints
    max_tilt_angle: float
    max_thrust: float
    min_thrust: float
    
    # Performance thresholds
    tracking_error_threshold: float
    velocity_error_threshold: float
    
    # Integral limits
    max_integral_pos: float


class ControllerTuningManager:
    """Manager for controller tuning profiles"""
    
    def __init__(self):
        self.profiles: Dict[str, ControllerTuningProfile] = {}
        self._initialize_default_profiles()
    
    def _initialize_default_profiles(self):
        """Initialize default tuning profiles"""
        
        # Conservative profile for stable, precise flight
        self.profiles["conservative"] = ControllerTuningProfile(
            name="conservative",
            description="Conservative gains for stable flight and precise tracking",
            kp_pos=np.array([15.0, 15.0, 18.0]),  # Higher position gains
            ki_pos=np.array([2.0, 2.0, 3.0]),    # Increased integral for steady-state
            kd_pos=np.array([8.0, 8.0, 10.0]),   # Higher derivative for damping
            kp_att=np.array([15.0, 15.0, 8.0]),  # Increased attitude gains
            kd_att=np.array([6.0, 6.0, 3.0]),    # More attitude damping
            ff_pos=1.5,                          # Increased feedforward
            ff_vel=1.0,                          # Better velocity feedforward
            max_tilt_angle=np.pi / 6,            # 30 degrees (conservative)
            max_thrust=20.0,
            min_thrust=0.5,
            tracking_error_threshold=1.5,        # Tighter tracking requirement
            velocity_error_threshold=0.8,        # Tighter velocity requirement
            max_integral_pos=3.0                 # Reduced integral windup
        )
        
        # Aggressive profile for fast, dynamic flight
        self.profiles["aggressive"] = ControllerTuningProfile(
            name="aggressive", 
            description="Aggressive gains for fast, dynamic maneuvers",
            kp_pos=np.array([25.0, 25.0, 30.0]),  # Very high position gains
            ki_pos=np.array([1.0, 1.0, 1.5]),     # Lower integral to prevent oscillation
            kd_pos=np.array([12.0, 12.0, 15.0]),  # High derivative for stability
            kp_att=np.array([20.0, 20.0, 10.0]),  # High attitude gains
            kd_att=np.array([8.0, 8.0, 4.0]),     # High attitude damping
            ff_pos=2.0,                           # Strong feedforward
            ff_vel=1.2,                           # Strong velocity feedforward
            max_tilt_angle=np.pi / 3,             # 60 degrees (aggressive)
            max_thrust=25.0,
            min_thrust=1.0,
            tracking_error_threshold=0.8,         # Very tight tracking
            velocity_error_threshold=0.5,         # Very tight velocity
            max_integral_pos=2.0                  # Tight integral control
        )
        
        # Simulation-optimized profile for SITL testing
        self.profiles["sitl_optimized"] = ControllerTuningProfile(
            name="sitl_optimized",
            description="Optimized for SITL testing with AirSim SimpleFlight",
            kp_pos=np.array([20.0, 20.0, 25.0]),  # Tuned for sim dynamics
            ki_pos=np.array([1.5, 1.5, 2.0]),     # Moderate integral for sim
            kd_pos=np.array([10.0, 10.0, 12.0]),  # Good damping for sim
            kp_att=np.array([18.0, 18.0, 8.0]),   # Attitude gains for sim
            kd_att=np.array([7.0, 7.0, 3.5]),     # Attitude damping for sim
            ff_pos=1.8,                           # Strong feedforward for sim
            ff_vel=1.1,                           # Good velocity feedforward
            max_tilt_angle=np.pi / 4,             # 45 degrees (balanced)
            max_thrust=22.0,
            min_thrust=0.8,
            tracking_error_threshold=1.0,         # Achievable tracking for sim
            velocity_error_threshold=0.6,         # Achievable velocity for sim
            max_integral_pos=2.5                  # Moderate integral control
        )
        
        # Precision tracking profile for minimal tracking error  
        self.profiles["precision_tracking"] = ControllerTuningProfile(
            name="precision_tracking",
            description="High-precision tracking optimized for minimal position error",
            kp_pos=np.array([18.0, 18.0, 22.0]),  # Moderate increase from sitl_optimized
            ki_pos=np.array([2.5, 2.5, 3.5]),     # Stronger integral for steady-state error elimination
            kd_pos=np.array([12.0, 12.0, 14.0]),  # Enhanced derivative for damping
            kp_att=np.array([22.0, 22.0, 10.0]),  # Increased attitude gains for precision
            kd_att=np.array([8.0, 8.0, 4.0]),     # Enhanced attitude damping
            ff_pos=2.2,                           # Stronger position feedforward
            ff_vel=1.3,                           # Enhanced velocity feedforward for tracking
            max_tilt_angle=np.pi / 4,             # 45 degrees (balanced agility/stability)
            max_thrust=25.0,                      # Increased thrust capability
            min_thrust=0.8,
            tracking_error_threshold=0.8,         # Tight tracking requirement
            velocity_error_threshold=0.4,         # Tight velocity requirement  
            max_integral_pos=2.0                  # Controlled integral windup prevention
        )
        
        # Enhanced tracking profile (conservative improvement over sitl_optimized)
        self.profiles["enhanced_tracking"] = ControllerTuningProfile(
            name="enhanced_tracking",
            description="Conservative enhancement of sitl_optimized for better tracking",
            kp_pos=np.array([22.0, 22.0, 28.0]),  # +10% increase from sitl_optimized
            ki_pos=np.array([2.0, 2.0, 2.5]),     # +33% increase for steady-state error
            kd_pos=np.array([11.0, 11.0, 13.0]),  # +10% increase for damping
            kp_att=np.array([20.0, 20.0, 9.0]),   # +11% increase for attitude control
            kd_att=np.array([8.0, 8.0, 4.0]),     # +14% increase for attitude damping
            ff_pos=2.0,                           # +11% increase in feedforward
            ff_vel=1.2,                           # +9% increase in velocity feedforward
            max_tilt_angle=np.pi / 4,             # 45 degrees (same as sitl_optimized)
            max_thrust=24.0,                      # +9% increase
            min_thrust=0.8,
            tracking_error_threshold=0.9,         # Tighter than sitl_optimized (1.0m)
            velocity_error_threshold=0.5,         # Tighter than sitl_optimized (0.6m/s)
            max_integral_pos=2.2                  # Slight reduction for tighter control
        )
        
        # Tracking optimized profile (minimal changes to working sitl_optimized)
        self.profiles["tracking_optimized"] = ControllerTuningProfile(
            name="tracking_optimized",
            description="Minimal tracking improvements to proven sitl_optimized profile",
            kp_pos=np.array([21.0, 21.0, 26.0]),  # +5% increase from sitl_optimized
            ki_pos=np.array([1.8, 1.8, 2.2]),     # +20% increase for steady-state error
            kd_pos=np.array([10.5, 10.5, 12.5]),  # +5% increase for damping
            kp_att=np.array([18.5, 18.5, 8.2]),   # +3% increase for attitude control
            kd_att=np.array([7.2, 7.2, 3.6]),     # +3% increase for attitude damping
            ff_pos=1.9,                           # +6% increase in feedforward
            ff_vel=1.15,                          # +5% increase in velocity feedforward
            max_tilt_angle=np.pi / 4,             # 45 degrees (same as sitl_optimized)
            max_thrust=22.0,                      # +5% increase
            min_thrust=0.8,
            tracking_error_threshold=0.95,        # Slightly tighter than sitl_optimized (1.0m)
            velocity_error_threshold=0.55,        # Slightly tighter than sitl_optimized (0.6m/s)
            max_integral_pos=2.3                  # Slight reduction for tighter control
        )
        
        # Original profile (for comparison)
        self.profiles["original"] = ControllerTuningProfile(
            name="original",
            description="Original DART-Planner tuning (Phase 2C)",
            kp_pos=np.array([10.0, 10.0, 12.0]),
            ki_pos=np.array([0.5, 0.5, 1.0]),
            kd_pos=np.array([6.0, 6.0, 8.0]),
            kp_att=np.array([12.0, 12.0, 5.0]),
            kd_att=np.array([4.0, 4.0, 2.0]),
            ff_pos=1.2,
            ff_vel=0.8,
            max_tilt_angle=np.pi / 3,
            max_thrust=20.0,
            min_thrust=0.5,
            tracking_error_threshold=2.0,
            velocity_error_threshold=1.0,
            max_integral_pos=5.0
        )
    
    def get_profile(self, name: str) -> Optional[ControllerTuningProfile]:
        """Get tuning profile by name"""
        return self.profiles.get(name)
    
    def list_profiles(self) -> Dict[str, str]:
        """List available profiles and their descriptions"""
        return {name: profile.description for name, profile in self.profiles.items()}
    
    def add_custom_profile(self, profile: ControllerTuningProfile):
        """Add a custom tuning profile"""
        self.profiles[profile.name] = profile
    
    def get_recommended_profile(self, scenario: str) -> str:
        """Get recommended profile for given scenario"""
        recommendations = {
            "sitl": "sitl_optimized",
            "simulation": "sitl_optimized", 
            "testing": "conservative",
            "hardware": "conservative",
            "aggressive": "aggressive",
            "racing": "aggressive",
            "precision": "conservative",
            "default": "sitl_optimized"
        }
        return recommendations.get(scenario.lower(), "sitl_optimized")


# Global instance for easy access
tuning_manager = ControllerTuningManager()


def get_controller_config(profile_name: str = "sitl_optimized") -> ControllerTuningProfile:
    """
    Get controller configuration for specified profile
    
    Args:
        profile_name: Name of the tuning profile to use
        
    Returns:
        ControllerTuningProfile object with tuning parameters
        
    Raises:
        ValueError: If profile_name doesn't exist
    """
    profile = tuning_manager.get_profile(profile_name)
    if profile is None:
        available = list(tuning_manager.profiles.keys())
        from dart_planner.common.errors import ConfigurationError
        raise ConfigurationError(f"Unknown profile '{profile_name}'. Available: {available}")
    
    return profile


def print_tuning_comparison():
    """Print comparison of all tuning profiles"""
    print("🎛️  Controller Tuning Profile Comparison")
    print("=" * 80)
    
    for name, profile in tuning_manager.profiles.items():
        print(f"\n📊 {profile.name.upper()} Profile:")
        print(f"   Description: {profile.description}")
        print(f"   Position gains: Kp={profile.kp_pos}, Ki={profile.ki_pos}, Kd={profile.kd_pos}")
        print(f"   Attitude gains: Kp={profile.kp_att}, Kd={profile.kd_att}")
        print(f"   Feedforward: pos={profile.ff_pos:.1f}, vel={profile.ff_vel:.1f}")
        print(f"   Max tilt: {np.degrees(profile.max_tilt_angle):.0f}°")
        print(f"   Tracking threshold: {profile.tracking_error_threshold:.1f}m")


if __name__ == "__main__":
    # Demo usage
    print_tuning_comparison()
    
    # Test profile access
    sitl_config = get_controller_config("sitl_optimized")
    print(f"\n✅ SITL Optimized config loaded: {sitl_config.name}")
