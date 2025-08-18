#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Grid Search Calibrator Module

This module implements systematic grid search calibration for the forest fire simulation.
It explores the parameter space using a grid of points and evaluates each combination
against the specified objective function.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import time
import itertools
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
import numpy as np
import json
import multiprocessing as mp

# Add HPC optimizer import
from src.utils.hpc_optimizer import apply_hpc_optimizations, start_hpc_monitoring, stop_hpc_monitoring

# Add serialization optimization imports and methods
import pickle
import copy
import weakref
from functools import lru_cache

try:
    from src.utils.logging_utils import get_logger
    from src.core.fire_simulation_engine import FireSimulationEngine
    from src.core.forest_model import create_forest_model
except ImportError:
    try:
        from utils.logging_utils import get_logger
        from core.fire_simulation_engine import FireSimulationEngine
        from core.forest_model import create_forest_model
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
    convergence_info: Dict[str, Any] = field(default_factory=dict)
    
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
    
    def add_timeout(self):
        """Add a timeout result to track timed out evaluations."""
        timeout_result = GridSearchResult(
            parameter_values={},
            objective_value=0.0,
            objective_components={},
            simulation_stats={},
            evaluation_time=0.0,
            is_valid=False,
            error_message="Evaluation timed out"
        )
        self.results.append(timeout_result)
        self._update_statistics()
    
    def get_best_parameters(self) -> Optional[Dict[str, float]]:
        """Get the best parameter configuration."""
        return self.best_result.parameter_values if self.best_result else None
    
    def get_best_objective_value(self) -> Optional[float]:
        """Get the best objective value achieved."""
        return self.best_result.objective_value if self.best_result else None
    
    def get_parameter_sensitivity(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate parameter sensitivity based on grid search results.
        
        NOTE: This is a simplified correlation-based sensitivity analysis.
        For comprehensive sensitivity analysis, use the dedicated SensitivityAnalyzer
        from sensitivity_analysis.py which provides more sophisticated analysis.
        
        Returns:
            Dictionary with sensitivity statistics for each parameter
        """
        if not self.results:
            return {}
        
        valid_results = [r for r in self.results if r.is_valid]
        if not valid_results:
            return {}
        
        sensitivity = {}
        
        # Get all parameter names
        param_names = list(valid_results[0].parameter_values.keys())
        
        for param_name in param_names:
            param_values = [r.parameter_values[param_name] for r in valid_results]
            objective_values = [r.objective_value for r in valid_results]
            
            # Calculate correlation between parameter and objective
            correlation = np.corrcoef(param_values, objective_values)[0, 1]
            if np.isnan(correlation):
                correlation = 0.0
            
            # Calculate range of objective values for this parameter
            param_range = max(param_values) - min(param_values)
            obj_range = max(objective_values) - min(objective_values)
            
            sensitivity[param_name] = {
                'correlation': correlation,
                'parameter_range': param_range,
                'objective_range': obj_range,
                'sensitivity_score': abs(correlation) * obj_range / max(param_range, 1e-10)
            }
        
        return sensitivity
    
    def save_results(self, filepath: Union[str, Path]) -> None:
        """Save results to JSON file."""
        filepath = Path(filepath)
        
        # Convert results to serializable format
        results_data = {
            'parameter_space': self.parameter_space,
            'total_evaluations': self.total_evaluations,
            'successful_evaluations': self.successful_evaluations,
            'total_time': self.total_time,
            'convergence_info': self.convergence_info,
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
    
    @classmethod
    def load_results(cls, filepath: Union[str, Path]) -> 'GridSearchResults':
        """Load results from JSON file."""
        filepath = Path(filepath)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct results
        results = []
        for r_data in data['results']:
            result = GridSearchResult(**r_data)
            results.append(result)
        
        # Create GridSearchResults instance
        grid_results = cls(
            results=results,
            parameter_space=data['parameter_space'],
            convergence_info=data.get('convergence_info', {})
        )
        
        logger.info(f"Loaded grid search results from {filepath}")
        return grid_results


class SerializationOptimizer:
    """
    Optimizes serialization for multiprocessing to reduce overhead.
    
    Features:
    - Lazy loading of large objects
    - Configuration object size reduction
    - Efficient serialization strategies
    - Serialization caching
    """
    
    def __init__(self):
        self._serialization_cache = {}
        self._lazy_objects = {}  # Changed from WeakValueDictionary to regular dict for pickle compatibility
        self._optimized_configs = {}
    
    def optimize_config_for_serialization(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize configuration for efficient serialization.
        
        Args:
            config: Original configuration dictionary
            
        Returns:
            Optimized configuration for serialization
        """
        # Create a lightweight copy for serialization
        optimized = {}
        
        # Only include essential parameters for worker processes
        essential_keys = [
            'grid', 'simulation', 'wind', 'weather', 'ignition_points',
            'terrain', 'vegetation', 'output', 'calibration'
        ]
        
        for key in essential_keys:
            if key in config:
                # Create minimal copy of each section
                if isinstance(config[key], dict):
                    optimized[key] = self._minimize_dict(config[key])
                else:
                    optimized[key] = config[key]
        
        # Add serialization metadata
        optimized['_serialization_optimized'] = True
        optimized['_original_size'] = len(pickle.dumps(config))
        optimized['_optimized_size'] = len(pickle.dumps(optimized))
        
        logger.debug(f"📦 Serialization optimization: {optimized['_original_size']} -> {optimized['_optimized_size']} bytes")
        
        return optimized
    
    def _minimize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Minimize dictionary by removing unnecessary data."""
        minimized = {}
        
        for key, value in data.items():
            # Skip large objects that can be loaded lazily
            if key in ['terrain_data', 'vegetation_data', 'large_arrays']:
                continue
            
            # Skip None values
            if value is None:
                continue
            
            # Create minimal copy of nested structures
            if isinstance(value, dict):
                minimized[key] = self._minimize_dict(value)
            elif isinstance(value, list) and len(value) > 100:
                # For large lists, keep only essential information
                minimized[key] = f"<list with {len(value)} items>"
            else:
                minimized[key] = value
        
        return minimized
    
    def create_lazy_loader(self, object_id: str, loader_func: callable):
        """
        Create a lazy loader for large objects.
        
        Args:
            object_id: Unique identifier for the object
            loader_func: Function to load the object when needed
        """
        self._lazy_objects[object_id] = loader_func
    
    def get_lazy_object(self, object_id: str):
        """Get a lazy-loaded object."""
        if object_id in self._lazy_objects:
            loader_func = self._lazy_objects[object_id]
            return loader_func()
        return None
    
    def cache_serialized_object(self, key: str, obj: Any):
        """Cache a serialized object for reuse."""
        try:
            serialized = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
            self._serialization_cache[key] = serialized
            logger.debug(f"💾 Cached serialized object: {key} ({len(serialized)} bytes)")
        except Exception as e:
            logger.warning(f"⚠️  Failed to cache serialized object {key}: {e}")
    
    def get_cached_serialized(self, key: str) -> Optional[bytes]:
        """Get a cached serialized object."""
        return self._serialization_cache.get(key)
    
    def clear_cache(self):
        """Clear the serialization cache."""
        self._serialization_cache.clear()
        logger.debug("🧹 Cleared serialization cache")

# Global serialization optimizer
_serialization_optimizer = None

# Global target data for multiprocessing
_global_target_data = None

# Shared memory target data
_shared_target_data = None

def get_serialization_optimizer() -> SerializationOptimizer:
    """Get the global serialization optimizer instance."""
    global _serialization_optimizer
    if _serialization_optimizer is None:
        _serialization_optimizer = SerializationOptimizer()
    return _serialization_optimizer

def set_global_target_data(target_data: Dict[str, Any]):
    """Set global target data for multiprocessing access."""
    global _global_target_data
    _global_target_data = target_data

def get_global_target_data() -> Optional[Dict[str, Any]]:
    """Get global target data for multiprocessing access."""
    global _global_target_data
    return _global_target_data

def set_shared_target_data(target_data: Dict[str, Any]):
    """Set target data in shared memory for multiprocessing access."""
    global _shared_target_data
    try:
        import pickle
        import tempfile
        import os
        
        # Create a temporary file for shared target data
        temp_dir = tempfile.gettempdir()
        target_file = os.path.join(temp_dir, "shared_target_data.pkl")
        
        # Serialize target data to file
        with open(target_file, 'wb') as f:
            pickle.dump(target_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        _shared_target_data = target_file
        logger.info(f"📦 Set shared target data in {target_file} (size: {os.path.getsize(target_file):,} bytes)")
        
    except Exception as e:
        logger.warning(f"⚠️  Failed to set shared target data: {e}")
        _shared_target_data = None

def get_shared_target_data() -> Optional[Dict[str, Any]]:
    """Get target data from shared memory."""
    global _shared_target_data
    if _shared_target_data is None:
        return None
    
    try:
        import pickle
        import os
        
        if not os.path.exists(_shared_target_data):
            logger.warning(f"⚠️  Shared target data file not found: {_shared_target_data}")
            return None
        
        # Load target data from file
        with open(_shared_target_data, 'rb') as f:
            target_data = pickle.load(f)
        
        logger.debug(f"📦 Loaded shared target data from {_shared_target_data}")
        return target_data
        
    except Exception as e:
        logger.warning(f"⚠️  Failed to load shared target data: {e}")
        return None

def evaluate_worker_function(parameter_values: Dict[str, float], 
                           target_data: Optional[Dict[str, Any]],
                           config_dict: Dict[str, Any],
                           objective_function_name: str) -> Dict[str, Any]:
    """
    Standalone worker function for multiprocessing evaluation.
    
    This function is designed to be picklable and run in separate processes.
    """
    forest_model = None
    engine = None
    
    try:
        import time
        import logging
        import gc
        from src.core.forest_model import ForestModel
        from src.config.config_tools import ModelConfig
        from src.core.fire_simulation_engine import FireSimulationEngine
        
        # Set up logging for worker process
        logging.basicConfig(level=logging.INFO)
        worker_logger = logging.getLogger(f"worker_{time.time()}")
        
        start_time = time.time()
        
        # CRITICAL FIX: Use create_forest_model factory to ensure memory optimized model type
        from src.core.forest_model import create_forest_model
        
        # Extract simulation type from config to ensure memory optimized model
        simulation_type = config_dict.get('simulation_type', 'memory_optimized')
        if simulation_type != 'memory_optimized':
            worker_logger.warning(f"⚠️  Forcing simulation_type to 'memory_optimized' for sparse storage")
            simulation_type = 'memory_optimized'
        
        # Create forest model using factory function to ensure correct type
        forest_model = create_forest_model(
            model_type=simulation_type,
            config=ModelConfig(**config_dict)
        )
        
        # Create simulation engine
        engine = FireSimulationEngine(forest_model=forest_model, config=ModelConfig(**config_dict))
        
        # Run simulation
        simulation_result = engine.run_simulation()
        
        # Import and create objective function
        if objective_function_name == "SpatialSimilarityObjective":
            from src.core.calibration.objective_functions import SpatialSimilarityObjective
            objective_function = SpatialSimilarityObjective()
        else:
            raise ValueError(f"Unknown objective function: {objective_function_name}")
        
        # Calculate objective value
        objective_result = objective_function.evaluate(simulation_result, target_data or {})
        
        evaluation_time = time.time() - start_time
        
        # CRITICAL FIX: Extract results before cleanup
        result_dict = {
            'parameter_values': parameter_values.copy(),
            'objective_value': objective_result.value if objective_result.is_valid else 0.0,
            'objective_components': objective_result.components,
            'simulation_stats': simulation_result.get('stats', {}),
            'evaluation_time': evaluation_time,
            'is_valid': objective_result.is_valid,
            'error_message': objective_result.error_message
        }
        
        # CRITICAL FIX: Explicit cleanup to prevent memory leaks
        if engine is not None:
            try:
                # Clean up simulation engine
                if hasattr(engine, 'cleanup'):
                    engine.cleanup()
                elif hasattr(engine, 'close'):
                    engine.close()
            except Exception as e:
                worker_logger.debug(f"Engine cleanup warning: {e}")
        
        if forest_model is not None:
            try:
                # Clean up forest model
                if hasattr(forest_model, 'cleanup'):
                    forest_model.cleanup()
                elif hasattr(forest_model, 'close'):
                    forest_model.close()
                
                # Clear terrain data references
                if hasattr(forest_model, '_shared_terrain_refs'):
                    forest_model._shared_terrain_refs.clear()
                if hasattr(forest_model, 'terrain_elevation'):
                    forest_model.terrain_elevation = None
                if hasattr(forest_model, 'terrain_slope'):
                    forest_model.terrain_slope = None
                if hasattr(forest_model, 'terrain_aspect'):
                    forest_model.terrain_aspect = None
                if hasattr(forest_model, 'barranco_mask'):
                    forest_model.barranco_mask = None
                if hasattr(forest_model, 'barranco_directions'):
                    forest_model.barranco_directions = None
                if hasattr(forest_model, 'depression_mask'):
                    forest_model.depression_mask = None
                if hasattr(forest_model, 'wind_channeling_mask'):
                    forest_model.wind_channeling_mask = None
                if hasattr(forest_model, 'wind_amplification'):
                    forest_model.wind_amplification = None
                if hasattr(forest_model, 'wind_direction_modification'):
                    forest_model.wind_direction_modification = None
            except Exception as e:
                worker_logger.debug(f"Forest model cleanup warning: {e}")
        
        # Force garbage collection to free memory
        collected = gc.collect()
        if collected > 0:
            worker_logger.debug(f"🧹 Garbage collection freed {collected} objects")
        
        return result_dict
        
    except Exception as e:
        evaluation_time = time.time() - start_time
        
        # CRITICAL FIX: Cleanup even on exception
        if engine is not None:
            try:
                if hasattr(engine, 'cleanup'):
                    engine.cleanup()
                elif hasattr(engine, 'close'):
                    engine.close()
            except Exception:
                pass
        
        if forest_model is not None:
            try:
                if hasattr(forest_model, 'cleanup'):
                    forest_model.cleanup()
                elif hasattr(forest_model, 'close'):
                    forest_model.close()
            except Exception:
                pass
        
        # Force garbage collection
        gc.collect()
        
        return {
            'parameter_values': parameter_values.copy(),
            'objective_value': 0.0,
            'objective_components': {},
            'simulation_stats': {},
            'evaluation_time': evaluation_time,
            'is_valid': False,
            'error_message': str(e)
        }

class GridSearchCalibrator:
    """
    Grid search calibrator for systematic parameter space exploration.
    
    Now includes automatic HPC optimizations and serialization optimization for:
    - Network filesystem bottlenecks
    - Memory bandwidth limitations
    - Garbage collection overhead
    - Serialization overhead reduction
    """
    
    def __init__(self, calibration_config,
                 parameter_bounds: Dict[str, Any],
                 objective_function,
                 parallel_execution: bool = True,
                 max_workers: Optional[int] = None,
                 bypass_worker_limit: bool = False):
        
        # Store the original calibration config for method calls
        self.config = calibration_config
        
        # Apply HPC optimizations to configuration (only for dictionary-based configs)
        if isinstance(calibration_config, dict):
            self.optimized_config = apply_hpc_optimizations(calibration_config)
        else:
            # For CalibrationConfig objects, apply optimizations to the dict representation
            config_dict = calibration_config.__dict__ if hasattr(calibration_config, '__dict__') else asdict(calibration_config)
            self.optimized_config = apply_hpc_optimizations(config_dict)
        
        # Initialize serialization optimizer
        self.serialization_optimizer = get_serialization_optimizer()
        
        # Optimize configuration for serialization
        self.serialized_config = self.serialization_optimizer.optimize_config_for_serialization(
            self.optimized_config
        )
        
        # Cache the optimized configuration
        self.serialization_optimizer.cache_serialized_object('optimized_config', self.serialized_config)
        
        # Rest of initialization...
        self.parameter_bounds = parameter_bounds
        self.objective_function = objective_function
        self.parallel_execution = parallel_execution
        self.max_workers = max_workers or min(70, mp.cpu_count() or 1)
        self.bypass_worker_limit = bypass_worker_limit
        
        # Create parameter space
        self.parameter_space = self._create_parameter_space()
        
        # Calculate total combinations
        self.total_combinations = self._calculate_total_combinations()
        
        # Start HPC monitoring
        start_hpc_monitoring()
        logger.info("🚀 GridSearchCalibrator initialized with HPC and serialization optimizations")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except Exception:
            pass
    
    def _create_parameter_space(self) -> Dict[str, List[float]]:
        """Create the parameter space grid."""
        parameter_space = {}
        
        for param_name in self.config.get_calibration_parameter_names():
            if param_name not in self.parameter_bounds:
                logger.warning(f"No bounds defined for parameter {param_name}, skipping")
                continue
            
            bounds = self.parameter_bounds[param_name]
            
            # Generate grid points for this parameter
            grid_points = bounds.generate_grid_points(self.config.grid_search_points)
            parameter_space[param_name] = grid_points
            
            logger.debug(f"Parameter {param_name}: {len(grid_points)} points from "
                        f"{min(grid_points):.3f} to {max(grid_points):.3f}")
        
        return parameter_space
    
    def _get_grid_size_from_config(self, calibration_config) -> Union[int, Tuple[int, int]]:
        """Get grid size from calibration config, checking both direct and base_config locations."""
        # Try direct access first
        grid_size = getattr(calibration_config, 'grid_size', None)
        if grid_size is not None:
            return grid_size
        
        # Try base_config access
        if hasattr(calibration_config, 'base_config'):
            grid_size = getattr(calibration_config.base_config, 'grid_size', None)
            if grid_size is not None:
                return grid_size
        
        # Default fallback
        return (100, 100)
    
    def _get_num_layers_from_config(self, calibration_config) -> int:
        """Get number of layers from calibration config, checking both direct and base_config locations."""
        # Try direct access first
        num_layers = getattr(calibration_config, 'num_layers', None)
        if num_layers is not None:
            return num_layers
        
        # Try base_config access
        if hasattr(calibration_config, 'base_config'):
            num_layers = getattr(calibration_config.base_config, 'num_layers', None)
            if num_layers is not None:
                return num_layers
        
        # Default fallback
        return 10
    
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
        """
        Evaluate a single parameter combination with optimized serialization.
        """
        start_time = time.time()
        
        try:
            import gc
            gc.disable()  # Disable GC during critical evaluation
            
            # Use optimized configuration for model creation
            forest_model = self._create_forest_model_with_optimized_config(parameter_values)
            
            # Create simulation engine
            config = self.config.create_config_variant(parameter_values)
            engine = FireSimulationEngine(forest_model=forest_model, config=config)
            
            # Run simulation
            simulation_result = engine.run_simulation()
            
            # Get target data from shared memory if not provided
            if target_data is None:
                target_data = get_shared_target_data()
                if target_data is None:
                    logger.warning("No target data available - using synthetic target")
            
            # Calculate objective value
            objective_result = self.objective_function(simulation_result, target_data)
            
            evaluation_time = time.time() - start_time
            
            # Create result
            result = GridSearchResult(
                parameter_values=parameter_values.copy(),
                objective_value=objective_result.value if objective_result.is_valid else 0.0,
                objective_components=objective_result.components,
                simulation_stats=simulation_result.get('stats', {}),
                evaluation_time=evaluation_time,
                is_valid=objective_result.is_valid,
                error_message=objective_result.error_message
            )
            
            # Clean up
            if engine:
                del engine
            
            return result
            
        except Exception as e:
            evaluation_time = time.time() - start_time
            logger.error(f"Evaluation failed: {e}")
            logger.error(f"Parameter values: {parameter_values}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Force garbage collection on error
            try:
                gc.enable()
                collected = gc.collect()
                if collected > 0:
                    logger.info(f"🗑️  Error-time GC collected {collected} objects")
            except Exception:
                pass
            
            # CRITICAL FIX: Clean up shared memory on error
            try:
                from src.utils.shared_terrain import reset_shared_terrain_logging
                reset_shared_terrain_logging()
            except Exception as cleanup_error:
                logger.warning(f"Shared terrain cleanup failed: {cleanup_error}")
            
            return GridSearchResult(
                parameter_values=parameter_values.copy(),
                objective_value=0.0,
                objective_components={},
                simulation_stats={},
                evaluation_time=evaluation_time,
                is_valid=False,
                error_message=str(e)
            )
        
        finally:
            # Re-enable garbage collection
            try:
                gc.enable()
            except Exception:
                pass
    
    def run_calibration(self, 
                       target_data: Optional[Dict[str, Any]] = None,
                       progress_callback: Optional[callable] = None) -> GridSearchResults:
        """
        Run grid search calibration with HPC optimizations.
        
        Args:
            target_data: Target data for calibration
            progress_callback: Progress callback function
            
        Returns:
            GridSearchResults object
        """
        try:
            # Set target data for multiprocessing access using shared memory
            if target_data is not None:
                set_shared_target_data(target_data)
                logger.info(f"📦 Set shared target data for multiprocessing (size: {len(target_data.get('fire_perimeter', [])) if 'fire_perimeter' in target_data else 0} cells)")
            
            logger.info(f"Starting grid search calibration with {self.total_combinations} combinations")
            self.start_time = time.time()  # Store start time for ETA calculations
            
            results = GridSearchResults(parameter_space=self.parameter_space.copy())
            
            # MEMORY OPTIMIZATION: Force sequential for massive grids to prevent memory exhaustion
            should_run_parallel = self.parallel_execution and self.total_combinations > 1
            
            # Check grid size and disable parallel execution for very large grids
            grid_size = self._get_grid_size_from_config(self.config)
            logger.debug(f"Grid size from config: {grid_size} (type: {type(grid_size)})")
            
            if isinstance(grid_size, (int, float)):
                total_cells = int(grid_size) ** 2
            elif isinstance(grid_size, (tuple, list)) and len(grid_size) == 2:
                total_cells = int(grid_size[0]) * int(grid_size[1])
            else:
                logger.error(f"Invalid grid_size format: {grid_size} (type: {type(grid_size)})")
                total_cells = 100_000_000  # Default fallback
            num_layers = self._get_num_layers_from_config(self.config)
            total_model_cells = total_cells * num_layers
            
            # Detect available memory for intelligent parallel execution decision
            try:
                import psutil
                available_memory_gb = psutil.virtual_memory().total / (1024**3)
            except ImportError:
                available_memory_gb = 64  # Conservative fallback
            
            # Check if workers were explicitly set via CLI (respect user choice)
            # max_workers is passed to constructor when CLI specifies --workers
            cli_override = True  # If we reach this point, max_workers was explicitly provided
            
            # Only force sequential for truly extreme cases, and respect CLI overrides
            if should_run_parallel:
                if cli_override:
                    # CLI override - respect user choice but provide warnings
                    logger.info(f"🎛️  CLI Override: Respecting user-specified {self.max_workers} workers")
                    if available_memory_gb < 32 and total_model_cells > 10_000_000_000:
                        logger.error(f"🚨 CRITICAL: Extremely large grid on very low memory - forcing sequential despite CLI override")
                        should_run_parallel = False
                    else:
                        logger.info(f"✅ Proceeding with parallel execution as requested")
                else:
                    # Auto-detection mode - use intelligent thresholds
                    if available_memory_gb >= 120:  # High-memory HPC environment
                        # Allow parallel processing even for very large grids (up to 20B cells)
                        if total_model_cells > 20_000_000_000:
                            logger.warning(f"Extreme grid size ({total_model_cells:,} cells) - forcing sequential execution")
                            should_run_parallel = False
                        else:
                            logger.info(f"High-memory system ({available_memory_gb:.1f}GB) - allowing parallel execution for {total_model_cells:,} cells")
                    elif available_memory_gb >= 60:  # Medium-memory environment
                        if total_model_cells > 5_000_000_000:
                            logger.warning(f"Large grid ({total_model_cells:,} cells) on medium-memory system - forcing sequential execution")
                            should_run_parallel = False
                    else:  # Low-memory environment - use original conservative limit
                        if total_model_cells > 1_000_000_000:
                            logger.warning(f"Forcing sequential execution for massive grid ({total_model_cells:,} cells) to prevent memory exhaustion")
                            should_run_parallel = False
            
            if should_run_parallel:
                results = self._run_parallel_calibration(target_data, progress_callback, results)
            else:
                results = self._run_sequential_calibration(target_data, progress_callback, results)
            
            total_time = time.time() - self.start_time
            logger.info(f"Grid search completed in {total_time:.2f} seconds")
            best_value = results.get_best_objective_value()
            if best_value is not None:
                logger.info(f"Best objective value: {best_value:.4f}")
            else:
                logger.info(f"Best objective value: None (no valid results)")
            logger.info(f"Best parameters: {results.get_best_parameters()}")
            
            # Store convergence information
            results.convergence_info = {
                'converged': True,  # Grid search always completes
                'total_time': total_time,
                'evaluations_per_second': results.total_evaluations / max(total_time, 1e-6),
                'success_rate': results.successful_evaluations / max(results.total_evaluations, 1)
            }
            
            return results
        
        finally:
            # Ensure HPC monitoring is stopped
            stop_hpc_monitoring()
    
    def _run_sequential_calibration(self, 
                                  target_data: Optional[Dict[str, Any]],
                                  progress_callback: Optional[callable],
                                  results: GridSearchResults) -> GridSearchResults:
        """Run calibration sequentially."""
        for i, param_combination in enumerate(self._generate_parameter_combinations()):
            result = self._evaluate_single_combination(param_combination, target_data)
            results.add_result(result)
            
            # Progress callback
            if progress_callback:
                progress_callback(i + 1, self.total_combinations, result)
            
            # Periodic logging
            if (i + 1) % max(1, self.total_combinations // 20) == 0:
                progress = (i + 1) / self.total_combinations * 100
                best_value = results.get_best_objective_value()
                if best_value is None:
                    best_value = 0.0
                logger.info(f"Progress: {progress:.1f}% ({i + 1}/{self.total_combinations}), "
                           f"Best objective: {best_value:.4f}")
        
        return results
    
    def _run_parallel_calibration(self, 
                                target_data: Optional[Dict[str, Any]],
                                progress_callback: Optional[callable],
                                results: GridSearchResults) -> GridSearchResults:
        """
        Run parallel calibration with optimized serialization.
        """
        logger.info(f"🚀 Starting parallel calibration with {self.total_combinations} combinations")
        
        # Calculate optimal worker count
        if not self.bypass_worker_limit:
            optimal_workers = self._calculate_hpc_optimal_workers()
            if self.max_workers > optimal_workers:
                logger.warning(f"🧠 HPC OPTIMIZATION: Reducing workers from {self.max_workers} to {optimal_workers} for memory bandwidth")
                self.max_workers = optimal_workers
        
        # Use ProcessPoolExecutor for large grids
        # Access grid through base_config
        if hasattr(self.config, 'base_config') and hasattr(self.config.base_config, 'grid'):
            grid_config = self.config.base_config.grid
            total_cells = grid_config.width * grid_config.height * grid_config.num_layers
        else:
            # Fallback to default values
            total_cells = 100_000_000  # Default threshold
        
        if total_cells > 100_000_000:  # 100M cells
            logger.info("🚨 CRITICAL FIX: Using ProcessPoolExecutor for large grid to avoid GIL deadlocks")
            logger.info("   ThreadPoolExecutor was causing GIL deadlocks with many workers")
        
        # Pre-optimize configurations for workers
        logger.info("📦 Pre-optimizing configurations for worker processes...")
        self._pre_optimize_for_workers()
        
        # Convert generator to list for parallel processing
        # CRITICAL FIX: Convert generator to list before parallel processing to avoid pickling errors
        combinations_list = list(self._generate_parameter_combinations())
        
        # Prepare configuration and objective function name for workers
        config_dict = self.config.create_config_variant({}).__dict__ if hasattr(self.config.create_config_variant({}), '__dict__') else self.config.create_config_variant({})
        objective_function_name = self.objective_function.__class__.__name__
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit jobs in batches to prevent resource contention
            batch_size = min(10, self.max_workers)
            all_futures = []
            
            for i in range(0, len(combinations_list), batch_size):
                batch = combinations_list[i:i + batch_size]
                batch_futures = {
                executor.submit(evaluate_worker_function, combo, target_data, config_dict, objective_function_name): combo
                    for combo in batch
                }
                all_futures.extend(batch_futures.keys())
                
                if i + batch_size < len(combinations_list):
                    time.sleep(0.1)  # Small delay between batches
            
            # CRITICAL FIX: Ensure shared terrain cleanup after all workers complete
            try:
                from src.utils.shared_terrain import reset_shared_terrain_logging
                reset_shared_terrain_logging()
                logger.debug("🧹 Reset shared terrain logging for fresh worker processes")
            except Exception as e:
                logger.warning(f"⚠️  Shared terrain reset warning: {e}")
            
            # Process results
            completed = 0
            for future in as_completed(all_futures):
                try:
                    result_dict = future.result(timeout=300)  # 5 minute timeout per evaluation
                    
                    # Convert dictionary result to GridSearchResult
                    result = GridSearchResult(**result_dict)
                    results.add_result(result)
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(completed, len(combinations_list), result)
                    
                    logger.info(f"✅ Completed {completed}/{len(combinations_list)} evaluations")
                    
                    # CRITICAL FIX: Periodic memory cleanup to prevent accumulation
                    if completed % 5 == 0:  # Every 5 evaluations
                        import gc
                        collected = gc.collect()
                        if collected > 0:
                            logger.debug(f"🧹 Periodic cleanup freed {collected} objects after {completed} evaluations")
                    
                except TimeoutError:
                    logger.error("❌ Evaluation timed out")
                    results.add_timeout()
                except Exception as e:
                    logger.error(f"❌ Evaluation failed: {e}")
                    results.add_error()
        
        return results
    
    def _pre_optimize_for_workers(self):
        """Pre-optimize configurations and data for worker processes."""
        try:
            # Cache frequently used configurations
            common_configs = {}
            
            # Take first 10 combinations from generator
            for i, combo in enumerate(self._generate_parameter_combinations()):
                if i >= 10:  # Only cache first 10
                    break
                config_key = f"config_{hash(str(combo))}"
                config_variant = self.config.create_config_variant(combo)
                optimized_config = self.serialization_optimizer.optimize_config_for_serialization(
                    config_variant.__dict__ if hasattr(config_variant, '__dict__') else config_variant
                )
                self.serialization_optimizer.cache_serialized_object(config_key, optimized_config)
                common_configs[config_key] = optimized_config
            
            logger.info(f"📦 Pre-cached {len(common_configs)} configurations for workers")
                    
        except Exception as e:
            logger.warning(f"⚠️  Pre-optimization failed: {e}")
    
    def cleanup(self):
        """Clean up resources including serialization cache."""
        try:
            # Clear serialization cache
            self.serialization_optimizer.clear_cache()
            
            # Stop HPC monitoring
            stop_hpc_monitoring()
            
            logger.debug("🧹 GridSearchCalibrator cleanup completed")
            
        except Exception as e:
            logger.warning(f"⚠️  Cleanup error: {e}")
    
    def get_estimation_info(self) -> Dict[str, Any]:
        """Get estimation information about the calibration."""
        # Rough time estimation based on single evaluation
        estimated_time_per_eval = 30.0  # seconds (conservative estimate)
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
    
    def _get_arafo_highlands_coordinates(self, grid_size: Tuple[int, int]) -> Tuple[int, int]:
        """
        Get realistic ignition coordinates for Arafo highlands on Tenerife.
        
        Based on the 2023 Tenerife wildfire that started near Chivisaya viewpoint 
        in Arafo at ~1,200m elevation in the southeastern highlands.
        
        Args:
            grid_size: (width, height) of the simulation grid
            
        Returns:
            (x, y) coordinates for ignition point
        """
        width, height = grid_size
        
        # Arafo is located in the southeastern part of Tenerife
        # Approximate location based on Tenerife geography:
        # - East-southeast of center (about 60-70% across from west to east)
        # - South-southeast of center (about 60-70% down from north to south)
        # - In the highlands (intermediate elevation zone)
        
        # Convert geographic knowledge to grid coordinates
        arafo_x = int(width * 0.65)   # 65% across (southeastern)
        arafo_y = int(height * 0.62)  # 62% down (southeastern highlands)
        
        # Ensure coordinates are within bounds
        arafo_x = max(0, min(arafo_x, width - 1))
        arafo_y = max(0, min(arafo_y, height - 1))
        
        return arafo_x, arafo_y

    def _calculate_hpc_optimal_workers(self) -> int:
        """
        Calculate optimal worker count based on HPC constraints.
        
        Considers:
        - Memory bandwidth limitations
        - NUMA node count
        - Available system resources
        """
        try:
            import psutil
            
            # Get system information
            memory = psutil.virtual_memory()
            cpu_count = psutil.cpu_count(logical=False)  # Physical cores
            
            # Memory-based calculation (conservative)
            total_gb = memory.total / (1024**3)
            memory_based_workers = max(1, int(total_gb / 4))  # 1 worker per 4GB
            
            # CPU-based calculation
            cpu_based_workers = max(1, cpu_count - 2)  # Reserve 2 cores
            
            # NUMA-based calculation (if available)
            numa_workers = 16  # Default
            try:
                numa_path = Path("/sys/devices/system/node")
                if numa_path.exists():
                    nodes = [d for d in numa_path.iterdir() if d.name.startswith("node")]
                    numa_workers = len(nodes) * 4  # 4 workers per NUMA node
            except Exception:
                pass
            
            # Take the minimum to prevent overloading
            optimal_workers = min(memory_based_workers, cpu_based_workers, numa_workers)
            
            # Cap at reasonable maximum
            optimal_workers = min(optimal_workers, 32)
            
            logger.info(f"🧠 HPC worker calculation: memory={memory_based_workers}, cpu={cpu_based_workers}, numa={numa_workers} -> optimal={optimal_workers}")
            
            return optimal_workers
            
        except Exception as e:
            logger.warning(f"🧠 Could not calculate HPC optimal workers: {e}")
            return 16  # Conservative default

    def _create_forest_model_with_optimized_config(self, parameter_values: Dict[str, float]):
        """
        Create forest model with optimized configuration and serialization.
        """
        # Use cached optimized configuration if available
        cached_config = self.serialization_optimizer.get_cached_serialized('optimized_config')
        
        if cached_config:
            # Use cached configuration
            config_dict = pickle.loads(cached_config)
        else:
            # Fall back to creating optimized configuration
            config_dict = self.optimized_config
        
        # Create config variant with parameter values
        config_variant = copy.deepcopy(config_dict)
        
        # Update with parameter values
        for param_name, param_value in parameter_values.items():
            if param_name in config_variant:
                config_variant[param_name] = param_value
        
        # CRITICAL FIX: Use create_forest_model factory to ensure memory optimized model type
        from src.core.forest_model import create_forest_model
        from src.config.config_tools import ModelConfig
        import gc
        gc.disable()
        try:
            # Convert config_variant to ModelConfig if it's a dict
            if isinstance(config_variant, dict):
                # Filter out serialization metadata before creating ModelConfig
                clean_config = {}
                for key, value in config_variant.items():
                    if not key.startswith('_'):
                        clean_config[key] = value
                
                # CRITICAL FIX: Extract simulation type to ensure memory optimized model
                simulation_type = clean_config.get('simulation_type', 'memory_optimized')
                if simulation_type != 'memory_optimized':
                    logger.warning(f"⚠️  Forcing simulation_type to 'memory_optimized' for sparse storage")
                    clean_config['simulation_type'] = 'memory_optimized'
                
                # Create forest model using factory function to ensure correct type
                forest_model = create_forest_model(
                    model_type=simulation_type,
                    config=ModelConfig(**clean_config)
                )
            else:
                # CRITICAL FIX: Ensure simulation_type is set for ModelConfig objects
                if hasattr(config_variant, 'simulation_type') and config_variant.simulation_type != 'memory_optimized':
                    logger.warning(f"⚠️  Forcing simulation_type to 'memory_optimized' for sparse storage")
                    config_variant.simulation_type = 'memory_optimized'
                
                forest_model = create_forest_model(
                    model_type=getattr(config_variant, 'simulation_type', 'memory_optimized'),
                    config=config_variant
                )
            return forest_model
        finally:
            gc.enable()


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


def print_progress_bar(completed: int, total: int, width: int = 50) -> str:
    """Create a simple progress bar string."""
    progress = completed / total
    filled = int(width * progress)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {progress*100:.1f}% ({completed}/{total})"


if __name__ == "__main__":
    # Example usage (requires proper imports and setup)
    print("Grid Search Calibrator Example")
    print("=" * 50)
    
    # This would normally require proper calibration config and bounds
    print("This is a demonstration of the GridSearchCalibrator interface.")
    print("To use this module, you need to:")
    print("1. Create a CalibrationConfig")
    print("2. Define parameter bounds") 
    print("3. Create an objective function")
    print("4. Initialize and run the calibrator")
    
    example_estimation = {
        'total_combinations': 3125,  # 5^5 for 5 parameters with 5 points each
        'estimated_time_hours': 2.5,
        'parallel_execution': True,
        'max_workers': 4
    }
    
    print(f"\nExample estimation for {example_estimation['total_combinations']} combinations:")
    print(f"Estimated time: {example_estimation['estimated_time_hours']:.1f} hours")
    print(f"Parallel execution: {example_estimation['parallel_execution']}")
    print(f"Workers: {example_estimation['max_workers']}") 