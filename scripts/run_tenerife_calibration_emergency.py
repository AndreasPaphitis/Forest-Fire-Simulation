#!/usr/bin/env python3
"""
EMERGENCY Tenerife Calibration - Extreme Memory Optimization
For local testing when HPC fails
"""

import sys
import os
from pathlib import Path
import logging

# Add src to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
from core.calibration.calibration_config import CalibrationConfig

def main():
    """Run emergency calibration with extreme optimizations."""
    
    # EMERGENCY CONFIGURATION
    EMERGENCY_CONFIG = {
        'model_resolution': 50.0,  # 50m resolution (5x coarser)
        'max_steps': 50,  # Half the steps
        'num_layers': 5,  # Minimal layers
        'grid_size': (100, 100),  # Fixed small grid
        'simulation_timeout_minutes': 15.0,  # Shorter timeout
        'memory_optimization_level': 3,  # Maximum optimization
        'use_lidar_data': False,  # DISABLE LiDAR temporarily
        'shared_terrain_info': None,  # Disable shared terrain
    }
    
    print("🚨 EMERGENCY CALIBRATION MODE")
    print("📊 Configuration:")
    for key, value in EMERGENCY_CONFIG.items():
        print(f"   {key}: {value}")
    
    # Create calibration config
    calib_config = CalibrationConfig()
    
    # Apply emergency settings
    calib_config.base_config.model_resolution = EMERGENCY_CONFIG['model_resolution']
    calib_config.base_config.max_steps = EMERGENCY_CONFIG['max_steps']
    calib_config.base_config.num_layers = EMERGENCY_CONFIG['num_layers']
    calib_config.base_config.grid_size = EMERGENCY_CONFIG['grid_size']
    calib_config.base_config.simulation_timeout_minutes = EMERGENCY_CONFIG['simulation_timeout_minutes']
    calib_config.base_config.memory_optimization_level = EMERGENCY_CONFIG['memory_optimization_level']
    calib_config.base_config.use_lidar_data = EMERGENCY_CONFIG['use_lidar_data']
    calib_config.base_config.shared_terrain_info = EMERGENCY_CONFIG['shared_terrain_info']
    
    # Minimal parameter space
    calib_config.grid_search_points = 2  # Only 2 points per parameter
    calib_config.max_workers = 2  # Only 2 workers
    
    # Create calibrator
    calibrator = TenerifeFirePerimeterCalibrator(
        config=calib_config,
        experiment_name="emergency_calibration_50m_50t_"
    )
    
    print(f"🎯 Total combinations: {calibrator.total_combinations}")
    print(f"🔧 Workers: {calibrator.max_workers}")
    print(f"⏱️  Expected time: ~30-60 minutes")
    
    # Run calibration
    results = calibrator.run_calibration()
    
    print("✅ Emergency calibration completed!")
    print(f"📊 Best objective: {results.get_best_objective_value()}")
    print(f"📁 Results: {calibrator.results_dir}")

if __name__ == "__main__":
    main()
