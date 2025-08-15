#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example Calibration Script

This script demonstrates how to use the forest fire simulation calibration framework.
It provides complete examples for different calibration methods and shows best practices
for setting up and running calibration experiments.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import time
import numpy as np
from pathlib import Path

# Import calibration framework components
try:
    from src.core.calibration import (
        CalibrationConfig, CalibrationMethod, CalibrationObjective,
        get_default_calibration_bounds, create_calibration_parameters,
        create_default_spatial_objective,
        GridSearchCalibrator, create_progress_callback,
        SensitivityAnalyzer, create_sensitivity_progress_callback,
        create_synthetic_target_data, save_calibration_results,
        create_calibration_report, validate_calibration_config
    )
    from src.config.config_tools import ModelConfig
    from src.utils.logging_utils import get_logger
except ImportError:
    print("Error: Could not import calibration framework components.")
    print("Make sure you're running this from the project root directory.")
    exit(1)

logger = get_logger(__name__)


def example_basic_calibration():
    """
    Example 1: Basic grid search calibration with spatial similarity objective.
    This is the simplest way to get started with calibration.
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Grid Search Calibration")
    print("="*60)
    
    # Step 1: Create base simulation configuration
    base_config = ModelConfig(
        grid_size=(50, 50),
        num_layers=5,
        max_steps=50,
        random_seed=42
    )
    
    # Step 2: Create calibration configuration
    calib_config = CalibrationConfig(
        experiment_name="basic_grid_search",
        method=CalibrationMethod.GRID_SEARCH,
        objective=CalibrationObjective.SPATIAL_SIMILARITY,
        base_config=base_config,
        calibration_parameters=[
            'spread_probability',
            'fuel_consumption_rate',
            'ignition_threshold'
        ],
        grid_search_points=3,  # 3 points per parameter = 3^3 = 27 combinations
        max_iterations=27,
        results_dir="calibration_results/basic_example"
    )
    
    # Step 3: Validate configuration
    is_valid, errors = validate_calibration_config(calib_config)
    if not is_valid:
        print("Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        return
    
    print("Configuration validated successfully!")
    print(calib_config.summary())
    
    # Step 4: Get parameter bounds
    parameter_bounds = get_default_calibration_bounds()
    
    # Step 5: Create objective function
    objective_function = create_default_spatial_objective()
    
    # Step 6: Create synthetic target data (replace with real data in practice)
    target_data = create_synthetic_target_data((50, 50), "circular")
    print(f"Created synthetic target with {target_data['burned_cells']} burned cells")
    
    # Step 7: Initialize calibrator
    calibrator = GridSearchCalibrator(
        calibration_config=calib_config,
        parameter_bounds=parameter_bounds,
        objective_function=objective_function,
        parallel_execution=True,
        max_workers=2  # Reduce for example
    )
    
    # Step 8: Show estimation
    estimation = calibrator.get_estimation_info()
    print(f"\nCalibration estimation:")
    print(f"  Total combinations: {estimation['total_combinations']}")
    print(f"  Estimated time: {estimation['estimated_time_seconds']:.1f} seconds")
    print(f"  Parallel execution: {estimation['parallel_execution']}")
    
    # Step 9: Run calibration
    print("\nStarting calibration...")
    progress_callback = create_progress_callback(verbose=True)
    
    start_time = time.time()
    results = calibrator.run_calibration(
        target_data=target_data,
        progress_callback=progress_callback
    )
    runtime = time.time() - start_time
    
    # Step 10: Display results
    print(f"\nCalibration completed in {runtime:.2f} seconds")
    print(f"Best objective value: {results.get_best_objective_value():.4f}")
    print(f"Best parameters:")
    for param, value in results.get_best_parameters().items():
        print(f"  {param}: {value:.4f}")
    
    # Step 11: Save results
    save_calibration_results(results, calib_config.results_dir, "basic_grid_search")
    
    # Step 12: Generate report
    report_path = create_calibration_report(results, calib_config, calib_config.results_dir)
    print(f"Generated report: {report_path}")
    
    return results


def example_sensitivity_analysis():
    """
    Example 2: One-at-a-time sensitivity analysis to identify important parameters.
    This helps you understand which parameters have the most impact.
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Sensitivity Analysis")
    print("="*60)
    
    # Step 1: Create configuration for sensitivity analysis
    base_config = ModelConfig(
        grid_size=(40, 40),
        num_layers=3,
        max_steps=30,
        random_seed=123
    )
    
    calib_config = CalibrationConfig(
        experiment_name="sensitivity_analysis",
        method=CalibrationMethod.SENSITIVITY_ANALYSIS,
        objective=CalibrationObjective.SPATIAL_SIMILARITY,
        base_config=base_config,
        calibration_parameters=[
            'spread_probability',
            'fuel_consumption_rate', 
            'ignition_threshold',
            'min_fuel_value',
            'slope_influence',
            'wind_influence_on_spread'
        ],
        results_dir="calibration_results/sensitivity_example"
    )
    
    print(calib_config.summary())
    
    # Step 2: Get parameter bounds and create objective function
    parameter_bounds = get_default_calibration_bounds()
    objective_function = create_default_spatial_objective()
    
    # Step 3: Create target data
    target_data = create_synthetic_target_data((40, 40), "elliptical")
    
    # Step 4: Initialize sensitivity analyzer
    analyzer = SensitivityAnalyzer(
        calibration_config=calib_config,
        parameter_bounds=parameter_bounds,
        objective_function=objective_function,
        perturbation_method="percentage",
        perturbation_values=[-0.3, -0.15, 0.15, 0.3]  # ±30%, ±15%
    )
    
    # Step 5: Run sensitivity analysis
    print("\nStarting sensitivity analysis...")
    progress_callback = create_sensitivity_progress_callback(verbose=True)
    
    start_time = time.time()
    sensitivity_results = analyzer.run_sensitivity_analysis(
        target_data=target_data,
        progress_callback=progress_callback
    )
    runtime = time.time() - start_time
    
    # Step 6: Display results
    print(f"\nSensitivity analysis completed in {runtime:.2f} seconds")
    
    summary = sensitivity_results.get_sensitivity_summary()
    print(f"Baseline objective: {summary['baseline_objective']:.4f}")
    
    print("\nParameter sensitivity ranking:")
    for i, (param_name, sensitivity) in enumerate(sensitivity_results.get_most_sensitive_parameters()):
        print(f"  {i+1}. {param_name:25s}: {sensitivity:.4f}")
    
    # Step 7: Save results
    sensitivity_results.save_results(calib_config.results_dir / "sensitivity_results.json")
    
    return sensitivity_results


def example_fire_behavior_calibration():
    """
    Example 3: Fire behavior calibration focusing on burned area and spread rate.
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Fire Behavior Calibration")
    print("="*60)
    
    # Step 1: Create configuration with fire behavior objective
    base_config = ModelConfig(
        grid_size=(60, 60),
        num_layers=4,
        max_steps=40,
        random_seed=456
    )
    
    calib_config = CalibrationConfig(
        experiment_name="fire_behavior_calibration",
        method=CalibrationMethod.GRID_SEARCH,
        objective=CalibrationObjective.FIRE_BEHAVIOR,
        base_config=base_config,
        calibration_parameters=[
            'spread_probability',
            'fuel_consumption_rate',
            'ignition_threshold',
            'slope_influence'
        ],
        grid_search_points=2,  # 2^4 = 16 combinations for quick demo
        results_dir="calibration_results/fire_behavior_example"
    )
    
    print(calib_config.summary())
    
    # Step 2: Create fire behavior objective function
    from src.core.calibration.objective_functions import FireBehaviorObjective
    
    objective_function = FireBehaviorObjective(
        target_burned_area=250,  # Target 250 burned cells
        target_spread_rate=6.25  # Target 6.25 cells per step
    )
    
    # Step 3: Create target data with target behavior metrics
    target_data = create_synthetic_target_data((60, 60), "random")
    
    # Add target fire behavior metrics
    target_data.update({
        'target_burned_area': 250,
        'target_spread_rate': 6.25  # cells per step
    })
    
    # Step 4: Get parameter bounds
    parameter_bounds = get_default_calibration_bounds()
    
    # Step 5: Initialize and run calibrator
    calibrator = GridSearchCalibrator(
        calibration_config=calib_config,
        parameter_bounds=parameter_bounds,
        objective_function=objective_function,
        parallel_execution=True,
        max_workers=2
    )
    
    print("\nStarting fire behavior calibration...")
    progress_callback = create_progress_callback(verbose=True)
    
    start_time = time.time()
    results = calibrator.run_calibration(
        target_data=target_data,
        progress_callback=progress_callback
    )
    runtime = time.time() - start_time
    
    # Step 6: Display results
    print(f"\nFire behavior calibration completed in {runtime:.2f} seconds")
    print(f"Best objective value: {results.get_best_objective_value():.4f}")
    
    if results.best_result:
        print("\nBest configuration:")
        for param, value in results.get_best_parameters().items():
            print(f"  {param}: {value:.4f}")
        
        print("\nObjective components:")
        components = results.best_result.objective_components
        for comp_name, comp_value in components.items():
            print(f"  {comp_name}: {comp_value:.4f}")
    
    # Step 7: Save results and generate report
    save_calibration_results(results, calib_config.results_dir, "fire_behavior")
    report_path = create_calibration_report(results, calib_config, calib_config.results_dir)
    print(f"Generated report: {report_path}")
    
    return results


def example_focused_calibration(sensitivity_results):
    """
    Example 4: Focused calibration using sensitivity analysis results.
    This demonstrates how to use sensitivity analysis to guide calibration.
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Focused Calibration Based on Sensitivity")
    print("="*60)
    
    # Step 1: Extract most sensitive parameters from previous analysis
    top_sensitive_params = [param for param, _ in sensitivity_results.get_most_sensitive_parameters(3)]
    print(f"Focusing on top 3 sensitive parameters: {', '.join(top_sensitive_params)}")
    
    # Step 2: Create focused calibration configuration
    base_config = ModelConfig(
        grid_size=(50, 50),
        num_layers=5,
        max_steps=45,
        random_seed=789
    )
    
    calib_config = CalibrationConfig(
        experiment_name="focused_calibration",
        method=CalibrationMethod.GRID_SEARCH,
        objective=CalibrationObjective.SPATIAL_SIMILARITY,
        base_config=base_config,
        calibration_parameters=top_sensitive_params,
        grid_search_points=4,  # Higher resolution for fewer parameters
        results_dir="calibration_results/focused_example"
    )
    
    print(calib_config.summary())
    
    # Step 3: Setup and run calibration
    parameter_bounds = get_default_calibration_bounds()
    objective_function = create_default_spatial_objective()
    target_data = create_synthetic_target_data((50, 50), "circular")
    
    calibrator = GridSearchCalibrator(
        calibration_config=calib_config,
        parameter_bounds=parameter_bounds,
        objective_function=objective_function,
        parallel_execution=True,
        max_workers=2
    )
    
    print("\nStarting focused calibration...")
    start_time = time.time()
    results = calibrator.run_calibration(target_data=target_data)
    runtime = time.time() - start_time
    
    # Step 4: Display and save results
    print(f"\nFocused calibration completed in {runtime:.2f} seconds")
    print(f"Best objective value: {results.get_best_objective_value():.4f}")
    print(f"Parameter sensitivity helped reduce search space by "
          f"{(6 - len(top_sensitive_params))/6*100:.0f}%")
    
    save_calibration_results(results, calib_config.results_dir, "focused")
    return results


def example_lidar_calibration():
    """
    Example 5: LiDAR-based calibration using real geographic data.
    This demonstrates how to calibrate using actual LiDAR and terrain data.
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: LiDAR-Based Calibration")
    print("="*60)
    
    # Step 1: Create calibration config from production configuration
    try:
        from src.core.calibration import create_calibration_from_production_config
        
        # This would use your actual production config file
        # For demo purposes, we'll create a manual configuration
        base_config = ModelConfig(
            grid_size=(1000, 1000),  # Smaller grid for calibration
            num_layers=20,
            layer_height=2.0,
            model_resolution=20.0,  # Updated to 20m resolution
            max_steps=30,
            random_seed=789,
            
            # Geographic configuration (Tenerife example)
            geo_bounds=(273500, 3094350, 278500, 3099350),  # 5km x 5km area
            crs="EPSG:25828",
            
            # LiDAR configuration (would point to real data in production)
            auto_size_from_lidar=False,
            lidar_data_dir="/path/to/lidar/data",  # Would be real path in production
            extinction_coefficient=0.5,
            pad_bin_size=2.0,
            exclude_ground_layer=True,
            
            # Terrain configuration
            dem_file="/path/to/terrain/data.tif",  # Would be real path in production
            
            # Processing settings
            tile_size=100,
            tile_overlap_ratio=0.05,
            memory_optimization_level=1
        )
        
        calib_config = CalibrationConfig(
            experiment_name="lidar_calibration_demo",
            method=CalibrationMethod.GRID_SEARCH,
            objective=CalibrationObjective.SPATIAL_SIMILARITY,
            base_config=base_config,
            calibration_parameters=[
                'spread_probability',
                'fuel_consumption_rate',
                'ignition_threshold'
            ],
            
            # Geographic settings for calibration
            geo_bounds=(273500, 3094350, 278500, 3099350),
            crs="EPSG:25828", 
            model_resolution=20.0,
            
            # LiDAR settings for calibration (disabled for demo)
            use_lidar_data=False,  # Set to True with real data
            lidar_data_dir=None,   # Would be real path in production
            
            # Terrain settings for calibration (disabled for demo)
            use_terrain=False,     # Set to True with real data
            dem_file=None,         # Would be real path in production
            
            # Calibration settings
            grid_search_points=3,  # Small for demo
            results_dir="calibration_results/lidar_demo",
            max_workers=2
        )
        
        print("LiDAR calibration configuration created successfully!")
        print(calib_config.summary())
        
        # Step 2: For demo purposes, create synthetic target data
        # In production, this would be real historical fire data in the same CRS
        target_data = create_synthetic_target_data((1000, 1000), "elliptical")
        
        # Add geographic metadata to target data
        target_data.update({
            'geo_bounds': calib_config.geo_bounds,
            'crs': calib_config.crs,
            'resolution': calib_config.model_resolution
        })
        
        print(f"Created target data with {target_data['burned_cells']} burned cells")
        print(f"Geographic bounds: {target_data['geo_bounds']}")
        print(f"CRS: {target_data['crs']}")
        
        # Step 3: Set up calibration components
        parameter_bounds = get_default_calibration_bounds()
        objective_function = create_default_spatial_objective()
        
        # Step 4: Initialize calibrator
        calibrator = GridSearchCalibrator(
            calibration_config=calib_config,
            parameter_bounds=parameter_bounds,
            objective_function=objective_function,
            parallel_execution=True,
            max_workers=2
        )
        
        # Step 5: Show estimation for LiDAR-based calibration
        estimation = calibrator.get_estimation_info()
        print(f"\nLiDAR calibration estimation:")
        print(f"  Total combinations: {estimation['total_combinations']}")
        print(f"  Estimated time: {estimation['estimated_time_seconds']:.1f} seconds")
        print(f"  Geographic area: 5km x 5km")
        print(f"  Grid resolution: {calib_config.model_resolution}m")
        
        # Step 6: Run calibration (would use real LiDAR data in production)
        print("\nStarting LiDAR-based calibration...")
        progress_callback = create_progress_callback(verbose=True)
        
        start_time = time.time()
        results = calibrator.run_calibration(
            target_data=target_data,
            progress_callback=progress_callback
        )
        runtime = time.time() - start_time
        
        # Step 7: Display results
        print(f"\nLiDAR calibration completed in {runtime:.2f} seconds")
        print(f"Best objective value: {results.get_best_objective_value():.4f}")
        print(f"Best parameters for LiDAR simulation:")
        for param, value in results.get_best_parameters().items():
            print(f"  {param}: {value:.4f}")
        
        # Step 8: Save results with geographic metadata
        save_calibration_results(results, calib_config.results_dir, "lidar_calibration")
        
        # Add usage notes
        print(f"\n{'='*60}")
        print("PRODUCTION USAGE NOTES:")
        print("="*60)
        print("To use with real LiDAR data:")
        print("1. Set use_lidar_data=True")
        print("2. Provide valid lidar_data_dir path")
        print("3. Set use_terrain=True if terrain effects needed")
        print("4. Provide valid dem_file path")
        print("5. Ensure geo_bounds match your LiDAR data extent")
        print("6. Use appropriate CRS for your geographic region")
        print("7. Consider larger grid_size for full-scale calibration")
        
        return results
        
    except Exception as e:
        logger.error(f"LiDAR calibration example failed: {e}")
        print(f"Error: {e}")
        print("This example requires proper LiDAR data paths for full functionality.")
        return None


def main():
    """
    Main function demonstrating the complete calibration workflow.
    """
    print("Forest Fire Simulation Calibration Framework")
    print("=" * 60)
    print("This example demonstrates different calibration approaches.")
    print("Note: These are simplified examples with small grids for quick execution.")
    print()
    
    try:
        # Example 1: Basic grid search
        basic_results = example_basic_calibration()
        
        # Example 2: Sensitivity analysis
        sensitivity_results = example_sensitivity_analysis()
        
        # Example 3: Fire behavior calibration
        fire_behavior_results = example_fire_behavior_calibration()
        
        # Example 4: Focused calibration based on sensitivity
        focused_results = example_focused_calibration(sensitivity_results)
        
        # Example 5: LiDAR-based calibration
        lidar_results = example_lidar_calibration()
        
        # Summary
        print("\n" + "="*60)
        print("CALIBRATION EXAMPLES COMPLETED")
        print("="*60)
        print(f"✓ Basic grid search: {basic_results.get_best_objective_value():.4f}")
        print(f"✓ Sensitivity analysis: {len(sensitivity_results.get_most_sensitive_parameters())} parameters ranked")
        print(f"✓ Fire behavior: {fire_behavior_results.get_best_objective_value():.4f}")
        print(f"✓ Focused calibration: {focused_results.get_best_objective_value():.4f}")
        if lidar_results:
            print(f"✓ LiDAR calibration: {lidar_results.get_best_objective_value():.4f}")
        else:
            print("✓ LiDAR calibration: Demo completed (requires real data paths)")
        print()
        print("Check the calibration_results/ directory for detailed outputs.")
        print("HTML reports have been generated for visual analysis.")
        print("\nFor production LiDAR calibration:")
        print("- Use create_calibration_from_production_config() with your config file")
        print("- Ensure LiDAR data directories and DEM files are accessible")
        print("- Set appropriate geographic bounds for your study area")
        
    except Exception as e:
        logger.error(f"Example execution failed: {e}")
        print(f"Error: {e}")
        print("This might be due to missing dependencies or configuration issues.")


if __name__ == "__main__":
    main() 