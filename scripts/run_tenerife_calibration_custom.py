#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tenerife Fire Perimeter Calibration Runner - CUSTOM VERSION

CUSTOM CONFIGURATION:
✅ 10m resolution (coarse for speed)
✅ 100 timesteps (short simulations)
✅ Top 4 parameters (spread_probability, fuel_consumption_rate, ember_probability, ignition_threshold)
✅ 3-point grid search (3⁴ = 81 combinations)
✅ Estimated runtime: ~3-4 hours

Usage:
    # Default custom configuration
    python scripts/run_tenerife_calibration_custom.py
    
    # With custom memory and workers
    python scripts/run_tenerife_calibration_custom.py --memory 64 --workers 32
    
    # Dry run (setup only, no calibration)
    python scripts/run_tenerife_calibration_custom.py --dry-run

Author: Forest Fire Simulation Team
Date: 2025
Version: 4.0 (Custom)
"""

import os
import sys
import argparse
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

# Set NumExpr to maximum threads for HPC
os.environ['NUMEXPR_MAX_THREADS'] = '128'
os.environ['NUMEXPR_NUM_THREADS'] = '128'

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.calibration.fire_perimeter_calibration import (
        FirePerimeterDiscovery,
        TenerifeFirePerimeterCalibrator
    )
    from src.core.optimization_factory import (
        create_optimized_fire_simulation_engine,
        create_optimized_forest_model,
        log_optimization_status
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

logger = get_logger(__name__)

# === CUSTOM CONFIGURATION ===

CUSTOM_CONFIG = {
    'grid_search_points': 3,  # 3 points per parameter
    'max_steps': 100,  # 100 timesteps as requested
    'model_resolution': 10.0,  # 10m resolution as requested
    'parameters': [
        'spread_probability',      # Top parameter 1
        'fuel_consumption_rate',   # Top parameter 2
        'ember_probability',       # Top parameter 3
        'ignition_threshold'       # Top parameter 4
    ],
    'estimated_hours': 3.5
}

def validate_system_resources(memory_gb: int, workers: int) -> bool:
    """Validate that system has sufficient resources for custom calibration."""
    try:
        import psutil
        
        # Check memory
        total_memory_gb = psutil.virtual_memory().total / (1024**3)
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        
        logger.info(f"System check: {total_memory_gb:.1f}GB total, {available_memory_gb:.1f}GB available")
        
        # Check CPU cores
        cpu_count = psutil.cpu_count(logical=False)
        logical_cores = psutil.cpu_count(logical=True)
        
        logger.debug(f"CPU: {cpu_count} physical, {logical_cores} logical cores, {workers} workers requested")
        
        # Basic availability check only
        if available_memory_gb < total_memory_gb * 0.7:
            logger.warning(f"High memory usage: {available_memory_gb:.1f}GB available ({available_memory_gb/total_memory_gb*100:.1f}%)")
        
        # Basic worker validation only
        if workers > cpu_count * 2:
            logger.warning(f"High worker count: {workers} workers on {cpu_count} cores")
        
        return True
        
    except ImportError:
        logger.warning("psutil not available - skipping system validation")
        return True

def estimate_custom_calibration_time(parameters: List[str], grid_points: int, workers: int) -> Dict[str, float]:
    """Estimate calibration time for custom configuration."""
    
    # Calculate total combinations: 3⁴ = 81
    total_combinations = grid_points ** len(parameters)
    
    # Optimized time per simulation with 10m resolution and 100 steps
    # 10m resolution = 4x fewer cells, 100 steps = 2.5x fewer steps
    base_time_per_sim_minutes = 1.0  # ~1 minute per simulation
    
    # Parallel efficiency factor
    parallel_efficiency = 0.9
    
    # Calculate times
    total_time_minutes = total_combinations * base_time_per_sim_minutes
    parallel_time_minutes = total_time_minutes / (workers * parallel_efficiency)
    
    # Convert to hours
    parallel_time_hours = parallel_time_minutes / 60
    
    # Memory estimation (peak usage)
    # 10m resolution uses ~40-50% less memory than 5m
    peak_memory_gb = 24.0  # Optimized estimate for 10m resolution
    
    return {
        'total_combinations': total_combinations,
        'base_time_per_sim_minutes': base_time_per_sim_minutes,
        'total_time_minutes': total_time_minutes,
        'parallel_time_minutes': parallel_time_minutes,
        'parallel_time_hours': parallel_time_hours,
        'peak_memory_gb': peak_memory_gb
    }

class CustomTenerifeCalibrator(TenerifeFirePerimeterCalibrator):
    """
    Custom version with specific optimizations for 10m resolution and 100 timesteps.
    """
    
    def __init__(self, **kwargs):
        # Override default parameters with custom settings
        kwargs.update({
            'experiment_name': f"tenerife_custom_10m_100t_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        })
        
        super().__init__(**kwargs)
        
        # Store custom config
        self.custom_config = CUSTOM_CONFIG
        
        # Override max_steps for 100 timesteps
        self.max_steps = CUSTOM_CONFIG['max_steps']
        
        logger.info(f"🚀 CustomTenerifeCalibrator initialized with 10m resolution, 100 timesteps")
        logger.info(f"📊 Target: {CUSTOM_CONFIG['estimated_hours']} hours")
    
    def _create_optimized_forest_model(self, config):
        """Create custom-optimized forest model with 10m resolution."""
        try:
            # Force 10m resolution for speed
            config.model_resolution = self.custom_config['model_resolution']
            
            optimized_model = create_optimized_forest_model(
                grid_size=config.grid_size,
                num_layers=config.num_layers,
                config=config,
                force_optimization=True
            )
            
            logger.info(f"✅ Created custom forest model: {type(optimized_model).__name__} (10m resolution)")
            return optimized_model
            
        except Exception as e:
            logger.error(f"❌ Failed to create optimized forest model: {e}")
            from src.core.forest_model import create_forest_model
            return create_forest_model(model_type='memory_optimized', config=config)
    
    def _create_optimized_simulation_engine(self, forest_model, config):
        """Create custom-optimized simulation engine with 100 timesteps."""
        try:
            # Force 100 timesteps for speed
            config.max_steps = self.max_steps
            
            optimized_engine = create_optimized_fire_simulation_engine(
                forest_model=forest_model,
                config=config,
                force_optimization=True
            )
            
            logger.info(f"✅ Created custom simulation engine: {type(optimized_engine).__name__} (100 timesteps)")
            return optimized_engine
            
        except Exception as e:
            logger.error(f"❌ Failed to create optimized simulation engine: {e}")
            from src.core.fire_simulation_engine import FireSimulationEngine
            return FireSimulationEngine(forest_model=forest_model, config=config)
    
    def _calculate_optimal_grid_size_from_day4(self, buffer_percent: float = 10.0) -> Tuple[int, int]:
        """
        Override to use 10m resolution instead of 5m for custom calibration.
        """
        try:
            # Import geopandas for shapefile reading
            if not hasattr(self, '_spatial_libs_available'):
                try:
                    import geopandas as gpd
                    self._spatial_libs_available = True
                except ImportError:
                    self._spatial_libs_available = False
            
            if not self._spatial_libs_available:
                logger.warning("⚠️  Spatial libraries not available, using fallback grid size")
                return (500, 500)  # Smaller fallback for 10m resolution
            
            import geopandas as gpd
            
            # Find Day 4 GeoJSON file (prioritize JSON over shapefiles)
            day4_file = None
            for day_dir in sorted(self.base_directory.iterdir()):
                if not day_dir.is_dir():
                    continue
                
                day_info = self._parse_day_directory(day_dir.name)
                if day_info and day_info[0] == 4:  # Day 4
                    file_path = self._find_shapefile(day_dir)
                    if file_path:
                        day4_file = file_path
                        break
            
            if not day4_file:
                logger.warning("⚠️  Day 4 file not found, using fallback grid size")
                return (500, 500)  # Smaller fallback for 10m resolution
            
            logger.info(f"📍 Using Day 4 file for grid size calculation: {day4_file.name}")
            
            # Load Day 4 GeoJSON file
            gdf = gpd.read_file(day4_file)
            
            # Log the original CRS
            logger.info(f"🗺️  Original CRS: {gdf.crs}")
            
            # Convert from CRS84 (degrees) to EPSG:25828 (meters) for Tenerife
            if gdf.crs != "EPSG:25828":
                logger.info(f"🔄 Converting from {gdf.crs} to EPSG:25828")
                gdf = gdf.to_crs("EPSG:25828")
            
            # Get bounds of ALL fire polygons (entire fire complex)
            bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
            
            # Move northern side 10% up for additional buffer
            height_m_original = bounds[3] - bounds[1]  # maxy - miny
            north_expansion = height_m_original * 0.10
            bounds = (bounds[0], bounds[1], bounds[2], bounds[3] + north_expansion)
            
            # Calculate dimensions in meters
            width_m = bounds[2] - bounds[0]  # maxx - minx
            height_m = bounds[3] - bounds[1]  # maxy - miny
            
            # Add buffer
            buffer_factor = 1.0 + (buffer_percent / 100.0)
            buffered_width_m = width_m * buffer_factor
            buffered_height_m = height_m * buffer_factor
            
            # CRITICAL FIX: Use 10m resolution instead of 5m for custom calibration
            cell_size_m = self.custom_config['model_resolution']  # 10.0m
            grid_width = int(buffered_width_m / cell_size_m)
            grid_height = int(buffered_height_m / cell_size_m)
            
            # Ensure minimum size but much smaller than before
            grid_width = max(grid_width, 250)  # Minimum 250x250 cells for 10m resolution
            grid_height = max(grid_height, 250)
            
            # Calculate total cells
            total_cells = grid_width * grid_height * 25  # 25 layers
            
            # Calculate area for reference
            grid_area_km2 = (grid_width * cell_size_m / 1000) * (grid_height * cell_size_m / 1000)
            
            logger.info(f"🗺️  Day 4 fire bounds (EPSG:25828): {bounds}")
            logger.info(f"🔥 Fire complex dimensions: {width_m:.0f}m × {height_m:.0f}m")
            logger.info(f"🎯 Grid: {grid_width} × {grid_height} = {total_cells/1e6:.1f}M cells ({grid_area_km2:.1f} km²)")
            logger.info(f"🎯 Using {cell_size_m}m resolution for custom calibration")
            
            return (grid_width, grid_height)
            
        except Exception as e:
            logger.error(f"❌ Error calculating optimal grid size: {e}")
            logger.warning("⚠️  Using fallback grid size")
            return (500, 500)  # Smaller fallback for 10m resolution
    
    def create_calibration_config(self, training_data, top_5_parameters=None, grid_size=None):
        """Create custom calibration configuration."""
        
        # Use custom parameters (top 4)
        if top_5_parameters is None:
            top_5_parameters = self.custom_config['parameters']
        
        # Create base config
        calib_config = super().create_calibration_config(
            training_data=training_data,
            top_5_parameters=top_5_parameters,
            grid_size=grid_size
        )
        
        # Override with custom settings
        calib_config.grid_search_points = self.custom_config['grid_search_points']
        calib_config.max_steps = self.max_steps
        calib_config.simulation_timeout_minutes = 20.0  # Shorter timeout for 100 steps
        calib_config.memory_limit_gb = self.memory_gb
        calib_config.max_workers = self.workers
        
        return calib_config

def create_quiet_progress_callback(total_combinations: int, quiet_mode: bool = False):
    """Create progress callback for calibration monitoring."""
    from src.core.calibration.grid_search import create_progress_callback
    
    if quiet_mode:
        def progress_callback(completed: int, total: int, current_result=None):
            if completed % 10 == 0 or completed == total:  # Update every 10 completions
                progress = (completed / total) * 100
                print(f"🎯 Progress: {progress:.1f}% ({completed}/{total})")
        return progress_callback
    else:
        return create_progress_callback(total_combinations)

def main():
    """Main execution function for custom calibration."""
    
    parser = argparse.ArgumentParser(
        description="Custom Tenerife fire perimeter calibration with 10m resolution and 100 timesteps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default custom configuration
  python scripts/run_tenerife_calibration_custom.py
  
  # With custom memory and workers
  python scripts/run_tenerife_calibration_custom.py --memory 64 --workers 32
  
  # Dry run (setup only)
  python scripts/run_tenerife_calibration_custom.py --dry-run
        """
    )
    
    # System configuration
    parser.add_argument('--memory', type=int, default=24,
                       help='Available memory in GB (default: 24)')
    parser.add_argument('--workers', type=int, default=48,
                       help='Number of parallel workers (default: 48)')
    parser.add_argument('--grid-points', type=int, default=3,
                       help='Grid search points per parameter (default: 3)')
    
    # Parameter configuration (use custom parameters)
    parser.add_argument('--parameters', nargs='+', 
                       default=CUSTOM_CONFIG['parameters'],
                       help='Parameters to calibrate (default: top 4 custom parameters)')
    
    # Data configuration
    parser.add_argument('--emsr-dir', type=str, 
                       default="EMSR Delineations",
                       help='Directory containing EMSR fire perimeter data')
    parser.add_argument('--training-days', nargs='+', type=int, default=[1, 2],
                       help='Days to use for training/calibration (default: [1, 2])')
    parser.add_argument('--test-days', nargs='+', type=int, default=[3, 4],
                       help='Days to use for testing/validation (default: [3, 4])')
    
    # Grid configuration
    parser.add_argument('--grid-size', type=int, default=None,
                       help='Override grid size (default: auto-calculate from Day 4)')
    
    # Execution control
    parser.add_argument('--dry-run', action='store_true',
                       help='Setup only, no calibration execution')
    parser.add_argument('--quiet', action='store_true',
                       help='Quiet mode with minimal output')
    
    args = parser.parse_args()
    
    print(f"🚀 CUSTOM TENERIFE FIRE PERIMETER CALIBRATION")
    print("=" * 60)
    print("Custom Configuration:")
    print(f"✅ Resolution: {CUSTOM_CONFIG['model_resolution']}m")
    print(f"✅ Timesteps: {CUSTOM_CONFIG['max_steps']}")
    print(f"✅ Parameters: {len(args.parameters)} ({', '.join(args.parameters)})")
    print(f"✅ Grid search: {args.grid_points} points per parameter")
    print(f"✅ Workers: {args.workers}")
    print(f"✅ Memory: {args.memory}GB")
    print(f"✅ Target: {CUSTOM_CONFIG['estimated_hours']} hours")
    print()
    
    # Log optimization status
    log_optimization_status()
    
    try:
        # Step 1: System validation
        print(f"\n🔍 SYSTEM VALIDATION")
        print("=" * 30)
        
        if not validate_system_resources(args.memory, args.workers):
            print("❌ System validation failed")
            return
        
        print(f"✅ System validated: {args.memory}GB memory, {args.workers} workers")
        
        # Step 2: Emergency cleanup
        print(f"\n🧹 EMERGENCY CLEANUP")
        print("=" * 30)
        
        try:
            emergency_cleanup_shared_memory()
            print("✅ Shared memory cleanup completed")
        except Exception as e:
            logger.warning(f"Shared memory cleanup failed: {e}")
        
        # Step 3: Memory protection setup
        print(f"\n🛡️  MEMORY PROTECTION SETUP")
        print("=" * 30)
        
        memory_thresholds = ProductionMemoryThresholds(
            process_warning_gb=args.memory * 0.6,
            process_critical_gb=args.memory * 0.8,
            process_emergency_gb=args.memory * 0.9,
            system_warning_percent=70.0,
            system_critical_percent=85.0,
            system_emergency_percent=95.0
        )
        
        setup_production_memory_protection(memory_thresholds)
        print("✅ Memory protection configured")
        
        # Step 4: Create custom calibrator
        print(f"\n🎯 CREATING CUSTOM CALIBRATOR")
        print("=" * 30)
        
        calibrator_kwargs = {
            'memory_gb': args.memory,
            'workers': args.workers,
            'grid_search_points': args.grid_points,
            'experiment_name': f"tenerife_custom_10m_100t_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        calibrator = CustomTenerifeCalibrator(**calibrator_kwargs)
        
        # Step 5: Create EMSR target data
        print(f"\n🔥 CREATING EMSR TARGET DATA")
        print("=" * 50)
        
        # Paths to EMSR files
        day1_path = f"{args.emsr_dir}/Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp"
        day2_path = f"{args.emsr_dir}/Day 2 (21_08_23)/EMSR685_AOI01_DEL_MONIT01_observedEventA_v1.shp"
        
        if not os.path.exists(day1_path):
            raise FileNotFoundError(f"Day 1 EMSR file not found: {day1_path}")
        if not os.path.exists(day2_path):
            raise FileNotFoundError(f"Day 2 EMSR file not found: {day2_path}")
        
        print(f"📁 Day 1 EMSR: {day1_path}")
        print(f"📁 Day 2 EMSR: {day2_path}")
        
        # CRITICAL: Use the same grid size for both target data creation and calibration
        if args.grid_size is not None:
            grid_size = (args.grid_size, args.grid_size)
            print(f"🎯 Using specified grid size: {grid_size[0]} × {grid_size[1]}")
        else:
            # Use Day 4 grid size calculation to match the calibrator's default method
            temp_calibrator = CustomTenerifeCalibrator(
                memory_gb=args.memory,
                workers=args.workers,
                grid_search_points=args.grid_points,
                experiment_name="temp_grid_calc"
            )
            grid_size = temp_calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
            print(f"🎯 Using Day 4 grid size: {grid_size[0]} × {grid_size[1]} (matches calibrator default)")
        
        # Step 6: Set up training/validation split
        print(f"\n📊 SETTING UP TRAINING/VALIDATION SPLIT")
        print("=" * 50)
        
        discovery = FirePerimeterDiscovery(args.emsr_dir)
        fire_dataset = discovery.discover_fire_perimeters()
        
        if not fire_dataset.fire_perimeters:
            raise ValueError(f"No fire perimeters found in {args.emsr_dir}")
        
        print(f"📁 Found {len(fire_dataset.fire_perimeters)} fire perimeters:")
        for fp in fire_dataset.fire_perimeters:
            print(f"   Day {fp.day_number} ({fp.date}): {fp.area_hectares:.1f} ha")
        
        # Set up training/validation split
        training_data, validation_data = calibrator.setup_training_test_split(
            fire_dataset,
            training_days=args.training_days,
            test_days=args.test_days
        )
        
        print(f"\n✅ Training/Validation split complete:")
        print(f"   🎯 Training (calibration): {len(training_data)} fire perimeters")
        for fp in training_data:
            print(f"      Day {fp.day_number} ({fp.date}): {fp.area_hectares:.1f} ha")
        print(f"   🧪 Validation: {len(validation_data)} fire perimeters")
        for fp in validation_data:
            print(f"      Day {fp.day_number} ({fp.date}): {fp.area_hectares:.1f} ha")
        
        # Step 7: Create calibration configuration
        calib_config = calibrator.create_calibration_config(
            training_data=training_data,
            top_5_parameters=args.parameters,
            grid_size=grid_size
        )
        
        # Step 8: Final confirmation and execution
        print(f"\n🚀 READY TO EXECUTE CUSTOM CALIBRATION")
        print("=" * 50)
        
        estimates = estimate_custom_calibration_time(args.parameters, args.grid_points, args.workers)
        
        print(f"📊 Performance estimates:")
        print(f"   Total combinations: {estimates['total_combinations']:,} ({args.grid_points}^{len(args.parameters)})")
        print(f"   Time per simulation: {estimates['base_time_per_sim_minutes']:.1f} minutes")
        print(f"   Parallel time: {estimates['parallel_time_hours']:.1f} hours")
        print(f"   Peak memory: {estimates['peak_memory_gb']:.1f} GB")
        print(f"   Results directory: {calibrator.results_dir}")
        print()
        print(f"🎯 Custom Configuration Summary:")
        print(f"   Resolution: {CUSTOM_CONFIG['model_resolution']}m (4x fewer cells)")
        print(f"   Timesteps: {CUSTOM_CONFIG['max_steps']} (2.5x fewer steps)")
        print(f"   Parameters: {len(args.parameters)} top parameters")
        print(f"   Grid search: {args.grid_points} points each")
        
        if args.dry_run:
            logger.info(f"✅ DRY RUN COMPLETE - Configuration validated")
            logger.info(f"📊 Runtime: {estimates['parallel_time_hours']:.1f}h, Memory: {estimates['peak_memory_gb']:.1f}GB")
            logger.info(f"📁 Results: {calibrator.results_dir}")
            logger.info("To run actual calibration, remove --dry-run flag")
            return
        
        # Final user confirmation
        if estimates['parallel_time_hours'] > 4:
            print(f"⚠️  This will take ~{estimates['parallel_time_hours']:.1f} hours")
            print(f"   Make sure you're on a stable node")
            
            response = input(f"\nContinue? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print(f"❌ Cancelled by user")
                return
        
        # Step 9: Execute custom calibration
        print(f"\n🚀 EXECUTING CUSTOM CALIBRATION")
        print("=" * 50)
        
        start_time = time.time()
        
        # Create progress callback
        progress_callback = create_quiet_progress_callback(
            estimates['total_combinations'], 
            quiet_mode=args.quiet
        )
        
        # Run calibration
        results = calibrator.run_calibration(
            calibration_config=calib_config,
            test_data=validation_data,
            progress_callback=progress_callback
        )
        
        total_time = time.time() - start_time
        
        # Step 10: Results summary
        print(f"\n✅ CUSTOM CALIBRATION COMPLETE")
        print("=" * 50)
        print(f"Total time: {total_time/3600:.2f} hours")
        print(f"Results saved to: {calibrator.results_dir}")
        
        if results and hasattr(results, 'best_parameters'):
            print(f"Best parameters: {results.best_parameters}")
            print(f"Best objective: {results.best_objective_value:.4f}")
        
    except Exception as e:
        logger.error(f"❌ Custom calibration failed: {e}")
        raise

if __name__ == "__main__":
    main()
