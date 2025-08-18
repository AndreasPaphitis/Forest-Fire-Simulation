#!/usr/bin/env python3
"""
Debug script to understand why the simulation is ending immediately.
"""

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig

def debug_simulation_loop():
    """Debug why the simulation loop is ending immediately."""
    
    print("🔍 Debugging simulation loop...")
    
    # Create a very simple config
    config = ModelConfig(
        grid_size=(10, 10),  # Very small grid
        num_layers=2,
        max_steps=5,
        simulation_type='memory_optimized',
        
        # Very aggressive fire parameters
        spread_probability=0.99,
        fuel_consumption_rate=0.001,  # Very low consumption
        ignition_threshold=0.001,  # Very low threshold
        min_fuel_value=0.001,
        max_fuel_value=1.0,
        
        # No wind to simplify
        wind_speed=0.0,
        wind_direction=0.0,
        
        # Disable history
        store_full_states=False,
        
        # Don't stop when fire goes out
        stop_when_fire_extinguished=False
    )
    
    # Test parameters
    params = {
        'spread_probability': 0.99,
        'fuel_consumption_rate': 0.001,
        'ignition_threshold': 0.001
    }
    
    print("📋 Configuration:")
    print(f"  Grid size: {config.grid_size}")
    print(f"  Max steps: {config.max_steps}")
    print(f"  Stop when extinguished: {config.stop_when_fire_extinguished}")
    
    try:
        # Run evaluation
        result = evaluate_worker_function(
            parameter_values=params,
            target_data=None,
            config_dict=config.__dict__,
            objective_function_name="SpatialSimilarityObjective"
        )
        
        print("\n✅ Evaluation completed successfully!")
        
        # Check simulation results
        stats = result['simulation_stats']
        
        print(f"\n📊 Simulation Results:")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Total steps: {stats.get('total_steps', 0)}")
        print(f"  Steps (compatibility): {stats.get('steps', 0)}")
        print(f"  Final active cells: {stats.get('final_active_cells', 0)}")
        print(f"  Total burned cells: {stats.get('total_burned_cells', 0)}")
        print(f"  Max active cells: {stats.get('max_active_cells', 0)}")
        print(f"  Evaluation time: {result['evaluation_time']:.2f}s")
        
        # Check if the simulation actually ran
        if stats.get('total_steps', 0) == 0 and stats.get('steps', 0) == 0:
            print(f"\n❌ SIMULATION DID NOT RUN - Both 'total_steps' and 'steps' are 0")
            print(f"  This suggests the simulation loop is not executing properly")
        else:
            print(f"\n✅ Simulation ran for {stats.get('total_steps', stats.get('steps', 0))} steps")
        
        # Check if there are any error messages
        if 'error_message' in result and result['error_message']:
            print(f"\n❌ Error message: {result['error_message']}")
        
        return stats.get('total_steps', 0) > 0 or stats.get('steps', 0) > 0
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_simulation_loop()
    if success:
        print("\n🎉 Simulation loop is working!")
    else:
        print("\n💥 Simulation loop is not working!")
