#!/usr/bin/env python3
"""
Detailed diagnostic script to understand fire spread issues during calibration.
"""

import sys
import os
import numpy as np
import logging

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.config_tools import create_config
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.calibration.objective_functions import SpatialSimilarityObjective

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def diagnose_fire_spread():
    """Diagnose why fire is not spreading during calibration."""
    
    logger.info("🔍 Starting fire spread diagnosis...")
    
    # Test different configurations to understand fire spread
    test_configs = [
        {
            'name': 'Basic Test',
            'grid_size': (50, 50),
            'num_layers': 3,
            'initial_fuel_load': 5.0,
            'max_steps': 20,
            'wind_speed': 5.0,
            'wind_direction': 0.0,
            'temperature': 25.0,
            'humidity': 50.0
        },
        {
            'name': 'Higher Fuel Load',
            'grid_size': (50, 50),
            'num_layers': 3,
            'initial_fuel_load': 10.0,
            'max_steps': 20,
            'wind_speed': 5.0,
            'wind_direction': 0.0,
            'temperature': 25.0,
            'humidity': 50.0
        },
        {
            'name': 'Higher Temperature',
            'grid_size': (50, 50),
            'num_layers': 3,
            'initial_fuel_load': 5.0,
            'max_steps': 20,
            'wind_speed': 5.0,
            'wind_direction': 0.0,
            'temperature': 35.0,
            'humidity': 30.0
        }
    ]
    
    for test_config in test_configs:
        logger.info(f"\n🧪 Testing configuration: {test_config['name']}")
        
        # Create configuration
        config = create_config(
            grid_size=test_config['grid_size'],
            num_layers=test_config['num_layers'],
            initial_fuel_load=test_config['initial_fuel_load'],
            max_steps=test_config['max_steps'],
            wind_speed=test_config['wind_speed'],
            wind_direction=test_config['wind_direction'],
            temperature=test_config['temperature'],
            humidity=test_config['humidity']
        )
        
        # Create forest model
        forest_model = create_forest_model(
            model_type='memory_optimized',
            grid_size=config.grid_size,
            num_layers=config.num_layers,
            config=config
        )
        
        # Set ignition point
        ignition_x, ignition_y = forest_model.width // 2, forest_model.height // 2
        ignition_z = 0
        
        forest_model.set_ignition(ignition_x, ignition_y, ignition_z)
        
        # Check initial conditions
        logger.info(f"   Initial fuel load: {forest_model.fuel_load[ignition_x, ignition_y, ignition_z]}")
        logger.info(f"   Initial state: {forest_model.state[ignition_x, ignition_y, ignition_z]}")
        
        # Check fuel load in neighboring cells
        neighbors = [
            (ignition_x-1, ignition_y, ignition_z),
            (ignition_x+1, ignition_y, ignition_z),
            (ignition_x, ignition_y-1, ignition_z),
            (ignition_x, ignition_y+1, ignition_z)
        ]
        
        logger.info("   Fuel load in neighboring cells:")
        for nx, ny, nz in neighbors:
            if 0 <= nx < forest_model.width and 0 <= ny < forest_model.height:
                fuel = forest_model.fuel_load[nx, ny, nz]
                state = forest_model.state[nx, ny, nz]
                logger.info(f"     ({nx}, {ny}, {nz}): fuel={fuel}, state={state}")
        
        # Run simulation
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        simulation_result = engine.run_simulation(max_steps=test_config['max_steps'])
        
        # Analyze results
        stats = simulation_result.get('stats', {})
        total_burned = stats.get('total_burned_cells', 0)
        max_active = stats.get('max_active_cells', 0)
        steps = stats.get('steps', 0)
        
        logger.info(f"   Results:")
        logger.info(f"     Total burned cells: {total_burned}")
        logger.info(f"     Max active cells: {max_active}")
        logger.info(f"     Steps completed: {steps}")
        
        if total_burned <= 1:
            logger.warning(f"   ⚠️  Fire did not spread! Only {total_burned} cell burned")
        else:
            logger.info(f"   ✅ Fire spread to {total_burned} cells")
        
        # Check final state
        result_forest_model = simulation_result['forest_model']
        
        # Count burned cells in final state
        if hasattr(result_forest_model.state, 'shape'):
            state_shape = result_forest_model.state.shape
            if len(state_shape) == 3:
                burned_cells = np.sum(result_forest_model.state == 2)  # BURNED state
                burning_cells = np.sum(result_forest_model.state == 1)  # BURNING state
                logger.info(f"   Final state analysis:")
                logger.info(f"     Burned cells: {burned_cells}")
                logger.info(f"     Still burning: {burning_cells}")
        
        # Test objective function
        objective_function = SpatialSimilarityObjective()
        objective_result = objective_function.evaluate(simulation_result, target_data=None)
        
        logger.info(f"   Objective value: {objective_result.value}")
        
        if objective_result.value < 0.01:
            logger.warning(f"   ⚠️  Very low objective value - fire spread insufficient")
        else:
            logger.info(f"   ✅ Good objective value")

def test_calibration_parameters():
    """Test the specific parameters used in calibration."""
    
    logger.info("\n🎯 Testing calibration parameters...")
    
    # Create a configuration similar to what might be used in calibration
    config = create_config(
        grid_size=(100, 100),  # Larger grid
        num_layers=3,
        initial_fuel_load=5.0,
        max_steps=50,  # More steps
        wind_speed=10.0,  # Higher wind
        wind_direction=45.0,  # Diagonal wind
        temperature=30.0,  # Higher temperature
        humidity=40.0  # Lower humidity
    )
    
    logger.info(f"Calibration-like configuration:")
    logger.info(f"   Grid size: {config.grid_size}")
    logger.info(f"   Fuel load: {config.initial_fuel_load}")
    logger.info(f"   Wind speed: {config.wind_speed}")
    logger.info(f"   Temperature: {config.temperature}")
    logger.info(f"   Humidity: {config.humidity}")
    
    # Create forest model
    forest_model = create_forest_model(
        model_type='memory_optimized',
        grid_size=config.grid_size,
        num_layers=config.num_layers,
        config=config
    )
    
    # Set ignition point
    ignition_x, ignition_y = forest_model.width // 2, forest_model.height // 2
    ignition_z = 0
    
    forest_model.set_ignition(ignition_x, ignition_y, ignition_z)
    
    # Run simulation
    engine = FireSimulationEngine(forest_model=forest_model, config=config)
    simulation_result = engine.run_simulation(max_steps=config.max_steps)
    
    # Analyze results
    stats = simulation_result.get('stats', {})
    total_burned = stats.get('total_burned_cells', 0)
    max_active = stats.get('max_active_cells', 0)
    steps = stats.get('steps', 0)
    
    logger.info(f"Calibration test results:")
    logger.info(f"   Total burned cells: {total_burned}")
    logger.info(f"   Max active cells: {max_active}")
    logger.info(f"   Steps completed: {steps}")
    
    if total_burned < 10:
        logger.error(f"   ❌ Insufficient fire spread for calibration! Only {total_burned} cells burned")
        logger.error(f"   This explains why calibration returns 0.0 objective values")
    else:
        logger.info(f"   ✅ Adequate fire spread for calibration")
    
    # Test objective function
    objective_function = SpatialSimilarityObjective()
    objective_result = objective_function.evaluate(simulation_result, target_data=None)
    
    logger.info(f"   Objective value: {objective_result.value}")
    
    if objective_result.value < 0.01:
        logger.error(f"   ❌ Objective value too low for calibration")
    else:
        logger.info(f"   ✅ Objective value acceptable for calibration")

if __name__ == "__main__":
    diagnose_fire_spread()
    test_calibration_parameters()
