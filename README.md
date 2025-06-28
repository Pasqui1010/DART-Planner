# Distributed Aerial Robotics Trajectory Planner (DART-Planner)

[![Status](https://img.shields.io/badge/Status-Active%20Development-blue.svg)](https://github.com/Pasqui1010/DART-Planner)
[![Performance](https://img.shields.io/badge/Performance-Optimized-green.svg)](https://github.com/Pasqui1010/DART-Planner)
[![Control Frequency](https://img.shields.io/badge/Control%20Freq-745%20Hz-orange.svg)](https://github.com/Pasqui1010/DART-Planner)
[![Stability](https://img.shields.io/badge/Failsafes-0%20Activations-green.svg)](https://github.com/Pasqui1010/DART-Planner)

## Overview

This repository implements a distributed three-layer drone control architecture that separates high-level trajectory planning from low-level control execution. The system uses DIAL-MPC for optimal trajectory generation in the cloud layer and geometric control for attitude control in the edge layer.

## System Performance

| Metric | Before Optimization | After Optimization | Improvement |
|--------|---------------------|-------------------|-------------|
| Position Tracking | 193.9m mean error | 67.2m mean error | 2.9x reduction |
| Control Frequency | 100 Hz | 745 Hz average | 7.4x increase |
| System Stability | Failsafe activations | 0 failsafe activations | Stable operation |
| Data Collection | 1,900 data points | 13,547 data points | 7.1x increase |

## Architecture

### Three-Layer Hierarchical Architecture
```
Layer 1: Global Planner      Layer 2: DIAL-MPC         Layer 3: Reactive Controller
      (Cloud - 0.1-1Hz)        (Cloud - 1-10Hz)           (Edge - 100-1000Hz)
┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────────┐
│ Strategic Planning  │───▶│ Trajectory          │───▶│ Geometric Control    │
│                     │    │ Optimization        │    │                      │
│ • A*/D* Lite search │    │                     │    │ • SE(3) attitude     │
│ • Semantic reasoning│    │ • DIAL-MPC solver   │    │ • Real-time control  │
│ • Mission waypoints │    │ • Dynamic feasible  │    │ • Failsafe behaviors │
│ • Uncertainty aware │    │ • Obstacle avoidance│    │ • Disturbance reject │
└─────────────────────┘    └─────────────────────┘    └──────────────────────┘
```

### Core Components

#### Layer 1: Global Strategic Planning
1. **Global Mission Planner** (`src/planning/global_mission_planner.py`)
   - High-level path planning using A*/D* Lite algorithms
   - Semantic reasoning and mission objective integration
   - Uncertainty-aware navigation and exploration strategies
   - Global waypoint generation and corridor planning

#### Layer 2: Trajectory Optimization  
2. **DIAL-MPC Planner** (`src/planning/dial_mpc_planner.py`)
   - Training-free iterative optimization
   - Dynamically feasible trajectory generation
   - Real-time obstacle avoidance and constraint handling
   - Warm-starting for computational efficiency

#### Layer 3: Reactive Control
3. **Geometric Controller** (`src/control/geometric_controller.py`)
   - SE(3) attitude control for quadrotors
   - Real-time thrust and torque computation
   - Multi-level failsafe behaviors
   - High-frequency control execution (100-1000Hz)

#### Supporting Components
4. **Trajectory Smoother** (`src/control/trajectory_smoother.py`)
   - C² continuity between trajectory segments
   - Quintic polynomial interpolation
   - Velocity and acceleration preservation

5. **Communication Layer** (`src/communication/`)
   - ZMQ-based cloud-edge communication
   - Asynchronous trajectory transmission
   - Connection management and error handling

## Technical Features

### Training-Free Operation
The system maintains training-free operation principles, using DIAL-MPC for optimization without neural network contamination while leveraging distributed processing for enhanced performance.

### Hierarchical Control Flow
- **Layer 1 (Global Planning)**: Strategic mission planning and waypoint generation (0.1-1Hz)
- **Layer 2 (DIAL-MPC)**: Local trajectory optimization and dynamic obstacle avoidance (1-10Hz)
- **Layer 3 (Reactive Control)**: High-frequency attitude control and immediate safety responses (100-1000Hz)
- **Communication**: Asynchronous inter-layer communication with robust error handling

### Safety Systems
- Multi-level failsafe implementation
- Graceful degradation under communication loss
- Real-time performance monitoring
- Control input saturation protection

## Performance Characteristics

### Control System
- **Frequency**: 744.5 Hz average (74% of 1kHz target)
- **Stability**: Zero failsafe activations over test period
- **Responsiveness**: Real-time attitude control
- **Robustness**: Maintains operation during communication delays

### Motion Profile
- **Average Speed**: 38.14 m/s
- **Maximum Speed**: 69.23 m/s
- **Trajectory Smoothness**: C² continuous motion profiles
- **Control Range**: Thrust 9.81-20.00N, Torque 0-5.03 N⋅m

## Project Structure

```
Controller/
├── src/                          # Main source code
│   ├── cloud/                    # Cloud-side components
│   ├── edge/                     # Edge-side components  
│   ├── control/                  # Control algorithms
│   ├── planning/                 # Path planning
│   ├── communication/            # Network communication
│   └── common/                   # Shared utilities
├── docs/                         # Documentation
│   ├── architecture/             # System architecture docs
│   ├── analysis/                 # Analysis reports
│   └── roadmap/                  # Implementation plans
├── experiments/                  # Experimental code & tests
│   ├── phase1/                   # Phase 1 optimization
│   ├── phase2/                   # Phase 2 optimization
│   ├── optimization/             # Optimization tools
│   └── validation/               # System validation
├── data/                         # Raw data & logs
│   ├── trajectory_logs/          # CSV trajectory data
│   └── profile_results/          # Performance profiles
├── results/                      # Generated visualizations
│   ├── figures/                  # Numbered figures
│   └── analysis_plots/           # Analysis visualizations
├── scripts/                      # Utility scripts
│   ├── analysis/                 # Data analysis
│   ├── visualization/            # Plot generation
│   └── utils/                    # General utilities
├── tests/                        # Unit tests
├── README.md                     # This file
├── requirements.txt              # Dependencies
└── LICENSE                       # License
```

## Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
```

### Running the System
```bash
# Test the optimized system
python experiments/validation/test_improved_system.py

# Generate visualizations
python scripts/visualization/create_comprehensive_visualization.py
python scripts/visualization/create_publication_ready_plots.py

# Run optimization experiments
python experiments/phase1/phase1_optimization_test.py
python experiments/phase2/phase2c_final_test.py
python experiments/validation/comprehensive_system_test.py
```

## Repository Organization

The repository is organized to support collaborative development:

### Code Organization
- **Clear Separation**: Code, documentation, data, and results are separated
- **Phase-Based Experiments**: Development organized by optimization phases
- **Modular Design**: Each component has clear interfaces and responsibilities
- **Documentation**: READMEs in each directory explain contents and usage

### Experimental Structure
- **Phase 1**: Controller gain optimization (completed)
- **Phase 2**: Velocity tracking and frequency optimization (completed)
- **Optimization**: Tools and analysis scripts for system tuning
- **Validation**: Comprehensive testing and system verification

## Technical Contributions

### System Architecture
1. **Three-Layer Hierarchical Design**: Clear separation of strategic planning, trajectory optimization, and reactive control
2. **Distributed Intelligence**: Global planning and DIAL-MPC in cloud, reactive control on edge
3. **Training-Free Optimization**: DIAL-MPC implementation without neural networks
4. **Geometric Control**: SE(3) attitude control for quadrotor platforms
5. **Safety Framework**: Multi-level failsafe design across all layers

### Implementation Features
- Complete system implementation with all source code
- Comprehensive logging and data collection
- Visualization tools for system analysis
- Reproducible experimental framework

## Future Development

### Planned Extensions
1. **Neural Scene Representation**: Integration with NeRF/3DGS mapping
2. **GPS-Denied Navigation**: VIO/LIO sensor fusion implementation
3. **Multi-Agent Coordination**: Shared planning protocols
4. **Enhanced Safety**: Advanced obstacle avoidance and disturbance rejection

### Research Applications
The system provides a foundation for:
- Advanced autonomous flight research
- Multi-agent coordination studies
- Neural scene representation integration
- Safety-critical autonomous systems

## Contributing

This repository is organized for collaborative development. Key areas for contribution include:

- **Control Algorithm Optimization**: Improving controller gains and performance
- **Planning Enhancement**: Extending DIAL-MPC capabilities
- **Safety Systems**: Enhancing failsafe and monitoring capabilities
- **Documentation**: Improving code documentation and guides
- **Testing**: Expanding test coverage and validation scenarios

## Contact

For questions, issues, or contributions, please use the GitHub issue tracker or submit pull requests.

## Status

- **Current Phase**: Optimized distributed control system
- **Next Phase**: Neural scene representation integration
- **Development Status**: Active development with stable foundation
