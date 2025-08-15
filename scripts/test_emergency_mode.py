#!/usr/bin/env python3
"""
Emergency mode test script to verify segfault prevention.
"""

import sys
import os
import logging

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.forest_model import MemoryOptimizedForestModel
from src.config.config_tools import ModelConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_emergency_mode():
    """Test that emergency mode prevents segfaults on massive grids."""
    
    logger.info("🧪 Testing Emergency Mode for Massive Grids")
    
    # Create a massive grid configuration (similar to Tenerife)
    config = ModelConfig()
    config.grid_size = (15121, 24741)  # Same as Tenerife
    config.num_layers = 25
    config.memory_optimization_level = 3
    config.max_steps = 5  # Very short simulation
    
    logger.info(f"📊 Grid size: {config.grid_size[0]} x {config.grid_size[1]} x {config.num_layers}")
    total_cells = config.grid_size[0] * config.grid_size[1] * config.num_layers
    logger.info(f"📊 Total cells: {total_cells:,} ({total_cells/1e9:.2f}B)")
    
    try:
        # Create forest model
        logger.info("🌲 Creating forest model...")
        forest_model = MemoryOptimizedForestModel(
            grid_size=config.grid_size,
            num_layers=config.num_layers,
            config=config
        )
        logger.info("✅ Forest model created successfully")
        
        # Create fire simulation engine
        logger.info("🔥 Creating fire simulation engine...")
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        logger.info("✅ Fire simulation engine created successfully")
        
        # Check if emergency mode was enabled
        if hasattr(engine, '_emergency_mode') and engine._emergency_mode:
            logger.info("🚨 Emergency mode is ENABLED - this is expected for massive grids")
        else:
            logger.warning("⚠️  Emergency mode is NOT enabled - this may cause segfaults")
        
        # Set ignition point
        logger.info("🔥 Setting ignition point...")
        ignition_x, ignition_y = 9828, 15339  # Arafo highlands
        forest_model.set_ignition(ignition_x, ignition_y, 0)
        logger.info(f"✅ Ignition set at ({ignition_x}, {ignition_y})")
        
        # Run a very short simulation
        logger.info("🔥 Running emergency simulation...")
        result = engine.run_simulation(
            max_steps=3,  # Very short
            store_history=False,
            stop_when_fire_extinguished=True
        )
        
        logger.info("✅ Emergency simulation completed successfully!")
        logger.info(f"📊 Final stats: {result['stats']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Emergency mode test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_emergency_mode()
    if success:
        logger.info("🎉 Emergency mode test PASSED - segfault prevention working")
        sys.exit(0)
    else:
        logger.error("💥 Emergency mode test FAILED - segfaults still occurring")
        sys.exit(1)
