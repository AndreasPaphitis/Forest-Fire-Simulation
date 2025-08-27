#!/usr/bin/env python3
"""
Debug Objective Function

This script tests the objective function directly to understand why it's returning
is_valid=False even when there's valid overlap.
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_objective_function():
    """Debug the objective function step by step."""
    print("🧪 DEBUG OBJECTIVE FUNCTION")
    print("=" * 50)
    
    # Step 1: Test with simple data
    print("\n📊 Step 1: Testing with Simple Data")
    try:
        from src.core.calibration.objective_functions import SpatialSimilarityObjective
        
        # Create simple test data
        test_target = np.zeros((609, 609))
        test_predicted = np.zeros((609, 609))
        
        # Add fire to both (simple test)
        test_target[300:400, 300:400] = 1  # 100x100 fire area
        test_predicted[350:450, 350:450] = 1  # 100x100 fire area, slightly offset
        
        print(f"   Test target cells: {np.sum(test_target > 0)}")
        print(f"   Test predicted cells: {np.sum(test_predicted > 0)}")
        
        # Calculate overlap manually
        overlap = np.sum((test_target > 0) & (test_predicted > 0))
        union = np.sum((test_target > 0) | (test_predicted > 0))
        
        print(f"   Overlap: {overlap}")
        print(f"   Union: {union}")
        
        if union > 0:
            jaccard = overlap / union
            print(f"   Manual Jaccard index: {jaccard:.4f}")
        else:
            print(f"   Manual Jaccard index: 0.0 (no overlap)")
        
        # Test objective function
        objective = SpatialSimilarityObjective()
        result = objective.evaluate(test_predicted, test_target)
        
        print(f"   Objective function result: {result.value:.8f}")
        print(f"   Is valid: {result.is_valid}")
        print(f"   Error message: {result.error_message}")
        
        if result.is_valid:
            print(f"   ✅ Objective function works correctly")
        else:
            print(f"   ❌ Objective function returns is_valid=False")
            print(f"   Components: {result.components}")
            
    except Exception as e:
        print(f"❌ Error in simple test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Test with actual target data
    print("\n🎯 Step 2: Testing with Actual Target Data")
    try:
        from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
        from src.core.calibration.calibration_config import CalibrationTarget
        
        # Create calibrator
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=8,
            workers=1,
            grid_search_points=2
        )
        
        # Create target
        target_file = Path("EMSR Delineations/Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.json")
        target = CalibrationTarget(
            fire_perimeter_path=str(target_file),
            weight=1.0
        )
        
        # Prepare target data
        target_data = calibrator._prepare_target_data([target], grid_size=(609, 609))
        
        if target_data and 'fire_perimeter' in target_data:
            fire_perim = target_data['fire_perimeter']
            
            # Convert to dense if sparse
            if hasattr(fire_perim, 'toarray'):
                target_2d = fire_perim.toarray()
                print(f"   Converted sparse target to dense: {target_2d.shape}")
            else:
                target_2d = fire_perim
                print(f"   Using dense target: {target_2d.shape}")
            
            print(f"   Target fire cells: {np.sum(target_2d > 0):,}")
            
            # Create a simulated fire that should overlap
            simulated_fire = np.zeros((609, 609))
            
            # Add fire around the ignition point (395, 377)
            ignition_x, ignition_y = 395, 377
            fire_radius = 50
            
            for i in range(max(0, ignition_x-fire_radius), min(609, ignition_x+fire_radius)):
                for j in range(max(0, ignition_y-fire_radius), min(609, ignition_y+fire_radius)):
                    if (i - ignition_x)**2 + (j - ignition_y)**2 <= fire_radius**2:
                        simulated_fire[i, j] = 1
            
            print(f"   Simulated fire cells: {np.sum(simulated_fire > 0):,}")
            
            # Calculate overlap manually
            overlap = np.sum((target_2d > 0) & (simulated_fire > 0))
            union = np.sum((target_2d > 0) | (simulated_fire > 0))
            
            print(f"   Overlap: {overlap}")
            print(f"   Union: {union}")
            
            if union > 0:
                jaccard = overlap / union
                print(f"   Manual Jaccard index: {jaccard:.4f}")
            else:
                print(f"   Manual Jaccard index: 0.0 (no overlap)")
            
            # Test objective function with actual data
            objective = SpatialSimilarityObjective()
            result = objective.evaluate(simulated_fire, target_2d)
            
            print(f"   Objective function result: {result.value:.8f}")
            print(f"   Is valid: {result.is_valid}")
            print(f"   Error message: {result.error_message}")
            
            if result.is_valid:
                print(f"   ✅ Objective function works with actual data")
                print(f"   Components: {result.components}")
            else:
                print(f"   ❌ Objective function fails with actual data")
                
        else:
            print(f"   ❌ Failed to prepare target data")
            
    except Exception as e:
        print(f"❌ Error in actual data test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Test the helper functions
    print("\n🔧 Step 3: Testing Helper Functions")
    try:
        from src.core.calibration.objective_functions import (
            calculate_jaccard_index, 
            calculate_dice_coefficient,
            calculate_area_ratio
        )
        
        # Test with simple data
        test_target = np.zeros((100, 100))
        test_predicted = np.zeros((100, 100))
        
        test_target[40:60, 40:60] = 1  # 20x20 fire
        test_predicted[50:70, 50:70] = 1  # 20x20 fire, offset
        
        jaccard = calculate_jaccard_index(test_predicted, test_target)
        dice = calculate_dice_coefficient(test_predicted, test_target)
        area_ratio = calculate_area_ratio(test_predicted, test_target)
        
        print(f"   Jaccard index: {jaccard:.4f}")
        print(f"   Dice coefficient: {dice:.4f}")
        print(f"   Area ratio: {area_ratio:.4f}")
        
        if jaccard > 0 and dice > 0:
            print(f"   ✅ Helper functions work correctly")
        else:
            print(f"   ❌ Helper functions return 0")
            
    except Exception as e:
        print(f"❌ Error in helper functions test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n🎯 OBJECTIVE FUNCTION DEBUG COMPLETE")
    print(f"=" * 50)
    
    return True

if __name__ == "__main__":
    debug_objective_function()
