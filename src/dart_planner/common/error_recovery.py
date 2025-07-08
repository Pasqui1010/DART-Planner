"""
Error Recovery Strategies for DART-Planner

This module provides error recovery mechanisms including:
- Retry logic with exponential backoff
- Fallback mechanisms for critical failures
- Graceful degradation strategies
- Circuit breaker patterns
"""

import asyncio
import time
import logging
from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps
import threading
import contextvars

from dart_planner.common.errors import DARTPlannerError
from .errors import CommunicationError, HardwareError, PlanningError

T = TypeVar('T')
logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: tuple = (CommunicationError, HardwareError)
):
    """
    Decorator for retrying operations with exponential backoff.
    
    Args:
        config: Retry configuration
        retryable_exceptions: Tuple of exceptions that should trigger retries
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # Last attempt failed, re-raise
                        logger.error(f"Operation failed after {config.max_attempts} attempts: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    if config.jitter:
                        # Add jitter to prevent thundering herd
                        import secrets
                        jitter_factor = 0.5 + (secrets.token_bytes(1)[0] / 255.0) * 0.5
                        delay *= jitter_factor
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    # For synchronous functions, we must use time.sleep
                    # This is acceptable for error recovery scenarios
                    import time
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # Last attempt failed, re-raise
                        logger.error(f"Operation failed after {config.max_attempts} attempts: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    if config.jitter:
                        # Add jitter to prevent thundering herd
                        import secrets
                        jitter_factor = 0.5 + (secrets.token_bytes(1)[0] / 255.0) * 0.5
                        delay *= jitter_factor
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        # Return async wrapper if function is async, sync wrapper otherwise
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


class FallbackStrategy:
    """Base class for fallback strategies."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    def execute_fallback(self, *args, **kwargs) -> Any:
        """Execute the fallback strategy."""
        raise NotImplementedError("Subclasses must implement execute_fallback")


class HoverFallback(FallbackStrategy):
    """Fallback to hover when planning fails."""
    
    def __init__(self):
        super().__init__("HoverFallback")
    
    def execute_fallback(self, current_state, **kwargs):
        """Generate a hover trajectory at current position."""
        from ..common.types import Trajectory
        import numpy as np
        
        self.logger.warning("Planning failed, falling back to hover")
        
        # Create a simple hover trajectory
        hover_position = current_state.position.copy()
        hover_velocity = np.zeros(3)
        hover_acceleration = np.zeros(3)
        
        # Generate trajectory for next 5 seconds
        timestamps = np.array([time.time() + i * 0.1 for i in range(50)])  # 5s at 10Hz
        
        positions = np.tile(hover_position, (50, 1))
        velocities = np.tile(hover_velocity, (50, 1))
        accelerations = np.tile(hover_acceleration, (50, 1))
        
        return Trajectory(
            timestamps=timestamps,
            positions=positions,
            velocities=velocities,
            accelerations=accelerations
        )


class EmergencyStopFallback(FallbackStrategy):
    """Emergency stop fallback for critical failures."""
    
    def __init__(self):
        super().__init__("EmergencyStopFallback")
    
    def execute_fallback(self, current_state, **kwargs):
        """Execute emergency stop procedure."""
        self.logger.error("Critical failure detected, executing emergency stop")
        
        # This would typically trigger:
        # 1. Immediate disarm
        # 2. Emergency landing
        # 3. Safety system activation
        
        return {
            "action": "emergency_stop",
            "reason": "Critical system failure",
            "timestamp": time.time()
        }


class GracefulDegradation:
    """Manages graceful degradation of system functionality."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.degraded_features = set()
        self.fallback_strategies = {}
    
    def register_fallback(self, feature: str, strategy: FallbackStrategy):
        """Register a fallback strategy for a feature."""
        self.fallback_strategies[feature] = strategy
        self.logger.info(f"Registered fallback strategy for {feature}: {strategy.name}")
    
    def mark_feature_degraded(self, feature: str, reason: str):
        """Mark a feature as degraded."""
        self.degraded_features.add(feature)
        self.logger.warning(f"Feature {feature} marked as degraded: {reason}")
    
    def is_feature_degraded(self, feature: str) -> bool:
        """Check if a feature is degraded."""
        return feature in self.degraded_features
    
    def execute_fallback(self, feature: str, *args, **kwargs) -> Any:
        """Execute fallback for a degraded feature."""
        if feature not in self.fallback_strategies:
            raise DARTPlannerError(f"No fallback strategy registered for {feature}")
        
        strategy = self.fallback_strategies[feature]
        return strategy.execute_fallback(*args, **kwargs)
    
    def get_system_status(self) -> dict:
        """Get current system degradation status."""
        return {
            "degraded_features": list(self.degraded_features),
            "available_fallbacks": list(self.fallback_strategies.keys()),
            "total_features": len(self.fallback_strategies)
        }


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        self.logger = logging.getLogger(__name__)
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise DARTPlannerError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.logger.info("Circuit breaker reset to CLOSED")
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.error(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
    
    def get_status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


# Global graceful degradation manager
# _global_degradation_manager = GracefulDegradation()
_global_degradation_manager_ctx: contextvars.ContextVar = contextvars.ContextVar("_global_degradation_manager_ctx", default=None)
_global_degradation_manager_lock = threading.Lock()

def get_degradation_manager() -> GracefulDegradation:
    """Get the global graceful degradation manager."""
    manager = _global_degradation_manager_ctx.get()
    if manager is None:
        with _global_degradation_manager_lock:
            manager = _global_degradation_manager_ctx.get()
            if manager is None:
                manager = GracefulDegradation()
                _global_degradation_manager_ctx.set(manager)
    return manager


def register_planning_fallbacks():
    """Register fallback strategies for planning components."""
    manager = get_degradation_manager()
    
    # Register hover fallback for planning failures
    manager.register_fallback("trajectory_planning", HoverFallback())
    
    # Register emergency stop for critical failures
    manager.register_fallback("critical_system", EmergencyStopFallback())
    
    return manager 
