#!/usr/bin/env python
"""
ULTRA-CLEAN Tenerife Calibration Runner with EMSR Target Data
- ONLY uses preprocessed data
- Uses real EMSR fire perimeter data
- NO raw PAD files
- NO shared memory complexity
- DIRECT to calibration
"""

import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime

# THREAD LIMITING
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# REDUCED LOGGING FOR CLEANER OUTPUT
import logging
logging.getLogger().setLevel(logging.ERROR)
logging.getLogger('src').setLevel(logging.ERROR)

# Import ONLY what we need
from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator, FirePerimeterDiscovery
from src.core.calibration.calibration_config import CalibrationConfig, CalibrationTarget
from src.config.config_tools import ModelConfig

def create_simple_progress_callback():
    """Create a simple progress callback."""
    start_time = time.time()
    
    def progress_callback(completed: int, total: int, result):
        if completed % 5 == 0 or completed == total:
            progress = (completed / total) * 100
            best_value = result.objective_value if result.is_valid else 0.0
            
            if completed > 0:
                elapsed_time = time.time() - start_time
                time_per_sim = elapsed_time / completed
                remaining = total - completed
                eta_seconds = remaining * time_per_sim
                eta_minutes = eta_seconds / 60
                eta_str = f"{eta_minutes:.0f}m" if eta_minutes >= 1 else f"{eta_seconds:.0f}s"
            else:
                eta_str = "calculating..."
            
            print(f"Progress: {progress:.1f}% ({completed}/{total}) | Best: {best_value:.4f} | ETA: {eta_str}")
    
    return progress_callback

def main():
    parser = argparse.ArgumentParser(description='Ultra-clean Tenerife calibration runner with EMSR data')
    parser.add_argument('--workers', type=int, default=4, help='Number of workers')
    parser.add_argument('--grid-points', type=int, default=3, help='Grid points per parameter')
    parser.add_argument('--max-steps', type=int, default=50, help='Maximum simulation steps')
    parser.add_argument('--memory', type=int, default=16, help='Memory in GB per process')
    
    args = parser.parse_args()
    
    # TOP 4 PARAMETERS
    top_4_parameters = [
        'spread_probability',
        'fuel_consumption_rate', 
        'ember_probability',
        'ember_ignition'
    ]
    
    # Create experiment name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_name = f"ultra_clean_emsr_calibration_{timestamp}"
    
    print(f"ULTRA-CLEAN EMSR CALIBRATION")
    print(f"   Workers: {args.workers}")
    print(f"   Grid points: {args.grid_points}")
    print(f"   Max steps: {args.max_steps}")
    print()
    
    try:
        # Step 1: Discover fire perimeters using existing architecture
        print("Discovering fire perimeters...")
        discovery = FirePerimeterDiscovery('EMSR Delineations')
        fire_dataset = discovery.discover_fire_perimeters()
        
        if not fire_dataset.fire_perimeters:
            print("No fire perimeters found!")
            return
        
        print(f"Found {len(fire_dataset.fire_perimeters)} fire perimeters")
        
        # Step 2: Create calibrator with FIXED grid size (no dynamic calculation)
        print("Creating calibrator...")
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=args.memory,
            workers=args.workers,
            grid_search_points=args.grid_points,
            experiment_name=experiment_name,
            grid_size=(609, 609),  # FIXED - no dynamic calculation
            base_directory='EMSR Delineations'
        )
        
        print(f"Grid: 609 × 609 cells")
        
        # Step 3: Set up training/validation split
        print("Setting up training/validation split...")
        training_data, validation_data = calibrator.setup_training_test_split(
            fire_dataset,
            training_days=[1, 2],
            test_days=[3, 4]
        )
        
        # Step 4: Create calibration configuration MANUALLY
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
            
            # PREPROCESSED TERRAIN ONLY (ModelConfig doesn't have preprocessed_lidar_dir)
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir='/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain'
        )
        
        # Create calibration config
        calib_config = CalibrationConfig(
            base_config=base_config,
            calibration_parameters=top_4_parameters,
            grid_search_points=args.grid_points,
            max_workers=args.workers,
            # Set preprocessed terrain on CalibrationConfig itself
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir='/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain'
        )
        
        # Set preprocessed LiDAR directory on calibration config (NOT on ModelConfig)
        # Use HPC absolute path for preprocessed LiDAR data
        calib_config.preprocessed_lidar_dir = "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_lidar"
        
        # Step 5: Create proper CalibrationTarget objects using existing architecture
        print("Setting up EMSR calibration targets...")
        calibration_targets = []
        
        # Use the discovered fire perimeters to create proper CalibrationTarget objects
        for i, fire_perimeter in enumerate(fire_dataset.fire_perimeters[:2]):  # Use first 2 for training
            if hasattr(fire_perimeter, 'shapefile_path') and fire_perimeter.shapefile_path:
                target = CalibrationTarget(
                    fire_perimeter_path=str(fire_perimeter.shapefile_path),
                    weight=1.0
                )
                calibration_targets.append(target)
                filename = Path(fire_perimeter.shapefile_path).name
                print(f"✅ Added target {i+1}: {filename}")
        
        if calibration_targets:
            calib_config.calibration_targets = calibration_targets
            print(f"✅ Using {len(calibration_targets)} EMSR calibration targets")
        else:
            print(f"⚠️  No valid EMSR targets found - using synthetic targets")
        
        print(f"✅ Using preprocessed LiDAR data: preprocessed_lidar")
        print(f"✅ Using preprocessed terrain data")
        
        print(f"Configuration ready:")
        print(f"   Grid size: 609 × 609")
        print(f"   Parameters: {len(top_4_parameters)}")
        print(f"   Total combinations: {args.grid_points ** len(top_4_parameters)}")
        print()
        
        # Step 6: Run calibration
        print("Starting calibration...")
        start_time = time.time()
        
        try:
            progress_callback = create_simple_progress_callback()
            results = calibrator.run_calibration(calib_config, validation_data, progress_callback=progress_callback)
            
            end_time = time.time()
            runtime_minutes = (end_time - start_time) / 60
            
            # Final summary
            print(f"\nCALIBRATION COMPLETED!")
            print(f"Runtime: {runtime_minutes:.2f} minutes")
            print(f"Best objective value: {results['best_objective_value']:.4f}")
            print(f"Results saved to: {calibrator.results_dir}")
            
            print(f"\nBEST PARAMETERS:")
            best_parameters = results['best_parameters']
            if isinstance(best_parameters, dict) and best_parameters:
                for param, value in best_parameters.items():
                    print(f"   {param}: {value:.4f}")
        
        except Exception as e:
            print(f"Calibration failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
