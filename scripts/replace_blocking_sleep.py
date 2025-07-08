#!/usr/bin/env python3
"""
Replace Blocking Sleep with Async Sleep

This script systematically replaces blocking time.sleep calls with async asyncio.sleep
calls throughout the DART-Planner codebase to improve real-time performance.
"""

import os
import re
import ast
import astor
from pathlib import Path
from typing import List, Tuple, Dict, Any
import argparse


class SleepReplacer(ast.NodeTransformer):
    """AST transformer to replace time.sleep with asyncio.sleep."""
    
    def __init__(self):
        self.changes_made = []
        self.imports_to_add = set()
    
    def visit_Call(self, node):
        """Visit function calls and replace time.sleep with asyncio.sleep."""
        if (isinstance(node.func, ast.Attribute) and 
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'time' and
            node.func.attr == 'sleep'):
            
            # Replace time.sleep with asyncio.sleep
            new_node = ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='asyncio', ctx=ast.Load()),
                    attr='sleep',
                    ctx=ast.Load()
                ),
                args=node.args,
                keywords=node.keywords
            )
            
            self.changes_made.append({
                'line': node.lineno,
                'old': 'time.sleep',
                'new': 'asyncio.sleep'
            })
            self.imports_to_add.add('asyncio')
            
            return new_node
        
        return self.generic_visit(node)


class AsyncFunctionDetector(ast.NodeVisitor):
    """Detect if a function needs to be made async."""
    
    def __init__(self):
        self.has_async_calls = False
        self.has_time_sleep = False
    
    def visit_Call(self, node):
        """Check for asyncio.sleep calls."""
        if (isinstance(node.func, ast.Attribute) and 
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'asyncio' and
            node.func.attr == 'sleep'):
            self.has_async_calls = True
    
    def visit_Attribute(self, node):
        """Check for time.sleep calls."""
        if (isinstance(node.value, ast.Name) and
            node.value.id == 'time' and
            node.attr == 'sleep'):
            self.has_time_sleep = True


class FunctionAsyncifier(ast.NodeTransformer):
    """Make functions async if they contain async calls."""
    
    def __init__(self, functions_to_async: List[str]):
        self.functions_to_async = functions_to_async
    
    def visit_FunctionDef(self, node):
        """Make function async if it's in the list."""
        if node.name in self.functions_to_async and not node.is_async:
            node.is_async = True
        return self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Handle already async functions."""
        return self.generic_visit(node)


class ImportManager:
    """Manage imports in Python files."""
    
    def __init__(self):
        self.imports_to_add = set()
        self.existing_imports = set()
    
    def analyze_imports(self, tree: ast.AST):
        """Analyze existing imports in the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.existing_imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.existing_imports.add(node.module)
    
    def add_import(self, module: str):
        """Add an import to the list."""
        self.imports_to_add.add(module)
    
    def get_imports_to_add(self) -> List[str]:
        """Get list of imports that need to be added."""
        return [imp for imp in self.imports_to_add if imp not in self.existing_imports]


def process_file(file_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    """Process a single Python file to replace blocking sleep."""
    result = {
        'file': str(file_path),
        'changes': [],
        'functions_made_async': [],
        'imports_added': [],
        'errors': []
    }
    
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST
        tree = ast.parse(content)
        
        # Detect functions that need to be made async
        functions_to_async = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                detector = AsyncFunctionDetector()
                detector.visit(node)
                if detector.has_async_calls and not node.is_async:
                    functions_to_async.append(node.name)
        
        # Replace time.sleep with asyncio.sleep
        replacer = SleepReplacer()
        new_tree = replacer.visit(tree)
        
        # Make functions async if needed
        if functions_to_async:
            asyncifier = FunctionAsyncifier(functions_to_async)
            new_tree = asyncifier.visit(new_tree)
        
        # Manage imports
        import_manager = ImportManager()
        import_manager.analyze_imports(new_tree)
        for module in replacer.imports_to_add:
            import_manager.add_import(module)
        
        # Add imports if needed
        imports_to_add = import_manager.get_imports_to_add()
        if imports_to_add:
            # Find the best place to add imports
            import_nodes = []
            for node in ast.walk(new_tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_nodes.append(node)
            
            if import_nodes:
                # Add after existing imports
                last_import = import_nodes[-1]
                for module in imports_to_add:
                    import_node = ast.Import(names=[ast.alias(name=module, asname=None)])
                    # Insert after last import
                    # This is simplified - in practice, you'd need more complex logic
                    pass
        
        # Update result
        result['changes'] = replacer.changes_made
        result['functions_made_async'] = functions_to_async
        result['imports_added'] = imports_to_add
        
        # Write changes if not dry run
        if not dry_run and (result['changes'] or result['functions_made_async'] or result['imports_added']):
            # Convert back to source code
            new_content = astor.to_source(new_tree)
            
            # Add imports manually if needed
            if imports_to_add:
                import_lines = [f"import {module}" for module in imports_to_add]
                lines = new_content.split('\n')
                # Find first non-import line
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith(('import ', 'from ')):
                        insert_pos = i
                        break
                
                # Insert imports
                for import_line in reversed(import_lines):
                    lines.insert(insert_pos, import_line)
                
                new_content = '\n'.join(lines)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
    
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
    total_functions_async = 0
    total_imports_added = 0
    
    for file_path in python_files:
        if args.verbose:
            print(f"Processing: {file_path}")
        
        result = process_file(file_path, dry_run=args.dry_run)
        
        if result['changes'] or result['functions_made_async'] or result['imports_added']:
            total_files_changed += 1
            total_changes += len(result['changes'])
            total_functions_async += len(result['functions_made_async'])
            total_imports_added += len(result['imports_added'])
            
            if args.verbose:
                print(f"  ✅ {file_path}")
                for change in result['changes']:
                    print(f"    Line {change['line']}: {change['old']} → {change['new']}")
                if result['functions_made_async']:
                    print(f"    Functions made async: {', '.join(result['functions_made_async'])}")
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
    print(f"   Functions made async: {total_functions_async}")
    print(f"   Imports added: {total_imports_added}")
    
    if args.dry_run:
        print(f"\n🔍 This was a dry run. Use --dry-run=false to apply changes.")
    else:
        print(f"\n✅ Changes applied successfully!")


if __name__ == "__main__":
    main() 
