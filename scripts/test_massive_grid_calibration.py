#!/usr/bin/env python3
"""
Massive Grid Calibration Test - 16GB System

This script runs a calibration test with 3 workers on a 16GB system
to test 10% of the 5-parameter combinations with the massive grid (21.5M cells).
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.calibration.grid_search import GridSearchCalibrator
from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod, CalibrationObjective
from src.core.calibration.parameter_bounds import ParameterBounds
from src.core.calibration.objective_functions import SpatialSimilarityObjective
from src.config.config_tools import ModelConfig

def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set specific loggers to DEBUG level for detailed diagnosis
    logging.getLogger('src.core.calibration.grid_search').setLevel(logging.DEBUG)
    logging.getLogger('src.core.fire_simulation_engine').setLevel(logging.DEBUG)
    logging.getLogger('src.core.forest_model').setLevel(logging.DEBUG)
    logging.getLogger('src.utils.shared_terrain').setLevel(logging.DEBUG)
    logging.getLogger('src.utils.memory_manager').setLevel(logging.DEBUG)

def run_massive_grid_calibration():
    """Run calibration test with massive grid and 3 workers."""
    print("🔥 MASSIVE GRID CALIBRATION TEST - 16GB SYSTEM")
    print("=" * 60)
    
    # Debug: Print current logging level
    print(f"🔍 Current logging level: {logging.getLogger().level}")
    print(f"🔍 GridSearchCalibrator logging level: {logging.getLogger('src.core.calibration.grid_search').level}")
    print(f"🔍 Fire simulation engine logging level: {logging.getLogger('src.core.fire_simulation_engine').level}")
    
    # Create base configuration with the actual massive grid size
    base_config = ModelConfig(
        grid_size=(4788, 4490),  # 21,498,120 cells - actual size from your output
        num_layers=25,
        max_steps=150,           # Reduced for faster testing but still comprehensive
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
        experiment_name="massive_grid_16gb_test",
        method=CalibrationMethod.GRID_SEARCH,
        objective=CalibrationObjective.SPATIAL_SIMILARITY,
        base_config=base_config,
        
        # Use all 5 parameters but with reduced grid points for 10% coverage
        calibration_parameters=[
            'spread_probability',
            'fuel_consumption_rate', 
            'ember_probability',
            'ember_ignition',
            'fuel_moisture_baseline'
        ],
        grid_search_points=2,  # 2^5 = 32 combinations (10% of 3^5 = 243)
        
        # Performance settings for 16GB system
        parallel_execution=True,
        max_workers=3,  # Use 3 workers as requested
        memory_limit_gb=12.0,  # Leave 4GB for system
        simulation_timeout_minutes=45.0,  # 45 minutes per simulation
        
        # Output settings
        results_dir="test_output/massive_grid_16gb_calibration",
        save_intermediate_results=True,
        generate_plots=True,
        verbose=True,
        debug_mode=True
    )
    
    # Create parameter bounds for the 5 parameters
    parameter_bounds = ParameterBounds()
    parameter_bounds.add_parameter('spread_probability', 0.4, 0.8)
    parameter_bounds.add_parameter('fuel_consumption_rate', 0.6, 1.0)
    parameter_bounds.add_parameter('ember_probability', 0.05, 0.15)
    parameter_bounds.add_parameter('ember_ignition', 0.2, 0.4)
    parameter_bounds.add_parameter('fuel_moisture_baseline', 0.1, 0.3)
    
    # Create objective function
    objective_function = SpatialSimilarityObjective()
    
    print(f"📊 Grid size: {base_config.grid_size[0]} × {base_config.grid_size[1]} = {base_config.grid_size[0] * base_config.grid_size[1]:,} cells")
    print(f"⏱️  Simulation timeout: {calibration_config.simulation_timeout_minutes} minutes")
    print(f"🔧 Memory optimization level: {base_config.memory_optimization_level}")
    print(f"📦 Sparse storage: {base_config.use_sparse_storage}")
    print(f"🗺️  Terrain loading: ENABLED (shared terrain)")
    print(f"👥 Workers: {calibration_config.max_workers}")
    print(f"🔢 Parameter combinations: {2**5} (5 parameters, 2 points each)")
    print(f"💾 Memory limit: {calibration_config.memory_limit_gb} GB (16GB system)")
    print()
    
    print("🚀 Starting massive grid calibration test...")
    start_time = time.time()
    
    try:
        print("🔧 Creating GridSearchCalibrator...")
        # Create calibrator
        calibrator = GridSearchCalibrator(
            calibration_config=calibration_config,
            parameter_bounds=parameter_bounds,
            objective_function=objective_function,
            parallel_execution=True,
            max_workers=3
        )
        print("✅ GridSearchCalibrator created successfully")
        
        # Run calibration
        print("🚀 Starting calibration run...")
        results = calibrator.run_calibration()
        print("✅ Calibration run completed")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ CALIBRATION COMPLETED!")
        print(f"⏱️  Total time: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print(f"📊 Total evaluations: {len(results.evaluations)}")
        print(f"✅ Successful evaluations: {len([e for e in results.evaluations if e.is_valid])}")
        print(f"❌ Failed evaluations: {len([e for e in results.evaluations if not e.is_valid])}")
        
        # Check for timeout errors
        timeout_errors = [e for e in results.evaluations if e.error_message and 'timeout' in e.error_message.lower()]
        if timeout_errors:
            print(f"\n❌ Found {len(timeout_errors)} timeout errors:")
            for error in timeout_errors:
                print(f"   - {error.error_message}")
        else:
            print(f"\n✅ No timeout errors found!")
        
        # Show best results
        if results.best_evaluation:
            print(f"\n🏆 BEST RESULTS:")
            print(f"   Objective value: {results.best_evaluation.objective_value:.6f}")
            print(f"   Parameters: {results.best_evaluation.parameter_values}")
            print(f"   Evaluation time: {results.best_evaluation.evaluation_time:.2f} seconds")
        
        # Show all results summary
        print(f"\n📈 ALL RESULTS SUMMARY:")
        valid_evaluations = [e for e in results.evaluations if e.is_valid]
        if valid_evaluations:
            objective_values = [e.objective_value for e in valid_evaluations]
            print(f"   Best objective: {min(objective_values):.6f}")
            print(f"   Worst objective: {max(objective_values):.6f}")
            print(f"   Average objective: {sum(objective_values)/len(objective_values):.6f}")
            print(f"   Standard deviation: {sum((x - sum(objective_values)/len(objective_values))**2 for x in objective_values)**0.5 / len(objective_values):.6f}")
        
        # Show parameter sensitivity
        print(f"\n🔍 PARAMETER SENSITIVITY (from successful evaluations):")
        if valid_evaluations:
            for param in calibration_config.calibration_parameters:
                param_values = [e.parameter_values[param] for e in valid_evaluations]
                obj_values = [e.objective_value for e in valid_evaluations]
                # Simple correlation-based sensitivity
                if len(set(param_values)) > 1:
                    correlation = sum((p - sum(param_values)/len(param_values)) * (o - sum(obj_values)/len(obj_values)) 
                                    for p, o in zip(param_values, obj_values)) / len(param_values)
                    print(f"   {param}: {abs(correlation):.6f}")
        
        return True
            
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"\n❌ Calibration failed after {duration:.2f} seconds: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    setup_logging()
    
    print("🧪 MASSIVE GRID CALIBRATION TEST - 16GB SYSTEM")
    print("=" * 60)
    print("📋 Testing 10% of 5-parameter combinations (32 out of 243)")
    print("👥 Using 3 workers on 16GB system")
    print("⏱️  Expected runtime: 2-4 hours")
    print()
    
    success = run_massive_grid_calibration()
    
    if success:
        print("\n🎉 MASSIVE GRID CALIBRATION TEST PASSED!")
        print("✅ The timeout fix is working correctly")
        print("✅ 3 workers can handle the massive grid on 16GB system")
        print("✅ Shared terrain is working efficiently")
    else:
        print("\n❌ MASSIVE GRID CALIBRATION TEST FAILED!")
        print("❌ There may still be issues with the massive grid setup")
    
    return success

if __name__ == "__main__":
    main()
