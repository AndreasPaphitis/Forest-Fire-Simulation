#!/usr/bin/env python3
"""
Test to check if there's an issue with larger grid sizes.
"""

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig

def test_grid_size_issue():
    """Test if there's an issue with larger grid sizes."""
    
    print("🔍 Testing grid size issue...")
    
    # Test different grid sizes
    grid_sizes = [
        (10, 10),   # Small - worked before
        (20, 20),   # Medium
        (30, 30),   # Larger
        (50, 50),   # Large - failed before
    ]
    
    results = []
    
    for grid_size in grid_sizes:
        print(f"\n--- Testing Grid Size: {grid_size} ---")
        
        # Create config
        config = ModelConfig(
            grid_size=grid_size,
            num_layers=3,
            max_steps=10,
            simulation_type='memory_optimized',
            
            # Aggressive fire parameters
            spread_probability=0.8,
            fuel_consumption_rate=0.01,
            ignition_threshold=0.1,
            min_fuel_value=0.1,
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
            'spread_probability': 0.8,
            'fuel_consumption_rate': 0.01,
            'ignition_threshold': 0.1
        }
        
        try:
            # Run evaluation
            result = evaluate_worker_function(
                parameter_values=params,
                target_data=None,
                config_dict=config.__dict__,
                objective_function_name="SpatialSimilarityObjective"
            )
            
            # Check results
            stats = result['simulation_stats']
            total_steps = stats.get('total_steps', 0)
            final_active = stats.get('final_active_cells', 0)
            max_active = stats.get('max_active_cells', 0)
            eval_time = result['evaluation_time']
            
            print(f"  ✅ Completed successfully")
            print(f"  Total steps: {total_steps}")
            print(f"  Final active cells: {final_active}")
            print(f"  Max active cells: {max_active}")
            print(f"  Evaluation time: {eval_time:.2f}s")
            
            if total_steps > 0:
                print(f"  ✅ Simulation ran for {total_steps} steps")
            else:
                print(f"  ❌ Simulation did not run (0 steps)")
            
            results.append({
                'grid_size': grid_size,
                'success': True,
                'total_steps': total_steps,
                'final_active': final_active,
                'max_active': max_active,
                'eval_time': eval_time
            })
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            results.append({
                'grid_size': grid_size,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n📊 Grid Size Test Summary:")
    for result in results:
        if result['success']:
            print(f"  {result['grid_size']}: {result['total_steps']} steps, {result['max_active']} max active cells")
        else:
            print(f"  {result['grid_size']}: FAILED - {result['error']}")
    
    # Check if there's a pattern
    working_sizes = [r for r in results if r['success'] and r['total_steps'] > 0]
    failed_sizes = [r for r in results if not r['success'] or r['total_steps'] == 0]
    
    if failed_sizes:
        print(f"\n❌ Grid size issue detected!")
        print(f"  Working sizes: {[r['grid_size'] for r in working_sizes]}")
        print(f"  Failed sizes: {[r['grid_size'] for r in failed_sizes]}")
    else:
        print(f"\n✅ All grid sizes working!")
    
    return len(failed_sizes) == 0

if __name__ == "__main__":
    success = test_grid_size_issue()
    if success:
        print("\n🎉 Grid size test passed!")
    else:
        print("\n💥 Grid size test failed!")
