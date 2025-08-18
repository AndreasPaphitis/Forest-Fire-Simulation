#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test New Default Parameters

This script tests that the new default parameters allow fire spread.
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_new_default_parameters():
    """Test that the new default parameters allow fire spread."""
    print("🧪 TESTING NEW DEFAULT PARAMETERS")
    print("=" * 60)
    
    try:
        from src.config.config_tools import create_config
        from src.core.forest_model import create_forest_model
        from src.core.fire_simulation_engine import FireSimulationEngine
        
        # Test with new default parameters (should work)
        print("\n1️⃣ TESTING NEW DEFAULT PARAMETERS")
        print("-" * 40)
        
        # Create config with default parameters (should use new defaults)
        config = create_config(
            grid_size=(50, 50),
            num_layers=3,
            max_steps=10
            # Don't override any parameters - use new defaults
        )
        
        print(f"   Default ignition_threshold: {config.ignition_threshold}")
        print(f"   Default fuel_consumption_rate: {config.fuel_consumption_rate}")
        print(f"   Default spread_probability: {config.spread_probability}")
        
        forest_model = create_forest_model(config=config)
        forest_model.set_ignition(25, 25, 0)
        
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        results = engine.run_simulation()
        
        print(f"   Total burned cells: {results['stats']['total_burned_cells']}")
        print(f"   Final active cells: {results['stats']['final_active_cells']}")
        print(f"   Simulation steps: {results['stats']['steps']}")
        
        if results['stats']['total_burned_cells'] > 1:
            print("   ✅ SUCCESS: New defaults allow fire spread!")
            return True
        else:
            print("   ❌ FAILURE: New defaults still don't work")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_calibration_with_new_parameters():
    """Test that calibration parameters include ignition_threshold."""
    print("\n2️⃣ TESTING CALIBRATION PARAMETERS")
    print("-" * 40)
    
    try:
        from src.core.calibration.parameter_bounds import get_default_calibration_bounds
        
        bounds = get_default_calibration_bounds()
        
        print(f"   Total calibration parameters: {len(bounds)}")
        
        # Check if ignition_threshold is included
        if 'ignition_threshold' in bounds:
            param = bounds['ignition_threshold']
            print(f"   ✅ ignition_threshold is included in calibration")
            print(f"      Range: [{param.min_value}, {param.max_value}]")
            print(f"      Default: {param.default_value}")
            print(f"      Tier: {param.calibration_tier}")
            return True
        else:
            print(f"   ❌ ignition_threshold is NOT included in calibration")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🔥 TESTING NEW DEFAULT PARAMETERS")
    print("=" * 80)
    
    # Run tests
    test1_passed = test_new_default_parameters()
    test2_passed = test_calibration_with_new_parameters()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY:")
    print(f"   New defaults: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Calibration params: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 SUCCESS: All fixes applied!")
        print("   - ignition_threshold lowered to 0.1")
        print("   - fuel_consumption_rate lowered to 0.3")
        print("   - ignition_threshold added to calibration parameters")
        print("   - Fire spread should now work in calibration!")
    else:
        print("\n❌ Some tests failed - need to investigate further")
    
    print("=" * 80)
