#!/usr/bin/env python3

import numpy as np
import geopandas as gpd
from pathlib import Path
import matplotlib.pyplot as plt

print('🔍 SPATIAL ALIGNMENT ANALYSIS')
print('=' * 60)

# 1. Load EMSR Day 1-2 data (calibration targets)
emsr_days = {
    1: "Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp",
    2: "Day 2 (21_08_23)/EMSR685_AOI01_DEL_MONIT01_observedEventA_v1.shp"
}

print('📊 EMSR TARGET DATA ANALYSIS:')
emsr_bounds = {}
emsr_centroids = {}

for day, shapefile_path in emsr_days.items():
    full_path = Path("EMSR Delineations") / shapefile_path
    if full_path.exists():
        try:
            gdf = gpd.read_file(full_path)
            
            # Transform to UTM Zone 28N for accurate measurements
            gdf_utm = gdf.to_crs(epsg=32628)
            
            bounds = gdf_utm.total_bounds  # [minx, miny, maxx, maxy]
            centroid_x = (bounds[0] + bounds[2]) / 2
            centroid_y = (bounds[1] + bounds[3]) / 2
            
            area_m2 = gdf_utm.geometry.area.sum()
            area_ha = area_m2 / 10000
            
            emsr_bounds[day] = bounds
            emsr_centroids[day] = (centroid_x, centroid_y)
            
            print(f'Day {day}:')
            print(f'  Bounds (UTM): {bounds}')
            print(f'  Centroid (UTM): ({centroid_x:.0f}, {centroid_y:.0f})')
            print(f'  Fire area: {area_ha:.1f} hectares')
            print(f'  Features: {len(gdf)}')
            print()
            
        except Exception as e:
            print(f'Day {day}: Error loading - {e}')
    else:
        print(f'Day {day}: File not found - {full_path}')

# 2. Analyze simulation grid setup
print('🎯 SIMULATION GRID ANALYSIS:')
print('Grid size: 609 × 609 cells')
print('Resolution: 20m per cell')
print('Total area: 12.18 × 12.18 km = 148.4 km²')

# Current ignition point
ignition_grid = (395, 377, 0)  # Grid coordinates
ignition_utm_x = ignition_grid[0] * 20  # Convert to meters
ignition_utm_y = ignition_grid[1] * 20

print(f'Ignition point (grid): ({ignition_grid[0]}, {ignition_grid[1]})')
print(f'Ignition point (relative UTM): ({ignition_utm_x}, {ignition_utm_y})')
print()

# 3. Check spatial alignment
print('🚨 SPATIAL ALIGNMENT CHECK:')

if emsr_centroids:
    # Use Day 1 or Day 2 centroid as reference
    day_to_check = 1 if 1 in emsr_centroids else 2
    emsr_centroid = emsr_centroids[day_to_check]
    
    print(f'EMSR Day {day_to_check} centroid: ({emsr_centroid[0]:.0f}, {emsr_centroid[1]:.0f}) UTM')
    print(f'Simulation ignition (relative): ({ignition_utm_x}, {ignition_utm_y}) relative')
    print()
    
    print('💡 ALIGNMENT ISSUES:')
    print('1. EMSR data is in ABSOLUTE UTM coordinates (real-world)')
    print('2. Simulation grid is RELATIVE coordinates (0,0 at grid origin)')
    print('3. We need to check if simulation grid is positioned over EMSR area')
    print()
    
    # Check if we can find simulation grid positioning
    try:
        # Look for any configuration that shows absolute positioning
        from src.config.config_tools import ModelConfig
        config = ModelConfig()
        print(f'Model resolution: {config.model_resolution}m')
        print(f'Grid size: {config.grid_size}')
        
        # Calculate simulation grid bounds if we knew the absolute origin
        grid_width_m = 609 * 20  # 12,180m
        grid_height_m = 609 * 20  # 12,180m
        
        print(f'Simulation grid size: {grid_width_m}m × {grid_height_m}m')
        print()
        
        print('🔍 CRITICAL QUESTIONS:')
        print('A) Where is the simulation grid (0,0) positioned in real UTM coordinates?')
        print('B) Does the simulation grid cover the EMSR fire area?')
        print('C) Is the ignition point at the real fire origin?')
        print()
        
        # Calculate distance if we assume simulation origin at EMSR bounds
        if day_to_check in emsr_bounds:
            emsr_bound = emsr_bounds[day_to_check]
            emsr_width = emsr_bound[2] - emsr_bound[0]
            emsr_height = emsr_bound[3] - emsr_bound[1]
            
            print(f'EMSR fire extent: {emsr_width:.0f}m × {emsr_height:.0f}m')
            print(f'Simulation grid: {grid_width_m}m × {grid_height_m}m')
            
            if emsr_width < grid_width_m and emsr_height < grid_height_m:
                print('✅ Simulation grid is large enough to contain EMSR fire')
            else:
                print('❌ Simulation grid may be too small for EMSR fire')
            
    except Exception as e:
        print(f'Error loading config: {e}')

else:
    print('❌ Could not load EMSR data for alignment check')

print()
print('💡 NEXT STEPS FOR ALIGNMENT VERIFICATION:')
print('1. Check preprocessing scripts for grid positioning')
print('2. Verify LiDAR bounds vs EMSR bounds')
print('3. Check if ignition point corresponds to real fire origin')
print('4. Create visualization overlay of simulation grid vs EMSR data')
