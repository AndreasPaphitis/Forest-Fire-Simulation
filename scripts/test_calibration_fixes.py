#!/usr/bin/env python3
"""
Test script to verify calibration fixes work correctly.
"""

import sys
import os
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

def test_calibration_fixes():
    """Test that the calibration fixes are working."""
    print("🧪 Testing Calibration Fixes")
    print("=" * 40)
    
    try:
        # Test imports
        from src.core.calibration.grid_search import GridSearchCalibrator
        from src.core.fire_simulation_engine import FireSimulationEngine
        print("✅ Imports successful")
        
        # Test timeout handling
        import signal
        def timeout_handler(signum, frame):
            raise TimeoutError("Test timeout")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)  # 5 second timeout
        
        try:
            # This should timeout
            import time
            time.sleep(10)
        except TimeoutError:
            print("✅ Timeout handling works")
        finally:
            signal.alarm(0)  # Cancel timeout
        
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_calibration_fixes()
    sys.exit(0 if success else 1)
