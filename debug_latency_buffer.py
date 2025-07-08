#!/usr/bin/env python3

from dart_planner.utils.latency_buffer import LatencyBuffer

def debug_latency_buffer():
    """Debug the latency buffer behavior."""
    print("Creating latency buffer with 25ms delay, 5ms period")
    b = LatencyBuffer(0.025, 0.005)
    print(f"Buffer size: {b.buffer_size}")
    print(f"Required size: {b.required_size}")
    
    print("\nPushing data:")
    for i in range(10):
        result = b.push(f"data_{i}")
        print(f"Push {i}: {result} (buffer size: {len(b.buffer)})")
        
    print(f"\nFinal buffer contents: {[item[1] for item in b.buffer]}")
    print(f"Statistics: {b.get_statistics()}")

if __name__ == "__main__":
    debug_latency_buffer() 