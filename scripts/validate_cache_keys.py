#!/usr/bin/env python3
"""
Validate cache key generation logic for CI workflows.
This script simulates the cache key generation used in GitHub Actions.
"""

import hashlib
import os
from pathlib import Path


def generate_cache_key(os_name, cache_key_prefix, files):
    """Generate a cache key similar to GitHub Actions cache action."""
    # Create a hash of the specified files
    file_hashes = []
    for file_pattern in files:
        for file_path in Path('.').glob(file_pattern):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                    file_hashes.append(f"{file_path}:{file_hash}")
    
    # Sort for consistent ordering
    file_hashes.sort()
    
    # Create the final hash
    content = f"{os_name}-{cache_key_prefix}-{'-'.join(file_hashes)}"
    return hashlib.md5(content.encode()).hexdigest()[:8]


def main():
    """Validate cache key generation for different scenarios."""
    print("🔍 Validating Cache Key Generation")
    print("=" * 50)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Quality Pipeline - Python 3.10",
            "os": "ubuntu",
            "prefix": "main",
            "files": ["**/pyproject.toml", "**/requirements*.txt"]
        },
        {
            "name": "Quality Pipeline - Python 3.9",
            "os": "ubuntu", 
            "prefix": "legacy",
            "files": ["**/pyproject.toml", "**/requirements*.txt"]
        },
        {
            "name": "SITL Tests",
            "os": "ubuntu",
            "prefix": "sitl",
            "files": ["**/requirements*.txt"]
        },
        {
            "name": "Docker Build",
            "os": "ubuntu",
            "prefix": "buildx",
            "files": ["demos/Dockerfile", "pyproject.toml"]
        }
    ]
    
    for scenario in scenarios:
        cache_key = generate_cache_key(
            scenario["os"],
            scenario["prefix"], 
            scenario["files"]
        )
        
        print(f"\n📋 {scenario['name']}")
        print(f"   OS: {scenario['os']}")
        print(f"   Prefix: {scenario['prefix']}")
        print(f"   Files: {', '.join(scenario['files'])}")
        print(f"   Cache Key: {scenario['os']}-pip-{scenario['prefix']}-{cache_key}")
        
        # Show restore keys
        print(f"   Restore Keys:")
        print(f"     - {scenario['os']}-pip-{scenario['prefix']}-")
        print(f"     - {scenario['os']}-pip-")
    
    print("\n" + "=" * 50)
    print("✅ Cache key validation completed")
    print("\n💡 Tips:")
    print("- Cache keys should be unique for different dependency sets")
    print("- Restore keys provide fallback options for cache hits")
    print("- File hashes ensure cache invalidation when dependencies change")


if __name__ == "__main__":
    main() 