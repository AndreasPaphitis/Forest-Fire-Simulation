#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Dynamic Grid Size Calculation

This script tests the new dynamic grid size calculation based on Day 4 fire perimeter.
It shows the area size that will be used for the simulation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_dynamic_grid_size():
    """Test the dynamic grid size calculation."""
    print("🧪 TESTING DYNAMIC GRID SIZE CALCULATION")
    print("=" * 60)
    
    try:
        from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
        
        # Create calibrator instance
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=60,
            grid_search_points=3,
            experiment_name="test_dynamic_grid"
        )
        
        print("✅ Calibrator created successfully")
        print(f"📁 EMSR directory: {calibrator.base_directory}")
        
        # Test grid size calculation
        print("\n🔍 CALCULATING OPTIMAL GRID SIZE:")
        print("-" * 40)
        
        optimal_grid_size = calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
        grid_width, grid_height = optimal_grid_size
        
        # Calculate area in different units
        cell_size_m = 20.0  # 20m resolution
        grid_width_m = grid_width * cell_size_m
        grid_height_m = grid_height * cell_size_m
        total_area_m2 = grid_width_m * grid_height_m
        total_area_km2 = total_area_m2 / 1_000_000
        total_area_ha = total_area_m2 / 10_000
        
        # Calculate total cells
        num_layers = 12
        total_cells = grid_width * grid_height * num_layers
        
        print(f"🎯 Grid dimensions: {grid_width} × {grid_height} cells")
        print(f"📏 Physical size: {grid_width_m:.0f}m × {grid_height_m:.0f}m")
        print(f"📊 Total area: {total_area_km2:.2f} km² ({total_area_ha:.1f} ha)")
        print(f"🔢 Total cells: {total_cells:,} ({total_cells/1e6:.1f}M)")
        
        # Compare with original full Tenerife
        original_width = 15121
        original_height = 24741
        original_layers = 25
        original_cells = original_width * original_height * original_layers
        original_area_km2 = (original_width * 20) * (original_height * 20) / 1_000_000
        
        print(f"\n📈 COMPARISON WITH ORIGINAL:")
        print("-" * 30)
        print(f"Original grid: {original_width} × {original_height} × {original_layers}")
        print(f"Original area: {original_area_km2:.2f} km²")
        print(f"Original cells: {original_cells:,} ({original_cells/1e6:.1f}M)")
        print(f"Reduction: {(1 - total_cells/original_cells)*100:.1f}% fewer cells")
        print(f"Area ratio: {total_area_km2/original_area_km2:.1%} of original area")
        
        # Memory estimation
        bytes_per_cell = 10  # Conservative estimate
        memory_gb = (total_cells * bytes_per_cell) / (1024**3)
        
        print(f"\n💾 MEMORY ESTIMATION:")
        print("-" * 25)
        print(f"Estimated memory: ~{memory_gb:.1f} GB")
        print(f"Memory efficiency: {'✅ Good' if memory_gb < 10 else '⚠️  High'}")
        
        # Show what the area represents
        print(f"\n🗺️  AREA REPRESENTATION:")
        print("-" * 30)
        print(f"This area represents approximately:")
        print(f"   • {total_area_km2:.1f} km² of Tenerife")
        print(f"   • About {total_area_km2/100:.1f}% of Tenerife's total area")
        print(f"   • Focused on the fire-affected region with 10% buffer")
        print(f"   • Much more manageable than the full island simulation")
        
        # Show different buffer options
        print(f"\n🔧 BUFFER OPTIONS:")
        print("-" * 20)
        for buffer_percent in [5, 10, 15, 20]:
            test_size = calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=buffer_percent)
            test_width, test_height = test_size
            test_cells = test_width * test_height * 12
            test_area_km2 = (test_width * 20) * (test_height * 20) / 1_000_000
            print(f"   {buffer_percent}% buffer: {test_width}×{test_height} cells, {test_area_km2:.1f} km², {test_cells/1e6:.1f}M cells")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dynamic_grid_size()
    if success:
        print(f"\n✅ Dynamic grid size calculation test completed successfully!")
    else:
        print(f"\n❌ Test failed!")
        sys.exit(1)
