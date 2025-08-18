#!/usr/bin/env python3
"""
Comprehensive test to verify all simulation logic is working in calibration.
"""

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig

def test_calibration_comprehensive():
    """Test that all simulation logic is working in calibration."""
    
    print("🧪 Comprehensive calibration test...")
    
    # Create a realistic config for calibration
    config = ModelConfig(
        grid_size=(100, 100),  # Larger grid for realistic testing
        num_layers=3,
        max_steps=50,  # More steps to see fire spread
        simulation_type='memory_optimized',
        
        # Realistic fire parameters
        spread_probability=0.6,
        fuel_consumption_rate=0.1,
        ignition_threshold=0.3,
        min_fuel_value=0.05,
        max_fuel_value=1.0,
        
        # Wind and terrain effects
        wind_speed=5.0,
        wind_direction=45.0,
        slope_influence=0.2,
        wind_influence_on_spread=0.3,
        
        # Memory optimizations
        memory_optimization_level=2,
        
        # Simulation control
        stop_when_fire_extinguished=True,
        store_full_states=False  # Disable history to avoid sparse copy issues
    )
    
    # Test multiple parameter combinations
    test_cases = [
        {
            'name': 'High Spread',
            'params': {
                'spread_probability': 0.8,
                'fuel_consumption_rate': 0.05,
                'ignition_threshold': 0.1
            }
        },
        {
            'name': 'Low Spread',
            'params': {
                'spread_probability': 0.3,
                'fuel_consumption_rate': 0.2,
                'ignition_threshold': 0.5
            }
        },
        {
            'name': 'Balanced',
            'params': {
                'spread_probability': 0.6,
                'fuel_consumption_rate': 0.1,
                'ignition_threshold': 0.3
            }
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1}: {test_case['name']} ---")
        
        try:
            # Run evaluation
            result = evaluate_worker_function(
                parameter_values=test_case['params'],
                target_data=None,
                config_dict=config.__dict__,
                objective_function_name="SpatialSimilarityObjective"
            )
            
            # Extract stats
            stats = result['simulation_stats']
            
            print(f"✅ {test_case['name']} completed successfully!")
            print(f"  Valid: {result['is_valid']}")
            print(f"  Objective: {result['objective_value']:.4f}")
            print(f"  Evaluation time: {result['evaluation_time']:.2f}s")
            print(f"  Total steps: {stats.get('total_steps', 0)}")
            print(f"  Final active cells: {stats.get('final_active_cells', 0)}")
            print(f"  Total burned cells: {stats.get('total_burned_cells', 0)}")
            print(f"  Max active cells: {stats.get('max_active_cells', 0)}")
            
            # Verify simulation behavior
            if stats.get('total_steps', 0) > 1:
                print(f"  ✅ Fire spread occurred over {stats.get('total_steps', 0)} steps")
            else:
                print(f"  ⚠️  Fire ended early after {stats.get('total_steps', 0)} steps")
                
            if stats.get('total_burned_cells', 0) > 0:
                print(f"  ✅ Fire burned {stats.get('total_burned_cells', 0)} cells")
            else:
                print(f"  ⚠️  No cells burned")
            
            results.append({
                'name': test_case['name'],
                'success': True,
                'stats': stats,
                'result': result
            })
            
        except Exception as e:
            print(f"❌ {test_case['name']} failed: {e}")
            results.append({
                'name': test_case['name'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"  Total tests: {len(test_cases)}")
    successful = sum(1 for r in results if r['success'])
    print(f"  Successful: {successful}")
    print(f"  Failed: {len(test_cases) - successful}")
    
    if successful > 0:
        # Analyze successful results
        avg_steps = sum(r['stats'].get('total_steps', 0) for r in results if r['success']) / successful
        avg_burned = sum(r['stats'].get('total_burned_cells', 0) for r in results if r['success']) / successful
        avg_time = sum(r['result']['evaluation_time'] for r in results if r['success']) / successful
        
        print(f"  Average steps: {avg_steps:.1f}")
        print(f"  Average burned cells: {avg_burned:.1f}")
        print(f"  Average evaluation time: {avg_time:.2f}s")
        
        # Check if simulations are behaving differently with different parameters
        step_counts = [r['stats'].get('total_steps', 0) for r in results if r['success']]
        if len(set(step_counts)) > 1:
            print(f"  ✅ Parameter changes affect simulation behavior")
        else:
            print(f"  ⚠️  All simulations had same step count")
    
    return successful == len(test_cases)

if __name__ == "__main__":
    success = test_calibration_comprehensive()
    if success:
        print("\n🎉 All calibration tests passed!")
    else:
        print("\n💥 Some calibration tests failed!")
