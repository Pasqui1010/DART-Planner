"""
Test security fixes for DART-Planner.

This test verifies:
1. Deep recursion protection in deserialize()
2. No dangerous subprocess usage in test files
"""

import pytest
import json
import numpy as np
from unittest.mock import patch, MagicMock

from dart_planner.communication.secure_serializer import SecureSerializer
from dart_planner.common.errors import CommunicationError


class TestSecurityFixes:
    """Test suite for security fixes."""
    
    def test_deep_recursion_protection(self):
        """Test that deserialize() is protected against deep recursion attacks."""
        serializer = SecureSerializer(secret_key="test_key")
        
        # Create a deeply nested structure that would cause recursion
        deep_structure = []
        current = deep_structure
        for i in range(150):  # Exceeds max_depth of 100
            current.append([])
            current = current[0]
        
        # Serialize the deep structure
        serialized = serializer.serialize(deep_structure)
        
        # Attempt to deserialize - should raise CommunicationError
        with pytest.raises(CommunicationError) as exc_info:
            serializer.deserialize(serialized)
        
        assert "Maximum recursion depth 100 exceeded" in str(exc_info.value)
    
    def test_normal_deserialization_still_works(self):
        """Test that normal deserialization still works with depth protection."""
        serializer = SecureSerializer(secret_key="test_key")
        
        # Create a normal nested structure
        normal_structure = {
            "positions": [[1, 2, 3], [4, 5, 6]],
            "velocities": [[0.1, 0.2, 0.3]],
            "nested": {
                "data": [1, 2, 3, 4, 5]
            }
        }
        
        # Serialize and deserialize
        serialized = serializer.serialize(normal_structure)
        deserialized = serializer.deserialize(serialized)
        
        # Verify the structure is preserved
        assert "positions" in deserialized
        assert "velocities" in deserialized
        assert "nested" in deserialized
        # Handle numpy arrays properly
        if hasattr(deserialized["nested"]["data"], 'tolist'):
            assert deserialized["nested"]["data"].tolist() == [1, 2, 3, 4, 5]
        else:
            assert deserialized["nested"]["data"] == [1, 2, 3, 4, 5]
    
    def test_numpy_array_restoration_still_works(self):
        """Test that numpy array restoration still works with depth protection."""
        serializer = SecureSerializer(secret_key="test_key")
        
        # Create structure with numpy arrays
        structure_with_arrays = {
            "position": np.array([1.0, 2.0, 3.0]),
            "velocity": np.array([0.1, 0.2, 0.3]),
            "nested": {
                "data": np.array([1, 2, 3, 4, 5])
            }
        }
        
        # Serialize and deserialize
        serialized = serializer.serialize(structure_with_arrays)
        deserialized = serializer.deserialize(serialized)
        
        # Verify numpy arrays are restored
        assert isinstance(deserialized["position"], np.ndarray)
        assert isinstance(deserialized["velocity"], np.ndarray)
        assert isinstance(deserialized["nested"]["data"], np.ndarray)
        assert np.array_equal(deserialized["position"], np.array([1.0, 2.0, 3.0]))
    
    def test_no_dangerous_subprocess_in_tests(self):
        """Test that no dangerous subprocess usage exists in test files."""
        import os
        import ast
        
        def check_file_for_dangerous_subprocess(filepath):
            """Check a single file for dangerous subprocess usage."""
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for dangerous patterns
                dangerous_patterns = [
                    'subprocess.Popen(shlex.split(',
                    'subprocess.Popen(user_input',
                    'subprocess.run(user_input',
                    'subprocess.call(user_input',
                    'subprocess.check_call(user_input',
                    'subprocess.check_output(user_input',
                ]
                
                for pattern in dangerous_patterns:
                    if pattern in content:
                        return f"Dangerous subprocess pattern found: {pattern}"
                
                return None
            except Exception as e:
                return f"Error reading file {filepath}: {e}"
        
        # Check all test files except this one
        test_dir = "tests"
        dangerous_files = []
        
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    # Skip this test file itself
                    if filepath == __file__:
                        continue
                    result = check_file_for_dangerous_subprocess(filepath)
                    if result:
                        dangerous_files.append((filepath, result))
        
        # Assert no dangerous files found
        if dangerous_files:
            error_msg = "Dangerous subprocess usage found in test files:\n"
            for filepath, issue in dangerous_files:
                error_msg += f"  {filepath}: {issue}\n"
            pytest.fail(error_msg)
        
        # If we get here, no dangerous usage was found
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
