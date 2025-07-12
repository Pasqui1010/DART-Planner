#!/usr/bin/env python3
"""
Debug script for quartic scheduler frequency issues.
"""

import asyncio
import time
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dart_planner.common.quartic_scheduler import (
    QuarticScheduler, QuarticTask, quartic_scheduler_context
)
from dart_planner.common.real_time_config import TaskPriority


async def debug_frequency():
    """Debug frequency accuracy issue."""
    print("Starting quartic scheduler debug...")
    
    execution_count = 0
    timestamps = []
    
    def counting_func():
        nonlocal execution_count
        execution_count += 1
        timestamps.append(time.perf_counter())
        if execution_count % 10 == 0:
            print(f"Executed {execution_count} times")
    
    async with quartic_scheduler_context(enable_monitoring=False) as scheduler:
        task = QuarticTask(
            name="debug_task",
            func=counting_func,
            frequency_hz=50.0
        )
        
        print(f"Task created with period: {task.period_s}s")
        print(f"Initial next_execution: {task.next_execution}")
        print(f"Current time: {time.perf_counter()}")
        
        scheduler.add_task(task)
        
        # Run for 1 second
        start_time = time.perf_counter()
        await asyncio.sleep(1.0)
        end_time = time.perf_counter()
        
        runtime = end_time - start_time
        expected_executions = int(50.0 * runtime)
        actual_executions = execution_count
        
        print(f"\nResults:")
        print(f"Runtime: {runtime:.3f}s")
        print(f"Expected executions: {expected_executions}")
        print(f"Actual executions: {actual_executions}")
        print(f"Frequency error: {((actual_executions - expected_executions) / expected_executions) * 100:.1f}%")
        
        if timestamps:
            intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
            avg_interval = sum(intervals) / len(intervals)
            print(f"Average interval: {avg_interval*1000:.2f}ms")
            print(f"Expected interval: {task.period_s*1000:.2f}ms")


if __name__ == "__main__":
    asyncio.run(debug_frequency()) 