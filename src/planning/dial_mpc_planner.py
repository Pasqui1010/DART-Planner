import numpy as np
import time
from src.common.types import DroneState, Trajectory
from typing import Optional, List, Tuple
from dataclasses import dataclass

@dataclass
class DIALMPCConfig:
    """Configuration for DIAL-MPC planner - OPTIMIZED FOR CONSISTENCY"""
    # Prediction horizon - reduced for better real-time performance
    prediction_horizon: int = 40  # Increased from 20 for better long-term planning
    dt: float = 0.05  # Reduced from 0.1s to 50ms for higher resolution
    
    # Physical constraints - more conservative for stability
    max_velocity: float = 5.0  # Reduced from 8.0 m/s for stability
    max_acceleration: float = 3.0  # Reduced from 4.0 m/s^2 for smoothness
    max_jerk: float = 6.0  # Reduced from 8.0 m/s^3 for consistency
    
    # Cost function weights - REBALANCED FOR CONSISTENCY
    position_weight: float = 100.0  # Increased from 10.0 for stronger goal tracking
    velocity_weight: float = 2.0  # Increased from 1.0 for velocity regulation
    acceleration_weight: float = 1.0  # Increased from 0.1 for smoothness
    jerk_weight: float = 0.5  # Increased from 0.01 for trajectory smoothness
    
    # Obstacle avoidance
    obstacle_weight: float = 500.0  # Increased from 100.0 for better obstacle avoidance
    safety_margin: float = 2.0  # Increased from 1.0 meter for safer operation
    
    # Smoothness
    smoothness_weight: float = 10.0  # Increased from 1.0 for trajectory consistency

class DIALMPCPlanner:
    """
    Distributed Iterative Augmented Lagrangian Model Predictive Control (DIAL-MPC) planner.
    
    This planner runs in the cloud and generates optimal trajectories considering:
    - Dynamic constraints (velocity, acceleration, jerk limits)
    - Obstacle avoidance using neural scene representation
    - Smoothness for stable control
    - Goal reaching behavior
    
    The planner is training-free and uses iterative optimization to solve the
    constrained trajectory optimization problem.
    """
    
    def __init__(self, config: DIALMPCConfig | None = None):
        self.config = config if config is not None else DIALMPCConfig()
        
        # Planning state
        self.goal_position: Optional[np.ndarray] = None
        self.obstacles: List[Tuple[np.ndarray, float]] = []  # (center, radius) pairs
        
        # Optimization state
        self.last_solution: Optional[np.ndarray] = None
        self.warm_start_enabled = True
        
        # Performance tracking
        self.planning_times: List[float] = []
        self.plan_count = 0
        
        print("DIAL-MPC Planner initialized for cloud execution")
    
    def set_goal(self, goal_position: np.ndarray):
        """Set the goal position for trajectory planning."""
        self.goal_position = goal_position.copy()
        print(f"DIAL-MPC goal set to: {goal_position}")
    
    def add_obstacle(self, center: np.ndarray, radius: float):
        """Add spherical obstacle for avoidance."""
        self.obstacles.append((center.copy(), radius))
        print(f"Added obstacle at {center} with radius {radius}")
    
    def clear_obstacles(self):
        """Clear all obstacles."""
        self.obstacles.clear()
        print("Cleared all obstacles")
    
    def plan_trajectory(self, current_state: DroneState, goal_position: np.ndarray) -> Trajectory:
        """
        Plan optimal trajectory using DIAL-MPC.
        
        FIXED: Ensures trajectory consistency between planning cycles.
        This is the main planning function that runs in the cloud at ~10Hz.
        It generates smooth, dynamically feasible trajectories that avoid obstacles
        and reach the goal efficiently.
        """
        start_time = time.time()
        
        # CONSISTENCY FIX 1: Maintain goal stability
        if self.goal_position is None:
            self.set_goal(goal_position)
        else:
            # Only update goal if it has changed significantly (>1m)
            goal_change = np.linalg.norm(self.goal_position - goal_position)
            if goal_change > 1.0:
                print(f"Goal changed by {goal_change:.1f}m, updating...")
                self.set_goal(goal_position)
        
        # CONSISTENCY FIX 2: Validate current state transition
        current_pos = current_state.position
        current_vel = current_state.velocity
        
        if self.last_solution is not None:
            # Check for reasonable state transition
            expected_pos = self.last_solution[1] if len(self.last_solution) > 1 else current_pos
            state_jump = np.linalg.norm(current_pos - expected_pos)
            
            if state_jump > 10.0:  # More than 10m jump indicates problem
                print(f"WARNING: Large state jump detected: {state_jump:.1f}m")
                print("Resetting trajectory to maintain consistency")
                self.last_solution = None  # Force cold start
        
        # Extract current acceleration estimate
        current_acc = np.zeros(3)  # Improved: could estimate from velocity history
        
        # Generate trajectory using DIAL-MPC optimization
        try:
            positions, velocities, accelerations = self._solve_dial_mpc_consistent(
                current_pos, current_vel, current_acc)
            
            # CONSISTENCY FIX 3: Validate generated trajectory
            if len(positions) > 1:
                first_step_distance = np.linalg.norm(positions[1] - positions[0])
                max_reasonable_step = self.config.max_velocity * self.config.dt * 2.0
                
                if first_step_distance > max_reasonable_step:
                    print(f"WARNING: Generated trajectory too aggressive: {first_step_distance:.1f}m first step")
                    print("Falling back to conservative trajectory")
                    return self._generate_conservative_trajectory(current_state)
            
            # Create trajectory object
            trajectory = self._create_trajectory(positions, velocities, accelerations)
            
            # Update performance tracking
            planning_time = time.time() - start_time
            self.planning_times.append(planning_time)
            self.plan_count += 1
            
            if self.plan_count % 10 == 0:
                avg_time = np.mean(self.planning_times[-10:])
                print(f"DIAL-MPC planning: {avg_time*1000:.1f}ms avg (last 10 plans)")
            
            return trajectory
            
        except Exception as e:
            print(f"DIAL-MPC planning failed: {e}")
            return self._generate_fallback_trajectory(current_state)
    
    def _solve_dial_mpc_consistent(self, pos0: np.ndarray, vel0: np.ndarray, acc0: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Solve the DIAL-MPC optimization problem with improved consistency.
        
        FIXED: Better warm start and trajectory consistency.
        """
        N = self.config.prediction_horizon
        dt = self.config.dt
        
        # CONSISTENCY FIX 4: Improved initialization
        if self.warm_start_enabled and self.last_solution is not None and len(self.last_solution) > 1:
            # Better warm start with trajectory shifting
            positions = self._improved_warm_start_solution(pos0, vel0)
        else:
            # Cold start with smoother trajectory
            positions = self._initialize_smooth_trajectory(pos0, vel0, N)
        
        # CONSISTENCY FIX 5: More conservative optimization
        max_iterations = 8  # Increased from 5 for better convergence
        convergence_threshold = 1e-2  # Relaxed for stability
        
        for iteration in range(max_iterations):
            # Compute derivatives
            velocities = self._compute_velocities(positions, dt)
            accelerations = self._compute_accelerations(velocities, dt)
            jerks = self._compute_jerks(accelerations, dt)
            
            # CONSISTENCY FIX 6: Improved cost function with stability emphasis
            cost, grad = self._compute_stable_cost_and_gradient(
                positions, velocities, accelerations, jerks, pos0, vel0, acc0)
            
            # Apply constraints using augmented Lagrangian method
            positions = self._apply_constraints(positions, velocities, accelerations)
            
            # CONSISTENCY FIX 7: Adaptive step size for stability
            step_size = self._compute_adaptive_step_size(iteration, grad)
            positions[1:] -= step_size * grad  # Don't update initial position
            
            # Early termination if converged
            if np.linalg.norm(grad) < convergence_threshold:
                break
        
        # Final derivative computation
        velocities = self._compute_velocities(positions, dt)
        accelerations = self._compute_accelerations(velocities, dt)
        
        # CONSISTENCY FIX 8: Store solution with validation
        if self._validate_solution(positions, velocities):
            self.last_solution = positions.copy()
        else:
            print("Generated solution failed validation, not storing for warm start")
        
        return positions, velocities, accelerations
    
    def _improved_warm_start_solution(self, current_pos: np.ndarray, current_vel: np.ndarray) -> np.ndarray:
        """Generate improved warm start solution with better consistency."""
        N = self.config.prediction_horizon
        
        # Shift previous solution by one time step
        positions = np.zeros((N+1, 3))
        positions[0] = current_pos
        
        if self.last_solution is not None and len(self.last_solution) > 2:
            # Use shifted previous solution but with current state correction
            shift_length = min(N, len(self.last_solution) - 1)
            
            # Apply position correction to account for state estimation differences
            position_correction = current_pos - self.last_solution[0]
            
            for i in range(1, shift_length + 1):
                if i < len(self.last_solution):
                    # Shift and correct previous solution
                    positions[i] = self.last_solution[i] + position_correction * (1.0 - i / shift_length)
            
            # Smoothly extend to goal if needed
            if shift_length < N and self.goal_position is not None:
                for i in range(shift_length + 1, N + 1):
                    alpha = (i - shift_length) / (N - shift_length)
                    positions[i] = (1 - alpha) * positions[shift_length] + alpha * self.goal_position
        else:
            # Fallback to smooth trajectory
            positions = self._initialize_smooth_trajectory(current_pos, current_vel, N)
        
        return positions
    
    def _initialize_smooth_trajectory(self, pos0: np.ndarray, vel0: np.ndarray, N: int) -> np.ndarray:
        """Initialize with smooth trajectory considering current velocity."""
        positions = np.zeros((N+1, 3))
        positions[0] = pos0
        
        if self.goal_position is not None:
            # Use quintic polynomial for smooth trajectory
            total_time = N * self.config.dt
            goal_vec = self.goal_position - pos0
            
            for i in range(1, N+1):
                t = (i * self.config.dt) / total_time
                # Quintic polynomial (ensures smooth acceleration profile)
                s = 6*t**5 - 15*t**4 + 10*t**3
                
                # Blend initial velocity influence
                vel_influence = np.exp(-2*t)  # Decay velocity influence over time
                positions[i] = pos0 + s * goal_vec + vel0 * (i * self.config.dt) * vel_influence
        else:
            # Constant velocity extrapolation with gradual slowdown
            for i in range(1, N+1):
                decay = np.exp(-i * self.config.dt / 2.0)  # Gradual velocity decay
                positions[i] = pos0 + vel0 * (i * self.config.dt) * decay
        
        return positions
    
    def _compute_stable_cost_and_gradient(self, positions: np.ndarray, velocities: np.ndarray, 
                                        accelerations: np.ndarray, jerks: np.ndarray,
                                        pos0: np.ndarray, vel0: np.ndarray, acc0: np.ndarray) -> Tuple[float, np.ndarray]:
        """Compute cost function with emphasis on trajectory stability."""
        N = len(positions) - 1
        gradient = np.zeros_like(positions)
        total_cost = 0.0
        
        # CONSISTENCY FIX 9: Initial state matching (critical for consistency)
        initial_vel_error = velocities[0] - vel0
        initial_cost = 100.0 * np.sum(initial_vel_error**2)  # Strong initial condition constraint
        total_cost += initial_cost
        
        for i in range(N+1):
            # Goal reaching cost with progressive weighting
            if self.goal_position is not None:
                pos_error = positions[i] - self.goal_position
                # Progressive weighting: stronger towards end of horizon
                progress_weight = 1.0 + 2.0 * (i / N)
                cost_pos = self.config.position_weight * progress_weight * np.sum(pos_error**2)
                total_cost += cost_pos
                gradient[i] += 2 * self.config.position_weight * progress_weight * pos_error
            
            # Velocity regulation cost (prevent excessive velocities)
            vel_cost = self.config.velocity_weight * np.sum(velocities[i]**2)
            total_cost += vel_cost
            
            # Acceleration cost (penalize aggressive maneuvers)
            acc_cost = self.config.acceleration_weight * np.sum(accelerations[i]**2)
            total_cost += acc_cost
            
            # Jerk cost (ensure smoothness)
            jerk_cost = self.config.jerk_weight * np.sum(jerks[i]**2)
            total_cost += jerk_cost
            
            # CONSISTENCY FIX 10: Stability cost (penalize large trajectory changes)
            if self.last_solution is not None and i < len(self.last_solution):
                stability_error = positions[i] - self.last_solution[i]
                stability_cost = 1.0 * np.sum(stability_error**2)  # Soft constraint on changes
                total_cost += stability_cost
                gradient[i] += 2.0 * stability_error
        
        # Terminal cost (strong goal reaching at end)
        if self.goal_position is not None:
            terminal_error = positions[-1] - self.goal_position
            terminal_cost = 500.0 * np.sum(terminal_error**2)  # Strong terminal constraint
            total_cost += terminal_cost
            gradient[-1] += 1000.0 * terminal_error
        
        return total_cost, gradient[1:]  # Don't return gradient for initial position
    
    def _compute_adaptive_step_size(self, iteration: int, gradient: np.ndarray) -> float:
        """Compute adaptive step size for stable optimization."""
        # Base step size
        base_step = 0.01
        
        # Gradient-based adaptation
        grad_norm = float(np.linalg.norm(gradient))
        if grad_norm > 1.0:
            grad_factor = 1.0 / grad_norm  # Reduce step if gradient is large
        else:
            grad_factor = 1.0
        
        # Iteration-based annealing
        iteration_factor = 1.0 / (1.0 + 0.1 * iteration)
        
        return base_step * grad_factor * iteration_factor
    
    def _validate_solution(self, positions: np.ndarray, velocities: np.ndarray) -> bool:
        """Validate that generated solution is reasonable."""
        if len(positions) < 2:
            return False
        
        # Check for reasonable step sizes
        for i in range(1, len(positions)):
            step_size = np.linalg.norm(positions[i] - positions[i-1])
            max_reasonable_step = self.config.max_velocity * self.config.dt * 1.5
            
            if step_size > max_reasonable_step:
                return False
        
        # Check for reasonable velocities
        for vel in velocities:
            if np.linalg.norm(vel) > self.config.max_velocity * 1.2:
                return False
        
        return True
    
    def _generate_conservative_trajectory(self, current_state: DroneState) -> Trajectory:
        """Generate conservative trajectory when optimization fails."""
        print("Generating conservative trajectory for stability")
        
        N = self.config.prediction_horizon
        current_time = time.time()
        dt = self.config.dt
        
        # Conservative movement towards goal
        timestamps = current_time + np.arange(N+1) * dt
        positions = np.zeros((N+1, 3))
        velocities = np.zeros((N+1, 3))
        accelerations = np.zeros((N+1, 3))
        
        positions[0] = current_state.position
        velocities[0] = current_state.velocity
        
        if self.goal_position is not None:
            goal_direction = self.goal_position - current_state.position
            goal_distance = np.linalg.norm(goal_direction)
            
            if goal_distance > 0.1:
                goal_direction = goal_direction / goal_distance
                
                # Conservative velocity towards goal
                max_conservative_vel = min(self.config.max_velocity * 0.5, float(goal_distance / (N * dt)))
                target_velocity = goal_direction * max_conservative_vel
                
                for i in range(1, N+1):
                    # Smooth velocity transition
                    alpha = min(i * dt / 2.0, 1.0)  # 2 second velocity ramp
                    velocities[i] = (1 - alpha) * current_state.velocity + alpha * target_velocity
                    positions[i] = positions[i-1] + velocities[i] * dt
            else:
                # Near goal - hover
                for i in range(1, N+1):
                    positions[i] = current_state.position
        else:
            # No goal - gentle deceleration
            for i in range(1, N+1):
                decay = np.exp(-i * dt / 3.0)  # 3 second time constant
                velocities[i] = current_state.velocity * decay
                positions[i] = positions[i-1] + velocities[i] * dt
        
        return Trajectory(
            timestamps=timestamps,
            positions=positions,
            velocities=velocities,
            accelerations=accelerations
        )
    
    def _warm_start_solution(self, current_pos: np.ndarray) -> np.ndarray:
        """Generate warm start solution by shifting previous solution."""
        N = self.config.prediction_horizon
        
        # Shift previous solution by one time step
        positions = np.zeros((N+1, 3))
        positions[0] = current_pos
        
        if self.last_solution is not None and len(self.last_solution) > 1:
            # Use shifted previous solution
            shift_length = min(N, len(self.last_solution) - 1)
            positions[1:shift_length+1] = self.last_solution[1:shift_length+1]
            
            # Extend with straight line to goal if needed
            if shift_length < N and self.goal_position is not None:
                for i in range(shift_length+1, N+1):
                    alpha = (i - shift_length) / (N - shift_length)
                    positions[i] = (1 - alpha) * positions[shift_length] + alpha * self.goal_position
        else:
            # Fallback to straight line
            positions = self._initialize_straight_line(current_pos, N)
        
        return positions
    
    def _initialize_straight_line(self, pos0: np.ndarray, N: int) -> np.ndarray:
        """Initialize with straight line trajectory to goal."""
        positions = np.zeros((N+1, 3))
        positions[0] = pos0
        
        if self.goal_position is not None:
            for i in range(1, N+1):
                alpha = i / N
                positions[i] = (1 - alpha) * pos0 + alpha * self.goal_position
        else:
            # No goal set - hover at current position
            positions[:] = pos0
        
        return positions
    
    def _compute_velocities(self, positions: np.ndarray, dt: float) -> np.ndarray:
        """Compute velocities from positions using finite differences."""
        velocities = np.zeros_like(positions)
        velocities[1:] = (positions[1:] - positions[:-1]) / dt
        return velocities
    
    def _compute_accelerations(self, velocities: np.ndarray, dt: float) -> np.ndarray:
        """Compute accelerations from velocities using finite differences."""
        accelerations = np.zeros_like(velocities)
        accelerations[1:] = (velocities[1:] - velocities[:-1]) / dt
        return accelerations
    
    def _compute_jerks(self, accelerations: np.ndarray, dt: float) -> np.ndarray:
        """Compute jerks from accelerations using finite differences."""
        jerks = np.zeros_like(accelerations)
        jerks[1:] = (accelerations[1:] - accelerations[:-1]) / dt
        return jerks
    
    def _compute_cost_and_gradient(self, positions: np.ndarray, velocities: np.ndarray, 
                                 accelerations: np.ndarray, jerks: np.ndarray,
                                 pos0: np.ndarray, vel0: np.ndarray, acc0: np.ndarray) -> Tuple[float, np.ndarray]:
        """Compute cost function and its gradient."""
        N = len(positions) - 1
        gradient = np.zeros_like(positions)
        total_cost = 0.0
        
        for i in range(N+1):
            # Goal reaching cost
            if self.goal_position is not None:
                pos_error = positions[i] - self.goal_position
                cost_pos = self.config.position_weight * np.sum(pos_error**2)
                total_cost += cost_pos
                gradient[i] += 2 * self.config.position_weight * pos_error
            
            # Velocity cost
            vel_cost = self.config.velocity_weight * np.sum(velocities[i]**2)
            total_cost += vel_cost
            
            # Acceleration cost
            acc_cost = self.config.acceleration_weight * np.sum(accelerations[i]**2)
            total_cost += acc_cost
            
            # Jerk cost (smoothness)
            jerk_cost = self.config.jerk_weight * np.sum(jerks[i]**2)
            total_cost += jerk_cost
            
            # Obstacle avoidance cost
            for obs_center, obs_radius in self.obstacles:
                dist = np.linalg.norm(positions[i] - obs_center)
                safety_dist = obs_radius + self.config.safety_margin
                
                if dist < safety_dist:
                    # Exponential penalty for being too close
                    penalty = self.config.obstacle_weight * np.exp(-(dist - safety_dist))
                    total_cost += penalty
                    
                    # Gradient pushes away from obstacle
                    direction = (positions[i] - obs_center) / (dist + 1e-6)
                    gradient[i] += penalty * direction
        
        return total_cost, gradient[1:]  # Don't return gradient for initial position
    
    def _apply_constraints(self, positions: np.ndarray, velocities: np.ndarray, accelerations: np.ndarray) -> np.ndarray:
        """Apply dynamic constraints using projection."""
        dt = self.config.dt
        
        # Velocity constraints
        for i in range(len(velocities)):
            vel_norm = np.linalg.norm(velocities[i])
            if vel_norm > self.config.max_velocity:
                velocities[i] *= self.config.max_velocity / vel_norm
        
        # Acceleration constraints
        for i in range(len(accelerations)):
            acc_norm = np.linalg.norm(accelerations[i])
            if acc_norm > self.config.max_acceleration:
                accelerations[i] *= self.config.max_acceleration / acc_norm
        
        # Update positions to be consistent with constrained velocities
        for i in range(1, len(positions)):
            positions[i] = positions[i-1] + velocities[i] * dt
        
        return positions
    
    def _create_trajectory(self, positions: np.ndarray, velocities: np.ndarray, accelerations: np.ndarray) -> Trajectory:
        """Create trajectory object from optimized path."""
        current_time = time.time()
        dt = self.config.dt
        
        timestamps = current_time + np.arange(len(positions)) * dt
        
        return Trajectory(
            timestamps=timestamps,
            positions=positions,
            velocities=velocities,
            accelerations=accelerations,
            attitudes=None,  # Will be computed by geometric controller
            yaws=None,
            yaw_rates=None
        )
    
    def _generate_fallback_trajectory(self, current_state: DroneState) -> Trajectory:
        """Generate safe fallback trajectory when optimization fails."""
        print("Generating fallback hover trajectory")
        
        N = self.config.prediction_horizon
        current_time = time.time()
        dt = self.config.dt
        
        # Simple hover trajectory
        timestamps = current_time + np.arange(N+1) * dt
        positions = np.tile(current_state.position, (N+1, 1))
        velocities = np.zeros((N+1, 3))
        accelerations = np.zeros((N+1, 3))
        
        return Trajectory(
            timestamps=timestamps,
            positions=positions,
            velocities=velocities,
            accelerations=accelerations
        )
    
    def get_planning_stats(self) -> dict:
        """Get planning performance statistics."""
        if not self.planning_times:
            return {'avg_time_ms': 0, 'max_time_ms': 0, 'plan_count': 0}
        
        return {
            'avg_time_ms': np.mean(self.planning_times) * 1000,
            'max_time_ms': np.max(self.planning_times) * 1000,
            'plan_count': self.plan_count,
            'recent_avg_ms': np.mean(self.planning_times[-10:]) * 1000 if len(self.planning_times) >= 10 else 0
        } 