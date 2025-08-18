#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Focused Calibration Runner

This script runs focused grid search calibration using the top 5 most sensitive parameters
identified from the sensitivity analysis completed on 2025-08-18.

Top 5 Parameters (from sensitivity analysis):
1. spread_probability: 1.4063 (CRITICAL)
2. fuel_consumption_rate: 0.1609 (CRITICAL)
3. ember_probability: 0.1159 (CRITICAL)
4. ember_ignition: 0.0564 (CRITICAL)
5. fuel_moisture_baseline: 0.0382 (MODERATE)

Configuration:
- Grid points: 3 per parameter
- Total combinations: 3^5 = 243
- Estimated time: 20-30 minutes
- Memory requirement: <100 MB

Author: Forest Fire Simulation Team
Date: 2025-08-18
Version: 1.0
"""

import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
    from src.utils.logging_utils import get_logger
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Run focused calibration using top 5 parameters from sensitivity analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run focused calibration with default settings
  python scripts/run_focused_calibration.py
  
     # Run with custom grid points
   python scripts/run_focused_calibration.py --grid-points 5
  
  # Run with custom workers
  python scripts/run_focused_calibration.py --workers 10
  
  # Run with custom experiment name
  python scripts/run_focused_calibration.py --name "focused_calibration_v2"
        """
    )
    
    parser.add_argument(
        "--grid-points", type=int, default=3,
        help="Number of grid points per parameter (default: 3)"
    )
    
    parser.add_argument(
        "--workers", type=int, default=10,
        help="Number of parallel workers (default: 10)"
    )
    
    parser.add_argument(
        "--memory", type=int, default=50,
        help="Memory limit in GB (default: 50)"
    )
    
    parser.add_argument(
        "--name", type=str, default=None,
        help="Experiment name (default: auto-generated)"
    )
    
    parser.add_argument(
        "--training-days", nargs='+', type=int, default=[1, 2],
        help="Training days (default: 1 2)"
    )
    
    parser.add_argument(
        "--test-days", nargs='+', type=int, default=[3, 4],
        help="Test days (default: 3 4)"
    )
    
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show configuration without running calibration"
    )
    
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Auto-generate experiment name if not provided
    if args.name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.name = f"focused_calibration_top5_{timestamp}"
    
    # Top 5 parameters from sensitivity analysis (2025-08-18 results)
    top_5_parameters = [
        'spread_probability',        # 1.4063 - CRITICAL (13x more sensitive than #2)
        'fuel_consumption_rate',     # 0.1609 - CRITICAL
        'ember_probability',         # 0.1159 - CRITICAL
        'ember_ignition',           # 0.0564 - CRITICAL
        'fuel_moisture_baseline'    # 0.0382 - MODERATE
    ]
    
    # Calculate combinations
    total_combinations = args.grid_points ** len(top_5_parameters)
    
    print("🎯 FOCUSED CALIBRATION USING SENSITIVITY ANALYSIS RESULTS")
    print("=" * 70)
    print(f"📅 Analysis Date: 2025-08-18")
    print(f"🔬 Method: Method 2 Range-Based Sensitivity Analysis")
    print(f"📊 Top 5 Parameters (from sensitivity analysis):")
    
    for i, param in enumerate(top_5_parameters, 1):
        sensitivity_scores = [1.4063, 0.1609, 0.1159, 0.0564, 0.0382]
        print(f"   {i}. {param}: {sensitivity_scores[i-1]:.4f}")
    
    print(f"\n⚙️  CALIBRATION CONFIGURATION:")
    print(f"   Grid points per parameter: {args.grid_points}")
    print(f"   Total combinations: {args.grid_points}^{len(top_5_parameters)} = {total_combinations:,}")
    print(f"   Parallel workers: {args.workers}")
    print(f"   Memory limit: {args.memory} GB")
    print(f"   Training days: {args.training_days}")
    print(f"   Test days: {args.test_days}")
    print(f"   Experiment name: {args.name}")
    
         # Estimate time and memory (optimized for Day 4 grid with buffer)
     time_per_sim_minutes = 3.0  # Day 4 grid size estimate
     total_time_hours = (total_combinations * time_per_sim_minutes) / (60 * args.workers)
     memory_per_sim_gb = 0.2  # Optimized for Day 4 area
     peak_memory_gb = memory_per_sim_gb * min(args.workers, total_combinations)
    
    print(f"\n⏱️  ESTIMATES:")
    print(f"   Time per simulation: ~{time_per_sim_minutes:.1f} minutes")
    print(f"   Total time: ~{total_time_hours:.1f} hours")
    print(f"   Peak memory: ~{peak_memory_gb:.1f} GB")
    print(f"   Speedup: {total_combinations * time_per_sim_minutes / 60 / total_time_hours:.1f}x")
    
    if args.dry_run:
        print(f"\n✅ DRY RUN COMPLETE - Configuration validated")
        return
    
    # Validate memory requirements
    if peak_memory_gb > args.memory * 0.9:
        print(f"\n⚠️  WARNING: Peak memory ({peak_memory_gb:.1f} GB) may exceed limit ({args.memory} GB)")
        print(f"   Consider reducing workers or grid points")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Calibration cancelled")
            return
    
    print(f"\n🚀 STARTING FOCUSED CALIBRATION...")
    print(f"   Target completion: ~{total_time_hours:.1f} hours")
    print(f"   Results will be saved to: calibration_results/{args.name}")
    
    try:
        # Initialize calibrator
        calibrator = TenerifeFirePerimeterCalibrator(
            experiment_name=args.name,
            grid_search_points=args.grid_points,
            workers=args.workers,
            memory_gb=args.memory,
            training_days=args.training_days,
            test_days=args.test_days,
            verbose=args.verbose
        )
        
        # Run calibration with top 5 parameters
        start_time = time.time()
        results = calibrator.run_calibration(top_5_parameters=top_5_parameters)
        end_time = time.time()
        
        # Display results
        runtime_hours = (end_time - start_time) / 3600
        print(f"\n🎉 FOCUSED CALIBRATION COMPLETED!")
        print(f"   Runtime: {runtime_hours:.2f} hours")
        print(f"   Results saved to: calibration_results/{args.name}")
        
        if results and hasattr(results, 'get_best_parameters'):
            best_params = results.get_best_parameters()
            best_objective = results.get_best_objective_value()
            print(f"   Best objective value: {best_objective:.4f}")
            print(f"   Best parameters:")
            for param, value in best_params.items():
                print(f"     {param}: {value:.4f}")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Calibration interrupted by user")
    except Exception as e:
        print(f"\n❌ Calibration failed: {e}")
        logger.error(f"Calibration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
