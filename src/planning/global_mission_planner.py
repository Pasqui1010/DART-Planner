import numpy as np
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from common.types import DroneState, Trajectory

from neural_scene.base_neural_scene import PlaceholderNeuralScene
from neural_scene.uncertainty_field import UncertaintyField
from neural_scene.base_neural_scene import SensorData

class MissionPhase(Enum):
    """Different phases of autonomous mission execution"""
    TAKEOFF = "takeoff"
    EXPLORATION = "exploration"
    MAPPING = "mapping"
    NAVIGATION = "navigation"
    LANDING = "landing"
    EMERGENCY = "emergency"

@dataclass
class SemanticWaypoint:
    """Waypoint with semantic information"""
    position: np.ndarray
    semantic_label: str  # e.g., "safe_zone", "obstacle", "landing_pad"
    uncertainty: float  # Confidence in this waypoint
    priority: int  # Mission priority (1=highest)

@dataclass
class GlobalMissionConfig:
    """Configuration for global mission planning"""
    # Mission parameters
    exploration_radius: float = 50.0  # meters
    mapping_resolution: float = 0.5   # meters per voxel
    safety_margin: float = 2.0        # meters
    
    # Neural scene integration
    use_neural_scene: bool = True
    nerf_update_frequency: float = 0.1  # Hz
    uncertainty_threshold: float = 0.7  # [0,1]
    
    # Multi-agent coordination
    enable_multi_agent: bool = False
    communication_range: float = 100.0  # meters
    
    # Planning frequencies
    global_replan_frequency: float = 1.0   # Hz
    waypoint_update_frequency: float = 2.0  # Hz

class GlobalMissionPlanner:
    """
    Global Mission Planner - The highest level in the three-layer architecture.
    
    This layer handles:
    - Long-term mission planning and execution
    - Neural scene representation integration (NeRF/3DGS)
    - Semantic understanding and reasoning
    - Multi-agent coordination
    - Uncertainty-aware exploration
    - GPS-denied navigation strategy
    
    Architecture:
    Global Mission Planner (1-0.1Hz) ← THIS LAYER
            ↓
    DIAL-MPC Trajectory Optimizer (10Hz)
            ↓
    Geometric Controller (1kHz)
    """
    
    def __init__(self, config: Optional[GlobalMissionConfig] = None):
        self.config = config if config else GlobalMissionConfig()
        
        # Mission state
        self.current_phase = MissionPhase.TAKEOFF
        self.mission_waypoints: List[SemanticWaypoint] = []
        self.current_waypoint_index = 0
        
        # Neural scene representation (NeRF/3DGS integration ready)
        if self.config.use_neural_scene:
            self.neural_scene_model = PlaceholderNeuralScene(
                scene_bounds=np.array([
                    [-self.config.exploration_radius, -self.config.exploration_radius, 0],
                    [self.config.exploration_radius, self.config.exploration_radius, 20]
                ]),
                resolution=self.config.mapping_resolution
            )
            
            # Initialize uncertainty field for exploration planning  
            self.uncertainty_field = UncertaintyField(
                scene_bounds=np.array([
                    [-self.config.exploration_radius, -self.config.exploration_radius, 0],
                    [self.config.exploration_radius, self.config.exploration_radius, 20]
                ]),
                resolution=self.config.mapping_resolution
            )
        else:
            self.neural_scene_model = None
            self.uncertainty_field = None
            
        self.scene_uncertainty_map: Optional[np.ndarray] = None
        self.semantic_scene_map: Optional[Dict[str, np.ndarray]] = None
        
        # Multi-agent coordination
        self.other_agents: List[Dict[str, Any]] = []
        self.shared_neural_scene = None
        
        # Exploration state
        self.explored_regions: List[np.ndarray] = []
        self.high_uncertainty_regions: List[np.ndarray] = []
        
        # Performance tracking
        self.planning_history: List[Dict[str, Any]] = []
        self.last_global_plan_time = 0.0
        
        print("🌍 Global Mission Planner initialized")
        print(f"   Neural Scene: {'Enabled' if self.config.use_neural_scene else 'Disabled'}")
        print(f"   Multi-Agent: {'Enabled' if self.config.enable_multi_agent else 'Disabled'}")
    
    def set_mission_waypoints(self, waypoints: List[SemanticWaypoint]):
        """Set the high-level mission waypoints"""
        self.mission_waypoints = waypoints
        self.current_waypoint_index = 0
        print(f"🎯 Mission set with {len(waypoints)} semantic waypoints")
        
        for i, wp in enumerate(waypoints):
            print(f"   {i+1}. {wp.semantic_label} at {wp.position} (priority: {wp.priority})")
    
    def get_current_goal(self, current_state: DroneState) -> np.ndarray:
        """
        Get the current goal position for DIAL-MPC trajectory optimization.
        
        This is the key interface between Global Mission Planner and DIAL-MPC.
        The global planner provides intelligent goal selection based on:
        - Current mission phase
        - Neural scene understanding
        - Uncertainty awareness
        - Semantic reasoning
        """
        
        # Check if it's time for global replanning
        current_time = time.time()
        if current_time - self.last_global_plan_time > 1.0 / self.config.global_replan_frequency:
            self._execute_global_planning(current_state)
            self.last_global_plan_time = current_time
        
        # Phase-based goal selection
        if self.current_phase == MissionPhase.TAKEOFF:
            return self._plan_takeoff_goal(current_state)
        
        elif self.current_phase == MissionPhase.EXPLORATION:
            return self._plan_exploration_goal(current_state)
        
        elif self.current_phase == MissionPhase.MAPPING:
            return self._plan_mapping_goal(current_state)
        
        elif self.current_phase == MissionPhase.NAVIGATION:
            return self._plan_navigation_goal(current_state)
        
        elif self.current_phase == MissionPhase.LANDING:
            return self._plan_landing_goal(current_state)
        
        elif self.current_phase == MissionPhase.EMERGENCY:
            return self._plan_emergency_goal(current_state)
        
        else:
            # Default: hover in place
            return current_state.position
    
    def _execute_global_planning(self, current_state: DroneState):
        """Execute high-level global planning and phase transitions"""
        
        # Update neural scene representation
        if self.config.use_neural_scene:
            self._update_neural_scene(current_state)
        
        # Check for phase transitions
        self._check_phase_transitions(current_state)
        
        # Update uncertainty maps
        self._update_uncertainty_awareness(current_state)
        
        # Multi-agent coordination
        if self.config.enable_multi_agent:
            self._coordinate_with_other_agents(current_state)
        
        # Log planning decision
        self.planning_history.append({
            'timestamp': time.time(),
            'phase': self.current_phase.value,
            'position': current_state.position.copy(),
            'waypoint_index': self.current_waypoint_index,
            'uncertainty_regions': len(self.high_uncertainty_regions)
        })
    
    def _plan_takeoff_goal(self, current_state: DroneState) -> np.ndarray:
        """Plan takeoff to safe altitude"""
        safe_altitude = 5.0  # meters
        takeoff_goal = current_state.position.copy()
        takeoff_goal[2] = safe_altitude
        
        # Check if takeoff complete
        if current_state.position[2] >= safe_altitude - 0.5:
            print("✈️ Takeoff complete, transitioning to navigation")
            self.current_phase = MissionPhase.NAVIGATION
        
        return takeoff_goal
    
    def _plan_exploration_goal(self, current_state: DroneState) -> np.ndarray:
        """Plan exploration for neural scene mapping"""
        
        if self.high_uncertainty_regions:
            # Go to highest uncertainty region for active exploration
            target_region = max(self.high_uncertainty_regions, 
                              key=lambda r: self._get_region_uncertainty(r))
            print(f"🔍 Exploring high uncertainty region at {target_region}")
            return target_region
        
        else:
            # Systematic exploration pattern
            exploration_center = current_state.position[:2]  # X,Y only
            angle = len(self.explored_regions) * 0.5  # Spiral pattern
            radius = min(10.0 + len(self.explored_regions) * 2.0, self.config.exploration_radius)
            
            goal = np.array([
                exploration_center[0] + radius * np.cos(angle),
                exploration_center[1] + radius * np.sin(angle),
                current_state.position[2]  # Maintain altitude
            ])
            
            print(f"🗺️ Systematic exploration to {goal}")
            return goal
    
    def _plan_mapping_goal(self, current_state: DroneState) -> np.ndarray:
        """Plan optimal viewpoints for neural scene mapping"""
        # This would integrate with NeRF/3DGS training to find optimal viewpoints
        # For now, return next waypoint
        return self._plan_navigation_goal(current_state)
    
    def _plan_navigation_goal(self, current_state: DroneState) -> np.ndarray:
        """Plan navigation to mission waypoints"""
        
        if not self.mission_waypoints:
            print("⚠️ No mission waypoints set, hovering")
            return current_state.position
        
        # Get current target waypoint
        if self.current_waypoint_index >= len(self.mission_waypoints):
            print("🏁 Mission complete, transitioning to landing")
            self.current_phase = MissionPhase.LANDING
            return current_state.position
        
        current_waypoint = self.mission_waypoints[self.current_waypoint_index]
        
        # Check if waypoint reached
        distance_to_waypoint = np.linalg.norm(
            current_state.position - current_waypoint.position)
        
        if distance_to_waypoint < 2.0:  # 2 meter threshold
            print(f"✅ Reached waypoint {self.current_waypoint_index + 1}: {current_waypoint.semantic_label}")
            self.current_waypoint_index += 1
            
            # Check if mission complete
            if self.current_waypoint_index >= len(self.mission_waypoints):
                self.current_phase = MissionPhase.LANDING
                return current_state.position
            
            current_waypoint = self.mission_waypoints[self.current_waypoint_index]
        
        # Semantic reasoning for waypoint approach
        goal = self._apply_semantic_reasoning(current_waypoint, current_state)
        
        print(f"🎯 Navigating to waypoint {self.current_waypoint_index + 1}: {current_waypoint.semantic_label}")
        return goal
    
    def _plan_landing_goal(self, current_state: DroneState) -> np.ndarray:
        """Plan safe landing sequence"""
        # Gradual descent
        landing_goal = current_state.position.copy()
        landing_goal[2] = max(0.5, current_state.position[2] - 1.0)  # Descend 1m/s
        
        if current_state.position[2] <= 1.0:
            print("🛬 Landing sequence complete")
            # Mission complete
        
        return landing_goal
    
    def _plan_emergency_goal(self, current_state: DroneState) -> np.ndarray:
        """Plan emergency response (immediate safe landing)"""
        emergency_goal = current_state.position.copy()
        emergency_goal[2] = max(0.0, current_state.position[2] - 2.0)  # Fast descent
        print("🚨 Emergency landing!")
        return emergency_goal
    
    def _apply_semantic_reasoning(self, waypoint: SemanticWaypoint, current_state: DroneState) -> np.ndarray:
        """Apply semantic understanding to waypoint approach"""
        
        base_goal = waypoint.position.copy()
        
        # Semantic-aware adjustments
        if waypoint.semantic_label == "obstacle":
            # Approach with extra safety margin
            direction = current_state.position - base_goal
            direction_norm = np.linalg.norm(direction)
            if direction_norm > 0:
                direction = direction / direction_norm
                base_goal += direction * self.config.safety_margin
        
        elif waypoint.semantic_label == "landing_pad":
            # Approach from above
            base_goal[2] = max(base_goal[2] + 3.0, current_state.position[2])
        
        elif waypoint.semantic_label == "doorway":
            # Precise positioning for narrow passages
            base_goal[2] = waypoint.position[2]  # Maintain exact height
        
        return base_goal
    
    def _update_neural_scene(self, current_state: DroneState):
        """Update neural scene representation (NeRF/3DGS integration point)"""
        if self.neural_scene_model is None or self.uncertainty_field is None:
            return
        
        # Initialize scene if not already done
        if not self.neural_scene_model.is_initialized:
            initial_data = SensorData(
                rgb_images=[],  # Would contain actual camera images
                timestamp=time.time()
            )
            self.neural_scene_model.initialize_scene(initial_data)
            print("🧠 Neural scene model initialized")
        
        # Simulate incremental scene updates
        sensor_data = SensorData(
            rgb_images=[],  # Would contain actual camera images
            timestamp=time.time()
        )
        
        update_stats = self.neural_scene_model.incremental_update(sensor_data)
        
        # Update uncertainty field around current position
        if self.uncertainty_field:
            self.uncertainty_field.reduce_uncertainty_around_position(
                current_state.position, radius=3.0, reduction_factor=0.2
            )
        
        # Log updates periodically
        scene_stats = self.neural_scene_model.get_scene_statistics()
        if scene_stats['total_updates'] % 10 == 0:
            print(f"🧠 Neural scene updated (update #{scene_stats['total_updates']})")
    
    def _update_uncertainty_awareness(self, current_state: DroneState):
        """Update uncertainty maps for exploration planning"""
        
        # Simulate uncertainty reduction around current position
        current_pos = current_state.position
        
        # Remove uncertainty regions that have been explored
        self.high_uncertainty_regions = [
            region for region in self.high_uncertainty_regions
            if np.linalg.norm(region - current_pos) > 5.0  # 5m exploration radius
        ]
        
        # Add new uncertain regions (simulated)
        if len(self.high_uncertainty_regions) < 3 and np.random.random() < 0.1:
            new_uncertain_region = current_pos + np.random.uniform(-20, 20, 3)
            new_uncertain_region[2] = max(2.0, new_uncertain_region[2])  # Keep above ground
            self.high_uncertainty_regions.append(new_uncertain_region)
            print(f"❓ New uncertain region detected at {new_uncertain_region}")
    
    def _coordinate_with_other_agents(self, current_state: DroneState):
        """Coordinate with other agents for collaborative mapping"""
        # Placeholder for multi-agent coordination
        # This would integrate with communication protocols for shared NeRF building
        pass
    
    def _check_phase_transitions(self, current_state: DroneState):
        """Check and execute mission phase transitions"""
        
        # Emergency conditions
        if current_state.position[2] < 0.5:  # Too low
            if self.current_phase != MissionPhase.LANDING:
                print("🚨 Emergency: Altitude too low!")
                self.current_phase = MissionPhase.EMERGENCY
                return
        
        # Normal phase transitions are handled in individual planning functions
    
    def _get_region_uncertainty(self, region: np.ndarray) -> float:
        """Get uncertainty value for a region (placeholder)"""
        # This would query the actual neural scene uncertainty field
        return np.random.random()  # Placeholder
    
    def get_mission_status(self) -> Dict[str, Any]:
        """Get comprehensive mission status"""
        # Get neural scene updates from scene statistics
        neural_scene_updates = 0
        if self.neural_scene_model:
            scene_stats = self.neural_scene_model.get_scene_statistics()
            neural_scene_updates = scene_stats.get('total_updates', 0)
        
        return {
            'current_phase': self.current_phase.value,
            'waypoint_progress': f"{self.current_waypoint_index}/{len(self.mission_waypoints)}",
            'neural_scene_updates': neural_scene_updates,
            'uncertainty_regions': len(self.high_uncertainty_regions),
            'explored_regions': len(self.explored_regions),
            'planning_history_length': len(self.planning_history)
        } 