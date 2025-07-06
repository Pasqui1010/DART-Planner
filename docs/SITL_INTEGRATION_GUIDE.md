# DART-Planner SITL Integration Guide

This guide walks you through setting up DART-Planner with ArduPilot SITL (Software-in-the-Loop) for realistic flight dynamics testing.

## Prerequisites

- ✅ ArduPilot installed in WSL
- ✅ AirSim installed on Windows
- ✅ DART-Planner codebase
- ✅ Python 3.9+ with required dependencies

## Step 1: Configure AirSim Settings

1. **Copy the settings file** to your AirSim directory:
   ```bash
   # Copy from DART-Planner directory
   cp airsim_settings.json "C:\Users\pasqu\Documents\AirSim\settings.json"
   ```

2. **Verify the settings** contain:
   ```json
   {
     "SettingsVersion": 1.2,
     "SimMode": "Multirotor",
     "Vehicles": {
       "Copter": {
         "VehicleType": "SimpleFlight",
         "UseSerial": false,
         "LocalHostIp": "0.0.0.0",
         "UdpIp": "127.0.0.1",
         "UdpPort": 9003,
         "ControlPort": 9002
       }
     }
   }
   ```

## Step 2: Install Required Dependencies

```bash
# Install MAVLink support
pip install pymavlink

# Verify DART-Planner dependencies
pip install -r requirements.txt
```

## Step 3: Start ArduPilot SITL (WSL)

1. **Open WSL terminal** and navigate to your ArduPilot directory
2. **Launch SITL with AirSim configuration**:
   ```bash
   cd ardupilot
   ./Tools/autotest/sim_vehicle.py -v ArduCopter -f airsim-copter --console --map
   ```

3. **Wait for SITL to fully initialize** (you should see "APM: EKF3 IMU0 is using GPS" and similar messages)

## Step 4: Start AirSim

1. **Launch AirSim** from Windows
2. **Load the Blocks environment** (or your preferred environment)
3. **Verify connection** - you should see the drone in the simulation

## Step 5: Test DART-Planner Integration

1. **Run the integration script**:
   ```bash
   python scripts/sitl_integration.py
   ```

2. **Monitor the output** for:
   - ✅ "Connected to ArduPilot SITL successfully!"
   - ✅ "Flight mode set to: GUIDED"
   - ✅ "Vehicle armed successfully!"

## Step 6: Execute Test Mission

The integration script will automatically:
1. Connect to SITL via MAVLink
2. Set flight mode to GUIDED
3. Arm the vehicle
4. Execute a test mission with waypoints
5. Use DART-Planner's SE3 MPC for trajectory planning

## Troubleshooting

### Connection Issues
- **"Failed to connect to SITL"**: Ensure SITL is running and listening on port 14550
- **"No heartbeat"**: Check that ArduPilot SITL is fully initialized

### AirSim Issues
- **Drone not visible**: Verify AirSim settings.json is in the correct location
- **No communication**: Check that UDP ports 9002/9003 are not blocked by firewall

### WSL Network Issues
- **Cross-platform communication**: Ensure Windows Firewall allows UDP traffic
- **Port forwarding**: May need to configure WSL port forwarding for complex setups

## Advanced Configuration

### Custom Waypoints
Modify the `waypoints` list in `scripts/sitl_integration.py`:
```python
waypoints = [
    [lat1, lon1, alt1],  # Takeoff
    [lat2, lon2, alt2],  # Waypoint 1
    [lat3, lon3, alt3],  # Waypoint 2
    # ... more waypoints
]
```

### Different Ports
If using different MAVLink ports:
```bash
python scripts/sitl_integration.py --sitl-port 14560 --gcs-port 14561
```

### Mission Planner Integration
You can also use Mission Planner as a GCS:
1. Connect Mission Planner to `127.0.0.1:14551`
2. Monitor mission execution in real-time
3. Use Mission Planner's logging and analysis tools

## Performance Monitoring

The integration provides real-time monitoring of:
- **DART-Planner performance**: Planning time, success rate
- **Flight dynamics**: Position, velocity, attitude
- **Mission progress**: Waypoint completion, execution time

## Next Steps

1. **Test different mission types**: Obstacle avoidance, precision landing
2. **Validate planning algorithms**: Compare DART-Planner vs ArduPilot waypoint navigation
3. **Add sensor simulation**: Test with simulated LiDAR, camera data
4. **Performance benchmarking**: Measure planning efficiency and accuracy

## Support

For issues or questions:
- Check the [ArduPilot SITL documentation](https://ardupilot.org/dev/docs/sitl-with-airsim.html)
- Review DART-Planner test logs
- Verify all dependencies are correctly installed 