# Configuration Guide

This document provides a comprehensive reference for all configuration options in DART-Planner, including environment variables, CLI flags, and configuration files.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [CLI Commands](#cli-commands)
- [Configuration Hierarchy](#configuration-hierarchy)
- [Security Configuration](#security-configuration)
- [Development vs Production](#development-vs-production)

## Environment Variables

### Security Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DART_SECRET_KEY` | Secret key for JWT token signing | None | Yes |
| `DART_ZMQ_SECRET` | Secret key for ZMQ communication | None | No |

### Database Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DART_DB_URL` | Database connection URL | `sqlite:///~/.dart_planner/auth.db` | No |

### Application Mode

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DART_PLANNER_MODE` | Application mode (development/production) | `development` | No |
| `PYTHONUNBUFFERED` | Disable Python output buffering | `1` | No |

### Example Environment Setup

```bash
# Copy the example environment file
cp env.example .env

# Generate a secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Edit .env with your values
DART_SECRET_KEY="your_generated_secret_key_here"
DART_DB_URL="sqlite:///~/.dart_planner/auth.db"
DART_PLANNER_MODE="development"
```

## Configuration Files

DART-Planner uses YAML configuration files located in the `config/` directory.

### File Structure

```
config/
├── defaults.yaml      # Default configuration values
├── hardware.yaml      # Hardware-specific parameters
└── airframes.yaml     # Airframe-specific configurations
```

### Configuration Sections

#### Communication Settings

```yaml
communication:
  enable_heartbeat: true
  heartbeat:
    interval_ms: 100
    mavlink_timeout_s: 5.0
    timeout_ms: 500
  zmq_bind_address: 127.0.0.1
  zmq_enable_curve: false
  zmq_host: localhost
  zmq_port: 5555
  zmq_public_key: null
  zmq_secret_key: null
  zmq_server_key: null
```

| Setting | Description | Default | Units |
|---------|-------------|---------|-------|
| `enable_heartbeat` | Enable heartbeat monitoring | `true` | Boolean |
| `interval_ms` | Heartbeat interval | `100` | milliseconds |
| `mavlink_timeout_s` | MAVLink timeout | `5.0` | seconds |
| `timeout_ms` | General timeout | `500` | milliseconds |
| `zmq_bind_address` | ZMQ bind address | `127.0.0.1` | IP address |
| `zmq_enable_curve` | Enable ZMQ curve encryption | `false` | Boolean |
| `zmq_host` | ZMQ host | `localhost` | Hostname |
| `zmq_port` | ZMQ port | `5555` | Port number |

#### Hardware Configuration

```yaml
hardware:
  baud_rate: 921600
  control_frequency: 400.0
  mavlink_connection: /dev/ttyUSB0
  planning_frequency: 50.0
  telemetry_frequency: 10.0
```

| Setting | Description | Default | Units |
|---------|-------------|---------|-------|
| `baud_rate` | Serial communication baud rate | `921600` | baud |
| `control_frequency` | Control loop frequency | `400.0` | Hz |
| `mavlink_connection` | MAVLink device path | `/dev/ttyUSB0` | Path |
| `planning_frequency` | Planning loop frequency | `50.0` | Hz |
| `telemetry_frequency` | Telemetry frequency | `10.0` | Hz |

#### Planning Parameters

```yaml
planning:
  convergence_tolerance: 0.05
  dt: 0.1
  max_iterations: 15
  obstacle_weight: 1000.0
  position_weight: 100.0
  prediction_horizon: 8
  safety_margin: 1.5
  velocity_weight: 10.0
```

| Setting | Description | Default | Units |
|---------|-------------|---------|-------|
| `convergence_tolerance` | Optimization convergence tolerance | `0.05` | meters |
| `dt` | Time step for planning | `0.1` | seconds |
| `max_iterations` | Maximum optimization iterations | `15` | count |
| `obstacle_weight` | Obstacle avoidance weight | `1000.0` | dimensionless |
| `position_weight` | Position tracking weight | `100.0` | dimensionless |
| `prediction_horizon` | Planning horizon length | `8` | steps |
| `safety_margin` | Safety margin around obstacles | `1.5` | meters |
| `velocity_weight` | Velocity tracking weight | `10.0` | dimensionless |

#### Safety Limits

```yaml
safety:
  emergency_landing_altitude: 2.0
  max_acceleration: 10.0
  max_altitude: 50.0
  max_velocity: 15.0
  safety_radius: 100.0
```

| Setting | Description | Default | Units |
|---------|-------------|---------|-------|
| `emergency_landing_altitude` | Emergency landing altitude | `2.0` | meters |
| `max_acceleration` | Maximum acceleration | `10.0` | m/s² |
| `max_altitude` | Maximum flight altitude | `50.0` | meters |
| `max_velocity` | Maximum velocity | `15.0` | m/s |
| `safety_radius` | Safety radius | `100.0` | meters |

#### Security Settings

```yaml
security:
  enable_authentication: true
  enable_ssl: false
  secret_key: ''
  ssl_cert_file: null
  ssl_key_file: null
  token_expiry_hours: 24
```

| Setting | Description | Default | Units |
|---------|-------------|---------|-------|
| `enable_authentication` | Enable authentication | `true` | Boolean |
| `enable_ssl` | Enable SSL/TLS | `false` | Boolean |
| `secret_key` | Secret key for tokens | `''` | String |
| `ssl_cert_file` | SSL certificate file | `null` | Path |
| `ssl_key_file` | SSL private key file | `null` | Path |
| `token_expiry_hours` | Token expiry time | `24` | hours |

#### Simulation Settings

```yaml
simulation:
  airsim_host: localhost
  airsim_port: 41451
  enable_visualization: true
  simulation_speed: 1.0
  use_airsim: true
```

| Setting | Description | Default | Units |
|---------|-------------|---------|-------|
| `airsim_host` | AirSim host address | `localhost` | Hostname |
| `airsim_port` | AirSim port | `41451` | Port number |
| `enable_visualization` | Enable visualization | `true` | Boolean |
| `simulation_speed` | Simulation speed multiplier | `1.0` | dimensionless |
| `use_airsim` | Use AirSim for simulation | `true` | Boolean |

#### Logging Configuration

```yaml
logging:
  enable_console: true
  enable_file: false
  file: null
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  level: INFO
```

| Setting | Description | Default | Units |
|---------|-------------|---------|-------|
| `enable_console` | Enable console logging | `true` | Boolean |
| `enable_file` | Enable file logging | `false` | Boolean |
| `file` | Log file path | `null` | Path |
| `format` | Log message format | `'%(asctime)s - %(name)s - %(levelname)s - %(message)s'` | String |
| `level` | Logging level | `INFO` | Level |

#### Coordinate Frame Settings

```yaml
coordinate_frame:
  world_frame: ENU
  enforce_consistency: true
  validate_transforms: true
  auto_detect_frame: false
```

| Setting | Description | Default | Units |
|---------|-------------|---------|-------|
| `world_frame` | World coordinate frame | `ENU` | Frame type |
| `enforce_consistency` | Enforce coordinate consistency | `true` | Boolean |
| `validate_transforms` | Validate coordinate transforms | `true` | Boolean |
| `auto_detect_frame` | Auto-detect coordinate frame | `false` | Boolean |

### Hardware-Specific Configuration

The `hardware.yaml` file contains physical parameters for your specific drone:

```yaml
# Distance from center of mass to each motor (meters)
arm_length: 0.225  # [m] Example: 0.225 for 450mm quadcopter

# Maximum thrust each motor can produce at full throttle (Newtons)
max_motor_thrust: 12.0  # [N] Example: 12.0N per motor

# Maximum drag torque each propeller can produce (for yaw axis, Nm)
max_propeller_drag_torque: 0.18  # [Nm] Example: 0.18Nm per prop

# Number of arms/motors (e.g., 4 for quad, 6 for hex)
num_arms: 4

# Geometry type (e.g., 'x', 'plus', 'coaxial', etc.)
geometry: 'x'

# Transport-delay compensation settings
transport_delay:
  delay_ms: 25.0  # [ms] Transport delay to compensate for
  control_loop_period_ms: 5.0  # [ms] = 200Hz control loop
  enabled: true
  max_buffer_size: 1000
```

## CLI Commands

### Main CLI Interface

```bash
# Run the planner stack
python -m src.dart_planner_cli run --mode=cloud   # Launch cloud node
python -m src.dart_planner_cli run --mode=edge    # Launch edge node

# Available modes
--mode=cloud    # Cloud-based planning node
--mode=edge     # Edge-based planning node
--mode=local    # Local development mode
```

### Configuration Commands

```bash
# Validate configuration
python -m src.dart_planner_cli config validate

# Show current configuration
python -m src.dart_planner_cli config show

# Generate configuration template
python -m src.dart_planner_cli config generate
```

### Development Commands

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov=dart_planner

# Format code
black src/ tests/ scripts/

# Lint code
flake8 src/ tests/ scripts/

# Type checking
mypy src/ tests/ scripts/
```

## Configuration Hierarchy

DART-Planner uses a hierarchical configuration system with the following precedence (highest to lowest):

1. **Environment Variables** - Override all other settings
2. **Command Line Arguments** - Override file-based configuration
3. **User Configuration Files** - Override defaults
4. **Default Configuration Files** - Base configuration

### Configuration Loading Order

1. Load `config/defaults.yaml`
2. Load `config/hardware.yaml`
3. Load `config/airframes.yaml`
4. Apply environment variable overrides
5. Apply command line argument overrides

## Security Configuration

### Production Security Checklist

- [ ] Set `DART_SECRET_KEY` to a secure random value
- [ ] Enable SSL/TLS with valid certificates
- [ ] Configure proper database authentication
- [ ] Set appropriate file permissions
- [ ] Enable authentication (`security.enable_authentication: true`)
- [ ] Configure token expiry times
- [ ] Use secure ZMQ keys if enabled

### Key Generation

```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Generate ZMQ keys (if using curve encryption)
python -c "import zmq; print(zmq.curve_keypair())"
```

## Development vs Production

### Development Configuration

```yaml
environment: development
debug: true
logging:
  level: DEBUG
  enable_console: true
security:
  enable_authentication: false  # Disable for development
simulation:
  use_airsim: true
  enable_visualization: true
```

### Production Configuration

```yaml
environment: production
debug: false
logging:
  level: INFO
  enable_file: true
  file: /var/log/dart_planner/app.log
security:
  enable_authentication: true
  enable_ssl: true
  token_expiry_hours: 1  # Shorter expiry for security
simulation:
  use_airsim: false
  enable_visualization: false
```

### Environment-Specific Overrides

You can create environment-specific configuration files:

- `config/development.yaml` - Development overrides
- `config/production.yaml` - Production overrides
- `config/testing.yaml` - Testing overrides

These files will be loaded based on the `DART_PLANNER_MODE` environment variable.

## Troubleshooting

### Common Configuration Issues

1. **Permission Denied**: Check file permissions on configuration files
2. **Invalid YAML**: Use a YAML validator to check syntax
3. **Missing Environment Variables**: Ensure all required variables are set
4. **Port Conflicts**: Check if ports are already in use
5. **Database Connection**: Verify database URL and credentials

### Configuration Validation

```bash
# Validate configuration files
python -m src.dart_planner_cli config validate

# Check environment variables
python -c "import os; print([k for k in os.environ if k.startswith('DART_')])"

# Test configuration loading
python -c "from src.dart_planner.config.frozen_config import FrozenConfig; print(FrozenConfig())"
```

## Best Practices

1. **Never commit secrets** to version control
2. **Use environment variables** for sensitive configuration
3. **Validate configuration** before deployment
4. **Document custom configurations** for your specific setup
5. **Use configuration templates** for consistent deployments
6. **Test configuration changes** in development first
7. **Backup configuration** before making changes
8. **Use version control** for configuration templates (not secrets) 