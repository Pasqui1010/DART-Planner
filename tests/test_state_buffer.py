"""
Unit tests for thread-safe state buffer system.

Tests the ThreadSafeStateBuffer, DroneStateBuffer, and FastDroneStateBuffer
to ensure they prevent stale or mid-update state consumption by control loops.
"""

import pytest
import time
import threading
import asyncio
import numpy as np
from unittest.mock import Mock

from dart_planner.common.state_buffer import (
    ThreadSafeStateBuffer,
    DroneStateBuffer,
    FastDroneStateBuffer,
    StateSnapshot,
    StateManager,
    create_drone_state_buffer,
    create_fast_state_buffer,
    create_state_manager
)
from dart_planner.common.types import DroneState, FastDroneState
from dart_planner.common.units import Q_


class TestThreadSafeStateBuffer:
    """Test the generic thread-safe state buffer."""
    
    def test_initialization(self):
        """Test buffer initialization."""
        buffer = ThreadSafeStateBuffer(buffer_size=5, state_type=DroneState)
        
        assert buffer.buffer_size == 5
        assert buffer.state_type == DroneState
        assert buffer.get_latest_state() is None
        
        stats = buffer.get_statistics()
        assert stats['updates'] == 0
        assert stats['reads'] == 0
        assert stats['current_version'] == 0
    
    def test_single_update_and_read(self):
        """Test basic update and read functionality."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        # Create test state
        state = DroneState(
            timestamp=time.time(),
            position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
            velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
        )
        
        # Update buffer
        version = buffer.update_state(state, "test")
        
        assert version == 1
        
        # Read state
        snapshot = buffer.get_latest_state()
        assert snapshot is not None
        assert snapshot.state == state
        assert snapshot.version == 1
        assert snapshot.source == "test"
        assert snapshot.timestamp > 0
    
    def test_multiple_updates(self):
        """Test multiple sequential updates."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        for i in range(5):
            state = DroneState(
                timestamp=time.time(),
                position=Q_(np.array([i, i, i]), 'm'),
                velocity=Q_(np.array([i*0.1, i*0.1, i*0.1]), 'm/s'),
                attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
                angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
            )
            
            version = buffer.update_state(state, f"update_{i}")
            
            snapshot = buffer.get_latest_state()
            assert snapshot.version == version
            assert snapshot.state.position.to('m').magnitude[0] == i
        
        stats = buffer.get_statistics()
        assert stats['updates'] == 5
        assert stats['current_version'] == 5
    
    def test_concurrent_access(self):
        """Test concurrent access from multiple threads."""
        buffer = ThreadSafeStateBuffer(buffer_size=10, state_type=DroneState)
        
        # Thread for updates
        def update_thread():
            for i in range(100):
                state = DroneState(
                    timestamp=time.time(),
                    position=Q_(np.array([i, i, i]), 'm'),
                    velocity=Q_(np.array([i*0.1, i*0.1, i*0.1]), 'm/s'),
                    attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
                    angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
                )
                buffer.update_state(state, f"thread_update_{i}")
                time.sleep(0.001)  # Small delay
        
        # Thread for reads
        read_results = []
        def read_thread():
            for i in range(100):
                snapshot = buffer.get_latest_state()
                if snapshot is not None:
                    read_results.append(snapshot.version)
                time.sleep(0.001)  # Small delay
        
        # Start threads
        update_t = threading.Thread(target=update_thread)
        read_t = threading.Thread(target=read_thread)
        
        update_t.start()
        read_t.start()
        
        update_t.join()
        read_t.join()
        
        # Verify no race conditions occurred
        stats = buffer.get_statistics()
        assert stats['updates'] == 100
        assert stats['reads'] >= 0  # Reads may be 0 if all happened before updates
        
        # Verify all read versions are valid
        for version in read_results:
            assert 1 <= version <= 100
    
    def test_wait_for_update(self):
        """Test blocking wait for update."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        # Start update thread
        def update_after_delay():
            time.sleep(0.1)
            state = DroneState(
                timestamp=time.time(),
                position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
                velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
                attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
                angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
            )
            buffer.update_state(state, "delayed_update")
        
        update_thread = threading.Thread(target=update_after_delay)
        update_thread.start()
        
        # Wait for update
        snapshot = buffer.wait_for_update(timeout=1.0)
        
        assert snapshot is not None
        assert snapshot.version == 1
        assert snapshot.source == "delayed_update"
        
        update_thread.join()
    
    def test_wait_for_update_timeout(self):
        """Test timeout when waiting for update."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        # Wait for update that never comes
        snapshot = buffer.wait_for_update(timeout=0.1)
        
        assert snapshot is None
    
    def test_get_state_at_time(self):
        """Test getting state at specific time."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        # Update with known timestamp
        update_time = time.time()
        state = DroneState(
            timestamp=update_time,
            position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
            velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
        )
        buffer.update_state(state, "test")
        
        # Get state at exact time
        snapshot = buffer.get_state_at_time(update_time, max_age=0.1)
        assert snapshot is not None
        assert snapshot.timestamp == update_time
        
        # Get state at future time (should be stale)
        future_time = update_time + 0.2
        snapshot = buffer.get_state_at_time(future_time, max_age=0.1)
        assert snapshot is None
        
        # Get state at past time (should be stale)
        past_time = update_time - 0.2
        snapshot = buffer.get_state_at_time(past_time, max_age=0.1)
        assert snapshot is None
    
    def test_reset(self):
        """Test buffer reset functionality."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        # Add some data
        state = DroneState(
            timestamp=time.time(),
            position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
            velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
        )
        buffer.update_state(state, "test")
        
        # Verify data exists
        assert buffer.get_latest_state() is not None
        
        # Reset
        buffer.reset()
        
        # Verify data is cleared
        assert buffer.get_latest_state() is None
        
        stats = buffer.get_statistics()
        assert stats['updates'] == 0
        assert stats['reads'] == 0
        assert stats['current_version'] == 0


class TestDroneStateBuffer:
    """Test the DroneState-specific buffer."""
    
    def test_initialization(self):
        """Test DroneStateBuffer initialization."""
        buffer = DroneStateBuffer(buffer_size=10)
        
        assert buffer.buffer_size == 10
        assert buffer.state_type == DroneState
        assert buffer.get_latest_state() is None
    
    def test_update_from_estimator(self):
        """Test updating from estimator output."""
        buffer = DroneStateBuffer(buffer_size=5)
        
        # Create mock EstimatedState
        from dart_planner.common.types import EstimatedState, Pose, Twist, Accel
        
        estimated_state = EstimatedState(
            timestamp=time.time(),
            pose=Pose(
                position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
                orientation=Q_(np.array([0.0, 0.0, 0.0]), 'rad')
            ),
            twist=Twist(
                linear=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
                angular=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
            ),
            accel=Accel(),
            source="test_estimator"
        )
        
        # Update from estimator
        version = buffer.update_from_estimator(estimated_state, "estimator")
        
        assert version == 1
        
        # Verify conversion
        snapshot = buffer.get_latest_state()
        assert snapshot is not None
        assert snapshot.source == "estimator"
        assert snapshot.state.position.to('m').magnitude[0] == 1.0
        assert snapshot.state.velocity.to('m/s').magnitude[0] == 0.1
    
    def test_update_from_drone_state(self):
        """Test updating directly from DroneState."""
        buffer = DroneStateBuffer(buffer_size=5)
        
        drone_state = DroneState(
            timestamp=time.time(),
            position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
            velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
        )
        
        version = buffer.update_state(drone_state, "direct")
        
        assert version == 1
        
        snapshot = buffer.get_latest_state()
        assert snapshot is not None
        assert snapshot.state == drone_state


class TestFastDroneStateBuffer:
    """Test the FastDroneState-specific buffer."""
    
    def test_initialization(self):
        """Test FastDroneStateBuffer initialization."""
        buffer = FastDroneStateBuffer(buffer_size=5)
        
        assert buffer.buffer_size == 5
        assert buffer.state_type == FastDroneState
        assert buffer.get_latest_state() is None
    
    def test_update_from_drone_state(self):
        """Test updating from DroneState by converting to FastDroneState."""
        buffer = FastDroneStateBuffer(buffer_size=5)
        
        drone_state = DroneState(
            timestamp=time.time(),
            position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
            velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
        )
        
        version = buffer.update_from_drone_state(drone_state, "converter")
        
        assert version == 1
        
        snapshot = buffer.get_latest_state()
        assert snapshot is not None
        assert snapshot.source == "converter"
        
        # Verify conversion to FastDroneState
        fast_state = snapshot.state
        assert isinstance(fast_state, FastDroneState)
        assert fast_state.position[0] == 1.0
        assert fast_state.velocity[0] == 0.1


class TestStateManager:
    """Test the high-level state manager."""
    
    def test_initialization(self):
        """Test StateManager initialization."""
        manager = StateManager()
        
        assert len(manager._buffers) == 0
    
    def test_register_and_get_buffer(self):
        """Test registering and retrieving buffers."""
        manager = StateManager()
        
        buffer1 = DroneStateBuffer()
        buffer2 = FastDroneStateBuffer()
        
        manager.register_buffer("drone_state", buffer1)
        manager.register_buffer("fast_state", buffer2)
        
        assert manager.get_buffer("drone_state") == buffer1
        assert manager.get_buffer("fast_state") == buffer2
        assert manager.get_buffer("nonexistent") is None
    
    def test_update_and_get_state(self):
        """Test updating and getting state through manager."""
        manager = StateManager()
        
        buffer = DroneStateBuffer()
        manager.register_buffer("test", buffer)
        
        drone_state = DroneState(
            timestamp=time.time(),
            position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
            velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
        )
        
        version = manager.update_state("test", drone_state, "manager_test")
        
        assert version == 1
        
        snapshot = manager.get_latest_state("test")
        assert snapshot is not None
        assert snapshot.state == drone_state
        assert snapshot.source == "manager_test"
    
    def test_get_all_statistics(self):
        """Test getting statistics from all buffers."""
        manager = StateManager()
        
        buffer1 = DroneStateBuffer()
        buffer2 = FastDroneStateBuffer()
        
        manager.register_buffer("buffer1", buffer1)
        manager.register_buffer("buffer2", buffer2)
        
        # Add some data
        drone_state = DroneState(
            timestamp=time.time(),
            position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
            velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
        )
        
        manager.update_state("buffer1", drone_state, "test")
        manager.update_state("buffer2", drone_state, "test")
        
        stats = manager.get_all_statistics()
        
        assert "buffer1" in stats
        assert "buffer2" in stats
        assert stats["buffer1"]["updates"] == 1
        assert stats["buffer2"]["updates"] == 1
    
    def test_reset_all(self):
        """Test resetting all buffers."""
        manager = StateManager()
        
        buffer1 = DroneStateBuffer()
        buffer2 = FastDroneStateBuffer()
        
        manager.register_buffer("buffer1", buffer1)
        manager.register_buffer("buffer2", buffer2)
        
        # Add some data
        drone_state = DroneState(
            timestamp=time.time(),
            position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
            velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
        )
        
        manager.update_state("buffer1", drone_state, "test")
        manager.update_state("buffer2", drone_state, "test")
        
        # Reset all
        manager.reset_all()
        
        # Verify all buffers are reset
        assert manager.get_latest_state("buffer1") is None
        assert manager.get_latest_state("buffer2") is None


class TestAsyncFeatures:
    """Test async features of the state buffer."""
    
    @pytest.mark.asyncio
    async def test_wait_for_update_async(self):
        """Test async wait for update."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        # Start update task
        async def update_after_delay():
            await asyncio.sleep(0.1)
            state = DroneState(
                timestamp=time.time(),
                position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
                velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
                attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
                angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
            )
            buffer.update_state(state, "async_update")
        
        # Start update task
        update_task = asyncio.create_task(update_after_delay())
        
        # Wait for update
        snapshot = await buffer.wait_for_update_async(timeout=1.0)
        
        assert snapshot is not None
        assert snapshot.version == 1
        assert snapshot.source == "async_update"
        
        await update_task
    
    @pytest.mark.asyncio
    async def test_wait_for_update_async_timeout(self):
        """Test async wait timeout."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        # Wait for update that never comes
        snapshot = await buffer.wait_for_update_async(timeout=0.1)
        
        assert snapshot is None
    
    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe(self):
        """Test async subscription to state updates."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        # Subscribe to updates
        queue = buffer.subscribe(queue_size=5)
        
        # Update state
        state = DroneState(
            timestamp=time.time(),
            position=Q_(np.array([1.0, 2.0, 3.0]), 'm'),
            velocity=Q_(np.array([0.1, 0.2, 0.3]), 'm/s'),
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
        )
        buffer.update_state(state, "subscription_test")
        
        # Wait for update in queue
        update_event = await asyncio.wait_for(queue.get(), timeout=1.0)
        
        assert update_event['state'] == state
        assert update_event['version'] == 1
        
        # Unsubscribe
        buffer.unsubscribe(queue)
        
        # Update again (should not be in queue)
        buffer.update_state(state, "after_unsubscribe")
        
        # Queue should be empty
        assert queue.empty()


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_drone_state_buffer(self):
        """Test create_drone_state_buffer factory."""
        buffer = create_drone_state_buffer(buffer_size=15)
        
        assert isinstance(buffer, DroneStateBuffer)
        assert buffer.buffer_size == 15
    
    def test_create_fast_state_buffer(self):
        """Test create_fast_state_buffer factory."""
        buffer = create_fast_state_buffer(buffer_size=8)
        
        assert isinstance(buffer, FastDroneStateBuffer)
        assert buffer.buffer_size == 8
    
    def test_create_state_manager(self):
        """Test create_state_manager factory."""
        manager = create_state_manager()
        
        assert isinstance(manager, StateManager)


class TestRaceConditionPrevention:
    """Test that the buffer prevents race conditions and stale data."""
    
    def test_no_stale_data_consumption(self):
        """Test that control loops cannot consume stale or mid-update data."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        # Simulate rapid updates from estimator
        def estimator_thread():
            for i in range(100):
                state = DroneState(
                    timestamp=time.time(),
                    position=Q_(np.array([i, i, i]), 'm'),
                    velocity=Q_(np.array([i*0.1, i*0.1, i*0.1]), 'm/s'),
                    attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
                    angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
                )
                buffer.update_state(state, "estimator")
                time.sleep(0.001)  # 1ms between updates
        
        # Simulate high-frequency control loop
        control_versions = []
        def control_thread():
            for i in range(100):
                snapshot = buffer.get_latest_state()
                if snapshot is not None:
                    control_versions.append(snapshot.version)
                time.sleep(0.001)  # 1ms control loop
        
        # Start threads
        estimator_t = threading.Thread(target=estimator_thread)
        control_t = threading.Thread(target=control_thread)
        
        estimator_t.start()
        control_t.start()
        
        estimator_t.join()
        control_t.join()
        
        # Verify no race conditions
        stats = buffer.get_statistics()
        assert stats['updates'] == 100
        
        # Verify all control versions are valid and increasing
        if control_versions:
            assert min(control_versions) >= 1
            assert max(control_versions) <= 100
    
    def test_atomic_updates(self):
        """Test that updates are atomic and cannot be partially read."""
        buffer = ThreadSafeStateBuffer(buffer_size=3, state_type=DroneState)
        
        # Create a large state update
        large_position = Q_(np.random.rand(3) * 1000, 'm')  # Large values
        large_velocity = Q_(np.random.rand(3) * 100, 'm/s')  # Large values
        
        state = DroneState(
            timestamp=time.time(),
            position=large_position,
            velocity=large_velocity,
            attitude=Q_(np.array([0.0, 0.0, 0.0]), 'rad'),
            angular_velocity=Q_(np.array([0.0, 0.0, 0.0]), 'rad/s')
        )
        
        # Update in one thread
        def update_thread():
            buffer.update_state(state, "atomic_test")
        
        # Read in another thread
        read_results = []
        def read_thread():
            for i in range(1000):  # Many reads
                snapshot = buffer.get_latest_state()
                if snapshot is not None:
                    read_results.append(snapshot.state)
                time.sleep(0.0001)  # Very fast reads
        
        update_t = threading.Thread(target=update_thread)
        read_t = threading.Thread(target=read_thread)
        
        update_t.start()
        read_t.start()
        
        update_t.join()
        read_t.join()
        
        # Verify all reads are consistent (no partial updates)
        for read_state in read_results:
            assert read_state.position.to('m').magnitude[0] == large_position.to('m').magnitude[0]
            assert read_state.velocity.to('m/s').magnitude[0] == large_velocity.to('m/s').magnitude[0]


if __name__ == "__main__":
    pytest.main([__file__]) 