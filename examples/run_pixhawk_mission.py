"""
Example script to run a mission using the PixhawkInterface.
"""
import asyncio
import numpy as np
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from hardware.pixhawk_interface import PixhawkInterface

async def main():
    """Main function to run a simple mission."""
    # Use 'udp:127.0.0.1:14550' for SITL
    interface = PixhawkInterface()
    
    try:
        if not await interface.connect():
            print("Exiting.")
            return

        print("Waiting for drone to be ready (armed and in offboard mode)...")
        
        is_sitl = "udp:" in interface.config.mavlink_connection or "tcp:" in interface.config.mavlink_connection

        if is_sitl:
            print("SITL environment detected. Attempting to set mode and arm.")
            # In SITL, we can try to arm and set mode programmatically.
            # For real hardware, this should be done by the ground control station or pilot.
            await interface.set_mode("GUIDED")
            await asyncio.sleep(1)
            await interface.arm()
            await asyncio.sleep(1)
            await interface.set_mode("OFFBOARD")
        else:
            print("Real hardware detected. Please arm and set mode to OFFBOARD manually.")

        # Wait until the drone is armed and in the correct mode.
        while not interface.is_armed or (await interface.get_current_mode() != "OFFBOARD"):
            mode = await interface.get_current_mode()
            print(f"Current mode: {mode}, Armed: {interface.is_armed}. Waiting for OFFBOARD and arm.")
            await asyncio.sleep(1)
            
        print("✅ Drone is ready for mission.")

        # Define mission waypoints
        start_pos = interface.current_state.position
        
        # Takeoff to 5 meters above current altitude
        takeoff_alt = start_pos[2] + 5.0
        print(f"Commanding takeoff to {takeoff_alt}m...")
        await interface.takeoff(takeoff_alt)
        
        # Wait until takeoff is complete (e.g., reached target altitude)
        # This is a simple sleep, a better implementation would check altitude.
        print("Waiting for takeoff to complete...")
        await asyncio.sleep(10)
        
        # Simple square pattern relative to current position
        print("Defining mission waypoints...")
        mission_start_pos = interface.current_state.position
        waypoints = np.array([
            mission_start_pos + np.array([10, 0, 0]),
            mission_start_pos + np.array([10, 10, 0]),
            mission_start_pos + np.array([0, 10, 0]),
            mission_start_pos,
        ])

        # Execute mission
        print("Starting mission...")
        await interface.start_mission(waypoints)

    except asyncio.CancelledError:
        print("Main task cancelled.")
    except Exception as e:
        print(f"An error occurred in main: {e}")
    finally:
        print("Mission finished or interrupted. Landing...")
        await interface.land()
        await interface.close()
        
        # Print performance report
        report = interface.get_performance_report()
        print("\n--- Performance Report ---")
        if report:
            for key, value in report.items():
                print(f"{key}: {value:.2f}" if isinstance(value, float) else f"{key}: {value}")
        print("------------------------")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Script interrupted by user.") 