#!/usr/bin/env python3
"""

with proper import statements, assuming the package is installed in editable mode.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_sys_path_insert_files() -> List[Path]:
    python_files = []
    
    for root, dirs, files in os.walk(project_root):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'venv', 'build', 'dist']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                            python_files.append(file_path)
                except Exception as e:
                    print(f"Warning: Could not read {file_path}: {e}")
    
    return python_files


def fix_sys_path_insert(file_path: Path) -> bool:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        pattern = r'sys\.path\.insert\(0,\s*(?:str\()?([^)]+)(?:\))?\)'
        
        # Find all matches
        matches = re.finditer(pattern, content)
        replacements = []
        
        for match in matches:
            path_expr = match.group(1)
            # Extract the actual path from the expression
            if 'Path(__file__)' in path_expr:
                if 'parent.parent' in path_expr and 'src' in path_expr:
                    # This is likely trying to import from src
                    replacements.append(('src', match.group(0)))
                elif 'parent.parent' in path_expr:
                    # This is likely trying to import from project root
                    replacements.append(('dart_planner', match.group(0)))
            elif 'os.path.join' in path_expr:
                # Handle os.path.join patterns
                if 'src' in path_expr:
                    replacements.append(('src', match.group(0)))
                else:
                    replacements.append(('dart_planner', match.group(0)))
            elif 'src' in path_expr:
                replacements.append(('src', match.group(0)))
            else:
                replacements.append(('dart_planner', match.group(0)))
        
        # Apply replacements
        for import_name, sys_path_line in replacements:
            content = content.replace(sys_path_line, '')
            
            # Add proper import at the top if not already present
            if f'from {import_name}' not in content and f'import {import_name}' not in content:
                # Find the right place to insert the import
                lines = content.split('\n')
                import_inserted = False
                
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        # Insert after existing imports
                        lines.insert(i + 1, f'from {import_name} import *')
                        import_inserted = True
                        break
                
                if not import_inserted:
                    # Insert at the beginning after shebang and docstring
                    insert_pos = 0
                    for i, line in enumerate(lines):
                        if line.startswith('#!') or line.startswith('"""') or line.startswith("'''"):
                            insert_pos = i + 1
                        elif line.strip() and not line.startswith('#'):
                            break
                    
                    lines.insert(insert_pos, f'from {import_name} import *')
                
                content = '\n'.join(lines)
        
        # Clean up empty lines
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    
    files = find_sys_path_insert_files()
    
    if not files:
        return
    
    for file in files:
        print(f"  - {file}")
    
    # Fix each file
    fixed_count = 0
    for file_path in files:
        print(f"Processing {file_path}...")
        if fix_sys_path_insert(file_path):
            print(f"  ✅ Fixed {file_path}")
            fixed_count += 1
        else:
            print(f"  ⚠️  No changes needed for {file_path}")
    
    print(f"\n🎉 Fixed {fixed_count} out of {len(files)} files")
    
    if fixed_count > 0:
        print("\n📝 Next steps:")
        print("1. Install the package in editable mode: pip install -e .")
        print("2. Update any remaining import statements to use proper module paths")
        print("3. Test that all imports work correctly")


if __name__ == "__main__":
    main() 
