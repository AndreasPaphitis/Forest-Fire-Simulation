#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Expanded Bounding Box

This script tests the bounding box with the northern side moved 10% up.
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_expanded_bounding_box():
    """Test bounding box with northern side moved 10% up."""
    print("🗺️  TESTING EXPANDED BOUNDING BOX (NORTH +10%)")
    print("=" * 60)
    
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
            # Calculate original bounding box
            lons = [coord[0] for coord in all_coords]
            lats = [coord[1] for coord in all_coords]
            
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)
            
            print(f"\n📍 ORIGINAL BOUNDING BOX CORNERS:")
            print(f"   Southwest: ({min_lon:.6f}, {min_lat:.6f})")
            print(f"   Southeast: ({max_lon:.6f}, {min_lat:.6f})")
            print(f"   Northwest: ({min_lon:.6f}, {max_lat:.6f})")
            print(f"   Northeast: ({max_lon:.6f}, {max_lat:.6f})")
            
            # Calculate latitude range
            lat_range = max_lat - min_lat
            
            # Move northern side 10% up
            north_expansion = lat_range * 0.10
            new_max_lat = max_lat + north_expansion
            
            print(f"\n🔄 EXPANDING NORTHERN BOUNDARY:")
            print(f"   Original north: {max_lat:.6f}")
            print(f"   Latitude range: {lat_range:.6f}°")
            print(f"   10% expansion: {north_expansion:.6f}°")
            print(f"   New north: {new_max_lat:.6f}")
            
            print(f"\n📍 EXPANDED BOUNDING BOX CORNERS:")
            print(f"   Southwest: ({min_lon:.6f}, {min_lat:.6f})")
            print(f"   Southeast: ({max_lon:.6f}, {min_lat:.6f})")
            print(f"   Northwest: ({min_lon:.6f}, {new_max_lat:.6f})")
            print(f"   Northeast: ({max_lon:.6f}, {new_max_lat:.6f})")
            
            print(f"\n📏 EXPANDED BOUNDING BOX DIMENSIONS:")
            print(f"   Longitude range: {min_lon:.6f} to {max_lon:.6f} ({max_lon - min_lon:.6f}°)")
            print(f"   Latitude range:  {min_lat:.6f} to {new_max_lat:.6f} ({new_max_lat - min_lat:.6f}°)")
            
            # Convert to meters (approximate)
            # At Tenerife latitude (~28.5°N), 1° ≈ 111,000m
            lon_diff_m = (max_lon - min_lon) * 111000 * 0.88  # 0.88 factor for longitude
            lat_diff_m = (new_max_lat - min_lat) * 111000
            
            print(f"\n📐 EXPANDED PHYSICAL DIMENSIONS:")
            print(f"   Width:  {lon_diff_m:.0f} m ({lon_diff_m/1000:.1f} km)")
            print(f"   Height: {lat_diff_m:.0f} m ({lat_diff_m/1000:.1f} km)")
            print(f"   Area:   {(lon_diff_m * lat_diff_m / 1e6):.2f} km²")
            
            # Calculate grid size with 20m resolution
            grid_width = int(lon_diff_m / 20) + 1
            grid_height = int(lat_diff_m / 20) + 1
            
            print(f"\n🎯 EXPANDED GRID SIZE (20m resolution):")
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
            
            # Calculate memory usage
            total_cells = final_width * final_height * 12  # 12 layers
            memory_gb = total_cells * 8 / (1024**3)  # 8 bytes per cell
            
            print(f"\n💾 MEMORY ESTIMATION:")
            print(f"   Total cells: {total_cells:,}")
            print(f"   Memory: {memory_gb:.2f} GB")
            print(f"   Status: {'✅ Good' if memory_gb < 1 else '⚠️ High'}")
            
            # COMPARISON WITH ORIGINAL
            print(f"\n" + "="*60)
            print("📊 COMPARISON: ORIGINAL vs EXPANDED")
            print("="*60)
            
            # Original dimensions
            orig_lat_diff_m = (max_lat - min_lat) * 111000
            orig_grid_height = int(orig_lat_diff_m / 20) + 1
            orig_total_cells = grid_width * orig_grid_height * 12
            orig_memory_gb = orig_total_cells * 8 / (1024**3)
            
            print(f"\n🔴 ORIGINAL BOUNDING BOX:")
            print(f"   Height: {orig_lat_diff_m:.0f} m ({orig_lat_diff_m/1000:.1f} km)")
            print(f"   Grid height: {orig_grid_height} cells")
            print(f"   Total cells: {orig_total_cells:,}")
            print(f"   Memory: {orig_memory_gb:.2f} GB")
            
            print(f"\n🟢 EXPANDED BOUNDING BOX (NORTH +10%):")
            print(f"   Height: {lat_diff_m:.0f} m ({lat_diff_m/1000:.1f} km)")
            print(f"   Grid height: {grid_height} cells")
            print(f"   Total cells: {total_cells:,}")
            print(f"   Memory: {memory_gb:.2f} GB")
            
            print(f"\n📈 CHANGES:")
            height_increase = ((lat_diff_m - orig_lat_diff_m) / orig_lat_diff_m) * 100
            cell_increase = ((total_cells - orig_total_cells) / orig_total_cells) * 100
            memory_increase = ((memory_gb - orig_memory_gb) / orig_memory_gb) * 100
            
            print(f"   Height increase: {height_increase:.1f}%")
            print(f"   Cell increase: {cell_increase:.1f}%")
            print(f"   Memory increase: {memory_increase:.1f}%")
            
            print(f"\n🎯 GEOGRAPHIC CONTEXT:")
            print(f"   Original north boundary: {max_lat:.4f}°N")
            print(f"   New north boundary: {new_max_lat:.4f}°N")
            print(f"   Expansion: {north_expansion:.4f}° ({north_expansion * 111000:.0f} m)")
            print(f"   This provides additional buffer space north of the fire area")
            
        else:
            print("❌ No polygon coordinates found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_expanded_bounding_box()
