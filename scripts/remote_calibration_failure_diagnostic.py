#!/usr/bin/env python3
"""
Remote Calibration Failure Diagnostic Script

This script diagnoses why calibration is failing with "No valid parameters found"
on the remote machine where calibration is actually running.
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
            logging.FileHandler('remote_calibration_failure_diagnostic.log')
        ]
    )
    return logging.getLogger(__name__)

def test_worker_function_validation():
    """Test if worker function is properly validating parameters."""
    logger = setup_logging()
    logger.info("🔍 TESTING WORKER FUNCTION VALIDATION")
    
    try:
        from src.core.calibration.grid_search import evaluate_worker_function
        from src.config.config_tools import ModelConfig
        
        # Test with various parameter combinations
        test_cases = [
            {
                'name': 'Aggressive Fire Spread',
                'params': {
                    'spread_probability': 0.9,
                    'fuel_consumption_rate': 0.001,
                    'ignition_threshold': 0.05
                }
            },
            {
                'name': 'Moderate Fire Spread',
                'params': {
                    'spread_probability': 0.7,
                    'fuel_consumption_rate': 0.01,
                    'ignition_threshold': 0.1
                }
            },
            {
                'name': 'Conservative Fire Spread',
                'params': {
                    'spread_probability': 0.5,
                    'fuel_consumption_rate': 0.05,
                    'ignition_threshold': 0.2
                }
            }
        ]
        
        config = ModelConfig(
            grid_size=(20, 20),
            num_layers=3,
            max_steps=10,
            simulation_type='memory_optimized',
            stop_when_fire_extinguished=False
        )
        
        results = {}
        for test_case in test_cases:
            logger.info(f"Testing: {test_case['name']}")
            logger.info(f"Parameters: {test_case['params']}")
            
            try:
                result = evaluate_worker_function(
                    parameter_values=test_case['params'],
                    target_data=None,
                    config_dict=config.__dict__,
                    objective_function_name="SpatialSimilarityObjective"
                )
                
                logger.info(f"Result: {result}")
                logger.info(f"Objective value: {result.get('objective_value', 'N/A')}")
                logger.info(f"Is valid: {result.get('is_valid', 'N/A')}")
                logger.info(f"Error message: {result.get('error_message', 'N/A')}")
                
                results[test_case['name']] = {
                    'is_valid': result.get('is_valid', False),
                    'objective_value': result.get('objective_value', 0.0),
                    'error_message': result.get('error_message', '')
                }
                
            except Exception as e:
                logger.error(f"Test case failed: {e}")
                logger.error(traceback.format_exc())
                results[test_case['name']] = {
                    'is_valid': False,
                    'objective_value': 0.0,
                    'error_message': str(e)
                }
        
        # Summary
        valid_count = sum(1 for r in results.values() if r['is_valid'])
        total_count = len(results)
        
        logger.info(f"\n{'='*60}")
        logger.info("WORKER FUNCTION VALIDATION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Valid results: {valid_count}/{total_count}")
        
        for name, result in results.items():
            status = "✅ VALID" if result['is_valid'] else "❌ INVALID"
            logger.info(f"{status} {name}: {result['objective_value']:.4f}")
            if not result['is_valid'] and result['error_message']:
                logger.info(f"   Error: {result['error_message']}")
        
        return valid_count > 0
        
    except Exception as e:
        logger.error(f"Worker function validation test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_objective_function_validation():
    """Test if objective function is properly validating results."""
    logger = setup_logging()
    logger.info("🔍 TESTING OBJECTIVE FUNCTION VALIDATION")
    
    try:
        from src.core.calibration.objective_functions import SpatialSimilarityObjective
        from src.core.forest_model import create_forest_model
        from src.core.fire_simulation_engine import FireSimulationEngine
        from src.config.config_tools import ModelConfig
        
        # Create a simple simulation result
        config = ModelConfig(
            grid_size=(10, 10),
            num_layers=2,
            max_steps=5,
            simulation_type='memory_optimized',
            spread_probability=0.8,
            fuel_consumption_rate=0.01,
            ignition_threshold=0.1,
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
        simulation_result = engine.run_simulation()
        
        logger.info(f"Simulation completed")
        logger.info(f"Result keys: {list(simulation_result.keys())}")
        
        if 'stats' in simulation_result:
            stats = simulation_result['stats']
            logger.info(f"Steps: {stats.get('steps', 'N/A')}")
            logger.info(f"Total burned cells: {stats.get('total_burned_cells', 'N/A')}")
            logger.info(f"Final active cells: {stats.get('final_active_cells', 'N/A')}")
        
        # Test objective function
        objective_function = SpatialSimilarityObjective()
        
        # Test with no target data (should still work)
        result_no_target = objective_function.evaluate(simulation_result, None)
        logger.info(f"Objective (no target): {result_no_target.value}")
        logger.info(f"Is valid (no target): {result_no_target.is_valid}")
        logger.info(f"Error (no target): {result_no_target.error_message}")
        
        # Test with synthetic target data
        target_data = {
            'fire_perimeter': np.zeros((10, 10), dtype=np.float32)
        }
        target_data['fire_perimeter'][4:6, 4:6] = 1.0  # Small fire area
        
        result_with_target = objective_function.evaluate(simulation_result, target_data)
        logger.info(f"Objective (with target): {result_with_target.value}")
        logger.info(f"Is valid (with target): {result_with_target.is_valid}")
        logger.info(f"Error (with target): {result_with_target.error_message}")
        
        return result_no_target.is_valid or result_with_target.is_valid
        
    except Exception as e:
        logger.error(f"Objective function validation test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_parameter_bounds_validation():
    """Test if parameter bounds are properly defined and accessible."""
    logger = setup_logging()
    logger.info("🔍 TESTING PARAMETER BOUNDS VALIDATION")
    
    try:
        from src.core.calibration.parameter_bounds import get_default_calibration_bounds
        
        bounds = get_default_calibration_bounds()
        logger.info(f"Parameter bounds: {bounds}")
        
        # Check each parameter
        valid_params = []
        invalid_params = []
        
        for param_name, param_bounds in bounds.items():
            try:
                min_val = param_bounds.min_value
                max_val = param_bounds.max_value
                default_val = param_bounds.default_value
                
                logger.info(f"Parameter: {param_name}")
                logger.info(f"  Min: {min_val}, Max: {max_val}, Default: {default_val}")
                
                if min_val < max_val and min_val <= default_val <= max_val:
                    valid_params.append(param_name)
                    logger.info(f"  ✅ Valid bounds")
                else:
                    invalid_params.append(param_name)
                    logger.info(f"  ❌ Invalid bounds")
                    
            except Exception as e:
                invalid_params.append(param_name)
                logger.error(f"  ❌ Error accessing bounds: {e}")
        
        logger.info(f"\n{'='*60}")
        logger.info("PARAMETER BOUNDS SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Valid parameters: {len(valid_params)}")
        logger.info(f"Invalid parameters: {len(invalid_params)}")
        
        if valid_params:
            logger.info("Valid parameters:")
            for param in valid_params:
                logger.info(f"  ✅ {param}")
        
        if invalid_params:
            logger.warning("Invalid parameters:")
            for param in invalid_params:
                logger.warning(f"  ❌ {param}")
        
        return len(valid_params) > 0
        
    except Exception as e:
        logger.error(f"Parameter bounds validation test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_calibration_config_validation():
    """Test if calibration configuration is properly set up."""
    logger = setup_logging()
    logger.info("🔍 TESTING CALIBRATION CONFIGURATION")
    
    try:
        from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod
        from src.config.config_tools import ModelConfig
        
        # Create base config
        base_config = ModelConfig(
            grid_size=(20, 20),
            num_layers=3,
            max_steps=10,
            simulation_type='memory_optimized'
        )
        
        # Create calibration config
        calibration_config = CalibrationConfig(
            experiment_name="test_calibration",
            method=CalibrationMethod.GRID_SEARCH,
            base_config=base_config,
            calibration_parameters=['spread_probability', 'fuel_consumption_rate', 'ignition_threshold']
        )
        
        logger.info(f"Calibration config created successfully")
        logger.info(f"Experiment name: {calibration_config.experiment_name}")
        logger.info(f"Method: {calibration_config.method}")
        logger.info(f"Calibration parameters: {calibration_config.calibration_parameters}")
        logger.info(f"Total combinations: {calibration_config.get_total_combinations()}")
        
        # Test parameter generation
        param_combinations = list(calibration_config.generate_parameter_combinations())
        logger.info(f"Generated {len(param_combinations)} parameter combinations")
        
        if param_combinations:
            logger.info("First few combinations:")
            for i, combo in enumerate(param_combinations[:3]):
                logger.info(f"  {i+1}: {combo}")
        
        return len(param_combinations) > 0
        
    except Exception as e:
        logger.error(f"Calibration configuration test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_grid_search_validation():
    """Test if grid search is properly validating results."""
    logger = setup_logging()
    logger.info("🔍 TESTING GRID SEARCH VALIDATION")
    
    try:
        from src.core.calibration.grid_search import GridSearchCalibrator
        from src.core.calibration.calibration_config import CalibrationConfig, CalibrationMethod
        from src.config.config_tools import ModelConfig
        
        # Create minimal calibration config
        base_config = ModelConfig(
            grid_size=(10, 10),
            num_layers=2,
            max_steps=3,
            simulation_type='memory_optimized'
        )
        
        calibration_config = CalibrationConfig(
            experiment_name="test_grid_search",
            method=CalibrationMethod.GRID_SEARCH,
            base_config=base_config,
            calibration_parameters=['spread_probability'],
            grid_search_points=3  # Small grid for testing
        )
        
        # Create grid search calibrator
        calibrator = GridSearchCalibrator(calibration_config)
        
        logger.info(f"Grid search calibrator created")
        logger.info(f"Total combinations: {calibrator.total_combinations}")
        
        # Run a small grid search
        logger.info("Running small grid search...")
        results = calibrator.run_calibration(target_data=None)
        
        logger.info(f"Grid search completed")
        logger.info(f"Total evaluations: {results.total_evaluations}")
        logger.info(f"Successful evaluations: {results.successful_evaluations}")
        logger.info(f"Best objective value: {results.get_best_objective_value()}")
        logger.info(f"Best parameters: {results.get_best_parameters()}")
        
        # Check if any results are valid
        valid_results = [r for r in results.results if r.is_valid]
        logger.info(f"Valid results: {len(valid_results)}/{len(results.results)}")
        
        if valid_results:
            logger.info("Valid result details:")
            for i, result in enumerate(valid_results[:3]):
                logger.info(f"  {i+1}: Objective={result.objective_value:.4f}, Params={result.parameter_values}")
        
        return len(valid_results) > 0
        
    except Exception as e:
        logger.error(f"Grid search validation test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Run all diagnostic tests."""
    logger = setup_logging()
    logger.info("🚨 REMOTE CALIBRATION FAILURE DIAGNOSTIC STARTING")
    
    tests = [
        ("Worker Function Validation", test_worker_function_validation),
        ("Objective Function Validation", test_objective_function_validation),
        ("Parameter Bounds Validation", test_parameter_bounds_validation),
        ("Calibration Configuration", test_calibration_config_validation),
        ("Grid Search Validation", test_grid_search_validation),
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
        
        # Specific recommendations
        if not results.get("Worker Function Validation", {}).get('passed', False):
            logger.error("🔧 RECOMMENDATION: Fix worker function validation")
            logger.error("   - Check parameter validation logic")
            logger.error("   - Verify simulation execution")
            
        if not results.get("Objective Function Validation", {}).get('passed', False):
            logger.error("🔧 RECOMMENDATION: Fix objective function validation")
            logger.error("   - Check objective function evaluation logic")
            logger.error("   - Verify result structure")
            
        if not results.get("Parameter Bounds Validation", {}).get('passed', False):
            logger.error("🔧 RECOMMENDATION: Fix parameter bounds")
            logger.error("   - Check parameter bounds definition")
            logger.error("   - Verify bounds are reasonable")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
