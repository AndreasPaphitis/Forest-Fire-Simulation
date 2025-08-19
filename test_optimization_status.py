#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Optimization Status Diagnostic

This script checks if the performance optimizations are actually working
on the current system (local or HPC). It verifies imports, component creation,
and optimization settings.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("🔍 OPTIMIZATION STATUS DIAGNOSTIC")
print("=" * 50)

# 1. Check if optimized components exist
print("\n1. CHECKING OPTIMIZED COMPONENT FILES:")
optimized_files = [
    "src/core/optimized_fire_simulation_engine.py",
    "src/core/optimized_forest_model.py",
    "src/core/optimization_factory.py"
]

for file_path in optimized_files:
    if os.path.exists(file_path):
        print(f"✅ {file_path} - EXISTS")
    else:
        print(f"❌ {file_path} - MISSING")

# 2. Try to import optimization factory
print("\n2. TESTING OPTIMIZATION FACTORY IMPORT:")
try:
    from src.core.optimization_factory import (
        create_optimized_fire_simulation_engine,
        create_optimized_forest_model,
        get_optimization_status,
        HAS_OPTIMIZATIONS
    )
    print(f"✅ Optimization factory imported successfully")
    print(f"✅ HAS_OPTIMIZATIONS: {HAS_OPTIMIZATIONS}")
except ImportError as e:
    print(f"❌ Failed to import optimization factory: {e}")
    sys.exit(1)

# 3. Check optimization status
print("\n3. OPTIMIZATION STATUS:")
try:
    status = get_optimization_status()
    print(f"✅ Optimization status retrieved:")
    for key, value in status.items():
        print(f"   {key}: {value}")
except Exception as e:
    print(f"❌ Failed to get optimization status: {e}")

# 4. Test creating optimized components
print("\n4. TESTING OPTIMIZED COMPONENT CREATION:")
try:
    from src.config.config_tools import ModelConfig
    
    # Create a test config
    test_config = ModelConfig(
        grid_size=(100, 100),
        num_layers=5
    )
    
    print(f"✅ Test config created: {test_config.grid_size}")
    
    # Try to create optimized forest model
    print("\n   Creating optimized forest model...")
    forest_model = create_optimized_forest_model(
        grid_size=test_config.grid_size,
        num_layers=test_config.num_layers,
        config=test_config,
        force_optimization=True
    )
    print(f"✅ Forest model created: {type(forest_model)}")
    
    # Try to create optimized simulation engine
    print("\n   Creating optimized simulation engine...")
    engine = create_optimized_fire_simulation_engine(
        forest_model=forest_model,
        config=test_config,
        force_optimization=True
    )
    print(f"✅ Simulation engine created: {type(engine)}")
    
    # Check if they have optimization attributes
    print("\n   Checking optimization attributes:")
    if hasattr(engine, 'use_vectorized_processing'):
        print(f"   ✅ Engine has vectorized processing: {engine.use_vectorized_processing}")
    else:
        print(f"   ❌ Engine missing vectorized processing")
        
    if hasattr(engine, 'use_batch_updates'):
        print(f"   ✅ Engine has batch updates: {engine.use_batch_updates}")
    else:
        print(f"   ❌ Engine missing batch updates")
        
    if hasattr(engine, 'use_neighbor_caching'):
        print(f"   ✅ Engine has neighbor caching: {engine.use_neighbor_caching}")
    else:
        print(f"   ❌ Engine missing neighbor caching")
    
except Exception as e:
    print(f"❌ Failed to create optimized components: {e}")
    import traceback
    traceback.print_exc()

# 5. Test grid search optimization integration
print("\n5. TESTING GRID SEARCH INTEGRATION:")
try:
    from src.core.calibration.grid_search import GridSearchCalibrator
    from src.core.calibration.calibration_config import CalibrationConfig
    from src.core.calibration.parameter_bounds import ParameterBounds
    
    print("✅ Grid search components imported")
    
    # Create a minimal test
    test_params = {
        'fuel_consumption_rate': ParameterBounds(min_value=0.1, max_value=0.3, grid_points=2)
    }
    
    test_config = CalibrationConfig(
        base_config=test_config,
        parameter_bounds=test_params,
        max_workers=1
    )
    
    print("✅ Test calibration config created")
    
except Exception as e:
    print(f"❌ Grid search integration test failed: {e}")

print("\n" + "=" * 50)
print("🔍 DIAGNOSTIC COMPLETE")
print("=" * 50)
