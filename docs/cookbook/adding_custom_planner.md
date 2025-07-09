# Adding a Custom Planner

This guide walks you through creating a custom planning algorithm for DART-Planner.

## Prerequisites

- Basic understanding of Python and object-oriented programming
- Familiarity with the DART-Planner architecture
- Development environment set up (see [Development Setup](development_setup.md))

## Overview

DART-Planner uses a plugin architecture for planners. All planners inherit from `BasePlanner` and implement a standard interface. This allows you to create custom planning algorithms while maintaining compatibility with the rest of the system.

## Step 1: Understand the Base Planner Interface

First, let's look at the base planner interface:

```python
from abc import ABC, abstractmethod
from typing import Optional, List
import numpy as np

from src.common.types import DroneState, Trajectory, PlanningResult

class BasePlanner(ABC):
    """Base class for all planners in DART-Planner."""
    
    @abstractmethod
    def plan_trajectory(
        self,
        current_state: DroneState,
        goal_state: DroneState,
        obstacles: Optional[List[np.ndarray]] = None,
        constraints: Optional[dict] = None
    ) -> PlanningResult:
        """
        Plan a trajectory from current state to goal state.
        
        Args:
            current_state: Current drone state
            goal_state: Desired goal state
            obstacles: List of obstacle positions (optional)
            constraints: Planning constraints (optional)
            
        Returns:
            PlanningResult containing the planned trajectory
        """
        pass
    
    @abstractmethod
    def is_feasible(self, trajectory: Trajectory) -> bool:
        """Check if a trajectory is feasible."""
        pass
    
    @abstractmethod
    def get_planning_time(self) -> float:
        """Get the time taken for the last planning operation."""
        pass
```

## Step 2: Create Your Custom Planner

Create a new file `src/planning/custom_planner.py`:

```python
import numpy as np
from typing import Optional, List
import time

from src.planning.base_planner import BasePlanner
from src.common.types import DroneState, Trajectory, PlanningResult, TrajectoryPoint

class CustomPlanner(BasePlanner):
    """
    A custom planning algorithm for DART-Planner.
    
    This example implements a simple straight-line planner with obstacle avoidance.
    """
    
    def __init__(self, max_velocity: float = 5.0, safety_margin: float = 1.0):
        """
        Initialize the custom planner.
        
        Args:
            max_velocity: Maximum velocity in m/s
            safety_margin: Safety margin around obstacles in meters
        """
        self.max_velocity = max_velocity
        self.safety_margin = safety_margin
        self.last_planning_time = 0.0
        
    def plan_trajectory(
        self,
        current_state: DroneState,
        goal_state: DroneState,
        obstacles: Optional[List[np.ndarray]] = None,
        constraints: Optional[dict] = None
    ) -> PlanningResult:
        """Plan a trajectory using the custom algorithm."""
        start_time = time.time()
        
        # Extract positions
        start_pos = current_state.position
        goal_pos = goal_state.position
        
        # Simple straight-line planning with obstacle avoidance
        trajectory = self._plan_straight_line_with_obstacles(
            start_pos, goal_pos, obstacles or []
        )
        
        # Record planning time
        self.last_planning_time = time.time() - start_time
        
        # Create planning result
        result = PlanningResult(
            trajectory=trajectory,
            success=True,
            planning_time=self.last_planning_time,
            message="Custom planner completed successfully"
        )
        
        return result
    
    def _plan_straight_line_with_obstacles(
        self,
        start_pos: np.ndarray,
        goal_pos: np.ndarray,
        obstacles: List[np.ndarray]
    ) -> Trajectory:
        """Plan a straight-line trajectory avoiding obstacles."""
        
        # Calculate distance and direction
        direction = goal_pos - start_pos
        distance = np.linalg.norm(direction)
        
        if distance == 0:
            # Already at goal
            return Trajectory(points=[TrajectoryPoint(
                position=start_pos,
                velocity=np.zeros(3),
                acceleration=np.zeros(3),
                time=0.0
            )])
        
        # Normalize direction
        direction = direction / distance
        
        # Check for obstacles along the path
        if self._path_has_obstacles(start_pos, goal_pos, obstacles):
            # Use waypoint-based obstacle avoidance
            waypoints = self._generate_waypoints_around_obstacles(
                start_pos, goal_pos, obstacles
            )
            return self._plan_through_waypoints(waypoints)
        else:
            # Direct path is clear
            return self._plan_straight_line(start_pos, goal_pos)
    
    def _path_has_obstacles(
        self,
        start_pos: np.ndarray,
        goal_pos: np.ndarray,
        obstacles: List[np.ndarray]
    ) -> bool:
        """Check if there are obstacles along the path."""
        for obstacle in obstacles:
            # Simple line-sphere intersection test
            if self._line_sphere_intersection(start_pos, goal_pos, obstacle, self.safety_margin):
                return True
        return False
    
    def _line_sphere_intersection(
        self,
        line_start: np.ndarray,
        line_end: np.ndarray,
        sphere_center: np.ndarray,
        sphere_radius: float
    ) -> bool:
        """Check if a line intersects with a sphere."""
        # Vector from line start to sphere center
        v = sphere_center - line_start
        
        # Line direction
        d = line_end - line_start
        line_length = np.linalg.norm(d)
        d = d / line_length
        
        # Projection of v onto d
        t = np.dot(v, d)
        
        # Closest point on line to sphere center
        closest_point = line_start + t * d
        
        # Check if closest point is within line segment
        if t < 0 or t > line_length:
            return False
        
        # Check distance to sphere center
        distance = np.linalg.norm(closest_point - sphere_center)
        return distance <= sphere_radius
    
    def _generate_waypoints_around_obstacles(
        self,
        start_pos: np.ndarray,
        goal_pos: np.ndarray,
        obstacles: List[np.ndarray]
    ) -> List[np.ndarray]:
        """Generate waypoints to avoid obstacles."""
        # Simple implementation: add waypoints above obstacles
        waypoints = [start_pos]
        
        for obstacle in obstacles:
            # Add waypoint above the obstacle
            waypoint = obstacle.copy()
            waypoint[2] += self.safety_margin + 2.0  # 2m above obstacle
            waypoints.append(waypoint)
        
        waypoints.append(goal_pos)
        return waypoints
    
    def _plan_through_waypoints(self, waypoints: List[np.ndarray]) -> Trajectory:
        """Plan a trajectory through multiple waypoints."""
        trajectory_points = []
        current_time = 0.0
        
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            
            # Plan segment between waypoints
            segment = self._plan_straight_line(start, end)
            
            # Adjust timestamps
            for point in segment.points:
                point.time += current_time
                trajectory_points.append(point)
            
            # Update current time
            if segment.points:
                current_time = segment.points[-1].time
        
        return Trajectory(points=trajectory_points)
    
    def _plan_straight_line(self, start_pos: np.ndarray, goal_pos: np.ndarray) -> Trajectory:
        """Plan a simple straight-line trajectory."""
        distance = np.linalg.norm(goal_pos - start_pos)
        duration = distance / self.max_velocity
        
        # Generate trajectory points
        num_points = max(10, int(duration * 10))  # 10 Hz minimum
        points = []
        
        for i in range(num_points):
            t = i / (num_points - 1)
            time = t * duration
            
            # Linear interpolation
            position = start_pos + t * (goal_pos - start_pos)
            velocity = (goal_pos - start_pos) / duration
            acceleration = np.zeros(3)
            
            point = TrajectoryPoint(
                position=position,
                velocity=velocity,
                acceleration=acceleration,
                time=time
            )
            points.append(point)
        
        return Trajectory(points=points)
    
    def is_feasible(self, trajectory: Trajectory) -> bool:
        """Check if the trajectory is feasible."""
        if not trajectory.points:
            return False
        
        # Check velocity limits
        for point in trajectory.points:
            velocity_magnitude = np.linalg.norm(point.velocity)
            if velocity_magnitude > self.max_velocity:
                return False
        
        return True
    
    def get_planning_time(self) -> float:
        """Get the time taken for the last planning operation."""
        return self.last_planning_time
```

## Step 3: Register Your Planner

To use your custom planner, you need to register it in the dependency injection container. Create or update your configuration:

```python
from src.common.di_container_v2 import create_container
from src.planning.custom_planner import CustomPlanner

# Create container
builder = create_container()

# Register your custom planner
builder.runtime_stage().register_service(
    CustomPlanner,  # Interface (use BasePlanner if you want to replace the default)
    CustomPlanner   # Implementation
).done()

# Build the container
container = builder.build()
```

## Step 4: Test Your Planner

Create a test file `tests/planning/test_custom_planner.py`:

```python
import pytest
import numpy as np
from src.planning.custom_planner import CustomPlanner
from src.common.types import DroneState

class TestCustomPlanner:
    
    def setup_method(self):
        """Set up test fixtures."""
        self.planner = CustomPlanner(max_velocity=5.0, safety_margin=1.0)
        
        # Create test states
        self.start_state = DroneState(
            position=np.array([0.0, 0.0, 0.0]),
            velocity=np.zeros(3),
            attitude=np.zeros(3),
            angular_velocity=np.zeros(3)
        )
        
        self.goal_state = DroneState(
            position=np.array([10.0, 0.0, 5.0]),
            velocity=np.zeros(3),
            attitude=np.zeros(3),
            angular_velocity=np.zeros(3)
        )
    
    def test_basic_planning(self):
        """Test basic trajectory planning."""
        result = self.planner.plan_trajectory(self.start_state, self.goal_state)
        
        assert result.success
        assert result.trajectory is not None
        assert len(result.trajectory.points) > 0
        assert result.planning_time > 0
    
    def test_obstacle_avoidance(self):
        """Test obstacle avoidance."""
        obstacles = [np.array([5.0, 0.0, 2.0])]  # Obstacle in the middle
        
        result = self.planner.plan_trajectory(
            self.start_state, self.goal_state, obstacles
        )
        
        assert result.success
        assert result.trajectory is not None
        
        # Check that trajectory avoids the obstacle
        for point in result.trajectory.points:
            distance_to_obstacle = np.linalg.norm(point.position - obstacles[0])
            assert distance_to_obstacle > self.planner.safety_margin
    
    def test_feasibility_check(self):
        """Test trajectory feasibility checking."""
        result = self.planner.plan_trajectory(self.start_state, self.goal_state)
        
        assert self.planner.is_feasible(result.trajectory)
    
    def test_planning_time(self):
        """Test planning time measurement."""
        result = self.planner.plan_trajectory(self.start_state, self.goal_state)
        
        assert result.planning_time > 0
        assert result.planning_time == self.planner.get_planning_time()
```

## Step 5: Integration Testing

Test your planner with the full system:

```python
from src.control.geometric_controller import GeometricController
from src.hardware.airsim_interface import AirSimInterface
from src.planning.custom_planner import CustomPlanner

def test_custom_planner_integration():
    """Test custom planner with the full system."""
    
    # Initialize components
    controller = GeometricController()
    planner = CustomPlanner()
    airsim = AirSimInterface()
    
    # Create a simple mission
    start_state = airsim.get_drone_state()
    goal_state = DroneState(
        position=start_state.position + np.array([10.0, 0.0, 5.0]),
        velocity=np.zeros(3),
        attitude=np.zeros(3),
        angular_velocity=np.zeros(3)
    )
    
    # Plan and execute
    result = planner.plan_trajectory(start_state, goal_state)
    assert result.success
    
    # Execute the trajectory
    for point in result.trajectory.points:
        control_cmd = controller.compute_control(start_state, point)
        airsim.send_control_command(control_cmd)
```

## Verification Steps

1. **Run unit tests**: `pytest tests/planning/test_custom_planner.py -v`
2. **Check code quality**: `pre-commit run --all-files`
3. **Test integration**: Run the integration test above
4. **Performance test**: Ensure planning time is within acceptable limits

## Troubleshooting

### Common Issues

1. **Import errors**: Make sure your planner is in the correct directory structure
2. **Type errors**: Ensure your planner implements all abstract methods
3. **Performance issues**: Profile your planning algorithm and optimize bottlenecks
4. **Integration failures**: Check that your planner returns valid `PlanningResult` objects

### Performance Optimization

- Use efficient data structures (NumPy arrays)
- Implement early termination for infeasible cases
- Cache intermediate results when possible
- Profile with `cProfile` to identify bottlenecks

## Next Steps

- Add more sophisticated obstacle avoidance algorithms
- Implement different planning strategies (RRT, A*, etc.)
- Add support for dynamic obstacles
- Optimize for real-time performance

## Related Documentation

- [Base Planner API](../api/planning/base_planner.rst)
- [Planning System Overview](../api/planning/index.rst)
- [Trajectory Types](../api/common/types.rst)
- [Dependency Injection](../api/common/di_container_v2.rst) 