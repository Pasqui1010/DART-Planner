# 🚁 AirSim Setup Guide

Complete guide for setting up Microsoft AirSim with DART-Planner for drone simulation and testing.

## 📋 **Prerequisites**

### **System Requirements**
- **OS**: Windows 10/11 (recommended) or Ubuntu 20.04+
- **CPU**: Intel i5-8400 / AMD Ryzen 5 2600 or better
- **RAM**: 8 GB minimum, 16 GB recommended
- **GPU**: Integrated graphics minimum, dedicated GPU recommended
- **Storage**: 10 GB free space

### **Software Dependencies**
- **Python**: 3.8+ with pip
- **Git**: For cloning repositories
- **CMake**: 3.16+ (for building from source)
- **Visual Studio**: 2019+ (Windows) or GCC 7+ (Linux)

## 🛠️ **Installation Methods**

### **Method 1: Pre-built Binaries (Recommended)**

#### **Windows**
1. Download the latest AirSim release from [GitHub Releases](https://github.com/microsoft/AirSim/releases)
2. Extract to a directory (e.g., `C:\AirSim`)
3. Add the AirSim directory to your system PATH
4. Test installation:
   ```bash
   AirSimNH.exe -windowed
   ```

#### **Linux**
```bash
# Download and extract pre-built binary
wget https://github.com/microsoft/AirSim/releases/download/v1.8.1/AirSimNH-Linux.zip
unzip AirSimNH-Linux.zip -d AirSim
cd AirSim
chmod +x AirSimNH.sh
./AirSimNH.sh
```

### **Method 2: Build from Source**

#### **Windows**
```bash
# Clone AirSim repository
git clone https://github.com/microsoft/AirSim.git
cd AirSim

# Install dependencies (if not already installed)
# - Visual Studio 2019 or later
# - CMake 3.16 or later

# Build AirSim
build.cmd

# The built executable will be in:
# AirSim\Unreal\Environments\Blocks\WindowsNoEditor\AirSimNH.exe
```

#### **Linux**
```bash
# Install system dependencies
sudo apt update
sudo apt install build-essential cmake git

# Clone and build AirSim
git clone https://github.com/microsoft/AirSim.git
cd AirSim
./setup.sh
./build.sh

# The built executable will be in:
# AirSim/Unreal/Environments/Blocks/LinuxNoEditor/AirSimNH.sh
```

## ⚙️ **Configuration**

### **AirSim Settings File**

Create `airsim_settings.json` in your project root:

```json
{
  "SettingsVersion": 1.2,
  "SimMode": "SimpleFlight",
  "Vehicles": {
    "SimpleFlight": {
      "VehicleType": "SimpleFlight",
      "X": 0,
      "Y": 0,
      "Z": -2,
      "Yaw": 0
    }
  },
  "CameraDirector": {
    "X": 0,
    "Y": -10,
    "Z": 5,
    "Pitch": -30,
    "Yaw": 0
  },
  "SubWindows": [
    {
      "WindowID": 0,
      "ImageType": 0,
      "CameraName": "front_center",
      "Visible": true
    }
  ]
}
```

### **Advanced Configuration Options**

#### **Physics Settings**
```json
{
  "PhysicsEngineName": "FastPhysicsEngine",
  "ClockType": "SteppableClock",
  "ClockSpeed": 1.0,
  "Recording": {
    "RecordOnMove": false,
    "RecordInterval": 0.05
  }
}
```

#### **Sensor Configuration**
```json
{
  "Sensors": {
    "Imu": {
      "SensorType": 1,
      "Enabled": true
    },
    "Gps": {
      "SensorType": 3,
      "Enabled": true
    },
    "Magnetometer": {
      "SensorType": 4,
      "Enabled": true
    },
    "Barometer": {
      "SensorType": 5,
      "Enabled": true
    }
  }
}
```

## 🔧 **DART-Planner Integration**

### **Environment Variables**
```bash
# Set these in your shell or .env file
export DART_PLANNER_LOG_LEVEL=INFO
export DART_PLANNER_SIM_MODE=airsim
export DART_PLANNER_CONTROL_FREQ=1000
export AIRSIM_HOST=127.0.0.1
export AIRSIM_PORT=41451
```

### **Python Configuration**
```python
from src.hardware import AirSimConfig, AirSimDroneInterface

# Configure AirSim interface
config = AirSimConfig(
    ip="127.0.0.1",
    port=41451,
    timeout_value=10.0,
    vehicle_name="SimpleFlight",
    enable_api_control=True,
    max_velocity=10.0,
    max_acceleration=5.0
)

# Create and connect
interface = AirSimDroneInterface(config)
await interface.connect()
```

## 🧪 **Testing AirSim Integration**

### **Basic Connection Test**
```python
#!/usr/bin/env python3
"""Test AirSim connection"""

import asyncio
from src.hardware import AirSimDroneInterface, AirSimConfig

async def test_connection():
    config = AirSimConfig()
    interface = AirSimDroneInterface(config)
    
    try:
        if await interface.connect():
            print("✅ AirSim connection successful!")
            
            # Get initial state
            state = await interface.get_state()
            print(f"📍 Initial position: {state.position}")
            
            await interface.disconnect()
            print("✅ Disconnected safely!")
        else:
            print("❌ Failed to connect to AirSim")
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

### **Run SITL Tests**
```bash
# Mock mode (no AirSim required)
python tests/test_dart_sitl_comprehensive.py --mock-mode

# Full integration test (requires AirSim running)
python tests/test_dart_sitl_comprehensive.py

# Performance benchmarks
python scripts/run_sitl_tests.py --benchmark
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Connection Refused**
```
❌ Failed to connect to AirSim: Connection refused
```

**Solutions:**
1. Ensure AirSim is running before starting DART-Planner
2. Check if AirSim is listening on the correct port (default: 41451)
3. Verify firewall settings aren't blocking the connection
4. Try restarting AirSim

#### **API Control Not Enabled**
```
❌ API control not enabled
```

**Solutions:**
1. Make sure `enable_api_control=True` in your configuration
2. Check that the vehicle name matches your AirSim settings
3. Restart AirSim after changing settings

#### **Vehicle Not Found**
```
❌ Vehicle 'SimpleFlight' not found
```

**Solutions:**
1. Verify the vehicle name in `airsim_settings.json`
2. Check that `SimMode` is set to `"SimpleFlight"`
3. Restart AirSim after configuration changes

#### **Performance Issues**
```
⚠️ Control frequency below target
```

**Solutions:**
1. Reduce control frequency in configuration
2. Close other applications to free up CPU
3. Use mock mode for development without AirSim
4. Check system resource usage

### **Debug Mode**

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or in configuration
config = AirSimConfig(
    log_level=logging.DEBUG,
    enable_trace_logging=True
)
```

### **Network Diagnostics**

Test network connectivity:
```bash
# Test if AirSim is listening
netstat -an | grep 41451

# Test connection with telnet
telnet 127.0.0.1 41451

# Test with curl (if AirSim supports HTTP)
curl http://127.0.0.1:41451/health
```

## 📚 **Advanced Topics**

### **Custom Environments**

Create custom AirSim environments:
1. Install Unreal Engine 4.27
2. Create a new project or modify existing Blocks environment
3. Add AirSim plugin to your project
4. Configure vehicle and sensor settings
5. Build and test

### **Multi-Vehicle Simulation**

Configure multiple drones:
```json
{
  "Vehicles": {
    "Drone1": {
      "VehicleType": "SimpleFlight",
      "X": 0,
      "Y": 0,
      "Z": -2
    },
    "Drone2": {
      "VehicleType": "SimpleFlight", 
      "X": 5,
      "Y": 0,
      "Z": -2
    }
  }
}
```

### **Sensor Integration**

Add custom sensors:
```json
{
  "Sensors": {
    "Lidar": {
      "SensorType": 6,
      "Enabled": true,
      "NumberOfChannels": 16,
      "RotationsPerSecond": 10,
      "Range": 100
    }
  }
}
```

## 🔗 **Useful Links**

- [AirSim Documentation](https://microsoft.github.io/AirSim/)
- [AirSim GitHub Repository](https://github.com/microsoft/AirSim)
- [AirSim Community](https://github.com/microsoft/AirSim/discussions)
- [DART-Planner AirSim Interface](../REFACTORING_SUMMARY.md)

## 📞 **Getting Help**

- 📖 [DART-Planner Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/Pasqui1010/DART-Planner/issues)
- 💬 [Community Discussions](https://github.com/Pasqui1010/DART-Planner/discussions)
- 📧 [AirSim Support](https://github.com/microsoft/AirSim/issues) 