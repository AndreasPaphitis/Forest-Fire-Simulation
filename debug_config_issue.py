#!/usr/bin/env python3
"""
Debug script to test config attribute access issue.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config.config_tools import ModelConfig

def test_config_access():
    """Test accessing grid_size from ModelConfig."""
    print("=== TESTING CONFIG ATTRIBUTE ACCESS ===")
    
    # Create config with grid_size
    config = ModelConfig(
        grid_size=(609, 609),
        num_layers=20,
        max_steps=10,
        model_resolution=20.0,
        simulation_type="memory_optimized",
        memory_optimization_level=3,
        use_disk_storage=True,
        use_differential_history=True,
        use_sparse_storage=True,
        use_preprocessed_terrain=True,
        preprocessed_terrain_dir="preprocessed_terrain"
    )
    
    # Add LiDAR directory
    config.preprocessed_lidar_dir = "preprocessed_lidar"
    
    print(f"Config type: {type(config)}")
    print(f"Config grid_size: {config.grid_size}")
    print(f"Config grid_size type: {type(config.grid_size)}")
    
    # Test getattr
    grid_size_attr = getattr(config, 'grid_size', None)
    print(f"getattr(config, 'grid_size'): {grid_size_attr}")
    print(f"getattr type: {type(grid_size_attr)}")
    
    # Test direct access
    print(f"config.grid_size: {config.grid_size}")
    print(f"config.num_layers: {config.num_layers}")
    
    # Test if grid_size is a tuple
    if isinstance(config.grid_size, tuple):
        print("✅ grid_size is a tuple")
        width, height = config.grid_size
        print(f"Width: {width}, Height: {height}")
    else:
        print(f"❌ grid_size is not a tuple: {type(config.grid_size)}")
    
    return config

if __name__ == "__main__":
    config = test_config_access()
    print("\n=== CONFIG TEST COMPLETE ===")
