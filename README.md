# DART-Planner

Distributed Aerial Robotics Trajectory Planner

This repository contains a reference implementation of a three-layer planning
and control stack for autonomous quadrotors.  The design follows
edge-first principles: all safety-critical logic can run entirely on the
vehicle, while optional cloud components provide higher-level mission
guidance when connectivity is available.

Key subsystems

* **Trajectory optimisation** – an SE(3) model-predictive controller
  (`src/planning/se3_mpc_planner.py`).
* **Mapping** – a voxel-based obstacle map maintained by
  `src/perception/explicit_geometric_mapper.py`.
* **Simulation** – a lightweight physics model in
  `src/utils/drone_simulator.py` enables software-only testing.

The project is fully typed, linted, and covered by unit/integration tests
(`tests/` directory).  Continuous integration runs on every commit
via GitHub Actions.

## Architecture

### Edge-First Three-Layer Architecture
```
Layer 1: Mission Advisory     Layer 2: SE(3) Trajectory    Layer 3: Autonomous Edge
      (Cloud - Advisory)         (Hybrid Cloud/Edge)           (Edge - Critical)
┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────────┐
│ Strategic Guidance  │───▶│ SE(3) MPC           │───▶│ Onboard Autonomous   │
│                     │    │ Optimization        │    │ Controller           │
│ • A*/D* Lite search │    │                     │    │                      │
│ • Semantic reasoning│    │ • SE(3) MPC solver  │    │ • Full edge autonomy │
│ • Mission waypoints │    │ • Aerial dynamics   │    │ • Tiered failsafes   │
│ • Neural enhancement│    │ • Real-time capable │    │ • Local mapping      │
└─────────────────────┘    └─────────────────────┘    │ • Safety validation  │
                                                      │ • Emergency override │
     HYBRID PERCEPTION SYSTEM                        └──────────────────────┘
┌─────────────────────────────────────────────────┐
│ Real-Time Safety: Explicit Geometric Mapping   │
│ Intelligence Path: Neural Scene Enhancement     │
│ Development Aid: Proxy Oracle Interface        │
└─────────────────────────────────────────────────┘
```

### Core Components (Post-Refactor)

#### Layer 1: Mission Advisory (Cloud)
1. **Global Mission Planner** (`src/planning/global_mission_planner.py`)
   - High-level strategic guidance and waypoint generation
   - Semantic reasoning with neural scene enhancement
   - Uncertainty-aware exploration when neural intelligence available
   - **ADVISORY ROLE**: Enhances but doesn't control edge operations

#### Layer 2: Trajectory Optimization (Hybrid)
2. **SE(3) MPC Planner** (`src/planning/se3_mpc_planner.py`) **[NEW - REPLACES DIAL-MPC]**
   - **Domain-appropriate**: Designed specifically for aerial robotics
   - SE(3) manifold formulation for natural quadrotor dynamics
   - Real-time convex optimization with proven convergence
   - **Performance**: Faster and more accurate than misapplied DIAL-MPC
   
3. **DIAL-MPC Planner** (`src/planning/dial_mpc_planner.py`) **[DEPRECATED]**
   - **AUDIT FINDING**: Fundamentally mismatched for aerial systems
   - Designed for legged locomotion with contact dynamics
   - Retained for benchmarking and comparison purposes only

#### Layer 3: Autonomous Edge (Critical)
4. **Onboard Autonomous Controller** (`src/edge/onboard_autonomous_controller.py`) **[ENHANCED]**
   - **FULL AUTONOMY**: Operates independently of cloud connection
   - **Tiered Failsafes**: nominal → degraded → autonomous → emergency
   - **Local Intelligence**: Onboard mapping, planning, and control
   - **Safety Override**: Validates all trajectories against local sensors

5. **Geometric Controller** (`src/control/geometric_controller.py`)
   - SE(3) attitude control for quadrotors
   - Real-time thrust and torque computation
   - Multi-level failsafe behaviors
   - High-frequency control execution (100-1000Hz)

#### Hybrid Perception System (Critical Innovation)
6. **Explicit Geometric Mapper** (`src/perception/explicit_geometric_mapper.py`) **[ENHANCED]**
   - **Real-Time Safety Path**: Proven SLAM techniques for collision detection
   - **High Performance**: >1kHz queries for trajectory validation
   - **Reliable**: No convergence issues or research-level dependencies
   
7. **Neural Scene Interface** (`src/neural_scene/base_neural_scene.py`) **[REFACTORED]**
   - **Intelligence Path**: Semantic understanding when available
   - **Non-Critical**: System operates safely without neural input
   - **Development Aid**: Proxy oracle for testing and development

#### Supporting Components
8. **Trajectory Smoother** (`src/control/trajectory_smoother.py`)
   - C² continuity between trajectory segments
   - Quintic polynomial interpolation
   - Velocity and acceleration preservation

9. **Communication Layer** (`src/communication/`)
   - ZMQ-based cloud-edge communication
   - Asynchronous trajectory transmission
   - Connection management and error handling
   - **REFACTORED**: No longer critical path for safety-critical operations

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

### Running the Refactored System
```bash
# REFACTOR VALIDATION: Run algorithm comparison
python experiments/validation/algorithm_comparison.py

# Test the edge-first autonomous system
python experiments/validation/test_improved_system.py

# Benchmark DIAL-MPC vs SE(3) MPC performance
python experiments/validation/comprehensive_system_test.py

# Generate refactor analysis visualizations
python scripts/visualization/create_comprehensive_visualization.py
python scripts/visualization/create_publication_ready_plots.py

# Test hybrid perception system
python -c "
from src.perception.explicit_geometric_mapper import ExplicitGeometricMapper
from src.edge.onboard_autonomous_controller import OnboardAutonomousController
print('✅ Hybrid perception system ready')
print('✅ Edge-first autonomy ready')
"
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

### Developer Quick-Start
```bash
# 1. Clone and install dev hooks
pre-commit install          # auto-format, lint & type-check on every commit

# 2. Run the fast test suite
pytest -q                   # should pass in < 1 min

# 3. Spin up the web demo locally (Docker required)
make demo                   # or:
#   docker build -t dart-planner -f docker/Dockerfile .
#   docker run --rm -it -p 8080:8080 dart-planner
```

### Pull-Request Preview
For every open PR GitHub Actions automatically builds a **Docker preview image** and
leaves a comment with the `docker pull …` and `docker run …` commands.  Reviewers
can run the exact commit in seconds without setting up the Python environment.

## Contact

For questions, issues, or contributions, please use the GitHub issue tracker or submit pull requests.

## Status

- **Current Phase**: Optimized distributed control system
- **Next Phase**: Neural scene representation integration
- **Development Status**: Active development with stable foundation
