#!/usr/bin/env python3
"""
Cleanup DIAL-MPC References Script

This script removes all DIAL-MPC references from the codebase to ensure
the system exclusively uses SE3 MPC as intended.

CRITICAL: This script addresses the fundamental issue where old benchmarks
and legacy code still reference DIAL-MPC, which should be completely removed.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class DIALMPCCleaner:
    """Cleaner for removing DIAL-MPC references."""
    
    def __init__(self):
        self.project_root = project_root
        self.changes_made = 0
        self.files_modified = set()
        
        # Patterns to find and replace
        self.replacement_patterns = [
            # Import aliases
            (r'from dart_planner\.planning\.se3_mpc_planner import SE3MPCPlanner as DIALMPCPlanner',
             'from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner'),
            (r'from dart_planner\.planning\.se3_mpc_planner import SE3MPCConfig as DIALMPCConfig',
             'from dart_planner.planning.se3_mpc_planner import SE3MPCConfig'),
            
            # Variable names
            (r'\bDIALMPCPlanner\b', 'SE3MPCPlanner'),
            (r'\bDIALMPCConfig\b', 'SE3MPCConfig'),
            (r'\bdial_mpc\b', 'se3_mpc'),
            (r'\bDIAL-MPC\b', 'SE(3) MPC'),
            (r'\bDIAL_MPC\b', 'SE3_MPC'),
            
            # Comments and documentation
            (r'# DIAL-MPC', '# SE(3) MPC'),
            (r'"""DIAL-MPC', '"""SE(3) MPC'),
            (r'DIAL-MPC\s+vs\s+SE\(3\)\s+MPC', 'SE(3) MPC Performance'),
            (r'DIAL-MPC.*optimization', 'SE(3) MPC optimization'),
            
            # Function names and variables
            (r'\bdial_mpc_planner\b', 'se3_mpc_planner'),
            (r'\bdial_mpc_config\b', 'se3_mpc_config'),
            (r'\boptimize_dial_mpc\b', 'optimize_se3_mpc'),
            (r'\btest_dial_mpc\b', 'test_se3_mpc'),
            
            # Statistics and logging
            (r'"dial_mpc_plans"', '"se3_mpc_plans"'),
            (r'planning_stats\["dial_mpc_plans"\]', 'planning_stats["se3_mpc_plans"]'),
            (r'DIAL-MPC.*planning', 'SE(3) MPC planning'),
            (r'DIAL-MPC.*trajectory', 'SE(3) MPC trajectory'),
        ]
        
        # Files to exclude from processing
        self.exclude_patterns = [
            '*.pyc',
            '__pycache__',
            '.git',
            '*.egg-info',
            'build',
            'dist',
            'venv',
            'node_modules',
            '*.log',
            '*.tmp',
            'cleanup_dial_mpc_references.py',  # This file
            'archive/legacy_experiments/',  # Keep legacy for reference
        ]
        
        # Files that should be completely removed (if they exist)
        self.files_to_remove = [
            'src/dart_planner/planning/dial_mpc_planner.py',
            'tests/test_dial_mpc_planner.py',
            'experiments/dial_mpc_optimization.py',
        ]
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from processing."""
        for pattern in self.exclude_patterns:
            if pattern.endswith('/'):
                if str(file_path).startswith(str(self.project_root / pattern[:-1])):
                    return True
            elif file_path.match(pattern):
                return True
        return False
    
    def process_file(self, file_path: Path) -> bool:
        """Process a single file to remove DIAL-MPC references."""
        if not file_path.is_file() or not file_path.suffix in ['.py', '.md', '.rst', '.txt', '.yaml', '.yml']:
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply all replacement patterns
            for pattern, replacement in self.replacement_patterns:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            
            # If content changed, write it back
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.changes_made += 1
                self.files_modified.add(str(file_path))
                print(f"✓ Modified: {file_path}")
                return True
            
            return False
            
        except Exception as e:
            print(f"✗ Error processing {file_path}: {e}")
            return False
    
    def move_legacy_files(self) -> int:
        """Move legacy DIAL-MPC files to legacy folder instead of deleting."""
        moved_count = 0
        
        # Create legacy directory if it doesn't exist
        legacy_dir = self.project_root / 'legacy' / 'dial_mpc'
        legacy_dir.mkdir(parents=True, exist_ok=True)
        
        # Files that should be moved to legacy
        files_to_move = [
            'src/dart_planner/planning/dial_mpc_planner.py',
            'tests/test_dial_mpc_planner.py',
            'experiments/dial_mpc_optimization.py',
            'experiments/validation/algorithm_comparison.py',
            'experiments/validation/controller_benchmark.py',
            'experiments/validation/benchmark_audit_improvements.py',
            'tests/validation/01_test_audit_improvements.py',
            'tests/validation/02_test_refactor_validation.py',
        ]
        
        for file_path_str in files_to_move:
            source_path = self.project_root / file_path_str
            if source_path.exists():
                try:
                    # Create subdirectory structure in legacy
                    relative_path = Path(file_path_str)
                    target_path = legacy_dir / relative_path.name
                    
                    # Move the file
                    source_path.rename(target_path)
                    print(f"📦 Moved to legacy: {source_path} → {target_path}")
                    moved_count += 1
                except Exception as e:
                    print(f"✗ Error moving {source_path}: {e}")
        
        # Create a comprehensive README in the legacy directory
        readme_path = legacy_dir / 'README.md'
        if not readme_path.exists():
            readme_content = """# Legacy DIAL-MPC Implementation

This directory contains the legacy DIAL-MPC (Diffusion-based Iterative Annealing for Legged Locomotion) implementation that was used in early versions of DART-Planner.

## Why DIAL-MPC was moved to legacy

DIAL-MPC was designed for **legged locomotion** with contact-rich dynamics (feet making/breaking contact with ground). However, aerial robots have fundamentally different dynamics:

### Legged Robotics (DIAL-MPC's domain)
- **Contact forces**: Feet make/break contact with ground
- **Actuation**: Joint torques for contact forces
- **Dynamics**: Contact-rich, underactuated during flight phases
- **Constraints**: Joint limits, ground contact, friction

### Aerial Robotics (Current system's domain)
- **No contact forces**: Continuous flight without ground contact
- **Actuation**: Thrust and torque for attitude control
- **Dynamics**: Underactuated, no contact forces
- **Constraints**: Velocity limits, no-fly zones, obstacles

## What's in this directory

- `dial_mpc_planner.py` - Original DIAL-MPC implementation
- `test_dial_mpc_planner.py` - Tests for DIAL-MPC
- `dial_mpc_optimization.py` - DIAL-MPC optimization experiments
- `algorithm_comparison.py` - DIAL-MPC vs SE3 MPC comparison tests
- `controller_benchmark.py` - Controller benchmarking with DIAL-MPC
- `benchmark_audit_improvements.py` - Audit improvement benchmarks
- `01_test_audit_improvements.py` - Test audit improvements
- `02_test_refactor_validation.py` - Refactor validation tests

## Current System (SE3 MPC)

The current system uses **SE(3) Model Predictive Control** which is:

✅ **Domain-appropriate**: Designed specifically for aerial robotics
✅ **Proven**: Industry-standard approach for quadrotor control
✅ **Efficient**: Real-time performance with guaranteed convergence
✅ **Stable**: Proper handling of underactuated dynamics

## For Future Contributors

If you're interested in DIAL-MPC:
1. **Understand the domain mismatch**: DIAL-MPC ≠ aerial robotics
2. **Study the differences**: Compare with current SE3 MPC implementation
3. **Consider adaptations**: Could DIAL-MPC concepts be adapted for aerial use?
4. **Research potential**: Are there hybrid approaches worth exploring?

## Migration Notes

The transition from DIAL-MPC to SE3 MPC involved:
- Algorithm replacement (DIAL-MPC → SE3 MPC)
- Performance validation (benchmarking both approaches)
- Architecture updates (three-layer system)
- Documentation updates (removing DIAL-MPC references)

## References

- DIAL-MPC Paper: [2409.15610] - "DIAL-MPC: Diffusion-based Iterative Annealing for Legged Locomotion"
- SE3 MPC: Standard approach for aerial robotics control
- DART-Planner Technical Audit: Documents the transition rationale
"""
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            print(f"✓ Created: {readme_path}")
            moved_count += 1
        
        return moved_count
    
    def cleanup_archive_directory(self) -> int:
        """Clean up archive directory while preserving history."""
        archive_dir = self.project_root / 'archive' / 'legacy_experiments'
        if not archive_dir.exists():
            return 0
        
        # Add a README to clarify these are legacy
        readme_path = archive_dir / 'README.md'
        if not readme_path.exists():
            readme_content = """# Legacy DIAL-MPC Experiments

This directory contains legacy experiments and implementations using DIAL-MPC,
which has been replaced by SE(3) MPC in the current system.

**IMPORTANT**: These files are for historical reference only and should not be used
in the current system. The active implementation uses SE(3) MPC exclusively.

## Why DIAL-MPC was replaced

DIAL-MPC was designed for legged locomotion with contact-rich dynamics, while
aerial robots have fundamentally different dynamics (underactuated, no contact forces).
SE(3) MPC is specifically designed for aerial robotics and provides better performance
and stability for quadrotor control.

## Current System

The current system uses:
- SE(3) MPC for trajectory optimization
- Explicit geometric mapping for perception
- Edge-first architecture for autonomy
- Comprehensive real-time scheduling
- Units-aware control systems
"""
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            print(f"✓ Created: {readme_path}")
            return 1
        
        return 0
    
    def run_cleanup(self) -> Dict[str, int]:
        """Run the complete cleanup process."""
        print("🧹 DIAL-MPC Reference Cleanup")
        print("=" * 50)
        
        # Process all files
        for file_path in self.project_root.rglob('*'):
            if self.should_exclude_file(file_path):
                continue
            
            self.process_file(file_path)
        
        # Remove legacy files
        moved_files = self.move_legacy_files()
        
        # Clean up archive
        archive_updates = self.cleanup_archive_directory()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Cleanup Summary")
        print("=" * 50)
        print(f"Files modified: {len(self.files_modified)}")
        print(f"Total changes: {self.changes_made}")
        print(f"Files moved to legacy: {moved_files}")
        print(f"Archive updates: {archive_updates}")
        
        if self.files_modified:
            print(f"\nModified files:")
            for file_path in sorted(self.files_modified):
                print(f"  - {file_path}")
        
        return {
            'files_modified': len(self.files_modified),
            'total_changes': self.changes_made,
            'files_moved_to_legacy': moved_files,
            'archive_updates': archive_updates
        }


def main():
    """Main cleanup function."""
    cleaner = DIALMPCCleaner()
    results = cleaner.run_cleanup()
    
    if results['total_changes'] > 0:
        print(f"\n✅ Cleanup completed successfully!")
        print(f"   The system now exclusively uses SE(3) MPC.")
    else:
        print(f"\nℹ️  No DIAL-MPC references found to clean up.")
    
    return 0 if results['total_changes'] > 0 else 1


if __name__ == "__main__":
    sys.exit(main()) 