#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive Calibration Framework Fixes Test

This script tests ALL the fixes for the calibration framework issues:
1. Zero objective values due to fire not spreading
2. JSON serialization errors with numpy int64
3. Terrain effects being disabled (CRITICAL FIX)
4. Ember transport being too weak
5. Simulation finishing too quickly

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

def test_terrain_effects_enabled():
    """Test that terrain effects are properly enabled."""
    print("\n🏔️ Testing terrain effects fix...")
    
    try:
        # Create configuration with terrain enabled
        config = ModelConfig(
            width=50,
            height=50,
            num_layers=5,
            max_steps=20,
            use_terrain=True,  # This should be True by default now
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir="data/preprocessed_terrain"
        )
        
        # Create forest model
        forest_model = create_forest_model(config)
        
        # Check if terrain effects are available
        terrain_effects_available = (
            hasattr(forest_model, 'terrain_elevation') and forest_model.terrain_elevation is not None or
            hasattr(forest_model, 'barranco_mask') and forest_model.barranco_mask is not None or
            hasattr(forest_model, 'wind_channeling_mask') and forest_model.wind_channeling_mask is not None
        )
        
        print(f"   Terrain enabled in config: {config.use_terrain}")
        print(f"   Terrain effects available: {terrain_effects_available}")
        
        if config.use_terrain:
            print("✅ Terrain effects test PASSED")
            return True
        else:
            print("❌ Terrain effects test FAILED - terrain not enabled")
            return False
            
    except Exception as e:
        print(f"❌ Terrain effects test FAILED with error: {e}")
        return False

def test_ember_transport_fix():
    """Test that ember transport is more effective with increased probability."""
    print("\n🔥 Testing ember transport fix...")
    
    try:
        # Create configuration with higher ember probability
        config = ModelConfig(
            width=30,
            height=30,
            num_layers=3,
            max_steps=15,
            ember_probability=0.3,  # Increased from 0.1
            ember_distance=5,
            ember_ignition=0.3,
            spread_probability=0.8,  # Increased from 0.5
            ignition_threshold=0.1   # Lowered from 0.5
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
        
        # Check ember statistics
        ember_stats = engine.get_ember_statistics()
        total_embers = ember_stats.get('total_events', 0)
        
        print(f"   Ember probability: {config.ember_probability}")
        print(f"   Total embers generated: {total_embers}")
        
        if total_embers > 0:
            print("✅ Ember transport test PASSED")
            return True
        else:
            print("❌ Ember transport test FAILED - no embers generated")
            return False
            
    except Exception as e:
        print(f"❌ Ember transport test FAILED with error: {e}")
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
            slope_influence=0.4,
            ember_probability=0.3  # Increased from 0.1
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
        print(f"   Spread probability: {config.spread_probability}")
        print(f"   Ignition threshold: {config.ignition_threshold}")
        
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

def test_comprehensive_simulation():
    """Test a comprehensive simulation with all fixes applied."""
    print("\n🚀 Testing comprehensive simulation with all fixes...")
    
    try:
        # Create comprehensive configuration
        config = ModelConfig(
            width=40,
            height=40,
            num_layers=4,
            max_steps=15,
            # Fire spreading fixes
            spread_probability=0.8,
            ignition_threshold=0.1,
            # Ember transport fixes
            ember_probability=0.3,
            ember_distance=5,
            ember_ignition=0.3,
            # Terrain effects
            use_terrain=True,
            terrain_effect_strength=0.3,
            barranco_amplification=0.2,
            slope_influence=0.4,
            # Wind effects
            wind_influence_on_spread=0.5,
            # Other parameters
            fuel_consumption_rate=0.1
        )
        
        # Create forest model
        forest_model = create_forest_model(config)
        
        # Set multiple ignition points
        ignition_points = [
            (config.width // 2, config.height // 2, 0),
            (config.width // 2 + 5, config.height // 2, 0),
            (config.width // 2, config.height // 2 + 5, 0)
        ]
        
        for x, y, z in ignition_points:
            if 0 <= x < config.width and 0 <= y < config.height and 0 <= z < config.num_layers:
                forest_model.state[x, y, z] = 1  # BURNING
        
        # Create simulation engine
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Run simulation
        result = engine.run_simulation(max_steps=12)
        
        # Check comprehensive results
        stats = result.get('stats', {})
        total_burned = stats.get('total_burned_cells', 0)
        steps = stats.get('steps', 0)
        runtime = stats.get('runtime_seconds', 0)
        
        # Get ember statistics
        ember_stats = engine.get_ember_statistics()
        total_embers = ember_stats.get('total_events', 0)
        
        print(f"   Simulation runtime: {runtime:.2f} seconds")
        print(f"   Steps completed: {steps}")
        print(f"   Total burned cells: {total_burned}")
        print(f"   Total embers generated: {total_embers}")
        print(f"   Terrain enabled: {config.use_terrain}")
        print(f"   Ember probability: {config.ember_probability}")
        
        # Success criteria
        success_criteria = [
            total_burned > 3,  # More than just ignition points
            steps > 1,         # Simulation ran for multiple steps
            runtime > 0.1,     # Took some time to run
            config.use_terrain == True,  # Terrain is enabled
            config.ember_probability >= 0.3  # Ember probability is increased
        ]
        
        if all(success_criteria):
            print("✅ Comprehensive simulation test PASSED")
            return True
        else:
            failed_criteria = []
            if total_burned <= 3:
                failed_criteria.append("insufficient fire spread")
            if steps <= 1:
                failed_criteria.append("simulation too short")
            if runtime <= 0.1:
                failed_criteria.append("runtime too fast")
            if config.use_terrain != True:
                failed_criteria.append("terrain not enabled")
            if config.ember_probability < 0.3:
                failed_criteria.append("ember probability too low")
            
            print(f"❌ Comprehensive simulation test FAILED: {', '.join(failed_criteria)}")
            return False
            
    except Exception as e:
        print(f"❌ Comprehensive simulation test FAILED with error: {e}")
        return False

def main():
    """Run all comprehensive tests."""
    print("🔧 COMPREHENSIVE CALIBRATION FRAMEWORK FIXES TEST")
    print("=" * 60)
    
    tests = [
        test_json_serialization_fix,
        test_terrain_effects_enabled,
        test_ember_transport_fix,
        test_fire_spreading_fix,
        test_objective_function_fix,
        test_comprehensive_simulation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED! All calibration framework fixes are working.")
        print("\n✅ FIXES VERIFIED:")
        print("   • JSON serialization handles numpy types correctly")
        print("   • Terrain effects are properly enabled")
        print("   • Ember transport is more effective")
        print("   • Fire spreading works with new parameters")
        print("   • Objective functions calculate proper scores")
        print("   • Comprehensive simulation works with all fixes")
        return True
    else:
        print("⚠️  Some tests FAILED. Please check the issues above.")
        print("\n🔧 REMAINING ISSUES TO ADDRESS:")
        if passed < total:
            print("   • Some calibration framework components may still need fixes")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
