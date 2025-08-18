#!/usr/bin/env python3
"""
Debug script to isolate the issue with advanced features.
"""

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig

def debug_advanced_features_issue():
    """Debug the issue with advanced features."""
    
    print("🔍 Debugging advanced features issue...")
    
    # Test different configurations to isolate the issue
    test_configs = [
        {
            'name': 'Basic (Working)',
            'config': {
                'grid_size': (50, 50),
                'num_layers': 3,
                'max_steps': 10,
                'spread_probability': 0.8,
                'fuel_consumption_rate': 0.01,
                'ignition_threshold': 0.1,
                'wind_speed': 0.0,
                'wind_direction': 0.0,
                'store_full_states': False,
                'stop_when_fire_extinguished': False
            }
        },
        {
            'name': '5 Layers',
            'config': {
                'grid_size': (50, 50),
                'num_layers': 5,  # Changed from 3 to 5
                'max_steps': 10,
                'spread_probability': 0.8,
                'fuel_consumption_rate': 0.01,
                'ignition_threshold': 0.1,
                'wind_speed': 0.0,
                'wind_direction': 0.0,
                'store_full_states': False,
                'stop_when_fire_extinguished': False
            }
        },
        {
            'name': 'Advanced Fire Params',
            'config': {
                'grid_size': (50, 50),
                'num_layers': 3,
                'max_steps': 10,
                'spread_probability': 0.7,  # Changed from 0.8
                'fuel_consumption_rate': 0.05,  # Changed from 0.01
                'ignition_threshold': 0.2,  # Changed from 0.1
                'wind_speed': 0.0,
                'wind_direction': 0.0,
                'store_full_states': False,
                'stop_when_fire_extinguished': False
            }
        },
        {
            'name': 'With Ember Params',
            'config': {
                'grid_size': (50, 50),
                'num_layers': 3,
                'max_steps': 10,
                'spread_probability': 0.8,
                'fuel_consumption_rate': 0.01,
                'ignition_threshold': 0.1,
                'ember_probability': 0.3,  # Added ember parameter
                'ember_distance': 8,
                'ember_ignition': 0.4,
                'wind_speed': 0.0,
                'wind_direction': 0.0,
                'store_full_states': False,
                'stop_when_fire_extinguished': False
            }
        },
        {
            'name': 'With Terrain Params',
            'config': {
                'grid_size': (50, 50),
                'num_layers': 3,
                'max_steps': 10,
                'spread_probability': 0.8,
                'fuel_consumption_rate': 0.01,
                'ignition_threshold': 0.1,
                'slope_influence': 0.4,  # Added terrain parameter
                'wind_influence_on_spread': 0.6,
                'terrain_effect_strength': 0.8,
                'wind_speed': 0.0,
                'wind_direction': 0.0,
                'store_full_states': False,
                'stop_when_fire_extinguished': False
            }
        }
    ]
    
    results = []
    
    for test_config in test_configs:
        print(f"\n--- Testing: {test_config['name']} ---")
        
        # Create config
        config = ModelConfig(**test_config['config'])
        
        # Test parameters (use same as config)
        params = {
            'spread_probability': config.spread_probability,
            'fuel_consumption_rate': config.fuel_consumption_rate,
            'ignition_threshold': config.ignition_threshold
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
                'name': test_config['name'],
                'success': True,
                'total_steps': total_steps,
                'final_active': final_active,
                'max_active': max_active,
                'eval_time': eval_time
            })
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            results.append({
                'name': test_config['name'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n📊 Advanced Features Debug Summary:")
    for result in results:
        if result['success']:
            print(f"  {result['name']}: {result['total_steps']} steps, {result['max_active']} max active cells")
        else:
            print(f"  {result['name']}: FAILED - {result['error']}")
    
    # Check which configuration breaks
    working_configs = [r for r in results if r['success'] and r['total_steps'] > 0]
    failed_configs = [r for r in results if not r['success'] or r['total_steps'] == 0]
    
    if failed_configs:
        print(f"\n❌ Issue identified!")
        print(f"  Working configs: {[r['name'] for r in working_configs]}")
        print(f"  Failed configs: {[r['name'] for r in failed_configs]}")
    else:
        print(f"\n✅ All configurations working!")
    
    return len(failed_configs) == 0

if __name__ == "__main__":
    success = debug_advanced_features_issue()
    if success:
        print("\n🎉 Advanced features debug passed!")
    else:
        print("\n💥 Advanced features debug failed!")
