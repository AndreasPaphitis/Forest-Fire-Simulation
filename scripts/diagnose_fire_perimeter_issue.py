#!/usr/bin/env python3
"""
Diagnose Fire Perimeter Issue

This script examines the fire perimeter data loading and coordinate system
alignment to identify why objective values are 0.0 despite successful simulations.
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def diagnose_fire_perimeter_issue():
    """Diagnose the fire perimeter issue step by step."""
    print("🔍 DIAGNOSE FIRE PERIMETER ISSUE")
    print("=" * 60)
    
    # Step 1: Examine EMSR data structure
    print("\n📁 Step 1: Examining EMSR Data Structure")
    emsr_dir = Path("EMSR Delineations")
    if not emsr_dir.exists():
        print(f"❌ EMSR directory not found: {emsr_dir}")
        return False
    
    print(f"✅ EMSR directory found: {emsr_dir}")
    
    # List all day directories
    day_dirs = [d for d in emsr_dir.iterdir() if d.is_dir() and d.name.startswith("Day")]
    print(f"📅 Found {len(day_dirs)} day directories:")
    for day_dir in sorted(day_dirs):
        print(f"   {day_dir.name}")
    
    # Step 2: Examine specific fire perimeter file
    print("\n🗺️  Step 2: Examining Fire Perimeter File")
    target_file = Path("EMSR Delineations/Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.json")
    
    if not target_file.exists():
        print(f"❌ Target file not found: {target_file}")
        return False
    
    print(f"✅ Target file found: {target_file}")
    print(f"   File size: {target_file.stat().st_size / 1024:.1f} KB")
    
    # Step 3: Load and examine the GeoJSON data
    print("\n📊 Step 3: Loading GeoJSON Data")
    try:
        import geopandas as gpd
        
        # Load the GeoJSON file
        gdf = gpd.read_file(target_file)
        print(f"✅ GeoJSON loaded successfully")
        print(f"   CRS: {gdf.crs}")
        print(f"   Number of features: {len(gdf)}")
        print(f"   Geometry types: {gdf.geometry.geom_type.unique()}")
        
        # Examine bounds
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        print(f"   Bounds: {bounds}")
        print(f"   Width: {bounds[2] - bounds[0]:.0f} m")
        print(f"   Height: {bounds[3] - bounds[1]:.0f} m")
        
        # Calculate area
        if gdf.crs != "EPSG:25828":
            print(f"   Converting CRS from {gdf.crs} to EPSG:25828")
            gdf_utm = gdf.to_crs("EPSG:25828")
        else:
            gdf_utm = gdf
        
        area_ha = gdf_utm.geometry.area.sum() / 10000
        print(f"   Area: {area_ha:.1f} hectares")
        
    except Exception as e:
        print(f"❌ Error loading GeoJSON: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Test target data preparation
    print("\n🔄 Step 4: Testing Target Data Preparation")
    try:
        from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
        
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=8,
            workers=1,
            grid_search_points=2
        )
        
        # Create calibration target
        from src.core.calibration.calibration_config import CalibrationTarget
        target = CalibrationTarget(
            fire_perimeter_path=str(target_file),
            weight=1.0
        )
        
        # Test with different grid sizes
        test_grid_sizes = [(100, 100), (500, 500), (609, 609)]
        
        for grid_size in test_grid_sizes:
            print(f"\n   Testing grid size: {grid_size}")
            try:
                target_data = calibrator._prepare_target_data([target], grid_size=grid_size)
                
                if target_data and 'fire_perimeter' in target_data:
                    fire_perim = target_data['fire_perimeter']
                    
                    # Get fire cells count
                    if hasattr(fire_perim, 'toarray'):
                        fire_cells = np.sum(fire_perim.toarray() > 0)
                        is_sparse = True
                    else:
                        fire_cells = np.sum(fire_perim > 0)
                        is_sparse = False
                    
                    print(f"     ✅ Target data prepared: {fire_cells:,} fire cells")
                    print(f"     Storage: {'Sparse' if is_sparse else 'Dense'}")
                    
                    # Check if fire cells are in the expected location
                    if hasattr(fire_perim, 'toarray'):
                        fire_grid = fire_perim.toarray()
                    else:
                        fire_grid = fire_perim
                    
                    # Find fire cell locations
                    fire_indices = np.where(fire_grid > 0)
                    if len(fire_indices[0]) > 0:
                        min_x, max_x = fire_indices[0].min(), fire_indices[0].max()
                        min_y, max_y = fire_indices[1].min(), fire_indices[1].max()
                        print(f"     Fire bounds: X({min_x}-{max_x}), Y({min_y}-{max_y})")
                        
                        # Check if fire is near the center (expected ignition point)
                        center_x, center_y = grid_size[0] // 2, grid_size[1] // 2
                        ignition_x, ignition_y = 395, 377  # Expected ignition point
                        
                        print(f"     Grid center: ({center_x}, {center_y})")
                        print(f"     Expected ignition: ({ignition_x}, {ignition_y})")
                        
                        # Check if fire overlaps with ignition area
                        ignition_area = fire_grid[max(0, ignition_x-10):min(grid_size[0], ignition_x+10),
                                                max(0, ignition_y-10):min(grid_size[1], ignition_y+10)]
                        ignition_fire_cells = np.sum(ignition_area > 0)
                        print(f"     Fire cells near ignition: {ignition_fire_cells}")
                        
                        if ignition_fire_cells == 0:
                            print(f"     ⚠️  WARNING: No fire cells near ignition point!")
                        else:
                            print(f"     ✅ Fire cells found near ignition point")
                    else:
                        print(f"     ❌ No fire cells found in grid")
                        
                else:
                    print(f"     ❌ Target data preparation failed")
                    
            except Exception as e:
                print(f"     ❌ Error with grid size {grid_size}: {e}")
        
    except Exception as e:
        print(f"❌ Error in target data preparation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Test coordinate system alignment
    print("\n🎯 Step 5: Testing Coordinate System Alignment")
    try:
        # Calculate expected grid position for the fire
        cell_size = 20.0  # 20m resolution
        grid_width, grid_height = 609, 609
        
        # Calculate grid bounds
        grid_width_m = grid_width * cell_size
        grid_height_m = grid_height * cell_size
        
        # Center the fire area in the simulation grid
        fire_center_x = (bounds[0] + bounds[2]) / 2
        fire_center_y = (bounds[1] + bounds[3]) / 2
        
        # Calculate grid bounds centered on fire
        grid_sw_x = fire_center_x - (grid_width_m / 2)
        grid_sw_y = fire_center_y - (grid_height_m / 2)
        grid_ne_x = fire_center_x + (grid_width_m / 2)
        grid_ne_y = fire_center_y + (grid_height_m / 2)
        
        print(f"   Fire center: ({fire_center_x:.0f}, {fire_center_y:.0f})")
        print(f"   Grid bounds: SW({grid_sw_x:.0f}, {grid_sw_y:.0f}) NE({grid_ne_x:.0f}, {grid_ne_y:.0f})")
        print(f"   Grid size: {grid_width_m:.0f}m × {grid_height_m:.0f}m")
        
        # Check if ignition point is within grid bounds
        ignition_x_m = 395 * cell_size + grid_sw_x
        ignition_y_m = 377 * cell_size + grid_sw_y
        
        print(f"   Ignition point (m): ({ignition_x_m:.0f}, {ignition_y_m:.0f})")
        
        if (grid_sw_x <= ignition_x_m <= grid_ne_x and 
            grid_sw_y <= ignition_y_m <= grid_ne_y):
            print(f"   ✅ Ignition point is within grid bounds")
        else:
            print(f"   ❌ Ignition point is outside grid bounds!")
            print(f"   This could explain why fire doesn't spread!")
        
    except Exception as e:
        print(f"❌ Error in coordinate system test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Test objective function with known data
    print("\n🧪 Step 6: Testing Objective Function")
    try:
        from src.core.calibration.objective_functions import SpatialSimilarityObjective
        
        # Create a simple test case
        test_target = np.zeros((609, 609))
        test_predicted = np.zeros((609, 609))
        
        # Add some fire to both (simple test)
        test_target[300:400, 300:400] = 1  # 100x100 fire area
        test_predicted[350:450, 350:450] = 1  # 100x100 fire area, slightly offset
        
        # Calculate overlap
        overlap = np.sum((test_target > 0) & (test_predicted > 0))
        union = np.sum((test_target > 0) | (test_predicted > 0))
        
        print(f"   Test target cells: {np.sum(test_target > 0)}")
        print(f"   Test predicted cells: {np.sum(test_predicted > 0)}")
        print(f"   Overlap: {overlap}")
        print(f"   Union: {union}")
        
        if union > 0:
            jaccard = overlap / union
            print(f"   Jaccard index: {jaccard:.4f}")
        else:
            print(f"   Jaccard index: 0.0 (no overlap)")
        
        # Test objective function
        objective = SpatialSimilarityObjective()
        result = objective.evaluate(test_predicted, test_target)
        
        print(f"   Objective function result: {result.value:.8f}")
        print(f"   Is valid: {result.is_valid}")
        
        if result.value > 0.0:
            print(f"   ✅ Objective function works correctly")
        else:
            print(f"   ❌ Objective function returns 0.0")
            
    except Exception as e:
        print(f"❌ Error in objective function test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n🎯 DIAGNOSIS COMPLETE")
    print(f"=" * 60)
    print(f"Key findings:")
    print(f"1. EMSR data structure and loading")
    print(f"2. Coordinate system alignment")
    print(f"3. Grid size and fire positioning")
    print(f"4. Objective function behavior")
    print(f"5. Potential ignition point misalignment")
    
    return True

if __name__ == "__main__":
    diagnose_fire_perimeter_issue()
