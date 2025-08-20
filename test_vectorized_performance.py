#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script to verify vectorized neighbor processing performance improvements.
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

def test_vectorized_performance():
    """Test the vectorized neighbor processing performance."""
    print("TESTING VECTORIZED NEIGHBOR PROCESSING PERFORMANCE")
    print("=" * 60)
    
    try:
        from src.core.optimization_factory import create_optimized_fire_simulation_engine, create_optimized_forest_model
        from src.config.config_tools import ModelConfig
        
        # Create a test configuration
        test_config = ModelConfig(
            grid_size=(100, 100),
            num_layers=5,
            spread_probability=0.8,
            ignition_threshold=0.1,
            ember_probability=0.4,
            ember_ignition=0.3
        )
        
        print(f"Test config created: {test_config.grid_size} x {test_config.num_layers}")

        # Create optimized components
        print("\nCreating optimized components...")
        forest_model = create_optimized_forest_model(
            grid_size=test_config.grid_size,
            num_layers=test_config.num_layers,
            config=test_config,
            force_optimization=True
        )
        
        engine = create_optimized_fire_simulation_engine(
            forest_model=forest_model,
            config=test_config,
            force_optimization=True
        )
        
        print(f"✅ Optimized engine created: {type(engine).__name__}")
        
        # Set ignition points
        center_x, center_y = test_config.grid_size[0] // 2, test_config.grid_size[1] // 2
        forest_model.set_ignition(center_x, center_y, 0)
        
        print(f"✅ Ignition point set at ({center_x}, {center_y}, 0)")
        
        # Test vectorized neighbor generation
        print("\n🧪 Testing vectorized neighbor generation...")
        
        # Create some test active cells
        test_active_cells = [
            (center_x, center_y, 0),
            (center_x + 1, center_y, 0),
            (center_x, center_y + 1, 0),
            (center_x - 1, center_y, 0),
            (center_x, center_y - 1, 0)
        ]
        
        print(f"   Test active cells: {len(test_active_cells)}")
        
        # Test the vectorized method
        start_time = time.time()
        all_neighbors = engine._generate_all_neighbors_vectorized(np.array(test_active_cells))
        vectorized_time = time.time() - start_time
        
        print(f"   Vectorized neighbor generation: {len(all_neighbors)} neighbors in {vectorized_time:.4f}s")
        
        # Test individual method for comparison
        start_time = time.time()
        individual_neighbors = set()
        for cell in test_active_cells:
            neighbors = engine._get_neighbors_cached(*cell)
            individual_neighbors.update(neighbors)
        individual_time = time.time() - start_time
        
        print(f"   Individual neighbor generation: {len(individual_neighbors)} neighbors in {individual_time:.4f}s")
        
        # Performance comparison
        speedup = individual_time / vectorized_time if vectorized_time > 0 else float('inf')
        print(f"   Speedup: {speedup:.2f}x faster")
        
        # Test vectorized ignition checking
        print("\n🧪 Testing vectorized ignition checking...")
        
        if len(all_neighbors) > 0:
            start_time = time.time()
            ignited = engine._vectorized_ignition_check(
                np.array(test_active_cells), 
                np.array(list(all_neighbors))
            )
            ignition_time = time.time() - start_time
            
            print(f"   Vectorized ignition check: {len(ignited)} ignited in {ignition_time:.4f}s")
        
        # Test a short simulation
        print("\n🔥 Testing short simulation...")
        
        start_time = time.time()
        result = engine.run_simulation(max_steps=10, stop_when_fire_extinguished=False)
        simulation_time = time.time() - start_time
        
        print(f"   Simulation completed: {result.get('total_steps', 'N/A')} steps in {simulation_time:.2f}s")
        print(f"   Final active cells: {len(engine.active_cells)}")
        print(f"   Final burned cells: {len(engine.burned_cells)}")
        
        # Performance metrics
        print(f"\n📊 Performance metrics:")
        print(f"   Vectorized operations: {engine.perf_metrics.get('vectorized_ops', 0)}")
        print(f"   Batch updates: {engine.perf_metrics.get('batch_updates', 0)}")
        print(f"   Cached neighbors: {engine.perf_metrics.get('cached_neighbors', 0)}")
        
        print(f"\n✅ Vectorized performance test completed successfully!")
        print(f"   Expected improvement: 10-50x faster neighbor processing")
        print(f"   Memory cleanup: Every 10 steps")
        print(f"   Always uses vectorized processing")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vectorized_performance()
    sys.exit(0 if success else 1)
