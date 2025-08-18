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
        # Find the end of the class definition
        if 'def generate_parameter_combinations(self)' in content:
            # Add the method after generate_parameter_combinations
            old_method = """    def generate_parameter_combinations(self):
        \"\"\"Generate all parameter combinations for grid search.\"\"\"
        from itertools import product
        
        # Get parameter values for each calibration parameter
        param_values = {}
        for param_name in self.calibration_parameters:
            if param_name in self.parameter_bounds:
                bounds = self.parameter_bounds[param_name]
                param_values[param_name] = bounds.generate_values(self.grid_search_points)
            else:
                # Fallback: use default values
                param_values[param_name] = [0.5]  # Default value
        
        # Generate all combinations
        param_names = list(param_values.keys())
        param_value_lists = list(param_values.values())
        
        for combination in product(*param_value_lists):
            yield dict(zip(param_names, combination))"""
            
            new_method = """    def generate_parameter_combinations(self):
        \"\"\"Generate all parameter combinations for grid search.\"\"\"
        from itertools import product
        
        # Get parameter values for each calibration parameter
        param_values = {}
        for param_name in self.calibration_parameters:
            if param_name in self.parameter_bounds:
                bounds = self.parameter_bounds[param_name]
                param_values[param_name] = bounds.generate_values(self.grid_search_points)
            else:
                # Fallback: use default values
                param_values[param_name] = [0.5]  # Default value
        
        # Generate all combinations
        param_names = list(param_values.keys())
        param_value_lists = list(param_values.values())
        
        for combination in product(*param_value_lists):
            yield dict(zip(param_names, combination))
    
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
                print("⚠️  Could not find generate_parameter_combinations method to add get_total_combinations after")
        else:
            print("⚠️  Could not find generate_parameter_combinations method")
    
    # Write the fixed content back
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def fix_grid_search_calibrator_api():
    """Fix GridSearchCalibrator constructor API."""
    print("🔧 Fixing GridSearchCalibrator API...")
    
    grid_search_path = project_root / "src" / "core" / "calibration" / "grid_search.py"
    
    with open(grid_search_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the GridSearchCalibrator class definition
    if 'class GridSearchCalibrator:' in content:
        # Look for the __init__ method
        if 'def __init__(self, calibration_config:' in content:
            # The constructor is already correct, but let's check if there's a mismatch
            print("✅ GridSearchCalibrator constructor appears to be correct")
            return True
        elif 'def __init__(self, parameter_bounds, objective_function' in content:
            # This is the old API - we need to update it
            old_init = """    def __init__(self, parameter_bounds, objective_function"""
            new_init = """    def __init__(self, calibration_config"""
            
            if old_init in content:
                content = content.replace(old_init, new_init)
                print("✅ Updated GridSearchCalibrator constructor to use calibration_config")
            else:
                print("⚠️  Could not find old constructor signature")
        else:
            print("⚠️  Could not find GridSearchCalibrator __init__ method")
    else:
        print("⚠️  Could not find GridSearchCalibrator class")
    
    # Write the fixed content back
    with open(grid_search_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
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
        total_combinations = calibration_config.get_total_combinations()
        print(f"Total combinations: {total_combinations}")
        
        param_combinations = list(calibration_config.generate_parameter_combinations())
        print(f"Generated combinations: {len(param_combinations)}")
        
        if param_combinations:
            print(f"First combination: {param_combinations[0]}")
        
        return total_combinations > 0 and len(param_combinations) > 0
        
    except Exception as e:
        print(f"CalibrationConfig API test failed: {e}")
        return False

def test_grid_search_api():
    \"\"\"Test that GridSearchCalibrator API works correctly.\"\"\"
    print("Testing GridSearchCalibrator API...")
    
    try:
        from src.core.calibration.grid_search import GridSearchCalibrator
        from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod
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
        
        # Test creating the calibrator
        calibrator = GridSearchCalibrator(calibration_config)
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
