#!/usr/bin/env python3
"""
Migration script to update legacy imports to new DI container and frozen config modules.

This script will:
1. Find all files with legacy imports
2. Replace them with new imports
3. Generate a migration report
4. Optionally create a backup of changed files
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
import argparse


class ImportMigrator:
    """Handles migration of legacy imports to new modules."""
    
    def __init__(self, project_root: Path, dry_run: bool = True, backup: bool = False):
        self.project_root = project_root
        self.dry_run = dry_run
        self.backup = backup
        self.changes: List[Dict] = []
        
        # Migration patterns: (old_import, new_import, description)
        self.migrations = [
            # Direct imports
            (
                r'from dart_planner\.common\.di_container import',
                'from dart_planner.common.di_container_v2 import',
                'DI container v1 to v2'
            ),
            (
                r'from dart_planner\.config\.settings import get_config',
                'from dart_planner.config.frozen_config import get_frozen_config as get_config',
                'Config settings to frozen_config'
            ),
            (
                r'from dart_planner\.config\.settings import DARTPlannerConfig',
                'from dart_planner.config.frozen_config import DARTPlannerFrozenConfig as DARTPlannerConfig',
                'Config class to frozen config class'
            ),
            # Import aliases
            (
                r'import dart_planner\.common\.di_container as di',
                'import dart_planner.common.di_container_v2 as di',
                'DI container import alias'
            ),
            (
                r'import dart_planner\.common\.di_container',
                'import dart_planner.common.di_container_v2',
                'DI container direct import'
            ),
            # Config manager imports
            (
                r'from dart_planner\.config\.settings import ConfigManager',
                'from dart_planner.config.frozen_config import ConfigurationManager as ConfigManager',
                'Config manager class'
            ),
            (
                r'from dart_planner\.config\.settings import get_config_manager',
                'from dart_planner.config.frozen_config import get_config_manager',
                'Config manager function'
            ),
        ]
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv', 'venv', 'build', 'dist'}]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def _fix_multiline_import(self, import_text: str, old_module: str, new_module: str) -> str:
        """Fix multiline imports by replacing the module name."""
        return import_text.replace(old_module, new_module)
    
    def _fix_multiline_config_import(self, import_text: str) -> str:
        """Fix multiline config imports with proper mappings."""
        # Replace the module name
        result = import_text.replace('dart_planner.config.settings', 'dart_planner.config.frozen_config')
        
        # Handle specific class name changes
        result = result.replace('DARTPlannerConfig', 'DARTPlannerFrozenConfig as DARTPlannerConfig')
        result = result.replace('ConfigManager', 'ConfigurationManager as ConfigManager')
        result = result.replace('get_config', 'get_frozen_config as get_config')
        
        return result
    
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate imports in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_changed = False
            
            for old_pattern, new_pattern, description in self.migrations:
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_pattern, content)
                    file_changed = True
                    self.changes.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'migration': description,
                        'old': old_pattern,
                        'new': new_pattern
                    })
            
            # Handle multiline imports separately
            if re.search(r'from dart_planner\.common\.di_container import \([\s\S]*?\)', content):
                content = re.sub(
                    r'from dart_planner\.common\.di_container import \([\s\S]*?\)',
                    lambda m: self._fix_multiline_import(m.group(0), 'di_container', 'di_container_v2'),
                    content
                )
                file_changed = True
                self.changes.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'migration': 'DI container multiline import',
                    'old': 'multiline di_container import',
                    'new': 'multiline di_container_v2 import'
                })
            
            if re.search(r'from dart_planner\.config\.settings import \([\s\S]*?\)', content):
                content = re.sub(
                    r'from dart_planner\.config\.settings import \([\s\S]*?\)',
                    lambda m: self._fix_multiline_config_import(m.group(0)),
                    content
                )
                file_changed = True
                self.changes.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'migration': 'Config settings multiline import',
                    'old': 'multiline settings import',
                    'new': 'multiline frozen_config import'
                })
            
            if file_changed and not self.dry_run:
                # Create backup if requested
                if self.backup:
                    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
                    shutil.copy2(file_path, backup_path)
                
                # Write updated content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return file_changed
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return False
    
    def run_migration(self) -> Dict:
        """Run the complete migration process."""
        print("🔍 Finding Python files...")
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files")
        
        print("\n🔄 Starting migration...")
        migrated_files = 0
        
        for file_path in python_files:
            if self.migrate_file(file_path):
                migrated_files += 1
                if self.dry_run:
                    print(f"  Would migrate: {file_path.relative_to(self.project_root)}")
                else:
                    print(f"  Migrated: {file_path.relative_to(self.project_root)}")
        
        # Generate report
        report = {
            'total_files': len(python_files),
            'migrated_files': migrated_files,
            'changes': self.changes,
            'dry_run': self.dry_run
        }
        
        return report
    
    def print_report(self, report: Dict):
        """Print a detailed migration report."""
        print("\n" + "="*60)
        print("MIGRATION REPORT")
        print("="*60)
        print(f"Total files scanned: {report['total_files']}")
        print(f"Files {'would be ' if report['dry_run'] else ''}migrated: {report['migrated_files']}")
        
        if report['changes']:
            print(f"\nChanges {'that would be ' if report['dry_run'] else ''}made:")
            for change in report['changes']:
                print(f"  📁 {change['file']}")
                print(f"     {change['migration']}")
                print(f"     {change['old']} → {change['new']}")
                print()
        
        if report['dry_run']:
            print("💡 This was a dry run. Use --execute to apply changes.")
        else:
            print("✅ Migration completed successfully!")
            if self.backup:
                print("💾 Backups created with .bak extension")


def main():
    parser = argparse.ArgumentParser(description='Migrate legacy imports to new modules')
    parser.add_argument('--execute', action='store_true', help='Actually apply changes (default is dry run)')
    parser.add_argument('--backup', action='store_true', help='Create backup files before modifying')
    parser.add_argument('--project-root', type=Path, default=Path.cwd(), help='Project root directory')
    
    args = parser.parse_args()
    
    migrator = ImportMigrator(
        project_root=args.project_root,
        dry_run=not args.execute,
        backup=args.backup
    )
    
    report = migrator.run_migration()
    migrator.print_report(report)
    
    if report['dry_run'] and report['migrated_files'] > 0:
        print("\n🚀 To apply these changes, run:")
        print("   python scripts/migrate_imports.py --execute")
        if args.backup:
            print("   python scripts/migrate_imports.py --execute --backup")


if __name__ == '__main__':
    main() 