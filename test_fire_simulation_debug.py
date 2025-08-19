#!/usr/bin/env python3
"""
Debug fire simulation parameters to understand why fire isn't spreading.
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.config_tools import ModelConfig
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine

def test_fire_spread_debug():
    """Test fire spread with different parameter combinations."""
    
    print("🧪 DEBUGGING FIRE SIMULATION PARAMETERS")
    print("=" * 50)
    
    # Test different parameter combinations
    test_cases = [
        {
            'name': 'Default Config',
            'params': {
                'grid_size': (50, 50),
                'num_layers': 5,
                'max_steps': 10,
                'spread_probability': 0.75,
                'fuel_consumption_rate': 0.5,
                'ignition_threshold': 0.08,
                'min_fuel_value': 0.05,
                'max_fuel_value': 1.0,
                'initial_fuel_load': 0.5
            }
        },
        {
            'name': 'Calibration Test Values',
            'params': {
                'grid_size': (50, 50),
                'num_layers': 5,
                'max_steps': 10,
                'spread_probability': 0.3,  # From calibration test
                'fuel_consumption_rate': 0.0001,  # From calibration test - VERY LOW
                'ignition_threshold': 0.08,
                'min_fuel_value': 0.05,
                'max_fuel_value': 1.0,
                'initial_fuel_load': 0.5
            }
        },
        {
            'name': 'Optimized for Spread',
            'params': {
                'grid_size': (50, 50),
                'num_layers': 5,
                'max_steps': 10,
                'spread_probability': 0.8,
                'fuel_consumption_rate': 0.1,  # Moderate consumption
                'ignition_threshold': 0.05,  # Very low threshold
                'min_fuel_value': 0.01,
                'max_fuel_value': 1.0,
                'initial_fuel_load': 0.8
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🔬 TEST CASE {i+1}: {test_case['name']}")
        print("-" * 30)
        
        # Create config
        config = ModelConfig(**test_case['params'])
        print(f"   Grid size: {config.grid_size}")
        print(f"   Spread probability: {config.spread_probability}")
        print(f"   Fuel consumption rate: {config.fuel_consumption_rate}")
        print(f"   Ignition threshold: {config.ignition_threshold}")
        print(f"   Min fuel value: {config.min_fuel_value}")
        print(f"   Initial fuel load: {config.initial_fuel_load}")
        
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
                continue
                
            # Analyze results
            stats = result.get('stats', {})
            active_cells = stats.get('active_cells', 0)
            burned_cells = stats.get('total_burned_cells', 0)  # Use correct key
            total_steps = stats.get('total_steps', 0)
            
            print(f"   ✅ Simulation completed:")
            print(f"      - Total steps: {total_steps}")
            print(f"      - Active cells: {active_cells}")
            print(f"      - Burned cells: {burned_cells}")
            
            if burned_cells > 1:
                print(f"   🎉 FIRE SPREAD SUCCESSFUL! Burned {burned_cells} cells")
            else:
                print(f"   ⚠️  Fire did not spread significantly")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_fire_spread_debug()
