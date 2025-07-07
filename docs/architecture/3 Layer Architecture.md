# **DART-Planner: 3-Layer Hierarchical Architecture**

This document outlines the three-layer hierarchical architecture for DART-Planner's autonomous navigation and control system. This design explicitly separates concerns to overcome onboard computational limits, manage system complexity, and leverage the strengths of specialized algorithms and computing environments.

## **Overall Philosophy: Cloud for Intelligence, Edge for Real-time Control and Safety**

The core principle of this architecture is to assign computationally intensive, high-level "cognitive" tasks (understanding, long-term planning, optimization) to the powerful **Cloud Node**, while delegating time-critical, high-frequency "reflexive" tasks (direct flight control, immediate reaction to local hazards) to the resource-constrained **Onboard (Edge) Node**. Communication between layers is deliberately designed to be robust and asynchronous, mitigating network vulnerabilities.

## **Unified Entry Point**

DART-Planner uses a unified CLI entry point that supports both cloud and edge modes:

```bash
# Run cloud node (Layer 1 & 2)
python -m src.dart_planner_cli run --mode=cloud

# Run edge node (Layer 3)
python -m src.dart_planner_cli run --mode=edge
```

This unified approach simplifies deployment and configuration while maintaining the clear separation between cloud and edge responsibilities.

## **Layer 1: Global/Strategic Planner (Cloud)**

This is the highest level of intelligence, responsible for long-term mission planning.

* **Purpose/Role:** To generate a high-level, feasible, and topologically correct mission path through the entire operating environment. It translates abstract mission objectives into a sequence of global waypoints or a general flight corridor.
* **Location:** **Cloud Node** (leveraging powerful CPUs/GPUs for complex computations).
* **Key Algorithms/Components:**
  * **Graph Search Algorithms (A\*, D\* Lite):** For finding paths on a discretized representation of the environment. D\* Lite is particularly useful for efficient replanning when global environmental changes are detected.
  * **Sampling-Based Planners (RRT\* variants, e.g., Informed RRT\*):** Excellent for exploring high-dimensional and geometrically complex environments, especially those with non-convex obstacles.
  * **Semantic Reasoner:** Interprets semantic information from the Neural Scene Representation to incorporate high-level mission rules (e.g., "avoid urban areas," "prioritize flying over green spaces," "stay away from people").
  * **Uncertainty-Aware Pathfinding:** Utilizes uncertainty information from the Neural Scene Representation to either avoid highly uncertain regions or strategically plan paths to actively explore and reduce uncertainty.
* **Inputs:**
  * Overall mission objectives (start, end, specific tasks, semantic preferences).
  * The **complete dynamic, semantic, and uncertainty-aware Neural Scene Representation** (managed and updated in the Cloud).
  * Current global drone state (periodically updated from Layer 3).
* **Outputs:** A relatively coarse, global path or sequence of waypoints/corridors (e.g., for the next minute of flight or a major mission segment). This plan is collision-free at a high level but not necessarily dynamically smooth for the drone.
* **Frequency:** **Low** (e.g., 0.1 Hz to 1 Hz, or triggered by significant mission changes, major environmental updates, or deviations from the current global path).
* **Key Challenges Addressed:**
  * **Large-scale Environment Navigation:** Solves pathfinding for vast and complex spaces.
  * **Semantic Interpretation:** Integrates abstract semantic rules into practical navigation.
  * **Uncertainty Guidance:** Provides intelligent guidance on how to deal with unknown areas.
  * **Computational Intensity:** Offloads the most demanding global search to powerful cloud resources.
* **Communication/Interfaces:** Provides its output to Layer 2 in the Cloud.

## **Layer 2: Local Trajectory Optimizer (SE(3) MPC)**

This layer refines the high-level plan into a precise, dynamically feasible, and optimal trajectory.

* **Purpose/Role:** To take a short segment of the global plan (from Layer 1) and generate a detailed, smooth, and dynamically optimal reference trajectory for the drone to follow over a short prediction horizon. It performs online optimization to account for local dynamics and immediate obstacles.
* **Location:** **Cloud Node** (utilizes cloud compute for SE(3) MPC's demanding optimization).
* **Key Algorithms/Components:**
  * **SE(3) MPC (Special Euclidean Group Model Predictive Control):** The core algorithm for this layer. It excels at finding optimal solutions in non-convex problem spaces while respecting the full 3D dynamics of aerial vehicles.
    * Its "sampling-based" nature with "diffusion-style annealing" allows it to navigate complex local scenarios.
    * It uses the drone's **full nonlinear dynamics model** for accurate predictions.
    * **Real-time Performance:** Achieves <50ms 95th percentile planning time for real-time operation.
  * **Local Scene Query Interface:** Queries the Neural Scene Representation (also in the Cloud) for detailed local dynamic obstacle information, semantic labels, and uncertainty values within its prediction horizon.
  * **Cost Function:** Designed to enforce dynamic feasibility, smoothness, energy efficiency, trajectory tracking, and incorporate penalties based on semantic information (e.g., proximity to certain objects) and uncertainty.
* **Inputs:**
  * Drone's current estimated state (periodically updated from Layer 3).
  * The next segment of the global plan/waypoints/corridor from Layer 1.
  * Detailed local environment data (dynamic obstacles, semantics, uncertainty) from the Neural Scene Representation.
* **Outputs:** A smooth, dynamically feasible, and optimal **reference trajectory** for the next few seconds (e.g., 5-10 seconds), consisting of a dense sequence of desired states (position, velocity, attitude, possibly even desired body rates). This trajectory is a compact data packet, suitable for network transmission.
* **Frequency:** **Medium** (e.g., 1 Hz to 10 Hz, or whenever a new segment of the global plan is needed/updated, or a significant local dynamic change occurs).
* **Key Challenges Addressed:**
  * **Non-convex Optimization:** Solves complex local optimization problems in cluttered, dynamic environments.
  * **Real-time Dynamic Obstacle Avoidance (Optimal):** Proactively plans optimal evasive maneuvers for predicted dynamic obstacles.
  * **Fine-Grained Semantic/Uncertainty Integration:** Directly uses detailed intelligence from the neural map to refine paths.
  * **Dynamic Feasibility:** Ensures generated paths are physically executable by the drone.
  * **Optimality:** Finds the "best" local path based on defined criteria.
* **Communication/Interfaces:** Receives high-level guidance from Layer 1 (Cloud-to-Cloud). Transmits the generated reference trajectory to Layer 3 (Cloud-to-Edge, via a robust and asynchronous link).

## **Layer 3: Reactive Controller (Edge)**

This is the drone's onboard "reflex" system, responsible for immediate flight execution.

* **Purpose/Role:** To execute the precise, optimal reference trajectory received from Layer 2 at a very high frequency. It ensures drone stability, rejects disturbances, and provides immediate, local safety overrides.
* **Location:** **Onboard (Edge) Node** (running on the drone's embedded processor).
* **Key Algorithms/Components:**
  * **High-Frequency Control Loop (Geometric Controller):** This is the core flight control algorithm that translates desired states into motor commands. It's designed for speed and robustness, not complex optimization.
    * **Real-time Performance:** Achieves <5ms 95th percentile control computation time.
    * **Robustness:** Handles model uncertainties and external disturbances.
  * **Robust State Estimation:** Processes onboard sensor data (IMU, cameras, LiDAR) to provide the drone's accurate real-time state (position, velocity, attitude, angular rates) even in GPS-denied environments.
    * **PX4EKF2StateEstimator:** Integrates with PX4's EKF2 for real hardware.
    * **AirSimStateEstimator:** Provides realistic simulation with configurable noise.
    * **Multi-sensor Fusion:** Combines IMU, visual, and range data for robust estimation.
  * **Fast Local Obstacle Avoidance (Reactive):** Uses direct readings from immediate local sensors (e.g., depth cameras, ultrasonic sensors) to implement fast, simple collision prevention, acting as a safety override if an unpredicted or extremely close obstacle is detected.
  * **Safety System:** Comprehensive safety monitoring and emergency procedures.
    * **SafetyWatchdog:** Monitors heartbeat and communication health.
    * **AirSimSafetyManager:** Manages safety violations and emergency procedures.
    * **Emergency Landing:** Automatic failsafe procedures for communication loss or critical failures.
* **Inputs:**
  * Drone's current estimated state from onboard state estimation.
  * The smooth, dynamically feasible **reference trajectory** received asynchronously from Layer 2 (Cloud-to-Edge).
  * Raw local obstacle sensor data (e.g., depth maps, LiDAR scans for immediate proximity).
* **Outputs:** Direct low-level motor commands (e.g., PWM signals to ESCs, or desired thrusts/torques that map to motor commands) at 1kHz.
* **Frequency:** **High** (e.g., 100 Hz to 1000 Hz, to ensure immediate reaction and stability).
* **Key Challenges Addressed:**
  * **Real-time Stability & Disturbance Rejection:** Maintains stable flight and compensates for external forces (e.g., wind).
  * **Onboard Compute Limitations:** Uses lightweight algorithms suitable for embedded hardware.
  * **Network Resilience:** Can operate robustly even if cloud updates are delayed or temporarily unavailable (by tracking the last valid trajectory segment).
  * **Immediate Safety:** Provides the fastest possible reaction to unforeseen, close-range obstacles.
* **Communication/Interfaces:** Receives reference trajectories from Layer 2 (Cloud-to-Edge). Sends current drone state and raw sensor data (for scene reconstruction) back to Layer 1 and 2 (Edge-to-Cloud).

## **State Estimation System**

The state estimation system provides accurate, real-time state information to all layers:

### **PX4EKF2StateEstimator**
- **Purpose:** Integrates with PX4's EKF2 for real hardware deployment
- **Inputs:** MAVLink messages (ATTITUDE, GLOBAL_POSITION_INT, ODOMETRY)
- **Outputs:** EstimatedState with pose, twist, and covariance information
- **Features:** 
  - Real-time MAVLink message parsing
  - Covariance estimation for uncertainty quantification
  - Robust to GPS-denied environments

### **AirSimStateEstimator**
- **Purpose:** Provides realistic simulation with configurable noise
- **Inputs:** AirSim ground-truth state
- **Outputs:** EstimatedState with realistic sensor noise
- **Features:**
  - Configurable Gaussian noise for position, orientation, velocity
  - Quaternion to Euler angle conversion
  - Realistic simulation of sensor imperfections

### **Performance Requirements**
- **Update Rate:** ≥100Hz for real-time control
- **Latency:** <2ms 95th percentile for edge processing
- **Accuracy:** <0.1m position, <0.1rad orientation in nominal conditions

## **Safety System**

The safety system ensures robust operation and emergency handling:

### **SafetyWatchdog**
- **Purpose:** Monitors system health and triggers emergency procedures
- **Features:**
  - Heartbeat monitoring for communication health
  - Configurable timeout thresholds
  - Emergency callback system for custom procedures
  - Integration with MAVLink heartbeat messages

### **AirSimSafetyManager**
- **Purpose:** Manages safety violations and emergency procedures in simulation
- **Features:**
  - Velocity and altitude limit monitoring
  - Safety violation counting and threshold management
  - Emergency landing procedures
  - Takeoff and landing automation

### **Safety Requirements**
- **Response Time:** <100ms for critical safety violations
- **Reliability:** 99.9% uptime for safety monitoring
- **Graceful Degradation:** Safe operation even with partial system failures

## **Communication Architecture**

### **Cloud-to-Edge Communication**
- **Protocol:** ZMQ for robust, asynchronous communication
- **Data:** Reference trajectories, mission updates
- **Frequency:** 1-10Hz depending on mission phase
- **Reliability:** Heartbeat monitoring with automatic failover

### **Edge-to-Cloud Communication**
- **Protocol:** ZMQ for state and sensor data transmission
- **Data:** Current state, sensor readings, health status
- **Frequency:** 10-100Hz depending on data type
- **Compression:** Telemetry compression for bandwidth efficiency

### **Safety Communication**
- **Protocol:** Heartbeat system with configurable timeouts
- **Frequency:** 10-100Hz heartbeat rate
- **Failover:** Automatic emergency procedures on communication loss

## **Performance Requirements**

### **Real-time Latency Requirements**
| Component | P95 Threshold | P99 Threshold | Mean Target |
|-----------|---------------|---------------|-------------|
| **Total Path** | ≤ 50ms | ≤ 100ms | ≤ 25ms |
| **Planning** | ≤ 50ms | ≤ 80ms | ≤ 20ms |
| **Control** | ≤ 5ms | ≤ 10ms | ≤ 2ms |
| **Actuator** | ≤ 2ms | ≤ 5ms | ≤ 1ms |
| **State Estimation** | ≤ 2ms | ≤ 5ms | ≤ 1ms |

### **Safety Requirements**
- **Emergency Response:** <100ms for critical safety violations
- **Communication Timeout:** <500ms before emergency procedures
- **Safety Violation Threshold:** ≤10 violations before emergency landing

## **Deployment Modes**

### **Cloud Mode (`--mode=cloud`)**
- Runs Layer 1 (Global Planner) and Layer 2 (SE(3) MPC)
- Requires powerful computing resources
- Handles mission planning and trajectory optimization
- Communicates with edge nodes via ZMQ

### **Edge Mode (`--mode=edge`)**
- Runs Layer 3 (Reactive Controller)
- Optimized for embedded hardware
- Handles real-time control and safety
- Communicates with cloud nodes via ZMQ

This 3-layer architecture provides a strong foundation for DART-Planner, effectively distributing the computational burden and allowing each component to operate within its optimal domain while maintaining strict real-time and safety requirements.
