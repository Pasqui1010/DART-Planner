#!/usr/bin/env python3
"""
Coordinate Frame Validation Script

This script validates that coordinate frame handling is consistent across the DART-Planner codebase.
It checks for frame-ambiguous functions and ensures proper coordinate frame usage.

Usage:
    python scripts/validate_coordinate_frames.py [--fix] [--verbose]
    
Exit codes:
    0: All validation passed
    1: Validation errors found
    2: Configuration or setup errors
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import subprocess

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dart_planner.common.coordinate_frames import WorldFrame, get_coordinate_frame_manager
from dart_planner.config.frozen_config import get_frozen_config


class CoordinateFrameValidator:
    """Validates coordinate frame consistency across the codebase."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
        # Patterns that indicate frame-ambiguous code
        self.frame_ambiguous_patterns = [
            # Direct gravity usage without frame context
            (r'np\.array\(\s*\[\s*0\s*,\s*0\s*,\s*[+-]?9\.8\d*\s*\]\s*\)', 
             'Hardcoded gravity vector - should use coordinate frame manager'),
            
            # Hardcoded altitude calculations
            (r'altitude\s*=\s*-?\s*\w+\.\w+\[2\]', 
             'Hardcoded altitude calculation - should use get_altitude_from_position()'),
            
            # Direct Z-axis assumptions
            (r'position\[2\].*altitude|altitude.*position\[2\]', 
             'Direct Z-axis altitude assumption - should use coordinate frame manager'),
            
            # Hardcoded NED/ENU conversions
            (r'# NED|# ENU', 
             'Hardcoded coordinate frame comment - should use coordinate frame manager'),
            
            # Hardcoded coordinate transformations
            (r'np\.array\(\s*\[\s*\w+\[1\]\s*,\s*\w+\[0\]\s*,\s*-\w+\[2\]\s*\]\s*\)', 
             'Hardcoded coordinate transformation - should use frame manager methods'),
        ]
        
        # Files to check
        self.source_dirs = [
            Path("src/dart_planner"),
            Path("tests"),
            Path("examples"),
            Path("scripts"),
        ]
        
        # Files to exclude from validation
        self.exclude_patterns = [
            "*.pyc",
            "__pycache__",
            ".git",
            "*.egg-info",
            "build",
            "dist",
            "validate_coordinate_frames.py",  # This file
            "coordinate_frames.py",  # Implementation file
        ]
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with optional level."""
        if self.verbose or level != "INFO":
            print(f"[{level}] {message}")
    
    def add_error(self, error: str):
        """Add an error to the list."""
        self.errors.append(error)
        self.log(error, "ERROR")
    
    def add_warning(self, warning: str):
        """Add a warning to the list."""
        self.warnings.append(warning)
        self.log(warning, "WARNING")
    
    def get_python_files(self) -> List[Path]:
        """Get all Python files to check."""
        python_files = []
        
        for source_dir in self.source_dirs:
            if source_dir.exists():
                for file_path in source_dir.rglob("*.py"):
                    # Check if file should be excluded
                    if any(pattern in str(file_path) for pattern in self.exclude_patterns):
                        continue
                    python_files.append(file_path)
        
        return python_files
    
    def validate_frame_ambiguous_patterns(self) -> bool:
        """Check for frame-ambiguous patterns in code."""
        self.log("Checking for frame-ambiguous patterns...")
        
        python_files = self.get_python_files()
        found_issues = False
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern, description in self.frame_ambiguous_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                    
                    for match in matches:
                        line_number = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_number - 1].strip()
                        
                        self.add_error(
                            f"{file_path}:{line_number}: {description}\n"
                            f"    Found: {line_content}"
                        )
                        found_issues = True
                        
            except Exception as e:
                self.add_error(f"Error reading {file_path}: {e}")
                found_issues = True
        
        return not found_issues
    
    def validate_coordinate_frame_imports(self) -> bool:
        """Check that coordinate frame utilities are properly imported."""
        self.log("Checking coordinate frame imports...")
        
        python_files = self.get_python_files()
        found_issues = False
        
        # Files that should use coordinate frame manager
        gravity_usage_files = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for gravity usage
                if re.search(r'gravity|altitude|position\[2\]', content, re.IGNORECASE):
                    gravity_usage_files.append(file_path)
                
                # Check for coordinate frame manager import
                if 'coordinate_frames' in content:
                    if not re.search(r'from.*coordinate_frames.*import', content):
                        self.add_warning(
                            f"{file_path}: References coordinate_frames but doesn't import it"
                        )
                        
            except Exception as e:
                self.add_error(f"Error reading {file_path}: {e}")
                found_issues = True
        
        # Check that gravity usage files import coordinate frame manager
        for file_path in gravity_usage_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Skip test files and implementation files
                if 'test_' in str(file_path) or 'coordinate_frames.py' in str(file_path):
                    continue
                
                if 'gravity' in content.lower() and 'coordinate_frames' not in content:
                    self.add_warning(
                        f"{file_path}: Uses gravity but doesn't import coordinate_frames"
                    )
                    
            except Exception as e:
                self.add_error(f"Error reading {file_path}: {e}")
                found_issues = True
        
        return not found_issues
    
    def validate_config_consistency(self) -> bool:
        """Validate that coordinate frame configuration is consistent."""
        self.log("Checking coordinate frame configuration consistency...")
        
        try:
            # Check that frozen config can be loaded
            config = get_frozen_config()
            frame_config = config.coordinate_frame
            
            self.log(f"Current coordinate frame: {frame_config.world_frame.value}")
            self.log(f"Enforce consistency: {frame_config.enforce_consistency}")
            
            # Check that coordinate frame manager can be initialized
            frame_manager = get_coordinate_frame_manager()
            
            # Validate gravity vector
            gravity_vector = frame_manager.get_gravity_vector()
            expected_magnitude = 9.80665
            actual_magnitude = abs(gravity_vector[2])  # Z component should have gravity magnitude
            
            if abs(actual_magnitude - expected_magnitude) > 0.001:
                self.add_error(
                    f"Gravity vector magnitude mismatch: expected {expected_magnitude}, "
                    f"got {actual_magnitude}"
                )
                return False
            
            # Validate frame consistency
            if frame_config.world_frame == WorldFrame.ENU:
                if gravity_vector[2] >= 0:
                    self.add_error(
                        f"ENU frame should have negative Z gravity, got {gravity_vector}"
                    )
                    return False
            elif frame_config.world_frame == WorldFrame.NED:
                if gravity_vector[2] <= 0:
                    self.add_error(
                        f"NED frame should have positive Z gravity, got {gravity_vector}"
                    )
                    return False
            
            self.log("Configuration consistency check passed")
            return True
            
        except Exception as e:
            self.add_error(f"Configuration validation failed: {e}")
            return False
    
    def validate_test_coverage(self) -> bool:
        """Check that coordinate frame functionality is properly tested."""
        self.log("Checking coordinate frame test coverage...")
        
        test_files = []
        for source_dir in self.source_dirs:
            if source_dir.exists():
                test_files.extend(source_dir.rglob("test_*.py"))
        
        # Check for coordinate frame tests
        coordinate_frame_tests = []
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'coordinate_frame' in content.lower():
                    coordinate_frame_tests.append(test_file)
                    
            except Exception as e:
                self.add_error(f"Error reading {test_file}: {e}")
        
        if not coordinate_frame_tests:
            self.add_warning("No coordinate frame tests found")
            return False
        
        self.log(f"Found {len(coordinate_frame_tests)} test files with coordinate frame tests")
        return True
    
    def run_validation(self) -> bool:
        """Run all validation checks."""
        self.log("Starting coordinate frame validation...")
        
        all_passed = True
        
        # Run all validation checks
        checks = [
            ("Frame-ambiguous patterns", self.validate_frame_ambiguous_patterns),
            ("Coordinate frame imports", self.validate_coordinate_frame_imports),
            ("Configuration consistency", self.validate_config_consistency),
            ("Test coverage", self.validate_test_coverage),
        ]
        
        for check_name, check_func in checks:
            self.log(f"Running {check_name} check...")
            try:
                if not check_func():
                    all_passed = False
                    self.log(f"{check_name} check failed", "ERROR")
                else:
                    self.log(f"{check_name} check passed")
            except Exception as e:
                self.add_error(f"{check_name} check failed with exception: {e}")
                all_passed = False
        
        return all_passed
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*60)
        print("COORDINATE FRAME VALIDATION SUMMARY")
        print("="*60)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All coordinate frame validation checks passed!")
        elif not self.errors:
            print(f"\n✅ No errors found, but {len(self.warnings)} warnings")
        else:
            print(f"\n❌ Found {len(self.errors)} errors and {len(self.warnings)} warnings")
        
        print()


def main():
    parser = argparse.ArgumentParser(description="Validate coordinate frame consistency")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    parser.add_argument("--fix", action="store_true",
                       help="Attempt to fix some issues automatically (not implemented)")
    
    args = parser.parse_args()
    
    if args.fix:
        print("ERROR: --fix option is not yet implemented")
        return 2
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    validator = CoordinateFrameValidator(verbose=args.verbose)
    
    try:
        success = validator.run_validation()
        validator.print_summary()
        
        if success:
            return 0
        else:
            return 1
            
    except Exception as e:
        print(f"ERROR: Validation failed with exception: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main()) 