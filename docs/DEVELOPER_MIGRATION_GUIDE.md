# Developer Migration Guide: New DI Container & Frozen Config

## Overview

DART-Planner has been completely refactored with a new dependency injection (DI) system and configuration management. This guide helps developers migrate from the old systems to the new architecture.

## 🚀 **What's New**

### **1. New DI Container (`di_container_v2`)**
- **Staged Registration**: Components are registered in stages (CORE, RUNTIME, etc.)
- **Type Safety**: Full type hints and validation
- **Dependency Graph**: Automatic dependency resolution with cycle detection
- **Compatibility Layer**: Backward compatibility with old API

### **2. Frozen Config (`frozen_config`)**
- **Immutable Configuration**: Configuration cannot be modified after creation
- **Type Safety**: Strongly typed configuration values
- **Validation**: Automatic validation of configuration values
- **Environment Integration**: Seamless integration with environment variables

### **3. Enhanced Security**
- **Secure Key Management**: Automatic key rotation and management
- **Token Expiration**: Short-lived access tokens (15 minutes)
- **HMAC Authentication**: Secure API access with HMAC tokens

## 📋 **Migration Checklist**

### **✅ Step 1: Update Imports**

**Old Way:**
```python
from dart_planner.common.di_container import get_container
from dart_planner.config.settings import get_config
```

**New Way:**
```python
from dart_planner.common.di_container_v2 import get_container
from dart_planner.config.frozen_config import get_frozen_config as get_config
```

### **✅ Step 2: Update Component Access**

**Old Way:**
```python
container = get_container()
planner = container.get_planner()
controller = container.get_controller()
```

**New Way:**
```python
container = get_container()

# Option 1: Direct resolution (recommended)
planner = container.resolve(SE3MPCPlanner)
controller = container.resolve(GeometricController)

# Option 2: Compatibility layer (for legacy code)
planner_container = container.create_planner_container()
planner = planner_container.get_se3_planner()
controller_container = container.create_control_container()
controller = controller_container.get_geometric_controller()
```

### **✅ Step 3: Update Configuration Access**

**Old Way:**
```python
config = get_config()
control_freq = config.control.frequency
planner_timeout = config.planning.timeout
```

**New Way:**
```python
config = get_frozen_config()
control_freq = config.control.frequency
planner_timeout = config.planning.timeout

# Configuration is now immutable
# config.control.frequency = 1000  # This will raise an error!
```

## 🔧 **Detailed Migration Examples**

### **Example 1: Basic Component Usage**

**Before Migration:**
```python
from dart_planner.common.di_container import get_container
from dart_planner.config.settings import get_config

def run_mission():
    container = get_container()
    config = get_config()
    
    # Get components
    planner = container.get_planner()
    controller = container.get_controller()
    
    # Use configuration
    control_freq = config.control.frequency
    
    # Run mission logic
    trajectory = planner.plan(goal)
    controller.execute(trajectory)
```

**After Migration:**
```python
from dart_planner.common.di_container_v2 import get_container
from dart_planner.config.frozen_config import get_frozen_config
from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner
from dart_planner.control.geometric_controller import GeometricController

def run_mission():
    container = get_container()
    config = get_frozen_config()
    
    # Get components with type safety
    planner = container.resolve(SE3MPCPlanner)
    controller = container.resolve(GeometricController)
    
    # Use immutable configuration
    control_freq = config.control.frequency
    
    # Run mission logic
    trajectory = planner.plan(goal)
    controller.execute(trajectory)
```

### **Example 2: Hardware Integration**

**Before Migration:**
```python
from dart_planner.hardware.airsim_interface import AirSimInterface

def connect_to_simulator():
    interface = AirSimInterface()
    interface.connect()
    return interface
```

**After Migration:**
```python
from dart_planner.hardware.airsim_adapter import AirSimAdapter
from dart_planner.common.di_container_v2 import get_container

def connect_to_simulator():
    container = get_container()
    airsim_adapter = container.resolve(AirSimAdapter)
    await airsim_adapter.connect()
    return airsim_adapter
```

### **Example 3: Configuration Management**

**Before Migration:**
```python
from dart_planner.config.settings import get_config

def setup_controller():
    config = get_config()
    
    # Configuration could be modified (dangerous!)
    config.control.frequency = 1000
    config.control.gains.kp = 2.0
    
    return config
```

**After Migration:**
```python
from dart_planner.config.frozen_config import get_frozen_config
from dart_planner.config.control_config import ControllerTuningProfile

def setup_controller():
    config = get_frozen_config()
    
    # Configuration is immutable - use tuning profiles instead
    tuning_profile = ControllerTuningProfile(
        frequency=1000,
        gains=ControllerGains(kp=2.0, ki=0.1, kd=0.05)
    )
    
    return config, tuning_profile
```

## 🛡️ **Security Migration**

### **Environment Variables**

**Old Way:**
```bash
export DART_SECRET_KEY=my_secret_key
export DART_ZMQ_SECRET=my_zmq_secret
```

**New Way:**
```bash
# For development/testing
export DART_SECRET_KEY=test_secret_key_value_123456789
export DART_ZMQ_SECRET=test_secret

# For production (automatic key management)
# Keys are automatically managed in ~/.dart_planner/keys.json
```

### **API Authentication**

**Old Way:**
```python
# No authentication required
response = requests.get("http://localhost:8080/api/status")
```

**New Way:**
```python
from dart_planner.security.auth import generate_hmac_token

# Generate HMAC token for API access
token = generate_hmac_token("GET", "/api/status", secret_key)
headers = {"Authorization": f"HMAC {token}"}
response = requests.get("http://localhost:8080/api/status", headers=headers)
```

## 🧪 **Testing Migration**

### **Unit Tests**

**Before Migration:**
```python
def test_planner():
    container = get_container()
    planner = container.get_planner()
    
    result = planner.plan(goal)
    assert result is not None
```

**After Migration:**
```python
def test_planner():
    container = get_container()
    planner = container.resolve(SE3MPCPlanner)
    
    result = planner.plan(goal)
    assert result is not None
```

### **Integration Tests**

**Before Migration:**
```python
def test_full_stack():
    container = get_container()
    planner = container.get_planner()
    controller = container.get_controller()
    
    # Test integration
    trajectory = planner.plan(goal)
    controller.execute(trajectory)
```

**After Migration:**
```python
def test_full_stack():
    container = get_container()
    planner = container.resolve(SE3MPCPlanner)
    controller = container.resolve(GeometricController)
    
    # Test integration
    trajectory = planner.plan(goal)
    controller.execute(trajectory)
```

## 🔍 **Troubleshooting**

### **Common Issues**

#### **1. Import Errors**
```python
# Error: ModuleNotFoundError: No module named 'dart_planner.common.di_container'
# Solution: Update import to use di_container_v2
from dart_planner.common.di_container_v2 import get_container
```

#### **2. Configuration Errors**
```python
# Error: AttributeError: can't set attribute
# Solution: Configuration is now immutable, use tuning profiles
config = get_frozen_config()
# config.control.frequency = 1000  # This will fail!
tuning_profile = ControllerTuningProfile(frequency=1000)
```

#### **3. Component Resolution Errors**
```python
# Error: No provider registered for type 'SomeComponent'
# Solution: Ensure component is registered in DI container
container = get_container()
# Check if component exists: container.resolve(SomeComponent)
```

#### **4. Security Errors**
```python
# Error: SecurityError: Missing required environment variable
# Solution: Set required environment variables
export DART_SECRET_KEY=test_secret_key_value_123456789
export DART_ZMQ_SECRET=test_secret
```

### **Debugging Tips**

1. **Check DI Container State:**
```python
container = get_container()
info = container.get_graph_info()
print(f"Registered components: {info['node_count']}")
print(f"Has cycles: {info['has_cycles']}")
```

2. **Validate Configuration:**
```python
config = get_frozen_config()
print(f"Control frequency: {config.control.frequency}")
print(f"Planning timeout: {config.planning.timeout}")
```

3. **Test Component Resolution:**
```python
container = get_container()
try:
    component = container.resolve(SomeComponent)
    print("Component resolved successfully")
except Exception as e:
    print(f"Component resolution failed: {e}")
```

## 📚 **Additional Resources**

- **[DI Migration Guide](DI_MIGRATION_GUIDE.md)**: Detailed technical migration
- **[Frozen Config API](api/config/index.rst)**: Complete configuration API reference
- **[DI Container API](api/common/index.rst)**: Complete DI container API reference
- **[Security Implementation](SECURITY_IMPLEMENTATION.md)**: Security features and best practices

## 🎯 **Next Steps**

1. **Update your imports** to use the new modules
2. **Test your code** with the new DI container and frozen config
3. **Update your tests** to use the new APIs
4. **Review security** implementation for your use case
5. **Report issues** if you encounter problems during migration

---

*This guide will be updated as the new architecture evolves. Check the latest documentation for the most current information.* 