#!/usr/bin/env python3
"""
Phase 2C-1: Control Loop Profiling System
Detailed timing instrumentation to identify computational bottlenecks
"""

import numpy as np
import time
import sys
import os
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.control.geometric_controller import GeometricController
from src.utils.drone_simulator import DroneSimulator
from src.planning.dial_mpc_planner import DIALMPCPlanner
from src.common.types import DroneState

class ControlLoopProfiler:
    """Real-time profiling system for control loop performance analysis"""
    
    def __init__(self, window_size=1000):
        self.window_size = window_size
        self.timings = defaultdict(lambda: deque(maxlen=window_size))
        self.counts = defaultdict(int)
        self.start_times = {}
        self.lock = threading.Lock()
        self.enabled = True
        
        # Performance thresholds (ms)
        self.thresholds = {
            'control_loop': 1.0,      # Target: 1ms for 1kHz
            'geometric_controller': 0.3,  # Should be very fast
            'drone_simulator': 0.5,   # Physics step
            'dial_mpc_planning': 8.0, # Already optimized
            'state_estimation': 0.2,  # Should be lightweight
            'communication': 0.1,     # ZMQ overhead
            'trajectory_tracking': 0.1, # Reference following
        }
        
    @contextmanager
    def profile(self, component_name):
        """Context manager for timing code sections"""
        if not self.enabled:
            yield
            return
            
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000.0
            
            with self.lock:
                self.timings[component_name].append(duration_ms)
                self.counts[component_name] += 1
    
    def get_stats(self, component_name):
        """Get statistical summary for a component"""
        with self.lock:
            if not self.timings[component_name]:
                return None
                
            times = list(self.timings[component_name])
            
        return {
            'mean': np.mean(times),
            'std': np.std(times),
            'min': np.min(times),
            'max': np.max(times),
            'p50': np.percentile(times, 50),
            'p95': np.percentile(times, 95),
            'p99': np.percentile(times, 99),
            'count': len(times),
            'total_count': self.counts[component_name]
        }
    
    def analyze_bottlenecks(self):
        """Identify the top computational bottlenecks"""
        print("\n🔍 CONTROL LOOP PERFORMANCE ANALYSIS")
        print("=" * 70)
        
        components = []
        
        for component in self.timings.keys():
            stats = self.get_stats(component)
            if stats and stats['count'] > 10:  # Minimum samples
                threshold = self.thresholds.get(component, 1.0)
                is_bottleneck = stats['mean'] > threshold
                
                components.append({
                    'name': component,
                    'mean': stats['mean'],
                    'p95': stats['p95'],
                    'threshold': threshold,
                    'is_bottleneck': is_bottleneck,
                    'samples': stats['count']
                })
        
        # Sort by mean execution time
        components.sort(key=lambda x: x['mean'], reverse=True)
        
        print(f"{'Component':<25} {'Mean (ms)':<10} {'P95 (ms)':<10} {'Threshold':<10} {'Status'}")
        print("-" * 70)
        
        total_time = 0
        bottlenecks = []
        
        for comp in components:
            status = "🔴 BOTTLENECK" if comp['is_bottleneck'] else "✅ OK"
            print(f"{comp['name']:<25} {comp['mean']:<10.2f} {comp['p95']:<10.2f} "
                  f"{comp['threshold']:<10.1f} {status}")
            
            total_time += comp['mean']
            if comp['is_bottleneck']:
                bottlenecks.append(comp)
        
        print("-" * 70)
        print(f"{'TOTAL LOOP TIME':<25} {total_time:<10.2f} {'':<10} {'1.0':<10} "
              f"{'🔴 TOO SLOW' if total_time > 1.0 else '✅ OK'}")
        
        # Calculate theoretical frequency
        theoretical_freq = 1000.0 / total_time if total_time > 0 else 0
        print(f"\n📊 PERFORMANCE METRICS:")
        print(f"   Total loop time: {total_time:.2f}ms")
        print(f"   Theoretical max frequency: {theoretical_freq:.0f}Hz")
        print(f"   Target frequency: 1000Hz")
        print(f"   Performance gap: {((1.0 - total_time/1.0) * 100):.1f}%")
        
        return bottlenecks, total_time, theoretical_freq
    
    def generate_optimization_recommendations(self, bottlenecks):
        """Generate specific optimization recommendations"""
        print(f"\n🔧 OPTIMIZATION RECOMMENDATIONS:")
        print("=" * 50)
        
        if not bottlenecks:
            print("✅ No major bottlenecks detected!")
            print("   System is performing within thresholds.")
            return
        
        priority_map = {
            'control_loop': 1,
            'geometric_controller': 2, 
            'drone_simulator': 3,
            'dial_mpc_planning': 4,
            'state_estimation': 2,
            'communication': 3,
            'trajectory_tracking': 2
        }
        
        # Sort bottlenecks by priority and impact
        bottlenecks.sort(key=lambda x: (
            priority_map.get(x['name'], 5),  # Priority (lower is higher)
            -x['mean']  # Impact (higher mean time = higher impact)
        ))
        
        for i, bottleneck in enumerate(bottlenecks[:5]):  # Top 5 bottlenecks
            name = bottleneck['name']
            mean_time = bottleneck['mean']
            potential_saving = mean_time - bottleneck['threshold']
            
            print(f"\n🎯 Priority {i+1}: {name}")
            print(f"   Current: {mean_time:.2f}ms")
            print(f"   Target:  {bottleneck['threshold']:.2f}ms")
            print(f"   Potential saving: {potential_saving:.2f}ms")
            
            # Specific recommendations
            if 'geometric_controller' in name:
                print("   💡 Optimizations:")
                print("      • Pre-compute rotation matrices")
                print("      • Vectorize PID calculations")
                print("      • Cache constant values")
                print("      • Use in-place operations")
                
            elif 'drone_simulator' in name:
                print("   💡 Optimizations:")
                print("      • Optimize physics integration")
                print("      • Reduce state vector copying")
                print("      • Use compiled physics solver")
                print("      • Cache dynamics matrices")
                
            elif 'dial_mpc' in name:
                print("   💡 Optimizations:")
                print("      • Reduce sampling frequency")
                print("      • Optimize trajectory smoothing")
                print("      • Cache trajectory segments")
                print("      • Use GPU acceleration")
                
            elif 'communication' in name:
                print("   💡 Optimizations:")
                print("      • Reduce ZMQ message frequency")
                print("      • Optimize serialization")
                print("      • Use async communication")
                print("      • Batch messages")
                
            elif 'state_estimation' in name:
                print("   💡 Optimizations:")
                print("      • Optimize matrix operations")
                print("      • Reduce sensor fusion complexity")
                print("      • Cache filter matrices")
                print("      • Use efficient data structures")
    
    def export_profile_data(self, filename="control_loop_profile.csv"):
        """Export profiling data for analysis"""
        with open(filename, 'w') as f:
            f.write("component,mean_ms,std_ms,min_ms,max_ms,p95_ms,samples\n")
            
            for component in self.timings.keys():
                stats = self.get_stats(component)
                if stats:
                    f.write(f"{component},{stats['mean']:.3f},{stats['std']:.3f},"
                           f"{stats['min']:.3f},{stats['max']:.3f},"
                           f"{stats['p95']:.3f},{stats['count']}\n")
        
        print(f"\n📁 Profile data exported to: {filename}")

def run_profiled_control_test():
    """Run a control test with detailed profiling enabled"""
    
    print("🚀 Starting Phase 2C-1: Control Loop Profiling Test")
    print("=" * 60)
    
    # Initialize profiler
    profiler = ControlLoopProfiler(window_size=2000)
    
    # Initialize components with Phase 1 optimal settings
    with profiler.profile('system_initialization'):
        controller = GeometricController()
        simulator = DroneSimulator()
        dial_mpc = DIALMPCPlanner()
    
    # Initialize drone state
    current_state = DroneState(
        timestamp=time.time(),
        position=np.array([0.0, 0.0, 2.0]),
        velocity=np.zeros(3),
        attitude=np.zeros(3),
        angular_velocity=np.zeros(3)
    )
    
    # Test parameters
    test_duration = 30.0  # seconds
    dt = 0.001  # 1kHz target
    
    print(f"⏱️  Running {test_duration}s profiling test at {1/dt:.0f}Hz target frequency...")
    
    # Circular trajectory for demanding velocity tracking
    radius = 5.0
    angular_vel = 0.5  # rad/s
    
    start_time = time.time()
    step_count = 0
    control_frequencies = []
    
    try:
        while time.time() - start_time < test_duration:
            loop_start = time.perf_counter()
            
            with profiler.profile('control_loop'):
                current_time = time.time() - start_time
                current_state.timestamp = time.time()
                
                # Generate reference trajectory
                with profiler.profile('trajectory_tracking'):
                    x_ref = radius * np.cos(angular_vel * current_time)
                    y_ref = radius * np.sin(angular_vel * current_time)
                    z_ref = 2.0
                    
                    vx_ref = -radius * angular_vel * np.sin(angular_vel * current_time)
                    vy_ref = radius * angular_vel * np.cos(angular_vel * current_time)
                    vz_ref = 0.0
                    
                    # Calculate desired acceleration
                    ax_ref = -radius * angular_vel * angular_vel * np.cos(angular_vel * current_time)
                    ay_ref = -radius * angular_vel * angular_vel * np.sin(angular_vel * current_time)
                    az_ref = 0.0
                
                # State estimation simulation (already have current_state)
                with profiler.profile('state_estimation'):
                    # Simulate state estimation processing time
                    pass
                
                # Control computation
                with profiler.profile('geometric_controller'):
                    desired_pos = np.array([x_ref, y_ref, z_ref])
                    desired_vel = np.array([vx_ref, vy_ref, vz_ref])
                    desired_acc = np.array([ax_ref, ay_ref, az_ref])
                    
                    control_output = controller.compute_control(
                        current_state, desired_pos, desired_vel, desired_acc
                    )
                
                # Physics simulation
                with profiler.profile('drone_simulator'):
                    current_state = simulator.step(current_state, control_output, dt)
                
                # Periodic DIAL-MPC planning (every 100ms)
                if step_count % 100 == 0:  # 10Hz planning
                    with profiler.profile('dial_mpc_planning'):
                        # Simulate DIAL-MPC planning call
                        goal_pos = np.array([x_ref, y_ref, z_ref])
                        dial_mpc.plan_trajectory(current_state, goal_pos)
                
                # Communication overhead simulation
                with profiler.profile('communication'):
                    # Simulate ZMQ message exchange
                    time.sleep(0.00005)  # 0.05ms simulated network latency
            
            # Calculate actual control frequency
            loop_end = time.perf_counter()
            actual_loop_time = loop_end - loop_start
            actual_freq = 1.0 / actual_loop_time if actual_loop_time > 0 else 0
            control_frequencies.append(actual_freq)
            
            step_count += 1
            
            # Target loop timing
            target_sleep = dt - actual_loop_time
            if target_sleep > 0:
                time.sleep(target_sleep)
                
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    
    # Analysis
    actual_avg_freq = np.mean(control_frequencies) if control_frequencies else 0
    
    print(f"\n📊 TEST RESULTS:")
    print(f"   Steps completed: {step_count}")
    print(f"   Actual average frequency: {actual_avg_freq:.1f}Hz")
    print(f"   Target frequency: {1/dt:.0f}Hz")
    print(f"   Frequency achievement: {(actual_avg_freq/(1/dt)*100):.1f}%")
    
    # Detailed bottleneck analysis
    bottlenecks, total_time, theoretical_freq = profiler.analyze_bottlenecks()
    profiler.generate_optimization_recommendations(bottlenecks)
    
    # Export data
    profiler.export_profile_data("phase2c_profile_results.csv")
    
    return profiler, bottlenecks, actual_avg_freq

if __name__ == "__main__":
    profiler, bottlenecks, actual_freq = run_profiled_control_test()
    
    print(f"\n🎯 Phase 2C-1 Complete!")
    print(f"📊 Identified {len(bottlenecks)} bottlenecks for optimization")
    print(f"⚡ Current frequency: {actual_freq:.0f}Hz")
    print(f"🚀 Ready for Phase 2C-2: Hotspot Optimization") 