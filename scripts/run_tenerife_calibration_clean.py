#!/usr/bin/env python
"""
UPDATED Tenerife Calibration Runner - TOP 4 SENSITIVITY ANALYSIS PARAMETERS
- Uses the top 4 most sensitive parameters from completed sensitivity analysis
- Minimal imports and clean execution
- Proper LiDAR configuration and HPC optimization
- Fire perimeter integration with EMSR data
- ALL NECESSARY CONFIGURATIONS INCLUDED
"""

import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime

# CRITICAL: Set environment variables BEFORE any imports
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# REDUCED LOGGING SETUP FOR CLEANER OUTPUT
import logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)

# Set specific loggers to WARNING level to reduce verbose output
logging.getLogger('src.core.forest_model').setLevel(logging.WARNING)
logging.getLogger('src.core.calibration').setLevel(logging.WARNING)
logging.getLogger('src.core.fire_simulation_engine').setLevel(logging.WARNING)
logging.getLogger('src.utils.lidar_utils').setLevel(logging.WARNING)
logging.getLogger('src.utils.terrain_preprocessor').setLevel(logging.WARNING)

def create_minimal_progress_callback():
    """Create a minimal progress callback."""
    start_time = time.time()
    
    def progress_callback(completed: int, total: int, result):
        # Report every single simulation
        progress = (completed / total) * 100
        best_value = result.objective_value if result.is_valid else 0.0
        current_value = result.objective_value if result.is_valid else 0.0
        
        if completed > 0:
            elapsed_time = time.time() - start_time
            time_per_sim = elapsed_time / completed
            remaining = total - completed
            eta_seconds = remaining * time_per_sim
            eta_minutes = eta_seconds / 60
            eta_str = f"{eta_minutes:.0f}m" if eta_minutes >= 1 else f"{eta_seconds:.0f}s"
        else:
            eta_str = "calculating..."
        
        print(f"Progress: {progress:.1f}% ({completed}/{total}) | Current: {current_value:.8f} | Best: {best_value:.8f} | ETA: {eta_str}")
    
    return progress_callback

def main():
    parser = argparse.ArgumentParser(description='Updated Tenerife calibration runner with top 4 sensitivity parameters')
    parser.add_argument('--workers', type=int, default=1, help='Number of workers (default: 1)')
    parser.add_argument('--grid-points', type=int, default=3, help='Grid points per parameter (default: 3)')
    parser.add_argument('--max-steps', type=int, default=15, help='Maximum simulation steps (default: 15)')
    parser.add_argument('--memory-gb', type=int, default=16, help='Memory allocation in GB (default: 16)')
    
    args = parser.parse_args()
    
    print(f"UPDATED TENERIFE CALIBRATION - TOP 4 SENSITIVITY PARAMETERS")
    print(f"   Workers: {args.workers}")
    print(f"   Grid points: {args.grid_points}")
    print(f"   Max steps: {args.max_steps}")
    print(f"   Memory: {args.memory_gb} GB")
    print(f"   Total combinations: {args.grid_points ** 4}")
    print()
    
    try:
        # Step 1: Import modules ONLY when needed
        print("Importing modules...")
        from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator, FirePerimeterDiscovery
        from src.core.calibration.calibration_config import CalibrationConfig, CalibrationTarget
        from src.config.config_tools import ModelConfig
        print("✅ Modules imported successfully")
        
        # Step 2: Discover fire perimeters
        print("Discovering fire perimeters...")
        discovery = FirePerimeterDiscovery('EMSR Delineations')
        fire_dataset = discovery.discover_fire_perimeters()
        
        if not fire_dataset.fire_perimeters:
            print("❌ No fire perimeters found!")
            return
        
        print(f"✅ Found {len(fire_dataset.fire_perimeters)} fire perimeters")
        
        # Debug: Show what fire perimeters were found
        for i, perimeter in enumerate(fire_dataset.fire_perimeters):
            print(f"   Fire perimeter {i+1}: {perimeter}")
            if hasattr(perimeter, 'shapefile_path'):
                print(f"     Shapefile path: {perimeter.shapefile_path}")
            else:
                print(f"     No shapefile_path attribute")
        
        # Step 3: Create calibrator with minimal settings
        print("Creating calibrator...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_name = f"ultra_clean_calibration_{timestamp}"
        
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=args.memory_gb,  # Use command line argument
            workers=args.workers,
            grid_search_points=args.grid_points,
            experiment_name=experiment_name,
            grid_size=(609, 609),
            base_directory='EMSR Delineations'
        )
        print("✅ Calibrator created")
        
        # Step 4: Set up training/validation split
        print("Setting up training/validation split...")
        training_data, validation_data = calibrator.setup_training_test_split(
            fire_dataset,
            training_days=[1, 2],
            test_days=[3, 4]
        )
        print("✅ Training/validation split created")
        
        # Step 5: Set up calibration targets FIRST (before creating calibration config)
        print("Setting up calibration targets...")
        calibration_targets = []
        
        # Use the discovered fire perimeters to create proper CalibrationTarget objects
        print("🔥 Using real EMSR fire perimeter data for calibration")
        for i, fire_perimeter in enumerate(fire_dataset.fire_perimeters[:2]):  # Use first 2 for training
            if hasattr(fire_perimeter, 'shapefile_path') and fire_perimeter.shapefile_path:
                target = CalibrationTarget(
                    fire_perimeter_path=str(fire_perimeter.shapefile_path),
                    weight=1.0
                )
                calibration_targets.append(target)
                filename = Path(fire_perimeter.shapefile_path).name
                print(f"✅ Added target {i+1}: {filename}")
        
        if not calibration_targets:
            print(f"⚠️  No valid EMSR targets found - falling back to synthetic targets")
            # Fallback to synthetic targets if EMSR data fails
            import numpy as np
            from src.core.calibration.calibration_utils import create_synthetic_target_data
            
            # Create synthetic target data that matches simulation scale
            synthetic_target = create_synthetic_target_data((609, 609), "circular")
            
            # Create a simple target around the ignition point
            target_fire = np.zeros((609, 609))
            # Create a small fire area around ignition point (395, 377)
            for i in range(390, 400):
                for j in range(370, 380):
                    if 0 <= i < 609 and 0 <= j < 609:
                        target_fire[i, j] = 1
            
            # Save synthetic target to file
            np.save("synthetic_target.npy", target_fire)
            
            # Create calibration target from synthetic data
            target = CalibrationTarget(
                fire_perimeter_path="synthetic_target.npy",  # Use synthetic data
                weight=1.0
            )
            calibration_targets.append(target)
            print(f"✅ Added synthetic target: {np.sum(target_fire > 0)} burned cells")
        
        print(f"✅ Using {len(calibration_targets)} calibration targets")
        
        # Step 6: Create calibration configuration with targets included
        print("Creating calibration configuration...")
        
        # Create base config with preprocessed data
        base_config = ModelConfig(
            grid_size=(609, 609),
            num_layers=20,  # Use 20 layers (preprocessed)
            max_steps=args.max_steps,
            model_resolution=20.0,
            simulation_type="memory_optimized",
            memory_optimization_level=3,
            use_disk_storage=True,
            use_differential_history=True,
            use_sparse_storage=True,
            
            # ENABLE LIDAR
            use_lidar=True,
            auto_size_from_lidar=False,  # Use fixed grid size
            preprocessed_lidar_dir='preprocessed_lidar',
            
            # PREPROCESSED TERRAIN
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir='preprocessed_terrain'
        )
        
        # CRITICAL FIX: Add preprocessed LiDAR directory to base config
        base_config.preprocessed_lidar_dir = "preprocessed_lidar"
        
        # CRITICAL FIX: Set ignition points for calibration
        base_config.ignition_points = [(395, 377, 0)]  # Center of 609×609 grid (Arafo highlands equivalent)
        
        # TOP 4 MOST SENSITIVE PARAMETERS FROM SENSITIVITY ANALYSIS
        # Based on completed sensitivity analysis results:
        # 1. min_fuel_value: 0.1727 (Most sensitive - 3.4x more than #2)
        # 2. spread_probability: 0.0511 (Second most sensitive)
        # 3. fuel_consumption_rate: 0.0494 (Third most sensitive)
        # 4. ember_probability: 0.0467 (Fourth most sensitive)
        top_4_parameters = [
            'min_fuel_value',           # 0.1727 - CRITICAL (Most sensitive)
            'spread_probability',       # 0.0511 - CRITICAL
            'fuel_consumption_rate',    # 0.0494 - CRITICAL
            'ember_probability'         # 0.0467 - CRITICAL
        ]
        
        print(f"🎯 Using top 4 sensitivity analysis parameters:")
        for i, param in enumerate(top_4_parameters, 1):
            print(f"   {i}. {param}")
        print()
        
        # Create calibration config WITH targets included
        calib_config = CalibrationConfig(
            base_config=base_config,
            calibration_parameters=top_4_parameters,
            grid_search_points=args.grid_points,
            max_workers=args.workers,
            calibration_targets=calibration_targets,  # Include targets here
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir='preprocessed_terrain'
        )
        
        # Set preprocessed LiDAR directory on calibration config
        calib_config.preprocessed_lidar_dir = 'preprocessed_lidar'
        
        print(f"✅ Using preprocessed LiDAR data: preprocessed_lidar")
        print(f"✅ Using preprocessed terrain data")
        
        print(f"Configuration ready:")
        print(f"   Grid size: 609 × 609")
        print(f"   Parameters: {len(top_4_parameters)}")
        print(f"   Total combinations: {args.grid_points ** len(top_4_parameters)}")
        print()
        
        # Step 7: Run calibration with minimal setup
        print("Starting calibration...")
        start_time = time.time()
        
        try:
            progress_callback = create_minimal_progress_callback()
            results = calibrator.run_calibration(calib_config, validation_data, progress_callback=progress_callback)
            
            end_time = time.time()
            runtime_minutes = (end_time - start_time) / 60
            
            # Final summary
            print(f"\n🎉 CALIBRATION COMPLETED!")
            print(f"Runtime: {runtime_minutes:.2f} minutes")
            print(f"Best objective value: {results['best_objective_value']:.8f}")
            print(f"Results saved to: {calibrator.results_dir}")
            
            print(f"\nBEST PARAMETERS:")
            best_parameters = results['best_parameters']
            if isinstance(best_parameters, dict) and best_parameters:
                for param, value in best_parameters.items():
                    print(f"   {param}: {value:.8f}")
        
        except Exception as e:
            print(f"❌ Calibration failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
