#!/usr/bin/env python3
"""
Simple calibration test to reproduce list.items() error.
This runs a minimal calibration using the existing grid search structure.
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
from src.core.calibration.calibration_config import CalibrationConfig, create_default_calibration_config
from src.core.calibration.parameter_bounds import get_default_calibration_bounds
from src.core.calibration.objective_functions import create_default_spatial_objective
from src.config.config_tools import ModelConfig

def main():
	"""Run simple calibration test to reproduce list.items() error."""
	
	# Setup basic logging
	logging.basicConfig(
		level=logging.DEBUG,
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		handlers=[
			logging.FileHandler("test_output/calibration_simple_test.log"),
			logging.StreamHandler()
		]
	)
	
	logger = logging.getLogger(__name__)
	logger.info("🚀 Starting simple calibration test to reproduce list.items() error")
	
	try:
		# Create a simple base config
		logger.info("📋 Creating base configuration...")
		base_config = ModelConfig(
			grid_size=(50, 50),
			num_layers=3,
			max_steps=3,
			debug=True,
			store_full_states=False,
			use_terrain=False,
			use_lidar=False,
			save_visualizations=False
		)
		
		# Create calibration config
		logger.info("🔧 Creating calibration configuration...")
		calibration_config = create_default_calibration_config(
			experiment_name="simple_test",
			base_config=base_config
		)
		
		# Set minimal parameter space for quick testing
		calibration_config.calibration_parameters = [
			'spread_probability',
			'fuel_consumption_rate'
		]
		
		# Set minimal grid search
		calibration_config.grid_search_points = 2
		calibration_config.max_workers = 2
		calibration_config.parallel_execution = True
		
		# Add simple target data
		calibration_config.calibration_targets = []
		
		logger.info(f"✅ Created calibration config: {calibration_config.experiment_name}")
		logger.info(f"📊 Parameter space: {len(calibration_config.calibration_parameters)} parameters")
		logger.info(f"🔍 Grid search points: {calibration_config.grid_search_points}")
		
		# Get parameter bounds and objective function
		logger.info("🔧 Getting parameter bounds and objective function...")
		parameter_bounds = get_default_calibration_bounds()
		objective_function = create_default_spatial_objective()
		
		# Create calibrator
		logger.info("🔧 Creating grid search calibrator...")
		calibrator = GridSearchCalibrator(
			calibration_config=calibration_config,
			parameter_bounds=parameter_bounds,
			objective_function=objective_function,
			parallel_execution=True,
			max_workers=2
		)
		logger.info(f"✅ Created calibrator with {len(calibrator.parameter_space)} parameters")
		
		# Run calibration
		logger.info("🔥 Starting calibration grid search...")
		start_time = time.time()
		
		results = calibrator.run_calibration()
		
		end_time = time.time()
		duration = end_time - start_time
		
		logger.info(f"✅ Calibration completed in {duration:.2f} seconds")
		logger.info(f"📊 Results: {len(results.results)} evaluations completed")
		
		# Check for errors
		failed_evaluations = [e for e in results.results if not e.is_valid]
		if failed_evaluations:
			logger.warning(f"⚠️  {len(failed_evaluations)} evaluations failed")
			for i, eval_result in enumerate(failed_evaluations[:3]):  # Show first 3
				logger.warning(f"  Failed evaluation {i+1}: {getattr(eval_result, 'error_message', 'Unknown error')}")
		else:
			logger.info("✅ All evaluations completed successfully")
		
		# Show best result
		if results.best_result:
			logger.info(f"🏆 Best objective value: {results.best_result.objective_value:.6f}")
			logger.info(f"🏆 Best parameters: {results.best_result.parameter_values}")
		
		return True
		
	except Exception as e:
		logger.error(f"❌ Calibration test failed: {e}")
		import traceback
		logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
		return False

if __name__ == "__main__":
	success = main()
	sys.exit(0 if success else 1)
