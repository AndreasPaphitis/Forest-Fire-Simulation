#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Terrain Subsetting Fix

This script tests the fix for the terrain subsetting issue by setting fire area bounds
and verifying that the correct geographic region is loaded.

Author: Forest Fire Simulation Team
Date: 2025
"""

import os
import sys
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_terrain_subsetting_fix():
    """Test the terrain subsetting fix."""
    
    print("🧪 TESTING TERRAIN SUBSETTING FIX")
    print("=" * 50)
    
    try:
        from src.config.config_tools import ModelConfig
        from src.core.forest_model import create_forest_model
        
        # Get Day 4 fire bounds
        print("🎯 Getting Day 4 fire bounds...")
        
        import geopandas as gpd
        day4_path = "EMSR Delineations/Day 4 (26_08_23)/EMSR685_AOI01_GRA_PRODUCT_observedEventA_v1.shp"
        gdf = gpd.read_file(day4_path)
        
        # Convert to EPSG:25828
        if gdf.crs != "EPSG:25828":
            print(f"🔄 Converting from {gdf.crs} to EPSG:25828")
            gdf = gdf.to_crs("EPSG:25828")
        
        # Get bounds
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        
        # Add 10% buffer
        width_m = bounds[2] - bounds[0]
        height_m = bounds[3] - bounds[1]
        buffer_factor = 1.1
        buffered_width_m = width_m * buffer_factor
        buffered_height_m = height_m * buffer_factor
        
        # Calculate grid size
        cell_size_m = 5.0
        grid_width = int(buffered_width_m / cell_size_m)
        grid_height = int(buffered_height_m / cell_size_m)
        
        print(f"🗺️  Day 4 fire bounds (EPSG:25828): {bounds}")
        print(f"🔥 Fire dimensions: {width_m:.0f}m × {height_m:.0f}m")
        print(f"🎯 Grid size: {grid_width} × {grid_height}")
        
        # Create configuration
        config = ModelConfig(
            grid_size=[grid_width, grid_height],
            num_layers=25,
            model_resolution=5.0,
            use_terrain=True,
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir="preprocessed_terrain"
        )
        
        print("✅ Configuration created")
        
        # Create forest model
        forest_model = create_forest_model(
            model_type='memory_optimized',
            config=config
        )
        
        print("✅ Forest model created")
        
        # Set fire area bounds for proper terrain subsetting
        forest_model.fire_area_bounds = bounds
        print(f"✅ Fire area bounds set: {bounds}")
        
        # Test terrain loading
        print("🔄 Testing terrain loading with fire area bounds...")
        terrain_success = forest_model.load_terrain_data(None)
        
        if terrain_success:
            print("✅ Terrain loading successful")
            
            # Check terrain data
            if hasattr(forest_model, 'terrain_elevation') and forest_model.terrain_elevation is not None:
                elev_data = forest_model.terrain_elevation
                print(f"📊 Terrain elevation loaded:")
                print(f"   Shape: {elev_data.shape}")
                print(f"   Min: {np.min(elev_data):.3f}m")
                print(f"   Max: {np.max(elev_data):.3f}m")
                print(f"   Mean: {np.mean(elev_data):.3f}m")
                
                # Check if we got the correct elevation range
                if np.max(elev_data) > 1000:  # Should be much higher than the wrong subset
                    print("✅ SUCCESS: Correct elevation range detected (southern Tenerife)")
                    print("   This indicates the fire area subsetting is working correctly!")
                else:
                    print("❌ FAILURE: Still getting low elevation range (northern Tenerife)")
                    print("   The subsetting fix may not be working correctly.")
            else:
                print("❌ Terrain elevation not loaded")
        else:
            print("❌ Terrain loading failed")
        
        return terrain_success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_terrain_subsetting_fix()
    
    if success:
        print(f"\n🎉 TERRAIN SUBSETTING FIX TEST PASSED!")
        print(f"✅ The fix is working correctly - proper geographic subsetting is active.")
    else:
        print(f"\n❌ TERRAIN SUBSETTING FIX TEST FAILED!")
        print(f"   The fix may need further adjustments.")
