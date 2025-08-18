#!/usr/bin/env python3
"""
Comprehensive test to verify embers, terrain effects, and vertical fire spread are working.
"""

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig

def test_advanced_features():
    """Test that embers, terrain effects, and vertical fire spread are working."""
    
    print("🧪 Testing Advanced Features: Embers, Terrain, Vertical Spread...")
    
    # Create a config with all advanced features enabled
    config = ModelConfig(
        grid_size=(50, 50),  # Medium grid for testing
        num_layers=5,  # Multiple layers for vertical spread
        max_steps=20,
        simulation_type='memory_optimized',
        
        # Fire parameters
        spread_probability=0.7,
        fuel_consumption_rate=0.05,
        ignition_threshold=0.2,
        min_fuel_value=0.1,
        max_fuel_value=1.0,
        
        # Wind and terrain effects
        wind_speed=8.0,
        wind_direction=45.0,
        slope_influence=0.4,
        wind_influence_on_spread=0.6,
        terrain_effect_strength=0.8,
        
        # Ember parameters
        ember_probability=0.3,
        ember_distance=8,
        ember_ignition=0.4,
        ember_height_factor=0.5,
        ember_wind_factor=0.7,
        ember_rise=3,
        
        # Memory optimizations
        memory_optimization_level=2,
        
        # Simulation control
        stop_when_fire_extinguished=False,
        store_full_states=False
    )
    
    # Test parameters
    params = {
        'spread_probability': 0.7,
        'fuel_consumption_rate': 0.05,
        'ignition_threshold': 0.2,
        'ember_probability': 0.3,
        'ember_distance': 8,
        'ember_ignition': 0.4,
        'slope_influence': 0.4,
        'wind_influence_on_spread': 0.6,
        'terrain_effect_strength': 0.8
    }
    
    print("📋 Configuration:")
    print(f"  Grid size: {config.grid_size}")
    print(f"  Layers: {config.num_layers}")
    print(f"  Max steps: {config.max_steps}")
    print(f"  Ember probability: {config.ember_probability}")
    print(f"  Ember distance: {config.ember_distance}")
    print(f"  Terrain effect strength: {config.terrain_effect_strength}")
    print(f"  Wind influence: {config.wind_influence_on_spread}")
    print(f"  Slope influence: {config.slope_influence}")
    
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
        print(f"  Final active cells: {stats.get('final_active_cells', 0)}")
        print(f"  Total burned cells: {stats.get('total_burned_cells', 0)}")
        print(f"  Max active cells: {stats.get('max_active_cells', 0)}")
        print(f"  Evaluation time: {result['evaluation_time']:.2f}s")
        
        # Check for advanced features
        print(f"\n🔧 Advanced Features Analysis:")
        
        # Check ember statistics
        ember_stats = stats.get('ember_statistics', {})
        if ember_stats:
            print(f"  📊 Ember Statistics:")
            print(f"    Total generated: {ember_stats.get('total_generated', 0)}")
            print(f"    Successful ignitions: {ember_stats.get('successful_ignitions', 0)}")
            print(f"    Failed attempts: {ember_stats.get('failed_attempts', 0)}")
            print(f"    Average distance: {ember_stats.get('average_distance', 0):.2f}")
            
            if ember_stats.get('total_generated', 0) > 0:
                print(f"    ✅ Ember generation: Working")
            else:
                print(f"    ❌ Ember generation: Not working")
        else:
            print(f"  ❌ Ember statistics: Not available")
        
        # Check spread statistics
        spread_stats = stats.get('spread_statistics', {})
        if spread_stats:
            print(f"  📊 Spread Statistics:")
            print(f"    Horizontal spread: {spread_stats.get('horizontal_spread', 0)}")
            print(f"    Vertical spread: {spread_stats.get('vertical_spread', 0)}")
            print(f"    Ember spread: {spread_stats.get('ember_spread', 0)}")
            print(f"    Diagonal spread: {spread_stats.get('diagonal_spread', 0)}")
            
            if spread_stats.get('vertical_spread', 0) > 0:
                print(f"    ✅ Vertical fire spread: Working")
            else:
                print(f"    ❌ Vertical fire spread: Not working")
                
            if spread_stats.get('ember_spread', 0) > 0:
                print(f"    ✅ Ember-caused spread: Working")
            else:
                print(f"    ❌ Ember-caused spread: Not working")
        else:
            print(f"  ❌ Spread statistics: Not available")
        
        # Check terrain effects
        terrain_info = stats.get('terrain_info', {})
        if terrain_info:
            print(f"  🏔️ Terrain Information:")
            print(f"    Terrain loaded: {terrain_info.get('terrain_loaded', False)}")
            print(f"    Elevation range: {terrain_info.get('elevation_range', 'N/A')}")
            print(f"    Slope effects: {terrain_info.get('slope_effects_enabled', False)}")
            
            if terrain_info.get('terrain_loaded', False):
                print(f"    ✅ Terrain data: Loaded")
            else:
                print(f"    ❌ Terrain data: Not loaded")
        else:
            print(f"  ❌ Terrain information: Not available")
        
        # Check wind effects
        wind_info = stats.get('wind_info', {})
        if wind_info:
            print(f"  💨 Wind Information:")
            print(f"    Wind field initialized: {wind_info.get('wind_initialized', False)}")
            print(f"    Wind speed range: {wind_info.get('wind_speed_range', 'N/A')}")
            print(f"    Terrain-modified wind: {wind_info.get('terrain_modified_wind', False)}")
            
            if wind_info.get('wind_initialized', False):
                print(f"    ✅ Wind effects: Working")
            else:
                print(f"    ❌ Wind effects: Not working")
        else:
            print(f"  ❌ Wind information: Not available")
        
        # Overall assessment
        print(f"\n📈 Feature Assessment:")
        
        features_working = 0
        total_features = 4
        
        # Check if features are working based on available data
        if ember_stats and ember_stats.get('total_generated', 0) > 0:
            features_working += 1
            print(f"  ✅ Embers: Working")
        else:
            print(f"  ❌ Embers: Not working or no data")
            
        if spread_stats and spread_stats.get('vertical_spread', 0) > 0:
            features_working += 1
            print(f"  ✅ Vertical spread: Working")
        else:
            print(f"  ❌ Vertical spread: Not working or no data")
            
        if terrain_info and terrain_info.get('terrain_loaded', False):
            features_working += 1
            print(f"  ✅ Terrain effects: Working")
        else:
            print(f"  ❌ Terrain effects: Not working or no data")
            
        if wind_info and wind_info.get('wind_initialized', False):
            features_working += 1
            print(f"  ✅ Wind effects: Working")
        else:
            print(f"  ❌ Wind effects: Not working or no data")
        
        print(f"\n  Working features: {features_working}/{total_features}")
        print(f"  Success rate: {(features_working/total_features)*100:.1f}%")
        
        if features_working >= 3:
            print(f"  🎉 Advanced features are mostly working!")
        elif features_working >= 2:
            print(f"  ⚠️  Some advanced features are working")
        else:
            print(f"  💥 Most advanced features are not working")
        
        return features_working >= 2
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_advanced_features()
    if success:
        print("\n🎉 Advanced features test passed!")
    else:
        print("\n💥 Advanced features test failed!")
