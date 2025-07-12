#!/usr/bin/env python3
"""
DART-Planner Obsolete Files Cleanup Script

This script identifies and archives obsolete files that are no longer needed
for the open source release, including temporary .md files, migration guides,
and cleanup artifacts.
"""

import os
import shutil
import glob
from pathlib import Path
from datetime import datetime
import argparse


class ObsoleteFilesCleanup:
    """Clean up obsolete files from the repository."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_root = Path.cwd()
        self.archive_dir = self.project_root / "archive" / "obsolete_files"
        self.cleanup_log = []
        
    def identify_obsolete_files(self):
        """Identify files that should be archived."""
        
        obsolete_files = []
        
        # Temporary/cleanup .md files (these are artifacts of the cleanup process)
        temp_md_files = [
            "DIAL_MPC_CLEANUP_SUMMARY.md",
            "PROJECT_STATUS_UPDATE.md", 
            "REMEDIATION_IMPLEMENTATION_SUMMARY.md",
            "REPOSITORY_CLEANUP_SUMMARY.md",
            "FINAL_CLEANUP_SUMMARY.md",
            "VERIFICATION_REPORT.md",
            "tracking_error_solution_summary.md",
            "TYPE_ANNOTATION_STATUS.md",
            "VALIDATION_RESULTS.md",
            "VULNERABILITY_AUDIT_IMPLEMENTATION.md",
            "REAL_TIME_CONFIG_MIGRATION_GUIDE.md",
            "CONFIG_MIGRATION_SUMMARY.md",
            "DI_MIGRATION_GUIDE.md",
            "MIGRATION_GUIDE.md",
            "CRITICAL_ISSUES_FIXED.md",
            "CI_IMPROVEMENTS_SUMMARY.md",
        ]
        
        # Temporary/backup files
        temp_files = [
            "README.md.backup",  # Empty backup file
            "bandit_report.json",  # Security scan report (regenerated)
        ]
        
        # Check each file
        for filename in temp_md_files + temp_files:
            file_path = self.project_root / filename
            if file_path.exists():
                obsolete_files.append(file_path)
                
        # Check for other temporary files
        temp_patterns = [
            "*.tmp",
            "*.bak", 
            "*.backup",
            "*_backup.*",
            "*_temp.*",
            "*_tmp.*",
        ]
        
        for pattern in temp_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    obsolete_files.append(file_path)
                    
        return obsolete_files
    
    def should_preserve_file(self, file_path: Path) -> bool:
        """Check if a file should be preserved despite being in obsolete list."""
        
        preserve_files = {
            # Keep these as they contain important information
            "README.md",
            "CONTRIBUTING.md", 
            "CODE_OF_CONDUCT.md",
            "LICENSE",
            "pyproject.toml",
            "requirements.txt",
            "requirements.in",
            "setup.py",
            "Makefile",
            ".gitignore",
            ".dockerignore",
            "docker-compose.yml",
            "docker-compose.dev.yml", 
            "docker-compose.demo.yml",
            "pytest.ini",
            ".flake8",
            ".bandit",
            "importlinter.ini",
            "alembic.ini",
            "env.example",
            "airsim_settings.json",
            ".pre-commit-config.yaml",
            ".editorconfig",
        }
        
        return file_path.name in preserve_files
    
    def archive_file(self, file_path: Path) -> bool:
        """Archive a single file."""
        
        if self.should_preserve_file(file_path):
            print(f"⚠️  Preserving important file: {file_path.name}")
            return False
            
        try:
            # Create archive directory if it doesn't exist
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine destination path
            dest_path = self.archive_dir / file_path.name
            
            # Handle filename conflicts
            counter = 1
            original_dest = dest_path
            while dest_path.exists():
                stem = original_dest.stem
                suffix = original_dest.suffix
                dest_path = self.archive_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            if self.dry_run:
                print(f"🔍 [DRY RUN] Would archive: {file_path} -> {dest_path}")
                return True
            else:
                # Move file to archive
                shutil.move(str(file_path), str(dest_path))
                print(f"📦 Archived: {file_path.name} -> {dest_path}")
                self.cleanup_log.append(f"Archived: {file_path.name}")
                return True
                
        except Exception as e:
            print(f"❌ Failed to archive {file_path}: {e}")
            return False
    
    def create_archive_readme(self):
        """Create a README explaining what was archived and why."""
        
        readme_content = f"""# Obsolete Files Archive

This directory contains files that were archived during the DART-Planner repository cleanup for open source release.

## Archive Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Why These Files Were Archived

### Temporary Documentation Files
These files were created during the development and cleanup process but are no longer needed for the open source release:

- **Cleanup Summaries**: Reports from various cleanup operations
- **Migration Guides**: Documentation for completed migrations  
- **Status Updates**: Temporary project status reports
- **Implementation Summaries**: Reports from completed implementations
- **Validation Results**: Temporary validation reports

### Temporary Files
- **Backup Files**: Empty or temporary backup files
- **Report Files**: Generated reports that can be recreated
- **Temporary Files**: Various temporary files created during development

## Files Archived

"""
        
        # Add list of archived files
        if self.archive_dir.exists():
            for file_path in sorted(self.archive_dir.glob("*")):
                if file_path.is_file():
                    readme_content += f"- `{file_path.name}`\n"
        
        readme_content += """

## Accessing Archived Files

If you need to reference any of these files:
1. They are preserved in this archive directory
2. They contain historical context and implementation details
3. They can be referenced for understanding the project's evolution

## Important Note

These files were archived because they are:
- **Temporary**: Created during development/cleanup process
- **Redundant**: Information is now in permanent documentation
- **Obsolete**: Superseded by current implementation
- **Generated**: Can be recreated if needed

The core project functionality and documentation remain intact in the main repository.

---
*This archive was created automatically by the repository cleanup script.*
"""
        
        readme_path = self.archive_dir / "README.md"
        if not self.dry_run:
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            print(f"📝 Created archive README: {readme_path}")
        else:
            print(f"🔍 [DRY RUN] Would create archive README: {readme_path}")
    
    def run_cleanup(self):
        """Run the complete cleanup process."""
        
        print("🧹 DART-Planner Obsolete Files Cleanup")
        print("=" * 50)
        
        # Identify obsolete files
        obsolete_files = self.identify_obsolete_files()
        
        if not obsolete_files:
            print("✅ No obsolete files found!")
            return
        
        print(f"📋 Found {len(obsolete_files)} potentially obsolete files:")
        for file_path in obsolete_files:
            print(f"   - {file_path.name}")
        
        print(f"\n{'[DRY RUN] ' if self.dry_run else ''}Starting cleanup...")
        
        # Archive files
        archived_count = 0
        for file_path in obsolete_files:
            if self.archive_file(file_path):
                archived_count += 1
        
        # Create archive README
        self.create_archive_readme()
        
        # Summary
        print(f"\n📊 Cleanup Summary:")
        print(f"   Files processed: {len(obsolete_files)}")
        print(f"   Files archived: {archived_count}")
        print(f"   Files preserved: {len(obsolete_files) - archived_count}")
        
        if self.cleanup_log:
            print(f"\n📝 Cleanup Log:")
            for entry in self.cleanup_log:
                print(f"   {entry}")
        
        print(f"\n✅ Cleanup {'simulation ' if self.dry_run else ''}completed!")
        
        if self.dry_run:
            print("\n💡 To perform actual cleanup, run without --dry-run flag")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Clean up obsolete files from DART-Planner")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without actually doing it")
    
    args = parser.parse_args()
    
    cleanup = ObsoleteFilesCleanup(dry_run=args.dry_run)
    cleanup.run_cleanup()


if __name__ == "__main__":
    main() 