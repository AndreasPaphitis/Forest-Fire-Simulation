#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fix Terrain Subsetting Issue

This script fixes the terrain subsetting problem where we were taking the top-left corner
instead of the correct geographic region that corresponds to the Day 4 fire area.

The issue: Day 4 fire area is in southern Tenerife (higher elevations), but we were
subsetting from the top-left corner of terrain data (northern region, lower elevations).

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

def analyze_terrain_subsetting_issue():
    """Analyze and fix the terrain subsetting issue."""
    
    print("🔍 ANALYZING TERRAIN SUBSETTING ISSUE")
    print("=" * 50)
    
    # Step 1: Load terrain metadata
    terrain_dir = Path("preprocessed_terrain")
    metadata_file = terrain_dir / "metadata.json"
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    print(f"📊 Terrain metadata:")
    print(f"   Grid size: {metadata['grid_size']}")
    print(f"   CRS: {metadata['crs']}")
    print(f"   Transform: {metadata['transform']}")
    print(f"   Elevation range: {metadata['elevation_range']}")
    
    # Step 2: Load full terrain data
    print(f"\n📋 Loading full terrain data...")
    elevation_file = terrain_dir / "elevation.npy"
    full_elevation = np.load(elevation_file)
    
    print(f"📊 Full terrain data:")
    print(f"   Shape: {full_elevation.shape}")
    print(f"   Min: {np.min(full_elevation):.3f}m")
    print(f"   Max: {np.max(full_elevation):.3f}m")
    print(f"   Mean: {np.mean(full_elevation):.3f}m")
    
    # Step 3: Calculate Day 4 fire area bounds
    print(f"\n🎯 Calculating Day 4 fire area bounds...")
    
    try:
        from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
        
        # Create temporary calibrator
        temp_calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=16,
            workers=1,
            grid_search_points=2,
            experiment_name="terrain_fix"
        )
        
        # Get Day 4 fire bounds
        day4_path = "EMSR Delineations/Day 4 (26_08_23)/EMSR685_AOI01_GRA_PRODUCT_observedEventA_v1.shp"
        
        import geopandas as gpd
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
        
        # Step 4: Map fire bounds to terrain grid coordinates
        print(f"\n🗺️  Mapping fire bounds to terrain grid...")
        
        # Get terrain transform information
        transform_str = metadata['transform']
        print(f"   Raw transform: {transform_str}")
        
        # Parse transform string
        # Format: | 5.00, 0.00, 310097.50|
        #         | 0.00,-5.00, 3165002.50|
        #         | 0.00, 0.00, 1.00|
        
        # Extract values from the string
        lines = transform_str.strip().split('\n')
        line1 = lines[0].replace('|', '').strip().split(',')
        line2 = lines[1].replace('|', '').strip().split(',')
        
        pixel_size_x = float(line1[0].strip())
        pixel_size_y = float(line2[1].strip())  # -5.0 (negative for top-to-bottom)
        origin_x = float(line1[2].strip())
        origin_y = float(line2[2].strip())
        
        print(f"📊 Terrain transform:")
        print(f"   Pixel size: {pixel_size_x}m × {abs(pixel_size_y)}m")
        print(f"   Origin: ({origin_x}, {origin_y})")
        
        # Calculate terrain bounds
        terrain_width, terrain_height = metadata['grid_size']
        terrain_max_x = origin_x + (terrain_width * pixel_size_x)
        terrain_max_y = origin_y + (terrain_height * pixel_size_y)
        
        print(f"📊 Terrain bounds:")
        print(f"   Min: ({origin_x}, {terrain_max_y})")
        print(f"   Max: ({terrain_max_x}, {origin_y})")
        
        # Map fire bounds to terrain grid coordinates
        fire_min_x, fire_min_y, fire_max_x, fire_max_y = bounds
        
        print(f"📊 Fire bounds (EPSG:25828):")
        print(f"   Min: ({fire_min_x}, {fire_min_y})")
        print(f"   Max: ({fire_max_x}, {fire_max_y})")
        
        # Check if fire area is within terrain bounds
        if (fire_min_x < origin_x or fire_max_x > terrain_max_x or 
            fire_min_y < terrain_max_y or fire_max_y > origin_y):
            print(f"⚠️  WARNING: Fire area extends outside terrain bounds!")
            print(f"   Terrain X: {origin_x} to {terrain_max_x}")
            print(f"   Fire X: {fire_min_x} to {fire_max_x}")
            print(f"   Terrain Y: {terrain_max_y} to {origin_y}")
            print(f"   Fire Y: {fire_min_y} to {fire_max_y}")
        
        # Convert to grid coordinates (note: Y-axis is inverted in raster)
        grid_min_x = int((fire_min_x - origin_x) / pixel_size_x)
        grid_max_x = int((fire_max_x - origin_x) / pixel_size_x)
        
        # For Y-axis, remember that raster Y=0 is at the top (origin_y)
        # and increases downward, so we need to invert the Y coordinates
        grid_min_y = int((origin_y - fire_max_y) / abs(pixel_size_y))  # fire_max_y becomes grid_min_y
        grid_max_y = int((origin_y - fire_min_y) / abs(pixel_size_y))  # fire_min_y becomes grid_max_y
        
        # Ensure bounds are within terrain
        grid_min_x = max(0, grid_min_x)
        grid_min_y = max(0, grid_min_y)
        grid_max_x = min(terrain_width, grid_max_x)
        grid_max_y = min(terrain_height, grid_max_y)
        
        print(f"🎯 Fire area in terrain grid:")
        print(f"   Grid bounds: ({grid_min_x}, {grid_min_y}) to ({grid_max_x}, {grid_max_y})")
        print(f"   Grid size: {grid_max_x - grid_min_x} × {grid_max_y - grid_min_y}")
        
        # Step 5: Extract correct terrain subset
        print(f"\n🔧 Extracting correct terrain subset...")
        
        # Extract the correct region
        correct_subset = full_elevation[grid_min_y:grid_max_y, grid_min_x:grid_max_x]
        
        print(f"📊 Correct subset:")
        print(f"   Shape: {correct_subset.shape}")
        print(f"   Min: {np.min(correct_subset):.3f}m")
        print(f"   Max: {np.max(correct_subset):.3f}m")
        print(f"   Mean: {np.mean(correct_subset):.3f}m")
        
        # Step 6: Compare with current wrong subset
        print(f"\n⚠️  COMPARISON WITH CURRENT WRONG SUBSET:")
        
        # Current wrong subset (top-left corner)
        wrong_subset = full_elevation[:grid_width, :grid_height]
        
        print(f"❌ Current wrong subset (top-left corner):")
        print(f"   Shape: {wrong_subset.shape}")
        print(f"   Min: {np.min(wrong_subset):.3f}m")
        print(f"   Max: {np.max(wrong_subset):.3f}m")
        print(f"   Mean: {np.mean(wrong_subset):.3f}m")
        
        print(f"✅ Correct subset (fire area):")
        print(f"   Shape: {correct_subset.shape}")
        print(f"   Min: {np.min(correct_subset):.3f}m")
        print(f"   Max: {np.max(correct_subset):.3f}m")
        print(f"   Mean: {np.mean(correct_subset):.3f}m")
        
        # Step 7: Create fix for forest model
        print(f"\n🛠️  CREATING FIX FOR FOREST MODEL")
        print("=" * 50)
        
        print("The issue is in the terrain subsetting logic in forest_model.py")
        print("We need to map the fire area bounds to the correct terrain grid coordinates")
        print("instead of just taking the top-left corner.")
        
        print(f"\n📋 Required changes:")
        print(f"1. Calculate fire area bounds in EPSG:25828 coordinates")
        print(f"2. Map bounds to terrain grid coordinates using transform")
        print(f"3. Extract correct subset: terrain[grid_min_y:grid_max_y, grid_min_x:grid_max_x]")
        print(f"4. Resize to target simulation grid if needed")
        
        return {
            'fire_bounds': bounds,
            'terrain_bounds': (origin_x, terrain_max_y, terrain_max_x, origin_y),
            'grid_bounds': (grid_min_x, grid_min_y, grid_max_x, grid_max_y),
            'correct_subset_shape': correct_subset.shape,
            'correct_elevation_range': (np.min(correct_subset), np.max(correct_subset))
        }
        
    except Exception as e:
        print(f"❌ Error analyzing terrain subsetting: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = analyze_terrain_subsetting_issue()
    
    if result:
        print(f"\n🎉 ANALYSIS COMPLETE!")
        print(f"✅ Fire bounds: {result['fire_bounds']}")
        print(f"✅ Terrain bounds: {result['terrain_bounds']}")
        print(f"✅ Grid bounds: {result['grid_bounds']}")
        print(f"✅ Correct subset shape: {result['correct_subset_shape']}")
        print(f"✅ Correct elevation range: {result['correct_elevation_range'][0]:.1f}m to {result['correct_elevation_range'][1]:.1f}m")
    else:
        print(f"\n❌ ANALYSIS FAILED")
