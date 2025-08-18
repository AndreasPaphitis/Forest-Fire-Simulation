#!/usr/bin/env python3
"""
Debug what happens in the _process_step method.
"""

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine
import numpy as np

def debug_step_processing():
    """Debug what happens in the _process_step method."""
    
    print("🔍 Debugging step processing...")
    
    # Create a simple config
    config = ModelConfig(
        grid_size=(10, 10),  # Very small grid for debugging
        num_layers=2,
        max_steps=10,
        simulation_type='memory_optimized',
        spread_probability=0.99,
        fuel_consumption_rate=0.001,  # Very low
        ignition_threshold=0.001,
        min_fuel_value=0.001,
        max_fuel_value=1.0,
        wind_speed=0.0,
        wind_direction=0.0
    )
    
    # Create forest model
    forest_model = create_forest_model(
        model_type='memory_optimized',
        config=config
    )
    
    # Set ignition point
    cx, cy = config.grid_size[0] // 2, config.grid_size[1] // 2
    forest_model.set_ignition(cx, cy, 0)
    print(f"Set ignition at ({cx}, {cy}, 0)")
    
    # Check ignition points
    ignition_points = getattr(forest_model, '_ignition_points', [])
    print(f"Ignition points: {ignition_points}")
    
    # Check state at ignition point
    state = forest_model.state[cx, cy, 0]
    fuel = forest_model.fuel_load[cx, cy, 0]
    print(f"Cell ({cx}, {cy}, 0): state={state}, fuel={fuel:.4f}")
    
    # Manually scan for burning cells
    print("\n🔍 Manually scanning for burning cells...")
    burning_count = 0
    for x in range(forest_model.width):
        for y in range(forest_model.height):
            for z in range(forest_model.num_layers):
                if forest_model.state[x, y, z] == 1:  # BURNING state
                    burning_count += 1
                    print(f"  Found burning cell at ({x}, {y}, {z})")
    print(f"Total burning cells found: {burning_count}")
    
    # Create engine
    engine = FireSimulationEngine(forest_model=forest_model, config=config)
    print(f"Engine created with {len(engine.active_cells)} active cells")
    
    # Run simulation for 1 step to trigger initialization
    print("\n🚀 Running simulation for 1 step to trigger initialization...")
    result = engine.run_simulation(max_steps=1, stop_when_fire_extinguished=False, store_history=False)
    
    # Check state after initialization
    print(f"Active cells after initialization: {len(engine.active_cells)}")
    print(f"Burned cells: {len(engine.burned_cells)}")
    
    # Check what happened to the ignition cell
    state = forest_model.state[cx, cy, 0]
    fuel = forest_model.fuel_load[cx, cy, 0]
    print(f"Cell ({cx}, {cy}, 0) after step: state={state}, fuel={fuel:.4f}")
    
    # Check if it's in burned cells
    if (cx, cy, 0) in engine.burned_cells:
        print(f"Cell ({cx}, {cy}, 0) is in burned_cells")
    else:
        print(f"Cell ({cx}, {cy}, 0) is NOT in burned_cells")
    
    # Check if it's in active cells
    if (cx, cy, 0) in engine.active_cells:
        print(f"Cell ({cx}, {cy}, 0) is in active_cells")
    else:
        print(f"Cell ({cx}, {cy}, 0) is NOT in active_cells")
    
    # Check simulation stats
    stats = result.get('stats', {})
    print(f"Simulation stats: {stats}")
    
    return True

if __name__ == "__main__":
    debug_step_processing()
