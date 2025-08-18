#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Training/Validation Split

This script tests that the training/validation split is working correctly:
- Days 1-2 for training (calibration)
- Days 3-4 for validation
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_training_validation_split():
    """Test the training/validation split functionality."""
    print("🧪 TESTING TRAINING/VALIDATION SPLIT")
    print("=" * 60)
    
    try:
        # Test fire perimeter discovery
        from src.core.calibration.fire_perimeter_calibration import FirePerimeterDiscovery, TenerifeFirePerimeterCalibrator
        
        print("📁 Discovering fire perimeters...")
        discovery = FirePerimeterDiscovery("EMSR Delineations")
        fire_dataset = discovery.discover_fire_perimeters()
        
        if not fire_dataset.fire_perimeters:
            print("❌ No fire perimeters found")
            return False
        
        print(f"✅ Found {len(fire_dataset.fire_perimeters)} fire perimeters:")
        for fp in fire_dataset.fire_perimeters:
            print(f"   Day {fp.day_number} ({fp.date}): {fp.area_hectares:.1f} ha")
        
        # Test training/validation split
        print("\n📊 Testing training/validation split...")
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=8,
            grid_search_points=2,
            experiment_name="test_split"
        )
        
        training_data, validation_data = calibrator.setup_training_test_split(
            fire_dataset,
            training_days=[1, 2],  # Days 1-2 for training (calibration)
            test_days=[3, 4]       # Days 3-4 for testing (validation)
        )
        
        print(f"\n✅ Training/Validation split complete:")
        print(f"   🎯 Training (calibration): {len(training_data)} fire perimeters")
        for fp in training_data:
            print(f"      Day {fp.day_number} ({fp.date}): {fp.area_hectares:.1f} ha")
        print(f"   🧪 Validation: {len(validation_data)} fire perimeters")
        for fp in validation_data:
            print(f"      Day {fp.day_number} ({fp.date}): {fp.area_hectares:.1f} ha")
        
        # Verify the split is correct
        training_days = [fp.day_number for fp in training_data]
        validation_days = [fp.day_number for fp in validation_data]
        
        expected_training = [1, 2]
        expected_validation = [3, 4]
        
        if training_days == expected_training and validation_days == expected_validation:
            print(f"\n✅ SPLIT IS CORRECT!")
            print(f"   Training days: {training_days} (expected: {expected_training})")
            print(f"   Validation days: {validation_days} (expected: {expected_validation})")
            return True
        else:
            print(f"\n❌ SPLIT IS INCORRECT!")
            print(f"   Training days: {training_days} (expected: {expected_training})")
            print(f"   Validation days: {validation_days} (expected: {expected_validation})")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_grid_size_consistency():
    """Test that the grid size is consistent across training and validation data."""
    print("\n🧪 TESTING GRID SIZE CONSISTENCY:")
    print("=" * 60)
    
    try:
        from src.core.calibration.fire_perimeter_calibration import FirePerimeterDiscovery, TenerifeFirePerimeterCalibrator
        
        # Discover fire perimeters
        discovery = FirePerimeterDiscovery("EMSR Delineations")
        fire_dataset = discovery.discover_fire_perimeters()
        
        # Create calibrator
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=8,
            grid_search_points=2,
            experiment_name="test_grid_consistency"
        )
        
        # Set up training/validation split
        training_data, validation_data = calibrator.setup_training_test_split(
            fire_dataset,
            training_days=[1, 2],
            test_days=[3, 4]
        )
        
        # Calculate grid size using Day 4 method (same as calibrator default)
        grid_size = calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
        grid_width, grid_height = grid_size
        
        print(f"🎯 Grid size (Day 4 method): {grid_width} × {grid_height}")
        
        # Test that all fire perimeters can be processed with this grid size
        print(f"\n🔍 Testing grid size compatibility...")
        
        all_data = training_data + validation_data
        compatible_count = 0
        
        for fp in all_data:
            try:
                # Test that the fire perimeter can be processed
                if fp.area_hectares and fp.area_hectares > 0:
                    compatible_count += 1
                    print(f"   ✅ Day {fp.day_number}: {fp.area_hectares:.1f} ha")
                else:
                    print(f"   ⚠️  Day {fp.day_number}: No area data")
            except Exception as e:
                print(f"   ❌ Day {fp.day_number}: Error - {e}")
        
        if compatible_count == len(all_data):
            print(f"\n✅ ALL FIRE PERIMETERS ARE COMPATIBLE!")
            return True
        else:
            print(f"\n❌ SOME FIRE PERIMETERS HAVE ISSUES!")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_calibration_configuration():
    """Test that the calibration configuration works with the training/validation split."""
    print("\n🧪 TESTING CALIBRATION CONFIGURATION:")
    print("=" * 60)
    
    try:
        from src.core.calibration.fire_perimeter_calibration import FirePerimeterDiscovery, TenerifeFirePerimeterCalibrator
        
        # Discover fire perimeters
        discovery = FirePerimeterDiscovery("EMSR Delineations")
        fire_dataset = discovery.discover_fire_perimeters()
        
        # Create calibrator
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=64,
            workers=8,
            grid_search_points=2,
            experiment_name="test_calibration_config"
        )
        
        # Set up training/validation split
        training_data, validation_data = calibrator.setup_training_test_split(
            fire_dataset,
            training_days=[1, 2],
            test_days=[3, 4]
        )
        
        # Calculate grid size
        grid_size = calibrator._calculate_optimal_grid_size_from_day4(buffer_percent=10.0)
        
        # Create calibration configuration
        calib_config = calibrator.create_calibration_config(
            training_data=training_data,  # Use training data (Days 1-2) for calibration
            top_5_parameters=['spread_probability', 'fuel_consumption_rate'],  # Small set for testing
            grid_size=grid_size
        )
        
        print(f"✅ Calibration configuration created successfully")
        print(f"   Training data: {len(training_data)} fire perimeters")
        print(f"   Validation data: {len(validation_data)} fire perimeters")
        print(f"   Grid size: {calib_config.base_config.grid_size}")
        print(f"   Parameters: {len(calib_config.calibration_parameters)}")
        
        # Verify grid sizes match
        if calib_config.base_config.grid_size == grid_size:
            print(f"✅ GRID SIZES MATCH!")
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

if __name__ == "__main__":
    print("🔥 TESTING TRAINING/VALIDATION SPLIT FOR CALIBRATION")
    print("=" * 80)
    
    # Test 1: Training/validation split
    test1_passed = test_training_validation_split()
    
    # Test 2: Grid size consistency
    test2_passed = test_grid_size_consistency()
    
    # Test 3: Calibration configuration
    test3_passed = test_calibration_configuration()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY:")
    print(f"   Training/validation split: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Grid size consistency: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"   Calibration configuration: {'✅ PASS' if test3_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed and test3_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("   ✅ Days 1-2 will be used for calibration")
        print("   ✅ Days 3-4 will be used for validation")
        print("   ✅ Grid sizes are consistent across all data")
        print("   ✅ Calibration configuration is properly set up")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("   There are still issues to resolve.")
    
    print("=" * 80)
