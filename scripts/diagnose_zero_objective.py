#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Diagnose Zero Objective Scores

This script diagnoses why calibration is producing zero objective scores (0.0000).
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def diagnose_zero_objective():
    """Diagnose why calibration is producing zero objective scores."""
    print("🔍 DIAGNOSING ZERO OBJECTIVE SCORES")
    print("=" * 60)
    
    try:
        # Test 1: Check if fire simulation works at all
        print("\n1️⃣ TESTING BASIC FIRE SIMULATION")
        print("-" * 40)
        
        from src.config.config_tools import create_config
        from src.core.forest_model import create_forest_model
        from src.core.fire_simulation_engine import FireSimulationEngine
        
        # Create a simple test configuration
        config = create_config(
            grid_size=(50, 50),
            num_layers=3,
            max_steps=10,
            spread_probability=0.8,  # High spread probability
            fuel_consumption_rate=1.0,
            max_fuel_value=1.0,
            initial_fuel_load=0.5,
            ignition_threshold=0.1,  # Low ignition threshold
            wind_speed=5.0,
            wind_direction=0.0
        )
        
        # Create forest model and set ignition
        forest_model = create_forest_model(config=config)
        forest_model.set_ignition(25, 25, 0)  # Center ignition
        
        # Run simulation
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        results = engine.run_simulation()
        
        print(f"   Final active cells: {results['stats']['final_active_cells']}")
        print(f"   Total burned cells: {results['stats']['total_burned_cells']}")
        print(f"   Simulation steps: {results['stats']['steps']}")
        
        if results['stats']['total_burned_cells'] <= 1:
            print("   ❌ CRITICAL: Fire is not spreading!")
            print("   This indicates a fundamental problem with fire spread logic")
            return False
        else:
            print("   ✅ Fire simulation is working")
        
        # Test 2: Check objective function with synthetic target
        print("\n2️⃣ TESTING OBJECTIVE FUNCTION")
        print("-" * 40)
        
        from src.core.calibration.objective_functions import SpatialSimilarityObjective
        
        # Create synthetic target data
        target_data = {
            'fire_perimeter': np.zeros((50, 50), dtype=np.float32)
        }
        
        # Create a simple circular target
        center_x, center_y = 25, 25
        radius = 10
        y, x = np.ogrid[:50, :50]
        mask = (x - center_x)**2 + (y - center_y)**2 <= radius**2
        target_data['fire_perimeter'][mask] = 1.0
        
        print(f"   Target fire cells: {np.sum(target_data['fire_perimeter'])}")
        
        # Test objective function
        objective_function = SpatialSimilarityObjective()
        objective_result = objective_function.evaluate(results, target_data)
        
        print(f"   Objective value: {objective_result.value}")
        print(f"   Is valid: {objective_result.is_valid}")
        print(f"   Components: {objective_result.components}")
        
        if objective_result.value > 0:
            print("   ✅ Objective function is working")
        else:
            print("   ❌ Objective function returning 0")
            print("   Components:", objective_result.components)
        
        # Test 3: Check calibration parameters
        print("\n3️⃣ CHECKING CALIBRATION PARAMETERS")
        print("-" * 40)
        
        # Check what parameters are being used in calibration
        from src.core.calibration.parameter_bounds import get_default_calibration_bounds
        
        bounds = get_default_calibration_bounds()
        print("   Default parameter bounds:")
        for param, (min_val, max_val) in bounds.items():
            print(f"     {param}: [{min_val}, {max_val}]")
        
        # Test 4: Check if the issue is with the large grid size
        print("\n4️⃣ TESTING LARGE GRID SIZE")
        print("-" * 40)
        
        # Test with a larger grid but still manageable
        large_config = create_config(
            grid_size=(200, 200),
            num_layers=5,
            max_steps=5,
            spread_probability=0.8,
            fuel_consumption_rate=1.0,
            max_fuel_value=1.0,
            initial_fuel_load=0.5,
            ignition_threshold=0.1
        )
        
        large_forest_model = create_forest_model(config=large_config)
        large_forest_model.set_ignition(100, 100, 0)
        
        large_engine = FireSimulationEngine(forest_model=large_forest_model, config=large_config)
        large_results = large_engine.run_simulation()
        
        print(f"   Large grid burned cells: {large_results['stats']['total_burned_cells']}")
        
        if large_results['stats']['total_burned_cells'] <= 1:
            print("   ❌ Large grid fire is not spreading!")
            print("   This might be the issue with the 4788x4490 grid")
        else:
            print("   ✅ Large grid fire simulation works")
        
        # Test 5: Check ignition setup
        print("\n5️⃣ CHECKING IGNITION SETUP")
        print("-" * 40)
        
        # Check if ignition is being set correctly
        test_model = create_forest_model(config=config)
        test_model.set_ignition(25, 25, 0)
        
        # Check if ignition was set
        ignition_cells = np.sum(test_model.state == 1)  # BURNING state
        print(f"   Ignition cells set: {ignition_cells}")
        
        if ignition_cells == 0:
            print("   ❌ CRITICAL: No ignition cells set!")
            print("   This would cause zero fire spread")
        else:
            print("   ✅ Ignition cells set correctly")
        
        # Test 6: Check fuel values
        print("\n6️⃣ CHECKING FUEL VALUES")
        print("-" * 40)
        
        # Check fuel load values
        fuel_values = test_model.fuel_load[25, 25, :]
        print(f"   Fuel values at ignition point: {fuel_values}")
        print(f"   Average fuel value: {np.mean(fuel_values):.3f}")
        print(f"   Max fuel value: {np.max(fuel_values):.3f}")
        print(f"   Min fuel value: {np.min(fuel_values):.3f}")
        
        if np.max(fuel_values) < 0.1:
            print("   ❌ CRITICAL: Fuel values are too low!")
            print("   This would prevent fire spread")
        else:
            print("   ✅ Fuel values look reasonable")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_calibration_config():
    """Check the calibration configuration being used."""
    print("\n🔧 CHECKING CALIBRATION CONFIGURATION")
    print("=" * 60)
    
    try:
        from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
        
        # Create a test calibrator
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=8,
            grid_search_points=2,
            experiment_name="diagnostic"
        )
        
        # Check what parameters are being calibrated
        print("   Calibration parameters:")
        for param in ['spread_probability', 'fuel_consumption_rate', 'ember_probability', 'ember_ignition', 'slope_influence']:
            print(f"     {param}")
        
        # Check grid size calculation
        grid_size = calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
        print(f"   Grid size: {grid_size}")
        
        # Check if this grid size is too large for fire spread
        total_cells = grid_size[0] * grid_size[1]
        print(f"   Total cells: {total_cells:,}")
        
        if total_cells > 10_000_000:  # 10M cells
            print("   ⚠️  WARNING: Very large grid size!")
            print("   This might cause fire to spread too slowly or not at all")
            print("   Consider using a smaller grid for testing")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🔥 DIAGNOSING ZERO OBJECTIVE SCORES IN CALIBRATION")
    print("=" * 80)
    
    # Run diagnostics
    test1_passed = diagnose_zero_objective()
    test2_passed = check_calibration_config()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 DIAGNOSTIC SUMMARY:")
    print(f"   Basic fire simulation: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Calibration config: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n✅ All diagnostics passed!")
        print("   The issue might be with specific parameter combinations")
        print("   or the very large grid size (4788x4490)")
    else:
        print("\n❌ Some diagnostics failed!")
        print("   Check the specific issues above")
    
    print("=" * 80)
