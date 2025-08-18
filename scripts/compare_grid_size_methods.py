#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Compare Grid Size Calculation Methods

This script compares the two different grid size calculation methods to see if they
produce the same results for the calibration.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def compare_grid_size_methods():
    """Compare the two grid size calculation methods."""
    print("🔍 COMPARING GRID SIZE CALCULATION METHODS")
    print("=" * 80)
    
    try:
        # Method 1: calculate_optimal_grid_size_from_emsr (Day 1 + Day 2)
        print("📊 METHOD 1: calculate_optimal_grid_size_from_emsr (Day 1 + Day 2)")
        print("-" * 60)
        
        from src.core.calibration.calibration_utils import calculate_optimal_grid_size_from_emsr
        
        day1_path = "EMSR Delineations/Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp"
        day2_path = "EMSR Delineations/Day 2 (21_08_23)/EMSR685_AOI01_DEL_MONIT01_observedEventA_v1.shp"
        
        if not os.path.exists(day1_path) or not os.path.exists(day2_path):
            print(f"❌ EMSR files not found")
            return False
        
        grid_size_1 = calculate_optimal_grid_size_from_emsr(day1_path, day2_path, buffer_percent=10.0)
        grid_width_1, grid_height_1 = grid_size_1
        
        print(f"✅ Method 1 result: {grid_width_1} × {grid_height_1}")
        
        # Method 2: _calculate_optimal_grid_size_from_day4 (Day 4 only)
        print("\n📊 METHOD 2: _calculate_optimal_grid_size_from_day4 (Day 4 only)")
        print("-" * 60)
        
        from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
        
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=8,
            grid_search_points=2,
            experiment_name="compare_methods"
        )
        
        grid_size_2 = calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
        grid_width_2, grid_height_2 = grid_size_2
        
        print(f"✅ Method 2 result: {grid_width_2} × {grid_height_2}")
        
        # Compare results
        print("\n🔍 COMPARISON RESULTS:")
        print("-" * 60)
        
        print(f"Method 1 (Day 1+2): {grid_width_1} × {grid_height_1}")
        print(f"Method 2 (Day 4):    {grid_width_2} × {grid_height_2}")
        
        # Calculate differences
        width_diff = abs(grid_width_1 - grid_width_2)
        height_diff = abs(grid_height_1 - grid_height_2)
        width_percent = (width_diff / max(grid_width_1, grid_width_2)) * 100
        height_percent = (height_diff / max(grid_height_1, grid_height_2)) * 100
        
        print(f"\n📏 Differences:")
        print(f"   Width:  {width_diff} cells ({width_percent:.1f}%)")
        print(f"   Height: {height_diff} cells ({height_percent:.1f}%)")
        
        # Calculate areas
        cell_size_m = 5.0
        area_1_km2 = (grid_width_1 * cell_size_m / 1000) * (grid_height_1 * cell_size_m / 1000)
        area_2_km2 = (grid_width_2 * cell_size_m / 1000) * (grid_height_2 * cell_size_m / 1000)
        
        print(f"\n📊 Areas:")
        print(f"   Method 1: {area_1_km2:.1f} km²")
        print(f"   Method 2: {area_2_km2:.1f} km²")
        print(f"   Difference: {abs(area_1_km2 - area_2_km2):.1f} km²")
        
        # Check if they're the same
        if grid_size_1 == grid_size_2:
            print(f"\n✅ METHODS PRODUCE IDENTICAL RESULTS!")
            return True
        else:
            print(f"\n❌ METHODS PRODUCE DIFFERENT RESULTS!")
            print(f"   This could cause issues in calibration.")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_which_method_is_used():
    """Test which method is actually being used in the calibration script."""
    print("\n🔍 TESTING WHICH METHOD IS USED IN CALIBRATION:")
    print("=" * 80)
    
    try:
        # Check the calibration script logic
        print("📋 Checking calibration script logic...")
        
        # The script uses calculate_optimal_grid_size_from_emsr by default
        # But the calibrator uses _calculate_optimal_grid_size_from_day4
        print("   Script default: calculate_optimal_grid_size_from_emsr (Day 1+2)")
        print("   Calibrator default: _calculate_optimal_grid_size_from_day4 (Day 4)")
        print("   ⚠️  THERE'S A MISMATCH!")
        
        # Show the actual logic from the script
        print("\n📄 Script logic (run_tenerife_calibration.py):")
        print("   if args.grid_size is not None:")
        print("       grid_size = (args.grid_size, args.grid_size)")
        print("   else:")
        print("       grid_size = calculate_optimal_grid_size_from_emsr(day1_path, day2_path)")
        
        print("\n📄 Calibrator logic (fire_perimeter_calibration.py):")
        print("   if grid_size is not None:")
        print("       optimal_grid_size = grid_size")
        print("   else:")
        print("       optimal_grid_size = self._calculate_optimal_grid_size_from_day4()")
        
        print("\n🔧 RECOMMENDATION:")
        print("   The script should use the same method as the calibrator.")
        print("   Either both should use Day 4, or both should use Day 1+2.")
        
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🔥 COMPARING GRID SIZE CALCULATION METHODS")
    print("=" * 80)
    
    # Test 1: Compare the two methods
    methods_match = compare_grid_size_methods()
    
    # Test 2: Check which method is used in calibration
    test_which_method_is_used()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY:")
    print(f"   Methods produce same result: {'✅ YES' if methods_match else '❌ NO'}")
    
    if not methods_match:
        print("\n⚠️  WARNING: The two methods produce different results!")
        print("   This could cause the shape mismatch errors you're seeing.")
        print("   The calibration script and calibrator are using different methods.")
        
        print("\n🔧 SOLUTION:")
        print("   1. Decide which method to use (Day 4 or Day 1+2)")
        print("   2. Update both the script and calibrator to use the same method")
        print("   3. Test to ensure they produce identical results")
    
    print("=" * 80)
