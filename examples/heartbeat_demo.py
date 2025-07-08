#!/usr/bin/env python3
"""
Heartbeat and Safety Watchdog Demonstration

This script demonstrates the bidirectional heartbeat system working with
ZMQ communication and the safety watchdog integration.
"""

import time
from dart_planner.common.di_container import get_container
import threading
import sys
import os

# Add src to path

from dart_planner.communication.heartbeat import HeartbeatMonitor, HeartbeatConfig, HeartbeatMessage
from dart_planner.communication.zmq_server import ZmqServer
from dart_planner.communication.zmq_client import ZmqClient
from dart_planner.hardware.safety_watchdog import SafetyWatchdog


def emergency_landing_callback():
    """Emergency landing callback - simulates emergency landing procedure"""
    print("🚨 EMERGENCY LANDING TRIGGERED!")
    print("   - Disabling API control")
    print("   - Initiating emergency descent")
    print("   - Activating failsafe systems")
    print("   - Emergency landing sequence complete")


def demo_basic_heartbeat():
    """Demonstrate basic heartbeat monitoring"""
    print("\n" + "="*50)
    print("BASIC HEARTBEAT DEMONSTRATION")
    print("="*50)
    
    # Create heartbeat monitor with emergency callback
    config = HeartbeatConfig(
        heartbeat_interval_ms=100,
        timeout_ms=300,
        emergency_callback=emergency_landing_callback
    )
    
    monitor = HeartbeatMonitor(config)
    monitor.start_monitoring()
    
    print("✅ Heartbeat monitoring started")
    print("   - Interval: 100ms")
    print("   - Timeout: 300ms")
    
    # Send heartbeats for a while
    print("\n📡 Sending heartbeats...")
    for i in range(10):
        monitor.heartbeat_received()
        print(f"   Heartbeat {i+1}/10 sent")
        time.sleep(0.05)  # 50ms between heartbeats
        
    # Check status
    status = monitor.get_status()
    print(f"\n📊 Status: {status['time_since_last_received_ms']:.1f}ms since last heartbeat")
    
    # Stop monitoring
    monitor.stop_monitoring()
    print("✅ Heartbeat monitoring stopped")


def demo_heartbeat_timeout():
    """Demonstrate heartbeat timeout triggering emergency"""
    print("\n" + "="*50)
    print("HEARTBEAT TIMEOUT DEMONSTRATION")
    print("="*50)
    
    # Create heartbeat monitor with emergency callback
    config = HeartbeatConfig(
        heartbeat_interval_ms=50,
        timeout_ms=200,
        emergency_callback=emergency_landing_callback
    )
    
    monitor = HeartbeatMonitor(config)
    monitor.start_monitoring()
    
    print("✅ Heartbeat monitoring started")
    print("   - Interval: 50ms")
    print("   - Timeout: 200ms")
    
    # Send one heartbeat then wait for timeout
    print("\n📡 Sending single heartbeat...")
    monitor.heartbeat_received()
    print("   Heartbeat sent")
    
    print("\n⏰ Waiting for timeout...")
    time.sleep(0.25)  # Wait longer than timeout
    
    # Stop monitoring
    monitor.stop_monitoring()
    print("✅ Heartbeat monitoring stopped")


def demo_zmq_heartbeat():
    """Demonstrate ZMQ communication with heartbeat"""
    print("\n" + "="*50)
    print("ZMQ HEARTBEAT DEMONSTRATION")
    print("="*50)
    
    # Start server
    print("🚀 Starting ZMQ server...")
    server = ZmqServer(port="5558", enable_heartbeat=True, emergency_callback=emergency_landing_callback)
    
    # Start client
    print("🔗 Connecting ZMQ client...")
    client = get_container().create_communication_container().get_zmq_client()host="localhost", port="5558", enable_heartbeat=True, emergency_callback=emergency_landing_callback)
    
    # Let them exchange heartbeats
    print("\n📡 Exchanging heartbeats...")
    time.sleep(0.3)
    
    # Check status
    if server.heartbeat_monitor and client.heartbeat_monitor:
        server_status = server.heartbeat_monitor.get_status()
        client_status = client.heartbeat_monitor.get_status()
        
        print(f"\n📊 Server status: {server_status['time_since_last_received_ms']:.1f}ms since last heartbeat")
        print(f"📊 Client status: {client_status['time_since_last_received_ms']:.1f}ms since last heartbeat")
        
        print("✅ Heartbeat exchange successful")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    client.close()
    server.close()
    print("✅ ZMQ connection closed")


def demo_safety_watchdog():
    """Demonstrate safety watchdog integration"""
    print("\n" + "="*50)
    print("SAFETY WATCHDOG DEMONSTRATION")
    print("="*50)
    
    # Create safety watchdog
    config = {
        "heartbeat_interval_ms": 100,
        "heartbeat_timeout_ms": 300
    }
    
    watchdog = SafetyWatchdog(config)
    watchdog.set_emergency_callback(emergency_landing_callback)
    watchdog.start_monitoring()
    
    print("✅ Safety watchdog started")
    print("   - Heartbeat interval: 100ms")
    print("   - Heartbeat timeout: 300ms")
    print("   - Emergency callback configured")
    
    # Send heartbeats
    print("\n📡 Sending heartbeats to watchdog...")
    for i in range(5):
        watchdog.heartbeat_received()
        print(f"   Heartbeat {i+1}/5 sent")
        time.sleep(0.05)
    
    # Check status
    status = watchdog.get_status()
    print(f"\n📊 Watchdog status:")
    print(f"   - Emergency triggered: {status['emergency_triggered']}")
    print(f"   - Time since last heartbeat: {status['heartbeat_status']['time_since_last_received_ms']:.1f}ms")
    print(f"   - Monitoring: {status['heartbeat_status']['monitoring']}")
    
    # Stop monitoring
    watchdog.stop_monitoring()
    print("✅ Safety watchdog stopped")


def main():
    """Run all demonstrations"""
    print("🔔 DART-Planner Heartbeat & Safety System Demonstration")
    print("="*60)
    
    try:
        # Run demonstrations
        demo_basic_heartbeat()
        demo_heartbeat_timeout()
        demo_zmq_heartbeat()
        demo_safety_watchdog()
        
        print("\n" + "="*60)
        print("✅ All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("  • Bidirectional heartbeat monitoring")
        print("  • Configurable timeout and interval")
        print("  • Emergency landing trigger on timeout")
        print("  • ZMQ integration with heartbeat")
        print("  • Safety watchdog with unified interface")
        print("  • MAVLink adapter support (structure ready)")
        
    except KeyboardInterrupt:
        print("\n⚠️ Demonstration interrupted by user")
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 
