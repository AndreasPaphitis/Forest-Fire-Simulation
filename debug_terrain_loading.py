#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug Terrain Loading Issues

This script tests the terrain loading mechanism to identify why preprocessed terrain
data is not being loaded properly.

Author: Forest Fire Simulation Team
Date: 2025
"""

import os
import sys
import json
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def debug_terrain_loading():
    """Debug the terrain loading mechanism."""
    
    print("🔍 DEBUGGING TERRAIN LOADING ISSUES")
    print("=" * 50)
    
    # Step 1: Check terrain files
    print("\n📋 STEP 1: CHECKING TERRAIN FILES")
    print("-" * 30)
    
    terrain_dir = Path("preprocessed_terrain")
    if not terrain_dir.exists():
        print(f"❌ Terrain directory not found: {terrain_dir}")
        return False
    
    print(f"✅ Terrain directory found: {terrain_dir}")
    
    # List all files
    terrain_files = list(terrain_dir.glob("*.npy"))
    print(f"📁 Found {len(terrain_files)} .npy files:")
    for file in terrain_files:
        print(f"   - {file.name}")
    
    # Step 2: Check metadata
    print("\n📋 STEP 2: CHECKING METADATA")
    print("-" * 30)
    
    metadata_file = terrain_dir / "metadata.json"
    if not metadata_file.exists():
        print(f"❌ Metadata file not found: {metadata_file}")
        return False
    
    print(f"✅ Metadata file found: {metadata_file}")
    
    # Load and analyze metadata
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    print(f"📊 Metadata contents:")
    for key, value in metadata.items():
        print(f"   {key}: {value}")
    
    # Check for required fields
    grid_size = metadata.get('grid_size', None)
    elevation_range = metadata.get('elevation_range', None)
    
    if grid_size:
        print(f"✅ Grid size found: {grid_size[0]} × {grid_size[1]}")
    else:
        print("❌ Grid size not found in metadata")
    
    if elevation_range:
        print(f"✅ Elevation range found: {elevation_range[0]:.1f}m to {elevation_range[1]:.1f}m")
    else:
        print("❌ Elevation range not found in metadata")
    
    # Step 3: Test loading individual terrain files
    print("\n📋 STEP 3: TESTING TERRAIN FILE LOADING")
    print("-" * 30)
    
    terrain_files_to_test = [
        'elevation.npy',
        'slope.npy',
        'aspect.npy',
        'barranco_mask.npy',
        'wind_amplification.npy'
    ]
    
    loaded_data = {}
    
    for filename in terrain_files_to_test:
        file_path = terrain_dir / filename
        if file_path.exists():
            try:
                data = np.load(file_path)
                loaded_data[filename] = data
                
                print(f"✅ {filename}:")
                print(f"   Shape: {data.shape}")
                print(f"   Data type: {data.dtype}")
                print(f"   Min: {np.min(data):.3f}")
                print(f"   Max: {np.max(data):.3f}")
                print(f"   Mean: {np.mean(data):.3f}")
                
                # Check if data is all zeros
                if np.all(data == 0):
                    print(f"   ⚠️  WARNING: All values are zero!")
                elif np.all(data == data[0, 0]):
                    print(f"   ⚠️  WARNING: All values are identical!")
                
            except Exception as e:
                print(f"❌ Failed to load {filename}: {e}")
        else:
            print(f"❌ File not found: {filename}")
    
    # Step 4: Test subsetting logic
    print("\n📋 STEP 4: TESTING SUBSETTING LOGIC")
    print("-" * 30)
    
    # Simulate the simulation grid size
    sim_width, sim_height = 4788, 4490
    print(f"📊 Simulation grid size: {sim_width} × {sim_height}")
    
    if 'elevation.npy' in loaded_data:
        terrain_data = loaded_data['elevation.npy']
        terrain_width, terrain_height = terrain_data.shape
        
        print(f"📊 Terrain data size: {terrain_width} × {terrain_height}")
        
        # Test subsetting
        if terrain_width >= sim_width and terrain_height >= sim_height:
            print("✅ Terrain data is large enough for subsetting")
            
            # Subset the data
            subset_data = terrain_data[:sim_width, :sim_height]
            print(f"✅ Subset successful: {subset_data.shape}")
            print(f"   Subset min: {np.min(subset_data):.3f}")
            print(f"   Subset max: {np.max(subset_data):.3f}")
            print(f"   Subset mean: {np.mean(subset_data):.3f}")
            
        else:
            print("❌ Terrain data too small for subsetting")
            print(f"   Required: {sim_width} × {sim_height}")
            print(f"   Available: {terrain_width} × {terrain_height}")
    
    # Step 5: Test the actual forest model loading
    print("\n📋 STEP 5: TESTING FOREST MODEL LOADING")
    print("-" * 30)
    
    try:
        from src.config.config_tools import ModelConfig
        from src.core.forest_model import create_forest_model
        
        # Create a test configuration
        config = ModelConfig(
            grid_size=[sim_width, sim_height],
            num_layers=25,
            model_resolution=5.0,
            use_terrain=True,
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir="preprocessed_terrain"
        )
        
        print("✅ Configuration created successfully")
        
        # Create forest model
        forest_model = create_forest_model(
            model_type='memory_optimized',
            config=config
        )
        
        print("✅ Forest model created successfully")
        print(f"   Model grid size: {forest_model.width} × {forest_model.height}")
        
        # Test terrain loading
        print("🔄 Testing terrain loading...")
        terrain_success = forest_model.load_terrain_data(None)  # No DEM file needed
        
        if terrain_success:
            print("✅ Terrain loading reported success")
        else:
            print("❌ Terrain loading reported failure")
        
        # Check what was actually loaded
        print("\n📊 Checking loaded terrain data:")
        
        if hasattr(forest_model, 'terrain_elevation') and forest_model.terrain_elevation is not None:
            elev_data = forest_model.terrain_elevation
            print(f"✅ Terrain elevation loaded:")
            print(f"   Shape: {elev_data.shape}")
            print(f"   Min: {np.min(elev_data):.3f}")
            print(f"   Max: {np.max(elev_data):.3f}")
            print(f"   Mean: {np.mean(elev_data):.3f}")
        else:
            print("❌ Terrain elevation not loaded")
        
        if hasattr(forest_model, 'terrain_slope') and forest_model.terrain_slope is not None:
            slope_data = forest_model.terrain_slope
            print(f"✅ Terrain slope loaded:")
            print(f"   Shape: {slope_data.shape}")
            print(f"   Min: {np.min(slope_data):.3f}")
            print(f"   Max: {np.max(slope_data):.3f}")
        else:
            print("❌ Terrain slope not loaded")
        
        if hasattr(forest_model, 'wind_amplification') and forest_model.wind_amplification is not None:
            wind_data = forest_model.wind_amplification
            print(f"✅ Wind amplification loaded:")
            print(f"   Shape: {wind_data.shape}")
            print(f"   Min: {np.min(wind_data):.3f}")
            print(f"   Max: {np.max(wind_data):.3f}")
        else:
            print("❌ Wind amplification not loaded")
        
    except Exception as e:
        print(f"❌ Forest model test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 6: Summary and recommendations
    print("\n📋 STEP 6: SUMMARY AND RECOMMENDATIONS")
    print("-" * 30)
    
    print("🔍 Issues identified:")
    
    # Check metadata structure
    if 'width' not in metadata and 'height' not in metadata:
        print("❌ Metadata uses 'grid_size' but code expects 'width' and 'height'")
    
    # Check terrain data quality
    if 'elevation.npy' in loaded_data:
        elev_data = loaded_data['elevation.npy']
        if np.all(elev_data == 0):
            print("❌ Elevation data is all zeros")
        elif np.all(elev_data == elev_data[0, 0]):
            print("❌ Elevation data is all identical")
        else:
            print("✅ Elevation data appears valid")
    
    print("\n🛠️ Recommendations:")
    print("1. Fix metadata structure to include 'width' and 'height' fields")
    print("2. Update terrain loading code to handle 'grid_size' format")
    print("3. Ensure proper subsetting logic for different grid sizes")
    print("4. Add better error handling and logging")
    
    return True

if __name__ == "__main__":
    debug_terrain_loading()
