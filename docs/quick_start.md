# 🚀 Quick Start Guide

Get DART-Planner running in minutes with this comprehensive setup guide.

## ⚡ **Try It in 30 Seconds**

### **Docker Demo (Recommended)**
```bash
# 1. Build the Docker image from the repository root
docker build -t dart-planner-demo -f demos/Dockerfile .

# 2. Run the complete simulation environment
docker run --rm -it -p 8080:8080 dart-planner-demo

# 3. Open your browser to http://localhost:8080
# Watch a drone autonomously navigate obstacles without any cloud connection!
```

## 🛠️ **Development Setup**

### **System Requirements**

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | Intel i5-8400 / AMD Ryzen 5 2600 | Intel i7-10700K / AMD Ryzen 7 3700X |
| **RAM** | 8 GB | 16 GB |
| **GPU** | Integrated Graphics | NVIDIA GTX 1660 / RTX 3060 |
| **Storage** | 10 GB free space | 20 GB SSD |
| **OS** | Ubuntu 20.04 / Windows 10 | Ubuntu 22.04 / Windows 11 |

### **1. Clone and Install**

```bash
# Clone the repository
git clone https://github.com/Pasqui1010/DART-Planner.git
cd DART-Planner

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements/base.txt
pip install -r requirements/dev.txt
```

> **⚠️ Important:** DART-Planner has specific version requirements for AirSim compatibility. See [Dependency Notes](DEPENDENCY_NOTES.md) if you encounter installation issues.

### **2. AirSim Setup**

#### **Windows (Recommended)**
```bash
# Download AirSim
git clone https://github.com/microsoft/AirSim.git
cd AirSim
build.cmd

# Or use pre-built binaries
# Download from: https://github.com/microsoft/AirSim/releases
```

#### **Linux**
```bash
# Install AirSim dependencies
sudo apt update
sudo apt install build-essential cmake git

# Clone and build AirSim
git clone https://github.com/microsoft/AirSim.git
cd AirSim
./setup.sh
./build.sh
```

### **3. Configuration**

#### **AirSim Settings**
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
      "Z": -2
    }
  }
}
```

#### **Environment Variables**
```bash
export DART_PLANNER_LOG_LEVEL=INFO
export DART_PLANNER_SIM_MODE=airsim
export DART_PLANNER_CONTROL_FREQ=1000
```

### **4. Your First Flight**

```python
#!/usr/bin/env python3
"""Simple DART-Planner example"""

import asyncio
from src.hardware import AirSimDroneInterface, AirSimConfig

async def main():
    # Configure AirSim interface
    config = AirSimConfig(
        ip="127.0.0.1",
        port=41451,
        enable_trace_logging=True
    )
    
    # Create interface
    interface = AirSimDroneInterface(config)
    
    # Connect to AirSim
    if await interface.connect():
        print("✅ Connected to AirSim!")
        
        # Take off
        if await interface.takeoff(altitude=2.0):
            print("🚁 Takeoff successful!")
            
            # Get current state
            state = await interface.get_state()
            print(f"📍 Position: {state.position}")
            
            # Land
            await interface.land()
            print("🛬 Landing complete!")
        
        # Disconnect
        await interface.disconnect()
        print("✅ Disconnected safely!")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🧪 **Running Tests**

### **Unit Tests**
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/control/          # Controller tests
pytest tests/planning/         # Planner tests
pytest tests/airsim/           # AirSim integration tests
```

### **SITL (Software-in-the-Loop) Tests**
```bash
# Start AirSim first, then run:
python tests/test_dart_sitl_comprehensive.py --mock-mode

# Full AirSim integration:
python tests/test_dart_sitl_comprehensive.py
```

### **Performance Benchmarks**
```bash
# Run performance benchmarks
python scripts/run_sitl_tests.py --benchmark

# Controller tuning
python scripts/tune_controller_for_sitl.py
```

## 🚀 **Performance Highlights**

DART-Planner's SE(3) MPC core was profiled on a Ryzen 9 5900X @ 3.7 GHz:

| Scenario | Baseline (pre-audit) | **DART-Planner** |
|----------|---------------------|------------------|
| Single step solve time | 5 241 ms | **2.1 ms** |
| Control loop frequency | 190 Hz | **≈ 479 Hz** |
| End-to-end mission success (100 runs) | 68 % | **100 %** |

👉 Reproduce with:
```bash
python experiments/phase2/phase2c_final_test.py  # prints timing table
```

## 🆘 **Troubleshooting**

### **Common Issues**

#### **AirSim Connection Failed**
- Ensure AirSim is running and listening on the correct port
- Check firewall settings
- Verify `airsim_settings.json` is in the correct location

#### **Import Errors**
- Make sure you're in the virtual environment
- Run `pip install -r requirements/base.txt` again
- Check Python version (3.8+ required)

#### **Performance Issues**
- Reduce control frequency in configuration
- Check system resources (CPU, RAM)
- Use mock mode for testing without AirSim

### **Getting Help**

- 📖 [Full Documentation](README.md)
- 🐛 [Report Issues](https://github.com/Pasqui1010/DART-Planner/issues)
- 💬 [Community Discussions](https://github.com/Pasqui1010/DART-Planner/discussions)

## 🎯 **Next Steps**

- 📚 Read the [Architecture Guide](architecture/README.md)
- 🔧 Explore [API Documentation](api/README.md)
- 🚀 Check out [Advanced Examples](examples/)
- 🤝 [Contribute to the Project](CONTRIBUTING.md) 