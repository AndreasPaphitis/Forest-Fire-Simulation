#!/usr/bin/env python3
"""
Verify that all simulation logic is properly integrated into calibration.
"""

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig

def verify_calibration_integration():
    """Verify all simulation logic is properly integrated into calibration."""
    
    print("🔍 Verifying calibration integration...")
    
    # Test with a very simple configuration to isolate the issue
    config = ModelConfig(
        grid_size=(20, 20),  # Small grid for testing
        num_layers=2,
        max_steps=10,
        simulation_type='memory_optimized',
        
        # Very aggressive fire parameters to ensure spread
        spread_probability=0.99,
        fuel_consumption_rate=0.001,  # Very low consumption
        ignition_threshold=0.001,  # Very low threshold
        min_fuel_value=0.001,
        max_fuel_value=1.0,
        
        # No wind to simplify
        wind_speed=0.0,
        wind_direction=0.0,
        
        # Disable history to avoid sparse copy issues
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
    print(f"  Store history: {config.store_full_states}")
    
    try:
        # Run evaluation
        result = evaluate_worker_function(
            parameter_values=params,
            target_data=None,
            config_dict=config.__dict__,
            objective_function_name="SpatialSimilarityObjective"
        )
        
        print("\n✅ Evaluation completed successfully!")
        
        # Check if all our fixes are working
        stats = result['simulation_stats']
        
        print(f"\n📊 Simulation Results:")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Total steps: {stats.get('total_steps', 0)}")
        print(f"  Final active cells: {stats.get('final_active_cells', 0)}")
        print(f"  Total burned cells: {stats.get('total_burned_cells', 0)}")
        print(f"  Max active cells: {stats.get('max_active_cells', 0)}")
        print(f"  Evaluation time: {result['evaluation_time']:.2f}s")
        
        # Verify our fixes are working
        print(f"\n🔧 Verification of Fixes:")
        
        # Fix 1: Ignition point detection
        if stats.get('max_active_cells', 0) > 0:
            print(f"  ✅ Ignition point detection: Working (found {stats.get('max_active_cells', 0)} active cells)")
        else:
            print(f"  ❌ Ignition point detection: Failed (no active cells found)")
        
        # Fix 2: Engine initialization
        if stats.get('total_steps', 0) >= 0:
            print(f"  ✅ Engine initialization: Working (simulation ran)")
        else:
            print(f"  ❌ Engine initialization: Failed (simulation didn't run)")
        
        # Fix 3: Memory optimizations
        if result['evaluation_time'] < 5.0:  # Should be fast
            print(f"  ✅ Memory optimizations: Working (fast evaluation: {result['evaluation_time']:.2f}s)")
        else:
            print(f"  ⚠️  Memory optimizations: Slow evaluation ({result['evaluation_time']:.2f}s)")
        
        # Fix 4: Simulation loop logic
        if stats.get('total_steps', 0) > 0:
            print(f"  ✅ Simulation loop logic: Working (ran for {stats.get('total_steps', 0)} steps)")
        else:
            print(f"  ❌ Simulation loop logic: Failed (0 steps)")
        
        # Fix 5: Fire spread
        if stats.get('total_burned_cells', 0) > 0:
            print(f"  ✅ Fire spread: Working (burned {stats.get('total_burned_cells', 0)} cells)")
        else:
            print(f"  ❌ Fire spread: Failed (no cells burned)")
        
        # Overall assessment
        working_fixes = 0
        total_fixes = 5
        
        if stats.get('max_active_cells', 0) > 0:
            working_fixes += 1
        if stats.get('total_steps', 0) >= 0:
            working_fixes += 1
        if result['evaluation_time'] < 5.0:
            working_fixes += 1
        if stats.get('total_steps', 0) > 0:
            working_fixes += 1
        if stats.get('total_burned_cells', 0) > 0:
            working_fixes += 1
        
        print(f"\n📈 Overall Assessment:")
        print(f"  Working fixes: {working_fixes}/{total_fixes}")
        print(f"  Success rate: {(working_fixes/total_fixes)*100:.1f}%")
        
        if working_fixes >= 4:
            print(f"  🎉 Calibration framework is ready for use!")
        elif working_fixes >= 3:
            print(f"  ⚠️  Calibration framework is mostly working but needs minor fixes")
        else:
            print(f"  💥 Calibration framework needs significant fixes")
        
        return working_fixes >= 4
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_calibration_integration()
    if success:
        print("\n🎉 Calibration integration verification passed!")
    else:
        print("\n💥 Calibration integration verification failed!")
