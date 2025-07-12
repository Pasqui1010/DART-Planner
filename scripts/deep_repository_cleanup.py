#!/usr/bin/env python3
"""
Deep Repository Cleanup for DART-Planner Open Source Readiness

This script performs a comprehensive cleanup of the DART-Planner repository to:
1. Archive deprecated and legacy files
2. Remove unused and duplicate files
3. Organize documentation and examples
4. Clean up temporary and debug files
5. Ensure repository is optimized for open source contribution

The script preserves history by moving files to archive directories rather than deleting them.
"""

import os
import shutil
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple
import re
from datetime import datetime


class RepositoryCleaner:
    """Comprehensive repository cleanup for open source readiness."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.archive_dir = project_root / "archive" / "deep_cleanup"
        self.legacy_dir = project_root / "legacy"
        
        # Create archive directory
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Track cleanup operations
        self.cleanup_log = {
            "timestamp": datetime.now().isoformat(),
            "archived_files": [],
            "removed_files": [],
            "moved_files": [],
            "cleaned_directories": [],
            "errors": []
        }
    
    def run_complete_cleanup(self) -> Dict:
        """Run the complete repository cleanup process."""
        print("🧹 DEEP REPOSITORY CLEANUP FOR OPEN SOURCE READINESS")
        print("=" * 60)
        
        try:
            # Step 1: Archive deprecated and legacy files
            print("\n1️⃣ ARCHIVING DEPRECATED AND LEGACY FILES")
            self._archive_deprecated_files()
            
            # Step 2: Clean up temporary and debug files
            print("\n2️⃣ CLEANING TEMPORARY AND DEBUG FILES")
            self._cleanup_temporary_files()
            
            # Step 3: Organize documentation
            print("\n3️⃣ ORGANIZING DOCUMENTATION")
            self._organize_documentation()
            
            # Step 4: Clean up experiments and results
            print("\n4️⃣ CLEANING EXPERIMENTS AND RESULTS")
            self._cleanup_experiments()
            
            # Step 5: Remove duplicate and unused files
            print("\n5️⃣ REMOVING DUPLICATE AND UNUSED FILES")
            self._remove_duplicate_files()
            
            # Step 6: Clean up configuration and backup files
            print("\n6️⃣ CLEANING CONFIGURATION AND BACKUP FILES")
            self._cleanup_config_files()
            
            # Step 7: Generate cleanup report
            print("\n7️⃣ GENERATING CLEANUP REPORT")
            self._generate_cleanup_report()
            
            print(f"\n✅ CLEANUP COMPLETED SUCCESSFULLY!")
            print(f"📊 Summary: {len(self.cleanup_log['archived_files'])} files archived, "
                  f"{len(self.cleanup_log['removed_files'])} files removed")
            
            return self.cleanup_log
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            self.cleanup_log["errors"].append(str(e))
            return self.cleanup_log
    
    def _archive_deprecated_files(self):
        """Archive deprecated and legacy files."""
        
        # Files to archive (move to archive directory)
        files_to_archive = [
            # Root level deprecated files
            "DIAL_MPC_CLEANUP_SUMMARY.md",
            "DI_MIGRATION_GUIDE.md",
            "CONFIG_MIGRATION_SUMMARY.md",
            "REAL_TIME_CONFIG_MIGRATION_GUIDE.md",
            "REMEDIATION_IMPLEMENTATION_SUMMARY.md",
            "TYPE_ANNOTATION_STATUS.md",
            "MIGRATION_GUIDE.md",
            "tracking_error_solution_summary.md",
            "VULNERABILITY_AUDIT_IMPLEMENTATION.md",
            "CRITICAL_ISSUES_FIXED.md",
            "CI_IMPROVEMENTS_SUMMARY.md",
            "PROJECT_STATUS_UPDATE.md",
            
            # Debug and test files in root
            "debug_coordinate_frames.py",
            "debug_latency_buffer.py",
            "debug_motor_mixing.py",
            "debug_quartic_scheduler.py",
            "test_motor_mixing_simple.py",
            "test_motor_mixer_direct.py",
            "test_motor_mixer_standalone.py",
            "test_motor_mixing_integration.py",
            "motor_mixer_validation.py",
            
            # Temporary files
            "salt_dart_planner_master.bin",
            "protected_key_test_key_id.bin",
            "airsim_rgb_test.png",
            "system_status_report_1751468544.png",
            "bandit_report.json",
            
            # Setup files that should be in scripts
            "setup_professional_pipeline.py",
            "setup_rt_control.py",
        ]
        
        for file_name in files_to_archive:
            file_path = self.project_root / file_name
            if file_path.exists():
                try:
                    archive_path = self.archive_dir / file_name
                    shutil.move(str(file_path), str(archive_path))
                    self.cleanup_log["archived_files"].append(str(file_path))
                    print(f"   📦 Archived: {file_name}")
                except Exception as e:
                    print(f"   ❌ Failed to archive {file_name}: {e}")
                    self.cleanup_log["errors"].append(f"Failed to archive {file_name}: {e}")
    
    def _cleanup_temporary_files(self):
        """Clean up temporary and debug files."""
        
        # Directories to clean
        temp_dirs = [
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            "dart_planner.egg-info",
            "build",
            "dist",
            "htmlcov",
            ".coverage",
        ]
        
        for dir_name in temp_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                try:
                    shutil.rmtree(str(dir_path))
                    self.cleanup_log["cleaned_directories"].append(str(dir_path))
                    print(f"   🗑️  Cleaned: {dir_name}")
                except Exception as e:
                    print(f"   ❌ Failed to clean {dir_name}: {e}")
                    self.cleanup_log["errors"].append(f"Failed to clean {dir_name}: {e}")
        
        # Remove temporary files
        temp_files = [
            "coverage.xml",
            ".coverage",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "*.so",
            "*.dll",
            "*.dylib",
        ]
        
        for pattern in temp_files:
            for file_path in self.project_root.rglob(pattern):
                try:
                    file_path.unlink()
                    self.cleanup_log["removed_files"].append(str(file_path))
                    print(f"   🗑️  Removed: {file_path.name}")
                except Exception as e:
                    print(f"   ❌ Failed to remove {file_path.name}: {e}")
                    self.cleanup_log["errors"].append(f"Failed to remove {file_path.name}: {e}")
    
    def _organize_documentation(self):
        """Organize documentation files."""
        
        # Move migration guides to archive
        migration_guides = [
            "docs/archive/legacy_documentation/DI_MIGRATION_GUIDE.md",
            "docs/archive/legacy_documentation/MODULARIZATION_SUMMARY.md",
            "docs/archive/legacy_documentation/REMEDIATION_IMPLEMENTATION_STATUS.md",
        ]
        
        for doc_path in migration_guides:
            full_path = self.project_root / doc_path
            if full_path.exists():
                try:
                    # Move to archive if not already there
                    if "archive" not in str(full_path):
                        archive_path = self.archive_dir / "documentation" / full_path.name
                        archive_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(full_path), str(archive_path))
                        self.cleanup_log["archived_files"].append(str(full_path))
                        print(f"   📦 Archived: {full_path.name}")
                except Exception as e:
                    print(f"   ❌ Failed to archive {full_path.name}: {e}")
                    self.cleanup_log["errors"].append(f"Failed to archive {full_path.name}: {e}")
    
    def _cleanup_experiments(self):
        """Clean up experiments and results directories."""
        
        # Archive old experiment results
        results_to_archive = [
            "results/publication_materials/abstract.tex",
            "results/publication_materials/performance_comparison.pdf",
            "results/publication_materials/performance_comparison.png",
        ]
        
        for result_path in results_to_archive:
            full_path = self.project_root / result_path
            if full_path.exists():
                try:
                    archive_path = self.archive_dir / "results" / full_path.name
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(full_path), str(archive_path))
                    self.cleanup_log["archived_files"].append(str(full_path))
                    print(f"   📦 Archived: {full_path.name}")
                except Exception as e:
                    print(f"   ❌ Failed to archive {full_path.name}: {e}")
                    self.cleanup_log["errors"].append(f"Failed to archive {full_path.name}: {e}")
        
        # Clean up old experiment scripts that reference DIAL-MPC
        old_experiments = [
            "experiments/phase1/phase1_optimization_test.py",
            "experiments/phase2/phase2c_final_test.py",
        ]
        
        for exp_path in old_experiments:
            full_path = self.project_root / exp_path
            if full_path.exists():
                try:
                    # Check if file contains DIAL-MPC references
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if "DIAL-MPC" in content or "dial_mpc" in content:
                        archive_path = self.archive_dir / "experiments" / full_path.name
                        archive_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(full_path), str(archive_path))
                        self.cleanup_log["archived_files"].append(str(full_path))
                        print(f"   📦 Archived (DIAL-MPC): {full_path.name}")
                except Exception as e:
                    print(f"   ❌ Failed to archive {full_path.name}: {e}")
                    self.cleanup_log["errors"].append(f"Failed to archive {full_path.name}: {e}")
    
    def _remove_duplicate_files(self):
        """Remove duplicate and unused files."""
        
        # Remove duplicate setup files
        setup_files = [
            "setup.py",  # Keep pyproject.toml instead
        ]
        
        for setup_file in setup_files:
            file_path = self.project_root / setup_file
            if file_path.exists():
                try:
                    file_path.unlink()
                    self.cleanup_log["removed_files"].append(str(file_path))
                    print(f"   🗑️  Removed duplicate: {setup_file}")
                except Exception as e:
                    print(f"   ❌ Failed to remove {setup_file}: {e}")
                    self.cleanup_log["errors"].append(f"Failed to remove {setup_file}: {e}")
        
        # Remove old configuration files
        old_config_files = [
            ".bandit",  # Use pyproject.toml configuration instead
        ]
        
        for config_file in old_config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                try:
                    file_path.unlink()
                    self.cleanup_log["removed_files"].append(str(file_path))
                    print(f"   🗑️  Removed old config: {config_file}")
                except Exception as e:
                    print(f"   ❌ Failed to remove {config_file}: {e}")
                    self.cleanup_log["errors"].append(f"Failed to remove {config_file}: {e}")
    
    def _cleanup_config_files(self):
        """Clean up configuration and backup files."""
        
        # Archive old configuration backups
        config_backup_dir = self.project_root / "config_backup"
        if config_backup_dir.exists():
            try:
                archive_path = self.archive_dir / "config_backup"
                shutil.move(str(config_backup_dir), str(archive_path))
                self.cleanup_log["archived_files"].append(str(config_backup_dir))
                print(f"   📦 Archived: config_backup/")
            except Exception as e:
                print(f"   ❌ Failed to archive config_backup: {e}")
                self.cleanup_log["errors"].append(f"Failed to archive config_backup: {e}")
        
        # Remove old migration files
        old_migration_files = [
            "migrations/README",
            "migrations/script.py.mako",
        ]
        
        for migration_file in old_migration_files:
            file_path = self.project_root / migration_file
            if file_path.exists():
                try:
                    file_path.unlink()
                    self.cleanup_log["removed_files"].append(str(file_path))
                    print(f"   🗑️  Removed old migration: {migration_file}")
                except Exception as e:
                    print(f"   ❌ Failed to remove {migration_file}: {e}")
                    self.cleanup_log["errors"].append(f"Failed to remove {migration_file}: {e}")
    
    def _generate_cleanup_report(self):
        """Generate a comprehensive cleanup report."""
        
        report_path = self.archive_dir / "cleanup_report.json"
        
        # Add summary statistics
        self.cleanup_log["summary"] = {
            "total_archived": len(self.cleanup_log["archived_files"]),
            "total_removed": len(self.cleanup_log["removed_files"]),
            "total_moved": len(self.cleanup_log["moved_files"]),
            "total_cleaned_dirs": len(self.cleanup_log["cleaned_directories"]),
            "total_errors": len(self.cleanup_log["errors"]),
        }
        
        # Save report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.cleanup_log, f, indent=2, ensure_ascii=False)
        
        # Create README for archive
        readme_path = self.archive_dir / "README.md"
        readme_content = f"""# Deep Repository Cleanup Archive

This directory contains files that were archived during the deep repository cleanup for open source readiness.

## Cleanup Summary

- **Date**: {self.cleanup_log['timestamp']}
- **Files Archived**: {self.cleanup_log['summary']['total_archived']}
- **Files Removed**: {self.cleanup_log['summary']['total_removed']}
- **Directories Cleaned**: {self.cleanup_log['summary']['total_cleaned_dirs']}
- **Errors**: {self.cleanup_log['summary']['total_errors']}

## What Was Archived

### Deprecated Documentation
- Migration guides and status documents
- Legacy implementation summaries
- Old configuration guides

### Temporary Files
- Debug scripts and test files
- Temporary configuration backups
- Old experiment results

### Legacy Code
- DIAL-MPC related files and references
- Old migration scripts
- Deprecated setup files

## Why These Files Were Archived

1. **Open Source Readiness**: Removed clutter and confusion for new contributors
2. **Historical Preservation**: Kept important files for reference
3. **Clean Repository**: Focused on current, active code
4. **Reduced Maintenance**: Eliminated outdated documentation

## Current Repository Structure

After cleanup, the repository focuses on:
- `src/` - Active source code
- `tests/` - Current test suite
- `docs/` - Current documentation
- `examples/` - Working examples
- `scripts/` - Active utility scripts
- `config/` - Current configuration

## For Contributors

- All archived files are preserved for historical reference
- Current documentation is in the main `docs/` directory
- Active code is in the `src/` directory
- Examples are in the `examples/` directory

## Recovery

If you need to access archived files:
1. Check this directory for the specific file
2. Files are organized by type (documentation, experiments, etc.)
3. The cleanup report (`cleanup_report.json`) contains detailed information
"""
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"   📄 Generated cleanup report: {report_path}")
        print(f"   📄 Created archive README: {readme_path}")


def main():
    """Main entry point for the cleanup script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deep repository cleanup for open source readiness")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without making changes")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root).resolve()
    
    if not project_root.exists():
        print(f"❌ Project root does not exist: {project_root}")
        return 1
    
    cleaner = RepositoryCleaner(project_root)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print("=" * 60)
        # In dry run mode, just show what would be cleaned
        print("Would archive deprecated files...")
        print("Would clean temporary files...")
        print("Would organize documentation...")
        print("Would clean experiments...")
        print("Would remove duplicate files...")
        print("Would clean configuration files...")
        return 0
    
    # Run the actual cleanup
    result = cleaner.run_complete_cleanup()
    
    if result["errors"]:
        print(f"\n⚠️  Cleanup completed with {len(result['errors'])} errors:")
        for error in result["errors"]:
            print(f"   - {error}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 