#!/usr/bin/env python3
"""
Emergency Calibration Diagnostic Script

This script performs comprehensive diagnostics to identify why the calibration framework
is failing with 0.0000 objective values and duplicate completion messages.
"""

import sys
import os
import time
import traceback
import logging
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """Set up detailed logging for diagnostics."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('emergency_calibration_diagnostic.log')
        ]
    )
    return logging.getLogger(__name__)

def test_worker_function_isolation():
    """Test if worker function can run in isolation."""
    logger = setup_logging()
    logger.info("🔍 TESTING WORKER FUNCTION ISOLATION")
    
    try:
        from src.core.calibration.grid_search import evaluate_worker_function
        from src.config.config_tools import ModelConfig
        
        # Create minimal test config
        config = ModelConfig(
            grid_size=(20, 20),
            num_layers=3,
            max_steps=5,
            simulation_type='memory_optimized',
            spread_probability=0.8,
            fuel_consumption_rate=0.01,
            ignition_threshold=0.1,
            stop_when_fire_extinguished=False
        )
        
        # Test parameters
        params = {
            'spread_probability': 0.8,
            'fuel_consumption_rate': 0.01,
            'ignition_threshold': 0.1
        }
        
        logger.info("Running isolated worker function...")
        result = evaluate_worker_function(
            parameter_values=params,
            target_data=None,
            config_dict=config.__dict__,
            objective_function_name="SpatialSimilarityObjective"
        )
        
        logger.info(f"Worker function result: {result}")
        logger.info(f"Objective value: {result.get('objective_value', 'N/A')}")
        logger.info(f"Is valid: {result.get('is_valid', 'N/A')}")
        logger.info(f"Error message: {result.get('error_message', 'N/A')}")
        
        return result.get('is_valid', False)
        
    except Exception as e:
        logger.error(f"Worker function isolation test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_simulation_result_structure():
    """Test the structure of simulation results."""
    logger = setup_logging()
    logger.info("🔍 TESTING SIMULATION RESULT STRUCTURE")
    
    try:
        from src.core.forest_model import create_forest_model
        from src.core.fire_simulation_engine import FireSimulationEngine
        from src.config.config_tools import ModelConfig
        
        # Create test simulation
        config = ModelConfig(
            grid_size=(10, 10),
            num_layers=2,
            max_steps=3,
            simulation_type='memory_optimized',
            spread_probability=0.9,
            fuel_consumption_rate=0.001,
            ignition_threshold=0.05,
            stop_when_fire_extinguished=False
        )
        
        forest_model = create_forest_model(
            model_type='memory_optimized',
            config=config
        )
        
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Set ignition points
        forest_model.set_ignition(5, 5, 0)
        
        # Run simulation
        result = engine.run_simulation()
        
        logger.info(f"Simulation result keys: {list(result.keys())}")
        logger.info(f"Has forest_model: {'forest_model' in result}")
        logger.info(f"Has stats: {'stats' in result}")
        
        if 'stats' in result:
            stats = result['stats']
            logger.info(f"Stats keys: {list(stats.keys())}")
            logger.info(f"Steps: {stats.get('steps', 'N/A')}")
            logger.info(f"Total burned cells: {stats.get('total_burned_cells', 'N/A')}")
            logger.info(f"Final active cells: {stats.get('final_active_cells', 'N/A')}")
        
        if 'forest_model' in result:
            fm = result['forest_model']
            logger.info(f"Forest model type: {type(fm)}")
            logger.info(f"Has state: {hasattr(fm, 'state')}")
            if hasattr(fm, 'state'):
                state = fm.state
                logger.info(f"State shape: {state.shape if hasattr(state, 'shape') else 'no shape'}")
                logger.info(f"State type: {type(state)}")
                if hasattr(state, 'shape'):
                    logger.info(f"State sum: {np.sum(state)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Simulation result structure test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_objective_function_detailed():
    """Test objective function with detailed logging."""
    logger = setup_logging()
    logger.info("🔍 TESTING OBJECTIVE FUNCTION DETAILED")
    
    try:
        from src.core.calibration.objective_functions import SpatialSimilarityObjective
        
        # Create synthetic target
        target_data = {
            'fire_perimeter': np.zeros((20, 20), dtype=np.float32)
        }
        
        # Create circular target
        center_x, center_y = 10, 10
        radius = 5
        y, x = np.ogrid[:20, :20]
        mask = (x - center_x)**2 + (y - center_y)**2 <= radius**2
        target_data['fire_perimeter'][mask] = 1.0
        
        logger.info(f"Target fire cells: {np.sum(target_data['fire_perimeter'])}")
        
        # Create mock simulation result
        predicted = np.zeros((20, 20, 3))
        predicted[8:12, 8:12, 0] = 1  # Some fire in ground layer
        
        mock_forest_model = type('MockModel', (), {
            'state': predicted,
            'width': 20,
            'height': 20,
            'num_layers': 3
        })()
        
        mock_result = {'forest_model': mock_forest_model}
        
        # Test objective function
        objective_function = SpatialSimilarityObjective()
        objective_result = objective_function.evaluate(mock_result, target_data)
        
        logger.info(f"Objective value: {objective_result.value}")
        logger.info(f"Is valid: {objective_result.is_valid}")
        logger.info(f"Error message: {objective_result.error_message}")
        logger.info(f"Components: {objective_result.components}")
        
        return objective_result.is_valid and objective_result.value > 0
        
    except Exception as e:
        logger.error(f"Objective function detailed test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_multiprocessing_issue():
    """Test if multiprocessing is causing the duplicate messages."""
    logger = setup_logging()
    logger.info("🔍 TESTING MULTIPROCESSING ISSUE")
    
    try:
        from concurrent.futures import ProcessPoolExecutor
        from src.core.calibration.grid_search import evaluate_worker_function
        from src.config.config_tools import ModelConfig
        
        config = ModelConfig(
            grid_size=(10, 10),
            num_layers=2,
            max_steps=2,
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
        
        logger.info("Testing multiprocessing with 2 workers...")
        
        with ProcessPoolExecutor(max_workers=2) as executor:
            futures = []
            for i in range(4):
                future = executor.submit(
                    evaluate_worker_function,
                    params,
                    None,
                    config.__dict__,
                    "SpatialSimilarityObjective"
                )
                futures.append(future)
            
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                    logger.info(f"Worker result: {result.get('objective_value', 'N/A')}")
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
        
        logger.info(f"All workers completed. Results: {len(results)}")
        return len(results) == 4
        
    except Exception as e:
        logger.error(f"Multiprocessing test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_logging_duplication():
    """Test if logging configuration is causing duplicate messages."""
    logger = setup_logging()
    logger.info("🔍 TESTING LOGGING DUPLICATION")
    
    try:
        # Check if there are multiple loggers configured
        root_logger = logging.getLogger()
        logger.info(f"Root logger handlers: {len(root_logger.handlers)}")
        
        # Check for duplicate handlers
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        logger.info(f"Handler types: {handler_types}")
        
        # Check if any logger has multiple handlers of the same type
        for handler_type in set(handler_types):
            count = handler_types.count(handler_type)
            if count > 1:
                logger.warning(f"Multiple {handler_type} handlers detected: {count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Logging duplication test failed: {e}")
        return False

def test_calibration_config():
    """Test the calibration configuration."""
    logger = setup_logging()
    logger.info("🔍 TESTING CALIBRATION CONFIGURATION")
    
    try:
        from src.core.calibration.calibration_config import CalibrationConfig
        from src.core.calibration.parameter_bounds import get_default_calibration_bounds
        
        # Get default bounds
        bounds = get_default_calibration_bounds()
        logger.info(f"Parameter bounds: {bounds}")
        
        # Create base config first
        base_config = ModelConfig(
            grid_size=(20, 20),
            num_layers=3,
            max_steps=5
        )
        
        # Create calibration config with proper base_config
        config = CalibrationConfig(
            experiment_name="test_calibration",
            method=CalibrationMethod.GRID_SEARCH,
            base_config=base_config,
            calibration_parameters=['spread_probability', 'fuel_consumption_rate']
        )
        
        logger.info(f"Calibration config created successfully")
        logger.info(f"Total combinations: {config.get_total_combinations()}")
        
        return True
        
    except Exception as e:
        logger.error(f"Calibration config test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Run all diagnostic tests."""
    logger = setup_logging()
    logger.info("🚨 EMERGENCY CALIBRATION DIAGNOSTIC STARTING")
    
    tests = [
        ("Worker Function Isolation", test_worker_function_isolation),
        ("Simulation Result Structure", test_simulation_result_structure),
        ("Objective Function Detailed", test_objective_function_detailed),
        ("Multiprocessing Issue", test_multiprocessing_issue),
        ("Logging Duplication", test_logging_duplication),
        ("Calibration Configuration", test_calibration_config),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            start_time = time.time()
            result = test_func()
            end_time = time.time()
            
            results[test_name] = {
                'passed': result,
                'time': end_time - start_time
            }
            
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{status} {test_name} ({end_time - start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ ERROR in {test_name}: {e}")
            results[test_name] = {
                'passed': False,
                'error': str(e),
                'time': 0
            }
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info(f"{'='*60}")
    
    passed = sum(1 for r in results.values() if r['passed'])
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result['passed'] else "❌ FAILED"
        logger.info(f"{status} {test_name}")
        if 'error' in result:
            logger.info(f"   Error: {result['error']}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed - issue may be in specific calibration run")
    else:
        logger.info("🚨 Issues detected - check individual test results above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
