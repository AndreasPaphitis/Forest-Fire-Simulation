#!/usr/bin/env python3
"""
Local Calibration Test with Mock Terrain and Real LiDAR

This script runs a local calibration test with:
- Mock terrain setup (no preprocessed terrain required)
- Real LiDAR data from PAD Results
- Actual Day 4 grid size (4788, 4490)
- 2 workers only
- All optimizations enabled
- Limited to first 10% of combinations
"""

import sys
import os
import time
import logging
from pathlib import Path
import numpy as np

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
            logging.FileHandler('local_calibration_mock_terrain.log')
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

def create_mock_terrain_config():
    """Create a test configuration with mock terrain and real LiDAR."""
    config = CalibrationConfig()
    
    # Enable all optimizations
    config.base_config.memory_optimization_level = 3
    config.base_config.use_sparse_storage = True
    config.base_config.use_disk_storage = True
    config.base_config.stop_when_fire_extinguished = True
    
    # Use smaller grid size for testing (to avoid memory issues)
    config.base_config.grid_size = (200, 200)  # 40K cells - manageable for testing
    config.base_config.num_layers = 10
    config.base_config.max_steps = 30  # Reduced for faster testing
    
    # Use mock terrain (no preprocessed terrain)
    config.base_config.use_terrain = False  # Disable terrain to use mock
    config.base_config.use_preprocessed_terrain = False
    config.base_config.preprocessed_terrain_dir = None
    
    # Use real LiDAR data from PAD Results
    config.base_config.use_lidar = True
    config.base_config.lidar_data_dir = "C:/Users/user/Desktop/UvA/YEAR 2/Thesis/LiDAR/Analysis files/Processed/PAD Results"
    config.base_config.auto_size_from_lidar = False  # We're setting grid size manually
    
    # Set calibration parameters
    config.grid_search_points = 3  # Reduce for faster testing
    config.parallel_execution = True
    config.max_workers = 2  # Force 2 workers only
    
    return config

def create_parameter_bounds():
    """Create parameter bounds for testing."""
    return {
        # TOP 5 PARAMETERS FROM SENSITIVITY ANALYSIS (2025-08-18 results)
        'spread_probability': ParameterBounds(0.6, 0.9, 0.75, ParameterType.PROBABILITY, CalibrationTier.CRITICAL),        # 1.4063 - CRITICAL
        'fuel_consumption_rate': ParameterBounds(0.1, 0.5, 0.25, ParameterType.POSITIVE_FLOAT, CalibrationTier.CRITICAL),   # 0.1609 - CRITICAL
        'ember_probability': ParameterBounds(0.1, 0.5, 0.3, ParameterType.PROBABILITY, CalibrationTier.CRITICAL),           # 0.1159 - CRITICAL
        'ember_ignition': ParameterBounds(0.01, 0.1, 0.05, ParameterType.POSITIVE_FLOAT, CalibrationTier.CRITICAL),        # 0.0564 - CRITICAL
        'fuel_moisture_baseline': ParameterBounds(0.1, 0.5, 0.3, ParameterType.PROBABILITY, CalibrationTier.MODERATE)      # 0.0382 - MODERATE
    }

def create_real_target_data():
    """Create target data based on actual Day 4 EMSR data."""
    # Create a 2D array representing the fire perimeter
    # Using the actual Day 4 grid size
    grid_size = (4788, 4490)
    
    # Create empty target array
    target_2d = np.zeros(grid_size, dtype=float)
    
    # Define fire perimeter coordinates (synthetic for testing)
    # These should be within the grid bounds
    fire_perimeter_coords = [
        (1000, 1000), (1001, 1000), (1002, 1000), (1003, 1000), (1004, 1000),
        (1000, 1001), (1001, 1001), (1002, 1001), (1003, 1001), (1004, 1001),
        (1000, 1002), (1001, 1002), (1002, 1002), (1003, 1002), (1004, 1002),
        (1000, 1003), (1001, 1003), (1002, 1003), (1003, 1003), (1004, 1003),
        (1000, 1004), (1001, 1004), (1002, 1004), (1003, 1004), (1004, 1004)
    ]
    
    # Mark fire perimeter cells as burned (value = 1.0)
    for x, y in fire_perimeter_coords:
        if 0 <= x < grid_size[0] and 0 <= y < grid_size[1]:
            target_2d[x, y] = 1.0
    
    # Create target data dictionary
    target_data = {
        'fire_perimeter': target_2d,  # 2D array instead of list of coordinates
        'fire_area': len(fire_perimeter_coords),
        'fire_duration': 10
    }
    
    print(f"🎯 Created target data: {target_2d.shape} array with {len(fire_perimeter_coords)} fire cells")
    print(f"   Fire area: {target_data['fire_area']} cells")
    print(f"   Target array sum: {np.sum(target_2d)}")
    
    return target_data

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

def check_data_availability():
    """Check if required data files are available."""
    print("🔍 CHECKING DATA AVAILABILITY:")
    
    # Check LiDAR data directory
    lidar_path = Path("C:/Users/user/Desktop/UvA/YEAR 2/Thesis/LiDAR/Analysis files/Processed/PAD Results")
    print(f"   LiDAR PAD Results: {'✅' if lidar_path.exists() else '❌'} {lidar_path}")
    
    if lidar_path.exists():
        # Count LiDAR tiles
        lidar_tiles = list(lidar_path.glob("PNOA_*_vegetation"))
        print(f"   LiDAR tiles found: {len(lidar_tiles)}")
        if lidar_tiles:
            print(f"   Sample tile: {lidar_tiles[0].name}")
    
    # Check EMSR data
    emsr_path = Path("EMSR Delineations/Day 4 (26_08_23)")
    print(f"   EMSR Day 4: {'✅' if emsr_path.exists() else '❌'} {emsr_path}")
    
    return True

def main():
    """Run the local calibration test with mock terrain and real LiDAR."""
    print("🚀 STARTING LOCAL CALIBRATION TEST WITH MOCK TERRAIN + REAL LIDAR")
    print("=" * 75)
    
    # Check data availability
    check_data_availability()
    print()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create test configuration
        print("📋 Creating mock terrain + real LiDAR configuration...")
        config = create_mock_terrain_config()
        
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
        
        # Create target data
        print("🎯 Creating target data...")
        target_data = create_real_target_data()
        
        # Create progress callback
        progress_callback = create_progress_callback(verbose=True)
        
        # Run calibration
        print("🔥 STARTING CALIBRATION WITH MOCK TERRAIN + REAL LIDAR...")
        print("=" * 75)
        
        start_time = time.time()
        results = calibrator.run_calibration(
            target_data=target_data,
            progress_callback=progress_callback
        )
        end_time = time.time()
        
        # Print results
        print("=" * 75)
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
        results_file = "local_calibration_mock_terrain_results.json"
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
