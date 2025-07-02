# 🎮 AirSim Integration Guide for DART-Planner

## **Mission Objective**
Validate DART-Planner's **2,496x performance breakthrough** (5,241ms → 2.1ms) in realistic AirSim simulation before hardware deployment.

---

## 🎯 **Why AirSim Integration?**

### **Perfect Bridge to Hardware** 🌉
- **Realistic Physics**: AirSim provides accurate flight dynamics
- **Visual Simulation**: 3D environment with realistic sensors
- **API Control**: Direct integration with DART-Planner algorithms
- **Hardware Preparation**: Validates system before costly real flights

### **Risk Mitigation** 🛡️
- **Algorithm Validation**: Test SE(3) MPC in realistic conditions
- **Performance Verification**: Confirm 2.1ms planning time holds
- **Safety Testing**: Validate failsafe behavior in safe environment
- **Mission Planning**: Test complex autonomous flight scenarios

---

## 🚀 **Quick Start (5 Minutes)**

### **1. Install Dependencies**
```bash
# Install AirSim Python packages
python scripts/setup_airsim_validation.py --install-deps

# Or manually:
pip install airsim pymavlink msgpack-rpc-python
```

### **2. Download AirSim Application**
- Visit: [AirSim Releases](https://microsoft.github.io/AirSim/)
- Download for your OS (Windows/Linux/Mac)
- Extract to folder (e.g., `C:\AirSim` or `~/AirSim`)

### **3. Quick Setup**
```bash
# Create AirSim settings and show setup guide
python scripts/setup_airsim_validation.py
```

### **4. Test Connection**
```bash
# Launch AirSim, then test connection
python scripts/setup_airsim_validation.py --test
```

### **5. Run DART-Planner Validation**
```bash
# Full autonomous mission validation
python scripts/setup_airsim_validation.py --full-validation
```

---

## 📊 **Validation Targets**

### **Performance Metrics**
| Metric | Target | Breakthrough Baseline |
|--------|--------|----------------------|
| **Planning Time** | <20ms | 2.1ms (simulation) |
| **Control Frequency** | >80Hz | 479Hz capability |
| **Mission Success** | 100% | 100% (10/10 tests) |
| **Trajectory Accuracy** | <2m RMS | <1m achieved |

### **Success Criteria** ✅
- [ ] **Planning Performance**: Mean planning time <20ms
- [ ] **Real-time Control**: Achieved frequency >80Hz  
- [ ] **Mission Completion**: 100% autonomous waypoint navigation
- [ ] **Safety Systems**: Proper failsafe activation when needed

---

## 🏗️ **Detailed Setup Instructions**

### **AirSim Application Setup**

#### **1. Download & Install**
```bash
# Windows
curl -L -o AirSim.zip https://github.com/Microsoft/AirSim/releases/latest/download/AirSim-Windows.zip
unzip AirSim.zip -d C:\AirSim

# Linux
curl -L -o AirSim.tar.gz https://github.com/Microsoft/AirSim/releases/latest/download/AirSim-Linux.tar.gz
tar -xzf AirSim.tar.gz -C ~/AirSim
```

#### **2. Configuration File**
Create `settings.json` in:
- **Windows**: `%USERPROFILE%\Documents\AirSim\settings.json`
- **Linux/Mac**: `~/Documents/AirSim/settings.json`

```json
{
  "SeeDocsAt": "https://github.com/Microsoft/AirSim/blob/master/docs/settings.md",
  "SettingsVersion": 1.2,
  "SimMode": "Multirotor",
  "ClockSpeed": 1.0,
  "ViewMode": "FlyWithMe",
  "Vehicles": {
    "Drone1": {
      "VehicleType": "SimpleFlight",
      "DefaultVehicleState": "Armed",
      "EnableCollisionPassthrogh": false,
      "EnableCollisions": true,
      "AllowAPIAlways": true,
      "RC": {
        "RemoteControlID": 0,
        "AllowAPIWhenDisconnected": true
      }
    }
  }
}
```

### **DART-Planner Integration**

#### **Interface Configuration**
```python
# Conservative settings for AirSim validation
config = AirSimConfig(
    control_frequency=100.0,  # Conservative from 479Hz capability
    planning_frequency=5.0,   # DART-Planner optimization frequency
    max_planning_time_ms=20.0,  # Allow overhead for AirSim
    waypoint_tolerance=2.0    # 2m waypoint tolerance
)
```

#### **Mission Definition**
```python
# Validation mission: 15x15m square at 10m altitude
waypoints = [
    np.array([15.0, 0.0, 10.0]),   # Forward
    np.array([15.0, 15.0, 10.0]),  # Right turn
    np.array([0.0, 15.0, 10.0]),   # Backward
    np.array([0.0, 0.0, 10.0])     # Return home
]
```

---

## 🧪 **Validation Test Scenarios**

### **Test 1: Basic Connection**
**Objective**: Verify AirSim connectivity and DART-Planner initialization
```bash
python scripts/setup_airsim_validation.py --test
```
**Expected**: Successful connection, API control enabled

### **Test 2: Planning Performance**
**Objective**: Validate SE(3) MPC planning time in AirSim environment
```python
# Check planning performance
interface = AirSimInterface()
await interface.connect()

# Measure planning time for single goal
start_time = time.perf_counter()
trajectory = interface.planner.plan_trajectory(current_state, goal)
planning_time = (time.perf_counter() - start_time) * 1000  # ms

assert planning_time < 20.0, f"Planning too slow: {planning_time}ms"
```

### **Test 3: Autonomous Mission**
**Objective**: Complete autonomous waypoint navigation
```bash
python scripts/setup_airsim_validation.py --full-validation
```
**Expected**: 
- Complete 4-waypoint square pattern
- Maintain planning time <20ms
- Achieve control frequency >80Hz
- Return to starting position

### **Test 4: Failure Scenarios**
**Objective**: Validate failsafe behavior
```python
# Test scenarios:
# 1. Invalid waypoint (outside bounds)
# 2. Planning timeout simulation  
# 3. Communication loss handling
# 4. Emergency stop response
```

---

## 📈 **Performance Analysis**

### **Real-time Monitoring**
During validation, monitor key metrics:

```python
# Performance tracking during mission
performance_stats = {
    "planning_times": [],      # Target: <20ms mean
    "control_frequency": 0.0,  # Target: >80Hz
    "mission_progress": 0.0,   # Target: 100%
    "position_errors": [],     # Target: <2m RMS
}
```

### **Success Validation**
```python
def validate_performance(report):
    """Validate DART-Planner performance in AirSim"""
    criteria = [
        ("Planning Time", report['mean_planning_time_ms'] < 20.0),
        ("Control Freq", report['achieved_frequency'] > 80.0),
        ("Success Rate", report['planning_success_rate'] > 0.95),
        ("Mission Complete", report['waypoint_progress'] == "4/4")
    ]
    
    for name, passed in criteria:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    return all(passed for _, passed in criteria)
```

---

## 🚁 **Integration with PX4 SITL (Advanced)**

### **Why PX4 SITL?**
- **Realistic Flight Controller**: Actual autopilot software
- **MAVLink Protocol**: Industry-standard communication
- **Hardware Preparation**: Mirrors real Pixhawk setup

### **Setup Commands**
```bash
# Install PX4 SITL
git clone https://github.com/PX4/Firmware.git
cd Firmware
make px4_sitl_default gazebo

# Launch with AirSim
make px4_sitl_default airsim_iris
```

### **DART-Planner Integration**
```python
# Enable PX4 SITL mode in AirSim interface
config = AirSimConfig(
    use_px4_sitl=True,
    mavlink_connection="udp:127.0.0.1:14550"
)
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **Connection Failed**
```
❌ AirSim connection failed: ConnectionError
```
**Solutions**:
- Ensure AirSim is running
- Check firewall settings
- Verify IP/port configuration (default: 127.0.0.1:41451)

#### **Planning Too Slow**
```
⚠️ Slow planning: 35.2ms
```
**Solutions**:
- Reduce `max_iterations` in SE3MPCConfig
- Increase `convergence_tolerance` for faster convergence
- Check CPU load and close unnecessary applications

#### **Vehicle Not Responding**
```
❌ Vehicle not moving to waypoints
```
**Solutions**:
- Verify `AllowAPIAlways: true` in settings.json
- Check vehicle is armed and API control enabled
- Confirm coordinate system (ENU vs NED)

### **Performance Optimization**

#### **For Better Planning Performance**
```python
# Optimized config for AirSim
planner_config = SE3MPCConfig(
    prediction_horizon=4,      # Reduce from 6
    dt=0.2,                   # Increase time step
    max_iterations=15,        # Reduce iterations
    convergence_tolerance=5e-2  # Relax tolerance
)
```

#### **For Better Control Frequency**
```python
# Reduce control frequency if needed
config = AirSimConfig(
    control_frequency=50.0,   # Reduce from 100Hz
    planning_frequency=2.0    # Reduce planning rate
)
```

---

## 🎯 **Expected Results**

### **Successful Validation Output**
```
🎉 DART-PLANNER AIRSIM VALIDATION: SUCCESS!
📊 Performance Results:
   Planning Time: 8.3ms (Target: <20ms) ✅
   Control Frequency: 95Hz (Target: >80Hz) ✅
   Mission Success: 100% (4/4 waypoints) ✅
   Position Accuracy: 1.2m RMS ✅

🚀 Ready for hardware deployment!
```

### **Performance Comparison**
| Metric | Original System | AirSim Validation | Hardware Target |
|--------|----------------|-------------------|-----------------|
| Planning Time | 5,241ms | 8-15ms | <10ms |
| Control Freq | 100Hz | 80-120Hz | >200Hz |
| Success Rate | 25% | 100% | >95% |
| Position Error | 193.9m | 1-3m | <1m |

---

## 🚀 **Next Steps After Validation**

### **If Validation Successful** ✅
1. **PX4 SITL Integration**: Add realistic flight controller
2. **Hardware-in-the-Loop**: Connect real Pixhawk hardware
3. **Real Flight Testing**: Follow 4-phase hardware roadmap

### **If Performance Issues** ⚠️
1. **Algorithm Optimization**: Tune SE(3) MPC parameters
2. **Computational Optimization**: Profile and optimize bottlenecks
3. **Hardware Upgrade**: Consider more powerful onboard computer

### **Documentation & Publication** 📚
1. **Performance Data**: Document AirSim validation results
2. **Academic Paper**: Include AirSim validation in publication
3. **Open Source**: Share validated AirSim integration

---

## 📚 **References & Resources**

### **AirSim Documentation**
- [AirSim Official Docs](https://microsoft.github.io/AirSim/)
- [AirSim Python APIs](https://microsoft.github.io/AirSim/apis/)
- [AirSim Settings Reference](https://microsoft.github.io/AirSim/settings/)

### **DART-Planner Documentation**
- [Hardware Validation Roadmap](../HARDWARE_VALIDATION_ROADMAP.md)
- [Breakthrough Summary](../analysis/BREAKTHROUGH_SUMMARY.md)
- [Performance Comparison](../analysis/SYSTEM_TEST_SUMMARY.md)

### **Integration Examples**
- [AirSim Interface](../../src/hardware/airsim_interface.py)
- [Validation Script](../../scripts/setup_airsim_validation.py)
- [SE(3) MPC Planner](../../src/planning/se3_mpc_planner.py)

---

**🎮 AirSim integration bridges the gap between breakthrough simulation results and real-world hardware deployment, providing confident validation of DART-Planner's revolutionary performance improvements.** 