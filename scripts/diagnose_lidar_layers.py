#!/usr/bin/env python
"""
Diagnostic script to check LiDAR layer detection in subsetted area
"""

import os
import re
import sys
from pathlib import Path
import numpy as np
import geopandas as gpd
from rasterio import open as rio_open
from rasterio.warp import calculate_default_transform, reproject, Resampling

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.lidar_utils import LiDARDataManager

def diagnose_lidar_layers():
    """Diagnose LiDAR layer detection issues"""
    
    print("🔍 DIAGNOSING LIDAR LAYER DETECTION")
    print("=" * 50)
    
    # Configuration
    lidar_data_dir = Path(r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\Analysis files\Processed\PAD Results")
    
    # Day 4 fire bounds (same as in calibration)
    emsr_dir = Path(r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\Coding\QGIS python scripts\EMSR Delineations")
    day4_path = emsr_dir / "Day 4 (26_08_23)"
    
    if not day4_path.exists():
        print(f"❌ Day 4 path not found: {day4_path}")
        return
    
    # Find Day 4 shapefile
    shp_files = list(day4_path.glob("*.shp"))
    if not shp_files:
        print(f"❌ No shapefiles found in: {day4_path}")
        return
    
    day4_file = shp_files[0]
    print(f"📁 Using Day 4 file: {day4_file}")
    
    # Calculate fire bounds with buffer
    gdf = gpd.read_file(str(day4_file))
    if gdf.empty:
        print("❌ Empty shapefile")
        return
    
    # Convert to UTM Zone 28N for accurate bounds
    gdf_utm = gdf.to_crs('EPSG:32628')
    bounds = gdf_utm.total_bounds  # [minx, miny, maxx, maxy]
    
    # Add 10% buffer for fire spread
    buffer_factor = 1.1
    width_m = bounds[2] - bounds[0]
    height_m = bounds[3] - bounds[1]
    center_x = (bounds[0] + bounds[2]) / 2
    center_y = (bounds[1] + bounds[3]) / 2
    
    buffered_width = width_m * buffer_factor
    buffered_height = height_m * buffer_factor
    
    geo_bounds = (
        center_x - buffered_width/2,   # minx
        center_y - buffered_height/2,  # miny
        center_x + buffered_width/2,   # maxx
        center_y + buffered_height/2   # maxy
    )
    
    print(f"🌍 Fire area bounds: {bounds}")
    print(f"🌍 Buffered bounds: {geo_bounds}")
    print(f"📏 Fire area: {width_m/1000:.1f}km × {height_m/1000:.1f}km")
    print(f"📏 Buffered area: {buffered_width/1000:.1f}km × {buffered_height/1000:.1f}km")
    
    # Check if LiDAR directory exists
    if not lidar_data_dir.exists():
        print(f"❌ LiDAR directory not found: {lidar_data_dir}")
        return
    
    print(f"\n📁 LiDAR directory: {lidar_data_dir}")
    
    # Check all PNOA directories
    pnoa_dirs = list(lidar_data_dir.glob("PNOA*"))
    print(f"📂 Found {len(pnoa_dirs)} PNOA directories")
    
    for pnoa_dir in pnoa_dirs:
        print(f"\n🔍 Checking PNOA directory: {pnoa_dir.name}")
        
        # Check for PAD raster directories
        pad_dirs = list(pnoa_dir.glob("*PAD*"))
        print(f"  📂 Found {len(pad_dirs)} PAD directories")
        
        for pad_dir in pad_dirs:
            print(f"  🔍 Checking PAD directory: {pad_dir.name}")
            
            # Check for PAD raster files
            pad_files = list(pad_dir.glob("*_pad_*.tif"))
            print(f"    📄 Found {len(pad_files)} PAD files")
            
            if pad_files:
                print("    📋 PAD file names:")
                for i, pad_file in enumerate(pad_files[:10]):  # Show first 10
                    print(f"      {i+1}. {pad_file.name}")
                
                if len(pad_files) > 10:
                    print(f"      ... and {len(pad_files) - 10} more files")
                
                # Test regex patterns
                print("\n    🔍 Testing regex patterns:")
                
                # Current pattern
                current_pattern = r'_pad_(\d+\.?\d*)\.0m\.tif$'
                current_matches = []
                
                # Alternative patterns
                alt_patterns = [
                    r'_pad_(\d+\.?\d*)m\.tif$',  # No .0 before m
                    r'_pad_(\d+)\.0m\.tif$',     # Integer only
                    r'_pad_(\d+\.?\d*)m\.tif$',  # Any decimal
                ]
                
                for pad_file in pad_files:
                    filename = pad_file.name
                    
                    # Test current pattern
                    match = re.search(current_pattern, filename)
                    if match:
                        height = float(match.group(1))
                        current_matches.append((height, filename))
                    
                    # Test alternative patterns
                    for i, pattern in enumerate(alt_patterns):
                        match = re.search(pattern, filename)
                        if match:
                            height = float(match.group(1))
                            print(f"      Pattern {i+1} ({pattern}): {height}m - {filename}")
                
                print(f"\n    ✅ Current pattern matches: {len(current_matches)}")
                if current_matches:
                    heights = [h for h, f in current_matches]
                    print(f"    📊 Height range: {min(heights)}m - {max(heights)}m")
                    print(f"    📊 Unique heights: {sorted(set(heights))}")
                
                # Check geographic bounds
                print("\n    🌍 Checking geographic bounds...")
                valid_files = 0
                for pad_file in pad_files[:5]:  # Check first 5 files
                    try:
                        with rio_open(pad_file) as src:
                            # Get file bounds
                            file_bounds = src.bounds
                            print(f"      {pad_file.name}: {file_bounds}")
                            
                            # Check if bounds overlap
                            overlap = (
                                file_bounds.left < geo_bounds[2] and
                                file_bounds.right > geo_bounds[0] and
                                file_bounds.bottom < geo_bounds[3] and
                                file_bounds.top > geo_bounds[1]
                            )
                            
                            if overlap:
                                valid_files += 1
                                print(f"        ✅ OVERLAPS with fire area")
                            else:
                                print(f"        ❌ NO OVERLAP with fire area")
                                
                    except Exception as e:
                        print(f"        ❌ Error reading {pad_file.name}: {e}")
                
                print(f"\n    📊 Files overlapping fire area: {valid_files}/{min(5, len(pad_files))}")
    
    # Test LiDARDataManager directly
    print(f"\n🔧 Testing LiDARDataManager directly...")
    try:
        lidar_manager = LiDARDataManager(
            lidar_data_dir=str(lidar_data_dir),
            geo_bounds=geo_bounds
        )
        
        # Test layer detection
        available_layers = lidar_manager._detect_available_layers()
        print(f"📊 LiDARDataManager detected {len(available_layers)} layers")
        print(f"📊 Layer keys: {sorted(available_layers.keys())}")
        
        max_layers = lidar_manager.get_max_available_layers()
        print(f"📊 Max available layers: {max_layers}")
        
    except Exception as e:
        print(f"❌ Error testing LiDARDataManager: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_lidar_layers()
