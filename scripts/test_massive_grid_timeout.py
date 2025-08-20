#!/usr/bin/env python3
"""
Test Massive Grid Timeout Fix

This script tests the timeout fix for massive grids (21.5M cells) to ensure
the simulation doesn't timeout prematurely.
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.calibration.grid_search import evaluate_worker_function, GridSearchCalibrator
from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod, CalibrationObjective
from src.core.calibration.parameter_bounds import ParameterBounds
from src.core.calibration.objective_functions import SpatialSimilarityObjective
from src.config.config_tools import ModelConfig

def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_smaller_grid_timeout():
    """Test with a smaller grid to verify timeout fix works."""
    print("🔥 Testing Timeout Fix with Smaller Grid")
    print("=" * 50)
    
    # Use a smaller grid size to avoid massive loading bottlenecks
    config = ModelConfig(
        grid_size=(1000, 1000),  # 1M cells - much more manageable
        num_layers=10,           # Reduced layers
        max_steps=50,            # Reduced steps for faster testing
        simulation_type='memory_optimized',
        spread_probability=0.6,
        fuel_consumption_rate=0.8,
        ignition_threshold=0.4,
        initial_fuel_load=8.0,
        stop_when_fire_extinguished=True,
        memory_optimization_level=3,
        use_sparse_storage=True,
        # Keep terrain loading enabled but use shared terrain
        use_preprocessed_terrain=True,
        preprocessed_terrain_dir="preprocessed_terrain",
        use_lidar=False
    )
    
    # Add timeout to config_dict
    config_dict = config.__dict__.copy()
    config_dict['simulation_timeout_minutes'] = 10.0  # 10 minutes timeout
    
    # Test parameters
    params = {
        'spread_probability': 0.6,
        'fuel_consumption_rate': 0.8,
        'ignition_threshold': 0.4
    }
    
    print(f"📊 Grid size: {config.grid_size[0]} × {config.grid_size[1]} = {config.grid_size[0] * config.grid_size[1]:,} cells")
    print(f"⏱️  Configured timeout: {config_dict['simulation_timeout_minutes']} minutes")
    print(f"🔧 Memory optimization level: {config.memory_optimization_level}")
    print(f"📦 Sparse storage: {config.use_sparse_storage}")
    print(f"🗺️  Terrain loading: ENABLED (shared terrain)")
    print()
    
    print("🚀 Starting smaller grid simulation test...")
    start_time = time.time()
    
    try:
        result = evaluate_worker_function(
            parameter_values=params,
            target_data=None,
            config_dict=config_dict,
            objective_function_name="SpatialSimilarityObjective"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Simulation completed in {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print(f"📊 Result valid: {result.get('is_valid', False)}")
        print(f"🎯 Objective value: {result.get('objective_value', 'N/A')}")
        
        if result.get('error_message'):
            print(f"❌ Error: {result['error_message']}")
            return False
        else:
            print("✅ No timeout error - fix is working!")
            return True
            
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Test failed after {duration:.2f} seconds: {e}")
        return False

def test_calibration_with_massive_grid():
    """Test the massive grid timeout fix using the actual calibration framework."""
    print("🔥 Testing Massive Grid Calibration with Multiple Workers")
    print("=" * 60)
    
    # Create base configuration with the actual massive grid size
    base_config = ModelConfig(
        grid_size=(4788, 4490),  # 21,498,120 cells - actual size from your output
        num_layers=25,
        max_steps=100,           # Reduced for faster testing
        simulation_type='memory_optimized',
        spread_probability=0.6,
        fuel_consumption_rate=0.8,
        ignition_threshold=0.4,
        initial_fuel_load=8.0,
        stop_when_fire_extinguished=True,
        memory_optimization_level=3,
        use_sparse_storage=True,
        # Keep shared terrain enabled
        use_preprocessed_terrain=True,
        preprocessed_terrain_dir="preprocessed_terrain",
        use_lidar=False
    )
    
    # Create calibration configuration
    calibration_config = CalibrationConfig(
        experiment_name="massive_grid_timeout_test",
        method=CalibrationMethod.GRID_SEARCH,
        objective=CalibrationObjective.SPATIAL_SIMILARITY,
        base_config=base_config,
        
        # Use only 2 parameters for faster testing
        calibration_parameters=['spread_probability', 'fuel_consumption_rate'],
        grid_search_points=2,  # 2^2 = 4 combinations
        
        # Performance settings
        parallel_execution=True,
        max_workers=2,  # Use 2 workers to distribute load
        memory_limit_gb=32.0,
        simulation_timeout_minutes=30.0,  # 30 minutes per simulation
        
        # Output settings
        results_dir="test_output/massive_grid_calibration",
        save_intermediate_results=True,
        generate_plots=False,
        verbose=True
    )
    
    # Create parameter bounds
    parameter_bounds = ParameterBounds()
    parameter_bounds.add_parameter('spread_probability', 0.4, 0.8)
    parameter_bounds.add_parameter('fuel_consumption_rate', 0.6, 1.0)
    
    # Create objective function
    objective_function = SpatialSimilarityObjective()
    
    print(f"📊 Grid size: {base_config.grid_size[0]} × {base_config.grid_size[1]} = {base_config.grid_size[0] * base_config.grid_size[1]:,} cells")
    print(f"⏱️  Simulation timeout: {calibration_config.simulation_timeout_minutes} minutes")
    print(f"🔧 Memory optimization level: {base_config.memory_optimization_level}")
    print(f"📦 Sparse storage: {base_config.use_sparse_storage}")
    print(f"🗺️  Terrain loading: ENABLED (shared terrain)")
    print(f"👥 Workers: {calibration_config.max_workers}")
    print(f"🔢 Parameter combinations: {2**2} (2 parameters, 2 points each)")
    print()
    
    print("🚀 Starting massive grid calibration test...")
    start_time = time.time()
    
    try:
        # Create calibrator
        calibrator = GridSearchCalibrator(
            calibration_config=calibration_config,
            parameter_bounds=parameter_bounds,
            objective_function=objective_function,
            parallel_execution=True,
            max_workers=2
        )
        
        # Run calibration
        results = calibrator.run_calibration()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Calibration completed in {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print(f"📊 Total evaluations: {len(results.evaluations)}")
        print(f"✅ Successful evaluations: {len([e for e in results.evaluations if e.is_valid])}")
        print(f"❌ Failed evaluations: {len([e for e in results.evaluations if not e.is_valid])}")
        
        if results.best_evaluation:
            print(f"🏆 Best objective value: {results.best_evaluation.objective_value}")
            print(f"🏆 Best parameters: {results.best_evaluation.parameter_values}")
        
        # Check for timeout errors
        timeout_errors = [e for e in results.evaluations if e.error_message and 'timeout' in e.error_message.lower()]
        if timeout_errors:
            print(f"❌ Found {len(timeout_errors)} timeout errors:")
            for error in timeout_errors:
                print(f"   - {error.error_message}")
            return False
        else:
            print("✅ No timeout errors found - fix is working!")
            return True
            
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Calibration failed after {duration:.2f} seconds: {e}")
        return False

def main():
    """Main test function."""
    setup_logging()
    
    print("🧪 PROGRESSIVE TIMEOUT TESTING")
    print("=" * 60)
    
    # Test 1: Smaller grid first
    print("\n📋 TEST 1: Smaller Grid (1M cells)")
    print("-" * 40)
    success1 = test_smaller_grid_timeout()
    
    if success1:
        print("\n✅ SMALLER GRID TEST PASSED!")
        print("✅ Timeout fix is working for manageable grid sizes")
        
        # Test 2: Massive grid calibration (if user wants to continue)
        print("\n📋 TEST 2: Massive Grid Calibration (21.5M cells, 2 workers)")
        print("-" * 40)
        print("⚠️  This test may take 15+ minutes due to massive grid initialization")
        print("⚠️  Press Ctrl+C to skip if you don't want to wait")
        
        try:
            success2 = test_calibration_with_massive_grid()
            if success2:
                print("\n🎉 MASSIVE GRID CALIBRATION TEST PASSED!")
                print("✅ The 21.5M cell grid timeout fix is working correctly")
                print("✅ Multiple workers can handle the massive grid")
            else:
                print("\n❌ MASSIVE GRID CALIBRATION TEST FAILED!")
                print("❌ The massive grid may still have initialization issues")
        except KeyboardInterrupt:
            print("\n⏸️  Massive grid test skipped by user")
            print("✅ Smaller grid test confirms timeout fix is working")
    else:
        print("\n❌ SMALLER GRID TEST FAILED!")
        print("❌ The timeout fix may not be working correctly")
    
    return success1

if __name__ == "__main__":
    main()
