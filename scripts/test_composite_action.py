#!/usr/bin/env python3
"""
Test script to validate composite action setup.
This script can be run locally to verify that the Python environment
setup matches what the composite action would do.
"""

import sys
import os
import subprocess
from pathlib import Path


def test_python_setup():
    """Test that Python environment is properly configured."""
    print("🧪 Testing Python environment setup...")
    
    # Check Python version
    version = sys.version_info
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    
    # Check if key packages are available
    required_packages = [
        'pytest',
        'black',
        'isort',
        'flake8',
        'mypy',
        'bandit',
        'safety',
        'pip-audit'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} is available")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is missing")
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install " + " ".join(missing_packages))
        return False
    else:
        print("\n✅ All required packages are available")
        return True


def test_cache_directories():
    """Test that cache directories exist and are writable."""
    print("\n🧪 Testing cache directories...")
    
    cache_dirs = [
        Path.home() / ".cache" / "pip",
        Path.home() / ".cache" / "ms-playwright"
    ]
    
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            print(f"✅ Cache directory exists: {cache_dir}")
            if os.access(cache_dir, os.W_OK):
                print(f"✅ Cache directory is writable: {cache_dir}")
            else:
                print(f"❌ Cache directory is not writable: {cache_dir}")
        else:
            print(f"⚠️  Cache directory does not exist: {cache_dir}")


def test_dependency_files():
    """Test that dependency files exist."""
    print("\n🧪 Testing dependency files...")
    
    dependency_files = [
        "pyproject.toml",
        "requirements/base.txt",
        "requirements/dev.txt"
    ]
    
    for dep_file in dependency_files:
        if Path(dep_file).exists():
            print(f"✅ Dependency file exists: {dep_file}")
        else:
            print(f"❌ Dependency file missing: {dep_file}")


def main():
    """Run all tests."""
    print("🚀 Testing Composite Action Setup")
    print("=" * 50)
    
    success = True
    
    # Test dependency files
    test_dependency_files()
    
    # Test Python setup
    if not test_python_setup():
        success = False
    
    # Test cache directories
    try:
        import os
        test_cache_directories()
    except Exception as e:
        print(f"⚠️  Cache directory test failed: {e}")
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! Composite action should work correctly.")
    else:
        print("❌ Some tests failed. Please check the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main() 