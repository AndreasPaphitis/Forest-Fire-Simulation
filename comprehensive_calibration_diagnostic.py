#!/usr/bin/env python
"""
Comprehensive diagnostic script to check all possible causes of zero objective scores in calibration.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.config_tools import create_config
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.calibration.objective_functions import SpatialSimilarityObjective
from src.core.calibration.calibration_utils import create_production_target_data
from src.core.core_simulation_framework import CellState
import numpy as np

def comprehensive_diagnostic():
    """Run comprehensive diagnostic to find all possible causes of zero objective scores."""
    
    print("🔍 COMPREHENSIVE CALIBRATION DIAGNOSTIC")
    print("=" * 60)
    
    # Test 1: Check if fire simulation works at all
    print("\n1️⃣ TESTING BASIC FIRE SIMULATION")
    print("-" * 40)
    
    config = create_config(
        grid_size=(50, 50),
        num_layers=3,
        max_steps=10,
        spread_probability=0.4,
        ignition_threshold=0.15,
        max_fuel_value=1.0,
        initial_fuel_load=0.5,
        fuel_consumption_rate=0.1,
        ignition_points=[(25, 25, 0)]
    )
    
    forest_model = create_forest_model(config=config)
    forest_model.set_ignition(25, 25, 0)
    
    engine = FireSimulationEngine(forest_model=forest_model, config=config)
    results = engine.run_simulation()
    
    print(f"   Final active cells: {results['stats']['final_active_cells']}")
    print(f"   Total burned cells: {results['stats']['total_burned_cells']}")
    print(f"   Simulation steps: {results['stats']['steps']}")
    
    if results['stats']['total_burned_cells'] <= 1:
        print("   ❌ CRITICAL: Fire is not spreading!")
        return False
    else:
        print("   ✅ Fire simulation is working")
    
    # Test 2: Check objective function with synthetic target
    print("\n2️⃣ TESTING OBJECTIVE FUNCTION WITH SYNTHETIC TARGET")
    print("-" * 40)
    
    objective_function = SpatialSimilarityObjective()
    objective_result = objective_function.evaluate(results, None)  # No target data
    
    print(f"   Objective value: {objective_result.value}")
    print(f"   Is valid: {objective_result.is_valid}")
    print(f"   Error message: {objective_result.error_message}")
    print(f"   Components: {objective_result.components}")
    
    if objective_result.value == 0.0:
        print("   ❌ CRITICAL: Objective function returns 0 with synthetic target!")
        return False
    else:
        print("   ✅ Objective function works with synthetic target")
    
    # Test 3: Check objective function with empty target data
    print("\n3️⃣ TESTING OBJECTIVE FUNCTION WITH EMPTY TARGET DATA")
    print("-" * 40)
    
    empty_target = {}
    objective_result2 = objective_function.evaluate(results, empty_target)
    
    print(f"   Objective value: {objective_result2.value}")
    print(f"   Is valid: {objective_result2.is_valid}")
    print(f"   Error message: {objective_result2.error_message}")
    
    if objective_result2.value == 0.0:
        print("   ❌ CRITICAL: Objective function returns 0 with empty target!")
        return False
    else:
        print("   ✅ Objective function works with empty target")
    
    # Test 4: Check forest model state format
    print("\n4️⃣ TESTING FOREST MODEL STATE FORMAT")
    print("-" * 40)
    
    state = forest_model.state
    print(f"   State type: {type(state)}")
    print(f"   State shape: {state.shape if hasattr(state, 'shape') else 'no shape'}")
    print(f"   State repr: {str(type(state))}")
    
    # Check if it's a SparseLayerAccessor
    if 'SparseLayerAccessor' in str(type(state)):
        print("   ✅ Using SparseLayerAccessor (expected)")
        
        # Check sparse layers
        for i, layer in enumerate(state.sparse_layers):
            nnz = layer.nnz
            print(f"   Layer {i}: {nnz} non-zero elements")
            if nnz > 0:
                print(f"   Layer {i} has burning cells")
    else:
        print("   ⚠️  Not using SparseLayerAccessor")
    
    # Test 5: Check target data creation
    print("\n5️⃣ TESTING TARGET DATA CREATION")
    print("-" * 40)
    
    try:
        # Try to create production target data (this might fail if files don't exist)
        target_data = create_production_target_data(
            dem_file="test_dem.tif",  # This will likely fail
            lidar_data_dir="test_lidar",  # This will likely fail
            grid_size=(50, 50),
            num_layers=3,
            model_resolution=5.0
        )
        print("   ✅ Production target data created successfully")
        print(f"   Target data keys: {list(target_data.keys())}")
    except Exception as e:
        print(f"   ⚠️  Production target data creation failed (expected): {e}")
        print("   This is normal if DEM/LiDAR files don't exist")
    
    # Test 6: Check objective function with real target data
    print("\n6️⃣ TESTING OBJECTIVE FUNCTION WITH REAL TARGET DATA")
    print("-" * 40)
    
    # Create a simple target for testing
    target_shape = (50, 50)
    target_2d = np.zeros(target_shape)
    
    # Create a circular target
    center_x, center_y = 25, 25
    radius = 10
    y, x = np.ogrid[:target_shape[0], :target_shape[1]]
    mask = (x - center_x)**2 + (y - center_y)**2 <= radius**2
    target_2d[mask] = 1.0
    
    real_target = {'fire_perimeter': target_2d}
    objective_result3 = objective_function.evaluate(results, real_target)
    
    print(f"   Objective value: {objective_result3.value}")
    print(f"   Is valid: {objective_result3.is_valid}")
    print(f"   Components: {objective_result3.components}")
    
    if objective_result3.value == 0.0:
        print("   ❌ CRITICAL: Objective function returns 0 with real target!")
        return False
    else:
        print("   ✅ Objective function works with real target")
    
    # Test 7: Check worker function simulation
    print("\n7️⃣ TESTING WORKER FUNCTION SIMULATION")
    print("-" * 40)
    
    # Simulate what the worker function does
    parameter_values = {
        'spread_probability': 0.4,
        'ignition_threshold': 0.15,
        'max_fuel_value': 1.0,
        'initial_fuel_load': 0.5
    }
    
    config_dict = config.__dict__.copy()
    config_dict.update(parameter_values)
    
    # Create new forest model and engine (like worker does)
    forest_model2 = create_forest_model(config=config)
    forest_model2.set_ignition(25, 25, 0)
    
    engine2 = FireSimulationEngine(forest_model=forest_model2, config=config)
    simulation_result2 = engine2.run_simulation()
    
    # Test objective function (like worker does)
    objective_result4 = objective_function.evaluate(simulation_result2, None)
    
    print(f"   Worker simulation - Final active cells: {simulation_result2['stats']['final_active_cells']}")
    print(f"   Worker simulation - Total burned cells: {simulation_result2['stats']['total_burned_cells']}")
    print(f"   Worker simulation - Objective value: {objective_result4.value}")
    print(f"   Worker simulation - Is valid: {objective_result4.is_valid}")
    
    if objective_result4.value == 0.0:
        print("   ❌ CRITICAL: Worker simulation returns 0 objective!")
        return False
    else:
        print("   ✅ Worker simulation works correctly")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - CALIBRATION SHOULD WORK!")
    print("If you're still getting 0 objective scores, the issue might be:")
    print("1. Target data not being passed to workers correctly")
    print("2. Memory issues causing simulation failures")
    print("3. Configuration overrides in the actual calibration run")
    
    return True

if __name__ == "__main__":
    comprehensive_diagnostic()
