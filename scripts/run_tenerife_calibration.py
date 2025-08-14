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
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

logger = get_logger(__name__)


def validate_system_resources(memory_gb: int, workers: int) -> bool:
    """Validate that system has sufficient resources."""
    try:
        import psutil
        
        # Check memory
        total_memory_gb = psutil.virtual_memory().total / (1024**3)
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        
        print(f"🔍 SYSTEM RESOURCE CHECK:")
        print(f"   Total memory: {total_memory_gb:.1f} GB")
        print(f"   Available memory: {available_memory_gb:.1f} GB")
        print(f"   Required memory: {memory_gb} GB")
        
        # Check CPU cores
        cpu_count = psutil.cpu_count(logical=False)
        logical_cores = psutil.cpu_count(logical=True)
        
        print(f"   Physical CPU cores: {cpu_count}")
        print(f"   Logical CPU cores: {logical_cores}")
        print(f"   Requested workers: {workers}")
        
        # Validate memory
        if total_memory_gb < memory_gb * 0.9:
            print(f"❌ Insufficient memory: {total_memory_gb:.1f} GB < {memory_gb} GB required")
            return False
        
        if available_memory_gb < memory_gb * 0.5:
            print(f"⚠️  WARNING: Low available memory: {available_memory_gb:.1f} GB")
            print(f"   Consider closing other applications")
        
        # Validate CPU
        if workers > logical_cores:
            print(f"⚠️  WARNING: Workers ({workers}) > logical cores ({logical_cores})")
            print(f"   This may cause performance degradation")
        
        if workers > cpu_count * 1.5:
            print(f"❌ Excessive workers: {workers} workers for {cpu_count} physical cores")
            print(f"   Recommended maximum: {int(cpu_count * 1.5)}")
            return False
        
        print(f"✅ System resources validated")
        return True
        
    except ImportError:
        print(f"⚠️  Cannot validate system resources (psutil not available)")
        print(f"   Proceeding with user-specified configuration")
        return True


def estimate_calibration_time(parameters: List[str], grid_points: int, workers: int) -> dict:
    """Estimate calibration time and resource requirements."""
    total_combinations = grid_points ** len(parameters)
    
    # Updated estimates for full Tenerife domain WITH SHARED TERRAIN
    time_per_sim_minutes = 25.0  # 20-30 minutes per simulation (more conservative)
    memory_per_sim_gb = 4.0      # ~4 GB per simulation (conservative for dense array initialization)
    
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
  # Standard 64GB/60-worker configuration
  python run_tenerife_calibration.py
  
  # High-memory 128GB/120-worker configuration  
  python run_tenerife_calibration.py --memory 128 --workers 120
  
  # 4-point grid search for higher accuracy
  python run_tenerife_calibration.py --grid-points 4
  
  # Custom parameters from sensitivity analysis
  python run_tenerife_calibration.py --parameters fuel_consumption_rate terrain_effect_strength wind_influence_on_spread barranco_amplification slope_influence
  
  # Dry run to validate setup
  python run_tenerife_calibration.py --dry-run --verbose
        """
    )
    
    parser.add_argument(
        '--memory',
        type=int,
        default=64,
        choices=[64, 128],
        help='Available memory in GB (default: 64)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: auto-detect based on memory)'
    )
    
    parser.add_argument(
        '--grid-points',
        type=int,
        default=3,
        choices=[3, 4, 5],
        help='Grid points per parameter (default: 3)'
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
    
    args = parser.parse_args()
    
    # Set default workers based on memory (reduced for stability)
    if args.workers is None:
        args.workers = 20 if args.memory == 64 else 30  # Reduced from 60/120 to 20/30
    
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
        # Step 1: Validate system resources
        if not validate_system_resources(args.memory, args.workers):
            print(f"❌ System resource validation failed")
            print(f"   Consider using --memory 128 --workers 120 or reducing worker count")
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
        
        # Step 4: Create calibrator
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=args.memory,
            workers=args.workers,
            grid_search_points=args.grid_points,
            experiment_name=args.experiment_name
        )
        
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
            print(f"✅ DRY RUN COMPLETE - Configuration validated successfully")
            print(f"📊 Estimated runtime: {estimates['parallel_time_hours']:.1f} hours")
            print(f"💾 Estimated peak memory: {estimates['peak_memory_gb']:.1f} GB")
            print(f"📁 Results directory: {calibrator.results_dir}")
            print(f"\nTo run actual calibration, remove --dry-run flag")
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
        
        # Run calibration
        print(f"\n🔥 STARTING CALIBRATION EXECUTION")
        print(f"⏱️  Estimated completion: {estimates['parallel_time_hours']:.1f} hours")
        print(f"📁 Monitor progress in: {calibrator.results_dir}")
        
        start_time = time.time()
        
        results = calibrator.run_calibration(calib_config, test_data)
        
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
        for param, value in results['best_parameters'].items():
            print(f"   {param}: {value:.4f}")
        
        print(f"\n🧪 VALIDATION:")
        for test_case, test_result in results['validation_results'].items():
            print(f"   {test_case}: {test_result['status']}")
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"1. Review calibration results in {calibrator.results_dir}")
        print(f"2. Analyze parameter sensitivity from grid search")
        print(f"3. Validate results on independent fire data")
        print(f"4. Consider refining parameter ranges for focused calibration")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Calibration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Calibration failed: {e}")
        logger.error(f"Calibration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
