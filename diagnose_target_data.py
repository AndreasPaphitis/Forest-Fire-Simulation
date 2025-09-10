#!/usr/bin/env python3

import numpy as np
import geopandas as gpd
from pathlib import Path
import json

print('🔍 DIAGNOSING CALIBRATION TARGET DATA')
print('=' * 50)

# 1. Check what EMSR target data looks like when rasterized
print('📊 EMSR TARGET DATA ANALYSIS:')
print('=' * 30)

emsr_files = {
    1: "Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp",
    2: "Day 2 (21_08_23)/EMSR685_AOI01_DEL_MONIT01_observedEventA_v1.shp"
}

for day, shapefile_path in emsr_files.items():
    full_path = Path("EMSR Delineations") / shapefile_path
    if full_path.exists():
        try:
            print(f'Day {day} EMSR data:')
            gdf = gpd.read_file(full_path)
            gdf_utm = gdf.to_crs(epsg=32628)  # Convert to UTM
            
            # Calculate area
            total_area_m2 = gdf_utm.geometry.area.sum()
            area_ha = total_area_m2 / 10000
            
            # Get bounds
            bounds = gdf_utm.total_bounds
            width_m = bounds[2] - bounds[0]
            height_m = bounds[3] - bounds[1]
            
            print(f'  Total area: {area_ha:.1f} hectares ({total_area_m2:.0f} m²)')
            print(f'  Bounds: {bounds}')
            print(f'  Size: {width_m:.0f}m × {height_m:.0f}m')
            print(f'  Features: {len(gdf)}')
            
            # Estimate cells at 20m resolution
            cells_20m = total_area_m2 / (20 * 20)
            print(f'  Estimated cells at 20m: {cells_20m:.0f}')
            print()
            
        except Exception as e:
            print(f'Day {day}: Error - {e}')

# 2. Simulate the calibration rasterization process
print('🎯 SIMULATING CALIBRATION RASTERIZATION:')
print('=' * 40)

try:
    # Load Day 1 data (most commonly used for calibration)
    day1_path = Path("EMSR Delineations") / emsr_files[1]
    gdf = gpd.read_file(day1_path)
    gdf_utm = gdf.to_crs(epsg=32628)
    
    # Get bounds
    bounds = gdf_utm.total_bounds
    fire_center_x = (bounds[0] + bounds[2]) / 2
    fire_center_y = (bounds[1] + bounds[3]) / 2
    
    print(f'Fire center: ({fire_center_x:.0f}, {fire_center_y:.0f}) UTM')
    
    # Simulate rasterization to 1197×1020 grid (LiDAR size)
    grid_width, grid_height = 1197, 1020
    cell_size = 20.0
    grid_width_m = grid_width * cell_size
    grid_height_m = grid_height * cell_size
    
    # Calculate grid bounds centered on fire (like calibration does)
    grid_sw_x = fire_center_x - (grid_width_m / 2)
    grid_sw_y = fire_center_y - (grid_height_m / 2)
    grid_ne_x = fire_center_x + (grid_width_m / 2)
    grid_ne_y = fire_center_y + (grid_height_m / 2)
    
    print(f'Grid bounds: SW({grid_sw_x:.0f}, {grid_sw_y:.0f}) NE({grid_ne_x:.0f}, {grid_ne_y:.0f})')
    print(f'Grid size: {grid_width}×{grid_height} = {grid_width * grid_height:,} cells')
    
    # Check if this matches LiDAR bounds
    with open('preprocessed_lidar/lidar_metadata.json', 'r') as f:
        lidar_meta = json.load(f)
    
    lidar_bounds = lidar_meta['fire_bounds']
    print(f'LiDAR bounds: {lidar_bounds}')
    
    # Check alignment
    lidar_sw_x, lidar_sw_y = lidar_bounds[0], lidar_bounds[1]
    lidar_ne_x, lidar_ne_y = lidar_bounds[2], lidar_bounds[3]
    
    offset_x = abs(grid_sw_x - lidar_sw_x)
    offset_y = abs(grid_sw_y - lidar_sw_y)
    
    print(f'Calibration grid offset from LiDAR: ({offset_x:.0f}, {offset_y:.0f}) meters')
    
    if offset_x > 1000 or offset_y > 1000:
        print('❌ MAJOR COORDINATE MISMATCH!')
        print('   Calibration grid and LiDAR grid are in different locations!')
    else:
        print('✅ Calibration grid roughly aligned with LiDAR')
    
    print()
    print('🚨 TARGET DATA SIZE ESTIMATE:')
    print(f'Day 1 fire area: {gdf_utm.geometry.area.sum() / (20*20):.0f} cells')
    print('Recent simulation results: 2,000-11,000 cells')
    ratio = (gdf_utm.geometry.area.sum() / (20*20)) / 6000  # avg simulation size
    print(f'Size ratio (target/simulation): {ratio:.2f}')
    
    if ratio < 0.1:
        print('❌ TARGET MUCH SMALLER than simulation!')
    elif ratio > 10:
        print('❌ TARGET MUCH LARGER than simulation!')
    else:
        print('✅ Target and simulation sizes reasonably matched')
        
except Exception as e:
    print(f'Error in rasterization simulation: {e}')

print()
print('💡 DIAGNOSIS SUMMARY:')
print('1. Check target data size vs simulation size')
print('2. Verify coordinate system alignment')
print('3. Ensure calibration uses correct grid positioning')
print('4. Test with single target to isolate issues')
