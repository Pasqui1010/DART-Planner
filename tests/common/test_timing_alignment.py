import numpy as np
import pytest

from dart_planner.common.timing_alignment import TimingManager, TimingConfig


def test_initial_control_delta():
    """
    The first update_control_timing call should record control_dt as the delta.
    """
    cfg = TimingConfig(control_frequency=100.0)
    tm = TimingManager(cfg)
    first_time = 0.5  # arbitrary timestamp
    tm.update_control_timing(first_time)
    # Only one record exists
    assert len(tm.control_times) == 1
    # Delta equals control_dt
    assert tm.control_times[0] == pytest.approx(tm.control_dt, rel=1e-6)


def test_constant_control_deltas():
    """
    Repeated calls at exact control_dt intervals should record identical deltas.
    """
    cfg = TimingConfig(control_frequency=50.0)
    tm = TimingManager(cfg)
    dt = tm.control_dt
    # Simulate 100 updates at exact dt intervals
    for i in range(1, 101):
        tm.update_control_timing(i * dt)
    assert len(tm.control_times) == 100
    # All deltas equal dt
    for delta in tm.control_times:
        assert delta == pytest.approx(dt, rel=1e-6)


def test_jitter_distribution():
    """
    Introduce small random jitter and ensure 99th percentile within 5% of control_dt.
    """
    np.random.seed(42)
    cfg = TimingConfig(control_frequency=200.0)
    tm = TimingManager(cfg)
    dt = tm.control_dt
    # Generate timestamps with ±2% jitter
    timestamps = [i * dt * (1 + np.random.uniform(-0.02, 0.02)) for i in range(1, 501)]
    for t in timestamps:
        tm.update_control_timing(t)
    # Compute 99th percentile of recorded deltas
    p99 = np.percentile(tm.control_times, 99)
    # Should be within 5% of dt
    assert p99 <= dt * 1.05 