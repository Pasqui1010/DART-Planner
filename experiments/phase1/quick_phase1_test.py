#!/usr/bin/env python3
"""
Quick Phase 1 Performance Test - Direct Run
Tests the current system performance after Phase 1 optimizations
"""

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import subprocess
import threading

from dart_planner.cloud.main_improved import main_improved as cloud_main
from dart_planner.edge.main_improved import main_improved


def run_quick_test():
    """Run a quick 15-second test to evaluate Phase 1 performance"""

    print("🔍 Phase 1 Performance Test")
    print("=" * 50)
    print("📊 Testing system with Phase 1 optimizations")
    print("🎯 Target: <30m position error")
    print("⏱️  Duration: 15 seconds")
    print("=" * 50)

    # Start cloud planner in background
    print("\n🌩️  Starting cloud planner...")
    cloud_process = None

    try:
        # Start cloud in subprocess
        cloud_process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.append('src'); from dart_planner.cloud.main_improved import main_improved; main_improved()",
            ],
            cwd=os.getcwd(),
        )

        # Give cloud time to start
        time.sleep(2)

        # Run edge controller directly
        print("🔧 Starting edge controller test...")
        main_improved(duration=15.0)

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        if cloud_process:
            print("🧹 Cleaning up cloud process...")
            cloud_process.terminate()
            try:
                cloud_process.wait(timeout=3)
            except:
                cloud_process.kill()

        print("✅ Test completed!")


if __name__ == "__main__":
    run_quick_test()
