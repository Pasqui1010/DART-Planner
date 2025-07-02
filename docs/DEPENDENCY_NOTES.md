# 📦 DART-Planner Dependency Notes

## 🚨 Critical Version Constraints

### Tornado Version Lock
**⚠️ IMPORTANT: tornado MUST remain at version 4.5.3**

```bash
# ✅ CORRECT
pip install tornado==4.5.3

# ❌ WRONG - Will break AirSim integration
pip install tornado>=5.0.0
```

**Why this constraint exists:**
- `airsim==1.8.1` depends on `msgpack-rpc-python==0.4.1`
- `msgpack-rpc-python` only works with `tornado<5.0`
- Upgrading tornado breaks the entire AirSim RPC stack

**Symptoms of wrong tornado version:**
- `ImportError` when importing airsim
- RPC connection failures to AirSim
- "incompatible API" errors

## 📋 Installation Order

### For Full Development (with AirSim)
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### For CI/Testing (without AirSim)
```bash
pip install -r requirements-ci.txt
pip install -r requirements-dev.txt
```

## 🔧 Troubleshooting

### "Cannot install airsim" Error
If you see numpy/tornado circular dependency errors:

1. **Check tornado version first:**
   ```bash
   pip show tornado
   ```

2. **If tornado is wrong version:**
   ```bash
   pip uninstall tornado airsim msgpack-rpc-python
   pip install tornado==4.5.3
   pip install msgpack-rpc-python==0.4.1
   pip install airsim==1.8.1
   ```

3. **If using conda, create clean environment:**
   ```bash
   conda create -n dart-planner python=3.10
   conda activate dart-planner
   pip install -r requirements.txt
   ```

### "ModuleNotFoundError: numpy" During AirSim Install
This happens when airsim tries to build but numpy isn't available yet:

```bash
# Install numpy first, then airsim
pip install numpy>=1.21.0
pip install airsim==1.8.1
```

## 🌍 Environment-Specific Notes

### Windows
- Use `requirements.txt` for full installation
- AirSim works best with Visual Studio build tools installed

### Linux
- May need additional system packages for AirSim compilation
- Consider using conda for easier dependency management

### CI/GitHub Actions
- Use `requirements-ci.txt` to avoid airsim installation issues
- Faster builds, no circular dependencies

## 🔄 Version Update Policy

### Safe to Update
- JAX ecosystem packages (jax, flax, optax, chex)
- Scientific computing (numpy, scipy, matplotlib)
- Testing tools (pytest, black, isort)

### DO NOT Update
- `tornado` (must stay 4.5.3)
- `msgpack-rpc-python` (must stay 0.4.1)
- `airsim` (unless you verify tornado compatibility)

### Update with Caution
- `websockets` (test AirSim integration after updates)
- `pyzmq` (test communication systems)

## 🆘 Getting Help

If you encounter dependency issues:

1. **Check this document first**
2. **Run the diagnostic script:**
   ```bash
   python scripts/diagnose_airsim_freeze.py
   ```
3. **Clean install in fresh environment:**
   ```bash
   pip freeze > old_requirements.txt  # backup
   pip uninstall -r old_requirements.txt -y
   pip install -r requirements.txt
   ```

## 📚 Related Documentation

- [AirSim Integration Guide](validation/AIRSIM_INTEGRATION_GUIDE.md)
- [SITL Integration Guide](implementation/SITL_INTEGRATION_GUIDE.md)
- [Hardware Validation Roadmap](HARDWARE_VALIDATION_ROADMAP.md) 