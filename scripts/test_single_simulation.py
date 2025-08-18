#!/usr/bin/env python3
"""
Single simulation test to isolate list.items() error.
This runs one simulation with the same parameters that cause the error in calibration.
"""

import os
import sys
import logging
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.fire_simulation_engine import FireSimulationEngine
from src.core.forest_model import create_forest_model
from src.core.calibration.calibration_config import CalibrationConfig
from src.utils.logging_utils import setup_logging

def main():
    """Run single simulation test to isolate list.items() error."""
    
    # Setup logging
    setup_logging(
        log_level=logging.DEBUG,
        log_file="test_output/single_simulation_test.log",
        console_level=logging.INFO
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting single simulation test to isolate list.items() error")
    
    # Load test configuration
    config_path = "hpc_deployment/local_calibration_test.json"
    if not os.path.exists(config_path):
        logger.error(f"❌ Test config not found: {config_path}")
        return False
    
    try:
        # Create calibration config
        logger.info("📋 Loading configuration...")
        calibration_config = CalibrationConfig.from_file(config_path)
        logger.info(f"✅ Loaded config: {calibration_config.config_name}")
        
        # Create a test parameter set (one that might cause the error)
        test_parameters = {
            'spread_probability': 0.3,
            'fuel_consumption_rate': 0.05,
            'ember_probability': 0.2,
            'ember_ignition': 0.35,
            'fuel_moisture_baseline': 0.2
        }
        
        logger.info(f"🧪 Testing with parameters: {test_parameters}")
        
        # Create config variant with test parameters
        logger.info("🔧 Creating config variant...")
        config_variant = calibration_config.create_config_variant(test_parameters)
        logger.info(f"✅ Created config variant type: {type(config_variant)}")
        
        # Create forest model
        logger.info("🌲 Creating forest model...")
        forest_model = create_forest_model(config_variant)
        logger.info(f"✅ Created forest model type: {type(forest_model)}")
        
        # Create simulation engine
        logger.info("🔥 Creating fire simulation engine...")
        engine = FireSimulationEngine(forest_model, config_variant)
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
