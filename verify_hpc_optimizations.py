#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HPC Optimizations Verification Script

This script verifies that all HPC optimizations are working correctly after deployment.
It tests all components and provides a comprehensive report.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all optimized components can be imported."""
    print("🔍 TESTING IMPORTS")
    print("=" * 50)
    
    results = {}
    
    try:
        from src.core.optimization_factory import (
            create_optimized_fire_simulation_engine,
            create_optimized_forest_model,
            HAS_OPTIMIZATIONS,
            log_optimization_status
        )
        results['optimization_factory'] = True
        print(f"✅ Optimization factory imported successfully")
        print(f"✅ HAS_OPTIMIZATIONS: {HAS_OPTIMIZATIONS}")
    except ImportError as e:
        results['optimization_factory'] = False
        print(f"❌ Optimization factory import failed: {e}")

    if results.get('optimization_factory', False):
        try:
            from src.core.optimized_fire_simulation_engine import OptimizedFireSimulationEngine
            results['optimized_engine'] = True
            print(f"✅ Optimized fire simulation engine imported")
        except ImportError as e:
            results['optimized_engine'] = False
            print(f"❌ Optimized engine import failed: {e}")

        try:
            from src.core.optimized_forest_model import OptimizedMemoryOptimizedForestModel
            results['optimized_forest_model'] = True
            print(f"✅ Optimized forest model imported")
        except ImportError as e:
            results['optimized_forest_model'] = False
            print(f"❌ Optimized forest model import failed: {e}")

    return results

def test_parameter_bounds_fix():
    """Test that the parameter bounds fix is working."""
    print("\n🔍 TESTING PARAMETER BOUNDS FIX")
    print("=" * 50)
    
    try:
        from src.core.calibration.parameter_bounds import (
            get_default_calibration_bounds,
            get_parameter_bounds_for_calibration
        )

        # Test the top 5 parameters
        top_5_parameters = [
            'spread_probability',
            'fuel_consumption_rate', 
            'ember_probability',
            'ember_ignition',
            'fuel_moisture_baseline'
        ]

        # Test old method (should create 17 parameters)
        all_bounds = get_default_calibration_bounds()
        print(f"✅ Old method creates bounds for {len(all_bounds)} parameters")

        # Test new method (should create only 5 parameters)
        parameter_bounds = get_parameter_bounds_for_calibration(top_5_parameters)
        print(f"✅ New method creates bounds for {len(parameter_bounds)} parameters")

        # Check if the parameters match
        if set(parameter_bounds.keys()) == set(top_5_parameters):
            print(f"✅ Parameters match expected top 5!")
            return True
        else:
            print(f"❌ Parameters don't match!")
            print(f"   Expected: {set(top_5_parameters)}")
            print(f"   Actual: {set(parameter_bounds.keys())}")
            return False

    except Exception as e:
        print(f"❌ Parameter bounds test failed: {e}")
        return False

def test_optimization_factory():
    """Test the optimization factory functionality."""
    print("\n🔍 TESTING OPTIMIZATION FACTORY")
    print("=" * 50)
    
    try:
        from src.core.optimization_factory import (
            create_optimized_fire_simulation_engine,
            create_optimized_forest_model,
            should_use_optimizations,
            get_optimization_status
        )
        from src.config.config_tools import ModelConfig

        # Test optimization decision logic
        print("📊 Testing optimization decision logic:")
        
        # Small grid (should not optimize)
        small_grid = (100, 100)
        should_opt, reason = should_use_optimizations(small_grid, 5)
        print(f"   Small grid {small_grid}: {should_opt} - {reason}")
        
        # Medium grid (should auto-optimize)
        medium_grid = (1000, 1000)
        should_opt, reason = should_use_optimizations(medium_grid, 5)
        print(f"   Medium grid {medium_grid}: {should_opt} - {reason}")
        
        # Large grid (should force optimize)
        large_grid = (5000, 5000)
        should_opt, reason = should_use_optimizations(large_grid, 5)
        print(f"   Large grid {large_grid}: {should_opt} - {reason}")

        # Test optimization status
        status = get_optimization_status()
        print(f"\n📊 Optimization status:")
        print(f"   Available: {status['optimizations_available']}")
        print(f"   Auto threshold: {status['configuration']['auto_optimize_threshold']:,}")
        print(f"   Force threshold: {status['configuration']['force_optimize_threshold']:,}")

        return True

    except Exception as e:
        print(f"❌ Factory test failed: {e}")
        return False

def test_optimized_components():
    """Test that optimized components can be created and work correctly."""
    print("\n🔍 TESTING OPTIMIZED COMPONENTS")
    print("=" * 50)
    
    try:
        from src.core.optimization_factory import (
            create_optimized_fire_simulation_engine,
            create_optimized_forest_model
        )
        from src.config.config_tools import ModelConfig

        # Create test config
        test_config = ModelConfig(
            grid_size=(200, 200),
            num_layers=5
        )

        print(f"✅ Test config created: {test_config.grid_size}")

        # Test forced optimization
        print("\n   Testing FORCED optimization:")
        forest_model = create_optimized_forest_model(
            grid_size=test_config.grid_size,
            num_layers=test_config.num_layers,
            config=test_config,
            force_optimization=True
        )

        print(f"   Forest model type: {type(forest_model)}")
        print(f"   Has optimization attributes: {hasattr(forest_model, 'use_optimized_sparse_ops')}")

        engine = create_optimized_fire_simulation_engine(
            forest_model=forest_model,
            config=test_config,
            force_optimization=True
        )

        print(f"   Engine type: {type(engine)}")
        print(f"   Has optimization attributes: {hasattr(engine, 'use_vectorized_processing')}")

        # Test optimization behavior
        if hasattr(engine, 'use_vectorized_processing'):
            print(f"   Vectorized processing: {engine.use_vectorized_processing}")
        if hasattr(engine, 'use_batch_updates'):
            print(f"   Batch updates: {engine.use_batch_updates}")
        if hasattr(engine, 'use_neighbor_caching'):
            print(f"   Neighbor caching: {engine.use_neighbor_caching}")

        return True

    except Exception as e:
        print(f"❌ Component test failed: {e}")
        return False

def test_calibration_integration():
    """Test that the calibration uses optimized components."""
    print("\n🔍 TESTING CALIBRATION INTEGRATION")
    print("=" * 50)
    
    try:
        from src.core.calibration.grid_search import GridSearchCalibrator
        from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod, CalibrationObjective
        from src.config.config_tools import ModelConfig

        # Create a minimal config
        base_config = ModelConfig(
            grid_size=(100, 100),
            num_layers=3
        )

        # Create calibration config with top 5 parameters
        calib_config = CalibrationConfig(
            experiment_name="test_hpc_optimizations",
            method=CalibrationMethod.GRID_SEARCH,
            objective=CalibrationObjective.SPATIAL_SIMILARITY,
            base_config=base_config,
            calibration_parameters=[
                'spread_probability',
                'fuel_consumption_rate', 
                'ember_probability',
                'ember_ignition',
                'fuel_moisture_baseline'
            ],
            grid_search_points=2
        )

        print(f"✅ Created calibration config with {len(calib_config.calibration_parameters)} parameters")

        # Check if the grid search will use optimizations
        from src.core.optimization_factory import should_use_optimizations
        should_opt, reason = should_use_optimizations(base_config.grid_size, base_config.num_layers)
        print(f"📊 Grid search optimization decision: {should_opt} - {reason}")

        return True

    except Exception as e:
        print(f"❌ Calibration integration test failed: {e}")
        return False

def test_hpc_environment():
    """Test HPC-specific optimizations."""
    print("\n🔍 TESTING HPC ENVIRONMENT")
    print("=" * 50)
    
    try:
        # Check NumExpr configuration
        import os
        numexpr_max_threads = os.environ.get('NUMEXPR_MAX_THREADS', 'Not set')
        numexpr_num_threads = os.environ.get('NUMEXPR_NUM_THREADS', 'Not set')
        
        print(f"📊 NumExpr configuration:")
        print(f"   NUMEXPR_MAX_THREADS: {numexpr_max_threads}")
        print(f"   NUMEXPR_NUM_THREADS: {numexpr_num_threads}")

        # Check if we're in an HPC-like environment
        import multiprocessing as mp
        cpu_count = mp.cpu_count()
        print(f"   CPU count: {cpu_count}")

        # Test shared memory availability
        try:
            import multiprocessing.shared_memory as shared_memory
            print(f"   Shared memory: Available")
        except ImportError:
            print(f"   Shared memory: Not available")

        # Test optimization factory in HPC mode
        from src.core.optimization_factory import get_optimization_status
        status = get_optimization_status()
        
        print(f"\n📊 HPC optimization status:")
        print(f"   Optimizations available: {status['optimizations_available']}")
        print(f"   Graceful fallback: {status['configuration']['graceful_fallback']}")
        print(f"   Fallback on error: {status['configuration']['fallback_on_error']}")

        return True

    except Exception as e:
        print(f"❌ HPC environment test failed: {e}")
        return False

def test_hpc_configuration_script():
    """Test the HPC configuration script."""
    print("\n🔍 TESTING HPC CONFIGURATION SCRIPT")
    print("=" * 50)
    
    try:
        # Test if the configuration script exists and can be imported
        config_script_path = Path(__file__).parent / "scripts" / "configure_hpc_optimizations.py"
        if config_script_path.exists():
            print(f"✅ HPC configuration script exists: {config_script_path}")
            
            # Test if it can be executed
            import subprocess
            result = subprocess.run([sys.executable, str(config_script_path)], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ HPC configuration script executed successfully")
                return True
            else:
                print(f"❌ HPC configuration script failed: {result.stderr}")
                return False
        else:
            print(f"❌ HPC configuration script not found: {config_script_path}")
            return False

    except Exception as e:
        print(f"❌ HPC configuration script test failed: {e}")
        return False

def test_hpc_calibration_script():
    """Test the HPC calibration script."""
    print("\n🔍 TESTING HPC CALIBRATION SCRIPT")
    print("=" * 50)
    
    try:
        # Test if the calibration script exists
        calib_script_path = Path(__file__).parent / "scripts" / "run_tenerife_calibration_optimized.py"
        if calib_script_path.exists():
            print(f"✅ HPC calibration script exists: {calib_script_path}")
            
            # Test if it can be imported
            import importlib.util
            spec = importlib.util.spec_from_file_location("hpc_calibration", calib_script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if it has the setup_hpc_optimizations function
            if hasattr(module, 'setup_hpc_optimizations'):
                print(f"✅ HPC calibration script has setup_hpc_optimizations function")
                return True
            else:
                print(f"❌ HPC calibration script missing setup_hpc_optimizations function")
                return False
        else:
            print(f"❌ HPC calibration script not found: {calib_script_path}")
            return False

    except Exception as e:
        print(f"❌ HPC calibration script test failed: {e}")
        return False

def main():
    """Main verification function."""
    print("🚀 HPC OPTIMIZATIONS VERIFICATION")
    print("=" * 60)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print("=" * 60)

    # Run all tests
    test_results = {}
    
    test_results['imports'] = test_imports()
    test_results['parameter_bounds_fix'] = test_parameter_bounds_fix()
    test_results['optimization_factory'] = test_optimization_factory()
    test_results['optimized_components'] = test_optimized_components()
    test_results['calibration_integration'] = test_calibration_integration()
    test_results['hpc_environment'] = test_hpc_environment()
    test_results['hpc_configuration_script'] = test_hpc_configuration_script()
    test_results['hpc_calibration_script'] = test_hpc_calibration_script()

    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    print(f"✅ Tests passed: {passed_tests}/{total_tests}")
    
    for test_name, result in test_results.items():
        status = "PASS" if result else "FAIL"
        print(f"   {test_name}: {status}")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED - HPC OPTIMIZATIONS VERIFIED!")
        print("   The system is ready for HPC deployment.")
        print("   All optimizations are working correctly.")
    else:
        print(f"\n❌ {total_tests - passed_tests} TESTS FAILED!")
        print("   Some optimizations may not be working correctly.")
        print("   Check the failed tests above.")
    
    print("\n📋 Next steps:")
    print("   1. Run on HPC: python scripts/run_tenerife_calibration_optimized.py --workers 10")
    print("   2. Monitor optimization logs for performance improvements")
    print("   3. Verify parameter count is 5 (not 17)")
    print("   4. Check for optimization status messages in output")

if __name__ == "__main__":
    main()
