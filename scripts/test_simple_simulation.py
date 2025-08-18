#!/usr/bin/env python3
"""
Simple simulation test to isolate list.items() error.
This runs one simulation using the existing ModelConfig structure.
"""

import os
import sys
import logging
import time
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.forest_model import create_forest_model
from src.config.config_tools import ModelConfig, load_config
from src.utils.logging_utils import get_logger

def main():
    """Run simple simulation test to isolate list.items() error."""
    
    # Setup basic logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("test_output/simple_simulation_test.log"),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting simple simulation test to isolate list.items() error")
    
    # Load test configuration
    config_path = "hpc_deployment/Forest_Fire_Simulation_local_test.json"
    if not os.path.exists(config_path):
        logger.error(f"❌ Test config not found: {config_path}")
        return False
    
    try:
        # Create model config
        logger.info("📋 Loading configuration...")
        config = load_config(config_path)
        logger.info(f"✅ Loaded config: {config.config_name}")
        
        # Create forest model
        logger.info("🌲 Creating forest model...")
        forest_model = create_forest_model("memory_optimized", config)
        logger.info(f"✅ Created forest model type: {type(forest_model)}")
        
        # Create simulation engine
        logger.info("🔥 Creating fire simulation engine...")
        engine = FireSimulationEngine(forest_model, config)
        logger.info(f"✅ Created engine type: {type(engine)}")
        
        # Run simulation
        logger.info("🚀 Starting simulation...")
        start_time = time.time()
        
        try:
            simulation_result = engine.run_simulation()
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"✅ Simulation completed successfully in {duration:.2f} seconds")
            logger.info(f"📊 Simulation stats: {simulation_result.get('stats', {})}")
            
            return True
            
        except AttributeError as attr_error:
            if "'list' object has no attribute 'items'" in str(attr_error):
                logger.error(f"❌ REPRODUCED: List object error in simulation: {attr_error}")
                import traceback
                logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
                return False
            else:
                logger.error(f"❌ AttributeError in simulation: {attr_error}")
                raise attr_error
                
        except Exception as sim_error:
            logger.error(f"❌ Simulation failed with error: {type(sim_error)} = {sim_error}")
            import traceback
            logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
