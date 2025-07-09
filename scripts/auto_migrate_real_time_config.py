#!/usr/bin/env python3
"""
Automated migration script for real-time configuration consolidation.
Run this script to automatically update imports and function calls.
"""

import re
from pathlib import Path

def migrate_file(file_path: Path):
    """Migrate a single file from legacy to new config system."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace imports
        content = re.sub(
            r"from dart_planner\.config\.real_time_config import",
            "from dart_planner.config.frozen_config import",
            content
        )

        content = re.sub(
            r"import dart_planner\.config\.real_time_config",
            "import dart_planner.config.frozen_config",
            content
        )

        # Replace function calls
        content = re.sub(
            r"get_real_time_config\(config\)",
            "config.real_time",
            content
        )

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Migrated {file_path}")
    except Exception as e:
        print(f"❌ Error migrating {file_path}: {e}")

def main():
    """Main migration function."""
    files_to_migrate = [
        Path("examples\real_time_integration_example.py"),
        Path("scripts\migrate_real_time_config.py"),
        Path("src\dart_planner\common\real_time_integration.py"),
    ]

    print("🔄 Starting real-time configuration migration...")
    for file_path in files_to_migrate:
        migrate_file(file_path)
    print("✅ Migration completed!")

if __name__ == "__main__":
    main()