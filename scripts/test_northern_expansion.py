#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Northern Expansion Logic

This script tests the northern expansion logic for the bounding box.
"""

def test_northern_expansion():
    """Test the northern expansion logic."""
    print("🗺️  TESTING NORTHERN EXPANSION LOGIC")
    print("=" * 50)
    
    # Simulate the bounds calculation from the actual method
    # Original bounds: [minx, miny, maxx, maxy]
    bounds = (1000.0, 2000.0, 3000.0, 4000.0)  # Example bounds in meters
    
    print(f"📍 Original bounds: {bounds}")
    print(f"   minx: {bounds[0]}, miny: {bounds[1]}, maxx: {bounds[2]}, maxy: {bounds[3]}")
    
    # Calculate original height
    height_m_original = bounds[3] - bounds[1]  # maxy - miny
    print(f"\n📏 Original height: {height_m_original:.0f} m")
    
    # Move northern side 10% up for additional buffer
    north_expansion = height_m_original * 0.10
    new_bounds = (bounds[0], bounds[1], bounds[2], bounds[3] + north_expansion)
    
    print(f"\n🔄 Northern expansion:")
    print(f"   10% expansion: {north_expansion:.0f} m")
    print(f"   New maxy: {new_bounds[3]:.0f} m")
    
    print(f"\n📍 New bounds: {new_bounds}")
    print(f"   minx: {new_bounds[0]}, miny: {new_bounds[1]}, maxx: {new_bounds[2]}, maxy: {new_bounds[3]}")
    
    # Calculate new dimensions
    width_m = new_bounds[2] - new_bounds[0]  # maxx - minx
    height_m = new_bounds[3] - new_bounds[1]  # maxy - miny
    
    print(f"\n📐 New dimensions:")
    print(f"   Width: {width_m:.0f} m")
    print(f"   Height: {height_m:.0f} m")
    print(f"   Area: {(width_m * height_m / 1e6):.2f} km²")
    
    # Calculate grid size
    cell_size_m = 20.0
    grid_width = int(width_m / cell_size_m)
    grid_height = int(height_m / cell_size_m)
    
    print(f"\n🎯 Grid size (20m resolution):")
    print(f"   Width: {grid_width} cells")
    print(f"   Height: {grid_height} cells")
    print(f"   Total: {grid_width * grid_height:,} cells")
    
    # Add 10% buffer
    buffer_width = int(grid_width * 0.1)
    buffer_height = int(grid_height * 0.1)
    final_width = grid_width + buffer_width
    final_height = grid_height + buffer_height
    
    print(f"\n🛡️  With 10% buffer:")
    print(f"   Width: {final_width} cells")
    print(f"   Height: {final_height} cells")
    print(f"   Total: {final_width * final_height:,} cells")
    
    # Calculate memory usage
    total_cells = final_width * final_height * 12  # 12 layers
    memory_gb = total_cells * 8 / (1024**3)  # 8 bytes per cell
    
    print(f"\n💾 Memory estimation:")
    print(f"   Total cells: {total_cells:,}")
    print(f"   Memory: {memory_gb:.2f} GB")
    
    print(f"\n✅ Northern expansion logic test completed!")

if __name__ == "__main__":
    test_northern_expansion()
