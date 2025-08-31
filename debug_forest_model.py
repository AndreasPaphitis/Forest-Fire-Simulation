#!/usr/bin/env python
"""
Debug script to test forest model state access.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.config_tools import ModelConfig
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine

def test_forest_model():
    """Test forest model creation and state access."""
    
    print("🔍 DEBUGGING FOREST MODEL STATE ACCESS")
    print("=" * 50)
    
    # Create config similar to sensitivity analysis
    config = ModelConfig(
        grid_size=(609, 609),
        num_layers=20,
        max_steps=20,
        model_resolution=20.0,
        simulation_type="memory_optimized",
        memory_optimization_level=2,
        use_disk_storage=True,
        use_differential_history=True,
        use_sparse_storage=True,
        use_preprocessed_terrain=True,
        engine_logging_interval=10,
        spread_probability=0.6,
        fuel_consumption_rate=0.8,
        ignition_threshold=0.4,
        initial_fuel_load=8.0,
        slope_influence=0.4,
        wind_influence_on_spread=0.3,
        terrain_effect_strength=0.7,
        wind_speed=5.0,
        wind_direction=45.0,
        random_seed=42
    )
    
    print(f"📊 Config created:")
    print(f"   Grid size: {config.grid_size}")
    print(f"   Num layers: {config.num_layers}")
    print(f"   Max steps: {config.max_steps}")
    print(f"   Simulation type: {config.simulation_type}")
    print(f"   Use sparse storage: {config.use_sparse_storage}")
    print()
    
    # Create forest model
    print("🌲 Creating forest model...")
    forest_model = create_forest_model(
        model_type="memory_optimized",
        config=config
    )
    
    print(f"📊 Forest model created:")
    print(f"   Type: {type(forest_model).__name__}")
    print(f"   Width: {getattr(forest_model, 'width', 'N/A')}")
    print(f"   Height: {getattr(forest_model, 'height', 'N/A')}")
    print(f"   Num layers: {getattr(forest_model, 'num_layers', 'N/A')}")
    print()
    
    # Check state attributes
    print("🔍 Checking state attributes:")
    print(f"   hasattr(forest_model, 'state'): {hasattr(forest_model, 'state')}")
    if hasattr(forest_model, 'state'):
        print(f"   forest_model.state: {forest_model.state}")
        if forest_model.state is not None:
            print(f"   forest_model.state.shape: {forest_model.state.shape}")
            print(f"   forest_model.state type: {type(forest_model.state)}")
    
    print(f"   hasattr(forest_model, 'state_layers'): {hasattr(forest_model, 'state_layers')}")
    if hasattr(forest_model, 'state_layers'):
        print(f"   forest_model.state_layers: {forest_model.state_layers}")
        if forest_model.state_layers is not None:
            print(f"   Type: {type(forest_model.state_layers)}")
            if isinstance(forest_model.state_layers, dict):
                print(f"   Keys: {list(forest_model.state_layers.keys())}")
                for key, value in list(forest_model.state_layers.items())[:3]:
                    print(f"     {key}: {type(value)} - {getattr(value, 'shape', 'no shape')}")
    
    print()
    
    # Test simulation
    print("🔥 Testing simulation...")
    engine = FireSimulationEngine(forest_model)
    
    # Set ignition point
    ignition_x, ignition_y = 395, 377
    forest_model.set_ignition_point(ignition_x, ignition_y, 0)
    print(f"   Ignition set at ({ignition_x}, {ignition_y}, 0)")
    
    # Run short simulation
    print("   Running 5 steps...")
    result = engine.run_simulation(
        max_steps=5,
        store_history=False,
        stop_when_fire_extinguished=True
    )
    
    print(f"   Simulation completed:")
    print(f"     Result keys: {list(result.keys())}")
    print(f"     Stats: {result.get('stats', {})}")
    
    # Check forest model after simulation
    print("🔍 Checking forest model after simulation:")
    print(f"   hasattr(forest_model, 'state'): {hasattr(forest_model, 'state')}")
    if hasattr(forest_model, 'state'):
        print(f"   forest_model.state: {forest_model.state}")
        if forest_model.state is not None:
            print(f"   forest_model.state.shape: {forest_model.state.shape}")
    
    print(f"   hasattr(forest_model, 'state_layers'): {hasattr(forest_model, 'state_layers')}")
    if hasattr(forest_model, 'state_layers'):
        print(f"   forest_model.state_layers: {forest_model.state_layers}")
        if forest_model.state_layers is not None:
            print(f"   Type: {type(forest_model.state_layers)}")
            if isinstance(forest_model.state_layers, dict):
                print(f"   Keys: {list(forest_model.state_layers.keys())}")
                for key, value in list(forest_model.state_layers.items())[:3]:
                    print(f"     {key}: {type(value)} - {getattr(value, 'shape', 'no shape')}")
                    if hasattr(value, 'toarray'):
                        try:
                            array = value.toarray()
                            print(f"       Array shape: {array.shape}")
                            print(f"       Burning cells: {np.sum(array == 2)}")
                        except Exception as e:
                            print(f"       Error converting to array: {e}")
    
    print()
    print("✅ Debug test completed!")

if __name__ == "__main__":
    import numpy as np
    test_forest_model()
