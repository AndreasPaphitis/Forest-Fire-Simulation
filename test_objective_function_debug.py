#!/usr/bin/env python3
"""
Debug objective function to understand why it returns 0.0.
"""

import sys
import os
import logging
import numpy as np
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.config_tools import ModelConfig
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.calibration.objective_functions import SpatialSimilarityObjective

def test_objective_function_debug():
    """Test the objective function with a simple simulation."""
    
    print("🧪 DEBUGGING OBJECTIVE FUNCTION")
    print("=" * 40)
    
    # Create a simple config
    config = ModelConfig(
        grid_size=(20, 20),
        num_layers=3,
        max_steps=5,
        spread_probability=0.8,
        fuel_consumption_rate=0.1,
        ignition_threshold=0.05,
        min_fuel_value=0.01,
        max_fuel_value=1.0,
        initial_fuel_load=0.8
    )
    
    print(f"   Grid size: {config.grid_size}")
    print(f"   Spread probability: {config.spread_probability}")
    print(f"   Fuel consumption rate: {config.fuel_consumption_rate}")
    print(f"   Ignition threshold: {config.ignition_threshold}")
    
    try:
        # Create forest model
        forest_model = create_forest_model(
            model_type='memory_optimized',
            config=config
        )
        
        # Set ignition point
        cx, cy = config.grid_size[0] // 2, config.grid_size[1] // 2
        forest_model.set_ignition(cx, cy, 0)
        print(f"   Set ignition at ({cx}, {cy}, 0)")
        
        # Create engine
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Run simulation
        print("   Running simulation...")
        result = engine.run_simulation()
        
        if result is None:
            print("   ❌ Simulation returned None")
            return
            
        # Analyze simulation result
        print("\n📊 SIMULATION RESULT ANALYSIS:")
        print(f"   Result keys: {list(result.keys())}")
        
        if 'stats' in result:
            stats = result['stats']
            print(f"   Stats keys: {list(stats.keys())}")
            print(f"   Total burned cells: {stats.get('total_burned_cells', 'N/A')}")
            print(f"   Final active cells: {stats.get('final_active_cells', 'N/A')}")
            print(f"   Max active cells: {stats.get('max_active_cells', 'N/A')}")
            print(f"   Steps: {stats.get('steps', 'N/A')}")
        
        if 'forest_model' in result:
            forest_model = result['forest_model']
            print(f"   Forest model type: {type(forest_model)}")
            
            if hasattr(forest_model, 'state'):
                state = forest_model.state
                print(f"   State type: {type(state)}")
                if hasattr(state, 'shape'):
                    print(f"   State shape: {state.shape}")
                if hasattr(state, 'nnz'):
                    print(f"   State nnz: {state.nnz}")
            
            # Check if engine has burned_cells
            if hasattr(engine, 'burned_cells'):
                print(f"   Engine burned_cells: {len(engine.burned_cells)} cells")
                if len(engine.burned_cells) > 0:
                    print(f"   Sample burned cells: {list(engine.burned_cells)[:5]}")
        
        # Test objective function
        print("\n🎯 OBJECTIVE FUNCTION TEST:")
        
        # Create target data
        target_data = {
            'fire_perimeter': np.zeros(config.grid_size, dtype=float)
        }
        # Mark a few cells as target
        target_data['fire_perimeter'][cx, cy] = 1.0
        target_data['fire_perimeter'][cx+1, cy] = 1.0
        target_data['fire_perimeter'][cx, cy+1] = 1.0
        
        print(f"   Target data shape: {target_data['fire_perimeter'].shape}")
        print(f"   Target cells: {np.sum(target_data['fire_perimeter'])}")
        
        # Create objective function
        objective = SpatialSimilarityObjective()
        
        # Evaluate
        objective_result = objective.evaluate(result, target_data)
        
        print(f"   Objective value: {objective_result.value}")
        print(f"   Is valid: {objective_result.is_valid}")
        if not objective_result.is_valid:
            print(f"   Error: {objective_result.error_message}")
        else:
            print(f"   Components: {objective_result.components}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_objective_function_debug()
