# Contributing to Distributed Drone Control System

Thank you for your interest in contributing to this distributed drone control system project. This document provides guidelines for contributing to the codebase, documentation, and research.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Contributing Guidelines](#contributing-guidelines)
- [Code Standards](#code-standards)
- [Documentation](#documentation)
- [Testing](#testing)
- [Issue Reporting](#issue-reporting)
- [Pull Request Process](#pull-request-process)
- [Research Contributions](#research-contributions)

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git for version control
- Basic understanding of control systems and robotics
- Familiarity with distributed computing concepts

### Initial Setup

1. Fork the repository
2. Clone your fork:
   ```bash
git clone https://github.com/Pasqui1010/DART-Planner.git
cd DART-Planner
```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the test suite to verify setup:
   ```bash
   python experiments/validation/test_improved_system.py
   ```

## Development Environment

### Repository Structure

The repository is organized for clear separation of concerns:

- `src/`: Main source code
  - `cloud/`: Cloud-side components (DIAL-MPC planning)
  - `edge/`: Edge-side components (geometric control)
  - `control/`: Control algorithms and implementations
  - `planning/`: Trajectory planning algorithms
  - `communication/`: Network communication protocols
- `experiments/`: Research experiments and validation
- `docs/`: Technical documentation and analysis
- `tests/`: Unit tests and integration tests
- `scripts/`: Utility scripts for analysis and visualization

### Branching Strategy

- `main`: Stable, tested code
- `develop`: Integration branch for new features
- `feature/feature-name`: Feature development branches
- `bugfix/issue-description`: Bug fix branches

## Contributing Guidelines

### Areas for Contribution

1. **Control Algorithm Optimization**
   - Improving geometric controller gains and performance
   - Enhancing DIAL-MPC optimization parameters
   - Implementing advanced control strategies

2. **Planning Enhancement**
   - Extending DIAL-MPC capabilities
   - Implementing obstacle avoidance algorithms
   - Adding trajectory optimization features

3. **Safety Systems**
   - Enhancing failsafe mechanisms
   - Improving monitoring and diagnostics
   - Adding safety validation tests

4. **Communication Layer**
   - Optimizing network protocols
   - Improving error handling
   - Adding communication redundancy

5. **Documentation and Testing**
   - Improving code documentation
   - Adding comprehensive tests
   - Creating tutorials and guides

### Research Contributions

This project serves as a foundation for advanced aerial robotics research. Research contributions are welcome in:

- Neural scene representation integration
- GPS-denied navigation using VIO/LIO
- Multi-agent coordination protocols
- Uncertainty-aware planning algorithms
- Real-world validation and deployment

## Code Standards

### Python Style Guide

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Include type hints where appropriate
- Maintain consistent indentation (4 spaces)

### Code Structure

```python
"""
Module docstring describing purpose and functionality.
"""

import standard_library_modules
import third_party_modules
import local_modules

class ExampleClass:
    """Class docstring explaining purpose and usage."""
    
    def __init__(self, parameter: type) -> None:
        """Initialize with clear parameter documentation."""
        self.parameter = parameter
    
    def method_name(self, input_param: type) -> return_type:
        """
        Method description with clear purpose.
        
        Args:
            input_param: Description of parameter
            
        Returns:
            Description of return value
        """
        # Implementation with clear comments
        return result
```

### Commit Messages

Use clear, descriptive commit messages:
```
feat: add trajectory smoothing implementation
fix: resolve geometric controller instability
docs: update API documentation for DIAL-MPC
test: add comprehensive control system tests
```

## Documentation

### Code Documentation

- Include docstrings for all classes and methods
- Use clear variable names that explain purpose
- Add inline comments for complex algorithms
- Update documentation when changing functionality

### Technical Documentation

- Update relevant documentation in `docs/` when making changes
- Include mathematical formulations for algorithms
- Provide clear explanations of design decisions
- Add diagrams and visualizations where helpful

### README Updates

Update the main README.md when:
- Adding new features or capabilities
- Changing system requirements
- Modifying installation procedures
- Adding new usage examples

## Testing

### Test Requirements

- Write unit tests for new functionality
- Include integration tests for system components
- Verify that changes don't break existing functionality
- Test edge cases and error conditions

### Running Tests

```bash
# Run basic system validation
python experiments/validation/test_improved_system.py

# Run communication tests
python tests/test_communication_flow.py

# Run comprehensive system tests
python experiments/validation/comprehensive_system_test.py
```

### Test Structure

```python
import unittest
from src.module import ComponentClass

class TestComponentClass(unittest.TestCase):
    """Test cases for ComponentClass functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.component = ComponentClass()
    
    def test_specific_functionality(self):
        """Test specific functionality with clear assertions."""
        result = self.component.method()
        self.assertEqual(result, expected_value)
        
    def test_error_conditions(self):
        """Test error handling and edge cases."""
        with self.assertRaises(ExpectedError):
            self.component.invalid_operation()
```

## Issue Reporting

### Bug Reports

When reporting bugs, include:

1. **Environment Information**
   - Python version
   - Operating system
   - Hardware specifications (if relevant)

2. **Steps to Reproduce**
   - Clear, step-by-step instructions
   - Minimal code example if applicable
   - Expected vs. actual behavior

3. **Error Information**
   - Full error messages and stack traces
   - Log files if available
   - System performance data if relevant

### Feature Requests

For feature requests, provide:

1. **Use Case Description**
   - Problem the feature would solve
   - Current workarounds or limitations
   - Expected benefits

2. **Technical Specifications**
   - Proposed implementation approach
   - Integration points with existing system
   - Performance considerations

3. **Research Context**
   - Relevance to aerial robotics research
   - Alignment with project goals
   - References to related work

## Pull Request Process

### Before Submitting

1. Ensure code follows style guidelines
2. Add or update tests for new functionality
3. Update documentation as needed
4. Verify all tests pass
5. Check that changes don't break existing functionality

### Pull Request Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Research contribution

## Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Documentation
- [ ] Code comments updated
- [ ] Documentation updated
- [ ] README updated if needed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Changes are well-documented
- [ ] No breaking changes introduced
```

### Review Process

1. Automated checks must pass
2. Code review by project maintainers
3. Discussion of technical approach if needed
4. Integration testing with existing system
5. Final approval and merge

## Research Contributions

### Experimental Work

- Document experimental procedures and results
- Include performance comparisons with baseline
- Provide analysis of technical improvements
- Consider reproducibility of results

### Publications and Citations

- Acknowledge the project in related publications
- Share research findings that could benefit the project
- Collaborate on joint publications when appropriate

### Data and Visualization

- Contribute analysis scripts and visualization tools
- Share experimental data following privacy guidelines
- Improve existing visualization and analysis capabilities

## Community Guidelines

### Communication

- Use clear, professional language in all communications
- Be respectful of different viewpoints and approaches
- Provide constructive feedback and suggestions
- Ask questions when clarification is needed

### Collaboration

- Work openly and transparently
- Share knowledge and expertise with the community
- Credit contributions appropriately
- Support newcomers to the project

### Code of Conduct

- Treat all participants with respect and professionalism
- Focus on constructive discussion and problem-solving
- Avoid discriminatory or inappropriate language
- Report any violations to project maintainers

## Getting Help

- Review existing documentation and issues before asking questions
- Use GitHub Issues for bug reports and feature requests
- Join discussions on technical approaches and research directions
- Contact maintainers for guidance on significant contributions

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.

Thank you for contributing to advancing aerial robotics research and distributed control systems! 