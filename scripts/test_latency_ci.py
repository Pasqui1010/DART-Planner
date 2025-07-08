#!/usr/bin/env python3
"""
Real-time Latency CI Testing Script

Standalone script for testing real-time latency requirements in CI environments.
Enforces the 50ms 95th percentile requirement for planner-to-actuator path.

Usage:
    python scripts/test_latency_ci.py [--duration SECONDS] [--frequency HZ] [--verbose]
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Add src to path for imports

from tests.test_real_time_latency import RealTimeLatencyTester


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Real-time Latency CI Testing")
    parser.add_argument(
        "--duration", 
        type=float, 
        default=30.0,
        help="Test duration in seconds (default: 30.0)"
    )
    parser.add_argument(
        "--frequency", 
        type=float, 
        default=10.0,
        help="Measurement frequency in Hz (default: 10.0)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--output", 
        type=str,
        help="Output results to JSON file"
    )
    return parser.parse_args()


async def main():
    """Main test execution"""
    args = parse_args()
    
    print("🚀 DART-Planner Real-time Latency CI Test")
    print("=" * 50)
    print(f"Duration: {args.duration}s")
    print(f"Frequency: {args.frequency}Hz")
    print(f"Target: <50ms 95th percentile")
    print()
    
    # Run latency test
    tester = RealTimeLatencyTester(
        test_duration_seconds=args.duration,
        measurement_frequency_hz=args.frequency
    )
    
    try:
        results = await tester.run_latency_test()
        
        # Print results
        if args.verbose:
            tester.print_results(results)
        else:
            print("📊 Latency Test Results:")
            print(f"   Total measurements: {results.total_measurements}")
            print(f"   Success rate: {results.success_rate*100:.1f}%")
            print(f"   Total P95 latency: {results.total_p95_ms:.1f}ms")
            print(f"   Planning P95 latency: {results.planning_p95_ms:.1f}ms")
            print(f"   Control P95 latency: {results.control_p95_ms:.1f}ms")
            print(f"   Actuator P95 latency: {results.actuator_p95_ms:.1f}ms")
        
        # Check requirements
        requirements_met = (
            results.meets_total_requirement and
            results.meets_planning_requirement and
            results.meets_control_requirement and
            results.meets_actuator_requirement and
            results.success_rate >= 0.95
        )
        
        print(f"\n🎯 Requirements Status:")
        print(f"   Total P95 ≤ 50ms: {'✅ PASS' if results.meets_total_requirement else '❌ FAIL'}")
        print(f"   Planning P95 ≤ 50ms: {'✅ PASS' if results.meets_planning_requirement else '❌ FAIL'}")
        print(f"   Control P95 ≤ 5ms: {'✅ PASS' if results.meets_control_requirement else '❌ FAIL'}")
        print(f"   Actuator P95 ≤ 2ms: {'✅ PASS' if results.meets_actuator_requirement else '❌ FAIL'}")
        print(f"   Success rate ≥ 95%: {'✅ PASS' if results.success_rate >= 0.95 else '❌ FAIL'}")
        
        # Output to JSON if requested
        if args.output:
            output_data = {
                "test_config": {
                    "duration_seconds": args.duration,
                    "frequency_hz": args.frequency,
                    "timestamp": time.time()
                },
                "results": {
                    "total_measurements": results.total_measurements,
                    "successful_measurements": results.successful_measurements,
                    "success_rate": results.success_rate,
                    "latency_stats": {
                        "total": {
                            "p50_ms": results.total_p50_ms,
                            "p95_ms": results.total_p95_ms,
                            "p99_ms": results.total_p99_ms,
                            "mean_ms": results.total_mean_ms,
                            "max_ms": results.total_max_ms
                        },
                        "planning": {
                            "p50_ms": results.planning_p50_ms,
                            "p95_ms": results.planning_p95_ms,
                            "p99_ms": results.planning_p99_ms,
                            "mean_ms": results.planning_mean_ms,
                            "max_ms": results.planning_max_ms
                        },
                        "control": {
                            "p50_ms": results.control_p50_ms,
                            "p95_ms": results.control_p95_ms,
                            "p99_ms": results.control_p99_ms,
                            "mean_ms": results.control_mean_ms,
                            "max_ms": results.control_max_ms
                        },
                        "actuator": {
                            "p50_ms": results.actuator_p50_ms,
                            "p95_ms": results.actuator_p95_ms,
                            "p99_ms": results.actuator_p99_ms,
                            "mean_ms": results.actuator_mean_ms,
                            "max_ms": results.actuator_max_ms
                        }
                    },
                    "requirements_met": {
                        "total": results.meets_total_requirement,
                        "planning": results.meets_planning_requirement,
                        "control": results.meets_control_requirement,
                        "actuator": results.meets_actuator_requirement,
                        "success_rate": results.success_rate >= 0.95
                    }
                }
            }
            
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\n📁 Results saved to: {args.output}")
        
        # Final status
        if requirements_met:
            print(f"\n🎉 ALL LATENCY REQUIREMENTS MET!")
            return 0
        else:
            print(f"\n❌ SOME LATENCY REQUIREMENTS FAILED")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 
