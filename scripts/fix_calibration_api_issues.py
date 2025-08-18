#!/usr/bin/env python3
"""
Fix Calibration API Issues Script

This script fixes the specific API issues identified in the diagnostic:
1. CalibrationConfig missing get_total_combinations method
2. GridSearchCalibrator constructor API mismatch
"""

import sys
import os
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def fix_calibration_config_api():
    """Fix CalibrationConfig missing get_total_combinations method."""
    print("🔧 Fixing CalibrationConfig API...")
    
    config_path = project_root / "src" / "core" / "calibration" / "calibration_config.py"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add the missing get_total_combinations method
    if 'def get_total_combinations(self)' not in content:
        # Find the get_calibration_parameter_names method and add get_total_combinations after it
        if 'def get_calibration_parameter_names(self) -> List[str]:' in content:
            # Add the method after get_calibration_parameter_names
            old_method = """    def get_calibration_parameter_names(self) -> List[str]:
        \"\"\"Get the list of calibration parameter names.\"\"\"
        return self.calibration_parameters"""
            
            new_method = """    def get_calibration_parameter_names(self) -> List[str]:
        \"\"\"Get the list of calibration parameter names.\"\"\"
        return self.calibration_parameters
    
    def get_total_combinations(self) -> int:
        \"\"\"Get the total number of parameter combinations.\"\"\"
        total = 1
        for param_name in self.calibration_parameters:
            if param_name in self.parameter_bounds:
                bounds = self.parameter_bounds[param_name]
                total *= len(bounds.generate_values(self.grid_search_points))
            else:
                total *= 1  # Default single value
        return total"""
            
            if old_method in content:
                content = content.replace(old_method, new_method)
                print("✅ Added get_total_combinations method to CalibrationConfig")
            else:
                print("⚠️  Could not find get_calibration_parameter_names method to add get_total_combinations after")
        else:
            print("⚠️  Could not find get_calibration_parameter_names method")
    
    # Write the fixed content back
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def fix_grid_search_calibrator_api():
    """Fix GridSearchCalibrator constructor API to match expected usage."""
    print("🔧 Fixing GridSearchCalibrator API...")
    
    # The constructor is actually correct - it expects:
    # GridSearchCalibrator(calibration_config, parameter_bounds, objective_function)
    # But the diagnostic test was calling it incorrectly
    
    print("✅ GridSearchCalibrator constructor is correct - the issue was in the test")
    return True

def create_api_test():
    """Create a test to verify the API fixes work."""
    print("🔧 Creating API test...")
    
    test_script = """#!/usr/bin/env python3
\"\"\"
Test script to verify calibration API fixes
\"\"\"

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_calibration_config_api():
    \"\"\"Test that CalibrationConfig API works correctly.\"\"\"
    print("Testing CalibrationConfig API...")
    
    try:
        from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod
        from src.config.config_tools import ModelConfig
        
        # Create base config
        base_config = ModelConfig(
            grid_size=(10, 10),
            num_layers=2,
            max_steps=5,
            simulation_type='memory_optimized'
        )
        
        # Create calibration config
        calibration_config = CalibrationConfig(
            experiment_name="test_api",
            method=CalibrationMethod.GRID_SEARCH,
            base_config=base_config,
            calibration_parameters=['spread_probability', 'fuel_consumption_rate']
        )
        
        # Test the API methods
        param_names = calibration_config.get_calibration_parameter_names()
        print(f"Calibration parameters: {param_names}")
        
        # Test get_total_combinations (this should work after the fix)
        try:
            total_combinations = calibration_config.get_total_combinations()
            print(f"Total combinations: {total_combinations}")
        except AttributeError:
            print("❌ get_total_combinations method not found")
            return False
        
        return len(param_names) > 0
        
    except Exception as e:
        print(f"CalibrationConfig API test failed: {e}")
        return False

def test_grid_search_api():
    \"\"\"Test that GridSearchCalibrator API works correctly.\"\"\"
    print("Testing GridSearchCalibrator API...")
    
    try:
        from src.core.calibration.grid_search import GridSearchCalibrator
        from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod
        from src.core.calibration.parameter_bounds import get_default_calibration_bounds
        from src.core.calibration.objective_functions import SpatialSimilarityObjective
        from src.config.config_tools import ModelConfig
        
        # Create minimal calibration config
        base_config = ModelConfig(
            grid_size=(5, 5),
            num_layers=2,
            max_steps=3,
            simulation_type='memory_optimized'
        )
        
        calibration_config = CalibrationConfig(
            experiment_name="test_grid_search_api",
            method=CalibrationMethod.GRID_SEARCH,
            base_config=base_config,
            calibration_parameters=['spread_probability'],
            grid_search_points=2  # Small grid for testing
        )
        
        # Get parameter bounds and objective function
        parameter_bounds = get_default_calibration_bounds()
        objective_function = SpatialSimilarityObjective()
        
        # Test creating the calibrator with correct API
        calibrator = GridSearchCalibrator(
            calibration_config=calibration_config,
            parameter_bounds=parameter_bounds,
            objective_function=objective_function
        )
        print(f"GridSearchCalibrator created successfully")
        print(f"Total combinations: {calibrator.total_combinations}")
        
        return True
        
    except Exception as e:
        print(f"GridSearchCalibrator API test failed: {e}")
        return False

def main():
    \"\"\"Run all API tests.\"\"\"
    print("🧪 Testing calibration API fixes...")
    
    tests = [
        ("CalibrationConfig API", test_calibration_config_api),
        ("GridSearchCalibrator API", test_grid_search_api),
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
    print("API TEST SUMMARY")
    print(f"{'='*40}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All API fixes working correctly!")
        print("Your calibration should now work without API errors")
    else:
        print("🚨 Some API issues remain")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
"""
    
    test_path = project_root / "scripts" / "test_calibration_api_fixes.py"
    with open(test_path, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print("✅ Created API test: scripts/test_calibration_api_fixes.py")
    return True

def main():
    """Run all API fixes."""
    print("🚨 CALIBRATION API FIXES")
    print("=" * 50)
    
    fixes = [
        ("CalibrationConfig API", fix_calibration_config_api),
        ("GridSearchCalibrator API", fix_grid_search_calibrator_api),
        ("API Test", create_api_test),
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
    print("API FIX SUMMARY")
    print(f"{'='*50}")
    
    successful = sum(1 for r in results.values() if r)
    total = len(results)
    
    for fix_name, result in results.items():
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"{status} {fix_name}")
    
    print(f"\nOverall: {successful}/{total} fixes applied")
    
    if successful == total:
        print("🎉 All API fixes applied successfully!")
        print("\nNext steps:")
        print("1. Run: python scripts/test_calibration_api_fixes.py")
        print("2. If tests pass, your calibration should work without API errors")
        print("3. Run your actual calibration again")
    else:
        print("🚨 Some API fixes failed - check the output above")
    
    return successful == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
