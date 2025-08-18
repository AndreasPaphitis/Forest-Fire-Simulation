#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug Calibration Zero Objective Values

This script investigates why the calibration framework is getting zero objective values
and why the best parameters are all at their minimum values.

Author: Forest Fire Simulation Team
Date: 2025
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_tools import ModelConfig
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.calibration.objective_functions import SpatialSimilarityObjective

def test_minimum_parameters():
    """Test what happens with the minimum parameter values that the calibration found."""
    print("🔍 Testing Minimum Parameters (What Calibration Found)")
    print("=" * 60)
    
    # These are the parameters that the calibration found as "best"
    min_params = {
        'ember_probability': 0.01,
        'fuel_consumption_rate': 0.1,
        'ember_ignition': 0.1,
        'slope_influence': 0.0,
        'ember_height_factor': 0.0
    }
    
    print("Parameters that calibration found as 'best':")
    for param, value in min_params.items():
        print(f"   {param}: {value}")
    
    # Create configuration with these minimum parameters
    config = ModelConfig(
        width=100,
        height=100,
        num_layers=5,
        max_steps=20,
        **min_params,
        use_terrain=True,
        use_preprocessed_terrain=True,
        preprocessed_terrain_dir="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain"
    )
    
    print(f"\nConfiguration created with:")
    print(f"   Grid size: {config.width}x{config.height}")
    print(f"   Max steps: {config.max_steps}")
    print(f"   Use terrain: {config.use_terrain}")
    print(f"   Use preprocessed terrain: {config.use_preprocessed_terrain}")
    
    try:
        # Create forest model
        forest_model = create_forest_model(config)
        print("✅ Forest model created successfully")
        
        # Set ignition points
        ignition_points = [
            (config.width // 2, config.height // 2, 0),
            (config.width // 2 + 2, config.height // 2, 0),
            (config.width // 2, config.height // 2 + 2, 0)
        ]
        
        for x, y, z in ignition_points:
            if 0 <= x < config.width and 0 <= y < config.height and 0 <= z < config.num_layers:
                forest_model.state[x, y, z] = 1  # BURNING
                print(f"   Set ignition point at ({x}, {y}, {z})")
        
        # Create simulation engine
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        print("✅ Simulation engine created successfully")
        
        # Run simulation
        print("\n🔥 Running simulation with minimum parameters...")
        result = engine.run_simulation()
        
        # Check results
        stats = result.get('stats', {})
        total_burned = stats.get('total_burned_cells', 0)
        steps = stats.get('steps', 0)
        runtime = stats.get('runtime_seconds', 0)
        
        print(f"   Simulation completed in {steps} steps")
        print(f"   Total burned cells: {total_burned}")
        print(f"   Runtime: {runtime:.2f} seconds")
        
        if total_burned == 0:
            print("❌ CRITICAL: No cells burned! This explains the zero objective values.")
            print("   The fire is not spreading at all with these parameters.")
            return False
        elif total_burned <= 3:
            print("⚠️  WARNING: Only ignition points burned. Fire is not spreading.")
            return False
        else:
            print("✅ Fire is spreading with minimum parameters")
            return True
            
    except Exception as e:
        print(f"❌ Error testing minimum parameters: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_maximum_parameters():
    """Test what happens with maximum parameter values to see if fire spreads better."""
    print("\n🔥 Testing Maximum Parameters (For Comparison)")
    print("=" * 60)
    
    # Test with maximum parameter values
    max_params = {
        'ember_probability': 0.5,
        'fuel_consumption_rate': 5.0,
        'ember_ignition': 0.6,
        'slope_influence': 1.0,
        'ember_height_factor': 1.0
    }
    
    print("Testing with maximum parameter values:")
    for param, value in max_params.items():
        print(f"   {param}: {value}")
    
    config = ModelConfig(
        width=100,
        height=100,
        num_layers=5,
        max_steps=20,
        **max_params,
        use_terrain=True,
        use_preprocessed_terrain=True,
        preprocessed_terrain_dir="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain"
    )
    
    try:
        # Create forest model
        forest_model = create_forest_model(config)
        
        # Set ignition points
        ignition_points = [
            (config.width // 2, config.height // 2, 0),
            (config.width // 2 + 2, config.height // 2, 0),
            (config.width // 2, config.height // 2 + 2, 0)
        ]
        
        for x, y, z in ignition_points:
            if 0 <= x < config.width and 0 <= y < config.height and 0 <= z < config.num_layers:
                forest_model.state[x, y, z] = 1  # BURNING
        
        # Create simulation engine
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Run simulation
        print("\n🔥 Running simulation with maximum parameters...")
        result = engine.run_simulation()
        
        # Check results
        stats = result.get('stats', {})
        total_burned = stats.get('total_burned_cells', 0)
        steps = stats.get('steps', 0)
        runtime = stats.get('runtime_seconds', 0)
        
        print(f"   Simulation completed in {steps} steps")
        print(f"   Total burned cells: {total_burned}")
        print(f"   Runtime: {runtime:.2f} seconds")
        
        if total_burned > 10:
            print("✅ Fire spreads much better with maximum parameters")
            return True
        else:
            print("❌ Even maximum parameters don't produce good fire spreading")
            return False
            
    except Exception as e:
        print(f"❌ Error testing maximum parameters: {e}")
        return False

def test_objective_function():
    """Test the objective function directly to see if it's working properly."""
    print("\n🎯 Testing Objective Function")
    print("=" * 60)
    
    try:
        # Create test data
        predicted = np.zeros((50, 50))
        predicted[20:30, 20:30] = 1  # Small square fire
        
        actual = np.zeros((50, 50))
        actual[18:32, 18:32] = 1  # Slightly larger overlapping fire
        
        # Create mock simulation result
        mock_forest_model = type('MockModel', (), {
            'state': np.stack([predicted] * 5, axis=2),
            'width': 50,
            'height': 50,
            'num_layers': 5
        })()
        
        mock_result = {'forest_model': mock_forest_model}
        mock_target = {'fire_perimeter': actual}
        
        # Test objective function
        spatial_obj = SpatialSimilarityObjective()
        result = spatial_obj.evaluate(mock_result, mock_target)
        
        print(f"   Objective value: {result.value:.4f}")
        print(f"   Components: {result.components}")
        print(f"   Is valid: {result.is_valid}")
        
        if result.value > 0.0 and result.is_valid:
            print("✅ Objective function is working correctly")
            return True
        else:
            print("❌ Objective function is not working correctly")
            return False
            
    except Exception as e:
        print(f"❌ Error testing objective function: {e}")
        return False

def test_terrain_loading():
    """Test if terrain data is being loaded properly."""
    print("\n🏔️ Testing Terrain Loading")
    print("=" * 60)
    
    try:
        config = ModelConfig(
            width=50,
            height=50,
            num_layers=3,
            use_terrain=True,
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain"
        )
        
        # Create forest model
        forest_model = create_forest_model(config)
        
        # Check if terrain data is loaded
        terrain_loaded = (
            hasattr(forest_model, 'terrain_elevation') and forest_model.terrain_elevation is not None or
            hasattr(forest_model, 'barranco_mask') and forest_model.barranco_mask is not None or
            hasattr(forest_model, 'wind_channeling_mask') and forest_model.wind_channeling_mask is not None
        )
        
        print(f"   Terrain enabled in config: {config.use_terrain}")
        print(f"   Preprocessed terrain enabled: {config.use_preprocessed_terrain}")
        print(f"   Preprocessed terrain dir: {config.preprocessed_terrain_dir}")
        print(f"   Terrain data loaded: {terrain_loaded}")
        
        if terrain_loaded:
            print("✅ Terrain loading test PASSED")
            return True
        else:
            print("❌ Terrain loading test FAILED - no terrain data loaded")
            return False
            
    except Exception as e:
        print(f"❌ Terrain loading test FAILED with error: {e}")
        return False

def main():
    """Run all diagnostic tests."""
    print("🔍 CALIBRATION ZERO OBJECTIVE DEBUG")
    print("=" * 80)
    
    tests = [
        test_minimum_parameters,
        test_maximum_parameters,
        test_objective_function,
        test_terrain_loading
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Debug Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED! The issue might be elsewhere.")
    else:
        print("⚠️  Some tests FAILED. This explains the zero objective values.")
        print("\n🔧 Root Cause Analysis:")
        print("   • If minimum parameters test failed: Fire doesn't spread with any parameters")
        print("   • If maximum parameters test failed: Even best parameters don't work")
        print("   • If objective function test failed: Objective calculation is broken")
        print("   • If terrain loading test failed: Terrain effects are not working")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
