# 🚁 SITL Integration Guide for DART-Planner

## **Overview**
Software-in-the-Loop (SITL) integration with AirSim provides the most realistic simulation environment before real hardware deployment. This guide covers setting up ArduPilot SITL with AirSim for DART-Planner validation.

## **🔧 Prerequisites**

### **1. ArduPilot SITL Setup**
```bash
# Clone ArduPilot
git clone https://github.com/ArduPilot/ardupilot.git
cd ardupilot
git submodule update --init --recursive

# Build SITL
./waf configure --board sitl
./waf copter

# Install MAVProxy
pip install MAVProxy pymavlink
```

### **2. AirSim Configuration**
Create `~/Documents/AirSim/settings.json`:
```json
{
  "SettingsVersion": 1.2,
  "LogMessagesVisible": true,
  "SimMode": "Multirotor",
  "OriginGeopoint": {
    "Latitude": -35.363261,
    "Longitude": 149.165230,
    "Altitude": 583
  },
  "Vehicles": {
    "Copter": {
      "VehicleType": "SimpleFlight",
      "UseSerial": false,
      "LocalHostIp": "127.0.0.1",
      "UdpIp": "127.0.0.1",
      "UdpPort": 9003,
      "ControlPort": 9002
    }
  }
}
```

## **🚀 Launch Sequence**

### **Step 1: Start AirSim**
1. Launch AirSim with Blocks environment
2. Verify vehicle appears in simulation
3. Note: Keep "Use Less CPU when in Background" unchecked in UE Editor

### **Step 2: Launch ArduPilot SITL**
```bash
cd ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter -f airsim-copter --console --map
```

### **Step 3: Connect DART-Planner**
```python
# Use SITL connection instead of real hardware
from src.hardware.pixhawk_interface import PixhawkInterface

interface = PixhawkInterface()
interface.config.mavlink_connection = "udp:127.0.0.1:14550"  # SITL default
await interface.connect()
```

## **🎯 DART-Planner SITL Integration**

### **Modified Hardware Interface**
```python
# src/hardware/sitl_interface.py
class SITLInterface(PixhawkInterface):
    """SITL-specific interface for DART-Planner"""
    
    def __init__(self):
        super().__init__()
        self.config.mavlink_connection = "udp:127.0.0.1:14550"
        self.config.control_frequency = 400.0  # Hz
        self.config.planning_frequency = 50.0  # Hz
        
    async def setup_sitl_parameters(self):
        """Configure SITL for optimal DART-Planner performance"""
        # Set parameters for SE(3) MPC compatibility
        await self.set_parameter("COM_ARM_WO_GPS", 1)  # Allow arming without GPS
        await self.set_parameter("EK3_ENABLE", 1)      # Enable EKF3
        await self.set_parameter("GPS_TYPE", 1)        # GPS type
```

### **Performance Validation**
```python
# scripts/validate_sitl_performance.py
async def validate_sitl_performance():
    """Validate DART-Planner performance with SITL"""
    
    interface = SITLInterface()
    await interface.connect()
    
    # Test scenarios
    scenarios = [
        "hover_stability",
        "waypoint_navigation", 
        "dynamic_replanning",
        "disturbance_rejection"
    ]
    
    for scenario in scenarios:
        result = await interface.run_scenario(scenario)
        print(f"✅ {scenario}: {result}")
```

## **📊 Expected Performance**

### **SITL Performance Targets**
- **Planning Time**: <5ms (vs 2.1ms simulation)
- **Control Frequency**: 400Hz sustained
- **Mission Success**: >95% completion rate
- **Position Accuracy**: <1m RMS error

### **Validation Metrics**
```python
# Key metrics to validate
metrics = {
    "planning_latency": "Average planning time in ms",
    "control_frequency": "Actual control loop frequency",
    "position_accuracy": "RMS position error",
    "mission_success": "Percentage of completed missions",
    "system_stability": "Uptime and error rates"
}
```

## **🛡️ Safety Considerations**

### **SITL Safety Features**
1. **Geofencing**: Virtual boundaries in simulation
2. **Altitude Limits**: Maximum height restrictions
3. **Emergency Procedures**: Failsafe validation
4. **Communication Loss**: Network failure simulation

### **Testing Safety Scenarios**
```python
# Test safety systems
safety_tests = [
    "geofence_violation",
    "altitude_limit_exceeded", 
    "communication_loss",
    "sensor_failure",
    "emergency_landing"
]
```

## **🔍 Debugging and Development**

### **MAVProxy Console**
```bash
# Connect to SITL console
mavproxy.py --master=127.0.0.1:14550 --console --map

# Useful commands:
# mode GUIDED    # Set flight mode
# arm throttle   # Arm vehicle
# wp load        # Load waypoints
# param show     # Show parameters
```

### **Log Analysis**
```bash
# SITL generates logs in ardupilot/logs/
# Analyze with Mission Planner or custom tools
```

## **🚀 Next Steps After SITL**

1. **✅ SITL Validation**: Complete all test scenarios
2. **🔧 HIL Testing**: Connect real Pixhawk hardware
3. **✈️ Tethered Flight**: Real hardware with safety tethers
4. **🌟 Free Flight**: Full autonomous operation

## **📚 Resources**

- [ArduPilot SITL Documentation](https://ardupilot.org/dev/docs/sitl-with-airsim.html)
- [AirSim API Reference](https://microsoft.github.io/AirSim/)
- [MAVLink Protocol](https://mavlink.io/en/)
- [DART-Planner Hardware Interface](../src/hardware/pixhawk_interface.py)

---

**Status**: Ready for implementation  
**Complexity**: Medium  
**Timeline**: 1-2 weeks  
**Risk Level**: 🟢 Low 