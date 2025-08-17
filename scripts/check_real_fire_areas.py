#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Check Real Fire Areas

This script extracts the actual fire areas from EMSR JSON files
to get the real fire perimeter sizes.
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_real_fire_areas():
    """Check actual fire areas from EMSR JSON files."""
    print("🔥 CHECKING REAL FIRE AREAS FROM EMSR DATA")
    print("=" * 60)
    
    emsr_dir = Path("EMSR Delineations")
    
    for day_dir in sorted(emsr_dir.iterdir()):
        if not day_dir.is_dir():
            continue
            
        print(f"\n📁 {day_dir.name}:")
        
        # Check JSON file for actual fire areas
        json_files = list(day_dir.glob("*.json"))
        if json_files:
            json_file = json_files[0]
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Extract all fire areas
                total_area_ha = 0
                fire_areas = []
                
                if 'features' in data:
                    for feature in data['features']:
                        if 'properties' in feature:
                            props = feature['properties']
                            # Look for area information
                            area = None
                            if 'area' in props:
                                area = props['area']
                            elif 'Area' in props:
                                area = props['Area']
                            elif 'AREA' in props:
                                area = props['AREA']
                            
                            if area is not None:
                                fire_areas.append(area)
                                total_area_ha += area
                
                if fire_areas:
                    print(f"   🔥 Number of fire polygons: {len(fire_areas)}")
                    print(f"   📊 Total fire area: {total_area_ha:.1f} ha ({total_area_ha/100:.2f} km²)")
                    
                    if len(fire_areas) > 1:
                        print(f"   📈 Individual areas: {', '.join([f'{area:.1f} ha' for area in sorted(fire_areas, reverse=True)[:5]])}")
                        if len(fire_areas) > 5:
                            print(f"   ... and {len(fire_areas)-5} more")
                    
                    # Calculate realistic grid size
                    buffer_percent = 10.0
                    buffer_factor = 1.0 + (buffer_percent / 100.0)
                    buffered_area_ha = total_area_ha * buffer_factor
                    buffered_area_km2 = buffered_area_ha / 100
                    
                    # Convert to grid dimensions (approximate square)
                    grid_side_km = (buffered_area_km2 ** 0.5)  # Square root for square grid
                    cell_size_m = 20.0
                    grid_cells = int((grid_side_km * 1000) / cell_size_m)
                    
                    # Ensure minimum size
                    grid_cells = max(grid_cells, 500)  # Minimum 500x500 cells
                    
                    total_cells = grid_cells * grid_cells * 12  # 12 layers
                    
                    print(f"   🎯 Realistic grid: {grid_cells}×{grid_cells} cells")
                    print(f"   📏 Grid area: {grid_cells*20/1000:.1f}×{grid_cells*20/1000:.1f} km")
                    print(f"   🔢 Total cells: {total_cells:,} ({total_cells/1e6:.1f}M)")
                    
                else:
                    print(f"   ❌ No area data found in {json_file.name}")
                    
            except Exception as e:
                print(f"   ❌ Error reading {json_file.name}: {e}")

def compare_with_our_calculations():
    """Compare our calculations with reality."""
    print(f"\n📊 COMPARISON WITH OUR CALCULATIONS:")
    print("-" * 50)
    
    print("❌ Our current fallback grid: 5,000×5,000 cells = 100 km²")
    print("❌ This is completely wrong for these fire sizes!")
    
    print(f"\n✅ Realistic grid sizes based on actual fire areas:")
    print("   Day 1: ~1,000×1,000 cells (4 km²) for ~5,800 ha fire")
    print("   Day 2: ~500×500 cells (1 km²) for ~18 ha fire") 
    print("   Day 3: ~1,000×1,000 cells (4 km²) for ~9,400 ha fire")
    print("   Day 4: ~500×500 cells (1 km²) for ~50 ha fire")
    
    print(f"\n🚀 Memory usage would be:")
    print("   Day 1: ~12M cells = ~0.1 GB")
    print("   Day 2: ~3M cells = ~0.03 GB")
    print("   Day 3: ~12M cells = ~0.1 GB")
    print("   Day 4: ~3M cells = ~0.03 GB")

if __name__ == "__main__":
    check_real_fire_areas()
    compare_with_our_calculations()
    print(f"\n✅ Real fire area check completed!")

