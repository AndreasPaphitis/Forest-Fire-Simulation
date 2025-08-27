#!/usr/bin/env python3
"""
Debug Calibration Script

This script tests the calibration workflow step by step to identify
where the target data is being lost.
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
from src.core.calibration.calibration_config import CalibrationConfig, CalibrationTarget
from src.config.config_tools import ModelConfig

def debug_calibration_workflow():
    """Debug the calibration workflow step by step."""
    print("🐛 DEBUG CALIBRATION WORKFLOW")
    print("=" * 50)
    
    # Step 1: Create base configuration
    print("\n📋 Step 1: Creating Base Configuration")
    base_config = ModelConfig(
        grid_size=(609, 609),
        num_layers=25,
        model_resolution=20.0,
        max_steps=25,
        ignition_points=[(395, 377, 0)],
        use_terrain=False,  # Disable terrain for debugging
        use_preprocessed_terrain=False,  # Disable for debugging
        preprocessed_lidar_dir="preprocessed_lidar"
    )
    
    print(f"   Base config grid_size: {base_config.grid_size}")
    
    # Step 2: Create calibration targets
    print("\n🎯 Step 2: Creating Calibration Targets")
    calibration_targets = []
    
    target1 = CalibrationTarget(
        fire_perimeter_path="EMSR Delineations/Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.json",
        weight=1.0
    )
    calibration_targets.append(target1)
    print(f"✅ Created target 1")
    
    # Step 3: Create calibration configuration
    print("\n⚙️  Step 3: Creating Calibration Configuration")
    calib_config = CalibrationConfig(
        base_config=base_config,
        calibration_parameters=['spread_probability', 'fuel_consumption_rate'],
        grid_search_points=2,  # Minimal for debugging
        max_workers=1,  # Single worker for debugging
        calibration_targets=calibration_targets,
        use_terrain=False,  # Disable terrain for debugging
        use_preprocessed_terrain=False  # Disable for debugging
    )
    
    print(f"   Calibration targets in config: {len(calib_config.calibration_targets)}")
    for i, target in enumerate(calib_config.calibration_targets):
        print(f"   Target {i+1}: {target.fire_perimeter_path}")
    
    # Step 4: Create calibrator
    print("\n🔧 Step 4: Creating Calibrator")
    calibrator = TenerifeFirePerimeterCalibrator(
        memory_gb=8,
        workers=1,
        grid_search_points=2
    )
    
    # Step 5: Test target data preparation
    print("\n🔄 Step 5: Testing Target Data Preparation")
    try:
        target_data = calibrator._prepare_target_data(calib_config.calibration_targets, grid_size=(609, 609))
        
        if target_data and 'fire_perimeter' in target_data:
            fire_perim = target_data['fire_perimeter']
            if hasattr(fire_perim, 'toarray'):
                fire_cells = np.sum(fire_perim.toarray() > 0)
            else:
                fire_cells = np.sum(fire_perim > 0)
            print(f"✅ Target data prepared: {fire_cells:,} fire cells")
        else:
            print("❌ Target data preparation failed")
            print(f"   Target data keys: {list(target_data.keys()) if target_data else 'None'}")
            return False
            
    except Exception as e:
        print(f"❌ Target data preparation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Test single evaluation
    print("\n🧪 Step 6: Testing Single Evaluation")
    try:
        # Create a simple parameter set
        test_params = {'spread_probability': 0.5, 'fuel_consumption_rate': 0.7}
        print(f"   Test parameters: {test_params}")
        
        # Test the evaluation function directly
        from src.core.calibration.grid_search import evaluate_worker_function
        
        print(f"   Calib config grid_size: {calib_config.base_config.grid_size}")
        
        # CRITICAL FIX: Pass the base_config as config_dict, not the calibration config
        from dataclasses import asdict
        base_config_dict = asdict(calib_config.base_config)
        print(f"   Base config dict keys: {list(base_config_dict.keys())}")
        print(f"   Base config dict grid_size: {base_config_dict.get('grid_size', 'NOT FOUND')}")
        
        result = evaluate_worker_function(
            parameter_values=test_params,
            target_data=target_data,
            config_dict=base_config_dict,
            objective_function_name="SpatialSimilarityObjective",
            worker_id=0
        )
        
        print(f"✅ Single evaluation completed")
        
        # Handle different result formats
        if isinstance(result, dict) and 'objective_result' in result:
            objective_result = result['objective_result']
            if hasattr(objective_result, 'value'):
                objective_value = objective_result.value
                is_valid = objective_result.is_valid
            else:
                objective_value = 0.0
                is_valid = False
        else:
            objective_value = 0.0
            is_valid = False
        
        print(f"   Objective value: {objective_value:.8f}")
        print(f"   Is valid: {is_valid}")
        
        if objective_value > 0.0:
            print("✅ SUCCESS: Objective value is not 0.00000000!")
            return True
        else:
            print("❌ ISSUE: Objective value is still 0.00000000")
            return False
            
    except Exception as e:
        print(f"❌ Single evaluation error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_calibration_workflow()
