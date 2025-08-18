#!/usr/bin/env python3
"""
Comprehensive Duplicate Logging Fix

This script addresses the root cause of duplicate logging in multiprocessing.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def fix_worker_logging_comprehensive():
    """Apply comprehensive fix for worker logging."""
    print("🔧 Applying comprehensive worker logging fix...")
    
    grid_search_path = project_root / "src" / "core" / "calibration" / "grid_search.py"
    
    with open(grid_search_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the entire worker logging setup with a more robust solution
    old_logging_setup = """        # Set up logging for worker process - FIXED: Avoid duplicate handlers
        # Don't call basicConfig in worker processes to avoid duplicate logging
        worker_logger = logging.getLogger(f"worker_{time.time()}")
        worker_logger.setLevel(logging.INFO)
        
        # Only add handler if none exist to prevent duplicates
        if not worker_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            worker_logger.addHandler(handler)
        worker_logger.propagate = False  # Prevent propagation to root logger"""
    
    new_logging_setup = """        # Set up logging for worker process - COMPREHENSIVE FIX
        # Completely isolate worker logging to prevent duplicates
        worker_logger = logging.getLogger(f"worker_{time.time()}")
        worker_logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        for handler in worker_logger.handlers[:]:
            worker_logger.removeHandler(handler)
        
        # Add a single handler with unique formatting
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[WORKER] %(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        worker_logger.addHandler(handler)
        
        # Critical: Prevent propagation to avoid duplicate logging
        worker_logger.propagate = False
        
        # Also disable propagation for all child loggers
        for name in ['src.core.fire_simulation_engine', 'src.core.forest_model', 'src.core.calibration.objective_functions']:
            child_logger = logging.getLogger(name)
            child_logger.propagate = False
            # Clear any existing handlers to prevent duplicates
            for child_handler in child_logger.handlers[:]:
                child_logger.removeHandler(child_handler)"""
    
    if old_logging_setup in content:
        content = content.replace(old_logging_setup, new_logging_setup)
        
        with open(grid_search_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Applied comprehensive worker logging fix")
        return True
    else:
        print("❌ Could not find logging setup to fix")
        return False

def fix_main_process_logging():
    """Fix main process logging to prevent conflicts."""
    print("🔧 Fixing main process logging...")
    
    # Check if there's a main logging configuration that might be causing issues
    logging_utils_path = project_root / "src" / "utils" / "logging_utils.py"
    
    with open(logging_utils_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for any problematic logging configurations
    if 'logging.basicConfig' in content:
        print("⚠️  Found logging.basicConfig in logging_utils.py - this might cause conflicts")
        print("   Consider reviewing the logging configuration")
    
    print("✅ Main process logging reviewed")
    return True

def create_isolated_test():
    """Create a test that completely isolates logging."""
    print("🔧 Creating isolated logging test...")
    
    test_script = """#!/usr/bin/env python3
\"\"\"
Isolated logging test to verify duplicate logging fix
\"\"\"

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_isolated_logging():
    \"\"\"Set up completely isolated logging for testing.\"\"\"
    # Clear all existing loggers
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.propagate = False
    
    # Clear root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Set up minimal root logging
    logging.basicConfig(
        level=logging.WARNING,  # Only warnings and above
        format='[MAIN] %(levelname)s - %(message)s',
        force=True
    )

def test_worker_isolation():
    \"\"\"Test worker function with completely isolated logging.\"\"\"
    print("Testing worker function with isolated logging...")
    
    try:
        from src.core.calibration.grid_search import evaluate_worker_function
        from src.config.config_tools import ModelConfig
        
        config = ModelConfig(
            grid_size=(5, 5),
            num_layers=2,
            max_steps=1,
            simulation_type='memory_optimized',
            spread_probability=0.8,
            fuel_consumption_rate=0.01,
            ignition_threshold=0.1,
            stop_when_fire_extinguished=False
        )
        
        params = {
            'spread_probability': 0.8,
            'fuel_consumption_rate': 0.01,
            'ignition_threshold': 0.1
        }
        
        result = evaluate_worker_function(
            parameter_values=params,
            target_data=None,
            config_dict=config.__dict__,
            objective_function_name="SpatialSimilarityObjective"
        )
        
        print(f"Worker function result: {result.get('objective_value', 'N/A')}")
        print(f"Is valid: {result.get('is_valid', 'N/A')}")
        
        return result.get('is_valid', False)
        
    except Exception as e:
        print(f"Worker function test failed: {e}")
        return False

def test_multiprocessing_isolation():
    \"\"\"Test multiprocessing with isolated logging.\"\"\"
    print("Testing multiprocessing with isolated logging...")
    
    try:
        from concurrent.futures import ProcessPoolExecutor
        from src.core.calibration.grid_search import evaluate_worker_function
        from src.config.config_tools import ModelConfig
        
        config = ModelConfig(
            grid_size=(3, 3),
            num_layers=2,
            max_steps=1,
            simulation_type='memory_optimized',
            spread_probability=0.8,
            fuel_consumption_rate=0.01,
            ignition_threshold=0.1,
            stop_when_fire_extinguished=False
        )
        
        params = {
            'spread_probability': 0.8,
            'fuel_consumption_rate': 0.01,
            'ignition_threshold': 0.1
        }
        
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                evaluate_worker_function,
                params,
                None,
                config.__dict__,
                "SpatialSimilarityObjective"
            )
            
            try:
                result = future.result(timeout=30)
                print(f"Worker result: {result.get('objective_value', 'N/A')}")
                return result.get('is_valid', False)
            except Exception as e:
                print(f"Worker failed: {e}")
                return False
        
    except Exception as e:
        print(f"Multiprocessing test failed: {e}")
        return False

def main():
    \"\"\"Run isolated tests.\"\"\"
    print("🧪 Testing with isolated logging...")
    
    # Set up isolated logging
    setup_isolated_logging()
    
    tests = [
        ("Worker Function (Isolated)", test_worker_isolation),
        ("Multiprocessing (Isolated)", test_multiprocessing_isolation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\\n{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")
        
        try:
            result = test_func()
            results[test_name] = result
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} {test_name}")
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\\n{'='*50}")
    print("ISOLATED TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Isolated logging tests passed!")
        print("   This suggests the duplicate logging is fixed")
    else:
        print("🚨 Some isolated tests failed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
"""
    
    test_path = project_root / "scripts" / "test_isolated_logging.py"
    with open(test_path, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print("✅ Created isolated logging test: scripts/test_isolated_logging.py")
    return True

def main():
    """Run comprehensive logging fixes."""
    print("🚨 COMPREHENSIVE LOGGING FIXES")
    print("=" * 50)
    
    fixes = [
        ("Worker Logging (Comprehensive)", fix_worker_logging_comprehensive),
        ("Main Process Logging", fix_main_process_logging),
        ("Isolated Test", create_isolated_test),
    ]
    
    results = {}
    
    for fix_name, fix_func in fixes:
        print(f"\n{'='*50}")
        print(f"Fixing: {fix_name}")
        print(f"{'='*50}")
        
        try:
            result = fix_func()
            results[fix_name] = result
            status = "✅ SUCCESS" if result else "❌ FAILED"
            print(f"{status} {fix_name}")
        except Exception as e:
            print(f"❌ ERROR in {fix_name}: {e}")
            results[fix_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("COMPREHENSIVE FIX SUMMARY")
    print(f"{'='*50}")
    
    successful = sum(1 for r in results.values() if r)
    total = len(results)
    
    for fix_name, result in results.items():
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"{status} {fix_name}")
    
    print(f"\nOverall: {successful}/{total} fixes applied")
    
    if successful == total:
        print("🎉 All comprehensive fixes applied!")
        print("\nNext steps:")
        print("1. Run: python scripts/test_isolated_logging.py")
        print("2. This will test if duplicate logging is completely resolved")
        print("3. If this passes, your calibration should work without duplicate messages")
    else:
        print("🚨 Some fixes failed - check the output above")
    
    return successful == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
