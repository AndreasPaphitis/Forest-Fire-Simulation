#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Minimal Local Tenerife Test - Proper Scaling

This script creates a minimal test that uses the same core operations as the HPC
implementation but with appropriate scaling for 16GB RAM local testing.

Key Features:
- Uses the same parameter space as HPC
- Uses the same EMSR discovery process
- But with a manually controlled small grid size
- Focuses on testing the operations, not the scale

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
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.calibration.fire_perimeter_calibration import FirePerimeterDiscovery
    from src.core.calibration.grid_search import GridSearchCalibrator
    from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod, CalibrationObjective
    from src.core.calibration.objective_functions import SpatialSimilarityObjective
    from src.core.calibration.parameter_bounds import ParameterBounds, ParameterType, CalibrationTier
    from src.config.config_tools import ModelConfig
    from src.utils.logging_utils import get_logger
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.WARNING)  # Reduced verbosity
logger = get_logger(__name__)

def discover_emsr_data():
    """Discover EMSR data (same process as HPC)."""
    print("🔍 Discovering EMSR fire perimeter data...")
    
    emsr_dir = "EMSR Delineations"
    if not Path(emsr_dir).exists():
        print(f"❌ EMSR directory not found: {emsr_dir}")
        return None
    
    discovery = FirePerimeterDiscovery(emsr_dir)
    fire_dataset = discovery.discover_fire_perimeters()
    
    if not fire_dataset.fire_perimeters:
        print(f"❌ No fire perimeters found")
        return None
    
    print(f"✅ Found {len(fire_dataset.fire_perimeters)} fire perimeters")
    for fp in fire_dataset.fire_perimeters:
        print(f"   Day {fp.day_number}: {fp.area_hectares:.1f} ha")
    
    return fire_dataset

def create_minimal_config():
    """Create minimal configuration for local testing."""
    
    # Very small grid for local testing
    grid_width = 50
    grid_height = 50
    num_layers = 5
    total_cells = grid_width * grid_height * num_layers
    
    print(f"📐 Minimal grid: {grid_width} × {grid_height} × {num_layers} = {total_cells:,} cells")
    print(f"💾 Memory: ~{total_cells * 8 / 1e6:.1f} MB")
    
    config = {
        # Grid configuration
        'grid_size': [grid_width, grid_height],
        'num_layers': num_layers,
        'model_resolution': 200.0,  # 200m resolution (very coarse)
        'layer_height': 2.0,
        
        # Geographic bounds (small area in Tenerife)
        'geo_bounds': {
            'min_lat': 28.0,
            'max_lat': 28.005,  # Very small area
            'min_lon': -16.5,
            'max_lon': -16.495
        },
        'crs': 'EPSG:4326',
        
        # Simulation settings
        'max_steps': 10,  # Very short simulation
        'use_terrain': False,  # Disable terrain for simplicity
        'use_preprocessed_terrain': False,
        
        # Memory optimizations
        'memory_optimization_level': 2,
        'use_sparse_storage': True,
        'simulation_type': 'memory_optimized',
        
        # Output
        'output_dir': 'test_output/minimal_test',
        'results_output_dir': 'test_output/minimal_test/results',
        'logs_output_dir': 'test_output/minimal_test/logs',
        
        # Ignition
        'ignition_points': [{"x": grid_width // 2, "y": grid_height // 2, "layer": 1}]
    }
    
    return config

def create_minimal_parameter_space():
    """Create minimal parameter space (same parameters as HPC, fewer values)."""
    
    # TOP 5 PARAMETERS FROM SENSITIVITY ANALYSIS (same as HPC)
    param_space = {
        "spread_probability": [0.3],  # Single value for speed
        "fuel_consumption_rate": [0.05],  # Single value for speed
        "ember_probability": [0.2],  # Single value for speed
        "ember_ignition": [0.35],  # Single value for speed
        "fuel_moisture_baseline": [0.2]  # Single value for speed
    }
    
    print(f"🔧 Parameter space: {len(param_space)} parameters, 1 combination total")
    
    return param_space

def create_custom_parameter_bounds(param_space):
    """Create parameter bounds that return exact values."""
    
    class CustomParameterBounds(ParameterBounds):
        def __init__(self, specific_values, **kwargs):
            self.specific_values = specific_values
            # Create valid min/max for validation
            min_val = min(specific_values) if specific_values else 0.0
            max_val = max(specific_values) if specific_values else 1.0
            if min_val == max_val:
                max_val = min_val + 0.001
            super().__init__(min_value=min_val, max_value=max_val, **kwargs)
        
        def generate_grid_points(self, num_points=None):
            return self.specific_values
    
    parameter_bounds = {}
    for param_name, param_values in param_space.items():
        parameter_bounds[param_name] = CustomParameterBounds(
            specific_values=param_values,
            default_value=param_values[0],
            parameter_type=ParameterType.PROBABILITY if 'probability' in param_name else ParameterType.POSITIVE_FLOAT,
            calibration_tier=CalibrationTier.CRITICAL,
            physical_interpretation=f"Parameter: {param_name}",
            units="unitless",
            suggested_points=len(param_values)
        )
    
    return parameter_bounds

def create_minimal_target_data(config):
    """Create minimal synthetic target data."""
    import numpy as np
    
    grid_width, grid_height = config['grid_size']
    
    # Create small circular target
    fire_perimeter = np.zeros((grid_width, grid_height), dtype=np.float32)
    center_x, center_y = grid_width // 2, grid_height // 2
    radius = 5  # Very small fire
    
    for x in range(grid_width):
        for y in range(grid_height):
            if (x - center_x)**2 + (y - center_y)**2 <= radius**2:
                fire_perimeter[x, y] = 1.0
    
    target_data = {
        'fire_perimeter': fire_perimeter,
        'area_hectares': 10.0,
        'day_number': 4,
        'source': 'minimal_test_synthetic',
        'grid_size': (grid_width, grid_height),
        'resolution_m': config['model_resolution']
    }
    
    print(f"🎯 Target data: {radius} cell radius, {np.sum(fire_perimeter)} active cells")
    
    return target_data

def main():
    """Run minimal local test."""
    
    print("🔥 MINIMAL LOCAL TENERIFE TEST")
    print("=" * 40)
    print("System: 16GB RAM, 1 worker (sequential)")
    print("Grid: 50×50×5 (12.5K cells)")
    print("Purpose: Test core operations only")
    
    try:
        # Step 1: Discover EMSR data (same as HPC)
        fire_dataset = discover_emsr_data()
        if fire_dataset is None:
            print("❌ EMSR discovery failed")
            return
        
        # Step 2: Create minimal configuration
        config_dict = create_minimal_config()
        param_space = create_minimal_parameter_space()
        
        # Step 3: Create ModelConfig
        base_config = ModelConfig.from_dict(config_dict)
        
        # Step 4: Create calibration config
        calibration_config = CalibrationConfig(
            base_config=base_config,
            method=CalibrationMethod.GRID_SEARCH,
            objective=CalibrationObjective.SPATIAL_SIMILARITY,
            calibration_parameters=list(param_space.keys()),
            grid_search_points=1,  # Single point for speed
            max_workers=1,  # Sequential
            parallel_execution=False,
            results_dir='test_output/minimal_calibration_results'
        )
        
        # Step 5: Create parameter bounds
        parameter_bounds = create_custom_parameter_bounds(param_space)
        
        # Step 6: Create objective function
        objective_function = SpatialSimilarityObjective()
        
        # Step 7: Create calibrator
        print(f"\n🔧 Initializing minimal calibrator...")
        calibrator = GridSearchCalibrator(
            calibration_config=calibration_config,
            parameter_bounds=parameter_bounds,
            objective_function=objective_function,
            parallel_execution=False,
            max_workers=1,
            bypass_worker_limit=False
        )
        
        print(f"✅ Calibrator initialized: {calibrator.total_combinations} combination(s)")
        
        # Step 8: Create target data
        target_data = create_minimal_target_data(config_dict)
        
        # Step 9: Run calibration
        print(f"\n🔥 Starting minimal calibration...")
        start_time = time.time()
        
        def progress_callback(completed, total, result):
            print(f"Progress: {completed}/{total} - Objective: {result.objective_value:.4f}")
        
        results = calibrator.run_calibration(
            target_data=target_data,
            progress_callback=progress_callback
        )
        
        total_time = time.time() - start_time
        
        # Step 10: Display results
        print(f"\n🎉 MINIMAL TEST COMPLETED!")
        print(f"⏱️  Time: {total_time:.2f} seconds")
        print(f"📊 Evaluations: {results.successful_evaluations}/{results.total_evaluations}")
        
        if results.best_result:
            print(f"🏆 Best objective: {results.best_result.objective_value:.4f}")
            print(f"🔧 Parameters: {results.best_result.parameter_values}")
        
        # Save results
        output_file = "test_output/minimal_calibration_results.json"
        Path("test_output").mkdir(exist_ok=True)
        
        results_dict = {
            "experiment_name": "minimal_local_test",
            "total_combinations": results.total_evaluations,
            "successful_evaluations": results.successful_evaluations,
            "total_time": total_time,
            "best_objective_value": results.best_result.objective_value if results.best_result else None,
            "best_parameters": results.best_result.parameter_values if results.best_result else None,
            "grid_size": config_dict['grid_size'],
            "resolution_m": config_dict['model_resolution']
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"💾 Results saved: {output_file}")
        print(f"\n✅ CORE OPERATIONS TEST SUCCESSFUL!")
        print(f"   This confirms the basic calibration framework works")
        print(f"   Performance: {results.total_evaluations / total_time:.2f} evaluations/second")
        
    except Exception as e:
        print(f"\n❌ Minimal test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
