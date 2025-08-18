#!/usr/bin/env python3
"""
Test simulation step by step to see what's happening.
"""

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine

def test_step_by_step():
    """Test simulation step by step."""
    
    print("🧪 Testing simulation step by step...")
    
    # Create a simple config
    config = ModelConfig(
        grid_size=(20, 20),
        num_layers=2,
        max_steps=5,
        simulation_type='memory_optimized',
        spread_probability=0.99,
        fuel_consumption_rate=0.0001,  # Very low
        ignition_threshold=0.001,
        min_fuel_value=0.001,
        max_fuel_value=1.0,
        wind_speed=0.0,
        wind_direction=0.0,
        stop_when_fire_extinguished=False
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
    
    # Create engine
    engine = FireSimulationEngine(forest_model=forest_model, config=config)
    
    # Run simulation step by step
    print("\n🚀 Running simulation step by step...")
    for step in range(5):
        print(f"\n--- Step {step} ---")
        
        # Check state before step
        print(f"Active cells before step: {len(engine.active_cells)}")
        print(f"Burned cells before step: {len(engine.burned_cells)}")
        
        # Run one step
        try:
            engine._process_step()
            print(f"Step {step} completed successfully")
        except Exception as e:
            print(f"Step {step} failed: {e}")
            break
        
        # Check state after step
        print(f"Active cells after step: {len(engine.active_cells)}")
        print(f"Burned cells after step: {len(engine.burned_cells)}")
        
        # Check ignition cell
        state = forest_model.state[cx, cy, 0]
        fuel = forest_model.fuel_load[cx, cy, 0]
        print(f"Ignition cell ({cx}, {cy}, 0): state={state}, fuel={fuel:.4f}")
        
        # Stop if no active cells
        if len(engine.active_cells) == 0:
            print("No active cells - stopping")
            break
    
    return True

if __name__ == "__main__":
    test_step_by_step()
