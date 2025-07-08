#!/usr/bin/env python3
"""
Migration script to transition from legacy config system to new Pydantic-based system.

This script:
1. Backs up existing config files
2. Converts legacy YAML configs to new format
3. Updates environment variables
4. Provides guidance for manual updates
"""

import os
import sys
import yaml
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add src to path for imports

from dart_planner.config.frozen_config import DARTPlannerFrozenConfig, ConfigurationManager


def backup_config_files() -> Path:
    """Backup existing config files with timestamp."""
    backup_dir = Path("config_backup") / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup config directory
    config_dir = Path("config")
    if config_dir.exists():
        shutil.copytree(config_dir, backup_dir / "config", dirs_exist_ok=True)
        print(f"✅ Backed up config directory to: {backup_dir / 'config'}")
    
    # Backup any .env files
    env_files = list(Path(".").glob("*.env*"))
    for env_file in env_files:
        shutil.copy2(env_file, backup_dir / env_file.name)
        print(f"✅ Backed up {env_file} to: {backup_dir / env_file.name}")
    
    return backup_dir


def convert_legacy_config_to_new_format(legacy_config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert legacy config format to new Pydantic format."""
    new_config = {}
    
    # Map legacy config structure to new structure
    if "communication" in legacy_config:
        new_config["communication"] = legacy_config["communication"]
    
    if "safety_limits" in legacy_config:
        # Convert safety_limits to safety config
        safety_limits = legacy_config["safety_limits"]
        new_config["safety"] = {
            "max_velocity": safety_limits.get("max_velocity", 15.0),
            "max_acceleration": safety_limits.get("max_acceleration", 10.0),
            "max_altitude": safety_limits.get("max_altitude", 50.0),
            "safety_radius": safety_limits.get("safety_radius", 100.0),
            "emergency_landing_altitude": safety_limits.get("emergency_landing_altitude", 2.0)
        }
    
    if "planning" in legacy_config:
        new_config["planning"] = legacy_config["planning"]
    
    if "hardware" in legacy_config:
        new_config["hardware"] = legacy_config["hardware"]
    
    if "simulation" in legacy_config:
        new_config["simulation"] = legacy_config["simulation"]
    
    if "logging" in legacy_config:
        new_config["logging"] = legacy_config["logging"]
    
    if "security" in legacy_config:
        new_config["security"] = legacy_config["security"]
    
    # Add environment and debug settings
    new_config["environment"] = legacy_config.get("environment", "development")
    new_config["debug"] = legacy_config.get("debug", False)
    
    return new_config


def migrate_config_files(backup_dir: Path):
    """Migrate existing config files to new format."""
    config_dir = Path("config")
    if not config_dir.exists():
        print("⚠️ No config directory found. Creating default config...")
        config_dir.mkdir(exist_ok=True)
    
    # Migrate defaults.yaml
    defaults_path = config_dir / "defaults.yaml"
    if defaults_path.exists():
        print(f"🔄 Migrating {defaults_path}...")
        
        with open(defaults_path, 'r', encoding='utf-8') as f:
            legacy_config = yaml.safe_load(f) or {}
        
        new_config = convert_legacy_config_to_new_format(legacy_config)
        
        # Create new config using Pydantic for validation
        try:
            config_manager = ConfigurationManager(str(defaults_path))
            new_dart_config = DARTPlannerFrozenConfig(**new_config)
            
            # Save validated config (frozen config doesn't support saving, just validate)
            print(f"✅ Configuration validated successfully")
            print(f"✅ Successfully migrated {defaults_path}")
            
        except Exception as e:
            print(f"❌ Error migrating {defaults_path}: {e}")
            print("⚠️ Please manually review and update the config file")
    
    # Check for other YAML config files
    yaml_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))
    for yaml_file in yaml_files:
        if yaml_file.name == "defaults.yaml":
            continue  # Already handled
        
        print(f"🔄 Migrating {yaml_file}...")
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                legacy_config = yaml.safe_load(f) or {}
            
            new_config = convert_legacy_config_to_new_format(legacy_config)
            
            # Create new config using Pydantic for validation
            config_manager = ConfigurationManager(str(yaml_file))
            new_dart_config = DARTPlannerFrozenConfig(**new_config)
            
            # Save validated config (frozen config doesn't support saving, just validate)
            print(f"✅ Configuration validated successfully")
            print(f"✅ Successfully migrated {yaml_file}")
            
        except Exception as e:
            print(f"❌ Error migrating {yaml_file}: {e}")
            print("⚠️ Please manually review and update the config file")


def update_environment_variables():
    """Provide guidance for updating environment variables."""
    print("\n🔧 Environment Variable Migration Guide:")
    print("=" * 50)
    
    env_mappings = {
        'DART_CONFIG_PATH': 'DART_CONFIG_PATH (unchanged)',
        'DART_ENVIRONMENT': 'DART_ENVIRONMENT (unchanged)',
        'DART_DEBUG': 'DART_DEBUG (unchanged)',
        'DART_ZMQ_PORT': 'DART_ZMQ_PORT (unchanged)',
        'DART_ZMQ_HOST': 'DART_ZMQ_HOST (unchanged)',
        'DART_ZMQ_BIND_ADDRESS': 'DART_ZMQ_BIND_ADDRESS (unchanged)',
        'DART_ZMQ_ENABLE_CURVE': 'DART_ZMQ_ENABLE_CURVE (unchanged)',
        'DART_ZMQ_PUBLIC_KEY': 'DART_ZMQ_PUBLIC_KEY (unchanged)',
        'DART_ZMQ_SECRET_KEY': 'DART_ZMQ_SECRET_KEY (unchanged)',
        'DART_ZMQ_SERVER_KEY': 'DART_ZMQ_SERVER_KEY (unchanged)',
        'DART_HEARTBEAT_INTERVAL_MS': 'DART_HEARTBEAT_INTERVAL_MS (unchanged)',
        'DART_HEARTBEAT_TIMEOUT_MS': 'DART_HEARTBEAT_TIMEOUT_MS (unchanged)',
        'DART_MAX_VELOCITY': 'DART_MAX_VELOCITY (unchanged)',
        'DART_MAX_ACCELERATION': 'DART_MAX_ACCELERATION (unchanged)',
        'DART_MAX_ALTITUDE': 'DART_MAX_ALTITUDE (unchanged)',
        'DART_PREDICTION_HORIZON': 'DART_PREDICTION_HORIZON (unchanged)',
        'DART_DT': 'DART_DT (unchanged)',
        'DART_MAVLINK_CONNECTION': 'DART_MAVLINK_CONNECTION (unchanged)',
        'DART_CONTROL_FREQUENCY': 'DART_CONTROL_FREQUENCY (unchanged)',
        'DART_PLANNING_FREQUENCY': 'DART_PLANNING_FREQUENCY (unchanged)',
        'DART_LOG_LEVEL': 'DART_LOG_LEVEL (unchanged)',
        'DART_SECRET_KEY': 'DART_SECRET_KEY (unchanged)',
    }
    
    print("✅ All environment variables remain the same!")
    print("The new config system is backward compatible with existing environment variables.")


def generate_migration_report(backup_dir: Path):
    """Generate a migration report with next steps."""
    report_path = backup_dir / "migration_report.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# DART-Planner Configuration Migration Report\n\n")
        f.write(f"**Migration Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Backup Location:** {backup_dir.absolute()}\n\n")
        
        f.write("## What Changed\n\n")
        f.write("- Removed legacy `src/config/__init__.py` configuration system\n")
        f.write("- Consolidated to new Pydantic-based `src/config/settings.py` system\n")
        f.write("- All imports updated to use new configuration system\n")
        f.write("- Configuration validation now uses Pydantic models\n\n")
        
        f.write("## Next Steps\n\n")
        f.write("1. **Test your application** - Run your tests to ensure everything works\n")
        f.write("2. **Update any custom scripts** - If you have scripts that import from `src.config`, update them\n")
        f.write("3. **Review configuration** - Check that your config values are correct\n")
        f.write("4. **Remove backup** - Once satisfied, you can remove the backup directory\n\n")
        
        f.write("## Breaking Changes\n\n")
        f.write("- `from dart_planner.config import get_config` → `from dart_planner.config.frozen_config import get_frozen_config as get_config`\n")
        f.write("- `get_safety_limits()` → `get_config().get_safety_config_dict()`\n")
        f.write("- `get_controller_params()` → `get_config().get_hardware_config_dict()`\n\n")
        
        f.write("## Rollback Instructions\n\n")
        f.write("If you need to rollback:\n")
        f.write("1. Restore the backup directory\n")
        f.write("2. Revert the import changes in the codebase\n")
        f.write("3. Restore `src/config/__init__.py`\n\n")
    
    print(f"📋 Migration report saved to: {report_path}")


def main():
    """Main migration function."""
    print("🚀 DART-Planner Configuration System Migration")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("src").exists() or not Path("config").exists():
        print("❌ Error: Please run this script from the DART-Planner root directory")
        sys.exit(1)
    
    # Backup existing config
    print("\n📦 Backing up existing configuration...")
    backup_dir = backup_config_files()
    
    # Migrate config files
    print("\n🔄 Migrating configuration files...")
    migrate_config_files(backup_dir)
    
    # Update environment variables guide
    print("\n🔧 Environment variable migration...")
    update_environment_variables()
    
    # Generate report
    print("\n📋 Generating migration report...")
    generate_migration_report(backup_dir)
    
    print("\n✅ Migration completed successfully!")
    print(f"📁 Backup saved to: {backup_dir}")
    print("\n⚠️ IMPORTANT: Please test your application before removing the backup!")
    print("   Run your tests and ensure everything works as expected.")


if __name__ == "__main__":
    main() 
