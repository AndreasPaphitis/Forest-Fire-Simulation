#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug script to identify the layer index out of range issue.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def debug_layer_issue():
    """Debug the layer index out of range issue."""
    print("DEBUGGING LAYER INDEX ISSUE")
    print("=" * 50)
    
    try:
        from src.core.optimization_factory import create_optimized_fire_simulation_engine, create_optimized_forest_model
        from src.config.config_tools import ModelConfig
        
        # Create test configuration
        test_config = ModelConfig(
            grid_size=(200, 200),  # Larger grid to reproduce the issue
            num_layers=5,
            spread_probability=0.8,
            ignition_threshold=0.1,
            ember_probability=0.4,
            ember_ignition=0.3
        )
        
        print(f"Test config: {test_config.grid_size} x {test_config.num_layers}")
        
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
        
        print(f"Optimized engine created: {type(engine).__name__}")
        
        # Debug layer information
        print(f"\nLayer Debug Information:")
        print(f"  forest_model.num_layers: {forest_model.num_layers}")
        print(f"  len(forest_model.state_layers): {len(forest_model.state_layers) if hasattr(forest_model, 'state_layers') else 'N/A'}")
        print(f"  len(forest_model.fuel_load_layers): {len(forest_model.fuel_load_layers) if hasattr(forest_model, 'fuel_load_layers') else 'N/A'}")
        
        if hasattr(forest_model, 'state_layers') and forest_model.state_layers:
            print(f"  state_layers[0] shape: {forest_model.state_layers[0].shape if hasattr(forest_model.state_layers[0], 'shape') else 'N/A'}")
        
        # Set ignition point
        center_x, center_y = test_config.grid_size[0] // 2, test_config.grid_size[1] // 2
        forest_model.set_ignition(center_x, center_y, 0)
        
        print(f"\nIgnition point set at ({center_x}, {center_y}, 0)")
        
        # Test a single step to trigger the issue
        print(f"\nRunning single step to trigger layer issue...")
        
        # Override the _safe_sparse_access method to add debugging
        original_safe_sparse_access = engine._safe_sparse_access
        
        def debug_safe_sparse_access(operation, *args, max_retries=3, fallback_value=None):
            try:
                # Try to extract coordinates from the operation
                import inspect
                source = inspect.getsource(operation)
                print(f"  DEBUG: Sparse access operation: {source[:100]}...")
                return original_safe_sparse_access(operation, *args, max_retries=max_retries, fallback_value=fallback_value)
            except Exception as e:
                print(f"  DEBUG: Sparse access failed: {e}")
                return fallback_value
        
        engine._safe_sparse_access = debug_safe_sparse_access
        
        # Run simulation
        result = engine.run_simulation(max_steps=1, stop_when_fire_extinguished=False)
        
        print(f"\nSimulation completed: {result.get('total_steps', 'N/A')} steps")
        print(f"Final active cells: {len(engine.active_cells)}")
        print(f"Final burned cells: {len(engine.burned_cells)}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_layer_issue()
    sys.exit(0 if success else 1)
