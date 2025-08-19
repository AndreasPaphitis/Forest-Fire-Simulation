#!/usr/bin/env python3
"""
Local Calibration Test with Limited Combinations

This script runs a local calibration test with:
- 2 workers only
- All optimizations enabled
- Limited to first 10% of combinations
- Comprehensive logging to see what's happening
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.calibration.grid_search import GridSearchCalibrator, create_progress_callback
from src.core.calibration.calibration_config import CalibrationConfig
from src.core.calibration.parameter_bounds import ParameterBounds, ParameterType, CalibrationTier
from src.core.calibration.objective_functions import SpatialSimilarityObjective

def setup_logging():
    """Set up comprehensive logging for debugging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('local_calibration_test.log')
        ]
    )
    
    # Set specific loggers to DEBUG for detailed output
    debug_loggers = [
        'src.core.calibration.grid_search',
        'src.core.forest_model',
        'src.core.fire_simulation_engine',
        'src.utils.shared_terrain'
    ]
    
    for logger_name in debug_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

def create_test_config():
    """Create a test configuration with all optimizations enabled."""
    config = CalibrationConfig()
    
    # Enable all optimizations
    config.base_config.memory_optimization_level = 3
    config.base_config.use_sparse_storage = True
    config.base_config.use_disk_storage = True
    config.base_config.stop_when_fire_extinguished = True
    
    # Set reasonable grid size for testing (smaller than HPC but still substantial)
    config.base_config.grid_size = (1000, 1000)  # 1M cells instead of 21M
    config.base_config.num_layers = 10
    config.base_config.max_steps = 200
    
    # Enable shared terrain
    config.base_config.use_terrain = True
    config.base_config.use_preprocessed_terrain = True
    config.base_config.preprocessed_terrain_dir = "preprocessed_terrain"
    
    # Set calibration parameters
    config.grid_search_points = 3  # Reduce from 5 to 3 for faster testing
    config.parallel_execution = True
    config.max_workers = 2  # Force 2 workers only
    
    return config

def create_parameter_bounds():
    """Create parameter bounds for testing."""
    return {
        'spread_probability': ParameterBounds(0.3, 0.7, 0.5, ParameterType.PROBABILITY, CalibrationTier.CRITICAL),
        'fuel_consumption_rate': ParameterBounds(0.0001, 0.001, 0.0005, ParameterType.POSITIVE_FLOAT, CalibrationTier.MODERATE),
        'ember_probability': ParameterBounds(0.1, 0.5, 0.3, ParameterType.PROBABILITY, CalibrationTier.LOW)
    }

def limit_combinations(calibrator, percentage=10):
    """Limit the parameter combinations to the first percentage."""
    total_combinations = calibrator.total_combinations
    limited_combinations = max(1, int(total_combinations * percentage / 100))
    
    print(f"🔧 LIMITING COMBINATIONS: {total_combinations} total -> {limited_combinations} ({percentage}%)")
    
    # Override the _generate_parameter_combinations method temporarily
    original_generator = calibrator._generate_parameter_combinations
    
    def limited_generator():
        count = 0
        for combo in original_generator():
            if count >= limited_combinations:
                break
            yield combo
            count += 1
    
    calibrator._generate_parameter_combinations = limited_generator
    calibrator.total_combinations = limited_combinations
    
    return limited_combinations

def main():
    """Run the local calibration test."""
    print("🚀 STARTING LOCAL CALIBRATION TEST")
    print("=" * 60)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create test configuration
        print("📋 Creating test configuration...")
        config = create_test_config()
        
        # Create parameter bounds
        print("🎯 Creating parameter bounds...")
        parameter_bounds = create_parameter_bounds()
        
        # Create objective function
        print("📊 Creating objective function...")
        objective_function = SpatialSimilarityObjective()
        
        # Create calibrator
        print("🔧 Creating GridSearchCalibrator...")
        calibrator = GridSearchCalibrator(
            calibration_config=config,
            parameter_bounds=parameter_bounds,
            objective_function=objective_function,
            parallel_execution=True,
            max_workers=2,  # Force 2 workers
            bypass_worker_limit=True  # Bypass HPC optimizations for local testing
        )
        
        # Get estimation info
        estimation = calibrator.get_estimation_info()
        print(f"📈 ESTIMATION: {estimation['total_combinations']} combinations")
        print(f"⏱️  ESTIMATED TIME: {estimation['estimated_time_hours']:.2f} hours")
        print(f"👥 WORKERS: {estimation['max_workers']}")
        
        # Limit combinations to 10%
        limited_combinations = limit_combinations(calibrator, percentage=10)
        
        # Create synthetic target data for testing
        print("🎯 Creating synthetic target data...")
        target_data = {
            'fire_perimeter': [(100, 100), (101, 100), (102, 100), (100, 101), (101, 101)],
            'fire_area': 5,
            'fire_duration': 10
        }
        
        # Create progress callback
        progress_callback = create_progress_callback(verbose=True)
        
        # Run calibration
        print("🔥 STARTING CALIBRATION...")
        print("=" * 60)
        
        start_time = time.time()
        results = calibrator.run_calibration(
            target_data=target_data,
            progress_callback=progress_callback
        )
        end_time = time.time()
        
        # Print results
        print("=" * 60)
        print("✅ CALIBRATION COMPLETED")
        print(f"⏱️  TOTAL TIME: {end_time - start_time:.2f} seconds")
        print(f"📊 TOTAL EVALUATIONS: {results.total_evaluations}")
        print(f"✅ SUCCESSFUL EVALUATIONS: {results.successful_evaluations}")
        print(f"❌ FAILED EVALUATIONS: {results.total_evaluations - results.successful_evaluations}")
        
        if results.best_result:
            print(f"🏆 BEST OBJECTIVE VALUE: {results.best_result.objective_value:.4f}")
            print(f"🎯 BEST PARAMETERS: {results.best_result.parameter_values}")
        else:
            print("⚠️  NO VALID RESULTS FOUND")
        
        # Save results
        results_file = "local_calibration_results.json"
        results.save_results(results_file)
        print(f"💾 Results saved to: {results_file}")
        
        # Print detailed statistics
        print("\n📊 DETAILED STATISTICS:")
        print(f"   Success rate: {results.successful_evaluations / max(results.total_evaluations, 1) * 100:.1f}%")
        print(f"   Average evaluation time: {results.total_time / max(results.total_evaluations, 1):.2f} seconds")
        
        if results.successful_evaluations > 0:
            valid_results = [r for r in results.results if r.is_valid]
            objective_values = [r.objective_value for r in valid_results]
            print(f"   Best objective: {max(objective_values):.4f}")
            print(f"   Worst objective: {min(objective_values):.4f}")
            print(f"   Average objective: {sum(objective_values) / len(objective_values):.4f}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ CALIBRATION FAILED: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main()
