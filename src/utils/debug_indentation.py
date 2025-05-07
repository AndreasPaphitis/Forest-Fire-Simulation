#!/usr/bin/env python

"""
Debug script to analyze indentation in a Python file.
This will print out each line and the number of spaces at the beginning.
"""

import sys
import os

def analyze_indentation(filename, start_line, end_line):
    """Analyze indentation in the given file between lines start_line and end_line."""
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return
    
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    start_line = max(1, start_line)
    end_line = min(len(lines), end_line)
    
    print(f"Analyzing indentation in {filename} from line {start_line} to {end_line}")
    print("=" * 60)
    print("Line #  |  Spaces  |  Content")
    print("-" * 60)
    
    for i in range(start_line - 1, end_line):
        line = lines[i]
        leading_spaces = len(line) - len(line.lstrip(' '))
        print(f"{i+1:6d}  |  {leading_spaces:7d}  |  {line.rstrip()}")
    
    print("=" * 60)

if __name__ == "__main__":
    analyze_indentation("vegetation data integration.py", 1045, 1065) 