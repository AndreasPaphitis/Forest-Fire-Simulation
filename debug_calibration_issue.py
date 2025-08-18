#!/usr/bin/env python3
"""
Detailed diagnostic to understand why calibration simulations end immediately.
"""

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine
import numpy as np

def debug_calibration_issue():
    """Debug why calibration simulations end immediately."""
    
    print("🔍 Debugging calibration issue...")
    
    # Create a simple config with very low fuel consumption
    config = ModelConfig(
        grid_size=(20, 20),  # Smaller grid for debugging
        num_layers=2,
        max_steps=10,
        simulation_type='memory_optimized',
        spread_probability=0.99,  # Almost certain spread
        fuel_consumption_rate=0.001,  # Extremely low consumption rate
        ignition_threshold=0.001,  # Extremely low threshold
        min_fuel_value=0.001,
        max_fuel_value=1.0,
        wind_speed=0.0,
        wind_direction=0.0
    )
    
    print("📋 Config created:")
    print(f"  Grid size: {config.grid_size}")
    print(f"  Spread probability: {config.spread_probability}")
    print(f"  Fuel consumption rate: {config.fuel_consumption_rate}")
    print(f"  Ignition threshold: {config.ignition_threshold}")
    
    # Create forest model directly to inspect
    print("\n🌲 Creating forest model...")
    forest_model = create_forest_model(
        model_type='memory_optimized',
        config=config
    )
    
    print(f"  Forest model created: {type(forest_model)}")
    print(f"  Grid dimensions: {forest_model.width} x {forest_model.height} x {forest_model.num_layers}")
    print(f"  Uses sparse storage: {getattr(forest_model, 'use_sparse_storage', False)}")
    
    # Check if forest model has burning cell detection
    print(f"  Has _get_burning_cells: {hasattr(forest_model, '_get_burning_cells')}")
    print(f"  Has _ignition_points: {hasattr(forest_model, '_ignition_points')}")
    
    # Check fuel data
    print("\n⛽ Checking fuel data...")
    try:
        fuel_data = forest_model.fuel_load
        print(f"  Fuel data type: {type(fuel_data)}")
        
        # Try to access fuel data
        if hasattr(fuel_data, 'shape'):
            print(f"  Fuel data shape: {fuel_data.shape}")
        else:
            print(f"  Fuel data is sparse accessor: {type(fuel_data)}")
            
        # Check a specific cell
        test_fuel = forest_model.fuel_load[10, 10, 0]
        print(f"  Fuel at (10, 10, 0): {test_fuel}")
        
    except Exception as e:
        print(f"  ❌ Error accessing fuel data: {e}")
    
    # Set ignition points
    print("\n🔥 Setting ignition points...")
    try:
        cx, cy = config.grid_size[0] // 2, config.grid_size[1] // 2
        forest_model.set_ignition(cx, cy, 0)
        print(f"  Set ignition at ({cx}, {cy}, 0)")
        
        # Check if ignition was set
        ignition_points = getattr(forest_model, '_ignition_points', [])
        print(f"  Ignition points: {ignition_points}")
        
        # Check state at ignition point
        state = forest_model.state[cx, cy, 0]
        print(f"  State at ignition point: {state}")
        
        # Check if _get_burning_cells works
        if hasattr(forest_model, '_get_burning_cells'):
            try:
                burning_cells = forest_model._get_burning_cells()
                print(f"  _get_burning_cells returned: {burning_cells}")
            except Exception as e:
                print(f"  ❌ _get_burning_cells failed: {e}")
        
    except Exception as e:
        print(f"  ❌ Error setting ignition: {e}")
    
    # Create simulation engine
    print("\n🚀 Creating simulation engine...")
    try:
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        print("  ✅ Engine created successfully")
        
        # Check initial active cells
        print(f"  Initial active cells: {len(engine.active_cells)}")
        if engine.active_cells:
            print(f"  Active cell positions: {list(engine.active_cells)[:5]}")
        
        # Manually check for burning cells
        print("\n🔍 Manually checking for burning cells...")
        burning_count = 0
        for x in range(forest_model.width):
            for y in range(forest_model.height):
                for z in range(forest_model.num_layers):
                    if forest_model.state[x, y, z] == 1:  # BURNING state
                        burning_count += 1
                        if burning_count <= 5:
                            print(f"    Found burning cell at ({x}, {y}, {z})")
        
        print(f"  Total burning cells found: {burning_count}")
        
    except Exception as e:
        print(f"  ❌ Error creating engine: {e}")
        return False
    
    # Run a single step manually
    print("\n⚡ Running single simulation step...")
    try:
        # Check active cells before step
        print(f"  Active cells before step: {len(engine.active_cells)}")
        
        # Check fuel before step
        for x, y, z in engine.active_cells:
            fuel = forest_model.fuel_load[x, y, z]
            print(f"    Cell ({x}, {y}, {z}) fuel before: {fuel:.4f}")
        
        # Run one step
        engine._process_step()
        
        # Check active cells after step
        print(f"  Active cells after step: {len(engine.active_cells)}")
        print(f"  Burned cells: {len(engine.burned_cells)}")
        
        # Check fuel after step
        for x, y, z in [(cx, cy, 0)]:
            state = forest_model.state[x, y, z]
            fuel = forest_model.fuel_load[x, y, z]
            print(f"    Cell ({x}, {y}, {z}) after step: state={state}, fuel={fuel:.4f}")
        
        if len(engine.active_cells) == 0:
            print("  ⚠️  All cells burned out in first step!")
        else:
            print("  ✅ Fire is still burning!")
        
    except Exception as e:
        print(f"  ❌ Error in simulation step: {e}")
        import traceback
        traceback.print_exc()
    
    return True

if __name__ == "__main__":
    debug_calibration_issue()
