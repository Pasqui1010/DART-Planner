"""
Tests for secure file utilities.
"""

import pytest
import tempfile
import os
import stat
from pathlib import Path
from unittest.mock import patch

from dart_planner.security.secure_file_utils import (
    validate_path_security,
    set_secure_permissions,
    create_secure_directory,
    secure_file_write,
    secure_file_read,
    secure_json_write,
    secure_json_read,
    secure_binary_write,
    secure_binary_read,
    check_file_security,
    secure_backup_file,
    SecurityError
)


class TestSecureFileUtils:
    """Test secure file utilities functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_keys.json"
        self.test_data = {"key1": "value1", "key2": "value2"}
        self.test_binary_data = b"test binary data"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_path_security_normal_file(self):
        """Test path security validation for normal file."""
        # Create a normal file
        self.test_file.write_text("test")
        
        # Should not raise an exception
        validate_path_security(self.test_file)
    
    def test_validate_path_security_symlink_file(self):
        """Test path security validation for symlink file."""
        # Create a normal file
        normal_file = Path(self.temp_dir) / "normal.txt"
        normal_file.write_text("test")
        
        # Create a symlink to it
        symlink_file = Path(self.temp_dir) / "symlink.txt"
        symlink_file.symlink_to(normal_file)
        
        # Should raise SecurityError
        with pytest.raises(SecurityError, match="is a symlink"):
            validate_path_security(symlink_file)
    
    def test_validate_path_security_symlink_parent(self):
        """Test path security validation for symlink parent directory."""
        # Create a symlink directory
        normal_dir = Path(self.temp_dir) / "normal_dir"
        normal_dir.mkdir()
        
        symlink_dir = Path(self.temp_dir) / "symlink_dir"
        symlink_dir.symlink_to(normal_dir)
        
        # Create a file in the symlinked directory
        test_file = symlink_dir / "test.txt"
        test_file.write_text("test")
        
        # Should raise SecurityError
        with pytest.raises(SecurityError, match="Parent directory.*is a symlink"):
            validate_path_security(test_file)
    
    def test_set_secure_permissions(self):
        """Test setting secure permissions."""
        # Create a file with loose permissions
        self.test_file.write_text("test")
        os.chmod(self.test_file, 0o666)
        
        # Set secure permissions
        set_secure_permissions(self.test_file)
        
        # Check permissions
        file_mode = stat.S_IMODE(self.test_file.stat().st_mode)
        assert file_mode == 0o600
        
        # Check parent directory permissions
        parent_mode = stat.S_IMODE(self.test_file.parent.stat().st_mode)
        assert parent_mode == 0o700
    
    def test_create_secure_directory(self):
        """Test creating secure directory."""
        secure_dir = Path(self.temp_dir) / "secure_dir"
        
        # Create secure directory
        created_dir = create_secure_directory(secure_dir)
        
        # Check it exists and has secure permissions
        assert created_dir.exists()
        dir_mode = stat.S_IMODE(created_dir.stat().st_mode)
        assert dir_mode == 0o700
    
    def test_create_secure_directory_symlink_parent(self):
        """Test creating secure directory with symlink parent."""
        # Create a symlink directory
        normal_dir = Path(self.temp_dir) / "normal_dir"
        normal_dir.mkdir()
        
        symlink_dir = Path(self.temp_dir) / "symlink_dir"
        symlink_dir.symlink_to(normal_dir)
        
        # Try to create directory in symlinked parent
        secure_dir = symlink_dir / "secure_dir"
        
        with pytest.raises(SecurityError, match="is a symlink"):
            create_secure_directory(secure_dir)
    
    def test_secure_file_write(self):
        """Test secure file writing."""
        with secure_file_write(self.test_file) as f:
            f.write("test data")
        
        # Check file exists and has secure permissions
        assert self.test_file.exists()
        file_mode = stat.S_IMODE(self.test_file.stat().st_mode)
        assert file_mode == 0o600
        
        # Check content
        assert self.test_file.read_text() == "test data"
    
    def test_secure_file_read(self):
        """Test secure file reading."""
        # Create file with test data
        self.test_file.write_text("test data")
        set_secure_permissions(self.test_file)
        
        with secure_file_read(self.test_file) as f:
            content = f.read()
        
        assert content == "test data"
    
    def test_secure_json_write(self):
        """Test secure JSON writing."""
        secure_json_write(self.test_file, self.test_data)
        
        # Check file exists and has secure permissions
        assert self.test_file.exists()
        file_mode = stat.S_IMODE(self.test_file.stat().st_mode)
        assert file_mode == 0o600
        
        # Check content
        import json
        loaded_data = json.loads(self.test_file.read_text())
        assert loaded_data == self.test_data
    
    def test_secure_json_read(self):
        """Test secure JSON reading."""
        # Create file with JSON data
        import json
        self.test_file.write_text(json.dumps(self.test_data))
        set_secure_permissions(self.test_file)
        
        loaded_data = secure_json_read(self.test_file)
        assert loaded_data == self.test_data
    
    def test_secure_binary_write(self):
        """Test secure binary writing."""
        secure_binary_write(self.test_file, self.test_binary_data)
        
        # Check file exists and has secure permissions
        assert self.test_file.exists()
        file_mode = stat.S_IMODE(self.test_file.stat().st_mode)
        assert file_mode == 0o600
        
        # Check content
        assert self.test_file.read_bytes() == self.test_binary_data
    
    def test_secure_binary_read(self):
        """Test secure binary reading."""
        # Create file with binary data
        self.test_file.write_bytes(self.test_binary_data)
        set_secure_permissions(self.test_file)
        
        loaded_data = secure_binary_read(self.test_file)
        assert loaded_data == self.test_binary_data
    
    def test_check_file_security_secure(self):
        """Test file security check for secure file."""
        # Create file with secure permissions
        self.test_file.write_text("test")
        set_secure_permissions(self.test_file)
        
        security_info = check_file_security(self.test_file)
        
        assert security_info["secure"] is True
        assert security_info["exists"] is True
        assert security_info["is_symlink"] is False
        assert security_info["parent_is_symlink"] is False
        assert security_info["file_permissions"] == "0o600"
        assert security_info["parent_permissions"] == "0o700"
        assert len(security_info["issues"]) == 0
    
    def test_check_file_security_insecure(self):
        """Test file security check for insecure file."""
        # Create file with loose permissions
        self.test_file.write_text("test")
        os.chmod(self.test_file, 0o666)
        
        security_info = check_file_security(self.test_file)
        
        assert security_info["secure"] is False
        assert "loose permissions" in security_info["issues"][0]
    
    def test_check_file_security_symlink(self):
        """Test file security check for symlink file."""
        # Create a normal file
        normal_file = Path(self.temp_dir) / "normal.txt"
        normal_file.write_text("test")
        
        # Create a symlink to it
        symlink_file = Path(self.temp_dir) / "symlink.txt"
        symlink_file.symlink_to(normal_file)
        
        security_info = check_file_security(symlink_file)
        
        assert security_info["secure"] is False
        assert security_info["is_symlink"] is True
        assert "symlink" in security_info["issues"][0]
    
    def test_check_file_security_nonexistent(self):
        """Test file security check for nonexistent file."""
        nonexistent_file = Path(self.temp_dir) / "nonexistent.txt"
        
        security_info = check_file_security(nonexistent_file)
        
        assert security_info["secure"] is False
        assert security_info["exists"] is False
        assert "does not exist" in security_info["issues"][0]
    
    def test_secure_backup_file(self):
        """Test secure file backup."""
        # Create original file
        self.test_file.write_text("original data")
        set_secure_permissions(self.test_file)
        
        # Create backup
        backup_path = secure_backup_file(self.test_file)
        
        # Check backup exists and has secure permissions
        assert backup_path is not None
        assert backup_path.exists()
        file_mode = stat.S_IMODE(backup_path.stat().st_mode)
        assert file_mode == 0o600
        
        # Check backup content
        assert backup_path.read_text() == "original data"
    
    def test_secure_backup_file_nonexistent(self):
        """Test secure backup of nonexistent file."""
        nonexistent_file = Path(self.temp_dir) / "nonexistent.txt"
        
        backup_path = secure_backup_file(nonexistent_file)
        
        assert backup_path is None
    
    def test_secure_file_write_custom_permissions(self):
        """Test secure file writing with custom permissions."""
        with secure_file_write(self.test_file, file_perms=0o400, dir_perms=0o500) as f:
            f.write("test data")
        
        # Check custom permissions
        file_mode = stat.S_IMODE(self.test_file.stat().st_mode)
        assert file_mode == 0o400
        
        parent_mode = stat.S_IMODE(self.test_file.parent.stat().st_mode)
        assert parent_mode == 0o500
    
    def test_secure_file_write_no_validation(self):
        """Test secure file writing without security validation."""
        # Create a symlink file
        normal_file = Path(self.temp_dir) / "normal.txt"
        normal_file.write_text("test")
        
        symlink_file = Path(self.temp_dir) / "symlink.txt"
        symlink_file.symlink_to(normal_file)
        
        # Should work without validation
        with secure_file_write(symlink_file, validate_security=False) as f:
            f.write("test data")
        
        # Check file was written
        assert symlink_file.exists()
    
    def test_secure_file_read_no_validation(self):
        """Test secure file reading without security validation."""
        # Create a symlink file
        normal_file = Path(self.temp_dir) / "normal.txt"
        normal_file.write_text("test data")
        
        symlink_file = Path(self.temp_dir) / "symlink.txt"
        symlink_file.symlink_to(normal_file)
        
        # Should work without validation
        with secure_file_read(symlink_file, validate_security=False) as f:
            content = f.read()
        
        assert content == "test data"


if __name__ == "__main__":
    pytest.main([__file__]) 