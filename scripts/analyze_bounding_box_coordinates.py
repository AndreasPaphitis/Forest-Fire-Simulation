#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Analyze Bounding Box Coordinates

This script calculates the geographic coordinates of the bounding box corners
and compares with the previous full grid implementation.
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def analyze_bounding_box():
    """Analyze the bounding box coordinates and compare with previous implementation."""
    print("🗺️  ANALYZING BOUNDING BOX COORDINATES")
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
            # Calculate bounding box
            lons = [coord[0] for coord in all_coords]
            lats = [coord[1] for coord in all_coords]
            
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)
            
            print(f"\n📍 BOUNDING BOX CORNERS (CRS84 degrees):")
            print(f"   Southwest: ({min_lon:.6f}, {min_lat:.6f})")
            print(f"   Southeast: ({max_lon:.6f}, {min_lat:.6f})")
            print(f"   Northwest: ({min_lon:.6f}, {max_lat:.6f})")
            print(f"   Northeast: ({max_lon:.6f}, {max_lat:.6f})")
            
            print(f"\n📏 BOUNDING BOX DIMENSIONS:")
            print(f"   Longitude range: {min_lon:.6f} to {max_lon:.6f} ({max_lon - min_lon:.6f}°)")
            print(f"   Latitude range:  {min_lat:.6f} to {max_lat:.6f} ({max_lat - min_lat:.6f}°)")
            
            # Convert to meters (approximate)
            # At Tenerife latitude (~28.5°N), 1° ≈ 111,000m
            lon_diff_m = (max_lon - min_lon) * 111000 * 0.88  # 0.88 factor for longitude
            lat_diff_m = (max_lat - min_lat) * 111000
            
            print(f"\n📐 PHYSICAL DIMENSIONS:")
            print(f"   Width:  {lon_diff_m:.0f} m ({lon_diff_m/1000:.1f} km)")
            print(f"   Height: {lat_diff_m:.0f} m ({lat_diff_m/1000:.1f} km)")
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
            
            # Calculate memory usage
            total_cells = final_width * final_height * 12  # 12 layers
            memory_gb = total_cells * 8 / (1024**3)  # 8 bytes per cell
            
            print(f"\n💾 MEMORY ESTIMATION:")
            print(f"   Total cells: {total_cells:,}")
            print(f"   Memory: {memory_gb:.2f} GB")
            print(f"   Status: {'✅ Good' if memory_gb < 1 else '⚠️ High'}")
            
            # COMPARISON WITH PREVIOUS FULL GRID
            print(f"\n" + "="*60)
            print("📊 COMPARISON WITH PREVIOUS FULL GRID IMPLEMENTATION")
            print("="*60)
            
            # Previous full grid (from logs)
            prev_width = 15121
            prev_height = 24741
            prev_layers = 25
            prev_total_cells = prev_width * prev_height * prev_layers
            prev_memory_gb = prev_total_cells * 8 / (1024**3)
            
            # Previous grid area (approximate - full Tenerife)
            prev_area_km2 = 149643.46  # From logs
            
            print(f"\n🔴 PREVIOUS FULL GRID:")
            print(f"   Dimensions: {prev_width} × {prev_height} × {prev_layers}")
            print(f"   Total cells: {prev_total_cells:,} ({prev_total_cells/1e6:.1f}M)")
            print(f"   Memory: {prev_memory_gb:.1f} GB")
            print(f"   Area: {prev_area_km2:.1f} km² (full Tenerife)")
            
            print(f"\n🟢 NEW OPTIMIZED GRID:")
            print(f"   Dimensions: {final_width} × {final_height} × 12")
            print(f"   Total cells: {total_cells:,} ({total_cells/1e6:.1f}M)")
            print(f"   Memory: {memory_gb:.2f} GB")
            print(f"   Area: {(lon_diff_m * lat_diff_m / 1e6):.1f} km² (fire area + buffer)")
            
            print(f"\n📈 IMPROVEMENTS:")
            cell_reduction = (1 - total_cells / prev_total_cells) * 100
            memory_reduction = (1 - memory_gb / prev_memory_gb) * 100
            area_reduction = (1 - (lon_diff_m * lat_diff_m / 1e6) / prev_area_km2) * 100
            
            print(f"   Cell reduction: {cell_reduction:.1f}%")
            print(f"   Memory reduction: {memory_reduction:.1f}%")
            print(f"   Area reduction: {area_reduction:.1f}%")
            print(f"   Focus: From full island to fire-affected area")
            
            print(f"\n🎯 GEOGRAPHIC CONTEXT:")
            print(f"   This bounding box covers the fire-affected area in Tenerife")
            print(f"   Coordinates: {min_lon:.4f}°W to {max_lon:.4f}°W, {min_lat:.4f}°N to {max_lat:.4f}°N")
            print(f"   This represents {(lon_diff_m * lat_diff_m / 1e6 / prev_area_km2 * 100):.1f}% of Tenerife's total area")
            
        else:
            print("❌ No polygon coordinates found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    analyze_bounding_box()
