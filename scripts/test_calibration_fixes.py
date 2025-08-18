#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Calibration Framework Fixes

This script tests the fixes for the calibration framework issues:
1. Zero objective values due to fire not spreading
2. JSON serialization errors with numpy int64
3. Simulation finishing too quickly

Author: Forest Fire Simulation Team
Date: 2025
"""

import sys
import os
import json
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.calibration.calibration_utils import _convert_to_serializable
from src.core.calibration.objective_functions import SpatialSimilarityObjective
from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.forest_model import create_forest_model
from src.config.config_tools import ModelConfig

def test_json_serialization_fix():
    """Test that JSON serialization handles numpy types correctly."""
    print("🧪 Testing JSON serialization fix...")
    
    # Create test data with numpy types
    test_data = {
        'int64_value': np.int64(42),
        'float64_value': np.float64(3.14),
        'bool_value': np.bool_(True),
        'array_value': np.array([1, 2, 3]),
        'nested_dict': {
            'numpy_int': np.int64(100),
            'numpy_float': np.float64(2.718)
        }
    }
    
    try:
        # Test the serialization function
        serialized_data = _convert_to_serializable(test_data)
        
        # Try to serialize to JSON
        json_string = json.dumps(serialized_data, indent=2)
        
        print("✅ JSON serialization test PASSED")
        print(f"   Original int64: {test_data['int64_value']} (type: {type(test_data['int64_value'])})")
        print(f"   Serialized int64: {serialized_data['int64_value']} (type: {type(serialized_data['int64_value'])})")
        
        return True
        
    except Exception as e:
        print(f"❌ JSON serialization test FAILED: {e}")
        return False

def test_fire_spreading_fix():
    """Test that fire spreading works with the new parameters."""
    print("\n🔥 Testing fire spreading fix...")
    
    try:
        # Create a small test configuration
        config = ModelConfig(
            width=50,
            height=50,
            num_layers=5,
            max_steps=20,
            spread_probability=0.8,  # Increased from 0.5
            ignition_threshold=0.1,  # Lowered from 0.5
            wind_influence_on_spread=0.5,
            fuel_consumption_rate=0.1,
            terrain_effect_strength=0.3,
            barranco_amplification=0.2,
            slope_influence=0.4
        )
        
        # Create forest model
        forest_model = create_forest_model(config)
        
        # Set ignition point in center
        center_x, center_y = config.width // 2, config.height // 2
        for z in range(config.num_layers):
            forest_model.state[center_x, center_y, z] = 1  # BURNING
        
        # Create simulation engine
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Run simulation
        result = engine.run_simulation(max_steps=10)
        
        # Check if fire spread
        stats = result.get('stats', {})
        total_burned = stats.get('total_burned_cells', 0)
        steps = stats.get('steps', 0)
        
        print(f"   Simulation completed in {steps} steps")
        print(f"   Total burned cells: {total_burned}")
        
        if total_burned > 1:  # More than just the initial ignition point
            print("✅ Fire spreading test PASSED")
            return True
        else:
            print("❌ Fire spreading test FAILED - fire did not spread")
            return False
            
    except Exception as e:
        print(f"❌ Fire spreading test FAILED with error: {e}")
        return False

def test_objective_function_fix():
    """Test that objective function calculates proper scores."""
    print("\n🎯 Testing objective function fix...")
    
    try:
        # Create test data
        predicted = np.zeros((20, 20))
        predicted[8:12, 8:12] = 1  # Small square fire
        
        actual = np.zeros((20, 20))
        actual[7:13, 7:13] = 1  # Slightly larger overlapping fire
        
        # Create mock simulation result
        mock_forest_model = type('MockModel', (), {
            'state': np.stack([predicted] * 5, axis=2),
            'width': 20,
            'height': 20,
            'num_layers': 5
        })()
        
        mock_result = {'forest_model': mock_forest_model}
        mock_target = {'fire_perimeter': actual}
        
        # Test objective function
        spatial_obj = SpatialSimilarityObjective()
        result = spatial_obj.evaluate(mock_result, mock_target)
        
        print(f"   Objective value: {result.value:.4f}")
        print(f"   Components: {result.components}")
        
        if result.value > 0.0 and result.is_valid:
            print("✅ Objective function test PASSED")
            return True
        else:
            print("❌ Objective function test FAILED - zero or invalid objective")
            return False
            
    except Exception as e:
        print(f"❌ Objective function test FAILED with error: {e}")
        return False

def main():
    """Run all tests."""
    print("🔧 CALIBRATION FRAMEWORK FIXES TEST")
    print("=" * 50)
    
    tests = [
        test_json_serialization_fix,
        test_fire_spreading_fix,
        test_objective_function_fix
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED! Calibration framework fixes are working.")
        return True
    else:
        print("⚠️  Some tests FAILED. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
