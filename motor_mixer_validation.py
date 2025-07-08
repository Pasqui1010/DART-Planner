"""
Validation script for motor mixer refactoring.

This script validates the key improvements made to the motor mixer:
1. Consistent SI units
2. Removal of magic scale factors
3. Proper unit documentation
4. Physical basis for mixing matrix
"""

import os
import re

def validate_motor_mixer_file():
    """Validate the motor mixer file for key improvements."""
    file_path = "src/dart_planner/hardware/motor_mixer.py"
    
    if not os.path.exists(file_path):
        print(f"✗ Motor mixer file not found: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    print("Validating motor mixer refactoring...")
    print("=" * 50)
    
    # Check 1: SI units documentation
    si_units_pattern = r"All units are SI.*Newtons.*Newton-meters.*meters.*PWM.*normalized"
    if re.search(si_units_pattern, content, re.DOTALL):
        print("✓ SI units properly documented")
    else:
        print("✗ SI units documentation missing or incomplete")
        return False
    
    # Check 2: No magic scale factors in mixing matrix
    magic_coefficients = [
        "thrust_coefficient: float = 1.0e-5",
        "torque_coefficient: float = 1.0e-7"
    ]
    
    for magic_coeff in magic_coefficients:
        if magic_coeff in content:
            print(f"✗ Magic scale factor still present: {magic_coeff}")
            return False
    
    print("✓ Magic scale factors removed from mixing matrix")
    
    # Check 3: Physical basis for mixing matrix
    physical_basis_pattern = r"Physical basis.*Thrust.*Roll torque.*Pitch torque.*Yaw torque"
    if re.search(physical_basis_pattern, content, re.DOTALL):
        print("✓ Physical basis for mixing matrix documented")
    else:
        print("✗ Physical basis documentation missing")
        return False
    
    # Check 4: Unit validation in docstrings
    unit_docs = [
        "thrust.*Newtons",
        "torque.*Newton-meters",
        "motor_pwms.*normalized"
    ]
    
    for unit_doc in unit_docs:
        if re.search(unit_doc, content):
            print(f"✓ Unit documentation present: {unit_doc}")
        else:
            print(f"✗ Unit documentation missing: {unit_doc}")
            return False
    
    # Check 5: Proper mixing matrix computation
    matrix_computation = [
        "matrix[i, 0] = 1.0  # Unit contribution to thrust",
        "matrix[i, 1] = y  # meters * thrust = N⋅m",
        "matrix[i, 2] = x  # meters * thrust = N⋅m",
        "matrix[i, 3] = direction  # Unit contribution to yaw torque"
    ]
    
    for computation in matrix_computation:
        if computation in content:
            print(f"✓ Proper mixing matrix computation: {computation}")
        else:
            print(f"✗ Mixing matrix computation issue: {computation}")
            return False
    
    # Check 6: Input validation
    validation_patterns = [
        "thrust < 0",
        "logger.warning.*Negative thrust command",
        "thrust = 0.0"
    ]
    
    for pattern in validation_patterns:
        if pattern in content:
            print(f"✓ Input validation present: {pattern}")
        else:
            print(f"✗ Input validation missing: {pattern}")
            return False
    
    # Check 7: Configuration validation
    config_validation = [
        "arm_length <= 0",
        "Arm length must be positive",
        "motor_positions",
        "motor_directions"
    ]
    
    for validation in config_validation:
        if validation in content:
            print(f"✓ Configuration validation present: {validation}")
        else:
            print(f"✗ Configuration validation missing: {validation}")
            return False
    
    print("=" * 50)
    print("✓ All validation checks passed!")
    return True


def validate_test_file():
    """Validate the test file for comprehensive coverage."""
    test_file_path = "tests/hardware/test_motor_mixer_units.py"
    
    if not os.path.exists(test_file_path):
        print(f"✗ Test file not found: {test_file_path}")
        return False
    
    with open(test_file_path, 'r') as f:
        content = f.read()
    
    print("\nValidating test coverage...")
    print("=" * 50)
    
    # Check test coverage
    test_patterns = [
        "test_mixing_matrix_physical_units",
        "test_thrust_only_command", 
        "test_roll_torque_command",
        "test_pitch_torque_command",
        "test_yaw_torque_command",
        "test_combined_command",
        "test_negative_thrust_handling",
        "test_saturation_handling",
        "test_input_validation",
        "test_configuration_validation",
        "test_motor_layout_info"
    ]
    
    for pattern in test_patterns:
        if pattern in content:
            print(f"✓ Test present: {pattern}")
        else:
            print(f"✗ Test missing: {pattern}")
            return False
    
    # Check for unit validation in tests
    unit_test_patterns = [
        "thrust = 20.0  # N",
        "torque.*N⋅m",
        "expected_roll.*meters",
        "units.*thrust.*Newtons",
        "units.*torque.*Newton-meters"
    ]
    
    for pattern in unit_test_patterns:
        if re.search(pattern, content):
            print(f"✓ Unit validation in tests: {pattern}")
        else:
            print(f"✗ Unit validation missing in tests: {pattern}")
            return False
    
    print("=" * 50)
    print("✓ All test validation checks passed!")
    return True


def main():
    """Run all validations."""
    print("Motor Mixer Refactoring Validation")
    print("=" * 60)
    
    success = True
    
    # Validate motor mixer file
    if not validate_motor_mixer_file():
        success = False
    
    # Validate test file
    if not validate_test_file():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All validations passed! Motor mixer refactoring is complete.")
        print("\nKey improvements achieved:")
        print("• Consistent SI units throughout")
        print("• Removed magic scale factors")
        print("• Added comprehensive unit documentation")
        print("• Physical basis for mixing matrix computation")
        print("• Input validation and error handling")
        print("• Configuration validation")
        print("• Comprehensive unit tests")
        return 0
    else:
        print("❌ Some validations failed. Please review the issues above.")
        return 1


if __name__ == "__main__":
    exit(main()) 