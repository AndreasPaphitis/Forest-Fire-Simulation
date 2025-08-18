#!/usr/bin/env python3
"""
Local calibration test script to reproduce list.items() error quickly.
This runs a minimal calibration with comprehensive debugging enabled.
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

from src.core.calibration.grid_search import GridSearchCalibrator
from src.core.calibration.calibration_config import CalibrationConfig
def main():
    """Run local calibration test with comprehensive debugging."""
    
    # Setup basic logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("test_output/local_calibration_test.log"),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting local calibration test to reproduce list.items() error")
    
    # Load test configuration
    config_path = "hpc_deployment/local_calibration_test.json"
    if not os.path.exists(config_path):
        logger.error(f"❌ Test config not found: {config_path}")
        return False
    
    try:
        # Create calibration config
        logger.info("📋 Loading calibration configuration...")
        calibration_config = CalibrationConfig.load_config(config_path)
        logger.info(f"✅ Loaded config: {calibration_config.config_name}")
        
        # Create calibrator
        logger.info("🔧 Creating grid search calibrator...")
        calibrator = GridSearchCalibrator(calibration_config)
        logger.info(f"✅ Created calibrator with {len(calibrator.parameter_space)} parameters")
        
        # Run calibration
        logger.info("🔥 Starting calibration grid search...")
        start_time = time.time()
        
        results = calibrator.run_calibration()
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"✅ Calibration completed in {duration:.2f} seconds")
        logger.info(f"📊 Results: {len(results.evaluations)} evaluations completed")
        
        # Check for errors
        failed_evaluations = [e for e in results.evaluations if not e.get('is_valid', True)]
        if failed_evaluations:
            logger.warning(f"⚠️  {len(failed_evaluations)} evaluations failed")
            for i, eval_result in enumerate(failed_evaluations[:3]):  # Show first 3
                logger.warning(f"  Failed evaluation {i+1}: {eval_result.get('error_message', 'Unknown error')}")
        else:
            logger.info("✅ All evaluations completed successfully")
        
        # Show best result
        if results.best_evaluation:
            logger.info(f"🏆 Best objective value: {results.best_evaluation['objective_value']:.6f}")
            logger.info(f"🏆 Best parameters: {results.best_evaluation['parameter_values']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Calibration test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
