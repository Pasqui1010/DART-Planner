# Real-Time Configuration Migration Guide

## Overview
The legacy `dart_planner.config.real_time_config` module has been consolidated
into `dart_planner.config.frozen_config.RealTimeConfig`. This migration
eliminates configuration duplication and provides a single source of truth.

## Files Requiring Migration

### examples\real_time_integration_example.py

**Legacy Imports:**
- `from dart_planner.config.real_time_config`

**Legacy Function Calls:**
- `get_control_loop_config` → config.real_time
- `get_planning_loop_config` → config.real_time
- `get_safety_loop_config` → config.real_time
- `get_communication_config` → config.real_time
- `get_control_loop_config` → config.real_time
- `get_planning_loop_config` → config.real_time
- `get_safety_loop_config` → config.real_time
- `get_communication_config` → config.real_time

**Migration Steps:**
1. Remove legacy imports
2. Use `config.real_time` directly from frozen config
3. Update function calls to access properties directly
4. Test the changes

### scripts\migrate_real_time_config.py

**Migration Steps:**
1. Remove legacy imports
2. Use `config.real_time` directly from frozen config
3. Update function calls to access properties directly
4. Test the changes

### src\dart_planner\common\real_time_integration.py

**Legacy Imports:**
- `from dart_planner.config.real_time_config`

**Legacy Function Calls:**
- `get_real_time_config` → config.real_time
- `get_control_loop_config` → config.real_time
- `get_planning_loop_config` → config.real_time
- `get_safety_loop_config` → config.real_time
- `get_communication_config` → config.real_time
- `get_control_loop_config` → config.real_time
- `get_planning_loop_config` → config.real_time
- `get_safety_loop_config` → config.real_time
- `get_control_loop_config` → config.real_time
- `get_planning_loop_config` → config.real_time
- `get_control_loop_config` → config.real_time

**Migration Steps:**
1. Remove legacy imports
2. Use `config.real_time` directly from frozen config
3. Update function calls to access properties directly
4. Test the changes

## Migration Examples

### Before (Legacy)
```python
from dart_planner.config.real_time_config import get_real_time_config

config = get_config()
rt_config = get_real_time_config(config)
frequency = rt_config.task_timing.control_loop_frequency_hz
```

### After (Consolidated)
```python
from dart_planner.config.frozen_config import get_frozen_config

config = get_frozen_config()
frequency = config.real_time.control_loop_frequency_hz
```

## New Configuration Properties

The consolidated `RealTimeConfig` includes all properties from the legacy system:

- `control_loop_frequency_hz`: Control loop frequency (default: 400.0)
- `planning_loop_frequency_hz`: Planning loop frequency (default: 25.0)
- `safety_loop_frequency_hz`: Safety loop frequency (default: 100.0)
- `max_control_latency_ms`: Maximum control latency (default: 2.5)
- `max_planning_latency_ms`: Maximum planning latency (default: 40.0)
- `max_safety_latency_ms`: Maximum safety latency (default: 10.0)
- `enable_deadline_monitoring`: Enable deadline monitoring (default: True)
- `enable_jitter_compensation`: Enable jitter compensation (default: True)
- `max_jitter_ms`: Maximum allowed jitter (default: 0.1)
- `enable_priority_scheduling`: Enable priority scheduling (default: True)
- `control_priority`: Control loop priority (default: 90)
- `planning_priority`: Planning loop priority (default: 70)
- `safety_priority`: Safety loop priority (default: 95)
- `enable_rt_os`: Enable real-time OS features (default: True)
- `enable_priority_inheritance`: Enable priority inheritance (default: True)
- `enable_timing_compensation`: Enable timing compensation (default: True)
- `max_scheduling_latency_ms`: Maximum scheduling latency (default: 0.1)
- `max_context_switch_ms`: Maximum context switch time (default: 0.01)
- `max_interrupt_latency_ms`: Maximum interrupt latency (default: 0.05)
- `clock_drift_compensation_factor`: Clock drift compensation factor (default: 0.1)
- `jitter_compensation_window`: Jitter compensation window size (default: 100)
- `timing_compensation_threshold_ms`: Timing compensation threshold (default: 0.1)
- `control_loop_deadline_ms`: Control loop deadline (default: 2.0)
- `control_loop_jitter_ms`: Control loop jitter tolerance (default: 0.1)
- `planning_loop_deadline_ms`: Planning loop deadline (default: 15.0)
- `planning_loop_jitter_ms`: Planning loop jitter tolerance (default: 1.0)
- `safety_loop_deadline_ms`: Safety loop deadline (default: 8.0)
- `safety_loop_jitter_ms`: Safety loop jitter tolerance (default: 0.5)
- `communication_frequency_hz`: Communication frequency (default: 10.0)
- `communication_deadline_ms`: Communication deadline (default: 100.0)
- `communication_jitter_ms`: Communication jitter tolerance (default: 5.0)
- `telemetry_frequency_hz`: Telemetry frequency (default: 10.0)
- `telemetry_deadline_ms`: Telemetry deadline (default: 100.0)
- `telemetry_jitter_ms`: Telemetry jitter tolerance (default: 5.0)
- `enable_performance_monitoring`: Enable performance monitoring (default: True)
- `monitoring_frequency_hz`: Performance monitoring frequency (default: 10.0)
- `stats_window_size`: Statistics window size (default: 1000)
- `deadline_violation_threshold`: Deadline violation alert threshold (default: 5)
- `jitter_threshold_ms`: Jitter alert threshold (default: 1.0)
- `execution_time_threshold_ms`: Execution time alert threshold (default: 10.0)
- `enable_timing_logs`: Enable timing logs (default: True)
- `enable_performance_reports`: Enable performance reports (default: True)
- `log_performance_interval_s`: Performance log interval (default: 10.0)

## Environment Variables

All real-time configuration can be set via environment variables:

- `DART_CONTROL_FREQUENCY_HZ` - Control loop frequency
- `DART_PLANNING_FREQUENCY_HZ` - Planning loop frequency
- `DART_SAFETY_FREQUENCY_HZ` - Safety loop frequency
- `DART_MAX_CONTROL_LATENCY_MS` - Maximum control latency
- `DART_ENABLE_DEADLINE_MONITORING` - Enable deadline monitoring
- And many more... (see frozen_config.py for complete list)

## Validation

After migration, validate your configuration:

```python
from dart_planner.config.frozen_config import get_frozen_config

config = get_frozen_config()
print(f"Control frequency: {config.real_time.control_loop_frequency_hz} Hz")
print(f"Planning frequency: {config.real_time.planning_loop_frequency_hz} Hz")
```