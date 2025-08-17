#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Coordinate Conversion Fixes

This script tests the coordinate conversion fixes in the dynamic grid sizing.
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_coordinate_conversion():
    """Test coordinate conversion from CRS84 to EPSG:25828."""
    print("🧪 TESTING COORDINATE CONVERSION FIXES")
    print("=" * 50)
    
    # Test with Day 4 JSON file
    day4_json = Path("EMSR Delineations/Day 4 (26_08_23)/EMSR685_AOI01_GRA_PRODUCT_observedEventA_v1.json")
    
    if not day4_json.exists():
        print("❌ Day 4 JSON file not found")
        return
    
    print(f"📄 Reading: {day4_json}")
    
    try:
        with open(day4_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ JSON loaded successfully")
        print(f"📊 CRS: {data.get('crs', {}).get('properties', {}).get('name', 'Unknown')}")
        print(f"🔥 Features: {len(data.get('features', []))}")
        
        # Get bounding box from all features
        all_coords = []
        for feature in data.get('features', []):
            if feature.get('geometry', {}).get('type') == 'Polygon':
                coords = feature['geometry']['coordinates'][0]  # First ring
                all_coords.extend(coords)
        
        if all_coords:
            # Calculate bounding box
            lons = [coord[0] for coord in all_coords]
            lats = [coord[1] for coord in all_coords]
            
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)
            
            print(f"\n📍 BOUNDING BOX (CRS84 degrees):")
            print(f"   Longitude: {min_lon:.6f} to {max_lon:.6f}")
            print(f"   Latitude:  {min_lat:.6f} to {max_lat:.6f}")
            
            # Convert to meters (approximate)
            # At Tenerife latitude (~28.5°N), 1° ≈ 111,000m
            lon_diff_m = (max_lon - min_lon) * 111000 * 0.88  # 0.88 factor for longitude
            lat_diff_m = (max_lat - min_lat) * 111000
            
            print(f"\n📏 DIMENSIONS (approximate meters):")
            print(f"   Width:  {lon_diff_m:.0f} m")
            print(f"   Height: {lat_diff_m:.0f} m")
            print(f"   Area:   {(lon_diff_m * lat_diff_m / 1e6):.2f} km²")
            
            # Calculate grid size with 20m resolution
            grid_width = int(lon_diff_m / 20) + 1
            grid_height = int(lat_diff_m / 20) + 1
            
            print(f"\n🎯 GRID SIZE (20m resolution):")
            print(f"   Width:  {grid_width} cells")
            print(f"   Height: {grid_height} cells")
            print(f"   Total:  {grid_width * grid_height:,} cells")
            
            # Add 10% buffer
            buffer_width = int(grid_width * 0.1)
            buffer_height = int(grid_height * 0.1)
            final_width = grid_width + buffer_width
            final_height = grid_height + buffer_height
            
            print(f"\n🛡️  WITH 10% BUFFER:")
            print(f"   Width:  {final_width} cells")
            print(f"   Height: {final_height} cells")
            print(f"   Total:  {final_width * final_height:,} cells")
            
        else:
            print("❌ No polygon coordinates found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_coordinate_conversion()
