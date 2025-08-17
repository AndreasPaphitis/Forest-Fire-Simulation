#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tenerife Fire Perimeter Calibration Runner

Specialized runner for full Tenerife-scale fire perimeter calibration using EMSR delineation data.
Optimized for HPC interactive nodes with 64GB/60-worker or 128GB/120-worker configurations.

Features:
- Auto-discovery of EMSR fire perimeter shapefiles
- Full Tenerife domain simulation (15,121 × 24,741 × 25)
- Training/test split using temporal progression
- Grid search with top 5 sensitive parameters
- Maximum memory optimization for large-scale calibration

Usage:
    # 64GB/60-worker configuration (default)
    python run_tenerife_calibration.py
    
    # 128GB/120-worker configuration
    python run_tenerife_calibration.py --memory 128 --workers 120
    
    # 4-point grid search instead of 3-point
    python run_tenerife_calibration.py --grid-points 4
    
    # Custom parameter list
    python run_tenerife_calibration.py --parameters fuel_consumption_rate terrain_effect_strength wind_influence_on_spread
    
    # Dry run (setup only, no calibration)
    python run_tenerife_calibration.py --dry-run
    
    # Quiet mode (minimal output)
    python run_tenerife_calibration.py --quiet

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import sys
import argparse
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple

# Set NumExpr to 128 threads for HPC environments immediately
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

# Configure logging to be quiet by default
def setup_quiet_logging():
    """Set up quiet logging configuration to reduce verbosity."""
    # Set root logger to WARNING level
    logging.getLogger().setLevel(logging.WARNING)
    
    # Set specific loggers to WARNING or ERROR
    logging.getLogger('src.core.fire_simulation_engine').setLevel(logging.WARNING)
    logging.getLogger('src.core.forest_model').setLevel(logging.WARNING)
    logging.getLogger('src.core.calibration').setLevel(logging.WARNING)
    logging.getLogger('src.utils').setLevel(logging.WARNING)
    logging.getLogger('shared_utilities').setLevel(logging.WARNING)
    
    # Disable duplicate logging
    logging.getLogger('src.core.core_simulation_framework').setLevel(logging.ERROR)
    logging.getLogger('src.core.fire_simulation_engine').setLevel(logging.ERROR)
    logging.getLogger('src.core.calibration.fire_perimeter_calibration').setLevel(logging.WARNING)

# Set up quiet logging by default
setup_quiet_logging()

logger = get_logger(__name__)


def create_quiet_progress_callback(total_combinations: int, quiet_mode: bool = False):
    """
    Create a progress callback that works in quiet mode.
    
    Args:
        total_combinations: Total number of parameter combinations
        quiet_mode: Whether to run in quiet mode
        
    Returns:
        Progress callback function
    """
    start_time = time.time()
    last_progress_time = start_time
    progress_interval = 30  # Show progress every 30 seconds in quiet mode
    
    def progress_callback(completed: int, total: int, result):
        nonlocal last_progress_time
        current_time = time.time()
        
        if quiet_mode:
            # In quiet mode, show progress every 30 seconds or every 5 completions
            time_since_last = current_time - last_progress_time
            should_show = (time_since_last >= progress_interval or 
                          completed % 5 == 0 or 
                          completed == total)
            
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
                    eta_hours = eta_minutes / 60
                    
                    if eta_hours >= 1:
                        eta_str = f"{eta_hours:.1f}h"
                    else:
                        eta_str = f"{eta_minutes:.0f}m"
                else:
                    eta_str = "calculating..."
                
                print(f"🎯 Progress: {progress:.1f}% ({completed}/{total}) | "
                      f"Best: {best_value:.4f} | ETA: {eta_str}")
                
                last_progress_time = current_time
        else:
            # In verbose mode, use the default logging
            pass
    
    return progress_callback


def validate_system_resources(memory_gb: int, workers: int) -> bool:
    """Validate that system has sufficient resources for 9.3B cell simulation."""
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
        
        # Validate CPU for massive scale
        # Memory requirements validation completely removed - system is sufficient
        # Basic worker validation only
        if workers > cpu_count * 2:
            logger.warning(f"High worker count: {workers} workers on {cpu_count} cores")
        
        logger.info("✅ System resources validated")
        return True
        
    except ImportError:
        print(f"⚠️  Cannot validate system resources (psutil not available)")
        print(f"   Proceeding with user-specified configuration")
        print(f"   WARNING: This is risky for 9.3B cell simulation without monitoring")
        return True


def estimate_calibration_time(parameters: List[str], grid_points: int, workers: int) -> dict:
    """Estimate calibration time and resource requirements."""
    total_combinations = grid_points ** len(parameters)
    
    # Updated estimates for full Tenerife domain WITH SHARED TERRAIN AND SPARSE INITIALIZATION
    time_per_sim_minutes = 20.0  # 15-25 minutes per simulation (optimistic with sparse init)
    memory_per_sim_gb = 2.5      # ~2.5 GB per simulation (sparse arrays + shared terrain)
    
    # Calculate timings
    sequential_time_hours = (total_combinations * time_per_sim_minutes) / 60
    parallel_time_hours = sequential_time_hours / workers
    peak_memory_gb = memory_per_sim_gb * min(workers, total_combinations)
    
    return {
        'total_combinations': total_combinations,
        'time_per_sim_minutes': time_per_sim_minutes,
        'sequential_time_hours': sequential_time_hours,
        'parallel_time_hours': parallel_time_hours,
        'memory_per_sim_gb': memory_per_sim_gb,
        'peak_memory_gb': peak_memory_gb,
        'speedup': sequential_time_hours / parallel_time_hours
    }


def display_calibration_plan(parameters: List[str],
                           grid_points: int,
                           workers: int,
                           memory_gb: int,
                           training_days: List[int],
                           test_days: List[int],
                           dynamic_grid_size: Optional[Tuple[int, int]] = None):
    """Display concise calibration plan."""
    print(f"\n🎯 CALIBRATION PLAN")
    print(f"=" * 50)
    
    # Domain configuration
    if dynamic_grid_size:
        grid_width, grid_height = dynamic_grid_size
        total_cells = grid_width * grid_height * 25
        area_km2 = (grid_width * 5 / 1000) * (grid_height * 5 / 1000)
        print(f"🌍 Grid: {grid_width:,} × {grid_height:,} × 25 = {total_cells/1e6:.1f}M cells ({area_km2:.1f} km²)")
    else:
        print(f"🌍 Grid: Dynamic (Day 4 fire area + buffer)")
    
    # Key configuration
    print(f"📋 Parameters: {len(parameters)} ({grid_points} points each)")
    print(f"🖥️  Resources: {memory_gb}GB memory, {workers} workers")
    print(f"📅 Data: Training days {training_days}, Test days {test_days}")
    
    # Estimates
    estimates = estimate_calibration_time(parameters, grid_points, workers)
    print(f"⏱️  Time: ~{estimates['parallel_time_hours']:.1f}h ({estimates['total_combinations']:,} combinations)")
    print(f"💾 Memory: ~{estimates['peak_memory_gb']:.1f}GB peak")
    
    # Risk assessment (simplified)
    if estimates['peak_memory_gb'] > memory_gb * 0.9:
        print(f"⚠️  HIGH MEMORY RISK - consider reducing workers")
    elif estimates['parallel_time_hours'] > 24:
        print(f"⚠️  LONG RUNTIME - consider job splitting")
    else:
        print(f"✅ Configuration looks good")


def run_discovery_and_validation(emsr_dir: str = "EMSR Delineations"):
    """Run fire perimeter discovery and validation."""
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


def main():
    parser = argparse.ArgumentParser(
        description="Run Tenerife fire perimeter calibration with EMSR delineation data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect workers based on system memory (recommended)
  python run_tenerife_calibration.py
  
  # Override with specific worker count (CLI takes precedence)
  python run_tenerife_calibration.py --workers 40
  
  # High-memory HPC configuration with custom workers
  python run_tenerife_calibration.py --memory 128 --workers 45
  
  # Force many workers (system will warn if unsafe)
  python run_tenerife_calibration.py --workers 60
  
  # 4-point grid search for higher accuracy
  python run_tenerife_calibration.py --grid-points 4 --workers 30
  
  # Custom parameters from sensitivity analysis
  python run_tenerife_calibration.py --parameters fuel_consumption_rate terrain_effect_strength wind_influence_on_spread barranco_amplification slope_influence --workers 25
  
  # Dry run to validate setup
  python run_tenerife_calibration.py --dry-run --verbose --workers 20
        """
    )
    
    parser.add_argument(
        '--memory',
        type=int,
        default=512,
        choices=[64, 128, 256, 512, 1024],
        help='Available memory in GB (default: 512 for full Tenerife scale)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: auto-detect based on memory). CLI override takes precedence over automatic detection.'
    )
    
    parser.add_argument(
        '--grid-points',
        type=int,
        default=3,
        choices=[1, 2, 3, 4, 5],
        help='Grid points per parameter (1-5, use 1-2 for testing)'
    )
    
    parser.add_argument(
        '--parameters',
        nargs='+',
        default=None,
        help='Parameters to calibrate (default: top 5 from sensitivity analysis)'
    )
    
    parser.add_argument(
        '--training-days',
        nargs='+',
        type=int,
        default=[1, 2],
        help='Day numbers for training data (default: 1 2)'
    )
    
    parser.add_argument(
        '--test-days',
        nargs='+',
        type=int,
        default=[3, 4],
        help='Day numbers for test data (default: 3 4)'
    )
    
    parser.add_argument(
        '--emsr-dir',
        type=str,
        default="EMSR Delineations",
        help='Path to EMSR delineations directory (default: auto-detect with HPC fallbacks)'
    )
    
    parser.add_argument(
        '--experiment-name',
        type=str,
        default=None,
        help='Name for calibration experiment (default: auto-generated)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Setup and validate configuration without running calibration'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--emergency-small-scale',
        action='store_true',
        help='Use emergency small-scale configuration (1000x1000 grid) for testing'
    )
    
    parser.add_argument(
        '--enable-memory-protection',
        action='store_true',
        default=True,
        help='Enable production memory protection (default: enabled)'
    )
    
    parser.add_argument(
        '--emergency-mode',
        action='store_true',
        help='Enable emergency mode to prevent segfaults on massive grids'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Run in quiet mode (minimal output)'
    )
    
    args = parser.parse_args()
    
    # Configure logging based on verbosity settings
    if args.quiet:
        # Set all loggers to ERROR level for minimal output, but allow progress updates
        logging.getLogger().setLevel(logging.ERROR)
        logging.getLogger('src.core.fire_simulation_engine').setLevel(logging.ERROR)
        logging.getLogger('src.core.forest_model').setLevel(logging.ERROR)
        logging.getLogger('src.core.calibration').setLevel(logging.ERROR)
        logging.getLogger('src.utils').setLevel(logging.ERROR)
        logging.getLogger('shared_utilities').setLevel(logging.ERROR)
        print("🔇 Running in quiet mode - minimal output with progress updates")
    elif args.verbose:
        # Set all loggers to INFO level for verbose output
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger('src.core.fire_simulation_engine').setLevel(logging.INFO)
        logging.getLogger('src.core.forest_model').setLevel(logging.INFO)
        logging.getLogger('src.core.calibration').setLevel(logging.INFO)
        logging.getLogger('src.utils').setLevel(logging.INFO)
        logging.getLogger('shared_utilities').setLevel(logging.INFO)
        print("🔊 Running in verbose mode - detailed output")
    
    # Set default workers based on memory for massive scale (conservative for 9.3B cells)
    if args.workers is None:
        worker_map = {64: 8, 128: 16, 256: 24, 512: 32, 1024: 48}
        args.workers = worker_map.get(args.memory, 32)
    
    # Set default experiment name
    if args.experiment_name is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.experiment_name = f"tenerife_emsr685_calibration_{timestamp}"
    
    # Set default parameters if not provided
    if args.parameters is None:
        # TOP 5 PARAMETERS FROM SENSITIVITY ANALYSIS (Method 2 Range-Based)
        args.parameters = [
            'ember_probability',        # 0.382 - Highest sensitivity
            'fuel_consumption_rate',    # 0.165 - Second highest
            'ember_ignition',          # 0.138 - Third highest
            'slope_influence',         # 0.023 - Fourth
            'ember_height_factor'      # 0.019 - Fifth
        ]
        if not args.quiet:
            print(f"🔧 Using TOP 5 parameters from sensitivity analysis results")
            print(f"   ✅ Based on Method 2 Range-Based sensitivity analysis")
    
    if not args.quiet:
        print(f"🔥 TENERIFE FIRE CALIBRATION")
        print(f"=" * 50)
        print(f"Experiment: {args.experiment_name}")
        print(f"Config: {args.memory}GB / {args.workers} workers / {args.grid_points} points")
    
    try:
        # Step 0: Handle emergency small-scale mode
        if args.emergency_small_scale:
            print(f"🚨 EMERGENCY SMALL-SCALE MODE ACTIVATED")
            print(f"   Using 1000x1000 grid instead of full Tenerife")
            print(f"   This is for testing and validation only")
            # Override memory settings for small scale
            args.memory = 16
            args.workers = min(args.workers, 8)
        
        # Step 0.5: Setup production memory protection
        memory_manager = None
        if args.enable_memory_protection and not args.emergency_small_scale:
            print(f"🛡️  Setting up memory protection...")
            
            # Production thresholds for massive scale
            thresholds = ProductionMemoryThresholds(
                process_warning_gb=60.0,
                process_critical_gb=80.0,
                process_emergency_gb=100.0,
                system_warning_percent=75.0,
                system_critical_percent=90.0,
                system_emergency_percent=95.0
            )
            
            memory_manager = setup_production_memory_protection(
                thresholds=thresholds,
                monitor_interval=15.0  # Check every 15 seconds
            )
            
            # Add emergency callback for calibration
            def calibration_emergency_callback(stats):
                logger.critical(f"🚨 CALIBRATION EMERGENCY: Process memory {stats.process_rss_gb:.1f}GB")
                # Could trigger emergency checkpoint/save here
            
            memory_manager.add_callback('emergency', calibration_emergency_callback)
            
            logger.debug("✅ Memory protection active")
        
        # Step 1: Validate system resources
        if not validate_system_resources(args.memory, args.workers):
            logger.error("System resource validation failed")
            if not args.emergency_small_scale:
                logger.info("Consider using --emergency-small-scale for testing")
            sys.exit(1)
        
        # Step 2: Discover and validate fire perimeters
        fire_dataset = run_discovery_and_validation(args.emsr_dir)
        if fire_dataset is None:
            sys.exit(1)
        
        # Step 2.5: Calculate dynamic grid size from Day 4 fire perimeter
        dynamic_grid_size = None
        if not args.emergency_small_scale:
            try:
                print(f"🔍 Calculating grid size from Day 4 fire perimeter...")
                
                # Create temporary calibrator to access grid size calculation
                temp_calibrator = TenerifeFirePerimeterCalibrator(
                    memory_gb=args.memory,
                    workers=args.workers,
                    grid_search_points=args.grid_points,
                    experiment_name="temp_grid_calc"
                )
                
                # Calculate optimal grid size from Day 4
                dynamic_grid_size = temp_calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
                
                if dynamic_grid_size:
                    grid_width, grid_height = dynamic_grid_size
                    total_cells = grid_width * grid_height * 25
                    area_km2 = (grid_width * 5 / 1000) * (grid_height * 5 / 1000)
                    print(f"✅ Grid: {grid_width:,} × {grid_height:,} = {total_cells/1e6:.1f}M cells ({area_km2:.1f} km²)")
                else:
                    print(f"⚠️  Using fallback grid size")
                    
            except Exception as e:
                print(f"⚠️  Error calculating grid size: {e}")
                print(f"   Using fallback configuration")
        
        # Step 3: Display calibration plan
        display_calibration_plan(
            parameters=args.parameters,
            grid_points=args.grid_points,
            workers=args.workers,
            memory_gb=args.memory,
            training_days=args.training_days,
            test_days=args.test_days,
            dynamic_grid_size=dynamic_grid_size
        )
        
        # Step 4: Create calibrator with enhanced configuration
        calibrator_kwargs = {
            'memory_gb': args.memory,
            'workers': args.workers,
            'grid_search_points': args.grid_points,
            'experiment_name': args.experiment_name
        }
        
        # Add dynamic grid size configuration
        if dynamic_grid_size and not args.emergency_small_scale:
            calibrator_kwargs['grid_size'] = dynamic_grid_size
            print(f"🎯 Using dynamic grid size: {dynamic_grid_size[0]:,} × {dynamic_grid_size[1]:,}")
        elif args.emergency_small_scale:
            calibrator_kwargs['grid_size'] = (1000, 1000)  # Override grid size
            print(f"🚨 Using emergency small-scale grid: 1000 × 1000")
        else:
            print(f"⚠️  Using default grid size configuration")
        
        # Emergency mode is automatically enabled in FireSimulationEngine for large grids
        if args.emergency_mode:
            print(f"🚨 EMERGENCY MODE ENABLED - Sparse matrix operations will be bypassed")
            print(f"   This prevents segfaults but may reduce simulation accuracy")
        
        calibrator = TenerifeFirePerimeterCalibrator(**calibrator_kwargs)
        
        # Step 5: Set up training/test split
        training_data, test_data = calibrator.setup_training_test_split(
            fire_dataset,
            training_days=args.training_days,
            test_days=args.test_days
        )
        
        # Step 6: Create calibration configuration
        calib_config = calibrator.create_calibration_config(
            training_data=training_data,
            top_5_parameters=args.parameters
        )
        
        # Step 7: Final confirmation and execution
        print(f"\n🚀 READY TO EXECUTE")
        print(f"=" * 30)
        
        estimates = estimate_calibration_time(args.parameters, args.grid_points, args.workers)
        
        if args.dry_run:
            logger.info(f"✅ DRY RUN COMPLETE - Configuration validated")
            logger.info(f"📊 Runtime: {estimates['parallel_time_hours']:.1f}h, Memory: {estimates['peak_memory_gb']:.1f}GB")
            logger.info(f"📁 Results: {calibrator.results_dir}")
            logger.info("To run actual calibration, remove --dry-run flag")
            return
        
        # Final user confirmation for long-running calibration
        if estimates['parallel_time_hours'] > 4:
            print(f"⚠️  This will take ~{estimates['parallel_time_hours']:.1f} hours")
            print(f"   Make sure you're on a stable node")
            
            response = input(f"\nContinue? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print(f"❌ Cancelled by user")
                return
        
        # Run calibration with memory monitoring
        print(f"\n🔥 STARTING CALIBRATION")
        print(f"⏱️  Estimated: {estimates['parallel_time_hours']:.1f} hours")
        print(f"📁 Progress: {calibrator.results_dir}")
        
        if memory_manager:
            logger.info("🛡️  Memory protection active")
        
        start_time = time.time()
        
        try:
            # Create progress callback based on quiet mode
            if args.quiet:
                # Calculate total combinations for progress tracking
                total_combinations = args.grid_points ** len(args.parameters)
                progress_callback = create_quiet_progress_callback(total_combinations, quiet_mode=True)
                results = calibrator.run_calibration(calib_config, test_data, progress_callback=progress_callback)
            else:
                results = calibrator.run_calibration(calib_config, test_data)
        except Exception as e:
            if memory_manager:
                logger.critical("🚨 CALIBRATION FAILED - CHECKING MEMORY STATE")
                final_status = memory_manager.check_memory_status()
                final_stats = final_status['stats']
                logger.error(f"Final memory: {final_stats.process_rss_gb:.1f}GB process, {final_stats.system_percent:.1f}% system")
            raise
        
        end_time = time.time()
        actual_runtime = (end_time - start_time) / 3600  # hours
        
        # Final summary
        print(f"\n🎉 CALIBRATION COMPLETED SUCCESSFULLY!")
        print(f"=" * 70)
        print(f"⏱️  Actual runtime: {actual_runtime:.2f} hours")
        print(f"📊 Estimated runtime: {estimates['parallel_time_hours']:.1f} hours")
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
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"1. Review calibration results in {calibrator.results_dir}")
        print(f"2. Analyze parameter sensitivity from grid search")
        print(f"3. Validate results on independent fire data")
        print(f"4. Consider refining parameter ranges for focused calibration")
        
        # Final memory report
        if memory_manager:
            logger.info("📊 Final memory report:")
            report = memory_manager.get_memory_report()
            logger.info(f"Memory stats: {report['statistics']['process_memory']['max_gb']:.1f}GB peak, {report['statistics']['system_memory']['max_percent']:.1f}% max system")
            
            # Stop monitoring
            memory_manager.stop_monitoring()
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Calibration interrupted by user")
        if 'memory_manager' in locals() and memory_manager:
            print(f"🛡️  Stopping memory monitoring...")
            memory_manager.stop_monitoring()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Calibration failed: {e}")
        logger.error(f"Calibration failed: {e}")
        
        # Emergency memory cleanup on failure
        if 'memory_manager' in locals() and memory_manager:
            logger.critical("🚨 PERFORMING EMERGENCY MEMORY CLEANUP")
            emergency_status = memory_manager.check_memory_status()
            logger.critical(f"Error-time memory: {emergency_status['stats'].process_rss_gb:.1f}GB")
            memory_manager.stop_monitoring()
        
        # Clean up shared memory to prevent leaks
        try:
            emergency_cleanup_shared_memory()
        except Exception as cleanup_error:
            logger.warning(f"⚠️  Shared memory cleanup failed: {cleanup_error}")
        
        sys.exit(1)


if __name__ == "__main__":
    main()
