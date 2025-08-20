#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Performance improvement test - compare optimized vs standard engines.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_performance_improvement():
    """Test performance improvement between optimized and standard engines."""
    print("PERFORMANCE IMPROVEMENT TEST")
    print("=" * 60)
    
    try:
        from src.core.optimization_factory import create_optimized_fire_simulation_engine, create_optimized_forest_model
        from src.core.fire_simulation_engine import FireSimulationEngine
        from src.core.forest_model import MemoryOptimizedForestModel
        from src.config.config_tools import ModelConfig
        
        # Test configuration
        test_config = ModelConfig(
            grid_size=(200, 200),  # Larger grid for meaningful comparison
            num_layers=5,
            spread_probability=0.8,
            ignition_threshold=0.1,
            ember_probability=0.4,
            ember_ignition=0.3
        )
        
        print(f"Test config: {test_config.grid_size} x {test_config.num_layers} = {test_config.grid_size[0] * test_config.grid_size[1] * test_config.num_layers:,} cells")
        
        # Test 1: Standard Engine
        print("\n1. Testing STANDARD engine...")
        
        start_time = time.time()
        standard_model = MemoryOptimizedForestModel(
            grid_size=test_config.grid_size,
            num_layers=test_config.num_layers,
            config=test_config
        )
        standard_engine = FireSimulationEngine(
            forest_model=standard_model,
            config=test_config
        )
        
        # Set ignition point
        center_x, center_y = test_config.grid_size[0] // 2, test_config.grid_size[1] // 2
        standard_model.set_ignition(center_x, center_y, 0)
        
        # Run simulation
        start_sim = time.time()
        standard_result = standard_engine.run_simulation(max_steps=5, stop_when_fire_extinguished=False)
        standard_sim_time = time.time() - start_sim
        standard_total_time = time.time() - start_time
        
        print(f"   Standard setup time: {standard_total_time - standard_sim_time:.3f}s")
        print(f"   Standard simulation time: {standard_sim_time:.3f}s")
        print(f"   Standard burned cells: {len(standard_engine.burned_cells)}")
        print(f"   Standard active cells: {len(standard_engine.active_cells)}")
        
        # Test 2: Optimized Engine
        print("\n2. Testing OPTIMIZED engine...")
        
        start_time = time.time()
        optimized_model = create_optimized_forest_model(
            grid_size=test_config.grid_size,
            num_layers=test_config.num_layers,
            config=test_config,
            force_optimization=True
        )
        optimized_engine = create_optimized_fire_simulation_engine(
            forest_model=optimized_model,
            config=test_config,
            force_optimization=True
        )
        
        # Set ignition point
        optimized_model.set_ignition(center_x, center_y, 0)
        
        # Run simulation
        start_sim = time.time()
        optimized_result = optimized_engine.run_simulation(max_steps=5, stop_when_fire_extinguished=False)
        optimized_sim_time = time.time() - start_sim
        optimized_total_time = time.time() - start_time
        
        print(f"   Optimized setup time: {optimized_total_time - optimized_sim_time:.3f}s")
        print(f"   Optimized simulation time: {optimized_sim_time:.3f}s")
        print(f"   Optimized burned cells: {len(optimized_engine.burned_cells)}")
        print(f"   Optimized active cells: {len(optimized_engine.active_cells)}")
        
        # Performance comparison
        print("\n3. PERFORMANCE COMPARISON")
        print("-" * 40)
        
        setup_speedup = standard_total_time / optimized_total_time if optimized_total_time > 0 else float('inf')
        sim_speedup = standard_sim_time / optimized_sim_time if optimized_sim_time > 0 else float('inf')
        
        print(f"   Setup speedup: {setup_speedup:.2f}x")
        print(f"   Simulation speedup: {sim_speedup:.2f}x")
        
        # Check if optimization metrics are available
        if hasattr(optimized_engine, 'perf_metrics'):
            print(f"   Vectorized operations: {optimized_engine.perf_metrics.get('vectorized_ops', 0)}")
            print(f"   Batch updates: {optimized_engine.perf_metrics.get('batch_updates', 0)}")
        
        # Success criteria
        significant_improvement = sim_speedup > 1.5 or optimized_sim_time < 0.5
        
        if significant_improvement:
            print(f"\nSUCCESS: Optimized engine shows significant improvement!")
            print(f"   Original concern: '2-3 mins per 5 timesteps'")
            print(f"   Optimized result: {optimized_sim_time:.3f}s per 5 timesteps")
            
            if optimized_sim_time < 60:  # Less than 1 minute
                improvement_factor = 120 / optimized_sim_time  # Assuming 2 min baseline
                print(f"   Estimated improvement: {improvement_factor:.1f}x faster")
        else:
            print(f"\nWARNING: Performance improvement is marginal")
            print(f"   Consider further optimizations")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_performance_improvement()
    sys.exit(0 if success else 1)
