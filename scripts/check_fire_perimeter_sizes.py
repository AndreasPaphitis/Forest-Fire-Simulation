#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Check Fire Perimeter Sizes

This script checks the actual fire perimeter sizes from EMSR data files
to validate our dynamic grid size calculations.
"""

import sys
from pathlib import Path
import json
import math

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def degrees_to_meters(lat_deg, lon_deg):
    """Convert degrees to meters at Tenerife's latitude (~28°N)."""
    # Earth's radius in meters
    R = 6371000
    
    # Convert to radians
    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)
    
    # Calculate meters per degree at this latitude
    meters_per_degree_lat = R * math.pi / 180  # ~111,000 m/degree
    meters_per_degree_lon = R * math.cos(lat_rad) * math.pi / 180  # ~98,000 m/degree at 28°N
    
    return meters_per_degree_lat, meters_per_degree_lon

def check_fire_perimeter_sizes():
    """Check actual fire perimeter sizes from EMSR data."""
    print("🔍 CHECKING ACTUAL FIRE PERIMETER SIZES")
    print("=" * 50)
    
    emsr_dir = Path("EMSR Delineations")
    
    for day_dir in sorted(emsr_dir.iterdir()):
        if not day_dir.is_dir():
            continue
            
        print(f"\n📁 {day_dir.name}:")
        
        # Check JSON file for metadata
        json_files = list(day_dir.glob("*.json"))
        if json_files:
            json_file = json_files[0]
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Extract area information if available
                if 'features' in data and data['features']:
                    feature = data['features'][0]
                    if 'properties' in feature:
                        props = feature['properties']
                        area_ha = props.get('area_ha', props.get('Area_ha', props.get('AREA_HA', None)))
                        if area_ha:
                            print(f"   🔥 Fire area: {area_ha:.1f} ha ({area_ha/100:.2f} km²)")
                
                # Calculate bounds from coordinates
                if 'features' in data and data['features']:
                    feature = data['features'][0]
                    if 'geometry' in feature and 'coordinates' in feature['geometry']:
                        coords = feature['geometry']['coordinates'][0]  # First ring
                        if coords:
                            x_coords = [coord[0] for coord in coords]
                            y_coords = [coord[1] for coord in coords]
                            
                            min_x, max_x = min(x_coords), max(x_coords)
                            min_y, max_y = min(y_coords), max(y_coords)
                            
                            # These are longitude (x) and latitude (y) in degrees
                            print(f"   📐 Bounds (degrees): ({min_x:.4f}, {min_y:.4f}) to ({max_x:.4f}, {max_y:.4f})")
                            
                            # Convert to meters
                            center_lat = (min_y + max_y) / 2
                            center_lon = (min_x + max_x) / 2
                            
                            meters_per_degree_lat, meters_per_degree_lon = degrees_to_meters(center_lat, center_lon)
                            
                            width_deg = max_x - min_x
                            height_deg = max_y - min_y
                            
                            width_m = width_deg * meters_per_degree_lon
                            height_m = height_deg * meters_per_degree_lat
                            
                            print(f"   📏 Dimensions: {width_m:.0f}m × {height_m:.0f}m")
                            
                            # Calculate area (approximate rectangle)
                            area_m2 = width_m * height_m
                            area_km2 = area_m2 / 1_000_000
                            area_ha = area_m2 / 10_000
                            
                            print(f"   📊 Calculated area: {area_km2:.2f} km² ({area_ha:.1f} ha)")
                            
                            # Calculate grid size with 10% buffer
                            buffer_percent = 10.0
                            buffer_factor = 1.0 + (buffer_percent / 100.0)
                            buffered_width_m = width_m * buffer_factor
                            buffered_height_m = height_m * buffer_factor
                            
                            cell_size_m = 20.0
                            grid_width = int(buffered_width_m / cell_size_m)
                            grid_height = int(buffered_height_m / cell_size_m)
                            
                            # Ensure minimum size
                            grid_width = max(grid_width, 1000)
                            grid_height = max(grid_height, 1000)
                            
                            total_cells = grid_width * grid_height * 12
                            
                            print(f"   🎯 With 10% buffer: {grid_width}×{grid_height} cells, {total_cells/1e6:.1f}M cells")
                            
            except Exception as e:
                print(f"   ❌ Error reading {json_file.name}: {e}")
        
        # Check file sizes as rough indicators
        shp_files = list(day_dir.glob("*.shp"))
        if shp_files:
            shp_size = shp_files[0].stat().st_size
            print(f"   📄 Shapefile size: {shp_size/1024:.1f} KB")
        
        kmz_files = list(day_dir.glob("*.kmz"))
        if kmz_files:
            kmz_size = kmz_files[0].stat().st_size
            print(f"   📄 KMZ file size: {kmz_size/1024:.1f} KB")

def check_tenerife_total_area():
    """Check what the total Tenerife area should be."""
    print(f"\n🗺️  TENERIFE AREA REFERENCE:")
    print("-" * 30)
    
    # Tenerife actual area
    tenerife_area_km2 = 2034  # Actual Tenerife area
    print(f"🌍 Tenerife total area: {tenerife_area_km2} km²")
    
    # Our current grid area
    current_grid_area_km2 = 10000  # 100km × 100km
    print(f"🎯 Our current grid area: {current_grid_area_km2} km²")
    
    print(f"📊 Our grid is {current_grid_area_km2/tenerife_area_km2:.1f}x larger than Tenerife!")
    print(f"⚠️  This suggests our fallback grid is too large")

if __name__ == "__main__":
    check_fire_perimeter_sizes()
    check_tenerife_total_area()
    print(f"\n✅ Fire perimeter size check completed!")
