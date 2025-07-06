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
pip install -r requirements/base.txt
pip install -r requirements/dev.txt
```

### For CI/Testing (without AirSim)
```bash
pip install -r requirements/ci.txt
pip install -r requirements/dev.txt
```