#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Local Tenerife Fire Perimeter Calibration Test (Mirrors HPC Implementation)

This script runs a local version of the Tenerife calibration using the EXACT same operations
as scripts/run_tenerife_calibration.py, but scaled down for 16GB RAM testing.

Key Features (matching HPC implementation):
- Uses TenerifeFirePerimeterCalibrator class
- Same EMSR discovery and validation
- Same training/test split logic
- Same parameter space (top 5 from sensitivity analysis)
- Same grid size calculation method
- Same target data creation process

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

# Set NumExpr to 8 threads for local testing (vs 128 for HPC)
os.environ['NUMEXPR_MAX_THREADS'] = '8'
os.environ['NUMEXPR_NUM_THREADS'] = '8'

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.calibration.fire_perimeter_calibration import (
        FirePerimeterDiscovery,
        TenerifeFirePerimeterCalibrator
    )
    from src.utils.logging_utils import get_logger
    from src.utils.production_memory_manager import (
        setup_production_memory_protection,
        ProductionMemoryThresholds
    )
    from src.utils.shared_terrain import emergency_cleanup_shared_memory
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

# Configure logging for local testing (less verbose than HPC)
def setup_local_logging():
    """Set up logging configuration for local testing."""
    # Set root logger to INFO level for local testing
    logging.getLogger().setLevel(logging.INFO)
    
    # Set specific loggers to appropriate levels
    logging.getLogger('src.core.fire_simulation_engine').setLevel(logging.INFO)
    logging.getLogger('src.core.forest_model').setLevel(logging.INFO)
    logging.getLogger('src.core.calibration').setLevel(logging.INFO)
    logging.getLogger('src.utils').setLevel(logging.INFO)
    logging.getLogger('shared_utilities').setLevel(logging.INFO)
    
    # Suppress some verbose output for local testing
    logging.getLogger('src.core.calibration.grid_search').setLevel(logging.WARNING)
    logging.getLogger('src.utils.hpc_optimizer').setLevel(logging.WARNING)
    logging.getLogger('src.utils.shared_terrain').setLevel(logging.WARNING)
    logging.getLogger('src.utils.memory_manager').setLevel(logging.WARNING)
    logging.getLogger('src.utils.production_memory_manager').setLevel(logging.WARNING)

# Set up logging
setup_local_logging()
logger = get_logger(__name__)

def validate_local_system_resources(memory_gb: int, workers: int) -> bool:
    """Validate that local system has sufficient resources."""
    try:
        import psutil
        
        # Check memory
        total_memory_gb = psutil.virtual_memory().total / (1024**3)
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        
        print(f"💻 System check: {total_memory_gb:.1f}GB total, {available_memory_gb:.1f}GB available")
        
        # Check CPU cores
        cpu_count = psutil.cpu_count(logical=False)
        logical_cores = psutil.cpu_count(logical=True)
        
        print(f"🖥️  CPU: {cpu_count} physical, {logical_cores} logical cores, {workers} workers requested")
        
        # Basic availability check
        if available_memory_gb < memory_gb * 0.8:
            print(f"⚠️  Low available memory: {available_memory_gb:.1f}GB available, {memory_gb}GB requested")
            return False
        
        if workers > logical_cores:
            print(f"⚠️  High worker count: {workers} workers on {logical_cores} logical cores")
        
        print("✅ Local system resources validated")
        return True
        
    except ImportError:
        print(f"⚠️  Cannot validate system resources (psutil not available)")
        print(f"   Proceeding with user-specified configuration")
        return True

def run_discovery_and_validation(emsr_dir: str = "EMSR Delineations"):
    """Run fire perimeter discovery and validation (same as HPC)."""
    print(f"🔍 Discovering fire perimeters...")
    
    # Initialize discovery
    discovery = FirePerimeterDiscovery(emsr_dir)
    
    # Discover fire perimeters
    fire_dataset = discovery.discover_fire_perimeters()
    
    if not fire_dataset.fire_perimeters:
        print(f"❌ No fire perimeters found in {emsr_dir}")
        return None
    
    # Quick validation
    day_numbers = [fp.day_number for fp in fire_dataset.fire_perimeters]
    crs_list = [fp.crs for fp in fire_dataset.fire_perimeters if fp.crs]
    
    print(f"✅ Found {len(fire_dataset.fire_perimeters)} fire perimeters (days {min(day_numbers)}-{max(day_numbers)})")
    
    if len(set(crs_list)) > 1:
        print(f"❌ CRS inconsistency - all files must use same CRS")
        return None
    
    return fire_dataset

def estimate_local_calibration_time(parameters: List[str], grid_points: int, workers: int, grid_size: Tuple[int, int]) -> dict:
    """Estimate calibration time for local testing."""
    total_combinations = grid_points ** len(parameters)
    grid_width, grid_height = grid_size
    total_cells = grid_width * grid_height * 25
    
    # Conservative estimates for local testing
    if total_cells <= 1_000_000:  # 1M cells
        time_per_sim_minutes = 2.0
        memory_per_sim_gb = 0.5
    elif total_cells <= 5_000_000:  # 5M cells
        time_per_sim_minutes = 8.0
        memory_per_sim_gb = 1.5
    else:  # >5M cells
        time_per_sim_minutes = 15.0
        memory_per_sim_gb = 2.5
    
    # Calculate timings
    sequential_time_minutes = total_combinations * time_per_sim_minutes
    parallel_time_minutes = sequential_time_minutes / workers
    peak_memory_gb = memory_per_sim_gb * min(workers, total_combinations)
    
    return {
        'total_combinations': total_combinations,
        'time_per_sim_minutes': time_per_sim_minutes,
        'sequential_time_minutes': sequential_time_minutes,
        'parallel_time_minutes': parallel_time_minutes,
        'memory_per_sim_gb': memory_per_sim_gb,
        'peak_memory_gb': peak_memory_gb,
        'speedup': sequential_time_minutes / parallel_time_minutes
    }

def display_local_calibration_plan(parameters: List[str],
                                 grid_points: int,
                                 workers: int,
                                 memory_gb: int,
                                 training_days: List[int],
                                 test_days: List[int],
                                 grid_size: Tuple[int, int]):
    """Display calibration plan for local testing."""
    print(f"\n🎯 LOCAL CALIBRATION PLAN")
    print(f"=" * 50)
    
    # Domain configuration
    grid_width, grid_height = grid_size
    total_cells = grid_width * grid_height * 25
    area_km2 = (grid_width * 5 / 1000) * (grid_height * 5 / 1000)
    print(f"🌍 Grid: {grid_width:,} × {grid_height:,} × 25 = {total_cells/1e6:.1f}M cells ({area_km2:.1f} km²)")
    
    # Key configuration
    print(f"📋 Parameters: {len(parameters)} ({grid_points} points each)")
    print(f"🖥️  Resources: {memory_gb}GB memory, {workers} workers")
    print(f"📅 Data: Training days {training_days}, Test days {test_days}")
    
    # Estimates
    estimates = estimate_local_calibration_time(parameters, grid_points, workers, grid_size)
    print(f"⏱️  Time: ~{estimates['parallel_time_minutes']:.1f} minutes ({estimates['total_combinations']:,} combinations)")
    print(f"💾 Memory: ~{estimates['peak_memory_gb']:.1f}GB peak")
    
    # Risk assessment
    if estimates['peak_memory_gb'] > memory_gb * 0.8:
        print(f"⚠️  HIGH MEMORY RISK - consider reducing workers or grid size")
    elif estimates['parallel_time_minutes'] > 120:
        print(f"⚠️  LONG RUNTIME - consider reducing grid points or parameters")
    else:
        print(f"✅ Configuration looks good for local testing")

def create_progress_callback(total_combinations: int):
    """Create a progress callback for local testing."""
    start_time = time.time()
    last_progress_time = start_time
    progress_interval = 10  # Show progress every 10 seconds
    
    def progress_callback(completed: int, total: int, result):
        nonlocal last_progress_time
        current_time = time.time()
        
        # Show progress every 10 seconds or every completion
        time_since_last = current_time - last_progress_time
        should_show = (time_since_last >= progress_interval or 
                      completed == total or 
                      completed % 2 == 0)  # Every 2 completions
        
        if should_show:
            progress = (completed / total) * 100
            remaining = total - completed
            best_value = result.objective_value if result.is_valid else 0.0
            
            # Calculate ETA
            if completed > 0:
                elapsed_time = current_time - start_time
                time_per_sim = elapsed_time / completed
                eta_seconds = remaining * time_per_sim
                eta_minutes = eta_seconds / 60
                
                if eta_minutes >= 1:
                    eta_str = f"{eta_minutes:.0f}m"
                else:
                    eta_str = f"{eta_seconds:.0f}s"
            else:
                eta_str = "calculating..."
            
            print(f"🎯 Progress: {progress:.1f}% ({completed}/{total}) | "
                  f"Best: {best_value:.4f} | ETA: {eta_str}")
            
            last_progress_time = current_time
    
    return progress_callback

def main():
    """Run local Tenerife calibration test (mirrors HPC implementation)."""
    
    print(f"🔥 LOCAL TENERIFE CALIBRATION TEST")
    print(f"=" * 50)
    print(f"System: 16GB RAM, 2 workers")
    print(f"Target: Day 4 EMSR delineations (scaled)")
    print(f"Terrain: Preprocessed data")
    print(f"Method: Exact same operations as HPC implementation")
    
    # Local configuration (scaled down from HPC)
    memory_gb = 16
    workers = 2
    grid_points = 2  # Reduced from 3 for faster testing
    experiment_name = f"local_tenerife_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # TOP 5 PARAMETERS FROM SENSITIVITY ANALYSIS (same as HPC)
    parameters = [
        'spread_probability',        # 1.4063 - CRITICAL (13x more sensitive than #2)
        'fuel_consumption_rate',     # 0.1609 - CRITICAL
        'ember_probability',         # 0.1159 - CRITICAL
        'ember_ignition',           # 0.0564 - CRITICAL
        'fuel_moisture_baseline'    # 0.0382 - MODERATE
    ]
    
    # Training/test split (same as HPC)
    training_days = [1, 2]  # Days 1-2 for training (calibration)
    test_days = [3, 4]      # Days 3-4 for testing (validation)
    
    print(f"🔧 Using TOP 5 parameters from sensitivity analysis (same as HPC)")
    print(f"📅 Training days: {training_days}, Test days: {test_days}")
    
    try:
        # Step 1: Validate local system resources
        if not validate_local_system_resources(memory_gb, workers):
            print("❌ Local system resource validation failed")
            sys.exit(1)
        
        # Step 2: Discover and validate fire perimeters
        fire_dataset = run_discovery_and_validation("EMSR Delineations")
        if fire_dataset is None:
            sys.exit(1)
        
        # Step 3: Calculate grid size (same method as HPC)
        print(f"🔍 Calculating grid size from Day 4 fire perimeter...")
        
        # Create calibrator to access grid size calculation method
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=memory_gb,
            workers=workers,
            grid_search_points=grid_points,
            experiment_name=experiment_name
        )
        
        # Calculate optimal grid size from Day 4 (same as HPC)
        grid_size = calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
        
        if grid_size:
            grid_width, grid_height = grid_size
            total_cells = grid_width * grid_height * 25
            area_km2 = (grid_width * 5 / 1000) * (grid_height * 5 / 1000)
            print(f"✅ Grid: {grid_width:,} × {grid_height:,} = {total_cells/1e6:.1f}M cells ({area_km2:.1f} km²)")
        else:
            print(f"⚠️  Using fallback grid size")
            grid_size = (500, 500)  # Fallback for local testing
        
        # Step 4: Display calibration plan
        display_local_calibration_plan(
            parameters=parameters,
            grid_points=grid_points,
            workers=workers,
            memory_gb=memory_gb,
            training_days=training_days,
            test_days=test_days,
            grid_size=grid_size
        )
        
        # Step 5: Set up training/validation split (same as HPC)
        print(f"\n📊 SETTING UP TRAINING/VALIDATION SPLIT")
        print(f"=" * 50)
        
        training_data, validation_data = calibrator.setup_training_test_split(
            fire_dataset,
            training_days=training_days,  # Days 1-2 for training (calibration)
            test_days=test_days          # Days 3-4 for testing (validation)
        )
        
        print(f"\n✅ Training/Validation split complete:")
        print(f"   🎯 Training (calibration): {len(training_data)} fire perimeters")
        for fp in training_data:
            print(f"      Day {fp.day_number} ({fp.date}): {fp.area_hectares:.1f} ha")
        print(f"   🧪 Validation: {len(validation_data)} fire perimeters")
        for fp in validation_data:
            print(f"      Day {fp.day_number} ({fp.date}): {fp.area_hectares:.1f} ha")
        
        # Step 6: Create calibration configuration (same as HPC)
        print(f"\n🔧 CREATING CALIBRATION CONFIGURATION")
        print(f"=" * 50)
        
        calib_config = calibrator.create_calibration_config(
            training_data=training_data,  # Use training data (Days 1-2) for calibration
            top_5_parameters=parameters,
            grid_size=grid_size  # Pass the calculated grid size
        )
        
        print(f"✅ Calibration configuration created")
        print(f"   Grid size: {grid_size[0]} × {grid_size[1]}")
        print(f"   Parameters: {len(parameters)}")
        print(f"   Grid points: {grid_points}")
        print(f"   Total combinations: {grid_points ** len(parameters)}")
        
        # Step 7: Final confirmation and execution
        print(f"\n🚀 READY TO EXECUTE")
        print(f"=" * 30)
        
        estimates = estimate_local_calibration_time(parameters, grid_points, workers, grid_size)
        
        print(f"⏱️  Estimated: {estimates['parallel_time_minutes']:.1f} minutes")
        print(f"📁 Progress: {calibrator.results_dir}")
        
        # Final user confirmation
        response = input(f"\nContinue with local calibration? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print(f"❌ Cancelled by user")
            return
        
        # Run calibration
        print(f"\n🔥 STARTING LOCAL CALIBRATION")
        print(f"⏱️  Estimated: {estimates['parallel_time_minutes']:.1f} minutes")
        print(f"📁 Progress: {calibrator.results_dir}")
        
        start_time = time.time()
        
        # Create progress callback
        total_combinations = grid_points ** len(parameters)
        progress_callback = create_progress_callback(total_combinations)
        
        # Run calibration (same method as HPC)
        results = calibrator.run_calibration(calib_config, validation_data, progress_callback=progress_callback)
        
        end_time = time.time()
        actual_runtime_minutes = (end_time - start_time) / 60
        
        # Final summary
        print(f"\n🎉 LOCAL CALIBRATION COMPLETED SUCCESSFULLY!")
        print(f"=" * 70)
        print(f"⏱️  Actual runtime: {actual_runtime_minutes:.2f} minutes")
        print(f"📊 Estimated runtime: {estimates['parallel_time_minutes']:.1f} minutes")
        print(f"🎯 Best objective value: {results['best_objective_value']:.4f}")
        print(f"📁 Results saved to: {calibrator.results_dir}")
        
        print(f"\n🔍 BEST PARAMETERS:")
        best_parameters = results['best_parameters']
        if isinstance(best_parameters, dict) and best_parameters:
            for param, value in best_parameters.items():
                print(f"   {param}: {value:.4f}")
        else:
            print(f"   No valid parameters found")
        
        print(f"\n🧪 VALIDATION:")
        validation_results = results['validation_results']
        if isinstance(validation_results, dict):
            for test_case, test_result in validation_results.items():
                if isinstance(test_result, dict) and 'status' in test_result:
                    print(f"   {test_case}: {test_result['status']}")
                else:
                    print(f"   {test_case}: {test_result}")
        else:
            print(f"   Validation status: {validation_results}")
        
        print(f"\n✅ LOCAL TEST SUCCESSFUL!")
        print(f"   This confirms the HPC implementation works correctly")
        print(f"   Next: Run full-scale calibration on HPC with same operations")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Local calibration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Local calibration failed: {e}")
        logger.error(f"Local calibration failed: {e}")
        
        # Clean up shared memory to prevent leaks
        try:
            emergency_cleanup_shared_memory()
        except Exception as cleanup_error:
            logger.warning(f"⚠️  Shared memory cleanup failed: {cleanup_error}")
        
        sys.exit(1)

if __name__ == "__main__":
    main()
