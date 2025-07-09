#!/usr/bin/env python3
"""
Comprehensive test runner for DART-Planner.

Executes all test suites including:
- Unit tests with coverage
- API tests for admin endpoints
- E2E Playwright tests for admin panel UI
- PixhawkInterface tests with MAVLink mocking
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
import time


class TestRunner:
    """Comprehensive test runner for DART-Planner"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.project_root = os.getcwd()
    
    def run_command(self, command, description, capture_output=True):
        """Run a command and return results"""
        print(f"\n{'='*60}")
        print(f"🔄 {description}")
        print(f"{'='*60}")
        
        try:
            if capture_output:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
            else:
                result = subprocess.run(
                    command,
                    cwd=self.project_root
                )
                return result.returncode == 0
            
            if result.returncode == 0:
                print(f"✅ {description} - PASSED")
                if result.stdout:
                    print("Output:")
                    print(result.stdout)
                return True
            else:
                print(f"❌ {description} - FAILED")
                if result.stderr:
                    print("Error:")
                    print(result.stderr)
                if result.stdout:
                    print("Output:")
                    print(result.stdout)
                return False
                
        except Exception as e:
            print(f"❌ {description} - ERROR: {e}")
            return False
    
    def run_unit_tests_with_coverage(self):
        """Run unit tests with coverage reporting"""
        command = [
            "python", "-m", "pytest", "tests/", "-v",
            "--cov=src", "--cov=dart_planner",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-report=xml",
            "--cov-fail-under=75",
            "-m", "not slow"
        ]
        return self.run_command(command, "Unit Tests with Coverage")
    
    def run_pixhawk_interface_tests(self):
        """Run PixhawkInterface unit tests"""
        command = ["python", "-m", "pytest", "tests/test_pixhawk_interface.py", "-v"]
        return self.run_command(command, "PixhawkInterface Unit Tests")
    
    def run_admin_api_tests(self):
        """Run admin API tests"""
        command = ["python", "-m", "pytest", "tests/test_admin_api.py", "-v"]
        return self.run_command(command, "Admin API Tests")
    
    def run_e2e_tests(self):
        """Run E2E Playwright tests"""
        # First check if Playwright browsers are installed
        if not self.run_command(["python", "-m", "playwright", "--version"], "Check Playwright Installation", capture_output=False):
            print("Installing Playwright browsers...")
            self.run_command(["python", "-m", "playwright", "install"], "Install Playwright Browsers", capture_output=False)
        
        command = ["python", "-m", "pytest", "tests/e2e/test_admin_panel_ui.py", "-v"]
        return self.run_command(command, "E2E Admin Panel UI Tests")
    
    def run_security_tests(self):
        """Run security-related tests"""
        command = ["python", "-m", "pytest", "tests/test_security.py", "tests/test_security_fixes.py", "-v"]
        return self.run_command(command, "Security Tests")
    
    def run_integration_tests(self):
        """Run integration tests"""
        command = ["python", "-m", "pytest", "tests/test_communication_flow.py", "tests/test_planner_controller_integration.py", "-v"]
        return self.run_command(command, "Integration Tests")
    
    def run_slow_tests(self):
        """Run slow tests (optional)"""
        command = ["python", "-m", "pytest", "tests/", "-v", "-m", "slow"]
        return self.run_command(command, "Slow Tests")
    
    def generate_coverage_report(self):
        """Generate detailed coverage report"""
        print(f"\n{'='*60}")
        print("📊 Coverage Report Summary")
        print(f"{'='*60}")
        
        # Check if coverage.xml exists
        coverage_file = os.path.join(self.project_root, "coverage.xml")
        if os.path.exists(coverage_file):
            print("✅ Coverage report generated successfully")
            print(f"📁 HTML report: {os.path.join(self.project_root, 'htmlcov', 'index.html')}")
            print(f"📁 XML report: {coverage_file}")
        else:
            print("⚠️ No coverage report found")
    
    def run_all_tests(self, include_slow=False, e2e_only=False, unit_only=False):
        """Run all test suites"""
        self.start_time = time.time()
        
        print("🚀 DART-Planner Test Suite")
        print("=" * 60)
        print(f"Project root: {self.project_root}")
        print(f"Python version: {sys.version}")
        
        results = {}
        
        if e2e_only:
            # Run only E2E tests
            results['e2e'] = self.run_e2e_tests()
        elif unit_only:
            # Run only unit tests
            results['unit'] = self.run_unit_tests_with_coverage()
            results['pixhawk'] = self.run_pixhawk_interface_tests()
            results['admin_api'] = self.run_admin_api_tests()
            results['security'] = self.run_security_tests()
            results['integration'] = self.run_integration_tests()
        else:
            # Run all tests
            results['unit'] = self.run_unit_tests_with_coverage()
            results['pixhawk'] = self.run_pixhawk_interface_tests()
            results['admin_api'] = self.run_admin_api_tests()
            results['security'] = self.run_security_tests()
            results['integration'] = self.run_integration_tests()
            results['e2e'] = self.run_e2e_tests()
            
            if include_slow:
                results['slow'] = self.run_slow_tests()
        
        # Generate coverage report
        self.generate_coverage_report()
        
        # Print summary
        self.print_summary(results)
        
        return all(results.values())
    
    def print_summary(self, results):
        """Print test execution summary"""
        end_time = time.time()
        duration = end_time - (self.start_time or 0)
        
        print(f"\n{'='*60}")
        print("📋 Test Execution Summary")
        print(f"{'='*60}")
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:15} : {status}")
        
        print(f"\nOverall: {passed}/{total} test suites passed")
        print(f"Duration: {duration:.2f} seconds")
        
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print("⚠️ Some tests failed. Check the output above for details.")
            sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run DART-Planner test suite")
    parser.add_argument(
        "--slow", 
        action="store_true", 
        help="Include slow tests"
    )
    parser.add_argument(
        "--e2e-only", 
        action="store_true", 
        help="Run only E2E tests"
    )
    parser.add_argument(
        "--unit-only", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--coverage-only", 
        action="store_true", 
        help="Run only coverage tests"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.coverage_only:
        success = runner.run_unit_tests_with_coverage()
    elif args.e2e_only:
        success = runner.run_all_tests(e2e_only=True)
    elif args.unit_only:
        success = runner.run_all_tests(unit_only=True)
    else:
        success = runner.run_all_tests(include_slow=args.slow)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main() 
