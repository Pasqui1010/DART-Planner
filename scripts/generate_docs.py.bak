#!/usr/bin/env python3
"""
Documentation Generator for DART-Planner SITL Framework

This script generates comprehensive API documentation for the SITL test framework,
including module docs, test scenarios, and usage examples.
"""

import os
from dart_planner.common.di_container import get_container
import sys
import inspect
import importlib
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Add src to path for imports


@dataclass
class DocSection:
    """Documentation section"""
    title: str
    content: str
    subsections: List['DocSection'] = field(default_factory=list)
    
    def to_markdown(self, level: int = 1) -> str:
        """Convert to markdown format"""
        header = "#" * level
        md = f"{header} {self.title}\n\n{self.content}\n\n"
        
        for subsection in self.subsections:
            md += subsection.to_markdown(level + 1)
        
        return md


class DocumentationGenerator:
    """Generate comprehensive documentation for DART-Planner SITL framework"""
    
    def __init__(self, output_dir: str = "docs/sitl"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Documentation sections
        self.sections: List[DocSection] = []
        
    def generate_all_docs(self):
        """Generate all documentation files"""
        print("🔧 Generating DART-Planner SITL Documentation...")
        
        # Generate main sections
        self._generate_overview()
        self._generate_api_reference()
        self._generate_test_scenarios_doc()
        self._generate_usage_examples()
        self._generate_troubleshooting_guide()
        
        # Write main documentation file
        self._write_main_documentation()
        
        # Generate additional files
        self._generate_test_configuration_guide()
        self._generate_performance_analysis_guide()
        
        print(f"✅ Documentation generated in {self.output_dir}")
        
    def _generate_overview(self):
        """Generate framework overview section"""
        content = """
The DART-Planner SITL (Software-in-the-Loop) Test Framework provides comprehensive
testing capabilities for autonomous drone navigation systems. It validates the
system's performance, robustness, and safety through simulated environments.

## Key Features

- **Comprehensive Test Scenarios**: From basic waypoint following to extreme stress tests
- **Performance Benchmarking**: Automated measurement against breakthrough targets
- **Failure Mode Testing**: Sensor failures, wind disturbance, communication issues
- **AirSim Integration**: Full integration with Microsoft AirSim for realistic simulation
- **Configurable Test Profiles**: Multiple test configurations for different validation needs
- **Detailed Reporting**: Performance metrics, visualization, and analysis tools

## Architecture

The framework consists of three main components:

1. **Test Engine** (`DARTSITLTester`): Core testing logic and scenario execution
2. **AirSim Interface**: Hardware abstraction layer for simulation integration  
3. **Analysis Tools**: Performance measurement, visualization, and reporting

## Testing Philosophy

The framework follows a tiered testing approach:

- **Smoke Tests**: Basic functionality verification (< 5 minutes)
- **Performance Tests**: Benchmark against breakthrough targets (10-15 minutes)
- **Comprehensive Tests**: Full scenario coverage including failures (30-45 minutes)
- **Hardware Ready**: Final validation for real-world deployment (60+ minutes)
        """
        
        self.sections.append(DocSection("Framework Overview", content))
        
    def _generate_api_reference(self):
        """Generate API reference documentation"""
        api_content = "Complete API reference for all SITL framework components.\n\n"
        
        # Import and document main classes
        try:
            from test_dart_sitl_comprehensive import DARTSITLTester
            api_content += self._document_class(DARTSITLTester)
            
            # Import control configuration
            from dart_planner.control.control_config import ControllerTuningManager, ControllerTuningProfile
            api_content += self._document_class(ControllerTuningManager)
            api_content += self._document_class(ControllerTuningProfile)
            
            # Import geometric controller
            from dart_planner.control.geometric_controller import GeometricController
            api_content += self._document_class(GeometricController)
            
        except ImportError as e:
            api_content += f"⚠️ Could not import modules for API documentation: {e}\n\n"
            
        self.sections.append(DocSection("API Reference", api_content))
        
    def _document_class(self, cls) -> str:
        """Document a Python class"""
        doc = f"## {cls.__name__}\n\n"
        
        # Class docstring
        if cls.__doc__:
            doc += f"{cls.__doc__.strip()}\n\n"
        
        # Constructor
        init_method = getattr(cls, '__init__', None)
        if init_method:
            sig = inspect.signature(init_method)
            doc += f"### Constructor\n\n```python\n{cls.__name__}{sig}\n```\n\n"
            
            if init_method.__doc__:
                doc += f"{init_method.__doc__.strip()}\n\n"
        
        # Public methods
        methods = []
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_'):  # Only public methods
                methods.append((name, method))
        
        if methods:
            doc += "### Methods\n\n"
            for name, method in methods:
                sig = inspect.signature(method)
                doc += f"#### `{name}{sig}`\n\n"
                
                if method.__doc__:
                    doc += f"{method.__doc__.strip()}\n\n"
                else:
                    doc += "No documentation available.\n\n"
        
        return doc
        
    def _generate_test_scenarios_doc(self):
        """Generate test scenarios documentation"""
        content = "Comprehensive documentation of all available test scenarios.\n\n"
        
        # Load test scenarios
        try:
            with open(scenarios_file, 'r') as f:
                scenarios = json.load(f)
            
            # Group scenarios by complexity
            basic_scenarios = []
            advanced_scenarios = []
            stress_scenarios = []
            
            for name, scenario in scenarios.items():
                expected_rate = scenario.get('expected_success_rate', 100)
                if expected_rate >= 90:
                    basic_scenarios.append((name, scenario))
                elif expected_rate >= 60:
                    advanced_scenarios.append((name, scenario))
                else:
                    stress_scenarios.append((name, scenario))
            
            # Document each group
            content += self._document_scenario_group("Basic Scenarios", basic_scenarios)
            content += self._document_scenario_group("Advanced Scenarios", advanced_scenarios)  
            content += self._document_scenario_group("Stress Test Scenarios", stress_scenarios)
            
        except FileNotFoundError:
            content += "⚠️ Test scenarios file not found\n\n"
        except json.JSONDecodeError as e:
            content += f"⚠️ Error parsing test scenarios: {e}\n\n"
            
        self.sections.append(DocSection("Test Scenarios", content))
        
    def _document_scenario_group(self, group_name: str, scenarios: List[tuple]) -> str:
        """Document a group of test scenarios"""
        doc = f"## {group_name}\n\n"
        
        for name, scenario in scenarios:
            doc += f"### {name.replace('_', ' ').title()}\n\n"
            doc += f"**Description**: {scenario.get('description', 'No description')}\n\n"
            
            # Waypoints
            if 'waypoints' in scenario:
                doc += f"**Waypoints**: {len(scenario['waypoints'])} points\n\n"
                
            # Key parameters
            params = []
            if 'max_velocity' in scenario:
                params.append(f"Max velocity: {scenario['max_velocity']} m/s")
            if 'success_radius' in scenario:
                params.append(f"Success radius: {scenario['success_radius']} m")
            if 'timeout' in scenario:
                params.append(f"Timeout: {scenario['timeout']} s")
            if 'expected_success_rate' in scenario:
                params.append(f"Expected success: {scenario['expected_success_rate']}%")
                
            if params:
                doc += f"**Parameters**: {', '.join(params)}\n\n"
            
            # Special features
            features = []
            if scenario.get('wind_enabled', False):
                wind_config = scenario.get('wind_config', {})
                features.append(f"Wind: {wind_config.get('type', 'enabled')}")
                
            if scenario.get('sensor_failures'):
                features.append(f"Sensor failures: {len(scenario['sensor_failures'])}")
                
            if scenario.get('obstacles'):
                features.append(f"Obstacles: {len(scenario['obstacles'])}")
                
            if features:
                doc += f"**Special Features**: {', '.join(features)}\n\n"
            
            doc += "---\n\n"
        
        return doc
        
    def _generate_usage_examples(self):
        """Generate usage examples documentation"""
        content = """
Practical examples for using the DART-Planner SITL framework.

## Quick Start Example

```python
from tests.test_dart_sitl_comprehensive import DARTSITLTester
import asyncio

async def basic_test():
    # Initialize tester
    tester = DARTSITLTester()
    
    # Run smoke test
    results = await tester.run_smoke_test()
    
    # Print results
    print(f"Test Results: {results}")
    
    await tester.cleanup()

# Run the test
asyncio.run(basic_test())
```

## Custom Test Scenario

```python
from tests.test_dart_sitl_comprehensive import DARTSITLTester
import numpy as np

async def custom_mission():
    tester = DARTSITLTester()
    
    # Define custom waypoints
    waypoints = [
        np.array([0, 0, -2]),
        np.array([10, 0, -2]),
        np.array([10, 10, -2]),
        np.array([0, 10, -2]),
        np.array([0, 0, -2])
    ]
    
    # Execute mission
    success = await tester.execute_mission(waypoints, timeout=120.0)
    
    # Get performance metrics
    metrics = tester.get_performance_metrics()
    print(f"Mission success: {success}")
    print(f"Average tracking error: {metrics['avg_tracking_error']:.2f}m")
    
    await tester.cleanup()

asyncio.run(custom_mission())
```

## Controller Tuning Example

```python
from dart_planner.control.control_config import get_controller_config, tuning_manager
from dart_planner.control.geometric_controller import GeometricController

# List available tuning profiles
profiles = tuning_manager.list_profiles()
print("Available profiles:", profiles)

# Load specific profile
sitl_config = get_controller_config("sitl_optimized")
print(f"Position gains: Kp={sitl_config.kp_pos}")

# Create controller with custom profile
controller = get_container().create_control_container().get_geometric_controller()tuning_profile="aggressive")
```

## Running Test Suites

```bash
# Run all test configurations
python scripts/run_sitl_tests.py --config all

# Run specific test configuration
python scripts/run_sitl_tests.py --config smoke

# Run with custom scenario
python scripts/run_sitl_tests.py --scenario precision_hover

# Generate performance report
python scripts/run_sitl_tests.py --config comprehensive --report
```

## Performance Analysis

```python
from tests.test_dart_sitl_comprehensive import DARTSITLTester

async def performance_analysis():
    tester = DARTSITLTester()
    
    # Run performance benchmark
    results = await tester.run_performance_test()
    
    # Analyze results
    breakthrough_achieved = all([
        results['planning_time'] < 15.0,  # ms
        results['control_frequency'] > 50.0,  # Hz  
        results['tracking_error'] < 5.0,  # m
        results['mission_success_rate'] > 0.8  # 80%
    ])
    
    print(f"Breakthrough targets achieved: {breakthrough_achieved}")
    
    await tester.cleanup()

asyncio.run(performance_analysis())
```
        """
        
        self.sections.append(DocSection("Usage Examples", content))
        
    def _generate_troubleshooting_guide(self):
        """Generate troubleshooting guide"""
        content = """
Common issues and solutions when using the SITL framework.

## AirSim Connection Issues

### Problem: "Failed to connect to AirSim"
**Symptoms**: Connection timeout, unable to ping AirSim
**Solutions**:
1. Verify AirSim is running and responsive
2. Check IP and port configuration in test settings
3. Ensure no firewall blocking the connection
4. Try increasing connection timeout value

### Problem: "API control not enabled"
**Symptoms**: Vehicle commands are ignored
**Solutions**:
1. Ensure `enable_api_control=True` in configuration
2. Check that vehicle is properly initialized
3. Verify vehicle name matches AirSim settings

## Performance Issues

### Problem: Low control frequency
**Symptoms**: Control frequency < 50Hz, poor tracking
**Solutions**:
1. Use "sitl_optimized" controller tuning profile
2. Reduce planning complexity or frequency
3. Check system resource usage (CPU, memory)
4. Optimize AirSim settings for performance

### Problem: High tracking error
**Symptoms**: Position error > 5m, mission failures
**Solutions**:
1. Switch to "conservative" tuning profile
2. Reduce maximum velocity limits
3. Increase success radius tolerance
4. Check for wind disturbance or sensor issues

## Test Execution Issues

### Problem: Test timeouts
**Symptoms**: Tests exceed timeout limits
**Solutions**:
1. Increase timeout values in test scenarios
2. Use simpler test scenarios for initial validation
3. Check for deadlocks in async operations
4. Monitor system resource usage

### Problem: Inconsistent results
**Symptoms**: Tests pass/fail randomly
**Solutions**:
1. Ensure deterministic initial conditions
2. Add delays between test runs for state reset
3. Check for memory leaks or resource cleanup issues
4. Use Monte Carlo testing to identify edge cases

## Configuration Issues

### Problem: Invalid test scenarios
**Symptoms**: JSON parsing errors, missing parameters
**Solutions**:
1. Validate JSON syntax in scenario files
2. Check for required parameters in scenario definitions
3. Use provided scenario templates as reference
4. Enable detailed logging for error diagnosis

### Problem: Missing dependencies
**Symptoms**: Import errors, module not found
**Solutions**:
1. Ensure all requirements are installed (`pip install -r requirements.txt`)
2. Check Python path includes src and tests directories
3. Verify AirSim Python client is properly installed
4. Use virtual environment to isolate dependencies

## Debugging Tips

1. **Enable Debug Logging**: Set log level to DEBUG for detailed output
2. **Use Mock Interface**: Test without AirSim using mock interface
3. **Step-by-step Debugging**: Run individual test components in isolation
4. **Performance Profiling**: Use cProfile to identify bottlenecks
5. **Memory Monitoring**: Check for memory leaks in long-running tests

## Getting Help

1. Check the GitHub Issues page for known problems
2. Review the test logs for detailed error information
3. Run the diagnostic script: `python scripts/diagnose_sitl_issues.py`
4. Contact the development team with detailed error logs
        """
        
        self.sections.append(DocSection("Troubleshooting Guide", content))
        
    def _write_main_documentation(self):
        """Write the main documentation file"""
        doc_file = self.output_dir / "README.md"
        
        with open(doc_file, 'w') as f:
            f.write("# DART-Planner SITL Test Framework Documentation\n\n")
            f.write("*Generated automatically - do not edit manually*\n\n")
            
            # Table of contents
            f.write("## Table of Contents\n\n")
            for i, section in enumerate(self.sections, 1):
                f.write(f"{i}. [{section.title}](#{section.title.lower().replace(' ', '-')})\n")
            f.write("\n")
            
            # Write all sections
            for section in self.sections:
                f.write(section.to_markdown())
                
        print(f"📖 Main documentation written to {doc_file}")
        
    def _generate_test_configuration_guide(self):
        """Generate test configuration guide"""
        config_file = self.output_dir / "test_configuration.md"
        
        content = """
# Test Configuration Guide

This guide explains how to configure and customize SITL tests for your specific needs.

## Test Configuration Files

The framework uses several configuration files:

- `tests/sitl_test_scenarios.json`: Test scenario definitions
- `src/control/control_config.py`: Controller tuning profiles
- `scripts/run_sitl_tests.py`: Test execution configurations

## Creating Custom Test Scenarios

### Basic Scenario Structure

```json
{
  "my_custom_test": {
    "description": "Custom test scenario description",
    "waypoints": [[0, 0, -2], [5, 5, -2], [0, 0, -2]],
    "max_velocity": 3.0,
    "success_radius": 1.0,
    "timeout": 60.0,
    "wind_enabled": false,
    "sensor_failures": [],
    "expected_success_rate": 90
  }
}
```

### Advanced Scenario Options

#### Wind Configuration
```json
"wind_config": {
  "type": "turbulent",
  "base_velocity": [2.0, 1.0, 0.0],
  "turbulence_intensity": 0.5,
  "correlation_time": 2.0
}
```

#### Sensor Failure Configuration
```json
"sensor_failures": [
  {
    "sensor": "gps",
    "failure_time": 10.0,
    "duration": 30.0,
    "type": "complete_loss"
  }
]
```

#### Communication Issues
```json
"communication_config": {
  "latency_ms": 150,
  "packet_loss_rate": 0.05,
  "jitter_ms": 50
}
```

## Controller Tuning Profiles

### Creating Custom Profiles

```python
from dart_planner.control.control_config import ControllerTuningProfile, tuning_manager

# Define custom profile
custom_profile = ControllerTuningProfile(
    name="my_custom_profile",
    description="Custom tuning for specific conditions",
    kp_pos=np.array([20.0, 20.0, 25.0]),
    ki_pos=np.array([1.0, 1.0, 1.5]),
    kd_pos=np.array([8.0, 8.0, 10.0]),
    # ... other parameters
)

# Add to manager
tuning_manager.add_custom_profile(custom_profile)
```

### Profile Selection Guidelines

- **Conservative**: For stable, precise flight and initial testing
- **Aggressive**: For fast, dynamic maneuvers and stress testing  
- **SITL Optimized**: For simulation testing with AirSim
- **Original**: Reference baseline from Phase 2C optimization

## Test Execution Configuration

### Command Line Options

```bash
# Basic test configurations
python scripts/run_sitl_tests.py --config smoke        # Quick validation
python scripts/run_sitl_tests.py --config performance  # Benchmark testing
python scripts/run_sitl_tests.py --config comprehensive # Full coverage
python scripts/run_sitl_tests.py --config hardware_ready # Pre-deployment

# Custom options
python scripts/run_sitl_tests.py --scenario custom_test --timeout 120
python scripts/run_sitl_tests.py --tuning_profile aggressive --report
```

### Programmatic Configuration

```python
from scripts.run_sitl_tests import SITLTestRunner

# Create test runner with custom config
runner = SITLTestRunner(
    scenarios=['basic_waypoint_mission', 'precision_hover'],
    tuning_profile='conservative',
    enable_reporting=True,
    timeout_multiplier=1.5
)

# Execute tests
results = await runner.run_tests()
```

## Performance Targets

### Breakthrough Targets (Aggressive)
- Planning time: < 15ms
- Control frequency: > 80Hz
- Tracking error: < 2m
- Mission success: > 95%

### Minimum Acceptable (Conservative)  
- Planning time: < 50ms
- Control frequency: > 50Hz
- Tracking error: < 5m
- Mission success: > 80%

## Best Practices

1. **Start Simple**: Begin with basic scenarios before advanced testing
2. **Validate Incrementally**: Test individual components before integration
3. **Use Appropriate Profiles**: Match controller tuning to test objectives
4. **Monitor Resources**: Check CPU, memory usage during testing
5. **Document Changes**: Track modifications to configurations
6. **Version Control**: Keep configuration files under version control
        """
        
        with open(config_file, 'w') as f:
            f.write(content)
            
        print(f"⚙️ Configuration guide written to {config_file}")
        
    def _generate_performance_analysis_guide(self):
        """Generate performance analysis guide"""
        analysis_file = self.output_dir / "performance_analysis.md"
        
        content = """
# Performance Analysis Guide

This guide explains how to analyze and interpret SITL test results for DART-Planner optimization.

## Key Performance Metrics

### Primary Metrics

1. **Planning Time** (ms)
   - Target: < 15ms (breakthrough), < 50ms (acceptable)
   - Measures: SE(3) MPC optimization time
   - Impact: Real-time capability, system responsiveness

2. **Control Frequency** (Hz)
   - Target: > 80Hz (breakthrough), > 50Hz (acceptable)  
   - Measures: Geometric controller execution rate
   - Impact: Tracking precision, stability

3. **Tracking Error** (m)
   - Target: < 2m (breakthrough), < 5m (acceptable)
   - Measures: Average position error from desired trajectory
   - Impact: Mission precision, safety margins

4. **Mission Success Rate** (%)
   - Target: > 95% (breakthrough), > 80% (acceptable)
   - Measures: Percentage of successful mission completions
   - Impact: System reliability, deployment readiness

### Secondary Metrics

- **Velocity Error** (m/s): Tracking accuracy in velocity space
- **Attitude Error** (rad): Orientation tracking precision
- **Computation Load** (%): CPU utilization during operation
- **Memory Usage** (MB): Peak memory consumption
- **Communication Latency** (ms): Network delay impact

## Performance Analysis Workflow

### 1. Data Collection

```python
from tests.test_dart_sitl_comprehensive import DARTSITLTester

async def collect_performance_data():
    tester = DARTSITLTester()
    
    # Run comprehensive performance test
    results = await tester.run_performance_test()
    
    # Get detailed metrics
    metrics = tester.get_performance_metrics()
    
    return results, metrics
```

### 2. Statistical Analysis

```python
import numpy as np
import matplotlib.pyplot as plt

def analyze_tracking_performance(position_errors):
    """Analyze tracking error statistics"""
    
    # Basic statistics
    mean_error = np.mean(position_errors)
    std_error = np.std(position_errors) 
    max_error = np.max(position_errors)
    p95_error = np.percentile(position_errors, 95)
    
    # Performance classification
    if mean_error < 2.0:
        classification = "BREAKTHROUGH"
    elif mean_error < 5.0:
        classification = "ACCEPTABLE" 
    else:
        classification = "NEEDS_IMPROVEMENT"
    
    return {
        'mean': mean_error,
        'std': std_error,
        'max': max_error,
        'p95': p95_error,
        'classification': classification
    }
```

### 3. Trend Analysis

```python
def analyze_performance_trends(test_results):
    """Analyze performance trends over multiple test runs"""
    
    # Extract time series data
    planning_times = [r['planning_time'] for r in test_results]
    tracking_errors = [r['tracking_error'] for r in test_results]
    
    # Check for degradation trends
    planning_trend = np.polyfit(range(len(planning_times)), planning_times, 1)[0]
    tracking_trend = np.polyfit(range(len(tracking_errors)), tracking_errors, 1)[0]
    
    return {
        'planning_degradation': planning_trend > 0.1,  # ms per test
        'tracking_degradation': tracking_trend > 0.01  # m per test
    }
```

## Visualization and Reporting

### Performance Dashboard

```python
import matplotlib.pyplot as plt
import seaborn as sns

def create_performance_dashboard(metrics):
    """Create comprehensive performance visualization"""
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Planning time distribution
    axes[0,0].hist(metrics['planning_times'], bins=30, alpha=0.7)
    axes[0,0].axvline(15, color='r', linestyle='--', label='Breakthrough Target')
    axes[0,0].set_title('Planning Time Distribution')
    axes[0,0].set_xlabel('Time (ms)')
    
    # Tracking error over time
    axes[0,1].plot(metrics['tracking_errors'])
    axes[0,1].axhline(2.0, color='r', linestyle='--', label='Breakthrough Target')
    axes[0,1].set_title('Tracking Error Timeline')
    axes[0,1].set_ylabel('Error (m)')
    
    # Control frequency stability
    axes[1,0].plot(metrics['control_frequencies'])
    axes[1,0].axhline(80, color='r', linestyle='--', label='Breakthrough Target')
    axes[1,0].set_title('Control Frequency')
    axes[1,0].set_ylabel('Frequency (Hz)')
    
    # Mission success summary
    success_data = [metrics['successful_missions'], metrics['total_missions'] - metrics['successful_missions']]
    axes[1,1].pie(success_data, labels=['Success', 'Failure'], autopct='%1.1f%%')
    axes[1,1].set_title('Mission Success Rate')
    
    plt.tight_layout()
    plt.savefig('performance_dashboard.png', dpi=300, bbox_inches='tight')
```

## Optimization Strategies

### For Low Planning Performance
- Reduce MPC horizon length
- Simplify cost function terms
- Use warm-start initialization
- Optimize solver settings

### For Poor Tracking Performance  
- Increase controller gains (Kp, Kd)
- Improve feedforward compensation
- Reduce velocity limits
- Check actuator saturation

### For Low Control Frequency
- Optimize control loop implementation
- Reduce computational complexity
- Profile for performance bottlenecks
- Consider hardware acceleration

### For Poor Mission Success
- Increase tolerance margins
- Improve failure detection and recovery
- Enhance state estimation robustness
- Add redundant navigation modes

## Benchmark Comparisons

### Against Previous Versions
```python
def compare_with_baseline(current_results, baseline_results):
    """Compare current performance with baseline"""
    
    improvements = {}
    for metric in ['planning_time', 'tracking_error', 'control_frequency']:
        current = current_results[metric]
        baseline = baseline_results[metric]
        
        if metric == 'control_frequency':
            improvement = (current - baseline) / baseline * 100
        else:
            improvement = (baseline - current) / baseline * 100
            
        improvements[metric] = improvement
    
    return improvements
```

### Against Literature Standards
- Compare with published UAV control benchmarks
- Evaluate against industry performance standards
- Assess relative to hardware capabilities

## Performance Regression Detection

### Automated Monitoring
```python
def detect_performance_regression(recent_results, historical_baseline):
    """Detect significant performance degradation"""
    
    alerts = []
    
    # Check planning time regression
    if recent_results['avg_planning_time'] > historical_baseline['planning_time'] * 1.2:
        alerts.append("Planning time degraded by >20%")
    
    # Check tracking error regression  
    if recent_results['avg_tracking_error'] > historical_baseline['tracking_error'] * 1.15:
        alerts.append("Tracking error increased by >15%")
    
    return alerts
```

## Reporting Templates

### Executive Summary Format
```
DART-Planner SITL Performance Report
=====================================

Test Date: {date}
Configuration: {config}
Total Scenarios: {total_scenarios}

BREAKTHROUGH METRICS STATUS:
✅/❌ Planning Time: {planning_time:.1f}ms (target: <15ms)
✅/❌ Control Frequency: {control_freq:.1f}Hz (target: >80Hz)  
✅/❌ Tracking Error: {tracking_error:.2f}m (target: <2m)
✅/❌ Mission Success: {success_rate:.1f}% (target: >95%)

OVERALL ASSESSMENT: {BREAKTHROUGH_ACHIEVED/NEEDS_OPTIMIZATION}
```

### Detailed Technical Report
- Full test results with statistical analysis
- Performance trend analysis over time
- Failure mode analysis and recommendations
- Optimization suggestions and next steps
        """
        
        with open(analysis_file, 'w') as f:
            f.write(content)
            
        print(f"📊 Performance analysis guide written to {analysis_file}")


def main():
    """Main entry point"""
    generator = DocumentationGenerator()
    generator.generate_all_docs()


if __name__ == "__main__":
    main() 
