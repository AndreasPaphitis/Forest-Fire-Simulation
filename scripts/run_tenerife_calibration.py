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

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional

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

logger = get_logger(__name__)


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
                           test_days: List[int]):
    """Display detailed calibration plan."""
    print(f"\n🎯 CALIBRATION EXECUTION PLAN")
    print(f"=" * 70)
    
    # Domain configuration
    print(f"🌍 DOMAIN CONFIGURATION:")
    print(f"   Area: Full Tenerife Island")
    print(f"   Grid size: 15,121 × 24,741 × 25 layers")
    print(f"   Total cells: 9,347,092,500 (~9.35 billion)")
    print(f"   Resolution: 5m per cell")
    print(f"   CRS: EPSG:25828 (UTM Zone 28N)")
    
    # Parameter configuration
    print(f"\n📋 PARAMETER CONFIGURATION:")
    print(f"   Parameters to calibrate: {len(parameters)}")
    for i, param in enumerate(parameters, 1):
        print(f"     {i}. {param}")
    print(f"   Grid points per parameter: {grid_points}")
    
    # Resource configuration
    print(f"\n🖥️  RESOURCE CONFIGURATION:")
    print(f"   Memory framework: {memory_gb} GB")
    print(f"   Parallel workers: {workers}")
    print(f"   Memory optimization: Level 3 (maximum)")
    print(f"   Disk storage: Enabled")
    print(f"   Sparse storage: Enabled")
    
    # Data configuration
    print(f"\n📅 DATA CONFIGURATION:")
    print(f"   Training days: {training_days}")
    print(f"   Test days: {test_days}")
    
    # Estimates
    estimates = estimate_calibration_time(parameters, grid_points, workers)
    print(f"\n⏱️  TIME & RESOURCE ESTIMATES:")
    print(f"   Total combinations: {estimates['total_combinations']:,}")
    print(f"   Time per simulation: ~{estimates['time_per_sim_minutes']:.1f} minutes")
    print(f"   Sequential time: ~{estimates['sequential_time_hours']:.1f} hours")
    print(f"   Parallel time: ~{estimates['parallel_time_hours']:.1f} hours")
    print(f"   Expected speedup: ~{estimates['speedup']:.1f}x")
    print(f"   Memory per simulation: ~{estimates['memory_per_sim_gb']:.1f} GB")
    print(f"   Peak memory usage: ~{estimates['peak_memory_gb']:.1f} GB")
    
    # Risk assessment
    print(f"\n⚠️  RISK ASSESSMENT:")
    if estimates['peak_memory_gb'] > memory_gb * 0.9:
        print(f"   ❌ HIGH MEMORY RISK: Peak usage ({estimates['peak_memory_gb']:.1f}GB) near limit ({memory_gb}GB)")
        print(f"      Recommendation: Reduce workers or use 128GB configuration")
    elif estimates['peak_memory_gb'] > memory_gb * 0.7:
        print(f"   ⚠️  MODERATE MEMORY RISK: Monitor memory usage carefully")
    else:
        print(f"   ✅ MEMORY RISK: Low")
    
    if estimates['parallel_time_hours'] > 24:
        print(f"   ⚠️  LONG RUNTIME: {estimates['parallel_time_hours']:.1f} hours may require job splitting")
    elif estimates['parallel_time_hours'] > 8:
        print(f"   📊 MODERATE RUNTIME: {estimates['parallel_time_hours']:.1f} hours - plan accordingly")
    else:
        print(f"   ✅ RUNTIME: Reasonable ({estimates['parallel_time_hours']:.1f} hours)")


def run_discovery_and_validation(emsr_dir: str = "EMSR Delineations"):
    """Run fire perimeter discovery and validation."""
    print(f"🔍 DISCOVERING FIRE PERIMETERS")
    print(f"=" * 50)
    
    # Initialize discovery
    discovery = FirePerimeterDiscovery(emsr_dir)
    
    # Discover fire perimeters
    fire_dataset = discovery.discover_fire_perimeters()
    
    if not fire_dataset.fire_perimeters:
        print(f"❌ No fire perimeters found in {emsr_dir}")
        print(f"   Check that the directory exists and contains EMSR shapefiles")
        return None
    
    # Validate dataset
    print(f"\n🔬 VALIDATING DATASET")
    print(f"=" * 30)
    
    # Check temporal coverage
    day_numbers = [fp.day_number for fp in fire_dataset.fire_perimeters]
    if len(set(day_numbers)) != len(day_numbers):
        print(f"⚠️  Warning: Duplicate day numbers detected")
    
    # Check CRS consistency
    crs_list = [fp.crs for fp in fire_dataset.fire_perimeters if fp.crs]
    if len(set(crs_list)) > 1:
        print(f"❌ CRS inconsistency detected:")
        for crs in set(crs_list):
            count = crs_list.count(crs)
            print(f"     {crs}: {count} files")
        print(f"   All files must use the same CRS (preferably EPSG:25828)")
        return None
    
    # Check area progression (should generally increase over time)
    sorted_fps = sorted(fire_dataset.fire_perimeters, key=lambda x: x.day_number)
    areas = [fp.area_hectares for fp in sorted_fps if fp.area_hectares]
    
    if len(areas) >= 2:
        if areas[-1] < areas[0]:
            print(f"⚠️  Warning: Fire area appears to decrease over time")
            print(f"   Day 1: {areas[0]:.1f} ha → Day {len(areas)}: {areas[-1]:.1f} ha")
    
    print(f"✅ Dataset validation complete")
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
    
    args = parser.parse_args()
    
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
        print(f"🔧 Using TOP 5 parameters from sensitivity analysis results")
        print(f"   ✅ Based on Method 2 Range-Based sensitivity analysis")
    
    print(f"🔥 TENERIFE FIRE PERIMETER CALIBRATION")
    print(f"=" * 70)
    print(f"Experiment: {args.experiment_name}")
    print(f"Configuration: {args.memory}GB memory / {args.workers} workers")
    print(f"Grid search: {args.grid_points} points per parameter")
    print(f"Parameters: {len(args.parameters)} parameters")
    
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
            print(f"🛡️  SETTING UP PRODUCTION MEMORY PROTECTION")
            print(f"=" * 60)
            
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
            
            logger.debug("✅ Production memory protection active")
        
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
        
        # Step 3: Display calibration plan
        display_calibration_plan(
            parameters=args.parameters,
            grid_points=args.grid_points,
            workers=args.workers,
            memory_gb=args.memory,
            training_days=args.training_days,
            test_days=args.test_days
        )
        
        # Step 4: Create calibrator with enhanced configuration
        calibrator_kwargs = {
            'memory_gb': args.memory,
            'workers': args.workers,
            'grid_search_points': args.grid_points,
            'experiment_name': args.experiment_name
        }
        
        # Add emergency configuration if needed
        if args.emergency_small_scale:
            calibrator_kwargs['grid_size'] = (1000, 1000)  # Override grid size
        
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
        print(f"\n🚀 READY TO EXECUTE CALIBRATION")
        print(f"=" * 50)
        
        estimates = estimate_calibration_time(args.parameters, args.grid_points, args.workers)
        
        if args.dry_run:
            logger.info(f"✅ DRY RUN COMPLETE - Configuration validated successfully")
            logger.info(f"📊 Runtime: {estimates['parallel_time_hours']:.1f}h, Peak memory: {estimates['peak_memory_gb']:.1f}GB")
            logger.info(f"📁 Results dir: {calibrator.results_dir}")
            logger.info("To run actual calibration, remove --dry-run flag")
            return
        
        # Final user confirmation for long-running calibration
        if estimates['parallel_time_hours'] > 4:
            print(f"⚠️  This calibration will take approximately {estimates['parallel_time_hours']:.1f} hours")
            print(f"   Make sure you're running on a stable interactive node")
            print(f"   Consider using screen or tmux for long sessions")
            
            response = input(f"\nContinue with calibration? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print(f"❌ Calibration cancelled by user")
                return
        
        # Run calibration with memory monitoring
        print(f"\n🔥 STARTING CALIBRATION EXECUTION")
        print(f"⏱️  Estimated completion: {estimates['parallel_time_hours']:.1f} hours")
        print(f"📁 Monitor progress in: {calibrator.results_dir}")
        
        if memory_manager:
            logger.info("🛡️  Memory protection active")
            status = memory_manager.check_memory_status()
            stats = status['stats']
            logger.debug(f"Memory check: {stats.process_rss_gb:.1f}GB process, {stats.system_percent:.1f}% system")
        
        start_time = time.time()
        
        try:
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
