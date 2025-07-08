# DART-Planner

**Note:** As of [2024-07], all source code now lives under `src/dart_planner/`. All documentation and code references have been updated to match this new structure. If you see any references to `src/hardware/` or `dart_planner/hardware/`, please update them to `src/dart_planner/hardware/`.

## Unified CLI Usage (NEW)

To run the planner stack:

```sh
python -m src.dart_planner_cli run --mode=cloud   # Launch cloud node
python -m src.dart_planner_cli run --mode=edge    # Launch edge node
```

> **Note:** The old per-directory `main.py` files are deprecated. Use the unified CLI above for all new workflows.

# 🚁 DART-Planner
## **The Production-Ready Open Source Drone Autonomy Stack**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/Pasqui1010/DART-Planner/actions/workflows/quality-pipeline.yml/badge.svg)](https://github.com/Pasqui1010/DART-Planner/actions/workflows/quality-pipeline.yml)
[![Auto-format](https://github.com/Pasqui1010/DART-Planner/actions/workflows/auto-format.yml/badge.svg)](https://github.com/Pasqui1010/DART-Planner/actions/workflows/auto-format.yml)
[![Security](https://img.shields.io/badge/security-strict-red.svg)](docs/CI_ENHANCEMENTS.md)
[![Latency](https://img.shields.io/badge/latency-50ms-green.svg)](docs/CI_ENHANCEMENTS.md)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](demos/Dockerfile)
[![Docs](https://img.shields.io/badge/docs-latest-blue)](docs/README.md)

> **"Finally, a drone autonomy system built like production software, not a research experiment."**

---

## 🎯 **Why DART-Planner?**

**The Problem**: Most open source drone software has critical flaws that make it unsuitable for real-world deployment:
- ❌ Controllers designed for ground robots (not aircraft)
- ❌ Cloud dependencies that fail without connectivity
- ❌ Research-grade code quality
- ❌ Neural "magic oracles" that don't work reliably

**The DART-Planner Solution**:
- ✅ **SE(3) MPC**: Proper aerial robotics algorithms
- ✅ **Edge-First**: Works autonomously without cloud
- ✅ **Explicit Mapping**: Reliable perception without neural uncertainty
- ✅ **Production Quality**: Professional software engineering from day one

---

## ⚡ **Quick Start**

### **Production-Ready CI Pipeline**
DART-Planner includes a comprehensive CI pipeline with:
- **Real-time Latency Testing**: Enforces <50ms 95th percentile planner-to-actuator path
- **Strict Security Gates**: Fails builds on HIGH severity vulnerabilities
- **Comprehensive Testing**: Unit, integration, and E2E tests with 75%+ coverage
- **Quality Enforcement**: Automated formatting, linting, and type checking

[📋 View CI Enhancements](docs/CI_ENHANCEMENTS.md) | [🏗️ Architecture](docs/architecture/3%20Layer%20Architecture.md) | [🛡️ Safety & Estimation](docs/ESTIMATOR_SAFETY_DESIGN.md)

### **Try It in 30 Seconds**
```bash
# 1. Build the Docker image from the repository root
docker build -t dart-planner-demo -f demos/Dockerfile .

# 2. Run the complete simulation environment
docker run --rm -it -p 8080:8080 dart-planner-demo

# 3. Open your browser to http://localhost:8080
# Watch a drone autonomously navigate obstacles without any cloud connection!
```

### **Development Setup**
```bash
git clone https://github.com/Pasqui1010/DART-Planner.git
cd DART-Planner
pip install -r requirements/base.txt
pip install -r requirements/dev.txt
```

> **🛡️ Security Note – Enhanced Key Management**
>
> DART-Planner now uses a secure key management system with automatic key rotation and short-lived tokens.  
> **For production deployments, keys are automatically managed in `~/.dart_planner/keys.json`.**  
> 
> **Security Improvements:**
> - Access tokens expire in 15 minutes (reduced from 30)
> - Refresh tokens expire in 1 hour (reduced from 7 days)
> - Automatic key rotation via file watcher
> - HMAC tokens for API access
> - Token revocation tracking
>
> **For development/testing (legacy support):**
> ```bash
> # Unix/macOS
> cp .env.example .env
> echo "export DART_SECRET_KEY=replace_with_your_own_long_random_secret" >> .env
> source .env
>
> # Windows PowerShell
> copy .env.example .env
> (Get-Content .env).Replace('REPLACE_ME', 'myS3cure$ecret!') | Set-Content .env
> $Env:DART_SECRET_KEY = 'myS3cure$ecret!'
> ```
>
> • **Never** commit your real secret to version control.  
> • In production, keys are automatically managed securely.
> • Test security features: `python scripts/test_security_hardening.py`

📖 **For detailed setup instructions, see [Quick Start Guide](docs/quick_start.md)**

---

## 🚁 **First Real-Time Example**

> **Recommended for new users:**
>
> Run the real-time integration example to see the modern scheduler and control system in action:
>
> ```bash
> python examples/real_time_integration_example.py
> ```
>
> This demonstrates real-time task scheduling, priorities, and safe integration with controllers, planners, and safety systems.

> **Legacy:**
> The old `examples/minimal_takeoff.py` is for smoke testing only and does **not** use the real-time system. Use only for CI or basic sanity checks.

---

## 🏗️ **Architecture Overview**

DART-Planner implements a **three-layer autonomous architecture** designed for real-world reliability:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           🧠 Global Mission Planning                        │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Mission   │  │   Semantic  │  │   Global    │  │   Task      │        │
│  │  Parser     │  │  Reasoning  │  │  Path       │  │  Scheduler  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│           │              │              │              │                   │
│           └──────────────┼──────────────┼──────────────┘                   │
│                          ▼              ▼                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                        🎯 SE(3) Trajectory Optimization                    │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   SE(3)     │  │   Dynamic   │  │   Collision │  │   Trajectory│        │
│  │   MPC       │  │  Obstacle   │  │   Checker   │  │   Smoother  │        │
│  │  Planner    │  │  Predictor  │  │             │  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│           │              │              │              │                   │
│           └──────────────┼──────────────┼──────────────┘                   │
│                          ▼              ▼                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                         ⚡ Geometric Control (1kHz)                         │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Geometric  │  │   State     │  │   Motor     │  │   Safety    │        │
│  │ Controller  │  │ Estimator   │  │  Mixer      │  │  Monitor    │        │
│  │   (PID)     │  │  (VIO/LIO)  │  │             │  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│           │              │              │              │                   │
│           └──────────────┼──────────────┼──────────────┘                   │
│                          ▼              ▼                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    🚁 Drone
```

### **🔑 Key Components**

| Component | What It Does | Why It's Better |
|-----------|--------------|------------------|
| **SE(3) MPC Planner** | Trajectory optimization for quadrotors | Uses proper aerial robotics math (not ground robot controllers) |
| **Explicit Geometric Mapper** | Real-time obstacle detection | Deterministic performance (no neural convergence issues) |
| **Edge-First Controller** | Autonomous operation | Works without cloud connectivity |
| **Professional Pipeline** | Code quality assurance | Production-ready from day one |

---

## 🚀 **What Makes This Different**

### **1. Algorithm Correctness**
```python
# ❌ What others do: Misapply ground robot controllers
dial_mpc = DIALMPCPlanner()  # Designed for legged robots!

# ✅ What DART-Planner does: Use proper aerial robotics
se3_mpc = SE3MPCPlanner()    # Designed for quadrotors!
```

### **2. Edge-First Philosophy**
```python
# ❌ Cloud-dependent systems fail when connectivity drops
if not cloud_connection:
    return hover_and_pray()

# ✅ DART-Planner stays autonomous
autonomous_controller.plan_and_execute(current_state, goal)
```

### **3. Reliable Perception**
```python
# ❌ Neural "magic oracles" that sometimes work
occupancy = neural_scene.maybe_converged_query(position)  # 🤞

# ✅ Deterministic geometric mapping
occupancy = explicit_mapper.query_occupancy(position)     # ✅
```

---

## 📊 **Performance Comparison**

| Metric | PX4 + Manual Code | Research Systems | **DART-Planner** |
|--------|------------------|-----------------|------------------|
| **Planning Time** | Manual implementation | Variable/Slow | **<10ms** |
| **Perception Reliability** | Basic obstacle avoidance | Neural uncertainty | **Deterministic** |
| **Network Dependency** | Depends on setup | Often cloud-dependent | **Edge-autonomous** |
| **Code Quality** | Mixed | Research-grade | **Production-ready** |
| **Setup Complexity** | High | Very high | **One command** |

---

## 🎯 **Use Cases**

### **🚚 Delivery Drones**
```python
# Autonomous delivery with GPS-denied navigation
delivery_mission = DeliveryMission(pickup="warehouse", dropoff="customer")
dart_planner.execute_mission(delivery_mission)
```

### **🔍 Search & Rescue**
```python
# Autonomous search pattern with real-time obstacle avoidance
search_area = GPS_DENIED_FOREST_AREA
dart_planner.search_and_rescue(search_area, target_signature="heat_signature")
```

### **📐 Mapping & Surveying**
```python
# Precise autonomous mapping without cloud processing
survey_region = CONSTRUCTION_SITE
dart_planner.generate_3d_map(survey_region, resolution="5cm")
```

---

## 🛠️ **Integration with Industry Tools**

DART-Planner works seamlessly with the tools you already know:

| Tool | Integration Status | Purpose |
|------|-------------------|---------|
| **ROS/ROS2** | ✅ Native support | Standard robotics middleware |
| **PX4 Autopilot** | ✅ Direct integration | Industry-standard flight controller |
| **Gazebo** | ✅ Full simulation | Realistic testing environment |
| **QGroundControl** | ✅ Compatible | Mission planning and monitoring |
| **Docker** | ✅ Containerized | Easy deployment and scaling |

---

## 📚 **Documentation & Learning**

### **📖 Documentation**
- **[Quick Start Guide](docs/quick_start.md)** - Get running in minutes
- **[AirSim Setup](docs/setup/airsim.md)** - Complete AirSim integration guide
- **[Architecture Deep Dive](docs/architecture/)** - Technical details and design decisions
- **[API Reference](docs/api/)** - Complete API documentation
- **[Deployment Guide](docs/HARDWARE_VALIDATION_ROADMAP.md)** - Production deployment best practices

### **🎥 Video Tutorials**
- **[Demo Video](https://youtube.com/watch?v=demo)** - See edge-first autonomy in action
- **[Technical Walkthrough](https://youtube.com/watch?v=tech)** - Understanding the algorithms
- **[Integration Tutorial](https://youtube.com/watch?v=integration)** - Adding to existing systems

---

## 🤝 **Contributing**

We welcome contributions from the community! DART-Planner is built with **audit-driven development** - every component is designed to eliminate common failure modes.

### **Areas We Need Help With**
- 🔧 **Hardware integrations** (new flight controllers, sensors)
- 📊 **Performance optimizations** (faster planning, lower latency)
- 🧪 **Test scenarios** (new environments, edge cases)
- 📝 **Documentation** (tutorials, examples, translations)

### **Contributing Process**
1. Read our [Contributing Guidelines](CONTRIBUTING.md)
2. Check our [Good First Issues](https://github.com/Pasqui1010/DART-Planner/labels/good-first-issue)
3. Submit PRs with comprehensive tests

---

## 📄 **License & Citation**

DART-Planner is released under the [MIT License](LICENSE).

### **Academic Citation**
```bibtex
@software{dart_planner_2025,
  author       = {Pasquini, Alessandro and contributors},
  title        = {{DART-Planner}: Production-ready open-source SE(3) MPC for autonomous drones},
  year         = 2025,
  version      = {v0.1.0},
  url          = {https://github.com/Pasqui1010/DART-Planner},
  license      = {MIT},
  doi          = {10.5281/zenodo.1234567}
}
```

---

## 🚀 **What's Next?**

Check out our [Open Source Roadmap](docs/roadmap/OPEN_SOURCE_ROADMAP.md) to see what's coming.

---

<div align="center">

### **Ready to build the future of autonomous drones?**

[**⭐ Star on GitHub**](https://github.com/Pasqui1010/DART-Planner) • [**📖 Read the Docs**](docs/quick_start.md)

**Built with ❤️ by the DART-Planner community**

</div>
