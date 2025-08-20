#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Grid Search Calibrator Module

Clean, focused implementation of systematic grid search calibration for forest fire simulation.
Explores parameter space using a grid of points and evaluates each combination.

Author: Forest Fire Simulation Team
Date: 2025
Version: 2.0 (Simplified)
"""

import time
import itertools
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import numpy as np
import json
import multiprocessing as mp

try:
    from src.utils.logging_utils import get_logger
    from src.core.fire_simulation_engine import FireSimulationEngine
    from src.core.forest_model import create_forest_model
    from src.config.config_tools import ModelConfig
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

logger = get_logger(__name__)


@dataclass
class GridSearchResult:
    """Single result from grid search evaluation."""
    parameter_values: Dict[str, float]
    objective_value: float
    objective_components: Dict[str, float]
    simulation_stats: Dict[str, Any]
    evaluation_time: float
    is_valid: bool = True
    error_message: str = ""


@dataclass
class GridSearchResults:
    """Complete results from grid search calibration."""
    results: List[GridSearchResult] = field(default_factory=list)
    best_result: Optional[GridSearchResult] = None
    parameter_space: Dict[str, List[float]] = field(default_factory=dict)
    total_evaluations: int = 0
    successful_evaluations: int = 0
    total_time: float = 0.0
    
    def __post_init__(self):
        """Update statistics after initialization."""
        self._update_statistics()
    
    def _update_statistics(self):
        """Update derived statistics."""
        self.total_evaluations = len(self.results)
        self.successful_evaluations = sum(1 for r in self.results if r.is_valid)
        self.total_time = sum(r.evaluation_time for r in self.results)
        
        # Find best result
        valid_results = [r for r in self.results if r.is_valid]
        if valid_results:
            self.best_result = max(valid_results, key=lambda x: x.objective_value)
    
    def add_result(self, result: GridSearchResult):
        """Add a new result and update statistics."""
        self.results.append(result)
        self._update_statistics()
    
    def add_error(self):
        """Add an error result to track failed evaluations."""
        error_result = GridSearchResult(
            parameter_values={},
            objective_value=0.0,
            objective_components={},
            simulation_stats={},
            evaluation_time=0.0,
            is_valid=False,
            error_message="Evaluation failed"
        )
        self.results.append(error_result)
        self._update_statistics()
    
    def get_best_parameters(self) -> Optional[Dict[str, float]]:
        """Get the best parameter configuration."""
        return self.best_result.parameter_values if self.best_result else None
    
    def get_best_objective_value(self) -> Optional[float]:
        """Get the best objective value achieved."""
        return self.best_result.objective_value if self.best_result else None
    
    def save_results(self, filepath: Union[str, Path]) -> None:
        """Save results to JSON file."""
        filepath = Path(filepath)
        
        results_data = {
            'parameter_space': self.parameter_space,
            'total_evaluations': self.total_evaluations,
            'successful_evaluations': self.successful_evaluations,
            'total_time': self.total_time,
            'results': [
                {
                    'parameter_values': r.parameter_values,
                    'objective_value': r.objective_value,
                    'objective_components': r.objective_components,
                    'simulation_stats': r.simulation_stats,
                    'evaluation_time': r.evaluation_time,
                    'is_valid': r.is_valid,
                    'error_message': r.error_message
                }
                for r in self.results
            ]
        }
        
        if self.best_result:
            results_data['best_result'] = {
                'parameter_values': self.best_result.parameter_values,
                'objective_value': self.best_result.objective_value,
                'objective_components': self.best_result.objective_components
            }
        
        with open(filepath, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        logger.info(f"Saved grid search results to {filepath}")


def evaluate_worker_function(parameter_values: Dict[str, float], 
                           target_data: Optional[Dict[str, Any]],
                           config_dict: Dict[str, Any],
                           objective_function_name: str,
                           worker_id: int = 0) -> Dict[str, Any]:
    """Worker function for multiprocessing evaluation."""
    import time
    import logging
    
    # Set up worker logging
    worker_logger = logging.getLogger(f"worker_{worker_id}")
    worker_logger.setLevel(logging.WARNING)
    
    start_time = time.time()
    
    try:
        # Remove worker_id from parameters if present
        if '_worker_id' in parameter_values:
            parameter_values.pop('_worker_id')
        
        # Create ModelConfig
        model_config = ModelConfig(**config_dict)
        
        # Create forest model
        forest_model = create_forest_model(
            model_type=config_dict.get('simulation_type', 'memory_optimized'),
            config=model_config
        )
        
        # Create simulation engine
        engine = FireSimulationEngine(forest_model=forest_model, config=model_config)
        
        # Run simulation
        simulation_result = engine.run_simulation()
        
        # Get objective function
        if objective_function_name == "SpatialSimilarityObjective":
            from src.core.calibration.objective_functions import SpatialSimilarityObjective
            objective_function = SpatialSimilarityObjective()
        else:
            raise ValueError(f"Unknown objective function: {objective_function_name}")
        
        # Calculate objective value
        objective_result = objective_function(simulation_result, target_data)
        
        evaluation_time = time.time() - start_time
        
        return {
            'parameter_values': parameter_values,
            'objective_value': objective_result.value if objective_result.is_valid else 0.0,
            'objective_components': objective_result.components if objective_result.is_valid else {},
            'simulation_stats': simulation_result.get('stats', {}),
            'evaluation_time': evaluation_time,
            'is_valid': objective_result.is_valid,
            'error_message': objective_result.error_message
        }
        
    except Exception as e:
        evaluation_time = time.time() - start_time
        worker_logger.error(f"Worker {worker_id} failed: {e}")
        
        return {
            'parameter_values': parameter_values,
            'objective_value': 0.0,
            'objective_components': {},
            'simulation_stats': {},
            'evaluation_time': evaluation_time,
            'is_valid': False,
            'error_message': str(e)
        }


class GridSearchCalibrator:
    """Clean grid search calibrator for systematic parameter space exploration."""
    
    def __init__(self, calibration_config,
                 parameter_bounds: Dict[str, Any],
                 objective_function,
                 parallel_execution: bool = True,
                 max_workers: Optional[int] = None):
        
        self.config = calibration_config
        self.parameter_bounds = parameter_bounds
        self.objective_function = objective_function
        self.parallel_execution = parallel_execution
        self.max_workers = max_workers or min(mp.cpu_count(), 16)
        
        # Create parameter space
        self.parameter_space = self._create_parameter_space()
        self.total_combinations = self._calculate_total_combinations()
        
        logger.info(f"GridSearchCalibrator initialized with {self.total_combinations} combinations")
    
    def _create_parameter_space(self) -> Dict[str, List[float]]:
        """Create the parameter space grid."""
        parameter_space = {}
        
        for param_name in self.config.get_calibration_parameter_names():
            if param_name not in self.parameter_bounds:
                logger.warning(f"No bounds defined for parameter {param_name}, skipping")
                continue
            
            bounds = self.parameter_bounds[param_name]
            grid_points = bounds.generate_grid_points(self.config.grid_search_points)
            parameter_space[param_name] = grid_points
        
        return parameter_space
    
    def _calculate_total_combinations(self) -> int:
        """Calculate total number of parameter combinations."""
        if not self.parameter_space:
            return 0
        
        total = 1
        for param_values in self.parameter_space.values():
            total *= len(param_values)
        
        return total
    
    def _generate_parameter_combinations(self):
        """Generate all parameter combinations for grid search."""
        param_names = list(self.parameter_space.keys())
        param_value_lists = [self.parameter_space[name] for name in param_names]
        
        for combination in itertools.product(*param_value_lists):
            yield dict(zip(param_names, combination))
    
    def _evaluate_single_combination(self, parameter_values: Dict[str, float],
                                   target_data: Optional[Dict[str, Any]] = None) -> GridSearchResult:
        """Evaluate a single parameter combination."""
        start_time = time.time()
        
        try:
            # Create config variant with parameters
            config = self.config.create_config_variant(parameter_values)
            
            # Create forest model
            forest_model = create_forest_model(
                model_type='memory_optimized',
                config=config
            )
            
            # Create simulation engine
            engine = FireSimulationEngine(forest_model=forest_model, config=config)
            
            # Run simulation
            simulation_result = engine.run_simulation()
            
            # Calculate objective value
            objective_result = self.objective_function(simulation_result, target_data)
            
            evaluation_time = time.time() - start_time
            
            return GridSearchResult(
                parameter_values=parameter_values.copy(),
                objective_value=objective_result.value if objective_result.is_valid else 0.0,
                objective_components=objective_result.components,
                simulation_stats=simulation_result.get('stats', {}),
                evaluation_time=evaluation_time,
                is_valid=objective_result.is_valid,
                error_message=objective_result.error_message
            )
            
        except Exception as e:
            evaluation_time = time.time() - start_time
            logger.error(f"Evaluation failed: {e}")
            
            return GridSearchResult(
                parameter_values=parameter_values.copy(),
                objective_value=0.0,
                objective_components={},
                simulation_stats={},
                evaluation_time=evaluation_time,
                is_valid=False,
                error_message=str(e)
            )
    
    def run_calibration(self, 
                       target_data: Optional[Dict[str, Any]] = None,
                       progress_callback: Optional[callable] = None) -> GridSearchResults:
        """Run grid search calibration."""
        logger.info(f"Starting grid search calibration with {self.total_combinations} combinations")
        start_time = time.time()
        
        results = GridSearchResults(parameter_space=self.parameter_space.copy())
        
        if self.parallel_execution and self.total_combinations > 1:
            results = self._run_parallel_calibration(target_data, progress_callback, results)
        else:
            results = self._run_sequential_calibration(target_data, progress_callback, results)
        
        total_time = time.time() - start_time
        logger.info(f"Grid search completed in {total_time:.2f} seconds")
        
        best_value = results.get_best_objective_value()
        if best_value is not None:
            logger.info(f"Best objective value: {best_value:.4f}")
        
        return results
    
    def _run_sequential_calibration(self, 
                                  target_data: Optional[Dict[str, Any]],
                                  progress_callback: Optional[callable],
                                  results: GridSearchResults) -> GridSearchResults:
        """Run calibration sequentially."""
        for i, param_combination in enumerate(self._generate_parameter_combinations()):
            result = self._evaluate_single_combination(param_combination, target_data)
            results.add_result(result)
            
            if progress_callback:
                progress_callback(i + 1, self.total_combinations, result)
            
            if (i + 1) % max(1, self.total_combinations // 20) == 0:
                progress = (i + 1) / self.total_combinations * 100
                best_value = results.get_best_objective_value() or 0.0
                logger.info(f"Progress: {progress:.1f}% ({i + 1}/{self.total_combinations}), "
                           f"Best objective: {best_value:.4f}")
        
        return results
    
    def _run_parallel_calibration(self, 
                                target_data: Optional[Dict[str, Any]],
                                progress_callback: Optional[callable],
                                results: GridSearchResults) -> GridSearchResults:
        """Run parallel calibration."""
        logger.info(f"Starting parallel calibration with {self.max_workers} workers")
        
        # Convert generator to list
        combinations_list = list(self._generate_parameter_combinations())
        
        # Prepare configuration for workers
        base_config = self.config.create_config_variant({})
        config_dict = base_config.__dict__ if hasattr(base_config, '__dict__') else base_config
        
        objective_function_name = self.objective_function.__class__.__name__
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            futures = {}
            for i, combo in enumerate(combinations_list):
                combo_with_worker = combo.copy()
                combo_with_worker['_worker_id'] = i
                
                future = executor.submit(
                    evaluate_worker_function, 
                    combo_with_worker, 
                    target_data, 
                    config_dict, 
                    objective_function_name, 
                    i
                )
                futures[future] = combo
            
            # Process results
            completed = 0
            for future in as_completed(futures):
                try:
                    result_dict = future.result(timeout=300)
                    result = GridSearchResult(**result_dict)
                    results.add_result(result)
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(completed, len(combinations_list), result)
                    
                    if completed % max(1, len(combinations_list) // 20) == 0:
                        progress = completed / len(combinations_list) * 100
                        best_value = results.get_best_objective_value() or 0.0
                        logger.info(f"Progress: {progress:.1f}% ({completed}/{len(combinations_list)}), "
                                   f"Best objective: {best_value:.4f}")
                
                except Exception as e:
                    logger.error(f"Evaluation failed: {e}")
                    results.add_error()
        
        return results
    
    def get_estimation_info(self) -> Dict[str, Any]:
        """Get estimation information about the calibration."""
        estimated_time_per_eval = 30.0  # seconds
        estimated_total_time = self.total_combinations * estimated_time_per_eval
        
        if self.parallel_execution:
            estimated_total_time /= min(self.max_workers, self.total_combinations)
        
        return {
            'total_combinations': self.total_combinations,
            'parameter_space': {name: len(values) for name, values in self.parameter_space.items()},
            'estimated_time_seconds': estimated_total_time,
            'estimated_time_hours': estimated_total_time / 3600,
            'parallel_execution': self.parallel_execution,
            'max_workers': self.max_workers if self.parallel_execution else 1
        }


def create_progress_callback(verbose: bool = True) -> callable:
    """Create a progress callback function for grid search."""
    def callback(completed: int, total: int, result: GridSearchResult):
        if verbose and completed % max(1, total // 10) == 0:
            progress = completed / total * 100
            status = "SUCCESS" if result.is_valid else "FAILED"
            obj_val = result.objective_value if result.is_valid else 0.0
            
            print(f"[{progress:6.1f}%] Evaluation {completed:4d}/{total}: "
                  f"{status} (Objective: {obj_val:.4f})")
    
    return callback


if __name__ == "__main__":
    print("Grid Search Calibrator - Clean Implementation")
    print("=" * 50)
    print("This module provides a simplified grid search calibration system.")
    print("Key features:")
    print("- Clean, focused implementation")
    print("- Parallel execution support")
    print("- Progress tracking")
    print("- Result saving and loading")
    print("- Error handling and recovery")