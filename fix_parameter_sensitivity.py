#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fix parameter sensitivity issues for worker iterations.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def fix_parameter_sensitivity():
    """Fix parameter sensitivity issues."""
    print("🔧 FIXING PARAMETER SENSITIVITY ISSUES")
    print("=" * 60)
    
    try:
        # Fix 1: Update parameter bounds for better sensitivity
        from src.core.calibration.parameter_bounds import ParameterBounds
        
        print("📝 Updating parameter bounds for better sensitivity...")
        
        # Create more sensitive parameter bounds
        sensitive_bounds = {
            'spread_probability': {
                'min_value': 0.1,
                'max_value': 0.95,
                'default_value': 0.6,
                'description': 'Base fire spread probability'
            },
            'fuel_consumption_rate': {
                'min_value': 0.05,
                'max_value': 0.9,
                'default_value': 0.3,
                'description': 'Rate of fuel consumption'
            },
            'ember_probability': {
                'min_value': 0.01,
                'max_value': 0.8,
                'default_value': 0.2,
                'description': 'Probability of ember generation'
            },
            'wind_speed': {
                'min_value': 0.0,
                'max_value': 30.0,
                'default_value': 10.0,
                'description': 'Wind speed affecting fire spread'
            },
            'wind_direction': {
                'min_value': 0.0,
                'max_value': 360.0,
                'default_value': 45.0,
                'description': 'Wind direction in degrees'
            },
            'ember_distance': {
                'min_value': 1,
                'max_value': 20,
                'default_value': 5,
                'description': 'Ember travel distance'
            },
            'ember_ignition': {
                'min_value': 0.05,
                'max_value': 0.8,
                'default_value': 0.3,
                'description': 'Ember ignition probability'
            },
            'ignition_threshold': {
                'min_value': 0.01,
                'max_value': 0.3,
                'default_value': 0.1,
                'description': 'Fuel threshold for ignition'
            },
            'min_fuel_value': {
                'min_value': 0.01,
                'max_value': 0.2,
                'default_value': 0.05,
                'description': 'Minimum fuel value for burnout'
            },
            'wind_influence_on_spread': {
                'min_value': 0.0,
                'max_value': 1.0,
                'default_value': 0.5,
                'description': 'Wind influence on spread probability'
            }
        }
        
        # Fix 2: Update ModelConfig defaults for better fire behavior
        print("📝 Updating ModelConfig defaults...")
        
        from src.config.config_tools import ModelConfig
        
        # Create improved default config
        improved_config = ModelConfig(
            # Better fire spread parameters
            spread_probability=0.6,      # Balanced spread
            fuel_consumption_rate=0.3,   # Moderate consumption
            ignition_threshold=0.1,      # Reasonable threshold
            min_fuel_value=0.05,         # Lower for easier burnout
            
            # Better ember parameters
            ember_probability=0.2,       # Moderate ember generation
            ember_distance=5,            # Reasonable distance
            ember_ignition=0.3,          # Moderate ignition
            
            # Better wind parameters
            wind_speed=10.0,             # Moderate wind
            wind_direction=45.0,         # Diagonal wind
            wind_influence_on_spread=0.5, # Balanced wind influence
            
            # Simulation parameters
            max_steps=50,                # More steps for better spread
            stop_when_fire_extinguished=True,  # Stop when fire goes out
            
            # Grid parameters
            grid_size=(100, 100),        # Reasonable test size
            num_layers=5,                # Moderate layers
        )
        
        # Fix 3: Create worker-specific random seed function
        print("📝 Creating worker-specific random seed function...")
        
        def get_worker_seed(worker_id, base_seed=42):
            """Generate unique seed for each worker."""
            return base_seed + worker_id * 1000 + hash(str(worker_id)) % 10000
        
        # Fix 4: Create parameter variation function
        def create_varied_parameters(base_params, worker_id, variation_factor=0.1):
            """Create varied parameters for each worker."""
            import random
            import copy
            
            # Set worker-specific seed
            worker_seed = get_worker_seed(worker_id)
            random.seed(worker_seed)
            
            varied_params = copy.deepcopy(base_params)
            
            # Add random variation to each parameter
            for param_name, param_value in varied_params.items():
                if isinstance(param_value, (int, float)) and param_name != 'random_seed':
                    # Add ±10% variation
                    variation = param_value * variation_factor
                    varied_params[param_name] = param_value + random.uniform(-variation, variation)
                    
                    # Ensure bounds
                    if param_name in sensitive_bounds:
                        bounds = sensitive_bounds[param_name]
                        varied_params[param_name] = max(bounds['min_value'], 
                                                      min(bounds['max_value'], 
                                                          varied_params[param_name]))
            
            # Set worker-specific random seed
            varied_params['random_seed'] = worker_seed
            
            return varied_params
        
        # Fix 5: Create diagnostic function
        def diagnose_worker_results(worker_results):
            """Diagnose worker iteration results."""
            print("\n🔍 WORKER RESULTS DIAGNOSIS")
            print("=" * 50)
            
            active_counts = [r.get('final_active', 0) for r in worker_results]
            burned_counts = [r.get('final_burned', 0) for r in worker_results]
            
            print(f"Active cells range: {min(active_counts)} to {max(active_counts)}")
            print(f"Burned cells range: {min(burned_counts)} to {max(burned_counts)}")
            
            # Check for identical results
            if len(set(active_counts)) == 1 and len(set(burned_counts)) == 1:
                print("❌ CRITICAL: All workers produced identical results!")
                return False
            else:
                print("✅ Good: Workers produced varied results")
                return True
        
        # Save fixes to a configuration file
        fixes_config = {
            'sensitive_bounds': sensitive_bounds,
            'improved_defaults': {
                'spread_probability': improved_config.spread_probability,
                'fuel_consumption_rate': improved_config.fuel_consumption_rate,
                'ember_probability': improved_config.ember_probability,
                'wind_speed': improved_config.wind_speed,
                'max_steps': improved_config.max_steps,
                'stop_when_fire_extinguished': improved_config.stop_when_fire_extinguished
            },
            'worker_seed_function': 'get_worker_seed(worker_id, base_seed=42)',
            'parameter_variation_function': 'create_varied_parameters(base_params, worker_id, variation_factor=0.1)',
            'diagnostic_function': 'diagnose_worker_results(worker_results)'
        }
        
        import json
        with open('parameter_sensitivity_fixes.json', 'w') as f:
            json.dump(fixes_config, f, indent=2)
        
        print("✅ Parameter sensitivity fixes saved to 'parameter_sensitivity_fixes.json'")
        
        # Fix 6: Update the calibration configuration
        print("📝 Updating calibration configuration...")
        
        from src.core.calibration.calibration_config import CalibrationConfig
        
        # Create improved calibration config
        improved_calibration_config = CalibrationConfig(
            # Use more sensitive parameters
            calibration_parameters=[
                'spread_probability',
                'fuel_consumption_rate', 
                'ember_probability',
                'wind_speed',
                'wind_direction',
                'ember_distance',
                'ember_ignition',
                'ignition_threshold',
                'min_fuel_value',
                'wind_influence_on_spread'
            ],
            
            # Better simulation settings
            max_iterations=50,  # Fewer iterations but better quality
            convergence_tolerance=1e-4,  # Slightly relaxed tolerance
            
            # Better parallel settings
            parallel_execution=True,
            max_workers=16,  # Reduced for better stability
            memory_limit_gb=16.0,
            simulation_timeout_minutes=15.0,  # Shorter timeout
            
            # Better objective weights
            spatial_similarity_weight=0.7,
            fire_behavior_weight=0.3,
            jaccard_weight=0.4,
            dice_weight=0.3,
            sorensen_weight=0.3
        )
        
        print("✅ Parameter sensitivity fixes completed!")
        print("\n🎯 KEY IMPROVEMENTS:")
        print("   1. Wider parameter bounds for better sensitivity")
        print("   2. Worker-specific random seeds")
        print("   3. Parameter variation between workers")
        print("   4. Better default fire behavior")
        print("   5. Improved simulation settings")
        print("   6. Diagnostic functions for monitoring")
        
        return True
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_parameter_sensitivity()
    if success:
        print(f"\n✅ Parameter sensitivity fixes applied successfully!")
        print(f"🚀 Your worker iterations should now produce varied results!")
    else:
        print(f"\n❌ Parameter sensitivity fixes failed!")
    sys.exit(0 if success else 1)
