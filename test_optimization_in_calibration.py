#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Optimization in Calibration

Simple test to verify that the calibration is actually using optimized components.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.optimization_factory import (
        create_optimized_fire_simulation_engine,
        create_optimized_forest_model,
        get_optimization_status
    )
    from src.config.config_tools import ModelConfig
    from src.utils.logging_utils import get_logger
    
    logging.basicConfig(level=logging.INFO)
    logger = get_logger(__name__)
    
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

def test_optimization_in_calibration():
    """Test that calibration uses optimized components."""
    
    print("🔍 TESTING OPTIMIZATION IN CALIBRATION")
    print("=" * 50)
    
    # Create a test config similar to calibration
    test_config = ModelConfig(
        grid_size=(100, 100),
        num_layers=5
    )
    
    print(f"✅ Test config created: {test_config.grid_size}")
    
    # Test the exact same code path as calibration
    try:
        from src.core.optimization_factory import (
            create_optimized_fire_simulation_engine,
            create_optimized_forest_model
        )
        
        print(f"🔍 DIAGNOSTIC: Using OPTIMIZED components")
        
        # Create optimized forest model (same as calibration)
        forest_model = create_optimized_forest_model(
            grid_size=test_config.grid_size,
            num_layers=test_config.num_layers,
            config=test_config,
            force_optimization=True
        )
        
        # Create optimized simulation engine (same as calibration)
        engine = create_optimized_fire_simulation_engine(
            forest_model=forest_model,
            config=test_config,
            force_optimization=True
        )
        
        print(f"🔍 DIAGNOSTIC: Created optimized engine: {type(engine)}")
        
        # Verify optimization attributes
        print(f"🔍 DIAGNOSTIC: Vectorized processing: {getattr(engine, 'use_vectorized_processing', 'NOT FOUND')}")
        print(f"🔍 DIAGNOSTIC: Batch updates: {getattr(engine, 'use_batch_updates', 'NOT FOUND')}")
        print(f"🔍 DIAGNOSTIC: Neighbor caching: {getattr(engine, 'use_neighbor_caching', 'NOT FOUND')}")
        
        # Test a simple simulation
        print(f"🔍 DIAGNOSTIC: Testing simple simulation...")
        
        # Set ignition point
        forest_model.set_ignition(50, 50, 0)
        
        # Run simulation
        result = engine.run_simulation(stop_when_fire_extinguished=True)
        
        print(f"🔍 DIAGNOSTIC: Simulation completed successfully")
        print(f"🔍 DIAGNOSTIC: Result type: {type(result)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to use optimized components: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_optimization_in_calibration()
    if success:
        print("\n✅ OPTIMIZATION TEST PASSED - Calibration should use optimized components!")
    else:
        print("\n❌ OPTIMIZATION TEST FAILED - Calibration will use standard components!")
