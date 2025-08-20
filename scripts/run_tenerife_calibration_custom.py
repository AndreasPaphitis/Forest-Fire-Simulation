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
    python scripts/run_tenerife_calibration_custom.py

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
    'memory_limit_gb': 24.0,
    'max_workers': 48,
    'estimated_hours': 3.5
}

def estimate_custom_calibration_time(config: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate calibration time for custom configuration."""
    
    # Calculate total combinations: 3⁴ = 81
    total_combinations = config['grid_search_points'] ** len(config['parameters'])
    
    # Optimized time per simulation with 10m resolution and 100 steps
    # 10m resolution = 4x fewer cells, 100 steps = 2.5x fewer steps
    base_time_per_sim_seconds = 60.0  # ~1 minute per simulation
    
    # Parallel efficiency factor
    parallel_efficiency = 0.9
    
    # Calculate times
    total_time_seconds = total_combinations * base_time_per_sim_seconds
    parallel_time_seconds = total_time_seconds / (config['max_workers'] * parallel_efficiency)
    
    # Convert to hours
    parallel_time_hours = parallel_time_seconds / 3600
    
    return {
        'total_combinations': total_combinations,
        'base_time_per_sim_seconds': base_time_per_sim_seconds,
        'total_time_seconds': total_time_seconds,
        'parallel_time_seconds': parallel_time_seconds,
        'parallel_time_hours': parallel_time_hours,
        'peak_memory_gb': config['memory_limit_gb']
    }

class CustomTenerifeCalibrator(TenerifeFirePerimeterCalibrator):
    """
    Custom version with specific optimizations for 10m resolution and 100 timesteps.
    """
    
    def __init__(self, **kwargs):
        # Override default parameters with custom settings
        kwargs.update({
            'memory_gb': CUSTOM_CONFIG['memory_limit_gb'],
            'workers': CUSTOM_CONFIG['max_workers'],
            'grid_search_points': CUSTOM_CONFIG['grid_search_points'],
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
        calib_config.memory_limit_gb = self.custom_config['memory_limit_gb']
        calib_config.max_workers = self.custom_config['max_workers']
        
        return calib_config

def main():
    """Main execution function for custom calibration."""
    
    parser = argparse.ArgumentParser(description="Custom Tenerife fire perimeter calibration")
    
    # EMSR data directory
    parser.add_argument('--emsr-dir', type=str, 
                       default="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/EMSR/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1",
                       help='EMSR data directory')
    
    # Training/test days
    parser.add_argument('--training-days', type=int, nargs='+', default=[1, 2],
                       help='Training days (default: 1 2)')
    parser.add_argument('--test-days', type=int, nargs='+', default=[3, 4],
                       help='Test days (default: 3 4)')
    
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
    print(f"✅ Parameters: {len(CUSTOM_CONFIG['parameters'])} ({', '.join(CUSTOM_CONFIG['parameters'])})")
    print(f"✅ Grid search: {CUSTOM_CONFIG['grid_search_points']} points per parameter")
    print(f"✅ Workers: {CUSTOM_CONFIG['max_workers']}")
    print(f"✅ Memory: {CUSTOM_CONFIG['memory_limit_gb']}GB")
    print(f"✅ Target: {CUSTOM_CONFIG['estimated_hours']} hours")
    print()
    
    try:
        # Step 1: Emergency cleanup
        print(f"🧹 EMERGENCY CLEANUP")
        print("=" * 30)
        
        try:
            emergency_cleanup_shared_memory()
            print("✅ Shared memory cleanup completed")
        except Exception as e:
            logger.warning(f"Shared memory cleanup failed: {e}")
        
        # Step 2: Memory protection setup
        print(f"🛡️  MEMORY PROTECTION SETUP")
        print("=" * 30)
        
        memory_thresholds = ProductionMemoryThresholds(
            process_warning_gb=CUSTOM_CONFIG['memory_limit_gb'] * 0.6,
            process_critical_gb=CUSTOM_CONFIG['memory_limit_gb'] * 0.8,
            process_emergency_gb=CUSTOM_CONFIG['memory_limit_gb'] * 0.9,
            system_warning_percent=70.0,
            system_critical_percent=85.0,
            system_emergency_percent=95.0
        )
        
        setup_production_memory_protection(memory_thresholds)
        print("✅ Memory protection configured")
        
        # Step 3: Create custom calibrator
        print(f"🎯 CREATING CUSTOM CALIBRATOR")
        print("=" * 30)
        
        calibrator = CustomTenerifeCalibrator()
        
        # Step 4: Create EMSR target data
        print(f"🔥 CREATING EMSR TARGET DATA")
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
        
        # Step 5: Set up training/validation split
        print(f"📊 SETTING UP TRAINING/VALIDATION SPLIT")
        print("=" * 50)
        
        discovery = FirePerimeterDiscovery(args.emsr_dir)
        fire_dataset = discovery.discover_fire_perimeters()
        
        if not fire_dataset.fire_perimeters:
            raise ValueError(f"No fire perimeters found in {args.emsr_dir}")
        
        print(f"📁 Found {len(fire_dataset.fire_perimeters)} fire perimeters")
        
        # Set up training/validation split
        training_data, validation_data = calibrator.setup_training_test_split(
            fire_dataset,
            training_days=args.training_days,
            test_days=args.test_days
        )
        
        print(f"✅ Training/Validation split complete:")
        print(f"   🎯 Training: {len(training_data)} fire perimeters")
        print(f"   🧪 Validation: {len(validation_data)} fire perimeters")
        
        # Step 6: Create calibration configuration
        calib_config = calibrator.create_calibration_config(
            training_data=training_data,
            top_5_parameters=CUSTOM_CONFIG['parameters']
        )
        
        # Step 7: Final confirmation and execution
        print(f"🚀 READY TO EXECUTE CUSTOM CALIBRATION")
        print("=" * 50)
        
        estimates = estimate_custom_calibration_time(CUSTOM_CONFIG)
        
        print(f"📊 Performance estimates:")
        print(f"   Total combinations: {estimates['total_combinations']:,} (3⁴)")
        print(f"   Time per simulation: {estimates['base_time_per_sim_seconds']:.1f} seconds")
        print(f"   Parallel time: {estimates['parallel_time_hours']:.1f} hours")
        print(f"   Peak memory: {estimates['peak_memory_gb']:.1f} GB")
        print(f"   Results directory: {calibrator.results_dir}")
        print()
        print(f"🎯 Custom Configuration Summary:")
        print(f"   Resolution: {CUSTOM_CONFIG['model_resolution']}m (4x fewer cells)")
        print(f"   Timesteps: {CUSTOM_CONFIG['max_steps']} (2.5x fewer steps)")
        print(f"   Parameters: {len(CUSTOM_CONFIG['parameters'])} top parameters")
        print(f"   Grid search: {CUSTOM_CONFIG['grid_search_points']} points each")
        
        if args.dry_run:
            logger.info(f"✅ DRY RUN COMPLETE - Configuration validated")
            logger.info(f"📊 Runtime: {estimates['parallel_time_hours']:.1f}h, Memory: {estimates['peak_memory_gb']:.1f}GB")
            logger.info(f"📁 Results: {calibrator.results_dir}")
            logger.info("To run actual calibration, remove --dry-run flag")
            return
        
        # Final user confirmation
        print(f"⚠️  This will take ~{estimates['parallel_time_hours']:.1f} hours")
        print(f"   Make sure you're on a stable node")
        
        response = input(f"\nContinue? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print(f"❌ Cancelled by user")
            return
        
        # Step 8: Execute custom calibration
        print(f"🚀 EXECUTING CUSTOM CALIBRATION")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run calibration
        results = calibrator.run_calibration(
            calibration_config=calib_config,
            test_data=validation_data
        )
        
        total_time = time.time() - start_time
        
        # Step 9: Results summary
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
