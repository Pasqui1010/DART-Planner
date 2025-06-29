# **Project 2: Advanced Aerial Robot Navigation and Control \- 3-Layer Hierarchical Architecture**

This document outlines the proposed three-layer hierarchical architecture for the drone's autonomous navigation and control system in Project 2\. This design explicitly separates concerns to overcome onboard computational limits, manage system complexity, and leverage the strengths of specialized algorithms and computing environments.

## **Overall Philosophy: Cloud for Intelligence, Edge for Real-time Control and Safety**

The core principle of this architecture is to assign computationally intensive, high-level "cognitive" tasks (understanding, long-term planning, optimization) to the powerful **Cloud Node**, while delegating time-critical, high-frequency "reflexive" tasks (direct flight control, immediate reaction to local hazards) to the resource-constrained **Onboard (Edge) Node**. Communication between layers is deliberately designed to be robust and asynchronous, mitigating network vulnerabilities.

## **Layer 1: Global/Strategic Planner**

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

## **Layer 2: Local Trajectory Optimizer (DIAL-MPC)**

This layer refines the high-level plan into a precise, dynamically feasible, and optimal trajectory.

* **Purpose/Role:** To take a short segment of the global plan (from Layer 1\) and generate a detailed, smooth, and dynamically optimal reference trajectory for the drone to follow over a short prediction horizon. It performs online optimization to account for local dynamics and immediate obstacles.
* **Location:** **Cloud Node** (utilizes cloud compute for DIAL-MPC's demanding optimization).
* **Key Algorithms/Components:**
  * **DIAL-MPC (Diffusion-Inspired Annealing for Legged Model Predictive Control, adapted for aerial dynamics):** The core algorithm for this layer. It excels at finding optimal solutions in non-convex problem spaces.
    * Its "sampling-based" nature with "diffusion-style annealing" allows it to navigate complex local scenarios.
    * It uses the drone's **full nonlinear dynamics model** for accurate predictions.
  * **Local Scene Query Interface:** Queries the Neural Scene Representation (also in the Cloud) for detailed local dynamic obstacle information, semantic labels, and uncertainty values within its prediction horizon.
  * **Cost Function:** Designed to enforce dynamic feasibility, smoothness, energy efficiency, trajectory tracking, and incorporate penalties based on semantic information (e.g., proximity to certain objects) and uncertainty.
* **Inputs:**
  * Drone's current estimated state (periodically updated from Layer 3).
  * The next segment of the global plan/waypoints/corridor from Layer 1\.
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

## **Layer 3: Reactive Controller**

This is the drone's onboard "reflex" system, responsible for immediate flight execution.

* **Purpose/Role:** To execute the precise, optimal reference trajectory received from Layer 2 at a very high frequency. It ensures drone stability, rejects disturbances, and provides immediate, local safety overrides.
* **Location:** **Onboard (Edge) Node** (running on the drone's embedded processor).
* **Key Algorithms/Components:**
  * **High-Frequency Control Loop (e.g., Geometric Controller or Cascaded PID):** This is the core flight control algorithm that translates desired states into motor commands. It's designed for speed and robustness, not complex optimization.
  * **Robust State Estimation (VIO/LIO):** Processes onboard sensor data (IMU, cameras, LiDAR) to provide the drone's accurate real-time state (position, velocity, attitude, angular rates) even in GPS-denied environments.
  * **Fast Local Obstacle Avoidance (Reactive):** Uses direct readings from immediate local sensors (e.g., depth cameras, ultrasonic sensors) to implement fast, simple collision prevention, acting as a safety override if an unpredicted or extremely close obstacle is detected.
  * **Failsafe Logic/Mode Switching:** Manages predefined safe behaviors (e.g., hover, slow down, safe landing) in case of communication loss with the cloud or detection of critical onboard failures.
* **Inputs:**
  * Drone's current estimated state from onboard VIO/LIO.
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

This 3-layer architecture provides a strong foundation for Project 2, effectively distributing the computational burden and allowing each component to operate within its optimal domain.
