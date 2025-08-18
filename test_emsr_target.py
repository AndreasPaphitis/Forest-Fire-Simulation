#!/usr/bin/env python
"""
Simple test script to verify EMSR target data works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.calibration.calibration_utils import create_emsr_target_data
from src.core.calibration.objective_functions import SpatialSimilarityObjective
from src.config.config_tools import create_config
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine

def test_emsr_target():
    """Test EMSR target data creation and objective function."""
    
    print("🧪 TESTING EMSR TARGET DATA")
    print("=" * 40)
    
    # Paths to EMSR files
    day1_path = "EMSR Delineations/Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp"
    day2_path = "EMSR Delineations/Day 2 (21_08_23)/EMSR685_AOI01_DEL_MONIT01_observedEventA_v1.shp"
    
    try:
        # Create EMSR target data
        target_data = create_emsr_target_data(day1_path, day2_path, grid_size=(50, 50))
        print(f"✅ EMSR target data created successfully")
        print(f"   Primary target cells: {target_data['fire_perimeter'].sum()}")
        
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
        
        # Test objective function
        objective_function = SpatialSimilarityObjective()
        objective_result = objective_function.evaluate(results, target_data)
        
        print(f"   Objective value: {objective_result.value}")
        print(f"   Is valid: {objective_result.is_valid}")
        print(f"   Components: {objective_result.components}")
        
        if objective_result.value > 0:
            print("✅ SUCCESS: EMSR target data works!")
            return True
        else:
            print("❌ FAILURE: Objective value is 0")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_emsr_target()
    if success:
        print("\n🎯 Ready to use EMSR target data in calibration!")
    else:
        print("\n❌ Need to fix EMSR target data")
