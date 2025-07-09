# Dependency Management Guide

This document outlines the comprehensive dependency management system implemented for DART-Planner to ensure reproducible builds, security, and maintainability.

## Overview

DART-Planner uses a modern dependency management approach with:
- **pip-tools** for lockfile generation and dependency resolution
- **Multi-stage Docker builds** for secure production deployments
- **Automated dependency updates** with Dependabot
- **Conflict detection** in CI/CD pipeline
- **Separate environments** for development, production, and CI

## Key Improvements Implemented

### 1. Lockfile Management with pip-tools

#### Problem Solved
- **Non-reproducible builds** due to missing lockfile
- **Source of truth drift** between requirements files
- **Manual dependency management** prone to errors

#### Solution
- **requirements.in**: Direct dependencies with version constraints
- **requirements.txt**: Pinned versions (generated automatically)
- **requirements-dev.txt**: Development dependencies (generated)
- **requirements-ci.txt**: CI dependencies (generated)

#### Usage
```bash
# Compile requirements from requirements.in
python scripts/update_dependencies.py compile

# Compile all requirement files
python scripts/update_dependencies.py compile --all

# Validate lockfile is up to date
python scripts/update_dependencies.py validate
```

### 2. Multi-Stage Docker Builds

#### Problem Solved
- **Dev tools in production** increasing attack surface
- **Large production images** with unnecessary dependencies
- **Inconsistent builds** between environments

#### Solution
- **Builder stage**: Compiles dependencies and builds application
- **Production stage**: Contains only runtime dependencies
- **Development stage**: Includes all development tools

#### Docker Images
```bash
# Production image (minimal, secure)
docker build -f demos/Dockerfile -t dart-planner:latest .

# Development image (with all tools)
docker build -f demos/Dockerfile.dev -t dart-planner:dev .
```

### 3. Accelerated Security Patching

#### Problem Solved
- **Slow security updates** with weekly Dependabot schedule
- **Manual security monitoring** required
- **Delayed vulnerability fixes**

#### Solution
- **Daily Dependabot runs** for all ecosystems
- **Automated security scanning** in CI
- **Immediate notification** of security issues

#### Configuration
```yaml
# .github/dependabot.yml
schedule:
  interval: "daily"  # Changed from weekly
  time: "09:00"
  timezone: "UTC"
```

### 4. Dependency Conflict Detection

#### Problem Solved
- **Hidden dependency conflicts** causing runtime issues
- **No automated conflict checking**
- **Manual conflict resolution** required

#### Solution
- **Automated conflict detection** in CI pipeline
- **Lockfile validation** before deployment
- **Conflict resolution tools** and documentation

#### CI Integration
```yaml
# .github/workflows/quality-pipeline.yml
- name: Dependency conflict detection
  run: |
    echo "🔍 Checking for dependency conflicts..."
    pip check
    echo "✅ No dependency conflicts found"

- name: Lockfile validation
  run: |
    echo "🔍 Validating lockfile consistency..."
    python scripts/update_dependencies.py validate
    echo "✅ Lockfile is up to date"
```

## File Structure

```
DART-Planner/
├── requirements.in              # Direct dependencies (source of truth)
├── requirements.txt             # Pinned production dependencies (generated)
├── requirements-dev.txt         # Development dependencies (generated)
├── requirements-ci.txt          # CI dependencies (generated)
├── pyproject.toml              # Project metadata and optional dependencies
├── scripts/
│   └── update_dependencies.py  # Dependency management script
├── demos/
│   ├── Dockerfile              # Production Docker image
│   └── Dockerfile.dev          # Development Docker image
├── .github/
│   ├── dependabot.yml          # Automated dependency updates
│   └── workflows/
│       └── quality-pipeline.yml # CI with dependency checks
└── Makefile                    # Convenient development commands
```

## Dependency Management Workflow

### Adding New Dependencies

1. **Add to requirements.in**:
   ```bash
   echo "new-package>=1.0.0" >> requirements.in
   ```

2. **Compile requirements**:
   ```bash
   make compile
   # or
   python scripts/update_dependencies.py compile
   ```

3. **Install in environment**:
   ```bash
   make sync
   # or
   python scripts/update_dependencies.py sync
   ```

4. **Validate changes**:
   ```bash
   make validate
   make check
   ```

### Updating Dependencies

1. **Check for updates**:
   ```bash
   make outdated
   # or
   python scripts/update_dependencies.py outdated
   ```

2. **Update with latest versions**:
   ```bash
   python scripts/update_dependencies.py compile --upgrade
   ```

3. **Test changes**:
   ```bash
   make test
   make lint
   make security
   ```

### Security Updates

1. **Automatic detection**: Dependabot creates PRs daily
2. **Manual checking**:
   ```bash
   make security
   # or
   pip-audit
   safety check
   bandit -r src/
   ```

3. **Update vulnerable dependencies**:
   ```bash
   # Update specific package
   echo "vulnerable-package>=2.0.0" >> requirements.in
   make compile
   make sync
   ```

## Development Commands

### Using Makefile
```bash
make help              # Show all available commands
make install           # Install production dependencies
make install-dev       # Install development dependencies
make compile           # Compile requirements.txt
make compile-dev       # Compile all requirement files
make sync              # Sync environment with requirements.txt
make validate          # Validate lockfile is up to date
make check             # Check for dependency conflicts
make outdated          # Show outdated dependencies
make test              # Run tests
make test-cov          # Run tests with coverage
make lint              # Run linting checks
make format            # Format code
make security          # Run security checks
make docker-build      # Build production Docker image
make docker-dev        # Build development Docker image
make clean             # Clean build artifacts
```

### Using Script Directly
```bash
python scripts/update_dependencies.py compile      # Compile requirements.txt
python scripts/update_dependencies.py compile --upgrade  # Update to latest versions
python scripts/update_dependencies.py compile --dev      # Include dev dependencies
python scripts/update_dependencies.py compile --all      # Compile all files
python scripts/update_dependencies.py validate     # Validate lockfile
python scripts/update_dependencies.py sync         # Sync environment
python scripts/update_dependencies.py check        # Check conflicts
python scripts/update_dependencies.py outdated     # Show outdated
```

## Best Practices

### 1. Always Use requirements.in
- **Never edit requirements.txt directly** - it's generated
- **Add dependencies to requirements.in** with appropriate version constraints
- **Use semantic versioning** for version constraints

### 2. Regular Maintenance
- **Run `make validate`** before committing to ensure lockfile is current
- **Check for conflicts** with `make check` regularly
- **Monitor outdated dependencies** with `make outdated`

### 3. Security
- **Review Dependabot PRs** promptly, especially security updates
- **Run security scans** regularly with `make security`
- **Update vulnerable dependencies** immediately

### 4. CI/CD Integration
- **Dependency checks** run automatically in CI
- **Lockfile validation** prevents deployment with outdated dependencies
- **Conflict detection** catches issues before they reach production

### 5. Docker Best Practices
- **Use multi-stage builds** to minimize production image size
- **Separate development and production** Dockerfiles
- **Pin base images** for reproducible builds

## Troubleshooting

### Common Issues

#### Lockfile Out of Date
```bash
# Error: requirements.txt is outdated
make validate
# Solution: Run make compile
```

#### Dependency Conflicts
```bash
# Error: Dependency conflicts found
make check
# Solution: Resolve conflicts manually or update requirements.in
```

#### Installation Issues
```bash
# Error: Package not found
# Solution: Check requirements.in and run make compile
```

#### Docker Build Failures
```bash
# Error: Build stage fails
# Solution: Check requirements.in and ensure all dependencies are listed
```

### Debugging Commands
```bash
# Check what's installed
pip list

# Check dependency tree
pip show <package-name>

# Check for conflicts
pip check

# Validate lockfile
python scripts/update_dependencies.py validate

# Show dependency resolution
pip-compile --dry-run requirements.in
```

## Migration Guide

### From Manual requirements.txt Management

1. **Backup current requirements.txt**:
   ```bash
   cp requirements.txt requirements.txt.backup
   ```

2. **Create requirements.in** from current dependencies:
   ```bash
   # Extract direct dependencies (manual process)
   # Add to requirements.in with version constraints
   ```

3. **Generate new requirements.txt**:
   ```bash
   make compile
   ```

4. **Validate consistency**:
   ```bash
   make validate
   make check
   ```

5. **Update CI/CD** to use new workflow

### From Poetry or Pipenv

1. **Export dependencies** from existing lockfile
2. **Create requirements.in** with exported dependencies
3. **Generate requirements.txt** with pip-tools
4. **Update Dockerfiles** to use new approach
5. **Update CI/CD** configuration

## Future Enhancements

### Planned Improvements
1. **Automated dependency updates** with semantic versioning
2. **Dependency vulnerability scanning** in CI
3. **Dependency usage analysis** to identify unused packages
4. **Automated conflict resolution** suggestions
5. **Dependency update notifications** via Slack/email

### Monitoring and Metrics
1. **Dependency update frequency** tracking
2. **Security vulnerability response time** monitoring
3. **Build reproducibility** validation
4. **Dependency conflict frequency** tracking

## Conclusion

The implemented dependency management system provides:
- **Reproducible builds** through lockfiles
- **Secure deployments** with minimal attack surface
- **Automated updates** for security patches
- **Conflict detection** to prevent runtime issues
- **Clear workflows** for dependency management

This ensures DART-Planner maintains high security, reliability, and maintainability standards as the project evolves. 