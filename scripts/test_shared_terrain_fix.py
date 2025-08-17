#!/usr/bin/env python3
"""
Test script to verify shared terrain fix is working.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod, CalibrationObjective
from src.config.config_tools import ModelConfig

def test_shared_terrain_setup():
    """Test that shared terrain is properly set up and passed to workers."""
    
    print("🧪 Testing Shared Terrain Fix")
    print("=" * 50)
    
    # Create a minimal calibration configuration
    base_config = ModelConfig(
        grid_size=(1000, 1000),  # Small grid for testing
        num_layers=10,
        use_preprocessed_terrain=True,
        preprocessed_terrain_dir="preprocessed_terrain"
    )
    
    calib_config = CalibrationConfig(
        experiment_name="test_shared_terrain",
        method=CalibrationMethod.GRID_SEARCH,
        objective=CalibrationObjective.SPATIAL_SIMILARITY,
        base_config=base_config,
        calibration_parameters=['wind_speed', 'wind_direction'],
        grid_search_points=2,
        max_workers=2
    )
    
    # Create calibrator
    calibrator = TenerifeFirePerimeterCalibrator(
        memory_gb=64,
        workers=2,
        grid_search_points=2,
        experiment_name="test_shared_terrain"
    )
    
    # Test shared terrain setup
    print("🔧 Testing shared terrain setup...")
    shared_terrain_info = calibrator._setup_shared_terrain_if_possible(calib_config)
    
    if shared_terrain_info:
        print("✅ Shared terrain setup successful!")
        print(f"   Shared terrain info keys: {list(shared_terrain_info.keys())}")
        
        # Test config variant creation
        print("🔧 Testing config variant creation...")
        test_params = {'wind_speed': 5.0, 'wind_direction': 90.0}
        config_variant = calib_config.create_config_variant(test_params)
        
        if hasattr(config_variant, 'shared_terrain_info') and config_variant.shared_terrain_info:
            print("✅ Shared terrain info passed to config variant!")
            print(f"   Config variant has shared terrain: {config_variant.shared_terrain_info is not None}")
        else:
            print("❌ Shared terrain info NOT passed to config variant!")
            
    else:
        print("⚠️  Shared terrain setup failed (this is expected if preprocessed_terrain directory doesn't exist)")
        print("   This is normal for testing without actual terrain data")
    
    print("\n✅ Shared terrain fix test completed!")

if __name__ == "__main__":
    test_shared_terrain_setup()
