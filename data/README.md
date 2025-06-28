# Data

This directory contains all experimental data, logs, and raw results from system tests.

## Structure

- **`trajectory_logs/`** - CSV files containing trajectory tracking data from various test runs
- **`profile_results/`** - Performance profiling data and timing measurements

## Trajectory Logs

Contains CSV files with detailed trajectory tracking data:

- `trajectory_log_*.csv` - Original trajectory logs from initial testing phases
- `improved_trajectory_log_*.csv` - Trajectory logs from optimized system runs

### Log File Format
Each trajectory log contains columns for:
- Timestamp
- Position (x, y, z)
- Velocity (vx, vy, vz) 
- Attitude (roll, pitch, yaw)
- Control inputs
- System state information

## Profile Results

Contains performance profiling data:
- `phase2c_profile_results.csv` - Phase 2C control loop profiling results
- Timing measurements for different system components
- Performance metrics and bottleneck analysis

## Data Usage

These files are used by analysis scripts in `experiments/` to:
- Generate performance visualizations
- Calculate tracking error metrics
- Analyze system improvements over time
- Validate optimization results 