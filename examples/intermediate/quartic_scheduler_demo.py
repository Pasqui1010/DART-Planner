#!/usr/bin/env python3
"""
Quartic Scheduler Demonstration

This script demonstrates how the quartic scheduler replaces asyncio.sleep(dt)
for hard real-time tasks and validates performance with jitter histograms.

The demo compares:
1. Traditional asyncio.sleep approach
2. Quartic scheduler with precise timers
3. Jitter analysis and histogram generation

Usage:
    python examples/quartic_scheduler_demo.py
"""

import asyncio
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dart_planner.common.quartic_scheduler import (
    QuarticScheduler, QuarticTask, create_control_task, 
    create_planning_task, quartic_scheduler_context
)
from dart_planner.common.real_time_config import TaskPriority
from dart_planner.common.logging_config import get_logger


class MockControlSystem:
    """Mock control system for demonstration."""
    
    def __init__(self, name: str):
        self.name = name
        self.iteration_count = 0
        self.execution_times = []
        self.timestamps = []
        self.logger = get_logger(f"MockControl.{name}")
    
    def control_step(self) -> Dict[str, Any]:
        """Simulate a control step with variable execution time."""
        start_time = time.perf_counter()
        
        # Simulate control computation with some jitter
        computation_time = 0.001 + np.random.normal(0, 0.0002)  # 1ms ± 0.2ms
        computation_time = max(0.0005, computation_time)  # Minimum 0.5ms
        
        # Simulate actual work
        time.sleep(computation_time)
        
        # Record timing
        end_time = time.perf_counter()
        execution_time = (end_time - start_time) * 1000.0
        self.execution_times.append(execution_time)
        self.timestamps.append(end_time)
        self.iteration_count += 1
        
        # Log every 100 iterations
        if self.iteration_count % 100 == 0:
            self.logger.info(
                f"{self.name}: Iteration {self.iteration_count}, "
                f"ExecTime={execution_time:.3f}ms"
            )
        
        return {
            'iteration': self.iteration_count,
            'execution_time_ms': execution_time,
            'timestamp': end_time
        }
    
    def planning_step(self) -> Dict[str, Any]:
        """Simulate a planning step with longer execution time."""
        start_time = time.perf_counter()
        
        # Simulate planning computation (longer than control)
        computation_time = 0.005 + np.random.normal(0, 0.001)  # 5ms ± 1ms
        computation_time = max(0.002, computation_time)  # Minimum 2ms
        
        # Simulate actual work
        time.sleep(computation_time)
        
        # Record timing
        end_time = time.perf_counter()
        execution_time = (end_time - start_time) * 1000.0
        self.execution_times.append(execution_time)
        self.timestamps.append(end_time)
        self.iteration_count += 1
        
        # Log every 50 iterations (planning runs less frequently)
        if self.iteration_count % 50 == 0:
            self.logger.info(
                f"{self.name}: Planning iteration {self.iteration_count}, "
                f"ExecTime={execution_time:.3f}ms"
            )
        
        return {
            'iteration': self.iteration_count,
            'execution_time_ms': execution_time,
            'timestamp': end_time
        }


async def traditional_asyncio_demo(duration_s: float = 10.0) -> Dict[str, Any]:
    """
    Demonstrate traditional asyncio.sleep approach.
    
    This shows the baseline performance using asyncio.sleep for timing.
    """
    print("\n" + "="*60)
    print("TRADITIONAL ASYNCIO.SLEEP DEMO")
    print("="*60)
    
    control_system = MockControlSystem("Traditional")
    control_frequency = 400.0  # 400 Hz
    control_dt = 1.0 / control_frequency
    
    start_time = time.perf_counter()
    iteration_count = 0
    
    print(f"Running traditional asyncio.sleep demo for {duration_s}s at {control_frequency}Hz")
    print(f"Expected period: {control_dt*1000:.3f}ms")
    
    while (time.perf_counter() - start_time) < duration_s:
        loop_start = time.perf_counter()
        
        # Execute control step
        result = control_system.control_step()
        
        # Calculate sleep time
        elapsed = time.perf_counter() - loop_start
        sleep_time = max(0.0, control_dt - elapsed)
        
        # Traditional asyncio.sleep approach
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        
        iteration_count += 1
    
    runtime = time.perf_counter() - start_time
    actual_frequency = iteration_count / runtime
    
    print(f"Traditional Demo Results:")
    print(f"  Runtime: {runtime:.2f}s")
    print(f"  Iterations: {iteration_count}")
    print(f"  Actual Frequency: {actual_frequency:.1f}Hz")
    print(f"  Expected Frequency: {control_frequency:.1f}Hz")
    print(f"  Frequency Error: {((actual_frequency - control_frequency) / control_frequency) * 100:.2f}%")
    
    if control_system.execution_times:
        exec_times = np.array(control_system.execution_times)
        print(f"  Mean Execution Time: {np.mean(exec_times):.3f}ms")
        print(f"  Max Execution Time: {np.max(exec_times):.3f}ms")
        print(f"  Min Execution Time: {np.min(exec_times):.3f}ms")
        print(f"  Std Execution Time: {np.std(exec_times):.3f}ms")
    
    return {
        'method': 'traditional_asyncio',
        'runtime_s': runtime,
        'iterations': iteration_count,
        'actual_frequency_hz': actual_frequency,
        'expected_frequency_hz': control_frequency,
        'execution_times': control_system.execution_times,
        'timestamps': control_system.timestamps
    }


async def quartic_scheduler_demo(duration_s: float = 10.0) -> Dict[str, Any]:
    """
    Demonstrate quartic scheduler with precise timers.
    
    This shows the improved performance using the quartic scheduler.
    """
    print("\n" + "="*60)
    print("QUARTIC SCHEDULER DEMO")
    print("="*60)
    
    control_system = MockControlSystem("Quartic")
    planning_system = MockControlSystem("QuarticPlanning")
    
    print(f"Running quartic scheduler demo for {duration_s}s")
    print("Tasks: 400Hz control, 50Hz planning")
    
    async with quartic_scheduler_context(enable_monitoring=True, max_jitter_ms=1.0) as scheduler:
        # Create tasks
        control_task = create_control_task(
            control_system.control_step, 
            frequency_hz=400.0, 
            name="control_loop"
        )
        
        planning_task = create_planning_task(
            planning_system.planning_step,
            frequency_hz=50.0,
            name="planning_loop"
        )
        
        # Add tasks to scheduler
        scheduler.add_task(control_task)
        scheduler.add_task(planning_task)
        
        # Run for specified duration
        await asyncio.sleep(duration_s)
        
        # Get statistics
        control_stats = scheduler.get_task_stats("control_loop")
        planning_stats = scheduler.get_task_stats("planning_loop")
        global_stats = scheduler.get_global_stats()
        
        print(f"Quartic Scheduler Results:")
        print(f"  Runtime: {global_stats['runtime_s']:.2f}s")
        print(f"  Total Cycles: {global_stats['cycle_count']}")
        print(f"  Missed Deadlines: {global_stats['total_missed_deadlines']}")
        print(f"  Overruns: {global_stats['total_overruns']}")
        
        if control_stats:
            print(f"\nControl Task ({control_stats['frequency_hz']}Hz):")
            print(f"  Executions: {control_stats['execution_count']}")
            print(f"  Actual Frequency: {control_stats['actual_frequency_hz']:.1f}Hz")
            print(f"  Missed Deadlines: {control_stats['missed_deadlines']}")
            if 'mean_execution_time_ms' in control_stats:
                print(f"  Mean Execution Time: {control_stats['mean_execution_time_ms']:.3f}ms")
                print(f"  Max Execution Time: {control_stats['max_execution_time_ms']:.3f}ms")
        
        if planning_stats:
            print(f"\nPlanning Task ({planning_stats['frequency_hz']}Hz):")
            print(f"  Executions: {planning_stats['execution_count']}")
            print(f"  Actual Frequency: {planning_stats['actual_frequency_hz']:.1f}Hz")
            print(f"  Missed Deadlines: {planning_stats['missed_deadlines']}")
            if 'mean_execution_time_ms' in planning_stats:
                print(f"  Mean Execution Time: {planning_stats['mean_execution_time_ms']:.3f}ms")
                print(f"  Max Execution Time: {planning_stats['max_execution_time_ms']:.3f}ms")
        
        # Generate jitter histograms
        results_dir = Path("results/quartic_demo")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        scheduler.generate_jitter_histogram(
            task_name="control_loop",
            save_path=str(results_dir / "control_jitter_histogram.png")
        )
        
        scheduler.generate_jitter_histogram(
            task_name="planning_loop", 
            save_path=str(results_dir / "planning_jitter_histogram.png")
        )
        
        scheduler.generate_jitter_histogram(
            save_path=str(results_dir / "global_jitter_histogram.png")
        )
        
        return {
            'method': 'quartic_scheduler',
            'control_stats': control_stats,
            'planning_stats': planning_stats,
            'global_stats': global_stats,
            'control_execution_times': list(control_system.execution_times),
            'planning_execution_times': list(planning_system.execution_times)
        }


def analyze_jitter_comparison(traditional_results: Dict[str, Any], 
                            quartic_results: Dict[str, Any]) -> None:
    """Analyze and compare jitter between traditional and quartic approaches."""
    print("\n" + "="*60)
    print("JITTER COMPARISON ANALYSIS")
    print("="*60)
    
    # Calculate jitter for traditional approach
    traditional_timestamps = np.array(traditional_results['timestamps'])
    traditional_jitter = []
    
    if len(traditional_timestamps) > 1:
        expected_period = 1.0 / traditional_results['expected_frequency_hz']
        for i in range(1, len(traditional_timestamps)):
            actual_period = traditional_timestamps[i] - traditional_timestamps[i-1]
            jitter = (actual_period - expected_period) * 1000.0  # Convert to ms
            traditional_jitter.append(jitter)
    
    traditional_jitter = np.array(traditional_jitter)
    
    # Get quartic jitter data
    quartic_control_jitter = []
    if 'control_stats' in quartic_results and 'jitter_analysis' in quartic_results['control_stats']:
        jitter_data = quartic_results['control_stats']['jitter_analysis']
        quartic_control_jitter = [
            jitter_data['mean_jitter_ms'],
            jitter_data['std_jitter_ms'],
            jitter_data['max_jitter_ms'],
            jitter_data['min_jitter_ms']
        ]
    
    # Print comparison
    print("Traditional asyncio.sleep Jitter:")
    if len(traditional_jitter) > 0:
        print(f"  Mean: {np.mean(traditional_jitter):.3f}ms")
        print(f"  Std Dev: {np.std(traditional_jitter):.3f}ms")
        print(f"  Max: {np.max(traditional_jitter):.3f}ms")
        print(f"  Min: {np.min(traditional_jitter):.3f}ms")
        print(f"  Samples: {len(traditional_jitter)}")
    else:
        print("  No jitter data available")
    
    print("\nQuartic Scheduler Jitter (Control Task):")
    if quartic_control_jitter:
        print(f"  Mean: {quartic_control_jitter[0]:.3f}ms")
        print(f"  Std Dev: {quartic_control_jitter[1]:.3f}ms")
        print(f"  Max: {quartic_control_jitter[2]:.3f}ms")
        print(f"  Min: {quartic_control_jitter[3]:.3f}ms")
    else:
        print("  No jitter data available")
    
    # Create comparison plot
    if len(traditional_jitter) > 0:
        plt.figure(figsize=(15, 10))
        
        # Jitter comparison
        plt.subplot(2, 2, 1)
        plt.hist(traditional_jitter, bins=50, alpha=0.7, label='Traditional asyncio.sleep', 
                color='red', edgecolor='black')
        plt.xlabel('Jitter (ms)')
        plt.ylabel('Frequency')
        plt.title('Traditional asyncio.sleep Jitter Distribution')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Execution time comparison
        plt.subplot(2, 2, 2)
        traditional_exec_times = np.array(traditional_results['execution_times'])
        quartic_exec_times = np.array(quartic_results['control_execution_times'])
        
        plt.hist(traditional_exec_times, bins=30, alpha=0.7, label='Traditional', 
                color='red', edgecolor='black')
        plt.hist(quartic_exec_times, bins=30, alpha=0.7, label='Quartic Scheduler', 
                color='blue', edgecolor='black')
        plt.xlabel('Execution Time (ms)')
        plt.ylabel('Frequency')
        plt.title('Execution Time Distribution Comparison')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Frequency accuracy comparison
        plt.subplot(2, 2, 3)
        methods = ['Traditional', 'Quartic']
        freq_errors = [
            abs(traditional_results['actual_frequency_hz'] - traditional_results['expected_frequency_hz']) / traditional_results['expected_frequency_hz'] * 100,
            abs(quartic_results['control_stats']['actual_frequency_hz'] - quartic_results['control_stats']['frequency_hz']) / quartic_results['control_stats']['frequency_hz'] * 100
        ]
        
        bars = plt.bar(methods, freq_errors, color=['red', 'blue'], alpha=0.7)
        plt.ylabel('Frequency Error (%)')
        plt.title('Frequency Accuracy Comparison')
        plt.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar, error in zip(bars, freq_errors):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    f'{error:.2f}%', ha='center', va='bottom')
        
        # Performance summary
        plt.subplot(2, 2, 4)
        plt.axis('off')
        
        summary_text = f"""
        Performance Summary:
        
        Traditional asyncio.sleep:
        - Frequency Error: {freq_errors[0]:.2f}%
        - Mean Jitter: {np.mean(traditional_jitter):.3f}ms
        - Max Jitter: {np.max(traditional_jitter):.3f}ms
        
        Quartic Scheduler:
        - Frequency Error: {freq_errors[1]:.2f}%
        - Mean Jitter: {quartic_control_jitter[0] if quartic_control_jitter else 'N/A'}ms
        - Max Jitter: {quartic_control_jitter[2] if quartic_control_jitter else 'N/A'}ms
        
        Improvement:
        - Frequency accuracy improved by {freq_errors[0] - freq_errors[1]:.2f}%
        """
        
        plt.text(0.1, 0.5, summary_text, fontsize=10, verticalalignment='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        
        plt.tight_layout()
        
        # Save comparison plot
        results_dir = Path("results/quartic_demo")
        results_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(str(results_dir / "jitter_comparison.png"), dpi=300, bbox_inches='tight')
        print(f"\nComparison plot saved to: {results_dir / 'jitter_comparison.png'}")
        plt.show()


async def main():
    """Main demonstration function."""
    print("Quartic Scheduler Demonstration")
    print("Comparing traditional asyncio.sleep vs quartic scheduler")
    print("="*60)
    
    # Run demonstrations
    duration = 10.0  # 10 seconds each
    
    traditional_results = await traditional_asyncio_demo(duration)
    quartic_results = await quartic_scheduler_demo(duration)
    
    # Analyze and compare results
    analyze_jitter_comparison(traditional_results, quartic_results)
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("Check the 'results/quartic_demo/' directory for generated plots.")
    print("The quartic scheduler provides:")
    print("- More precise timing with reduced jitter")
    print("- Better frequency accuracy")
    print("- Comprehensive jitter analysis")
    print("- Support for multiple task priorities")
    print("- Real-time performance monitoring")


if __name__ == "__main__":
    asyncio.run(main()) 