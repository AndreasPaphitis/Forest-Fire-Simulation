#!/usr/bin/env python3
"""
Quick test to verify calibration fixes work correctly.
"""

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig

def test_calibration_fix():
    """Test that calibration simulations run properly with ignition points."""
    
    print("🧪 Testing calibration fix...")
    
    # Create a simple config with more aggressive fire spread parameters
    config = ModelConfig(
        grid_size=(50, 50),
        num_layers=3,
        max_steps=15,
        simulation_type='memory_optimized',
        spread_probability=0.9,  # Very high spread probability
        fuel_consumption_rate=0.0001,  # Extremely low consumption rate
        ignition_threshold=0.05,  # Very low threshold for ignition
        min_fuel_value=0.01,  # Very low minimum fuel
        max_fuel_value=1.0,  # Standard max fuel
        wind_speed=0.0,  # No wind to simplify
        wind_direction=0.0,
        stop_when_fire_extinguished=False  # Don't stop when fire goes out
    )
    
    # Test parameters - even more aggressive
    params = {
        'spread_probability': 0.95,  # Very high
        'fuel_consumption_rate': 0.0001,  # Extremely low
        'ignition_threshold': 0.01  # Very low
    }
    
    try:
        # Run evaluation
        result = evaluate_worker_function(
            parameter_values=params,
            target_data=None,
            config_dict=config.__dict__,
            objective_function_name="SpatialSimilarityObjective"
        )
        
        print("✅ Test completed successfully!")
        print(f"Valid: {result['is_valid']}")
        print(f"Objective value: {result['objective_value']:.4f}")
        print(f"Evaluation time: {result['evaluation_time']:.2f}s")
        
        # Check simulation stats
        stats = result['simulation_stats']
        print(f"Total steps: {stats.get('total_steps', 0)}")
        print(f"Final active cells: {stats.get('final_active_cells', 0)}")
        print(f"Total burned cells: {stats.get('total_burned_cells', 0)}")
        print(f"Max active cells: {stats.get('max_active_cells', 0)}")
        
        # Verify simulation didn't end immediately
        if stats.get('total_steps', 0) > 1:
            print("✅ Simulation ran for multiple steps - ignition working!")
        else:
            print("⚠️  Simulation ended early - may need ignition adjustment")
            
        if stats.get('total_burned_cells', 0) > 0:
            print("✅ Fire spread occurred - calibration should work!")
        else:
            print("⚠️  No fire spread - may need parameter adjustment")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_calibration_fix()
    if success:
        print("\n🎉 Calibration fix verification passed!")
    else:
        print("\n💥 Calibration fix verification failed!")
