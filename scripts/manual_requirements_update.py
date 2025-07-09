#!/usr/bin/env python3
"""
Manual requirements.txt update script for DART-Planner.

This script updates requirements.txt with pinned versions based on requirements.in
when pip-tools is not available or having compatibility issues.
"""

import re
from pathlib import Path


def parse_requirements_in(file_path: str) -> list[str]:
    """Parse requirements.in and extract package names."""
    requirements = []
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '>=' in line:
                # Extract package name from "package>=version"
                package = line.split('>=')[0].strip()
                requirements.append(package)
    
    return requirements


def get_pinned_versions() -> dict[str, str]:
    """Return a dictionary of package names to pinned versions."""
    return {
        # Core dependencies
        "fastapi": "0.110.0",
        "uvicorn[standard]": "0.29.0",
        "pydantic": "2.5.0",
        "sqlalchemy": "2.0.23",
        "alembic": "1.13.1",
        "passlib[bcrypt]": "1.7.4",
        "python-jose[cryptography]": "3.3.0",
        "python-multipart": "0.0.6",
        
        # Scientific computing
        "numpy": "1.24.3",
        "scipy": "1.11.4",
        "matplotlib": "3.8.2",
        "pandas": "2.1.4",
        
        # Communication and networking
        "pyzmq": "25.1.2",
        "websockets": "12.0",
        "python-socketio": "5.10.0",
        
        # Hardware and simulation
        "pymavlink": "2.4.37",
        "airsim": "1.8.1",
        
        # Security and cryptography
        "cryptography": "41.0.8",
        "bcrypt": "4.1.2",
        
        # Monitoring and logging
        "structlog": "23.2.0",
        
        # Development dependencies
        "pytest": "7.4.3",
        "pytest-asyncio": "0.21.1",
        "pytest-cov": "4.1.0",
        "pytest-rerunfailures": "12.0",
        "pytest-benchmark": "4.0.0",
        "pytest-xdist": "3.3.1",
        "black": "23.11.0",
        "isort": "5.12.0",
        "flake8": "6.1.0",
        "mypy": "1.7.1",
        "pre-commit": "3.6.0",
        
        # Documentation
        "sphinx": "7.2.6",
        "sphinx-rtd-theme": "1.3.0",
        
        # CI and security tools
        "pip-audit": "1.0.0",
        "safety": "2.3.5",
        "bandit": "1.7.5",
    }


def update_requirements_txt():
    """Update requirements.txt with pinned versions."""
    requirements_in = parse_requirements_in("requirements.in")
    pinned_versions = get_pinned_versions()
    
    # Create new requirements.txt content
    content = [
        "# DART-Planner Production Dependencies",
        "# Pinned versions for reproducible builds",
        "# Generated from requirements.in",
        "",
        "# Core dependencies"
    ]
    
    # Group packages by category
    categories = {
        "Core dependencies": [
            "fastapi", "uvicorn[standard]", "pydantic", "sqlalchemy", 
            "alembic", "passlib[bcrypt]", "python-jose[cryptography]", 
            "python-multipart"
        ],
        "Scientific computing": ["numpy", "scipy", "matplotlib", "pandas"],
        "Communication and networking": ["pyzmq", "websockets", "python-socketio"],
        "Hardware and simulation": ["pymavlink", "airsim"],
        "Security and cryptography": ["cryptography", "bcrypt"],
        "Monitoring and logging": ["structlog"],
        "Development and testing (optional)": [
            "pytest", "pytest-asyncio", "pytest-cov", "pytest-rerunfailures",
            "pytest-benchmark", "pytest-xdist", "black", "isort", "flake8", "mypy"
        ],
        "Documentation": ["sphinx", "sphinx-rtd-theme"],
        "Monitoring and logging": ["structlog"]
    }
    
    for category, packages in categories.items():
        if any(pkg in requirements_in for pkg in packages):
            content.append(f"\n# {category}")
            for pkg in packages:
                if pkg in requirements_in and pkg in pinned_versions:
                    content.append(f"{pkg}=={pinned_versions[pkg]}")
    
    # Write to requirements.txt
    with open("requirements.txt", "w") as f:
        f.write("\n".join(content))
    
    print("✅ Successfully updated requirements.txt with pinned versions")
    print(f"📦 Updated {len([pkg for pkg in requirements_in if pkg in pinned_versions])} packages")


if __name__ == "__main__":
    update_requirements_txt() 