#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Analyze Terrain Coverage

This script analyzes how our preprocessed terrain data covers the new expanded bounding box area.
"""

import sys
from pathlib import Path
import json
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def analyze_terrain_coverage():
    """Analyze terrain data coverage for the new bounding box."""
    print("🗺️  ANALYZING TERRAIN DATA COVERAGE")
    print("=" * 60)
    
    # Load terrain metadata
    metadata_file = Path("preprocessed_terrain/metadata.json")
    if not metadata_file.exists():
        print("❌ Terrain metadata not found")
        return
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    print(f"📊 TERRAIN METADATA:")
    print(f"   Grid size: {metadata['grid_size']}")
    print(f"   CRS: {metadata['crs']}")
    print(f"   Transform: {metadata['transform']}")
    print(f"   Elevation range: {metadata['elevation_range']}")
    
    # Parse transform matrix manually
    transform_str = metadata['transform'].strip()
    # Extract values using regex-like approach
    import re
    numbers = re.findall(r'[-+]?\d*\.?\d+', transform_str)
    pixel_size_x = float(numbers[0])  # 5.00
    pixel_size_y = abs(float(numbers[4]))  # 5.00 (absolute value of -5.00)
    origin_x = float(numbers[2])  # 310097.50
    origin_y = float(numbers[5])  # 3165002.50
    
    print(f"\n📐 TERRAIN TRANSFORM PARAMETERS:")
    print(f"   Pixel size X: {pixel_size_x} m")
    print(f"   Pixel size Y: {pixel_size_y} m")
    print(f"   Origin X: {origin_x} m")
    print(f"   Origin Y: {origin_y} m")
    
    # Calculate terrain extent
    terrain_width = metadata['grid_size'][0] * pixel_size_x
    terrain_height = metadata['grid_size'][1] * pixel_size_y
    terrain_max_x = origin_x + terrain_width
    terrain_max_y = origin_y + terrain_height
    
    print(f"\n🗺️  TERRAIN EXTENT (EPSG:25828):")
    print(f"   Southwest: ({origin_x:.0f}, {origin_y:.0f})")
    print(f"   Northeast: ({terrain_max_x:.0f}, {terrain_max_y:.0f})")
    print(f"   Width: {terrain_width:.0f} m")
    print(f"   Height: {terrain_height:.0f} m")
    print(f"   Area: {(terrain_width * terrain_height / 1e6):.1f} km²")
    
    # Our new bounding box coordinates (from previous analysis)
    # Convert from CRS84 to EPSG:25828 (approximate)
    # Southwest: (-16.596376, 28.286242)
    # Northeast: (-16.375075, 28.471462)
    
    # Approximate conversion factors for Tenerife
    # This is a rough conversion - in practice we'd use proper CRS transformation
    lon_to_x_factor = 111000 * 0.88  # meters per degree longitude
    lat_to_y_factor = 111000  # meters per degree latitude
    
    # Reference point (approximate center of Tenerife)
    ref_lon = -16.5
    ref_lat = 28.3
    ref_x = 320000  # Approximate EPSG:25828 X coordinate
    ref_y = 3160000  # Approximate EPSG:25828 Y coordinate
    
    # Convert our bounding box to EPSG:25828
    bbox_sw_lon, bbox_sw_lat = -16.596376, 28.286242
    bbox_ne_lon, bbox_ne_lat = -16.375075, 28.471462
    
    # Calculate offsets from reference
    sw_x = ref_x + (bbox_sw_lon - ref_lon) * lon_to_x_factor
    sw_y = ref_y + (bbox_sw_lat - ref_lat) * lat_to_y_factor
    ne_x = ref_x + (bbox_ne_lon - ref_lon) * lon_to_x_factor
    ne_y = ref_y + (bbox_ne_lat - ref_lat) * lat_to_y_factor
    
    print(f"\n🎯 NEW BOUNDING BOX (APPROXIMATE EPSG:25828):")
    print(f"   Southwest: ({sw_x:.0f}, {sw_y:.0f})")
    print(f"   Northeast: ({ne_x:.0f}, {ne_y:.0f})")
    print(f"   Width: {ne_x - sw_x:.0f} m")
    print(f"   Height: {ne_y - sw_y:.0f} m")
    print(f"   Area: {((ne_x - sw_x) * (ne_y - sw_y) / 1e6):.1f} km²")
    
    # Check if bounding box is within terrain extent
    bbox_within_terrain = (
        sw_x >= origin_x and sw_y >= origin_y and
        ne_x <= terrain_max_x and ne_y <= terrain_max_y
    )
    
    print(f"\n🔍 COVERAGE ANALYSIS:")
    print(f"   Bounding box within terrain: {'✅ YES' if bbox_within_terrain else '❌ NO'}")
    
    if bbox_within_terrain:
        print(f"   ✅ Full coverage available")
        print(f"   ✅ All terrain layers will work")
        print(f"   ✅ Elevation, slope, aspect, barranco data available")
        print(f"   ✅ Wind channeling and depression data available")
    else:
        print(f"   ⚠️  Partial or no coverage")
        print(f"   ⚠️  May need to extend terrain processing")
        
        # Calculate overlap
        overlap_x_min = max(sw_x, origin_x)
        overlap_y_min = max(sw_y, origin_y)
        overlap_x_max = min(ne_x, terrain_max_x)
        overlap_y_max = min(ne_y, terrain_max_y)
        
        if overlap_x_max > overlap_x_min and overlap_y_max > overlap_y_min:
            overlap_area = (overlap_x_max - overlap_x_min) * (overlap_y_max - overlap_y_min) / 1e6
            bbox_area = (ne_x - sw_x) * (ne_y - sw_y) / 1e6
            coverage_percent = (overlap_area / bbox_area) * 100
            print(f"   📊 Coverage: {coverage_percent:.1f}% ({overlap_area:.1f} km² of {bbox_area:.1f} km²)")
        else:
            print(f"   ❌ No overlap - terrain data completely outside bounding box")
    
    # Calculate grid indices for the bounding box
    if bbox_within_terrain:
        # Convert to grid indices
        sw_col = int((sw_x - origin_x) / pixel_size_x)
        sw_row = int((origin_y - sw_y) / pixel_size_y)  # Note: Y is inverted
        ne_col = int((ne_x - origin_x) / pixel_size_x)
        ne_row = int((origin_y - ne_y) / pixel_size_y)
        
        grid_width = ne_col - sw_col
        grid_height = ne_row - sw_row
        
        print(f"\n🎯 GRID INDICES FOR BOUNDING BOX:")
        print(f"   Column range: {sw_col} to {ne_col} ({grid_width} cells)")
        print(f"   Row range: {sw_row} to {ne_row} ({grid_height} cells)")
        print(f"   Total cells: {grid_width * grid_height:,}")
        
        # Compare with our calculated grid size
        expected_width = 1189  # From our previous calculation
        expected_height = 1130
        
        print(f"\n📊 GRID SIZE COMPARISON:")
        print(f"   Expected (from bounding box): {expected_width} × {expected_height}")
        print(f"   Available (from terrain): {grid_width} × {grid_height}")
        print(f"   Match: {'✅ YES' if abs(grid_width - expected_width) < 10 and abs(grid_height - expected_height) < 10 else '⚠️ CLOSE'}")
    
    print(f"\n💡 RECOMMENDATIONS:")
    if bbox_within_terrain:
        print(f"   ✅ Use existing terrain data - full coverage available")
        print(f"   ✅ Extract subset for bounding box area")
        print(f"   ✅ All preprocessing layers available")
    else:
        print(f"   ⚠️  Extend terrain processing to cover bounding box")
        print(f"   ⚠️  May need to reprocess LiDAR data")
        print(f"   ⚠️  Check if LiDAR coverage extends to bounding box area")

if __name__ == "__main__":
    analyze_terrain_coverage()
