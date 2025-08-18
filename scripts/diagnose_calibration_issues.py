#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Diagnose Calibration Issues

This script diagnoses why the calibration framework is still getting small objective values
despite all the fixes being applied.

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

def check_configuration_fixes():
    """Check if all configuration fixes are properly applied."""
    print("🔧 Checking Configuration Fixes...")
    print("=" * 50)
    
    # Create a test configuration
    config = ModelConfig(
        width=50,
        height=50,
        num_layers=5,
        max_steps=20
    )
    
    print(f"✅ use_terrain: {config.use_terrain}")
    print(f"✅ use_preprocessed_terrain: {config.use_preprocessed_terrain}")
    print(f"✅ preprocessed_terrain_dir: {config.preprocessed_terrain_dir}")
    print(f"✅ spread_probability: {config.spread_probability}")
    print(f"✅ ignition_threshold: {config.ignition_threshold}")
    print(f"✅ ember_probability: {config.ember_probability}")
    
    # Check if fixes are applied
    fixes_applied = {
        'terrain_enabled': config.use_terrain == True,
        'preprocessed_terrain_enabled': config.use_preprocessed_terrain == True,
        'spread_probability_increased': config.spread_probability >= 0.8,
        'ignition_threshold_lowered': config.ignition_threshold <= 0.1,
        'ember_probability_increased': config.ember_probability >= 0.3
    }
    
    print("\n📊 Fix Status:")
    for fix_name, applied in fixes_applied.items():
        status = "✅" if applied else "❌"
        print(f"   {status} {fix_name}: {applied}")
    
    return all(fixes_applied.values())

def test_fire_spreading():
    """Test if fire spreading works with the new parameters."""
    print("\n🔥 Testing Fire Spreading...")
    print("=" * 50)
    
    try:
        # Create configuration with all fixes
        config = ModelConfig(
            width=40,
            height=40,
            num_layers=4,
            max_steps=15,
            spread_probability=0.8,
            ignition_threshold=0.1,
            ember_probability=0.3,
            use_terrain=True,
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain"
        )
        
        # Create forest model
        forest_model = create_forest_model(config)
        
        # Set multiple ignition points
        ignition_points = [
            (config.width // 2, config.height // 2, 0),
            (config.width // 2 + 3, config.height // 2, 0),
            (config.width // 2, config.height // 2 + 3, 0)
        ]
        
        for x, y, z in ignition_points:
            if 0 <= x < config.width and 0 <= y < config.height and 0 <= z < config.num_layers:
                forest_model.state[x, y, z] = 1  # BURNING
        
        # Create simulation engine
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Run simulation
        result = engine.run_simulation(max_steps=10)
        
        # Check results
        stats = result.get('stats', {})
        total_burned = stats.get('total_burned_cells', 0)
        steps = stats.get('steps', 0)
        runtime = stats.get('runtime_seconds', 0)
        
        print(f"   Simulation completed in {steps} steps")
        print(f"   Total burned cells: {total_burned}")
        print(f"   Runtime: {runtime:.2f} seconds")
        print(f"   Spread probability: {config.spread_probability}")
        print(f"   Ignition threshold: {config.ignition_threshold}")
        print(f"   Ember probability: {config.ember_probability}")
        
        if total_burned > 3:  # More than just ignition points
            print("✅ Fire spreading test PASSED")
            return True
        else:
            print("❌ Fire spreading test FAILED - fire did not spread")
            return False
            
    except Exception as e:
        print(f"❌ Fire spreading test FAILED with error: {e}")
        return False

def test_objective_function():
    """Test if objective function calculates proper scores."""
    print("\n🎯 Testing Objective Function...")
    print("=" * 50)
    
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
        print(f"   Is valid: {result.is_valid}")
        
        if result.value > 0.0 and result.is_valid:
            print("✅ Objective function test PASSED")
            return True
        else:
            print("❌ Objective function test FAILED - zero or invalid objective")
            return False
            
    except Exception as e:
        print(f"❌ Objective function test FAILED with error: {e}")
        return False

def test_terrain_loading():
    """Test if terrain data is being loaded properly."""
    print("\n🏔️ Testing Terrain Loading...")
    print("=" * 50)
    
    try:
        config = ModelConfig(
            width=30,
            height=30,
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
    print("🔍 CALIBRATION ISSUES DIAGNOSTIC")
    print("=" * 60)
    
    tests = [
        check_configuration_fixes,
        test_fire_spreading,
        test_objective_function,
        test_terrain_loading
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Diagnostic Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED! The fixes should be working.")
        print("\n💡 If you're still getting small objective values, possible causes:")
        print("   1. The calibration parameters are too conservative")
        print("   2. The target data doesn't match the simulation scale")
        print("   3. The simulation is running too few steps")
        print("   4. The ignition points are not in good locations")
        return True
    else:
        print("⚠️  Some tests FAILED. This explains the small objective values.")
        print("\n🔧 Issues to address:")
        if passed < total:
            print("   • Some calibration framework components are not working properly")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
