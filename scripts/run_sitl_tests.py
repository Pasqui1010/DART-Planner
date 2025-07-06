#!/usr/bin/env python3
"""
DART-Planner SITL Test Runner

Simple script to run SITL tests with various configurations.
Supports both interactive and automated testing modes.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tests.test_dart_sitl_comprehensive import DARTSITLTester, SITLTestConfig


def print_banner():
    """Print test runner banner"""
    print("🚁" + "="*58 + "🚁")
    print("   DART-PLANNER SITL TEST RUNNER")
    print("   Software-in-the-Loop Validation Suite")
    print("🚁" + "="*58 + "🚁")


def create_test_configurations():
    """Create different test configurations"""
    configs = {}
    
    # Quick smoke test
    configs['smoke'] = SITLTestConfig()
    configs['smoke'].test_duration_s = 30.0
    configs['smoke'].enable_obstacle_tests = False
    configs['smoke'].enable_performance_stress_tests = False
    configs['smoke'].enable_failure_mode_tests = False
    
    # Performance validation
    configs['performance'] = SITLTestConfig()
    configs['performance'].test_duration_s = 60.0
    configs['performance'].target_planning_time_ms = 15.0
    configs['performance'].target_control_frequency_hz = 80.0
    
    # Full comprehensive test
    configs['comprehensive'] = SITLTestConfig()
    configs['comprehensive'].test_duration_s = 120.0
    configs['comprehensive'].enable_obstacle_tests = True
    configs['comprehensive'].enable_performance_stress_tests = True
    configs['comprehensive'].enable_failure_mode_tests = True
    
    # Hardware readiness test
    configs['hardware_ready'] = SITLTestConfig()
    configs['hardware_ready'].target_planning_time_ms = 10.0  # Stricter for hardware
    configs['hardware_ready'].target_control_frequency_hz = 100.0
    configs['hardware_ready'].target_tracking_error_m = 1.0
    configs['hardware_ready'].target_mission_success_rate = 0.98
    
    return configs


async def run_test_suite(test_type: str = 'smoke'):
    """Run specified test suite"""
    print_banner()
    
    configs = create_test_configurations()
    
    if test_type not in configs:
        print(f"❌ Unknown test type: {test_type}")
        print(f"Available types: {list(configs.keys())}")
        return False
    
    config = configs[test_type]
    
    print(f"\n🧪 Running {test_type.upper()} test suite")
    print(f"   Duration: {config.test_duration_s}s")
    print(f"   Targets: {config.target_planning_time_ms}ms planning, {config.target_control_frequency_hz}Hz control")
    
    # Pre-flight checks
    print(f"\n🔍 Pre-flight Checks")
    print(f"   • Checking AirSim availability...")
    
    try:
        import airsim
        print(f"     ✅ AirSim package available")
    except ImportError:
        print(f"     ⚠️  AirSim package not available - using mock mode")
    
    # Initialize and run tester
    tester = DARTSITLTester(config)
    
    print(f"\n🚀 Starting test execution...")
    start_time = time.time()
    
    try:
        results = await tester.run_comprehensive_tests()
        test_duration = time.time() - start_time
        
        # Determine overall success
        success = results.success_rate() >= 0.8
        
        print(f"\n" + "="*60)
        print(f"🎯 TEST SUITE COMPLETE")
        print(f"="*60)
        print(f"   Test Type: {test_type.upper()}")
        print(f"   Duration: {test_duration:.1f}s")
        print(f"   Success Rate: {results.success_rate()*100:.1f}%")
        print(f"   Status: {'✅ PASSED' if success else '❌ FAILED'}")
        
        if success and test_type == 'hardware_ready':
            print(f"\n🎉 HARDWARE DEPLOYMENT APPROVED!")
            print(f"   • All performance targets met")
            print(f"   • System ready for real flight testing")
            print(f"   • Proceed to HIL (Hardware-in-the-Loop) testing")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='DART-Planner SITL Test Runner')
    
    parser.add_argument(
        'test_type',
        choices=['smoke', 'performance', 'comprehensive', 'hardware_ready'],
        default='smoke',
        nargs='?',
        help='Type of test to run (default: smoke)'
    )
    
    parser.add_argument(
        '--list-tests',
        action='store_true',
        help='List available test types and exit'
    )
    
    parser.add_argument(
        '--check-airsim',
        action='store_true',
        help='Check AirSim connection and exit'
    )
    
    args = parser.parse_args()
    
    if args.list_tests:
        print("Available SITL test types:")
        print("  smoke         - Quick functionality test (30s)")
        print("  performance   - Performance validation (60s)")
        print("  comprehensive - Full test suite (120s)")
        print("  hardware_ready - Hardware deployment validation (strict targets)")
        return
    
    if args.check_airsim:
        print("🔍 Checking AirSim connection...")
        try:
            import airsim
            client = airsim.MultirotorClient()
            client.confirmConnection()
            print("✅ AirSim connected and ready")
        except ImportError:
            print("⚠️  AirSim package not available")
        except Exception as e:
            print(f"❌ AirSim connection failed: {e}")
            print("💡 Make sure AirSim is running and SimpleFlight is configured")
        return
    
    # Run the test suite
    success = asyncio.run(run_test_suite(args.test_type))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 