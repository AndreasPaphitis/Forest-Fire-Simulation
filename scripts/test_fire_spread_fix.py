#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Fire Spread Fix

This script tests if adjusting the ignition threshold fixes the fire spread issue.
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_fire_spread_with_lower_threshold():
    """Test fire spread with a lower ignition threshold."""
    print("🧪 TESTING FIRE SPREAD WITH LOWER IGNITION THRESHOLD")
    print("=" * 60)
    
    try:
        from src.config.config_tools import create_config
        from src.core.forest_model import create_forest_model
        from src.core.fire_simulation_engine import FireSimulationEngine
        
        # Test 1: Current parameters (should fail)
        print("\n1️⃣ TESTING CURRENT PARAMETERS (should fail)")
        print("-" * 40)
        
        config1 = create_config(
            grid_size=(50, 50),
            num_layers=3,
            max_steps=10,
            spread_probability=0.8,
            fuel_consumption_rate=1.0,
            max_fuel_value=1.0,
            initial_fuel_load=0.5,
            ignition_threshold=0.5,  # Current default - too high
            wind_speed=5.0,
            wind_direction=0.0
        )
        
        forest_model1 = create_forest_model(config=config1)
        forest_model1.set_ignition(25, 25, 0)
        
        engine1 = FireSimulationEngine(forest_model=forest_model1, config=config1)
        results1 = engine1.run_simulation()
        
        print(f"   Ignition threshold: 0.5")
        print(f"   Total burned cells: {results1['stats']['total_burned_cells']}")
        print(f"   Final active cells: {results1['stats']['final_active_cells']}")
        
        # Test 2: Lower ignition threshold (should work)
        print("\n2️⃣ TESTING LOWER IGNITION THRESHOLD (should work)")
        print("-" * 40)
        
        config2 = create_config(
            grid_size=(50, 50),
            num_layers=3,
            max_steps=10,
            spread_probability=0.8,
            fuel_consumption_rate=0.5,  # Lower consumption rate
            max_fuel_value=1.0,
            initial_fuel_load=0.5,
            ignition_threshold=0.1,  # Much lower threshold
            wind_speed=5.0,
            wind_direction=0.0
        )
        
        forest_model2 = create_forest_model(config=config2)
        forest_model2.set_ignition(25, 25, 0)
        
        engine2 = FireSimulationEngine(forest_model=forest_model2, config=config2)
        results2 = engine2.run_simulation()
        
        print(f"   Ignition threshold: 0.1")
        print(f"   Fuel consumption rate: 0.5")
        print(f"   Total burned cells: {results2['stats']['total_burned_cells']}")
        print(f"   Final active cells: {results2['stats']['final_active_cells']}")
        
        # Test 3: Even more aggressive parameters
        print("\n3️⃣ TESTING AGGRESSIVE PARAMETERS")
        print("-" * 40)
        
        config3 = create_config(
            grid_size=(50, 50),
            num_layers=3,
            max_steps=10,
            spread_probability=0.9,  # Very high spread probability
            fuel_consumption_rate=0.2,  # Very low consumption rate
            max_fuel_value=1.0,
            initial_fuel_load=0.8,  # Higher fuel load
            ignition_threshold=0.05,  # Very low threshold
            wind_speed=5.0,
            wind_direction=0.0
        )
        
        forest_model3 = create_forest_model(config=config3)
        forest_model3.set_ignition(25, 25, 0)
        
        engine3 = FireSimulationEngine(forest_model=forest_model3, config=config3)
        results3 = engine3.run_simulation()
        
        print(f"   Ignition threshold: 0.05")
        print(f"   Spread probability: 0.9")
        print(f"   Fuel consumption rate: 0.2")
        print(f"   Total burned cells: {results3['stats']['total_burned_cells']}")
        print(f"   Final active cells: {results3['stats']['final_active_cells']}")
        
        # Summary
        print("\n📊 SUMMARY:")
        print("-" * 40)
        print(f"   Test 1 (threshold=0.5): {results1['stats']['total_burned_cells']} cells")
        print(f"   Test 2 (threshold=0.1): {results2['stats']['total_burned_cells']} cells")
        print(f"   Test 3 (threshold=0.05): {results3['stats']['total_burned_cells']} cells")
        
        if results2['stats']['total_burned_cells'] > 1 or results3['stats']['total_burned_cells'] > 1:
            print("\n✅ SUCCESS: Lower ignition threshold fixes fire spread!")
            print("   The issue is that ignition_threshold=0.5 is too high")
            print("   Recommended fix: Lower ignition_threshold to 0.1-0.2")
            return True
        else:
            print("\n❌ FAILURE: Even lower thresholds don't work")
            print("   There might be another issue with the fire spread logic")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_calibration_parameters():
    """Test the actual calibration parameters being used."""
    print("\n🔧 TESTING CALIBRATION PARAMETERS")
    print("=" * 60)
    
    try:
        from src.core.calibration.parameter_bounds import get_default_calibration_bounds
        
        bounds = get_default_calibration_bounds()
        
        print("   Current calibration parameter bounds:")
        for param, (min_val, max_val) in bounds.items():
            print(f"     {param}: [{min_val}, {max_val}]")
        
        # Check if ignition_threshold is in the calibration parameters
        if 'ignition_threshold' in bounds:
            print(f"\n   ✅ ignition_threshold is in calibration parameters")
            print(f"   Range: [{bounds['ignition_threshold'][0]}, {bounds['ignition_threshold'][1]}]")
        else:
            print(f"\n   ❌ ignition_threshold is NOT in calibration parameters")
            print(f"   This might be the issue!")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🔥 TESTING FIRE SPREAD FIX")
    print("=" * 80)
    
    # Run tests
    test1_passed = test_fire_spread_with_lower_threshold()
    test2_passed = test_calibration_parameters()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY:")
    print(f"   Fire spread fix: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Calibration params: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed:
        print("\n🎯 RECOMMENDED FIX:")
        print("   1. Lower ignition_threshold from 0.5 to 0.1-0.2")
        print("   2. Lower fuel_consumption_rate from 1.0 to 0.3-0.5")
        print("   3. Add ignition_threshold to calibration parameters")
    else:
        print("\n❌ Need to investigate further")
    
    print("=" * 80)
