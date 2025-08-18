#!/usr/bin/env python3
"""
Diagnostic script to understand why calibration objective function returns 0.
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

def diagnose_calibration_issue():
    """Diagnose why calibration objective function returns 0."""
    
    logger.info("🔍 Starting calibration issue diagnosis...")
    
    # Create a simple configuration
    config = create_config(
        grid_size=(50, 50),
        num_layers=3,
        initial_fuel_load=5.0,
        max_steps=10
    )
    
    logger.info(f"📋 Configuration created: grid_size={config.grid_size}, fuel_load={config.initial_fuel_load}")
    
    # Create forest model
    forest_model = create_forest_model(
        model_type='memory_optimized',
        grid_size=config.grid_size,
        num_layers=config.num_layers,
        config=config
    )
    
    logger.info(f"🌲 Forest model created: {type(forest_model).__name__}")
    logger.info(f"   Grid size: {forest_model.width} x {forest_model.height} x {forest_model.num_layers}")
    
    # Set ignition point
    ignition_x, ignition_y = forest_model.width // 2, forest_model.height // 2
    ignition_z = 0  # Ground layer
    
    logger.info(f"🔥 Setting ignition point at ({ignition_x}, {ignition_y}, {ignition_z})")
    
    # Set the ignition point
    try:
        forest_model.set_ignition(ignition_x, ignition_y, ignition_z)
        logger.info("✅ Ignition point set successfully")
    except Exception as e:
        logger.error(f"❌ Failed to set ignition point: {e}")
        return
    
    # Check initial state
    logger.info("🔍 Checking initial forest model state...")
    
    # Check if ignition point is actually burning
    try:
        initial_state = forest_model.state[ignition_x, ignition_y, ignition_z]
        logger.info(f"   Initial state at ignition point: {initial_state}")
        
        if initial_state == 1:  # BURNING
            logger.info("✅ Ignition point is burning")
        else:
            logger.error(f"❌ Ignition point is not burning! State: {initial_state}")
            return
    except Exception as e:
        logger.error(f"❌ Failed to check initial state: {e}")
        return
    
    # Check fuel load at ignition point
    try:
        fuel_at_ignition = forest_model.fuel_load[ignition_x, ignition_y, ignition_z]
        logger.info(f"   Fuel load at ignition point: {fuel_at_ignition}")
        
        if fuel_at_ignition > 0:
            logger.info("✅ Fuel load is positive")
        else:
            logger.error(f"❌ Fuel load is zero or negative: {fuel_at_ignition}")
            return
    except Exception as e:
        logger.error(f"❌ Failed to check fuel load: {e}")
        return
    
    # Run simulation
    logger.info("🚀 Running fire simulation...")
    
    engine = FireSimulationEngine(forest_model=forest_model, config=config)
    
    try:
        simulation_result = engine.run_simulation(max_steps=10)
        logger.info("✅ Simulation completed successfully")
    except Exception as e:
        logger.error(f"❌ Simulation failed: {e}")
        return
    
    # Check simulation results
    logger.info("📊 Analyzing simulation results...")
    
    stats = simulation_result.get('stats', {})
    logger.info(f"   Total burned cells: {stats.get('total_burned_cells', 0)}")
    logger.info(f"   Final active cells: {stats.get('final_active_cells', 0)}")
    logger.info(f"   Max active cells: {stats.get('max_active_cells', 0)}")
    logger.info(f"   Steps completed: {stats.get('steps', 0)}")
    
    # Check if forest_model is in the result
    if 'forest_model' not in simulation_result:
        logger.error("❌ No forest_model in simulation result!")
        return
    
    result_forest_model = simulation_result['forest_model']
    logger.info(f"✅ Forest model found in simulation result: {type(result_forest_model).__name__}")
    
    # Check final state of the forest model
    logger.info("🔍 Checking final forest model state...")
    
    try:
        # Check if any cells are burning in the final state
        if hasattr(result_forest_model.state, 'shape'):
            state_shape = result_forest_model.state.shape
            logger.info(f"   Final state shape: {state_shape}")
            
            # Count burning cells in final state
            if len(state_shape) == 3:
                # 3D array - check for burning cells (state == 1)
                burning_cells = np.sum(result_forest_model.state == 1)
                logger.info(f"   Burning cells in final state: {burning_cells}")
                
                if burning_cells > 0:
                    logger.info("✅ Fire is still burning in final state")
                else:
                    logger.warning("⚠️  No burning cells in final state")
                    
            elif len(state_shape) == 2:
                # 2D array
                burning_cells = np.sum(result_forest_model.state == 1)
                logger.info(f"   Burning cells in final state: {burning_cells}")
                
                if burning_cells > 0:
                    logger.info("✅ Fire is still burning in final state")
                else:
                    logger.warning("⚠️  No burning cells in final state")
            else:
                logger.warning(f"⚠️  Unexpected state shape: {state_shape}")
                
        else:
            logger.warning("⚠️  Forest model state has no shape attribute")
            
    except Exception as e:
        logger.error(f"❌ Failed to check final state: {e}")
    
    # Test objective function
    logger.info("🎯 Testing objective function...")
    
    objective_function = SpatialSimilarityObjective()
    
    try:
        objective_result = objective_function.evaluate(simulation_result, target_data=None)
        logger.info(f"✅ Objective function evaluation completed")
        logger.info(f"   Objective value: {objective_result.value}")
        logger.info(f"   Is valid: {objective_result.is_valid}")
        
        if not objective_result.is_valid:
            logger.error(f"❌ Objective result is invalid: {objective_result.error_message}")
            return
        
        # Check components
        components = objective_result.components
        logger.info("📊 Objective function components:")
        for key, value in components.items():
            logger.info(f"   {key}: {value}")
        
        if objective_result.value == 0.0:
            logger.error("❌ Objective value is 0.0!")
            
            # Check if predicted cells is 0
            predicted_cells = components.get('predicted_cells', 0)
            target_cells = components.get('target_cells', 0)
            
            logger.info(f"   Predicted cells: {predicted_cells}")
            logger.info(f"   Target cells: {target_cells}")
            
            if predicted_cells == 0:
                logger.error("❌ No predicted cells burned - this is the problem!")
                
                # Check if the forest model state actually has any burned cells
                try:
                    if hasattr(result_forest_model.state, 'shape'):
                        state_shape = result_forest_model.state.shape
                        
                        if len(state_shape) == 3:
                            # Check for burned cells (state == 2)
                            burned_cells = np.sum(result_forest_model.state == 2)
                            logger.info(f"   Burned cells in final state: {burned_cells}")
                            
                            if burned_cells == 0:
                                logger.error("❌ No burned cells in forest model state!")
                                logger.error("   This means the fire didn't spread at all")
                            else:
                                logger.warning(f"⚠️  {burned_cells} burned cells found, but objective function didn't detect them")
                                
                        elif len(state_shape) == 2:
                            burned_cells = np.sum(result_forest_model.state == 2)
                            logger.info(f"   Burned cells in final state: {burned_cells}")
                            
                            if burned_cells == 0:
                                logger.error("❌ No burned cells in forest model state!")
                            else:
                                logger.warning(f"⚠️  {burned_cells} burned cells found, but objective function didn't detect them")
                                
                except Exception as e:
                    logger.error(f"❌ Failed to check burned cells: {e}")
            else:
                logger.warning(f"⚠️  {predicted_cells} predicted cells, but objective value is still 0")
        else:
            logger.info(f"✅ Objective value is {objective_result.value} - this is good!")
            
    except Exception as e:
        logger.error(f"❌ Objective function evaluation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_calibration_issue()
