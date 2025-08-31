#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixed Sensitivity Analysis Runner - Uses Same Grid Size as Calibration

This script performs sensitivity analysis using the SAME grid size and approach
as the existing calibration code (609×609 grid) to ensure consistency.

Author: Forest Fire Simulation Team
Date: 2025
"""

import os
import sys
import time
import argparse
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.calibration import (
        CalibrationConfig, CalibrationMethod, CalibrationObjective,
        SensitivityAnalyzer,
        get_default_calibration_bounds,
        create_sensitivity_progress_callback,
        save_calibration_results,
        create_calibration_report,
        validate_calibration_config,
    )
    from src.config.config_tools import ModelConfig
    from src.utils.logging_utils import get_logger
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the Forest-Fire-Simulation directory")
    sys.exit(1)

logging.getLogger("src.core.fire_simulation_engine").setLevel(logging.WARNING)
logger = get_logger(__name__, level=logging.WARNING)


class FixedSensitivityRunner:
    """
    Fixed sensitivity analysis runner that uses the SAME grid size as calibration (609×609).
    """
    
    def __init__(self, 
                 output_dir: Optional[str] = None,
                 experiment_name: Optional[str] = None,
                 workers: int = 8,
                 memory_level: int = 2):
        """
        Initialize the fixed sensitivity analysis runner.
        
        Args:
            output_dir: Output directory for results
            experiment_name: Name for this experiment
            workers: Number of parallel workers
            memory_level: Memory optimization level (1-3)
        """
        self.output_dir = Path(output_dir) if output_dir else Path("sensitivity_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.experiment_name = experiment_name or f"sensitivity_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.workers = workers
        self.memory_level = memory_level
        
        print(f"🔥 FIXED SENSITIVITY ANALYSIS RUNNER")
        print(f"=" * 50)
        print(f"Grid size: 609×609 (same as calibration)")
        print(f"Workers: {workers}")
        print(f"Memory level: {memory_level}")
        print(f"Output: {self.output_dir}")
        print()
    
    def create_fixed_config(self) -> CalibrationConfig:
        """Create configuration using the SAME settings as calibration."""
        
        # Use the EXACT same base config as calibration
        base_config = ModelConfig(
            grid_size=(609, 609),  # SAME as calibration
            num_layers=20,         # SAME as calibration
            max_steps=20,          # REDUCED from 25 to 20 for faster analysis
            model_resolution=20.0, # SAME as calibration
            simulation_type="memory_optimized",
            memory_optimization_level=self.memory_level,
            use_disk_storage=True,
            use_differential_history=True,
            use_sparse_storage=True,
            
            # PREPROCESSED TERRAIN - SAME as calibration
            use_preprocessed_terrain=True,
            
            # ENABLE STEP LOGGING for sensitivity analysis
            engine_logging_interval=10,  # Log every 10 steps instead of 100
            
            # Fire parameters
            spread_probability=0.6,
            fuel_consumption_rate=0.8,
            ignition_threshold=0.4,
            initial_fuel_load=8.0,
            
            # Terrain and wind effects
            slope_influence=0.4,
            wind_influence_on_spread=0.3,
            terrain_effect_strength=0.7,
            
            # Wind settings
            wind_speed=5.0,
            wind_direction=45.0,
            
            # Random seed for reproducibility
            random_seed=42
        )
        
        # Create calibration config
        config = CalibrationConfig(
            experiment_name=self.experiment_name,
            method=CalibrationMethod.SENSITIVITY_ANALYSIS,
            objective=CalibrationObjective.SPATIAL_SIMILARITY,
            base_config=base_config,
            preprocessed_terrain_dir="preprocessed_terrain",
            
            # All calibration parameters
            calibration_parameters=self._get_all_parameters(),
            
            # Results configuration
            results_dir=str(self.output_dir),
            save_intermediate_results=True,
            generate_plots=True,
            verbose=True,
            
            # Performance settings - CRITICAL: Set max_workers here
            parallel_execution=True,
            max_workers=self.workers,  # This should be set in the constructor
            memory_limit_gb=8.0,  # Conservative for 609×609 grid
            simulation_timeout_minutes=30.0,
            
            # Grid search settings
            grid_search_points=5,
            
            # Spatial similarity weights
            jaccard_weight=0.4,
            dice_weight=0.6
        )
        
        # CRITICAL FIX: Add synthetic calibration targets (same as calibration script)
        from src.core.calibration.calibration_config import CalibrationTarget
        import numpy as np
        
        # Create synthetic target data that matches simulation scale
        synthetic_target = np.zeros((609, 609))
        # Create a small fire area around ignition point (395, 377) - same as calibration
        for i in range(390, 400):
            for j in range(370, 380):
                if 0 <= i < 609 and 0 <= j < 609:
                    synthetic_target[i, j] = 1
        
        # Save synthetic target to file
        np.save("synthetic_target.npy", synthetic_target)
        
        # Create calibration target from synthetic data
        target = CalibrationTarget(
            fire_perimeter_path="synthetic_target.npy",  # Use synthetic data
            weight=1.0
        )
        config.calibration_targets = [target]
        
        print(f"✅ Created synthetic calibration target: {np.sum(synthetic_target > 0)} burned cells")
        print(f"✅ Target file: synthetic_target.npy")
        print()
        
        return config
    
    def _get_all_parameters(self) -> List[str]:
        """Get all calibration parameters (same as sensitivity analysis)."""
        return [
            'spread_probability',
            'fuel_consumption_rate',
            'ignition_threshold',
            'min_fuel_value',
            'max_fuel_value',
            'slope_influence',
            'wind_influence_on_spread',
            'ember_probability',
            'ember_ignition',
            'ember_distance',
            'wind_speed',
            'wind_direction',
            'ember_height_factor',
            'reference_wind_speed',
            'fuel_moisture_baseline'
        ]
    
    def create_enhanced_progress_callback(self):
        """Create an enhanced progress callback with worker tracking."""
        start_time = time.time()
        completed_count = 0
        total_count = 135  # 15 parameters × 9 perturbations
        
        def enhanced_callback(completed: int, total: int, result):
            nonlocal completed_count, start_time
            completed_count += 1
            
            # Calculate timing
            elapsed = time.time() - start_time
            avg_time_per_sim = elapsed / completed_count if completed_count > 0 else 0
            remaining_sims = total - completed_count
            eta_minutes = (remaining_sims * avg_time_per_sim) / 60
            
            # Calculate progress percentage
            progress_pct = (completed_count / total) * 100
            
            # Get worker info (approximate)
            active_workers = min(self.workers, remaining_sims)
            
            # Handle result format: (parameter_name, test_value, objective_value, is_valid, error_message)
            if isinstance(result, tuple) and len(result) == 5:
                param_name, test_value, objective_value, is_valid, error_msg = result
                status = "✅ SUCCESS" if is_valid else "❌ FAILED"
                sensitivity = objective_value if is_valid else 0.0
            else:
                # Handle SensitivityResult object format
                param_name = getattr(result, 'parameter_name', 'Unknown')
                is_valid = getattr(result, 'is_valid', False)
                sensitivity = getattr(result, 'sensitivity_index', 0.0)
                status = "✅ SUCCESS" if is_valid else "❌ FAILED"
            
            # Enhanced output
            print(f"\n🔄 PROGRESS UPDATE [{completed_count:3d}/{total}] ({progress_pct:5.1f}%)")
            print(f"   📊 Parameter: {param_name}")
            print(f"   🎯 Status: {status}")
            print(f"   📈 Objective Value: {sensitivity:.6f}")
            print(f"   ⏱️  Elapsed: {elapsed/60:.1f}min | ETA: {eta_minutes:.1f}min")
            print(f"   🔧 Active Workers: ~{active_workers}")
            print(f"   📊 Avg Time/Sim: {avg_time_per_sim:.1f}s")
            print("-" * 60)
        
        return enhanced_callback
    
    def print_sensitivity_measurement_info(self):
        """Print detailed information about how sensitivity is measured."""
        print("\n📊 SENSITIVITY MEASUREMENT METHODOLOGY")
        print("=" * 50)
        print("🎯 Objective Function Components:")
        print("   • Area Weight (30%): Total burned area")
        print("   • Spread Rate Weight (30%): Fire spread speed")
        print("   • Persistence Weight (20%): How long fire burns")
        print("   • Dispersion Weight (20%): Spatial fire distribution")
        print()
        print("🔬 Sensitivity Index Calculation:")
        print("   Formula: Sensitivity = (Output_Range / Param_Range) × (Param_Range / Middle_Output)")
        print("   • Output_Range: Max - Min objective values across parameter perturbations")
        print("   • Param_Range: Max - Min parameter values tested")
        print("   • Middle_Output: Median objective value for normalization")
        print()
        print("📈 Interpretation:")
        print("   • Higher values = More sensitive parameter")
        print("   • Lower values = Less sensitive parameter")
        print("   • Focus calibration on top-ranked parameters")
        print()
        print("🔧 Parameter Testing Strategy:")
        print("   • Each parameter tested at 9 values: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]")
        print("   • Range-based perturbation (relative to parameter bounds)")
        print("   • 25 simulation steps per test")
        print("   • 609×609×20 grid (same as calibration)")
        print()
    
    def run_sensitivity_analysis(self):
        """Run the sensitivity analysis with fixed configuration."""
        
        print("🚀 STARTING FIXED SENSITIVITY ANALYSIS")
        print("=" * 50)
        
        # Print sensitivity measurement info
        self.print_sensitivity_measurement_info()
        
        # Step 1: Create configuration
        print("📋 Step 1: Creating fixed configuration...")
        self.calibration_config = self.create_fixed_config()
        
        # Step 2: Validate configuration
        print("🔍 Step 2: Validating configuration...")
        is_valid, validation_errors = validate_calibration_config(self.calibration_config)
        if not is_valid:
            print("❌ Configuration validation failed:")
            for error in validation_errors:
                print(f"   - {error}")
            return None
        
        print("✅ Configuration validated successfully")
        
        # Step 3: Get parameter bounds and objective function
        print("⚙️ Step 3: Setting up parameter bounds and objective...")
        parameter_bounds = get_default_calibration_bounds()

        # FIX: Use the CORRECT objective function for sensitivity analysis
        from src.core.calibration.sensitivity_objective import create_sensitivity_objective
        objective_function = create_sensitivity_objective()  # ✅ Returns SensitivityAnalysisObjective
        
        # Step 4: Create sensitivity analyzer
        print("🔬 Step 4: Creating sensitivity analyzer...")
        analyzer = SensitivityAnalyzer(
            calibration_config=self.calibration_config,
            parameter_bounds=parameter_bounds,
            objective_function=objective_function,
            perturbation_method="range_based",
            perturbation_values=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],  # 9 points
            parallel_execution=True,
            max_workers=self.workers
        )
        
        # Debug: Print analyzer configuration
        print(f"🔧 SensitivityAnalyzer Configuration:")
        print(f"   Parallel execution: {analyzer.parallel_execution}")
        print(f"   Max workers: {analyzer.max_workers}")
        print(f"   Total evaluations: {len(analyzer._generate_all_evaluations())}")
        print()
        
        # Step 5: Run sensitivity analysis
        print("🎯 Step 5: Running sensitivity analysis...")
        print(f"   Total evaluations: {len(self.calibration_config.calibration_parameters)} × 9 = 135")
        print(f"   Grid size: 609×609×20")
        print(f"   Workers: {self.workers}")
        print(f"   Estimated time: ~17-34 minutes")
        print()
        
        start_time = time.time()
        
        # Use enhanced progress callback
        progress_callback = self.create_enhanced_progress_callback()
        
        print("🔥 STARTING SIMULATIONS - WATCH FOR WORKER UPDATES BELOW")
        print("=" * 70)
        
        # Create target data for spatial similarity objective (same as calibration)
        target_data = {
            'fire_perimeter': np.load("synthetic_target.npy")
        }
        
        results = analyzer.run_sensitivity_analysis(
            target_data=target_data,  # Use synthetic target data
            progress_callback=progress_callback
        )
        
        end_time = time.time()
        runtime = end_time - start_time
        
        print(f"\n✅ Sensitivity analysis completed in {runtime/60:.1f} minutes")
        
        return results
    
    def analyze_and_save_results(self, results):
        """Analyze and save the results."""
        
        print("\n📊 ANALYZING RESULTS")
        print("=" * 30)
        
        # Get sensitivity summary
        sensitivity_summary = results.get_sensitivity_summary()
        parameter_rankings = results.parameter_rankings
        
        # Check if we have valid results
        if sensitivity_summary['most_sensitive'] is None or sensitivity_summary['least_sensitive'] is None:
            print("❌ NO VALID SENSITIVITY RESULTS - All evaluations failed!")
            print("🔍 DIAGNOSING ISSUE:")
            print(f"   - Total evaluations: {len(results.evaluations)}")
            print(f"   - Valid evaluations: {len([e for e in results.evaluations if e.is_valid])}")
            print(f"   - Failed evaluations: {len([e for e in results.evaluations if not e.is_valid])}")
            print()
            
            # Show some failed evaluation details
            failed_evaluations = [e for e in results.evaluations if not e.is_valid][:5]
            print("📋 SAMPLE FAILED EVALUATIONS:")
            for i, eval in enumerate(failed_evaluations, 1):
                print(f"   {i}. {eval.parameter_name}={eval.test_value}: {eval.error_message}")
            print()
            
            print("💡 POSSIBLE CAUSES:")
            print("   1. Forest model state access issues")
            print("   2. Parameter bounds too extreme")
            print("   3. Simulation crashes")
            print("   4. Memory issues")
            print()
            
            return None
        
        print(f"📈 Most sensitive parameter: {sensitivity_summary['most_sensitive'][0]} ({sensitivity_summary['most_sensitive'][1]:.2f})")
        print(f"📉 Least sensitive parameter: {sensitivity_summary['least_sensitive'][0]} ({sensitivity_summary['least_sensitive'][1]:.2f})")
        print(f"📊 Mean sensitivity: {sensitivity_summary['mean_sensitivity']:.2f}")
        print()
        
        print("🏆 TOP 5 MOST SENSITIVE PARAMETERS:")
        for i, (param, sensitivity) in enumerate(parameter_rankings[:5], 1):
            print(f"   {i}. {param}: {sensitivity:.2f}")
        print()
        
        # Save results
        print("💾 Saving results...")
        saved_files = save_calibration_results(
            results=results,
            sensitivity_summary=sensitivity_summary,
            parameter_rankings=parameter_rankings,
            output_dir=self.output_dir,
            experiment_name=self.experiment_name
        )
        
        print("✅ Results saved successfully!")
        print(f"📁 Results directory: {self.output_dir}")
        print(f"📋 Summary file: {saved_files.get('summary_file', 'N/A')}")
        print(f"📊 Detailed results: {saved_files.get('detailed_results_file', 'N/A')}")
        
        return saved_files


def main():
    parser = argparse.ArgumentParser(description="Fixed Sensitivity Analysis Runner")
    parser.add_argument(
        '--output',
        type=str,
        default="sensitivity_results",
        help='Output directory for results'
    )
    parser.add_argument(
        '--name',
        type=str,
        default=None,
        help='Experiment name'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=8,
        help='Number of parallel workers'
    )
    parser.add_argument(
        '--memory-level',
        type=int,
        default=2,
        choices=[1, 2, 3],
        help='Memory optimization level (1=conservative, 2=balanced, 3=aggressive)'
    )
    
    args = parser.parse_args()
    
    # Create and run the analysis
    runner = FixedSensitivityRunner(
        output_dir=args.output,
        experiment_name=args.name,
        workers=args.workers,
        memory_level=args.memory_level
    )
    
    # Run sensitivity analysis
    results = runner.run_sensitivity_analysis()
    
    if results:
        # Analyze and save results
        runner.analyze_and_save_results(results)
        
        print("\n🎉 FIXED SENSITIVITY ANALYSIS COMPLETED SUCCESSFULLY!")
        print("🎯 Next step: Use the top 5 parameters for calibration")
    else:
        print("\n❌ Sensitivity analysis failed!")


if __name__ == "__main__":
    main()

