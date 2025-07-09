#!/usr/bin/env python3
"""
DART-Planner Dependency Management Script

This script helps manage dependencies and validate lockfile consistency.
It supports updating lockfiles and validating that they're synchronized with requirements.in files.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, and stderr."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def update_lockfiles() -> bool:
    """Update all lockfiles using pip-tools."""
    print("🔄 Updating lockfiles with pip-tools...")
    
    lockfile_configs = [
        ("requirements/requirements.in", "requirements/requirements.txt"),
        ("requirements/requirements-dev.in", "requirements/requirements-dev.txt"),
        ("requirements/requirements-ci.in", "requirements/requirements-ci.txt"),
    ]
    
    success = True
    for input_file, output_file in lockfile_configs:
        print(f"📦 Compiling {input_file} -> {output_file}")
        
        cmd = [
            "pip-compile",
            "--output-file", output_file,
            input_file
        ]
        
        exit_code, stdout, stderr = run_command(cmd)
        
        if exit_code != 0:
            print(f"❌ Failed to compile {input_file}")
            print(f"stdout: {stdout}")
            print(f"stderr: {stderr}")
            success = False
        else:
            print(f"✅ Successfully compiled {input_file}")
    
    return success


def validate_lockfiles() -> bool:
    """Validate that lockfiles are synchronized with requirements.in files."""
    print("🔍 Validating lockfile consistency...")
    
    lockfile_configs = [
        ("requirements/requirements.in", "requirements/requirements.txt"),
        ("requirements/requirements-dev.in", "requirements/requirements-dev.txt"),
        ("requirements/requirements-ci.in", "requirements/requirements-ci.txt"),
    ]
    
    success = True
    for input_file, output_file in lockfile_configs:
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        if not input_path.exists():
            print(f"❌ Input file not found: {input_file}")
            success = False
            continue
            
        if not output_path.exists():
            print(f"❌ Output file not found: {output_file}")
            success = False
            continue
        
        # Check if lockfile needs updating by running pip-compile --dry-run
        cmd = [
            "pip-compile",
            "--dry-run",
            "--output-file", output_file,
            input_file
        ]
        
        exit_code, stdout, stderr = run_command(cmd)
        
        if exit_code != 0:
            print(f"❌ Lockfile validation failed for {input_file}")
            print(f"stderr: {stderr}")
            success = False
        elif "Would update" in stdout:
            print(f"❌ Lockfile {output_file} is out of date")
            print("Run 'python scripts/update_dependencies.py update' to fix")
            success = False
        else:
            print(f"✅ Lockfile {output_file} is up to date")
    
    return success


def check_conflicts() -> bool:
    """Check for dependency conflicts."""
    print("🔍 Checking for dependency conflicts...")
    
    cmd = ["pip", "check"]
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code != 0:
        print("❌ Dependency conflicts detected:")
        print(stdout)
        print(stderr)
        return False
    else:
        print("✅ No dependency conflicts found")
        return True


def main():
    parser = argparse.ArgumentParser(description="DART-Planner Dependency Management")
    parser.add_argument(
        "command",
        choices=["update", "validate", "check"],
        help="Command to run: update lockfiles, validate consistency, or check conflicts"
    )
    
    args = parser.parse_args()
    
    if args.command == "update":
        success = update_lockfiles()
    elif args.command == "validate":
        success = validate_lockfiles()
    elif args.command == "check":
        success = check_conflicts()
    else:
        print(f"Unknown command: {args.command}")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 