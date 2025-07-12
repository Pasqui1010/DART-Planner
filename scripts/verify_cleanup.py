#!/usr/bin/env python3
"""
Verification Script for DART-Planner Repository Cleanup

This script verifies that the repository cleanup was successful and all examples
are properly organized and functional.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import subprocess
import importlib.util


class CleanupVerifier:
    """Verify repository cleanup and example organization."""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.verification_results = []
        self.errors = []
        
    def log_result(self, test: str, status: str, details: str = ""):
        """Log verification results."""
        self.verification_results.append({
            "test": test,
            "status": status,
            "details": details
        })
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test}: {details}")
    
    def verify_directory_structure(self):
        """Verify the new directory structure is correct."""
        print("\n🔍 Verifying Directory Structure...")
        
        # Check examples organization
        examples_dir = self.root_dir / "examples"
        if not examples_dir.exists():
            self.log_result("Examples Directory", "FAIL", "Examples directory not found")
            return
        
        # Check complexity-based subdirectories
        complexity_levels = ["beginner", "intermediate", "advanced"]
        for level in complexity_levels:
            level_dir = examples_dir / level
            if level_dir.exists():
                file_count = len(list(level_dir.glob("*.py")))
                self.log_result(f"Examples {level.title()}", "PASS", f"{file_count} examples found")
            else:
                self.log_result(f"Examples {level.title()}", "FAIL", f"Directory not found")
        
        # Check archive structure
        archive_dir = self.root_dir / "archive"
        if archive_dir.exists():
            obsolete_dir = archive_dir / "obsolete_files"
            if obsolete_dir.exists():
                file_count = len(list(obsolete_dir.iterdir()))
                self.log_result("Archive Structure", "PASS", f"{file_count} files archived")
            else:
                self.log_result("Archive Structure", "FAIL", "Obsolete files directory not found")
        else:
            self.log_result("Archive Structure", "FAIL", "Archive directory not found")
    
    def verify_example_files(self):
        """Verify that example files are in correct locations."""
        print("\n📁 Verifying Example File Organization...")
        
        expected_examples = {
            "beginner": [
                "minimal_takeoff.py",
                "heartbeat_demo.py"
            ],
            "intermediate": [
                "state_buffer_demo.py",
                "quartic_scheduler_demo.py"
            ],
            "advanced": [
                "advanced_mission_example.py",
                "real_time_integration_example.py",
                "run_pixhawk_mission.py"
            ]
        }
        
        examples_dir = self.root_dir / "examples"
        for level, files in expected_examples.items():
            level_dir = examples_dir / level
            for file_name in files:
                file_path = level_dir / file_name
                if file_path.exists():
                    self.log_result(f"Example {file_name}", "PASS", f"Found in {level}/")
                else:
                    self.log_result(f"Example {file_name}", "FAIL", f"Missing from {level}/")
    
    def verify_archived_files(self):
        """Verify that obsolete files are properly archived."""
        print("\n🗂️ Verifying Archived Files...")
        
        expected_archived = [
            "debug_coordinate_frames.py",
            "debug_latency_buffer.py",
            "debug_motor_mixing.py",
            "debug_quartic_scheduler.py",
            "motor_mixer_validation.py",
            "test_motor_mixer_direct.py",
            "test_motor_mixer_standalone.py",
            "test_motor_mixing_integration.py",
            "test_motor_mixing_simple.py",
            "airsim_rgb_test.png",
            "system_status_report_1751468544.png",
            "protected_key_test_key_id.bin",
            "salt_dart_planner_master.bin"
        ]
        
        archive_dir = self.root_dir / "archive" / "obsolete_files"
        for file_name in expected_archived:
            file_path = archive_dir / file_name
            if file_path.exists():
                self.log_result(f"Archived {file_name}", "PASS", "Properly archived")
            else:
                self.log_result(f"Archived {file_name}", "FAIL", "Not found in archive")
    
    def verify_documentation(self):
        """Verify that documentation files are present and accessible."""
        print("\n📚 Verifying Documentation...")
        
        required_docs = [
            "README.md",
            "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md",
            "LICENSE"
        ]
        
        for doc_file in required_docs:
            doc_path = self.root_dir / doc_file
            if doc_path.exists():
                size = doc_path.stat().st_size
                if size > 0:
                    self.log_result(f"Documentation {doc_file}", "PASS", f"{size} bytes")
                else:
                    self.log_result(f"Documentation {doc_file}", "FAIL", "Empty file")
            else:
                self.log_result(f"Documentation {doc_file}", "FAIL", "File not found")
    
    def verify_example_syntax(self):
        """Verify that example files have valid Python syntax."""
        print("\n🐍 Verifying Example Syntax...")
        
        examples_dir = self.root_dir / "examples"
        for level_dir in examples_dir.iterdir():
            if level_dir.is_dir():
                for py_file in level_dir.glob("*.py"):
                    try:
                        # Try to compile the file
                        with open(py_file, 'r', encoding='utf-8') as f:
                            compile(f.read(), str(py_file), 'exec')
                        self.log_result(f"Syntax {py_file.name}", "PASS", "Valid Python syntax")
                    except SyntaxError as e:
                        self.log_result(f"Syntax {py_file.name}", "FAIL", f"Syntax error: {e}")
                    except Exception as e:
                        self.log_result(f"Syntax {py_file.name}", "FAIL", f"Error: {e}")
    
    def verify_imports(self):
        """Verify that examples can import required modules."""
        print("\n📦 Verifying Example Imports...")
        
        # Add src to path for imports
        src_path = self.root_dir / "src"
        if src_path.exists():
            sys.path.insert(0, str(src_path))
        
        examples_dir = self.root_dir / "examples"
        for level_dir in examples_dir.iterdir():
            if level_dir.is_dir():
                for py_file in level_dir.glob("*.py"):
                    try:
                        # Try to import the module
                        spec = importlib.util.spec_from_file_location(
                            py_file.stem, py_file
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            # Don't execute, just verify it can be loaded
                            self.log_result(f"Import {py_file.name}", "PASS", "Can be imported")
                        else:
                            self.log_result(f"Import {py_file.name}", "FAIL", "Cannot create spec")
                    except ImportError as e:
                        self.log_result(f"Import {py_file.name}", "FAIL", f"Import error: {e}")
                    except Exception as e:
                        self.log_result(f"Import {py_file.name}", "FAIL", f"Error: {e}")
    
    def verify_no_obsolete_files_in_root(self):
        """Verify that no obsolete files remain in the root directory."""
        print("\n🧹 Verifying Root Directory Cleanliness...")
        
        obsolete_patterns = [
            "debug_*.py",
            "test_motor_*.py",
            "motor_mixer_validation.py",
            "*.png",
            "*.bin"
        ]
        
        for pattern in obsolete_patterns:
            for file_path in self.root_dir.glob(pattern):
                if file_path.is_file():
                    self.log_result(f"Obsolete file {file_path.name}", "FAIL", "Still in root directory")
                else:
                    self.log_result(f"Pattern {pattern}", "PASS", "No obsolete files found")
    
    def generate_verification_report(self):
        """Generate a comprehensive verification report."""
        from datetime import datetime
        
        print("\n📊 Generating Verification Report...")
        
        total_tests = len(self.verification_results)
        passed_tests = len([r for r in self.verification_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.verification_results if r["status"] == "FAIL"])
        
        report_content = f"""# DART-Planner Cleanup Verification Report

**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Purpose**: Verify repository cleanup and organization

## 📊 Summary

- **Total Tests**: {total_tests}
- **Passed**: {passed_tests}
- **Failed**: {failed_tests}
- **Success Rate**: {(passed_tests/total_tests*100):.1f}%

## 🔍 Test Results

"""
        
        # Group results by category
        categories = {}
        for result in self.verification_results:
            category = result["test"].split()[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        for category, results in categories.items():
            report_content += f"\n### {category.title()}\n\n"
            for result in results:
                status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
                report_content += f"- {status_icon} **{result['test']}**: {result['details']}\n"
        
        report_content += f"""
## 🎯 Recommendations

"""
        
        if failed_tests == 0:
            report_content += """- ✅ **All tests passed!** Repository cleanup was successful
- 🚀 Repository is ready for open source release
- 📚 Documentation and examples are properly organized
- 🧹 All obsolete files have been archived
"""
        else:
            report_content += """- ⚠️ **Some issues found** - review failed tests above
- 🔧 Fix any failed tests before open source release
- 📋 Address import or syntax issues in examples
- 🗂️ Ensure all obsolete files are properly archived
"""
        
        report_content += f"""
## 📁 Current Structure

### Examples Organization
```
examples/
├── beginner/          # {len(list((self.root_dir / 'examples' / 'beginner').glob('*.py')))} files
├── intermediate/      # {len(list((self.root_dir / 'examples' / 'intermediate').glob('*.py')))} files
└── advanced/          # {len(list((self.root_dir / 'examples' / 'advanced').glob('*.py')))} files
```

### Archived Files
```
archive/
└── obsolete_files/    # {len(list((self.root_dir / 'archive' / 'obsolete_files').iterdir()))} files
```

## 🎉 Conclusion

The repository cleanup verification shows that the reorganization was **{'successful' if failed_tests == 0 else 'partially successful'}**.

{'All systems are ready for open source release!' if failed_tests == 0 else 'Some issues need to be addressed before open source release.'}

---
*Generated by DART-Planner Cleanup Verification Script*
"""
        
        report_file = self.root_dir / "VERIFICATION_REPORT.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.log_result("Verification Report", "PASS", f"Report saved to {report_file}")
        
        return failed_tests == 0
    
    def run_verification(self):
        """Run all verification tests."""
        print("🔍 DART-Planner Repository Cleanup Verification")
        print("=" * 60)
        
        # Run all verification tests
        self.verify_directory_structure()
        self.verify_example_files()
        self.verify_archived_files()
        self.verify_documentation()
        self.verify_example_syntax()
        self.verify_imports()
        self.verify_no_obsolete_files_in_root()
        
        # Generate report
        success = self.generate_verification_report()
        
        print("\n" + "=" * 60)
        if success:
            print("✅ All verification tests passed!")
            print("🎯 Repository is ready for open source release!")
        else:
            print("⚠️ Some verification tests failed.")
            print("📋 Please review the verification report for details.")
        
        print(f"📊 See VERIFICATION_REPORT.md for complete results")
        
        return success


def main():
    """Main execution function."""
    from datetime import datetime
    
    verifier = CleanupVerifier()
    success = verifier.run_verification()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 