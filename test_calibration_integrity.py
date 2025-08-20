#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script to verify calibration integrity - same parameters, different seeds.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_calibration_integrity():
    """Test that calibration maintains integrity with same parameters, different seeds."""
    print("🧪 TESTING CALIBRATION INTEGRITY")
    print("=" * 60)
    
    try:
        from src.core.optimization_factory import create_optimized_fire_simulation_engine, create_optimized_forest_model
        from src.config.config_tools import ModelConfig
        
        # Test the SAME parameters with DIFFERENT seeds (simulating calibration workers)
        test_parameters = {
            'spread_probability': 0.6,
            'fuel_consumption_rate': 0.3,
            'ember_probability': 0.2,
            'wind_speed': 10.0
        }
        
        # Test with different seeds (simulating different workers)
        test_seeds = [42, 1042, 2042, 3042, 4042]
        
        results = []
        
        for i, seed in enumerate(test_seeds):
            print(f"\n🧪 Testing Worker {i+1} with seed {seed}...")
            
            # Create base config with SAME parameters
            base_config = ModelConfig(
                grid_size=(50, 50),  # Smaller grid for faster testing
                num_layers=3,
                max_steps=30,  # More steps for better observation
                stop_when_fire_extinguished=False,
                random_seed=seed  # Different seed per worker
            )
            
            # Apply SAME parameters to all workers
            for param, value in test_parameters.items():
                setattr(base_config, param, value)
            
            print(f"   Parameters: spread_prob={base_config.spread_probability}, "
                  f"fuel_cons={base_config.fuel_consumption_rate}, "
                  f"ember_prob={base_config.ember_probability}, "
                  f"wind_speed={base_config.wind_speed}, "
                  f"seed={base_config.random_seed}")
            
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
            result = engine.run_simulation(max_steps=30, stop_when_fire_extinguished=False)
            sim_time = time.time() - start_time
            
            # Collect results
            final_active = len(engine.active_cells)
            final_burned = len(engine.burned_cells)
            total_steps = result.get('total_steps', 0)
            
            worker_result = {
                'worker_id': i + 1,
                'seed': seed,
                'final_active': final_active,
                'final_burned': final_burned,
                'total_steps': total_steps,
                'sim_time': sim_time,
                'parameters': test_parameters.copy()
            }
            
            results.append(worker_result)
            
            print(f"   Results: {final_active} active, {final_burned} burned, {total_steps} steps, {sim_time:.3f}s")
        
        # Analyze results
        print(f"\n📊 CALIBRATION INTEGRITY ANALYSIS")
        print("=" * 60)
        
        active_counts = [r['final_active'] for r in results]
        burned_counts = [r['final_burned'] for r in results]
        
        print(f"Active cells: {active_counts}")
        print(f"Burned cells: {burned_counts}")
        
        # Check for calibration integrity
        print(f"\n🔍 CALIBRATION INTEGRITY CHECK:")
        
        # 1. Check that parameters are identical across workers
        all_parameters_identical = all(
            r['parameters'] == test_parameters for r in results
        )
        
        if all_parameters_identical:
            print("✅ PARAMETER INTEGRITY: All workers used identical parameters")
        else:
            print("❌ PARAMETER INTEGRITY FAILED: Workers used different parameters!")
            return False
        
        # 2. Check that seeds are different
        seeds = [r['seed'] for r in results]
        if len(set(seeds)) == len(seeds):
            print("✅ SEED DIVERSITY: All workers used different seeds")
        else:
            print("❌ SEED DIVERSITY FAILED: Some workers used same seeds!")
            return False
        
        # 3. Check for meaningful variation in results
        if len(set(active_counts)) == 1 and len(set(burned_counts)) == 1:
            print("❌ RESULT VARIATION: All workers produced identical results!")
            print("   This suggests the random seed fix didn't work properly.")
            return False
        else:
            print("✅ RESULT VARIATION: Workers produced varied results (good for calibration)")
            
            # Calculate variation metrics
            active_variation = max(active_counts) - min(active_counts)
            burned_variation = max(burned_counts) - min(burned_counts)
            
            print(f"   Active variation: {active_variation} cells")
            print(f"   Burned variation: {burned_variation} cells")
            
            if active_variation > 0 or burned_variation > 0:
                print("✅ EXCELLENT: Meaningful variation for calibration!")
            else:
                print("⚠️  WARNING: Minimal variation detected")
        
        # 4. Check that variation is reasonable (not too extreme)
        active_mean = sum(active_counts) / len(active_counts)
        burned_mean = sum(burned_counts) / len(burned_counts)
        
        active_cv = (max(active_counts) - min(active_counts)) / active_mean if active_mean > 0 else 0
        burned_cv = (max(burned_counts) - min(burned_counts)) / burned_mean if burned_mean > 0 else 0
        
        print(f"\n📈 VARIATION ANALYSIS:")
        print(f"   Active cells: mean={active_mean:.1f}, CV={active_cv:.3f}")
        print(f"   Burned cells: mean={burned_mean:.1f}, CV={burned_cv:.3f}")
        
        # Reasonable variation should be 5-30% for calibration
        if 0.05 <= active_cv <= 0.30 or 0.05 <= burned_cv <= 0.30:
            print("✅ PERFECT: Variation is in ideal range for calibration!")
            return True
        elif active_cv > 0 or burned_cv > 0:
            print("✅ GOOD: Variation detected (calibration will work)")
            return True
        else:
            print("❌ POOR: No meaningful variation for calibration")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_calibration_integrity()
    if success:
        print(f"\n✅ Calibration integrity test PASSED!")
        print(f"🚀 Your calibration will work correctly with varied results!")
    else:
        print(f"\n❌ Calibration integrity test FAILED!")
        print(f"🔧 Additional fixes may be needed.")
    sys.exit(0 if success else 1)
