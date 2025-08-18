#!/usr/bin/env python3
"""
Isolated logging test to verify duplicate logging fix
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_isolated_logging():
    """Set up completely isolated logging for testing."""
    # Clear all existing loggers
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.propagate = False
    
    # Clear root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Set up minimal root logging
    logging.basicConfig(
        level=logging.WARNING,  # Only warnings and above
        format='[MAIN] %(levelname)s - %(message)s',
        force=True
    )

def test_worker_isolation():
    """Test worker function with completely isolated logging."""
    print("Testing worker function with isolated logging...")
    
    try:
        from src.core.calibration.grid_search import evaluate_worker_function
        from src.config.config_tools import ModelConfig
        
        config = ModelConfig(
            grid_size=(5, 5),
            num_layers=2,
            max_steps=1,
            simulation_type='memory_optimized',
            spread_probability=0.8,
            fuel_consumption_rate=0.01,
            ignition_threshold=0.1,
            stop_when_fire_extinguished=False
        )
        
        params = {
            'spread_probability': 0.8,
            'fuel_consumption_rate': 0.01,
            'ignition_threshold': 0.1
        }
        
        result = evaluate_worker_function(
            parameter_values=params,
            target_data=None,
            config_dict=config.__dict__,
            objective_function_name="SpatialSimilarityObjective"
        )
        
        print(f"Worker function result: {result.get('objective_value', 'N/A')}")
        print(f"Is valid: {result.get('is_valid', 'N/A')}")
        
        return result.get('is_valid', False)
        
    except Exception as e:
        print(f"Worker function test failed: {e}")
        return False

def test_multiprocessing_isolation():
    """Test multiprocessing with isolated logging."""
    print("Testing multiprocessing with isolated logging...")
    
    try:
        from concurrent.futures import ProcessPoolExecutor
        from src.core.calibration.grid_search import evaluate_worker_function
        from src.config.config_tools import ModelConfig
        
        config = ModelConfig(
            grid_size=(3, 3),
            num_layers=2,
            max_steps=1,
            simulation_type='memory_optimized',
            spread_probability=0.8,
            fuel_consumption_rate=0.01,
            ignition_threshold=0.1,
            stop_when_fire_extinguished=False
        )
        
        params = {
            'spread_probability': 0.8,
            'fuel_consumption_rate': 0.01,
            'ignition_threshold': 0.1
        }
        
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                evaluate_worker_function,
                params,
                None,
                config.__dict__,
                "SpatialSimilarityObjective"
            )
            
            try:
                result = future.result(timeout=30)
                print(f"Worker result: {result.get('objective_value', 'N/A')}")
                return result.get('is_valid', False)
            except Exception as e:
                print(f"Worker failed: {e}")
                return False
        
    except Exception as e:
        print(f"Multiprocessing test failed: {e}")
        return False

def main():
    """Run isolated tests."""
    print("🧪 Testing with isolated logging...")
    
    # Set up isolated logging
    setup_isolated_logging()
    
    tests = [
        ("Worker Function (Isolated)", test_worker_isolation),
        ("Multiprocessing (Isolated)", test_multiprocessing_isolation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")
        
        try:
            result = test_func()
            results[test_name] = result
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} {test_name}")
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("ISOLATED TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Isolated logging tests passed!")
        print("   This suggests the duplicate logging is fixed")
    else:
        print("🚨 Some isolated tests failed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
