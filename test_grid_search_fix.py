#!/usr/bin/env python3
"""
Test script to verify the grid search fix for the list.items() error
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_worker_function_fix():
    """Test that the worker function fix works correctly."""
    print("🧪 Testing worker function fix...")
    
    try:
        from src.core.calibration.grid_search import evaluate_worker_function
        from src.config.config_tools import ModelConfig
        
        # Create a test config
        config = ModelConfig(
            grid_size=(10, 10),
            num_layers=2,
            max_steps=5,
            simulation_type='memory_optimized',
            spread_probability=0.8,
            fuel_consumption_rate=0.01,
            ignition_threshold=0.1,
            stop_when_fire_extinguished=False
        )
        
        # Test parameters (same as in your debug logs)
        params = {
            'spread_probability': 0.4,
            'fuel_consumption_rate': 0.050050000000000004,
            'ember_probability': 0.2,
            'ember_ignition': 0.35,
            'fuel_moisture_baseline': 0.1
        }
        
        print(f"Testing with parameters: {params}")
        
        result = evaluate_worker_function(
            parameter_values=params,
            target_data=None,
            config_dict=config.__dict__,
            objective_function_name="SpatialSimilarityObjective"
        )
        
        print(f"✅ Worker function completed successfully")
        print(f"   Objective value: {result.get('objective_value', 'N/A')}")
        print(f"   Is valid: {result.get('is_valid', 'N/A')}")
        print(f"   Error message: {result.get('error_message', 'N/A')}")
        
        return result.get('is_valid', False)
        
    except Exception as e:
        print(f"❌ Worker function test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_config_dict_creation():
    """Test that config_dict creation works correctly."""
    print("\n🧪 Testing config_dict creation...")
    
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
            experiment_name="test_config_dict_fix",
            method=CalibrationMethod.GRID_SEARCH,
            base_config=base_config,
            calibration_parameters=['spread_probability'],
            grid_search_points=2
        )
        
        # Get parameter bounds and objective function
        parameter_bounds = get_default_calibration_bounds()
        objective_function = SpatialSimilarityObjective()
        
        # Test creating the calibrator
        calibrator = GridSearchCalibrator(
            calibration_config=calibration_config,
            parameter_bounds=parameter_bounds,
            objective_function=objective_function,
            parallel_execution=False  # Use sequential for testing
        )
        
        print(f"✅ GridSearchCalibrator created successfully")
        print(f"   Total combinations: {calibrator.total_combinations}")
        
        # Test config_dict creation
        base_config_variant = calibration_config.create_config_variant({})
        print(f"   Base config variant type: {type(base_config_variant)}")
        
        # Test the config_dict creation logic
        if isinstance(base_config_variant, dict):
            config_dict = base_config_variant
        elif hasattr(base_config_variant, '__dict__'):
            try:
                from dataclasses import asdict
                config_dict = asdict(base_config_variant)
                print(f"   Converted using asdict()")
            except Exception as e:
                print(f"   asdict() failed: {e}")
                config_dict = base_config_variant.__dict__
                print(f"   Using __dict__")
        else:
            config_dict = {}
        
        print(f"   Config dict type: {type(config_dict)}")
        print(f"   Config dict keys: {list(config_dict.keys()) if isinstance(config_dict, dict) else 'not a dict'}")
        
        return isinstance(config_dict, dict) and len(config_dict) > 0
        
    except Exception as e:
        print(f"❌ Config dict creation test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all tests."""
    print("🔧 Testing Grid Search Fix")
    print("=" * 50)
    
    tests = [
        ("Worker Function Fix", test_worker_function_fix),
        ("Config Dict Creation", test_config_dict_creation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            success = test_func()
            results[test_name] = success
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status}")
        except Exception as e:
            print(f"❌ FAILED with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'=' * 50}")
    print("TEST SUMMARY")
    print(f"{'=' * 50}")
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The grid search fix is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. The fix may need further refinement.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
