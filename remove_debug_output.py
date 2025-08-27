#!/usr/bin/env python3
"""
Script to remove debug output from forest_model.py
"""

import re

def remove_debug_output():
    """Remove all debug print statements from forest_model.py"""
    
    # Read the file
    with open('src/core/forest_model.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove debug print statements
    # Pattern to match debug print statements
    debug_patterns = [
        r'# Debug: Check if we\'re accessing the ignition point\n\s*if x == 395 and y == 377 and z == 0:\n\s*print\(f"🔍 DEBUG: Accessing fuel at ignition point \({x}, {y}, {z}\)"\)\n\s*print\(f"🔍 DEBUG: sparse_matrix type: {type\(sparse_matrix\)}"\)\n\s*print\(f"🔍 DEBUG: sparse_layers keys: {list\(self\.sparse_layers\.keys\(\)\) if isinstance\(self\.sparse_layers, dict\) else \'not dict\'}"\)\n\s*',
        r'if x == 395 and y == 377 and z == 0:\n\s*print\(f"🔍 DEBUG: DOK matrix - found value: {value}"\)',
        r'if x == 395 and y == 377 and z == 0:\n\s*print\(f"🔍 DEBUG: DOK matrix - key not found, returning default: {self\.default_value}"\)',
        r'if x == 395 and y == 377 and z == 0:\n\s*print\(f"🔍 DEBUG: LIL matrix - found value: {value}"\)',
        r'if x == 395 and y == 377 and z == 0:\n\s*print\(f"🔍 DEBUG: LIL matrix - key not found, returning default: {self\.default_value}"\)',
        r'if x == 395 and y == 377 and z == 0:\n\s*print\(f"🔍 DEBUG: Generic matrix - found value: {val}"\)',
        r'if x == 395 and y == 377 and z == 0:\n\s*print\(f"🔍 DEBUG: Generic matrix - exception, returning default: {self\.default_value}"\)',
    ]
    
    # Simple approach: remove lines containing debug output
    lines = content.split('\n')
    cleaned_lines = []
    
    skip_next = False
    for i, line in enumerate(lines):
        # Skip debug-related lines
        if any(pattern in line for pattern in [
            '🔍 DEBUG:',
            '# Debug: Check if we\'re accessing the ignition point',
            'if x == 395 and y == 377 and z == 0:',
            'print(f"🔍 DEBUG:'
        ]):
            continue
        
        # Skip the print statements that follow the debug conditions
        if line.strip().startswith('print(f"🔍 DEBUG:'):
            continue
            
        cleaned_lines.append(line)
    
    # Write back the cleaned content
    with open('src/core/forest_model.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(cleaned_lines))
    
    print("✅ Debug output removed from forest_model.py")

if __name__ == "__main__":
    remove_debug_output()
