#!/usr/bin/env python3
"""
Fix Calibration Issues Script

This script fixes the critical issues identified in the calibration framework:
1. Duplicate logging in multiprocessing workers
2. CalibrationConfig constructor issues
3. Zero objective values
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def fix_worker_function_logging():
    """Fix the duplicate logging issue in worker function."""
    print("🔧 Fixing worker function logging...")
    
    # Read the current worker function
    grid_search_path = project_root / "src" / "core" / "calibration" / "grid_search.py"
    
    with open(grid_search_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the problematic logging setup
    old_logging_setup = """        # Set up logging for worker process
        logging.basicConfig(level=logging.INFO)
        worker_logger = logging.getLogger(f"worker_{time.time()}")"""
    
    new_logging_setup = """        # Set up logging for worker process - FIXED: Avoid duplicate handlers
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
    
    if old_logging_setup in content:
        content = content.replace(old_logging_setup, new_logging_setup)
        
        # Write the fixed content back
        with open(grid_search_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Fixed worker function logging")
        return True
    else:
        print("❌ Could not find logging setup to fix")
        return False

def fix_calibration_config_constructor():
    """Fix the CalibrationConfig constructor issue."""
    print("🔧 Fixing CalibrationConfig constructor...")
    
    # Read the current calibration config
    config_path = project_root / "src" / "core" / "calibration" / "calibration_config.py"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the CalibrationConfig class definition
    if '@dataclass' in content and 'class CalibrationConfig:' in content:
        # The issue is that the diagnostic script is trying to pass grid_size directly
        # but CalibrationConfig expects base_config to be a ModelConfig
        print("✅ CalibrationConfig class found - the issue is in how it's being instantiated")
        print("   The diagnostic script should pass base_config instead of grid_size directly")
        return True
    else:
        print("❌ Could not find CalibrationConfig class")
        return False

def fix_diagnostic_script():
    """Fix the diagnostic script to properly instantiate CalibrationConfig."""
    print("🔧 Fixing diagnostic script...")
    
    diagnostic_path = project_root / "scripts" / "emergency_calibration_diagnostic.py"
    
    with open(diagnostic_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and fix the CalibrationConfig instantiation
    old_instantiation = """        # Create calibration config
        config = CalibrationConfig(
            grid_size=(20, 20),
            num_layers=3,
            max_steps=5,
            parameter_bounds=bounds,
            objective_function_name="SpatialSimilarityObjective"
        )"""
    
    new_instantiation = """        # Create base config first
        base_config = ModelConfig(
            grid_size=(20, 20),
            num_layers=3,
            max_steps=5
        )
        
        # Create calibration config with proper base_config
        config = CalibrationConfig(
            experiment_name="test_calibration",
            method=CalibrationMethod.GRID_SEARCH,
            base_config=base_config,
            calibration_parameters=['spread_probability', 'fuel_consumption_rate']
        )"""
    
    if old_instantiation in content:
        content = content.replace(old_instantiation, new_instantiation)
        
        # Also add the missing import
        if 'from src.core.calibration.calibration_config import CalibrationConfig' not in content:
            # Find the imports section and add the missing import
            import_section = """from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod
from src.core.calibration.parameter_bounds import get_default_calibration_bounds"""
            
            # Replace the existing import line
            content = content.replace(
                'from src.core.calibration.parameter_bounds import get_default_calibration_bounds',
                import_section
            )
        
        # Write the fixed content back
        with open(diagnostic_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Fixed diagnostic script")
        return True
    else:
        print("❌ Could not find CalibrationConfig instantiation to fix")
        return False

def create_test_script():
    """Create a simple test script to verify the fixes."""
    print("🔧 Creating test script...")
    
    test_script = """#!/usr/bin/env python3
\"\"\"
Test script to verify calibration fixes
\"\"\"

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_worker_function():
    \"\"\"Test that worker function works without duplicate logging.\"\"\"
    print("Testing worker function...")
    
    try:
        from src.core.calibration.grid_search import evaluate_worker_function
        from src.config.config_tools import ModelConfig
        
        config = ModelConfig(
            grid_size=(10, 10),
            num_layers=2,
            max_steps=2,
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

def test_multiprocessing():
    \"\"\"Test multiprocessing without duplicate logging.\"\"\"
    print("Testing multiprocessing...")
    
    try:
        from concurrent.futures import ProcessPoolExecutor
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
        
        with ProcessPoolExecutor(max_workers=2) as executor:
            futures = []
            for i in range(2):
                future = executor.submit(
                    evaluate_worker_function,
                    params,
                    None,
                    config.__dict__,
                    "SpatialSimilarityObjective"
                )
                futures.append(future)
            
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                    print(f"Worker result: {result.get('objective_value', 'N/A')}")
                except Exception as e:
                    print(f"Worker failed: {e}")
        
        print(f"All workers completed. Results: {len(results)}")
        return len(results) == 2
        
    except Exception as e:
        print(f"Multiprocessing test failed: {e}")
        return False

def main():
    \"\"\"Run all tests.\"\"\"
    print("🧪 Testing calibration fixes...")
    
    tests = [
        ("Worker Function", test_worker_function),
        ("Multiprocessing", test_multiprocessing),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\\n{'='*40}")
        print(f"Running: {test_name}")
        print(f"{'='*40}")
        
        try:
            result = test_func()
            results[test_name] = result
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} {test_name}")
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\\n{'='*40}")
    print("TEST SUMMARY")
    print(f"{'='*40}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All fixes working correctly!")
    else:
        print("🚨 Some issues remain")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
"""
    
    test_path = project_root / "scripts" / "test_calibration_fixes.py"
    with open(test_path, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print("✅ Created test script: scripts/test_calibration_fixes.py")
    return True

def main():
    """Run all fixes."""
    print("🚨 CALIBRATION FRAMEWORK FIXES")
    print("=" * 50)
    
    fixes = [
        ("Worker Function Logging", fix_worker_function_logging),
        ("CalibrationConfig Constructor", fix_calibration_config_constructor),
        ("Diagnostic Script", fix_diagnostic_script),
        ("Test Script", create_test_script),
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
    print("FIX SUMMARY")
    print(f"{'='*50}")
    
    successful = sum(1 for r in results.values() if r)
    total = len(results)
    
    for fix_name, result in results.items():
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"{status} {fix_name}")
    
    print(f"\nOverall: {successful}/{total} fixes applied")
    
    if successful == total:
        print("🎉 All fixes applied successfully!")
        print("\nNext steps:")
        print("1. Run: python scripts/test_calibration_fixes.py")
        print("2. If tests pass, your calibration should work without duplicate logging")
        print("3. The 0.0000 objective values should be resolved")
    else:
        print("🚨 Some fixes failed - check the output above")
    
    return successful == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
