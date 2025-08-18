#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Updated Sensitivity Analysis Runner

This script runs sensitivity analysis using ONLY the 16 parameters that are 
actually implemented in the fire simulation engine, based on our definitive 
line-by-line code analysis.

Author: Forest Fire Simulation Team
Date: 2025
Version: 2.0 - Updated with definitive parameter list
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.calibration.sensitivity_analysis import SensitivityAnalyzer, SensitivityResults
    from src.core.calibration.sensitivity_objective import create_sensitivity_objective
    from src.core.calibration.parameter_bounds import get_default_calibration_bounds
    from src.core.calibration.calibration_config import CalibrationConfig
    from src.config.config_tools import ModelConfig
    from src.utils.logging_utils import get_logger
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

logger = get_logger(__name__)


def create_updated_calibration_config() -> CalibrationConfig:
    """
    Create calibration config with ONLY the 16 implemented parameters.
    
    Based on our definitive line-by-line analysis of the fire simulation engine.
    """
    
    # DEFINITIVE LIST OF IMPLEMENTED PARAMETERS (from line-by-line analysis)
    implemented_parameters = [
        # Core Fire Mechanics
        'spread_probability',      # Line 906 - Base fire spread probability
        'fuel_consumption_rate',   # Line 824 - Fuel consumption rate
        'ignition_threshold',      # Line 1050 - Ignition probability threshold
        'min_fuel_value',          # Lines 825, 883, 1369 - Minimum fuel for burning
        'max_fuel_value',          # Lines 1014, 1377 - Maximum fuel normalization
        
        # Environmental Interactions
        'wind_influence_on_spread', # Line 990 - Wind effect on fire spread
        'slope_influence',         # Line 1114 - Terrain slope effect
        'reference_wind_speed',    # Line 989 - Reference wind speed for scaling
        'fuel_moisture_baseline',  # Line 1387 - Baseline fuel moisture
        
        # Wind Parameters (Main Fire Spread)
        'wind_speed',              # Lines 920-994 - Wind speed via get_wind_speed_at_cell()
        'wind_direction',          # Lines 926-994 - Wind direction via get_wind_direction_at_cell()
        
        # Ember Mechanics
        'ember_probability',       # Line 1250 - Ember generation probability
        'ember_distance',          # Lines 1284, 1401 - Ember travel distance
        'ember_ignition',          # Line 1374 - Ember ignition probability
        'ember_height_factor',     # Line 1254 - Height factor for ember generation
        'ember_wind_factor',       # Line 1301 - Wind influence on ember direction
        'ember_rise'               # Line 1314 - Ember height change range
    ]
    
    logger.info(f"✅ Using {len(implemented_parameters)} implemented parameters")
    logger.info("Parameters: " + ", ".join(implemented_parameters))
    
    # Create base model config for Tenerife
    base_config = ModelConfig(
        config_name="Tenerife_Sensitivity_Analysis",
        grid_size=(1000, 1000),  # 1km x 1km grid
        num_layers=10,
        model_resolution=5.0,  # 5m resolution
        max_steps=200,
        stop_when_fire_extinguished=True,
        store_full_states=False,
        use_terrain=True,
        use_preprocessed_terrain=True,
        memory_optimization_level=2
    )
    
    # Create calibration config with implemented parameters only
    calibration_config = CalibrationConfig(
        base_config=base_config,
        calibration_parameters=implemented_parameters,
        grid_search_points=9,  # 9 test points per parameter for Method 2
        parallel_execution=True,
        max_workers=8,  # Conservative for stability
        experiment_name="definitive_sensitivity_analysis",
        experiment_description="Sensitivity analysis using only implemented parameters"
    )
    
    return calibration_config


def validate_parameter_bounds(parameter_bounds: Dict[str, Any], 
                            implemented_parameters: List[str]) -> Dict[str, Any]:
    """
    Validate and filter parameter bounds to include only implemented parameters.
    """
    validated_bounds = {}
    missing_bounds = []
    
    for param_name in implemented_parameters:
        if param_name in parameter_bounds:
            validated_bounds[param_name] = parameter_bounds[param_name]
            logger.debug(f"✅ Found bounds for {param_name}")
        else:
            missing_bounds.append(param_name)
            logger.warning(f"⚠️  No bounds found for {param_name}")
    
    if missing_bounds:
        logger.warning(f"Missing bounds for {len(missing_bounds)} parameters: {missing_bounds}")
        logger.warning("These parameters will be skipped in sensitivity analysis")
    
    logger.info(f"✅ Validated bounds for {len(validated_bounds)} parameters")
    return validated_bounds


def run_sensitivity_analysis(calibration_config: CalibrationConfig,
                           parameter_bounds: Dict[str, Any],
                           output_dir: Path) -> SensitivityResults:
    """
    Run sensitivity analysis with the updated configuration.
    """
    
    logger.info("🚀 Starting updated sensitivity analysis")
    logger.info(f"📊 Parameters to analyze: {len(calibration_config.calibration_parameters)}")
    logger.info(f"🔧 Test points per parameter: {calibration_config.grid_search_points}")
    
    # Calculate total evaluations
    total_evaluations = len(calibration_config.calibration_parameters) * calibration_config.grid_search_points
    logger.info(f"📈 Total evaluations: {total_evaluations}")
    
    # Create objective function
    objective_function = create_sensitivity_objective()
    logger.info("✅ Created sensitivity objective function")
    
    # Create sensitivity analyzer
    analyzer = SensitivityAnalyzer(
        calibration_config=calibration_config,
        parameter_bounds=parameter_bounds,
        objective_function=objective_function,
        perturbation_method="range_based",
        parallel_execution=calibration_config.parallel_execution,
        max_workers=calibration_config.max_workers
    )
    
    # Run sensitivity analysis
    start_time = time.time()
    results = analyzer.run_sensitivity_analysis(
        target_data=None,  # Not needed for sensitivity analysis
        progress_callback=None
    )
    total_time = time.time() - start_time
    
    # Log results
    logger.info(f"✅ Sensitivity analysis completed in {total_time:.2f} seconds")
    logger.info(f"🚀 Speed: {total_evaluations/(total_time/3600):.1f} evaluations/hour")
    
    return results


def save_results(results: SensitivityResults, output_dir: Path):
    """
    Save sensitivity analysis results to files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save detailed results
    results_file = output_dir / "sensitivity_analysis_results.json"
    results.save_results(results_file)
    logger.info(f"💾 Saved detailed results to {results_file}")
    
    # Save summary
    summary_file = output_dir / "sensitivity_summary.txt"
    summary = results.get_sensitivity_summary()
    
    with open(summary_file, 'w') as f:
        f.write("DEFINITIVE SENSITIVITY ANALYSIS RESULTS\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Analysis completed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total parameters analyzed: {summary['total_parameters']}\n")
        f.write(f"Valid analyses: {summary['valid_parameters']}\n")
        f.write(f"Total evaluations: {summary['total_evaluations']}\n")
        f.write(f"Total time: {summary['total_time']:.2f} seconds\n")
        f.write(f"Baseline objective: {summary['baseline_objective']:.4f}\n\n")
        
        f.write("PARAMETER RANKINGS (by sensitivity)\n")
        f.write("-" * 40 + "\n")
        for i, (param_name, sensitivity) in enumerate(results.parameter_rankings):
            f.write(f"{i+1:2d}. {param_name:25s}: {sensitivity:.4f}\n")
        
        f.write(f"\nMost sensitive parameter: {summary.get('most_sensitive', ('None', 0))[0]}\n")
        f.write(f"Least sensitive parameter: {summary.get('least_sensitive', ('None', 0))[0]}\n")
        f.write(f"Mean sensitivity: {summary.get('mean_sensitivity', 0):.4f}\n")
        f.write(f"Sensitivity range: {summary.get('sensitivity_range', 0):.4f}\n")
    
    logger.info(f"💾 Saved summary to {summary_file}")
    
    # Save top 5 parameters for calibration
    top5_file = output_dir / "top5_parameters_for_calibration.json"
    top5_params = results.get_most_sensitive_parameters(5)
    
    top5_data = {
        "top5_parameters": [param_name for param_name, _ in top5_params],
        "sensitivity_scores": [score for _, score in top5_params],
        "analysis_metadata": {
            "total_parameters": len(results.parameter_rankings),
            "analysis_date": time.strftime('%Y-%m-%d %H:%M:%S'),
            "method": "Method 2: Standardized Range-Based Sensitivity Analysis"
        }
    }
    
    with open(top5_file, 'w') as f:
        json.dump(top5_data, f, indent=2)
    
    logger.info(f"💾 Saved top 5 parameters to {top5_file}")


def main():
    """
    Main function to run updated sensitivity analysis.
    """
    logger.info("🎯 Starting Definitive Sensitivity Analysis")
    logger.info("=" * 60)
    
    # Create output directory
    output_dir = Path("sensitivity_analysis_results") / f"definitive_analysis_{time.strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Step 1: Create updated calibration config
        logger.info("📋 Step 1: Creating updated calibration configuration")
        calibration_config = create_updated_calibration_config()
        
        # Step 2: Get and validate parameter bounds
        logger.info("📋 Step 2: Validating parameter bounds")
        all_bounds = get_default_calibration_bounds()
        validated_bounds = validate_parameter_bounds(all_bounds, calibration_config.calibration_parameters)
        
        if len(validated_bounds) < len(calibration_config.calibration_parameters):
            logger.warning("⚠️  Some parameters missing bounds - analysis will be incomplete")
        
        # Step 3: Run sensitivity analysis
        logger.info("📋 Step 3: Running sensitivity analysis")
        results = run_sensitivity_analysis(calibration_config, validated_bounds, output_dir)
        
        # Step 4: Save results
        logger.info("📋 Step 4: Saving results")
        save_results(results, output_dir)
        
        # Step 5: Display summary
        logger.info("📋 Step 5: Analysis Summary")
        logger.info("=" * 60)
        
        summary = results.get_sensitivity_summary()
        logger.info(f"✅ Analysis completed successfully!")
        logger.info(f"📊 Parameters analyzed: {summary['total_parameters']}")
        logger.info(f"⏱️  Total time: {summary['total_time']:.2f} seconds")
        
        logger.info("\n🏆 TOP 5 MOST SENSITIVE PARAMETERS:")
        for i, (param_name, sensitivity) in enumerate(results.get_most_sensitive_parameters(5)):
            logger.info(f"  {i+1}. {param_name:25s}: {sensitivity:.4f}")
        
        logger.info(f"\n💾 Results saved to: {output_dir}")
        logger.info("🎯 Use these top 5 parameters for your calibration!")
        
    except Exception as e:
        logger.error(f"❌ Sensitivity analysis failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
