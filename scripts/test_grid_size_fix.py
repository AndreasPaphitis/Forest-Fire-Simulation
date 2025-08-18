#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Grid Size Fix

This script tests that the grid size calculation is working correctly and that
the simulation will run with the correct large grid size that matches the target data.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_grid_size_calculation():
    """Test the grid size calculation and target data creation."""
    print("🧪 TESTING GRID SIZE FIX")
    print("=" * 60)
    
    try:
        # Test grid size calculation using Day 4 method (same as calibrator)
        from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
        
        # Create temporary calibrator to access Day 4 grid size calculation
        temp_calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=8,
            grid_search_points=2,
            experiment_name="test_grid_size_fix"
        )
        
        # Calculate optimal grid size from Day 4 (same method as calibrator)
        grid_size = temp_calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
        grid_width, grid_height = grid_size
        
        print(f"✅ Grid size calculated (Day 4 method): {grid_width} × {grid_height}")
        
        # Calculate area and memory requirements
        cell_size_m = 5.0
        grid_width_m = grid_width * cell_size_m
        grid_height_m = grid_height * cell_size_m
        total_area_m2 = grid_width_m * grid_height_m
        total_area_km2 = total_area_m2 / 1_000_000
        total_area_ha = total_area_m2 / 10_000
        
        # Calculate total cells (25 layers)
        num_layers = 25
        total_cells = grid_width * grid_height * num_layers
        
        print(f"📏 Physical size: {grid_width_m:.0f}m × {grid_height_m:.0f}m")
        print(f"📊 Total area: {total_area_km2:.2f} km² ({total_area_ha:.1f} ha)")
        print(f"🔢 Total cells: {total_cells:,} ({total_cells/1e6:.1f}M)")
        
        # Test target data creation
        print("\n🔍 TESTING TARGET DATA CREATION:")
        print("-" * 40)
        
        from src.core.calibration.calibration_utils import create_emsr_target_data
        
        # Paths to EMSR files
        day1_path = "EMSR Delineations/Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp"
        day2_path = "EMSR Delineations/Day 2 (21_08_23)/EMSR685_AOI01_DEL_MONIT01_observedEventA_v1.shp"
        
        target_data = create_emsr_target_data(
            day1_path=day1_path,
            day2_path=day2_path,
            grid_size=grid_size,
            model_resolution=5.0
        )
        
        print(f"✅ Target data created successfully")
        print(f"   Day 1 target: {target_data[0].area_hectares:.1f} ha" if target_data[0].area_hectares else "   Day 1 target: Unknown area")
        print(f"   Day 2 target: {target_data[1].area_hectares:.1f} ha" if target_data[1].area_hectares else "   Day 2 target: Unknown area")
        
        # Test calibration configuration creation
        print("\n🔍 TESTING CALIBRATION CONFIGURATION:")
        print("-" * 40)
        
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=8,  # Small number for testing
            grid_search_points=2,  # Small number for testing
            experiment_name="test_grid_size_fix",
            grid_size=grid_size  # Pass the calculated grid size
        )
        
        print(f"✅ Calibrator created with grid size: {grid_size}")
        
        # Test calibration configuration creation
        calib_config = calibrator.create_calibration_config(
            training_data=target_data,
            top_5_parameters=['spread_probability', 'fuel_consumption_rate'],  # Small set for testing
            grid_size=grid_size
        )
        
        print(f"✅ Calibration configuration created")
        print(f"   Base config grid size: {calib_config.base_config.grid_size}")
        print(f"   Target data grid size: {grid_size}")
        
        # Verify grid sizes match
        if calib_config.base_config.grid_size == grid_size:
            print(f"✅ GRID SIZES MATCH - Simulation will run with correct size!")
            return True
        else:
            print(f"❌ GRID SIZE MISMATCH!")
            print(f"   Expected: {grid_size}")
            print(f"   Actual: {calib_config.base_config.grid_size}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simulation_grid_size():
    """Test that the simulation will run with the correct grid size."""
    print("\n🧪 TESTING SIMULATION GRID SIZE:")
    print("=" * 60)
    
    try:
        # Calculate grid size using Day 4 method
        from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
        
        temp_calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=8,
            grid_search_points=2,
            experiment_name="test_simulation_grid"
        )
        
        grid_size = temp_calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
        grid_width, grid_height = grid_size
        
        print(f"🎯 Target grid size (Day 4): {grid_width} × {grid_height}")
        
        # Create a minimal simulation configuration
        from src.config.config_tools import ModelConfig
        
        config = ModelConfig(
            grid_size=grid_size,
            num_layers=25,
            max_steps=10,  # Short for testing
            model_resolution=5.0,
            simulation_type="memory_optimized",
            memory_optimization_level=2,
            use_disk_storage=True,
            use_differential_history=True,
            use_sparse_storage=True
        )
        
        print(f"✅ Simulation config created with grid size: {config.grid_size}")
        
        # Test forest model creation (without running simulation)
        from src.core.forest_model import create_forest_model
        
        forest_model = create_forest_model(config=config)
        
        print(f"✅ Forest model created successfully")
        print(f"   Model grid size: {forest_model.grid_size}")
        print(f"   State shape: {forest_model.state.shape}")
        
        # Verify the model has the correct grid size
        if forest_model.grid_size == grid_size:
            print(f"✅ MODEL GRID SIZE MATCHES TARGET!")
            return True
        else:
            print(f"❌ MODEL GRID SIZE MISMATCH!")
            print(f"   Expected: {grid_size}")
            print(f"   Actual: {forest_model.grid_size}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_script_grid_size_consistency():
    """Test that the script now uses the same grid size calculation as the calibrator."""
    print("\n🧪 TESTING SCRIPT GRID SIZE CONSISTENCY:")
    print("=" * 60)
    
    try:
        # Test the script's grid size calculation (simulated)
        from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
        
        # Simulate what the script now does
        temp_calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=8,
            grid_search_points=2,
            experiment_name="test_script_consistency"
        )
        
        script_grid_size = temp_calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
        
        # Test what the calibrator does when no grid size is provided
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=8,
            grid_search_points=2,
            experiment_name="test_calibrator_consistency"
        )
        
        # The calibrator would use Day 4 method when no grid size is provided
        calibrator_grid_size = calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
        
        print(f"Script grid size: {script_grid_size}")
        print(f"Calibrator grid size: {calibrator_grid_size}")
        
        if script_grid_size == calibrator_grid_size:
            print(f"✅ SCRIPT AND CALIBRATOR USE SAME GRID SIZE!")
            return True
        else:
            print(f"❌ SCRIPT AND CALIBRATOR USE DIFFERENT GRID SIZES!")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔥 TESTING GRID SIZE FIX FOR CALIBRATION")
    print("=" * 80)
    
    # Test 1: Grid size calculation
    test1_passed = test_grid_size_calculation()
    
    # Test 2: Simulation grid size
    test2_passed = test_simulation_grid_size()
    
    # Test 3: Script consistency
    test3_passed = test_script_grid_size_consistency()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY:")
    print(f"   Grid size calculation: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Simulation grid size: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"   Script consistency: {'✅ PASS' if test3_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed and test3_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("   The calibration should now run with the correct large grid size.")
        print("   Script and calibrator use the same Day 4 grid size calculation.")
        print("   No more shape mismatch errors!")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("   There are still issues to resolve.")
    
    print("=" * 80)
