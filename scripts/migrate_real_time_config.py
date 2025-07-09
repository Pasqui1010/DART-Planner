#!/usr/bin/env python3
"""
Migration script to transition from legacy real_time_config.py to consolidated frozen_config.py.

This script:
1. Identifies files using legacy real_time_config imports
2. Provides migration guidance
3. Updates imports to use the new consolidated system
4. Validates the migration
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Set
import ast

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dart_planner.config.frozen_config import DARTPlannerFrozenConfig, RealTimeConfig


class RealTimeConfigMigrator:
    """Migrator for real-time configuration consolidation."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.tests_dir = project_root / "tests"
        self.examples_dir = project_root / "examples"
        self.scripts_dir = project_root / "scripts"
        
        # Legacy imports to replace
        self.legacy_imports = {
            'dart_planner.config.real_time_config': 'dart_planner.config.frozen_config',
            'dart_planner.common.real_time_config': 'dart_planner.common.real_time_config',  # Keep this for now
        }
        
        # Function mappings
        self.function_mappings = {
            'get_real_time_config': 'config.real_time',
            'get_task_timing_config': 'config.real_time',
            'get_scheduling_config': 'config.real_time',
            'get_performance_monitoring_config': 'config.real_time',
            'get_control_loop_config': 'config.real_time',
            'get_planning_loop_config': 'config.real_time',
            'get_safety_loop_config': 'config.real_time',
            'get_communication_config': 'config.real_time',
            'extend_config_with_real_time': 'REMOVED - use frozen config directly',
        }
    
    def find_files_with_legacy_imports(self) -> List[Path]:
        """Find all Python files that import from legacy real_time_config."""
        files_with_legacy_imports = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv', 'venv', 'build', 'dist', '.pytest_cache'}]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    if self._has_legacy_imports(file_path):
                        files_with_legacy_imports.append(file_path)
        
        return files_with_legacy_imports
    
    def _has_legacy_imports(self, file_path: Path) -> bool:
        """Check if a file has legacy real_time_config imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for legacy imports
            legacy_patterns = [
                r'from dart_planner\.config\.real_time_config import',
                r'import dart_planner\.config\.real_time_config',
                r'from dart_planner\.config\.real_time_config\.',
            ]
            
            for pattern in legacy_patterns:
                if re.search(pattern, content):
                    return True
            
            return False
        except Exception:
            return False
    
    def analyze_legacy_usage(self, file_path: Path) -> Dict[str, Any]:
        """Analyze how legacy real_time_config is used in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            analysis = {
                'imports': [],
                'function_calls': [],
                'class_usage': [],
                'suggested_migration': []
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if 'real_time_config' in alias.name:
                            analysis['imports'].append(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and 'real_time_config' in node.module:
                        analysis['imports'].append(f"from {node.module}")
                        for alias in node.names:
                            analysis['function_calls'].append(alias.name)
                
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in self.function_mappings:
                        analysis['function_calls'].append(node.func.id)
            
            return analysis
        except Exception as e:
            return {'error': str(e)}
    
    def generate_migration_guide(self, files_with_legacy_imports: List[Path]) -> str:
        """Generate a migration guide for the identified files."""
        guide = []
        guide.append("# Real-Time Configuration Migration Guide")
        guide.append("")
        guide.append("## Overview")
        guide.append("The legacy `dart_planner.config.real_time_config` module has been consolidated")
        guide.append("into `dart_planner.config.frozen_config.RealTimeConfig`. This migration")
        guide.append("eliminates configuration duplication and provides a single source of truth.")
        guide.append("")
        
        guide.append("## Files Requiring Migration")
        guide.append("")
        
        for file_path in files_with_legacy_imports:
            relative_path = file_path.relative_to(self.project_root)
            analysis = self.analyze_legacy_usage(file_path)
            
            guide.append(f"### {relative_path}")
            guide.append("")
            
            if 'error' in analysis:
                guide.append(f"⚠️ Error analyzing file: {analysis['error']}")
                guide.append("")
                continue
            
            if analysis['imports']:
                guide.append("**Legacy Imports:**")
                for imp in analysis['imports']:
                    guide.append(f"- `{imp}`")
                guide.append("")
            
            if analysis['function_calls']:
                guide.append("**Legacy Function Calls:**")
                for func in analysis['function_calls']:
                    if func in self.function_mappings:
                        guide.append(f"- `{func}` → {self.function_mappings[func]}")
                    else:
                        guide.append(f"- `{func}` → Check if still needed")
                guide.append("")
            
            guide.append("**Migration Steps:**")
            guide.append("1. Remove legacy imports")
            guide.append("2. Use `config.real_time` directly from frozen config")
            guide.append("3. Update function calls to access properties directly")
            guide.append("4. Test the changes")
            guide.append("")
        
        guide.append("## Migration Examples")
        guide.append("")
        guide.append("### Before (Legacy)")
        guide.append("```python")
        guide.append("from dart_planner.config.frozen_config import get_real_time_config")
        guide.append("")
        guide.append("config = get_config()")
        guide.append("rt_config = config.real_time")
        guide.append("frequency = rt_config.task_timing.control_loop_frequency_hz")
        guide.append("```")
        guide.append("")
        
        guide.append("### After (Consolidated)")
        guide.append("```python")
        guide.append("from dart_planner.config.frozen_config import get_frozen_config")
        guide.append("")
        guide.append("config = get_frozen_config()")
        guide.append("frequency = config.real_time.control_loop_frequency_hz")
        guide.append("```")
        guide.append("")
        
        guide.append("## New Configuration Properties")
        guide.append("")
        guide.append("The consolidated `RealTimeConfig` includes all properties from the legacy system:")
        guide.append("")
        
        # Get all properties from the new RealTimeConfig
        rt_config = RealTimeConfig()
        for field_name, field_info in rt_config.__fields__.items():
            default_value = field_info.default
            description = getattr(field_info, 'description', 'No description')
            guide.append(f"- `{field_name}`: {description} (default: {default_value})")
        
        guide.append("")
        guide.append("## Environment Variables")
        guide.append("")
        guide.append("All real-time configuration can be set via environment variables:")
        guide.append("")
        guide.append("- `DART_CONTROL_FREQUENCY_HZ` - Control loop frequency")
        guide.append("- `DART_PLANNING_FREQUENCY_HZ` - Planning loop frequency")
        guide.append("- `DART_SAFETY_FREQUENCY_HZ` - Safety loop frequency")
        guide.append("- `DART_MAX_CONTROL_LATENCY_MS` - Maximum control latency")
        guide.append("- `DART_ENABLE_DEADLINE_MONITORING` - Enable deadline monitoring")
        guide.append("- And many more... (see frozen_config.py for complete list)")
        guide.append("")
        
        guide.append("## Validation")
        guide.append("")
        guide.append("After migration, validate your configuration:")
        guide.append("")
        guide.append("```python")
        guide.append("from dart_planner.config.frozen_config import get_frozen_config")
        guide.append("")
        guide.append("config = get_frozen_config()")
        guide.append("print(f\"Control frequency: {config.real_time.control_loop_frequency_hz} Hz\")")
        guide.append("print(f\"Planning frequency: {config.real_time.planning_loop_frequency_hz} Hz\")")
        guide.append("```")
        
        return "\n".join(guide)
    
    def create_migration_script(self, files_with_legacy_imports: List[Path]) -> str:
        """Create an automated migration script."""
        script_lines = []
        script_lines.append("#!/usr/bin/env python3")
        script_lines.append('"""')
        script_lines.append("Automated migration script for real-time configuration consolidation.")
        script_lines.append("Run this script to automatically update imports and function calls.")
        script_lines.append('"""')
        script_lines.append("")
        script_lines.append("import re")
        script_lines.append("from pathlib import Path")
        script_lines.append("")
        
        script_lines.append("def migrate_file(file_path: Path):")
        script_lines.append('    """Migrate a single file from legacy to new config system."""')
        script_lines.append("    try:")
        script_lines.append("        with open(file_path, 'r', encoding='utf-8') as f:")
        script_lines.append("            content = f.read()")
        script_lines.append("")
        script_lines.append("        # Replace imports")
        script_lines.append('        content = re.sub(')
        script_lines.append('            r"from dart_planner\\.config\\.real_time_config import",')
        script_lines.append('            "from dart_planner.config.frozen_config import",')
        script_lines.append('            content')
        script_lines.append('        )')
        script_lines.append("")
        script_lines.append('        content = re.sub(')
        script_lines.append('            r"import dart_planner\\.config\\.real_time_config",')
        script_lines.append('            "import dart_planner.config.frozen_config",')
        script_lines.append('            content')
        script_lines.append('        )')
        script_lines.append("")
        script_lines.append("        # Replace function calls")
        script_lines.append('        content = re.sub(')
        script_lines.append('            r"get_real_time_config\\(config\\)",')
        script_lines.append('            "config.real_time",')
        script_lines.append('            content')
        script_lines.append('        )')
        script_lines.append("")
        script_lines.append("        # Write back")
        script_lines.append("        with open(file_path, 'w', encoding='utf-8') as f:")
        script_lines.append("            f.write(content)")
        script_lines.append("")
        script_lines.append("        print(f\"✅ Migrated {file_path}\")")
        script_lines.append("    except Exception as e:")
        script_lines.append(f"        print(f\"❌ Error migrating {{file_path}}: {{e}}\")")
        script_lines.append("")
        
        script_lines.append("def main():")
        script_lines.append('    """Main migration function."""')
        script_lines.append("    files_to_migrate = [")
        for file_path in files_with_legacy_imports:
            relative_path = file_path.relative_to(self.project_root)
            script_lines.append(f'        Path("{relative_path}"),')
        script_lines.append("    ]")
        script_lines.append("")
        script_lines.append("    print(\"🔄 Starting real-time configuration migration...\")")
        script_lines.append("    for file_path in files_to_migrate:")
        script_lines.append("        migrate_file(file_path)")
        script_lines.append("    print(\"✅ Migration completed!\")")
        script_lines.append("")
        
        script_lines.append('if __name__ == "__main__":')
        script_lines.append("    main()")
        
        return "\n".join(script_lines)
    
    def run_migration_analysis(self) -> None:
        """Run the complete migration analysis."""
        print("🔍 Analyzing real-time configuration usage...")
        
        files_with_legacy_imports = self.find_files_with_legacy_imports()
        
        if not files_with_legacy_imports:
            print("✅ No files found with legacy real_time_config imports!")
            return
        
        print(f"📋 Found {len(files_with_legacy_imports)} files with legacy imports:")
        for file_path in files_with_legacy_imports:
            print(f"  - {file_path.relative_to(self.project_root)}")
        
        # Generate migration guide
        guide = self.generate_migration_guide(files_with_legacy_imports)
        guide_path = self.project_root / "REAL_TIME_CONFIG_MIGRATION_GUIDE.md"
        
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide)
        
        print(f"📖 Migration guide written to: {guide_path}")
        
        # Generate migration script
        script_content = self.create_migration_script(files_with_legacy_imports)
        script_path = self.project_root / "scripts" / "auto_migrate_real_time_config.py"
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        print(f"🔧 Migration script written to: {script_path}")
        print("")
        print("📝 Next steps:")
        print("1. Review the migration guide")
        print("2. Run the migration script: python scripts/auto_migrate_real_time_config.py")
        print("3. Test your application")
        print("4. Remove the legacy real_time_config.py file")


def main():
    """Main function."""
    project_root = Path(__file__).parent.parent
    migrator = RealTimeConfigMigrator(project_root)
    migrator.run_migration_analysis()


if __name__ == "__main__":
    main() 