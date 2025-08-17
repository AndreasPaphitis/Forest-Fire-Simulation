#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for quiet mode progress updates.
"""

import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts.run_tenerife_calibration import create_quiet_progress_callback

def test_quiet_progress():
    """Test the quiet progress callback functionality."""
    
    print("🧪 Testing Quiet Mode Progress Updates")
    print("=" * 50)
    
    # Create a test progress callback
    total_combinations = 100
    progress_callback = create_quiet_progress_callback(total_combinations, quiet_mode=True)
    
    # Simulate calibration progress
    print("Simulating calibration with 100 combinations...")
    print("Progress updates should appear every 30 seconds or 5 completions")
    print()
    
    for i in range(1, total_combinations + 1):
        # Simulate a result
        class MockResult:
            def __init__(self, valid=True, value=0.5):
                self.is_valid = valid
                self.objective_value = value
        
        result = MockResult(valid=True, value=0.5 + (i % 10) * 0.1)
        
        # Call the progress callback
        progress_callback(i, total_combinations, result)
        
        # Simulate some processing time
        time.sleep(0.1)  # 100ms per simulation
    
    print("\n✅ Test completed!")
    print("In real calibration, you would see:")
    print("- Progress percentage and completion count")
    print("- Best objective value so far")
    print("- Estimated time remaining")
    print("- Updates every 30 seconds or 5 completions")

if __name__ == "__main__":
    test_quiet_progress()
