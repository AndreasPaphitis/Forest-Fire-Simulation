#!/usr/bin/env python
"""
Test script to verify the updated calibration script works with EMSR target data.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_emsr_target_integration():
    """Test that EMSR target data integration works correctly."""
    
    print("🧪 TESTING EMSR TARGET DATA INTEGRATION")
    print("=" * 50)
    
    try:
        # Test EMSR target data creation
        from src.core.calibration.calibration_utils import create_emsr_target_data
        
        # Paths to EMSR files
        day1_path = "EMSR Delineations/Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp"
        day2_path = "EMSR Delineations/Day 2 (21_08_23)/EMSR685_AOI01_DEL_MONIT01_observedEventA_v1.shp"
        
        # Check if files exist
        if not Path(day1_path).exists():
            print(f"❌ Day 1 file not found: {day1_path}")
            return False
        
        if not Path(day2_path).exists():
            print(f"❌ Day 2 file not found: {day2_path}")
            return False
        
        # Create EMSR target data
        target_data = create_emsr_target_data(day1_path, day2_path, grid_size=(50, 50))
        
        print(f"✅ EMSR target data created successfully")
        print(f"   Primary target cells: {target_data['fire_perimeter'].sum()}")
        print(f"   Day 1 target cells: {target_data['day1_fire_perimeter'].sum()}")
        print(f"   Day 2 target cells: {target_data['day2_fire_perimeter'].sum()}")
        
        # Test with objective function
        from src.core.calibration.objective_functions import SpatialSimilarityObjective
        from src.config.config_tools import create_config
        from src.core.forest_model import create_forest_model
        from src.core.fire_simulation_engine import FireSimulationEngine
        
        # Create test simulation
        config = create_config(
            grid_size=(50, 50),
            num_layers=3,
            max_steps=10,
            spread_probability=0.4,
            ignition_threshold=0.15,
            max_fuel_value=1.0,
            initial_fuel_load=0.5,
            fuel_consumption_rate=0.1,
            ignition_points=[(25, 25, 0)]
        )
        
        forest_model = create_forest_model(config=config)
        forest_model.set_ignition(25, 25, 0)
        
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        results = engine.run_simulation()
        
        print(f"   Simulation burned cells: {results['stats']['total_burned_cells']}")
        
        # Test objective function with EMSR target data
        objective_function = SpatialSimilarityObjective()
        objective_result = objective_function.evaluate(results, target_data)
        
        print(f"   Objective value: {objective_result.value}")
        print(f"   Is valid: {objective_result.is_valid}")
        print(f"   Components: {objective_result.components}")
        
        if objective_result.value > 0:
            print("✅ SUCCESS: EMSR target data works with objective function!")
            return True
        else:
            print("❌ FAILURE: Objective value is 0")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_calibration_script_update():
    """Test that the calibration script has been updated correctly."""
    
    print("\n🔧 TESTING CALIBRATION SCRIPT UPDATE")
    print("=" * 50)
    
    try:
        # Check if the updated script exists
        script_path = "scripts/run_tenerife_calibration.py"
        if not Path(script_path).exists():
            print(f"❌ Calibration script not found: {script_path}")
            return False
        
        # Read the script and check for EMSR target data usage
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Check for key indicators of EMSR target data integration
        checks = [
            ("create_emsr_target_data", "EMSR target data function import"),
            ("day1_path", "Day 1 EMSR path"),
            ("day2_path", "Day 2 EMSR path"),
            ("target_data = create_emsr_target_data", "EMSR target data creation"),
            ("test_data = target_data", "Target data assignment"),
        ]
        
        all_passed = True
        for check, description in checks:
            if check in content:
                print(f"   ✅ {description}")
            else:
                print(f"   ❌ {description} - NOT FOUND")
                all_passed = False
        
        if all_passed:
            print("✅ SUCCESS: Calibration script has been updated correctly!")
            return True
        else:
            print("❌ FAILURE: Calibration script update incomplete")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🧪 COMPREHENSIVE EMSR TARGET DATA TEST")
    print("=" * 60)
    
    # Test 1: EMSR target data integration
    test1_passed = test_emsr_target_integration()
    
    # Test 2: Calibration script update
    test2_passed = test_calibration_script_update()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ EMSR target data integration is working")
        print("✅ Calibration script has been updated correctly")
        print("\n🎯 READY TO RUN CALIBRATION WITH EMSR TARGET DATA!")
        print("\nTo run calibration:")
        print("   python scripts/run_tenerife_calibration.py --grid-size 100")
    else:
        print("❌ SOME TESTS FAILED")
        if not test1_passed:
            print("   - EMSR target data integration needs fixing")
        if not test2_passed:
            print("   - Calibration script update needs fixing")
