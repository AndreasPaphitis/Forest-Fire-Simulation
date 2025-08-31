#!/usr/bin/env python3
"""
Test script to verify reduced logging output
"""

import logging
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set up minimal logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)

# Set specific loggers to WARNING level
logging.getLogger('src.core.forest_model').setLevel(logging.WARNING)
logging.getLogger('src.core.calibration').setLevel(logging.WARNING)
logging.getLogger('src.core.fire_simulation_engine').setLevel(logging.WARNING)
logging.getLogger('src.utils.lidar_utils').setLevel(logging.WARNING)
logging.getLogger('src.utils.terrain_preprocessor').setLevel(logging.WARNING)

def test_logging_levels():
    """Test that logging levels are properly set"""
    print("Testing logging levels...")
    
    # Test forest model logger
    forest_logger = logging.getLogger('src.core.forest_model')
    print(f"Forest model logger level: {forest_logger.level} ({logging.getLevelName(forest_logger.level)})")
    
    # Test calibration logger
    calib_logger = logging.getLogger('src.core.calibration')
    print(f"Calibration logger level: {calib_logger.level} ({logging.getLevelName(calib_logger.level)})")
    
    # Test that debug messages are suppressed
    print("\nTesting message suppression...")
    forest_logger.debug("This debug message should NOT appear")
    forest_logger.info("This info message should NOT appear")
    forest_logger.warning("This warning message SHOULD appear")
    forest_logger.error("This error message SHOULD appear")
    
    print("\n✅ Logging levels configured for reduced output")

if __name__ == "__main__":
    test_logging_levels()
