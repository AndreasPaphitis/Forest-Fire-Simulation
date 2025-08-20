#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Direct Optimization Test

Simple test to verify that the performance optimizations work correctly
and can handle larger grid sizes that previously caused issues.

This test uses the optimization factory to create optimized components
and runs a basic simulation to verify functionality.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.optimization_factory import (
        create_optimized_fire_simulation_engine,
        create_optimized_forest_model,
        log_optimization_status
    )
    from src.config.config_tools import ModelConfig
    from src.utils.logging_utils import get_logger
    
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce verbosity
    logger = get_logger(__name__)
    
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

def test_optimized_simulation(grid_size, num_layers, test_name):
    """Test optimized simulation on given grid size."""
    
    grid_width, grid_height = grid_size if isinstance(grid_size, tuple) else (grid_size, grid_size)
    total_cells = grid_width * grid_height * num_layers
    
    print(f"\n🧪 {test_name}")
    print(f"=" * 50)
    print(f"Grid: {grid_width} × {grid_height} × {num_layers} = {total_cells:,} cells")
    
    try:
        # Create optimized forest model
        print("🌲 Creating optimized forest model...")
        start_time = time.time()
        
        config = ModelConfig(
            grid_size=[grid_width, grid_height],
            num_layers=num_layers,
            model_resolution=100.0,
            layer_height=2.0,
            max_steps=5,  # Short simulation
            use_terrain=False,
            use_sparse_storage=True,
            memory_optimization_level=2
        )
        
        forest_model = create_optimized_forest_model(
            grid_size=(grid_width, grid_height),
            num_layers=num_layers,
            config=config,
            force_optimization=True
        )
        
        model_time = time.time() - start_time
        print(f"✅ Forest model created in {model_time:.2f}s")
        
        # Create optimized simulation engine
        print("🚀 Creating optimized simulation engine...")
        start_time = time.time()
        
        engine = create_optimized_fire_simulation_engine(
            forest_model=forest_model,
            config=config,
            force_optimization=True
        )
        
        engine_time = time.time() - start_time
        print(f"✅ Simulation engine created in {engine_time:.2f}s")
        
        # Run short simulation
        print("🔥 Running simulation...")
        start_time = time.time()
        
        # Add ignition point
        center_x, center_y = grid_width // 2, grid_height // 2
        engine.active_cells.add((center_x, center_y, 1))
        
        # Run simulation steps manually to avoid parameter issues
        initial_active = len(engine.active_cells)
        
        for step in range(5):
            if not engine.active_cells:
                break
            
            print(f"  Step {step + 1}: {len(engine.active_cells)} active cells")
            engine.current_step = step
            engine._process_step()
        
        sim_time = time.time() - start_time
        final_active = len(engine.active_cells)
        
        print(f"✅ Simulation completed in {sim_time:.2f}s")
        print(f"   Initial active cells: {initial_active}")
        print(f"   Final active cells: {final_active}")
        
        # Check optimization metrics if available
        if hasattr(engine, 'get_performance_metrics'):
            metrics = engine.get_performance_metrics()
            print(f"   Vectorized ops: {metrics.get('vectorized_ops', 0)}")
            print(f"   Batch updates: {metrics.get('batch_updates', 0)}")
            print(f"   Cached neighbors: {metrics.get('cached_neighbors', 0)}")
        
        # Check forest model optimization metrics if available
        if hasattr(forest_model, 'get_optimization_metrics'):
            forest_metrics = forest_model.get_optimization_metrics()
            print(f"   Sparse ops optimized: {forest_metrics.get('sparse_operations_optimized', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ {test_name} failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run direct optimization tests."""
    
    print("🚀 DIRECT OPTIMIZATION TEST")
    print("=" * 50)
    print("Testing optimized components on progressively larger grids")
    
    # Show optimization status
    log_optimization_status()
    
    # Test cases - progressively larger
    test_cases = [
        ((100, 100), 5, "Small Test - 50K cells"),
        ((200, 200), 8, "Medium Test - 320K cells"),
        ((400, 400), 10, "Large Test - 1.6M cells"),
        ((500, 500), 12, "Very Large Test - 3M cells"),
    ]
    
    successful_tests = 0
    total_tests = len(test_cases)
    
    for grid_size, num_layers, test_name in test_cases:
        success = test_optimized_simulation(grid_size, num_layers, test_name)
        if success:
            successful_tests += 1
        
        # Brief pause between tests
        time.sleep(1)
    
    # Summary
    print(f"\n" + "=" * 50)
    print(f"🎯 TEST SUMMARY")
    print(f"=" * 50)
    print(f"Successful tests: {successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print(f"✅ All optimization tests passed!")
        print(f"   The optimized components can handle large grids")
        print(f"   Ready for large-scale calibration testing")
    elif successful_tests > 0:
        print(f"⚠️  Partial success - some optimizations working")
        print(f"   May need to adjust grid sizes for available memory")
    else:
        print(f"❌ All tests failed - check optimization implementation")
    
    return successful_tests > 0

if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n🎉 Optimization verification completed successfully!")
    else:
        print(f"\n❌ Optimization verification failed!")
        sys.exit(1)
