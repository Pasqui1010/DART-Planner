#!/usr/bin/env python3
"""
Simple Sleep Replacement Script

This script replaces blocking time.sleep calls with async asyncio.sleep
using regex patterns for simplicity.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any
import argparse


def process_file(file_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    """Process a single Python file to replace blocking sleep."""
    result = {
        'file': str(file_path),
        'changes': [],
        'imports_added': [],
        'errors': []
    }
    
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern to match time.sleep calls
        time_sleep_pattern = r'\btime\.sleep\s*\('
        
        # Find all time.sleep occurrences
        matches = list(re.finditer(time_sleep_pattern, content))
        
        if matches:
            # Check if asyncio is already imported
            has_asyncio_import = 'import asyncio' in content or 'from asyncio import' in content
            
            # Replace time.sleep with asyncio.sleep
            content = re.sub(time_sleep_pattern, 'asyncio.sleep(', content)
            
            # Add asyncio import if needed
            if not has_asyncio_import and matches:
                # Find the best place to add import
                import_pattern = r'^(import\s+.*?)$'
                import_matches = list(re.finditer(import_pattern, content, re.MULTILINE))
                
                if import_matches:
                    # Add after last import
                    last_import_pos = import_matches[-1].end()
                    content = content[:last_import_pos] + '\nimport asyncio' + content[last_import_pos:]
                else:
                    # Add at the beginning
                    content = 'import asyncio\n' + content
                
                result['imports_added'].append('asyncio')
            
            # Record changes
            for match in matches:
                result['changes'].append({
                    'line': content[:match.start()].count('\n') + 1,
                    'old': 'time.sleep',
                    'new': 'asyncio.sleep'
                })
            
            # Write changes if not dry run
            if not dry_run and content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    except Exception as e:
        result['errors'].append(str(e))
    
    return result


def find_python_files(directory: Path, exclude_patterns: List[str] = None) -> List[Path]:
    """Find all Python files in a directory."""
    if exclude_patterns is None:
        exclude_patterns = ['__pycache__', '.git', 'venv', 'env', 'node_modules']
    
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_patterns]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    return python_files


def main():
    """Main function to run the sleep replacement script."""
    parser = argparse.ArgumentParser(description='Replace blocking sleep with async sleep')
    parser.add_argument('--directory', '-d', default='src', help='Directory to process')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying them')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"❌ Directory {directory} does not exist")
        return
    
    print(f"🔍 Scanning directory: {directory}")
    
    # Find Python files
    python_files = find_python_files(directory)
    print(f"📁 Found {len(python_files)} Python files")
    
    # Process files
    total_changes = 0
    total_files_changed = 0
    total_imports_added = 0
    
    for file_path in python_files:
        if args.verbose:
            print(f"Processing: {file_path}")
        
        result = process_file(file_path, dry_run=args.dry_run)
        
        if result['changes'] or result['imports_added']:
            total_files_changed += 1
            total_changes += len(result['changes'])
            total_imports_added += len(result['imports_added'])
            
            if args.verbose:
                print(f"  ✅ {file_path}")
                for change in result['changes']:
                    print(f"    Line {change['line']}: {change['old']} → {change['new']}")
                if result['imports_added']:
                    print(f"    Imports added: {', '.join(result['imports_added'])}")
        
        if result['errors']:
            print(f"  ❌ Errors in {file_path}:")
            for error in result['errors']:
                print(f"    {error}")
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   Files processed: {len(python_files)}")
    print(f"   Files changed: {total_files_changed}")
    print(f"   Total sleep replacements: {total_changes}")
    print(f"   Imports added: {total_imports_added}")
    
    if args.dry_run:
        print(f"\n🔍 This was a dry run. Use --dry-run=false to apply changes.")
    else:
        print(f"\n✅ Changes applied successfully!")


if __name__ == "__main__":
    main() 
