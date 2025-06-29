# DART-Planner: Critical Technical Refactor Strategy

## Executive Summary

This document outlines the systematic refactor of DART-Planner based on a comprehensive technical analysis that identified four critical flaws in the original architecture. These issues pose unacceptable risks to system reliability, safety, and real-world viability.

## Critical Problems Identified

### Problem 1: Misapplied Control Algorithm (DIAL-MPC)

**Issue**: The current system uses DIAL-MPC as the core trajectory optimizer, but this algorithm was explicitly designed for **legged locomotion** with contact-rich dynamics (feet making/breaking contact with ground). 

**Evidence**: 
- DIAL-MPC paper [2409.15610] states it was "explicitly developed for torque-level control of legged robots"
- Aerial robots have fundamentally different dynamics (underactuated, no contact forces)
- Current implementation shows trajectory inconsistency issues (193.9m mean error initially)

**Risk**: Suboptimal or potentially unstable flight control due to algorithm mismatch with physical domain.

### Problem 2: Over-Reliance on Immature Neural Perception

**Issue**: The architecture places critical real-time planning decisions on NeRF/3DGS neural scene representation, expecting it to function as a "magic oracle" for geometry, dynamics, semantics, and uncertainty.

**Evidence**:
- State-of-the-art Splat-Nav paper shows only ~2Hz replanning capability
- Current `BaseNeuralScene` interface expects real-time density queries for DIAL-MPC
- No fallback mapping system for when neural model fails or is slow

**Risk**: System failure when neural model is too slow, noisy, or fails to converge.

### Problem 3: Fragile Cloud-Dependent Architecture  

**Issue**: The three-layer architecture places all high-level intelligence (Layers 1 & 2) in the cloud, creating a critical dependency on network connectivity.

**Evidence**:
- Current architecture requires continuous cloud connection for trajectory planning
- Failsafe logic is inadequate (simple "hover" command)
- Network outage = "brainless" drone

**Risk**: Catastrophic failure during network disruption in dynamic environments.

### Problem 4: Insufficient Engineering Rigor

**Issue**: The codebase lacks professional software engineering practices required for safety-critical autonomous systems.

**Evidence**:
- Missing comprehensive test coverage
- Insufficient benchmarking against proven baselines
- Simulation-only validation approach
- Incomplete documentation and type coverage

**Risk**: Unreliable, unmaintainable system prone to unexpected failures.

## Refactor Strategy

### Strategy 1: Replace DIAL-MPC with Domain-Appropriate Control

**Action**: Implement SE(3) Model Predictive Control designed specifically for aerial robotics.

**Implementation**:
1. Create `src/planning/se3_mpc_planner.py` - SE(3) formulation for quadrotor dynamics
2. Keep `dial_mpc_planner.py` for benchmarking comparison
3. Add cascaded PID/LQR baseline controller
4. Implement quantitative benchmarking framework

**Expected Outcome**: Dramatically improved trajectory tracking and system stability.

### Strategy 2: Hybrid Perception Architecture

**Action**: Implement dual-map system with explicit geometric mapping for safety-critical operations.

**Implementation**:
1. Enhance `src/perception/explicit_geometric_mapper.py` - Real-time SLAM integration
2. Refactor neural scene to offline/advisory role only
3. Add obstacle detection and tracking module
4. Create "proxy oracle" for development/testing

**Expected Outcome**: Reliable real-time collision avoidance with neural intelligence as enhancement, not dependency.

### Strategy 3: Edge-First Resilient Architecture

**Action**: Invert architecture priority - make edge autonomous, cloud advisory.

**Implementation**:
1. Enhance `src/edge/onboard_autonomous_controller.py` - Full autonomy capability
2. Refactor cloud components to provide high-level guidance only
3. Implement tiered failsafe logic (nominal → degraded → autonomous → emergency)
4. Add comprehensive system monitoring and watchdogs

**Expected Outcome**: Robust operation even with poor or no network connectivity.

### Strategy 4: Professional Engineering Standards

**Action**: Implement commercial-grade software engineering practices.

**Implementation**:
1. Comprehensive test suite (unit, integration, hardware-in-loop)
2. Monte Carlo stress testing for robustness validation
3. Complete API documentation and type annotations
4. Continuous integration with quality gates

**Expected Outcome**: Reliable, maintainable, and trustworthy codebase.

## Implementation Phases

### Phase 1: Core Algorithm Replacement (Week 1)
- [ ] Implement SE(3) MPC planner
- [ ] Create benchmarking framework
- [ ] Performance comparison studies

### Phase 2: Perception System Redesign (Week 2)  
- [ ] Enhance explicit geometric mapper
- [ ] Refactor neural scene integration
- [ ] Add SLAM interface layer

### Phase 3: Architecture Resilience (Week 3)
- [ ] Implement edge-first design
- [ ] Add tiered failsafe system
- [ ] System monitoring framework

### Phase 4: Engineering Quality (Week 4)
- [ ] Comprehensive test coverage
- [ ] Documentation completion
- [ ] CI/CD pipeline enhancement
- [ ] Stress testing implementation

## Success Metrics

1. **Control Performance**: <10m mean tracking error (vs 193.9m original)
2. **Real-time Capability**: Maintain >100Hz control frequency with new algorithms
3. **Robustness**: Zero failsafe activations under normal operation
4. **Resilience**: Graceful degradation during network outages
5. **Code Quality**: >90% test coverage, 100% type annotation coverage

## Risk Mitigation

1. **Backward Compatibility**: Keep original implementations for comparison
2. **Incremental Deployment**: Phase-by-phase validation with rollback capability
3. **Comprehensive Testing**: SITL → HIL → Real-world progression
4. **Documentation**: Every change documented with rationale

This refactor transforms DART-Planner from a high-risk research concept into a robust, production-ready autonomous flight system. 