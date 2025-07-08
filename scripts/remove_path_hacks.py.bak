#!/usr/bin/env python3
"""
Script to remove manual path hacks and implement proper dependency injection.

This script:
2. Replaces manual instantiation with dependency injection
3. Updates imports to use proper module paths
4. Adds dependency injection container usage
"""

import os
from dart_planner.common.di_container import get_container
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any


def find_files_with_path_hacks() -> List[Path]:
    python_files = []
    
    # Directories to scan
    scan_dirs = [
        project_root / "src",
        project_root / "tests", 
        project_root / "scripts",
        project_root / "examples",
        project_root / "demos",
        project_root / "migrations",
        project_root / "docs"
    ]
    
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
            
        for root, dirs, files in os.walk(scan_dir):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'venv', 'build', 'dist', '.pytest_cache']]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Check for path hacks or manual instantiation patterns
                            if any(pattern in content for pattern in [
                                'new get_container().create_planner_container().get_se3_planner()',
                                'new get_container().create_control_container().get_geometric_controller()',
                                'new get_container().create_hardware_container().get_airsim_adapter()',
                                'get_container().create_communication_container().get_zmq_server()',
                                'get_container().create_communication_container().get_zmq_client()',
                                'get_container().create_control_container().get_geometric_controller()',
                                'get_container().create_planner_container().get_se3_planner()'
                            ]):
                                python_files.append(file_path)
                    except Exception as e:
                        print(f"Warning: Could not read {file_path}: {e}")
    
    return python_files


def analyze_file_content(file_path: Path) -> Dict[str, Any]:
    """Analyze file content to identify patterns that need fixing."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            'path_hacks': [],
            'manual_instantiations': [],
            'imports_to_add': set(),
            'di_usage_needed': False
        }
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Check for path hacks
                analysis['path_hacks'].append((line_num, line.strip()))
            
            # Check for manual instantiations
            if any(pattern in line for pattern in [
                'get_container().create_planner_container().get_se3_planner()',
                'get_container().create_control_container().get_geometric_controller()',
                'get_container().create_hardware_container().get_airsim_adapter()',
                'get_container().create_communication_container().get_zmq_server()',
                'get_container().create_communication_container().get_zmq_client()',
                'get_container().create_control_container().get_trajectory_smoother()'
            ]):
                analysis['manual_instantiations'].append((line_num, line.strip()))
                analysis['di_usage_needed'] = True
        
        # Determine what imports are needed
        if analysis['di_usage_needed']:
            analysis['imports_to_add'].add('from dart_planner.common.di_container import get_container')
        
        return analysis
        
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return {'path_hacks': [], 'manual_instantiations': [], 'imports_to_add': set(), 'di_usage_needed': False}


def fix_file_with_di(file_path: Path) -> bool:
    """Fix a file by removing path hacks and adding dependency injection."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.split('\n')
        
        # Step 1: Remove path hacks
        new_lines = []
        for line in lines:
            if not any(pattern in line for pattern in [
            ]):
                new_lines.append(line)
        
        # Step 2: Add DI imports if needed
        di_imports_added = False
        for i, line in enumerate(new_lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                # Check if we need to add DI imports
                if not di_imports_added and any(pattern in content for pattern in [
                    'get_container().create_planner_container().get_se3_planner()',
                    'get_container().create_control_container().get_geometric_controller()',
                    'get_container().create_hardware_container().get_airsim_adapter()',
                    'get_container().create_communication_container().get_zmq_server()',
                    'get_container().create_communication_container().get_zmq_client()'
                ]):
                    new_lines.insert(i + 1, 'from dart_planner.common.di_container import get_container')
                    di_imports_added = True
                break
        
        # Step 3: Replace manual instantiations with DI
        for i, line in enumerate(new_lines):
            # Replace SE3MPCPlanner instantiation
            if 'get_container().create_planner_container().get_se3_planner()' in line:
                new_lines[i] = line.replace(
                    'get_container().create_planner_container().get_se3_planner()',
                    'get_container().create_planner_container().get_se3_planner()'
                )
            
            # Replace GeometricController instantiation
            elif 'get_container().create_control_container().get_geometric_controller()' in line:
                new_lines[i] = line.replace(
                    'get_container().create_control_container().get_geometric_controller()',
                    'get_container().create_control_container().get_geometric_controller()'
                )
            
            # Replace AirSimAdapter instantiation
            elif 'get_container().create_hardware_container().get_airsim_adapter()' in line:
                new_lines[i] = line.replace(
                    'get_container().create_hardware_container().get_airsim_adapter()',
                    'get_container().create_hardware_container().get_airsim_adapter()'
                )
            
            # Replace ZmqServer instantiation
            elif 'get_container().create_communication_container().get_zmq_server()' in line:
                new_lines[i] = line.replace(
                    'get_container().create_communication_container().get_zmq_server()',
                    'get_container().create_communication_container().get_zmq_server()'
                )
            
            # Replace ZmqClient instantiation
            elif 'get_container().create_communication_container().get_zmq_client()' in line:
                new_lines[i] = line.replace(
                    'get_container().create_communication_container().get_zmq_client()',
                    'get_container().create_communication_container().get_zmq_client()'
                )
            
            # Replace TrajectorySmoother instantiation
            elif 'get_container().create_control_container().get_trajectory_smoother()' in line:
                new_lines[i] = line.replace(
                    'get_container().create_control_container().get_trajectory_smoother()',
                    'get_container().create_control_container().get_trajectory_smoother()'
                )
        
        # Step 4: Update imports to use proper paths
        for i, line in enumerate(new_lines):
            # Fix relative imports that might be broken
            if line.strip().startswith('from .') and 'src.' not in line:
                # Convert relative imports to absolute imports
                if file_path.parts[-2] == 'src':  # File is directly in src submodule
                    module_name = file_path.parts[-1].replace('.py', '')
                    new_lines[i] = line.replace('from .', f'from dart_planner.{module_name}.')
                elif len(file_path.parts) > 2 and file_path.parts[-3] == 'src':
                    # File is in src/submodule/
                    submodule = file_path.parts[-2]
                    new_lines[i] = line.replace('from .', f'from dart_planner.{submodule}.')
        
        new_content = '\n'.join(new_lines)
        
        # Only write if content changed
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def create_di_bootstrap_script() -> None:
    """Create a bootstrap script to initialize the DI container."""
    bootstrap_content = '''#!/usr/bin/env python3
"""
Dependency Injection Bootstrap Script

This script initializes the global dependency injection container
and registers all system dependencies.
"""

import sys
from pathlib import Path

# Add src to path for imports

from dart_planner.common.di_container import DIContainer, ContainerConfig, set_container
from dart_planner.config.settings import ConfigManager
from dart_planner.config.airframe_config import AirframeConfigManager

def bootstrap_di_container():
    """Initialize the global dependency injection container."""
    
    # Create container configuration
    config = ContainerConfig(
        environment="development",
        log_level="INFO",
        enable_metrics=True,
        enable_safety=True
    )
    
    # Create and configure container
    container = DIContainer(config)
    
    # Register core dependencies
    container.register_singleton(ConfigManager, ConfigManager)
    container.register_singleton(AirframeConfigManager, AirframeConfigManager)
    
    # Set as global container
    set_container(container)
    
    print("✅ Dependency injection container initialized")
    return container

if __name__ == "__main__":
    bootstrap_di_container()
'''
    
    with open(bootstrap_path, 'w', encoding='utf-8') as f:
        f.write(bootstrap_content)
    
    print(f"✅ Created DI bootstrap script: {bootstrap_path}")


def create_migration_guide() -> None:
    """Create a migration guide for developers."""
    guide_content = '''# Dependency Injection Migration Guide

## Overview

This guide explains how to migrate from manual path hacks and direct instantiation
to proper dependency injection in DART-Planner.

## What Changed

### Before (Manual Path Hacks)
```python
import sys
import os

from planning.se3_mpc_planner import SE3MPCPlanner
from control.geometric_controller import GeometricController

# Manual instantiation
planner = get_container().create_planner_container().get_se3_planner()config)
controller = get_container().create_control_container().get_geometric_controller()config)
```

### After (Dependency Injection)
```python
from dart_planner.common.di_container import get_container

# Get dependencies from container
planner = get_container().create_planner_container().get_se3_planner()
controller = get_container().create_control_container().get_geometric_controller()
```

## Migration Steps

2. **Add DI imports**: Add `from dart_planner.common.di_container import get_container`
3. **Replace instantiations**: Use container methods instead of direct instantiation
4. **Update imports**: Use proper module paths (e.g., `from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner`)

## Available Container Methods

### Planner Container
- `get_se3_planner()` - Get SE3 MPC planner
- `get_cloud_planner()` - Get cloud planner
- `get_mission_planner()` - Get mission planner

### Control Container
- `get_geometric_controller()` - Get geometric controller
- `get_onboard_controller()` - Get onboard controller
- `get_trajectory_smoother()` - Get trajectory smoother

### Hardware Container
- `get_airsim_adapter()` - Get AirSim adapter
- `get_pixhawk_interface()` - Get Pixhawk interface
- `get_vehicle_io_factory()` - Get vehicle I/O factory

### Communication Container
- `get_zmq_server()` - Get ZMQ server
- `get_zmq_client()` - Get ZMQ client
- `get_heartbeat_manager()` - Get heartbeat manager

## Benefits

1. **No more path hacks**: Clean, standard Python imports
2. **Dependency management**: Centralized dependency resolution
3. **Testability**: Easy to mock dependencies for testing
4. **Configuration**: Centralized configuration management
5. **Lifecycle management**: Proper initialization and cleanup

## Testing

After migration, run the test suite to ensure everything works:

```bash
python -m pytest tests/
```

## Troubleshooting

### Import Errors
- Ensure you're using proper module paths (e.g., `from dart_planner.module import Class`)
- Check that the DI container is properly initialized

### Missing Dependencies
- Register new dependencies in the appropriate container class
- Use `container.register_singleton()` for singleton dependencies

### Configuration Issues
- Use `get_container().resolve(ConfigManager)` to access configuration
- Check that configuration files are in the correct location
'''
    
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print(f"✅ Created migration guide: {guide_path}")


def main():
    """Main function to remove path hacks and implement DI."""
    print("🔧 Removing manual path hacks and implementing dependency injection...")
    
    # Find files that need fixing
    files = find_files_with_path_hacks()
    
    if not files:
        print("✅ No files found with path hacks or manual instantiation")
        return
    
    print(f"Found {len(files)} files that need fixing:")
    for file in files:
        print(f"  - {file}")
    
    # Analyze each file
    total_fixed = 0
    for file_path in files:
        print(f"\nAnalyzing {file_path}...")
        
        analysis = analyze_file_content(file_path)
        
        if analysis['path_hacks']:
            print(f"  Found {len(analysis['path_hacks'])} path hacks")
        
        if analysis['manual_instantiations']:
            print(f"  Found {len(analysis['manual_instantiations'])} manual instantiations")
        
        if analysis['di_usage_needed']:
            print(f"  Needs DI container usage")
        
        # Fix the file
        if fix_file_with_di(file_path):
            print(f"  ✅ Fixed {file_path}")
            total_fixed += 1
        else:
            print(f"  ⚠️  No changes needed for {file_path}")
    
    # Create supporting files
    create_di_bootstrap_script()
    create_migration_guide()
    
    print(f"\n🎉 Migration complete!")
    print(f"Fixed {total_fixed} out of {len(files)} files")
    print("\n📝 Next steps:")
    print("1. Run the bootstrap script: python scripts/bootstrap_di.py")
    print("2. Test the system: python -m pytest tests/")
    print("3. Review the migration guide: docs/DI_MIGRATION_GUIDE.md")
    print("4. Update any remaining manual instantiations")


if __name__ == "__main__":
    main() 
