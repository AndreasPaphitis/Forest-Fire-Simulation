#!/usr/bin/env python3
"""
Test script to verify memory leak fix in grid search calibration.

This script runs a small grid search to test if the memory cleanup
mechanisms are working properly.
"""

import os
import sys
import time
import gc
import psutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def monitor_memory():
    """Monitor current memory usage."""
    process = psutil.Process()
    memory_info = process.memory_info()
    return memory_info.rss / (1024**3)  # Convert to GB

def test_memory_leak_fix():
    """Test the memory leak fix by running a small grid search."""
    print("🧪 Testing Memory Leak Fix")
    print("=" * 50)
    
    try:
        from src.core.calibration.grid_search import GridSearchCalibrator
        from src.core.calibration.parameter_bounds import ParameterBounds
        from src.core.calibration.objective_functions import SpatialSimilarityObjective
        from src.config.calibration_config import CalibrationConfig
        
        # Create a minimal configuration for testing
        config = CalibrationConfig()
        config.grid_search_points = 2  # Very small grid for testing
        config.base_config.grid.width = 100
        config.base_config.grid.height = 100
        config.base_config.grid.num_layers = 5
        
        # Create parameter bounds
        parameter_bounds = {
            'wind_speed': ParameterBounds(min_value=1.0, max_value=5.0),
            'wind_direction': ParameterBounds(min_value=0.0, max_value=360.0)
        }
        
        # Create objective function
        objective_function = SpatialSimilarityObjective()
        
        # Create calibrator
        calibrator = GridSearchCalibrator(
            calibration_config=config,
            parameter_bounds=parameter_bounds,
            objective_function=objective_function,
            parallel_execution=False,  # Use sequential for testing
            max_workers=1
        )
        
        print(f"📊 Grid search will evaluate {calibrator.total_combinations} combinations")
        
        # Monitor memory before
        initial_memory = monitor_memory()
        print(f"💾 Initial memory usage: {initial_memory:.2f} GB")
        
        # Run grid search
        print("🚀 Starting grid search...")
        start_time = time.time()
        
        results = calibrator.run_calibration(target_data={})
        
        end_time = time.time()
        
        # Monitor memory after
        final_memory = monitor_memory()
        memory_increase = final_memory - initial_memory
        
        print(f"✅ Grid search completed in {end_time - start_time:.2f} seconds")
        print(f"💾 Final memory usage: {final_memory:.2f} GB")
        print(f"📈 Memory increase: {memory_increase:.2f} GB")
        
        # Force garbage collection
        collected = gc.collect()
        print(f"🗑️  Garbage collection freed {collected} objects")
        
        # Check memory after garbage collection
        post_gc_memory = monitor_memory()
        print(f"💾 Memory after GC: {post_gc_memory:.2f} GB")
        
        # Test cleanup
        print("🧹 Testing cleanup...")
        calibrator.cleanup()
        
        # Check memory after cleanup
        post_cleanup_memory = monitor_memory()
        print(f"💾 Memory after cleanup: {post_cleanup_memory:.2f} GB")
        
        # Evaluate results
        if memory_increase < 0.5:  # Less than 500MB increase
            print("✅ MEMORY LEAK FIX SUCCESSFUL - Memory usage is stable")
            return True
        else:
            print("❌ MEMORY LEAK DETECTED - Memory usage increased significantly")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_memory_leak_fix()
    sys.exit(0 if success else 1)
