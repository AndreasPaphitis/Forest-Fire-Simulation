#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Analyze Simulation Timing and Fuel Consumption

This script investigates why simulations are finishing too quickly and analyzes
the fuel consumption mechanism to understand the root cause.

Author: Forest Fire Simulation Team
Date: 2025
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_tools import ModelConfig
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine

def analyze_fuel_consumption():
    """Analyze how fuel consumption affects simulation duration."""
    print("🔍 Analyzing Fuel Consumption Impact")
    print("=" * 60)
    
    # Test different fuel consumption rates
    fuel_rates = [0.1, 0.3, 0.5, 1.0, 2.0, 5.0]
    
    for fuel_rate in fuel_rates:
        print(f"\n🔥 Testing fuel_consumption_rate: {fuel_rate}")
        print("-" * 40)
        
        config = ModelConfig(
            grid_size=(50, 50),  # Smaller grid for faster testing
            num_layers=3,
            max_steps=50,  # More steps to see the effect
            fuel_consumption_rate=fuel_rate,
            spread_probability=0.8,
            ignition_threshold=0.1,
            use_terrain=True,
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain"
        )
        
        try:
            # Create forest model
            forest_model = create_forest_model(model_type="standard", config=config)
            
            # Set ignition points
            grid_width, grid_height = config.grid_size if isinstance(config.grid_size, tuple) else (config.grid_size, config.grid_size)
            ignition_points = [
                (grid_width // 2, grid_height // 2, 0),
                (grid_width // 2 + 1, grid_height // 2, 0),
                (grid_width // 2, grid_height // 2 + 1, 0)
            ]
            
            for x, y, z in ignition_points:
                if 0 <= x < grid_width and 0 <= y < grid_height and 0 <= z < config.num_layers:
                    forest_model.state[x, y, z] = 1  # BURNING
            
            # Create simulation engine
            engine = FireSimulationEngine(forest_model=forest_model, config=config)
            
            # Run simulation
            result = engine.run_simulation()
            
            # Check results
            stats = result.get('stats', {})
            total_burned = stats.get('total_burned_cells', 0)
            steps = stats.get('steps', 0)
            runtime = stats.get('runtime_seconds', 0)
            
            print(f"   Steps completed: {steps}/{config.max_steps}")
            print(f"   Total burned cells: {total_burned}")
            print(f"   Runtime: {runtime:.3f} seconds")
            print(f"   Burnout rate: {total_burned/steps:.1f} cells/step" if steps > 0 else "   Burnout rate: N/A")
            
            # Calculate fuel consumption analysis
            initial_fuel = config.initial_fuel_load
            min_fuel = config.min_fuel_value
            steps_to_burnout = (initial_fuel - min_fuel) / fuel_rate if fuel_rate > 0 else float('inf')
            
            print(f"   Theoretical steps to burnout: {steps_to_burnout:.1f}")
            print(f"   Fuel consumption per step: {fuel_rate}")
            
            if steps < config.max_steps:
                print(f"   ⚠️  Simulation stopped early (fire extinguished)")
            else:
                print(f"   ✅ Simulation completed all steps")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def analyze_simulation_steps():
    """Analyze what happens in each simulation step."""
    print("\n📊 Analyzing Simulation Steps")
    print("=" * 60)
    
    config = ModelConfig(
        grid_size=(30, 30),  # Very small grid for detailed analysis
        num_layers=2,
        max_steps=10,  # Few steps for detailed analysis
        fuel_consumption_rate=0.3,  # Moderate rate
        spread_probability=0.8,
        ignition_threshold=0.1,
        use_terrain=True,
        use_preprocessed_terrain=True,
        preprocessed_terrain_dir="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain"
    )
    
    try:
        # Create forest model
        forest_model = create_forest_model(model_type="standard", config=config)
        
        # Set single ignition point
        grid_width, grid_height = config.grid_size if isinstance(config.grid_size, tuple) else (config.grid_size, config.grid_size)
        ignition_point = (grid_width // 2, grid_height // 2, 0)
        forest_model.state[ignition_point[0], ignition_point[1], ignition_point[2]] = 1
        
        print(f"Grid size: {grid_width}x{grid_height}x{config.num_layers} = {grid_width * grid_height * config.num_layers} total cells")
        print(f"Ignition point: {ignition_point}")
        print(f"Initial fuel load: {config.initial_fuel_load}")
        print(f"Min fuel value: {config.min_fuel_value}")
        print(f"Fuel consumption rate: {config.fuel_consumption_rate}")
        print(f"Steps to burnout: {(config.initial_fuel_load - config.min_fuel_value) / config.fuel_consumption_rate:.1f}")
        
        # Create simulation engine
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Run simulation with step-by-step analysis
        print("\nStep-by-step analysis:")
        print("-" * 40)
        
        for step in range(config.max_steps):
            # Check current state before step
            active_cells = len(engine.active_cells)
            burned_cells = len(engine.burned_cells)
            
            print(f"Step {step+1}: Active={active_cells}, Burned={burned_cells}")
            
            if active_cells == 0:
                print(f"   Fire extinguished after {step+1} steps")
                break
            
            # Process one step
            engine._process_step()
            
            # Check state after step
            new_active_cells = len(engine.active_cells)
            new_burned_cells = len(engine.burned_cells)
            
            print(f"   After step: Active={new_active_cells}, Burned={new_burned_cells}")
            print(f"   Change: Active={new_active_cells-active_cells:+d}, Burned={new_burned_cells-burned_cells:+d}")
            
            if new_active_cells == 0:
                print(f"   Fire extinguished after {step+1} steps")
                break
                
    except Exception as e:
        print(f"❌ Error in step analysis: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

def analyze_parameter_impact():
    """Analyze the impact of different parameters on simulation duration."""
    print("\n⚙️ Analyzing Parameter Impact")
    print("=" * 60)
    
    # Test different parameter combinations
    test_cases = [
        {
            'name': 'Low fuel consumption, high spread',
            'params': {
                'fuel_consumption_rate': 0.1,
                'spread_probability': 0.9,
                'ignition_threshold': 0.05
            }
        },
        {
            'name': 'High fuel consumption, low spread',
            'params': {
                'fuel_consumption_rate': 1.0,
                'spread_probability': 0.3,
                'ignition_threshold': 0.3
            }
        },
        {
            'name': 'Balanced parameters',
            'params': {
                'fuel_consumption_rate': 0.3,
                'spread_probability': 0.6,
                'ignition_threshold': 0.1
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 {test_case['name']}")
        print("-" * 30)
        
        config = ModelConfig(
            grid_size=(40, 40),
            num_layers=3,
            max_steps=30,
            **test_case['params'],
            use_terrain=True,
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain"
        )
        
        try:
            # Create forest model
            forest_model = create_forest_model(model_type="standard", config=config)
            
            # Set ignition points
            grid_width, grid_height = config.grid_size if isinstance(config.grid_size, tuple) else (config.grid_size, config.grid_size)
            ignition_points = [
                (grid_width // 2, grid_height // 2, 0),
                (grid_width // 2 + 1, grid_height // 2, 0)
            ]
            
            for x, y, z in ignition_points:
                if 0 <= x < grid_width and 0 <= y < grid_height and 0 <= z < config.num_layers:
                    forest_model.state[x, y, z] = 1
            
            # Create simulation engine
            engine = FireSimulationEngine(forest_model=forest_model, config=config)
            
            # Run simulation
            result = engine.run_simulation()
            
            # Check results
            stats = result.get('stats', {})
            total_burned = stats.get('total_burned_cells', 0)
            steps = stats.get('steps', 0)
            runtime = stats.get('runtime_seconds', 0)
            
            print(f"   Steps: {steps}/{config.max_steps}")
            print(f"   Burned cells: {total_burned}")
            print(f"   Runtime: {runtime:.3f}s")
            print(f"   Efficiency: {total_burned/steps:.1f} cells/step" if steps > 0 else "   Efficiency: N/A")
            
            # Parameter summary
            print(f"   Fuel consumption: {config.fuel_consumption_rate}")
            print(f"   Spread probability: {config.spread_probability}")
            print(f"   Ignition threshold: {config.ignition_threshold}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

def main():
    """Run all timing analysis tests."""
    print("🔍 SIMULATION TIMING ANALYSIS")
    print("=" * 80)
    
    analyze_fuel_consumption()
    analyze_simulation_steps()
    analyze_parameter_impact()
    
    print("\n📋 Summary:")
    print("=" * 40)
    print("The analysis will help identify:")
    print("1. How fuel consumption rate affects simulation duration")
    print("2. What happens in each simulation step")
    print("3. Which parameters have the biggest impact on timing")
    print("4. Whether simulations are terminating prematurely")

if __name__ == "__main__":
    main()
