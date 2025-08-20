#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug script to identify parameter sensitivity issues in worker iterations.
"""

import os
import sys
import time
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def debug_parameter_sensitivity():
    """Debug why worker iterations produce the same results."""
    print("🔍 DEBUGGING PARAMETER SENSITIVITY ISSUE")
    print("=" * 60)
    
    try:
        from src.core.optimization_factory import create_optimized_fire_simulation_engine, create_optimized_forest_model
        from src.config.config_tools import ModelConfig
        
        # Test different parameter combinations
        test_configs = [
            {
                'name': 'Conservative',
                'spread_probability': 0.3,
                'fuel_consumption_rate': 0.8,
                'ember_probability': 0.1,
                'wind_speed': 5.0
            },
            {
                'name': 'Aggressive', 
                'spread_probability': 0.9,
                'fuel_consumption_rate': 0.2,
                'ember_probability': 0.6,
                'wind_speed': 15.0
            },
            {
                'name': 'Balanced',
                'spread_probability': 0.6,
                'fuel_consumption_rate': 0.5,
                'ember_probability': 0.3,
                'wind_speed': 10.0
            },
            {
                'name': 'High Wind',
                'spread_probability': 0.7,
                'fuel_consumption_rate': 0.4,
                'ember_probability': 0.4,
                'wind_speed': 25.0
            },
            {
                'name': 'Low Wind',
                'spread_probability': 0.7,
                'fuel_consumption_rate': 0.4,
                'ember_probability': 0.4,
                'wind_speed': 1.0
            }
        ]
        
        results = []
        
        for i, config_params in enumerate(test_configs):
            print(f"\n🧪 Testing {config_params['name']} configuration...")
            
            # Create base config
            base_config = ModelConfig(
                grid_size=(100, 100),
                num_layers=5,
                max_steps=20,
                stop_when_fire_extinguished=False,
                random_seed=42 + i  # Different seed for each test
            )
            
            # Apply test parameters
            for param, value in config_params.items():
                if param != 'name':
                    setattr(base_config, param, value)
            
            print(f"   Parameters: spread_prob={base_config.spread_probability}, "
                  f"fuel_cons={base_config.fuel_consumption_rate}, "
                  f"ember_prob={base_config.ember_probability}, "
                  f"wind_speed={base_config.wind_speed}")
            
            # Create optimized components
            forest_model = create_optimized_forest_model(
                grid_size=base_config.grid_size,
                num_layers=base_config.num_layers,
                config=base_config,
                force_optimization=True
            )
            
            engine = create_optimized_fire_simulation_engine(
                forest_model=forest_model,
                config=base_config,
                force_optimization=True
            )
            
            # Set ignition point
            center_x, center_y = base_config.grid_size[0] // 2, base_config.grid_size[1] // 2
            forest_model.set_ignition(center_x, center_y, 0)
            
            # Run simulation
            start_time = time.time()
            result = engine.run_simulation(max_steps=20, stop_when_fire_extinguished=False)
            sim_time = time.time() - start_time
            
            # Collect results
            final_active = len(engine.active_cells)
            final_burned = len(engine.burned_cells)
            total_steps = result.get('total_steps', 0)
            
            test_result = {
                'name': config_params['name'],
                'final_active': final_active,
                'final_burned': final_burned,
                'total_steps': total_steps,
                'sim_time': sim_time,
                'params': config_params
            }
            
            results.append(test_result)
            
            print(f"   Results: {final_active} active, {final_burned} burned, {total_steps} steps, {sim_time:.3f}s")
        
        # Analyze results
        print(f"\n📊 PARAMETER SENSITIVITY ANALYSIS")
        print("=" * 60)
        
        # Check for identical results
        active_counts = [r['final_active'] for r in results]
        burned_counts = [r['final_burned'] for r in results]
        
        if len(set(active_counts)) == 1 and len(set(burned_counts)) == 1:
            print("❌ CRITICAL ISSUE: All configurations produced identical results!")
            print(f"   Active cells: {active_counts[0]} (all identical)")
            print(f"   Burned cells: {burned_counts[0]} (all identical)")
            print("\n🔧 POTENTIAL CAUSES:")
            print("   1. Random seed not being used properly")
            print("   2. Parameters not being applied to engine")
            print("   3. Simulation ending too early")
            print("   4. Fire extinguishing immediately")
            print("   5. Parameter bounds too narrow")
        else:
            print("✅ Parameter sensitivity detected!")
            print(f"   Active cells range: {min(active_counts)} to {max(active_counts)}")
            print(f"   Burned cells range: {min(burned_counts)} to {max(burned_counts)}")
        
        # Detailed analysis
        print(f"\n📋 DETAILED RESULTS:")
        for result in results:
            print(f"   {result['name']:12}: {result['final_active']:4} active, "
                  f"{result['final_burned']:4} burned, {result['total_steps']:2} steps")
        
        # Check for simulation issues
        print(f"\n🔍 SIMULATION ISSUES:")
        for result in results:
            if result['final_active'] == 0 and result['final_burned'] < 10:
                print(f"   ❌ {result['name']}: Fire extinguished too quickly")
            elif result['final_active'] > 1000:
                print(f"   ⚠️  {result['name']}: Fire spread too aggressively")
            elif result['total_steps'] < 5:
                print(f"   ⚠️  {result['name']}: Simulation ended too early")
        
        return results
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = debug_parameter_sensitivity()
    if results:
        print(f"\n✅ Debug completed with {len(results)} test configurations")
    else:
        print(f"\n❌ Debug failed")
    sys.exit(0 if results else 1)
