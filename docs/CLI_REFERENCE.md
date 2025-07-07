# DART-Planner CLI Reference

This document provides a quick reference for the unified DART-Planner command-line interface.

## 🚀 **Quick Start**

### **Basic Usage**

```bash
# Run cloud node (Layers 1 & 2)
python -m src.dart_planner_cli run --mode=cloud

# Run edge node (Layer 3)
python -m src.dart_planner_cli run --mode=edge
```

### **Command Structure**

```
python -m src.dart_planner_cli <command> [options]
```

## 📋 **Commands**

### **`run` - Start DART-Planner Stack**

Starts the DART-Planner system in the specified mode.

#### **Options**

| Option | Required | Values | Description |
|--------|----------|--------|-------------|
| `--mode` | Yes | `cloud`, `edge` | Operating mode |

#### **Examples**

```bash
# Start cloud node for mission planning and trajectory optimization
python -m src.dart_planner_cli run --mode=cloud

# Start edge node for real-time control and safety
python -m src.dart_planner_cli run --mode=edge

# Run both modes in separate terminals for full system
# Terminal 1:
python -m src.dart_planner_cli run --mode=cloud
# Terminal 2:
python -m src.dart_planner_cli run --mode=edge
```

## 🏗️ **Operating Modes**

### **Cloud Mode (`--mode=cloud`)**

**Purpose:** Runs the high-level planning and optimization layers.

**Components:**
- **Layer 1:** Global/Strategic Planner
- **Layer 2:** SE(3) MPC Trajectory Optimizer
- **Neural Scene Representation**
- **Mission Management**

**Requirements:**
- Powerful computing resources (CPU/GPU)
- Network connectivity for edge communication
- Configuration for mission parameters

**Typical Use Cases:**
- Mission planning and optimization
- Environment mapping and understanding
- Long-term trajectory generation
- Multi-vehicle coordination

### **Edge Mode (`--mode=edge`)**

**Purpose:** Runs the real-time control and safety layers.

**Components:**
- **Layer 3:** Reactive Controller
- **State Estimation System**
- **Safety Watchdog**
- **Hardware Interface**

**Requirements:**
- Embedded hardware (Pixhawk, companion computer)
- Real-time operating system
- Sensor data (IMU, cameras, GPS)

**Typical Use Cases:**
- Real-time flight control
- Safety monitoring and emergency procedures
- Sensor data processing
- Hardware interface management

## ⚙️ **Configuration**

### **Environment Variables**

```bash
# Set configuration file path
export DART_CONFIG_PATH=/path/to/config.yaml

# Set log level
export DART_LOG_LEVEL=INFO

# Set hardware interface
export DART_HARDWARE_INTERFACE=pixhawk  # or airsim
```

### **Configuration Files**

The system uses YAML configuration files:

```yaml
# config/defaults.yaml
hardware:
  interface: "pixhawk"  # or "airsim"
  connection: "/dev/ttyACM0"

safety:
  max_velocity: 15.0
  max_altitude: 100.0
  heartbeat_timeout_ms: 500

planning:
  prediction_horizon: 10
  dt: 0.1
```

## 🔧 **Development and Testing**

### **Simulation Mode**

For development and testing, use AirSim:

```bash
# Start AirSim first, then run edge mode
python -m src.dart_planner_cli run --mode=edge
```

### **Real Hardware Mode**

For real hardware deployment:

```bash
# Ensure Pixhawk is connected and configured
python -m src.dart_planner_cli run --mode=edge
```

### **Full System Testing**

```bash
# Terminal 1: Start cloud node
python -m src.dart_planner_cli run --mode=cloud

# Terminal 2: Start edge node
python -m src.dart_planner_cli run --mode=edge

# Terminal 3: Monitor logs
tail -f logs/dart_planner.log
```

## 📊 **Monitoring and Debugging**

### **Log Levels**

```bash
# Set log level via environment variable
export DART_LOG_LEVEL=DEBUG
python -m src.dart_planner_cli run --mode=cloud
```

Available log levels:
- `DEBUG`: Detailed debugging information
- `INFO`: General information messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical error messages

### **Performance Monitoring**

The system provides real-time performance metrics:

```bash
# Monitor latency (if latency testing is enabled)
python scripts/test_latency_ci.py --verbose

# Check system status
python scripts/check_system_status.py
```

### **Safety Monitoring**

```bash
# Monitor safety violations
python scripts/monitor_safety.py

# Check heartbeat status
python scripts/check_heartbeat.py
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Import Errors**

```bash
# Ensure you're in the project root directory
cd /path/to/DART-Planner

# Install dependencies
pip install -r requirements/dev.txt

# Try running again
python -m src.dart_planner_cli run --mode=cloud
```

#### **Configuration Errors**

```bash
# Check configuration file
cat config/defaults.yaml

# Validate configuration
python scripts/validate_config.py
```

#### **Hardware Connection Issues**

```bash
# Check hardware connection
python scripts/test_hardware_connection.py

# Verify MAVLink communication
python scripts/test_mavlink.py
```

#### **Network Communication Issues**

```bash
# Check ZMQ connectivity
python scripts/test_zmq_connection.py

# Monitor network traffic
python scripts/monitor_network.py
```

### **Emergency Procedures**

#### **Emergency Stop**

```bash
# Send emergency stop command
python scripts/emergency_stop.py

# Or use keyboard interrupt
Ctrl+C
```

#### **System Reset**

```bash
# Reset system state
python scripts/reset_system.py

# Clear logs
python scripts/clear_logs.py
```

## 📚 **Integration Examples**

### **With Mission Planning**

```bash
# Start cloud node with mission file
export DART_MISSION_FILE=missions/waypoint_mission.yaml
python -m src.dart_planner_cli run --mode=cloud

# Start edge node
python -m src.dart_planner_cli run --mode=edge
```

### **With External Tools**

```bash
# Start cloud node
python -m src.dart_planner_cli run --mode=cloud &

# Use external planning tool
python external_planner.py

# Start edge node
python -m src.dart_planner_cli run --mode=edge
```

### **With Monitoring Tools**

```bash
# Start system with monitoring
python -m src.dart_planner_cli run --mode=cloud &
python -m src.dart_planner_cli run --mode=edge &

# Start monitoring dashboard
python scripts/start_monitoring_dashboard.py
```

## 🔄 **Migration from Legacy Entry Points**

### **Old Entry Points (Deprecated)**

```bash
# OLD - Don't use these anymore
python src/cloud/main.py
python src/edge/main.py
```

### **New Unified Entry Point**

```bash
# NEW - Use this instead
python -m src.dart_planner_cli run --mode=cloud
python -m src.dart_planner_cli run --mode=edge
```

### **Migration Checklist**

- [ ] Update deployment scripts to use new CLI
- [ ] Update CI/CD pipelines
- [ ] Update documentation references
- [ ] Test both modes with new entry point
- [ ] Remove references to old main.py files

## 📖 **Additional Resources**

- [Architecture Documentation](docs/architecture/3%20Layer%20Architecture.md)
- [Safety & Estimation Design](docs/ESTIMATOR_SAFETY_DESIGN.md)
- [CI Enhancements](docs/CI_ENHANCEMENTS.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) 