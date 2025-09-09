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
    from src.core.forest_model import create_forest_model, MemoryOptimizedForestModel
    from src.core.calibration.objective_functions import ObjectiveResult
except ImportError:
    try:
        from utils.logging_utils import get_logger
        from core.forest_model import create_forest_model, MemoryOptimizedForestModel
        from core.calibration.objective_functions import ObjectiveResult
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

logger = get_logger(__name__)
# Set main logger level to WARNING to reduce verbosity
logger.setLevel(logging.WARNING)

# Set worker logger level to WARNING to reduce verbose output
def get_worker_logger(name):
    worker_logger = logging.getLogger(name)
    worker_logger.setLevel(logging.WARNING)
    return worker_logger


class GridSearchResult:
    """Single result from grid search evaluation."""
    
    def __init__(self, parameter_values: Dict[str, float], objective_result: 'ObjectiveResult', 
                 simulation_stats: Dict[str, Any], evaluation_time: float, vertical_fire_spread: Optional[Dict[str, Any]] = None):
        self.parameter_values = parameter_values
        self.objective_result = objective_result
        self.simulation_stats = simulation_stats
        self.evaluation_time = evaluation_time
        self.vertical_fire_spread = vertical_fire_spread
    
    # Convenience properties for backward compatibility
    @property
    def objective_value(self) -> float:
        return self.objective_result.value
    
    @property
    def objective_components(self) -> Dict[str, float]:
        return self.objective_result.components
    
    @property
    def is_valid(self) -> bool:
        return self.objective_result.is_valid
    
    @property
    def error_message(self) -> str:
        return self.objective_result.error_message


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
        
        # Find best result (CRITICAL FIX: Use min() for error minimization objective)
        valid_results = [r for r in self.results if r.is_valid]
        if valid_results:
            self.best_result = min(valid_results, key=lambda x: x.objective_value)
    
    def add_result(self, result: GridSearchResult):
        """Add a new result and update statistics."""
        self.results.append(result)
        self._update_statistics()
    
    def add_error(self):
        """Add an error result to track failed evaluations."""
        error_objective = ObjectiveResult(
            value=0.0,
            components={},
            is_valid=False,
            error_message="Evaluation failed"
        )
        error_result = GridSearchResult(
            parameter_values={},
            objective_result=error_objective,
            simulation_stats={},
            evaluation_time=0.0,
            vertical_fire_spread=None
        )
        self.results.append(error_result)
        self._update_statistics()
    
    def add_timeout(self):
        """Add a timeout result to track timed out evaluations."""
        timeout_objective = ObjectiveResult(
            value=0.0,
            components={},
            is_valid=False,
            error_message="Evaluation timed out"
        )
        timeout_result = GridSearchResult(
            parameter_values={},
            objective_result=timeout_objective,
            simulation_stats={},
            evaluation_time=0.0,
            vertical_fire_spread=None
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
                    'vertical_fire_spread': getattr(r, 'vertical_fire_spread', None),
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
        
        # Import the serialization function
        from src.core.calibration.calibration_utils import _convert_to_serializable
        
        with open(filepath, 'w') as f:
            json.dump(_convert_to_serializable(results_data), f, indent=2)
        
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
        logger.debug(f"📦 Set shared target data in {target_file} (size: {os.path.getsize(target_file):,} bytes)")
        
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
                           objective_function_name: str,
                           worker_id: int = 0) -> Dict[str, Any]:
    """
    Standalone worker function for multiprocessing evaluation.
    
    This function is designed to be picklable and run in separate processes.
    """
    # CRITICAL FIX: Add import synchronization to prevent deadlock
    import threading
    import time
    
    # Global import lock to prevent multiple workers importing simultaneously
    if not hasattr(evaluate_worker_function, '_import_lock'):
        evaluate_worker_function._import_lock = threading.Lock()
    
    # Wait for import lock with timeout to prevent infinite hanging
    if not evaluate_worker_function._import_lock.acquire(timeout=30):
        print(f"⚠️  Worker {worker_id}: Import lock timeout - proceeding anyway")
    else:
        try:
            # CRITICAL FIX: Import all required modules at the top to avoid scoping issues
            import logging
            import gc
            import sys
            from src.core.forest_model import ForestModel, create_forest_model
            from src.config.config_tools import ModelConfig
            from src.core.fire_simulation_engine import FireSimulationEngine
        finally:
            evaluate_worker_function._import_lock.release()
    
    # CRITICAL FIX: Add function to get objective function by name
    def get_objective_function_by_name(name):
        if name == "SpatialSimilarityObjective":
            from src.core.calibration.objective_functions import SpatialSimilarityObjective
            return SpatialSimilarityObjective()
        elif name == "CorrectedSpatialErrorObjective":
            from src.core.calibration.objective_functions_corrected import CorrectedSpatialErrorObjective
            return CorrectedSpatialErrorObjective()
        else:
            raise ValueError(f"Unknown objective function: {name}")
    
    # CRITICAL FIX: Add global KeyError 7 handler to catch ALL instances
    original_excepthook = sys.excepthook
    
    def keyerror_7_handler(exctype, value, traceback):
        if exctype == KeyError and hasattr(value, 'args') and len(value.args) > 0:
            if value.args[0] == 7:
                print(f"🔍 GLOBAL KeyError 7 caught: {value}")
                print(f"🔍 This KeyError 7 is happening outside the simulation engine")
                import traceback as tb
                tb.print_exception(exctype, value, traceback)
            elif value.args[0] == 11:
                print(f"🔍 GLOBAL KeyError 11 caught: {value}")
                print(f"🔍 This KeyError 11 is happening outside the simulation engine")
                import traceback as tb
                tb.print_exception(exctype, value, traceback)
        original_excepthook(exctype, value, traceback)
    
    sys.excepthook = keyerror_7_handler
    
    forest_model = None
    engine = None
    
    # Set up logging for worker process - MINIMAL OUTPUT
    worker_logger = logging.getLogger(f"worker_{time.time()}")
    worker_logger.setLevel(logging.WARNING)  # Reduced to WARNING to minimize output
    
    # Clear any existing handlers
    for handler in worker_logger.handlers[:]:
        worker_logger.removeHandler(handler)
    
    # Add a single handler with minimal formatting
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[WORKER] %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    worker_logger.addHandler(handler)
    
    # Critical: Prevent propagation to avoid duplicate logging
    worker_logger.propagate = False
    
    # Only log critical errors from first worker
    if worker_id < 1:
        worker_logger.error(f"Worker {worker_id} started")
    
    # CRITICAL FIX: Validate that we have actual parameters
    if not parameter_values:
        worker_logger.error(f"🎯 WORKER {worker_id}: No parameters provided!")
        return {
            'parameter_values': {},
            'objective_result': ObjectiveResult(
                value=0.0,
                components={},
                is_valid=False,
                error_message="No parameters provided"
            ),
            'simulation_stats': {},
            'evaluation_time': 0.0
        }
    
    try:
        # Also disable propagation for all child loggers
        for name in ['src.core.fire_simulation_engine', 'src.core.forest_model', 'src.core.calibration.objective_functions']:
            child_logger = logging.getLogger(name)
            child_logger.propagate = False
            # Clear any existing handlers to prevent duplicates
            for child_handler in child_logger.handlers[:]:
                child_logger.removeHandler(child_handler)
        
        # EMERGENCY FIX: Add timeout for worker initialization
        import threading
        import time
        
        worker_ready = threading.Event()
        worker_error = None
        worker_result = None
        
        def run_worker_with_timeout():
            nonlocal worker_error, worker_result
            # Import threading at the top of the function
            import threading
            import time
            try:
                # CRITICAL FIX: Extract simulation_type from config_dict instead of passing entire dict
                simulation_type = config_dict.get('simulation_type', 'memory_optimized')
                if simulation_type not in ['standard', 'memory_optimized']:
                    worker_logger.warning(f"⚠️  Invalid simulation_type '{simulation_type}', using 'memory_optimized'")
                    simulation_type = 'memory_optimized'
        
                # CRITICAL FIX: Create ModelConfig object from config_dict
                worker_logger.debug("🔧 Creating ModelConfig...")
                from src.config.config_tools import ModelConfig
                
                # Extract timeout before creating ModelConfig (ModelConfig doesn't accept this parameter)
                timeout_minutes = config_dict.pop('simulation_timeout_minutes', None)
                
                # Ensure unique random seed for each worker to prevent identical results
                # CRITICAL FIX: Use worker_id to create unique seeds for each worker
                base_seed = config_dict.get('random_seed', 42)
                # Use a large multiplier to ensure seeds are well-separated and unique
                worker_seed = base_seed + (worker_id * 100000)
                
                # Create a copy of config_dict to avoid modifying the shared config
                worker_config_dict = config_dict.copy()
                worker_config_dict['random_seed'] = worker_seed
                
                # DEBUG: Log the seed generation to verify uniqueness (REDUCED VERBOSITY)
                if worker_id < 1:  # Only log first worker
                    worker_logger.info(f"🔧 Worker {worker_id}: seed={worker_seed}, params={parameter_values}")
                
                # CRITICAL: Each worker tests DIFFERENT parameter combinations for grid search
                # This ensures we explore the full parameter space systematically
                
                # CRITICAL FIX: Debug the worker_config_dict before filtering
                worker_logger.debug(f"🔍 worker_config_dict keys before filtering: {list(worker_config_dict.keys())}")
                worker_logger.debug(f"🔍 ignition_points in worker_config_dict BEFORE filtering: {'ignition_points' in worker_config_dict}")
                if 'ignition_points' in worker_config_dict:
                    worker_logger.debug(f"🔍 ignition_points value BEFORE filtering: {worker_config_dict['ignition_points']}")
                if 'grid_size' in worker_config_dict:
                    worker_logger.debug(f"🔍 worker_config_dict grid_size: {worker_config_dict['grid_size']}")
                else:
                    worker_logger.debug(f"🔍 grid_size NOT in worker_config_dict")
                
                # CRITICAL FIX: Only keep valid ModelConfig parameters
                valid_params = [
                    'grid_size', 'num_layers', 'layer_height', 'model_resolution', 'max_steps', 'random_seed',
                    'debug', 'store_full_states', 'stop_when_fire_extinguished', 'spread_probability',
                    'fuel_consumption_rate', 'ignition_threshold', 'min_fuel_value', 'max_fuel_value',
                    'initial_fuel_load', 'fuel_moisture_baseline', 'wind_speed', 'wind_direction', 'temperature',
                    'humidity', 'reference_wind_speed', 'wind_influence_on_spread', 'slope_influence',
                    'terrain_effect_strength', 'barranco_threshold', 'barranco_amplification',
                    'barranco_direction_weight', 'min_depression_depth', 'min_depression_area',
                    'ember_probability', 'ember_distance', 'ember_ignition', 'ember_height_factor',
                    'ember_rise', 'ember_wind_factor', 'memory_optimization_level', 'use_disk_storage',
                    'use_sparse_storage', 'disk_storage_dir', 'bytes_per_cell', 'tile_size', 'chunk_size',
                    'simulation_type', 'output_dir', 'results_output_dir', 'logs_output_dir',
                    'checkpoints_output_dir', 'monitoring_output_dir', 'temp_storage_dir',
                    'history_keyframe_interval', 'engine_logging_interval', 'ignition_points',
                    'config_name', 'config_version', 'extinction_coefficient', 'pad_bin_size',
                    'exclude_ground_layer', 'use_lidar', 'auto_size_from_lidar', 'max_grid_size',
                    'max_vegetation_height_m', 'lidar_load_max_retries', 'lidar_load_retry_delay_seconds',
                    'lidar_data_dir', 'preprocessed_lidar_dir', 'use_terrain', 'dem_file', 'use_preprocessed_terrain', 'preprocessed_terrain_dir',
                    'terrain_preprocessing_config', 'hpc_io_block_size', 'hpc_memory_limit_per_node',
                    'hpc_mode_gdal', 'gdal_cache_mb', 'gdal_thread_count', 'max_parallel_tiles',
                    'reserve_cpus', 'save_interval'
                ]
                
                # Keep only valid parameters
                filtered_config = {}
                for param in valid_params:
                    if param in worker_config_dict:
                        filtered_config[param] = worker_config_dict[param]
                
                worker_config_dict = filtered_config
                
                # 🚨 CRITICAL FIX: FORCE ignition_points into worker_config_dict if missing
                if 'ignition_points' not in worker_config_dict:
                    worker_config_dict['ignition_points'] = [(395, 377, 0)]  # Force default ignition
                    worker_logger.warning(f"🚨 FORCED ignition_points into worker_config_dict: {worker_config_dict['ignition_points']}")
                
                # CRITICAL DEBUG: Check if ignition_points survived filtering
                worker_logger.debug(f"🔍 worker_config_dict keys after filtering: {list(worker_config_dict.keys())}")
                worker_logger.debug(f"🔍 ignition_points in filtered config: {'ignition_points' in worker_config_dict}")
                if 'ignition_points' in worker_config_dict:
                    worker_logger.debug(f"🔍 ignition_points value after filtering: {worker_config_dict['ignition_points']}")
                
                model_config = ModelConfig(**worker_config_dict)
                worker_logger.debug(f"✅ ModelConfig created successfully with worker seed: {worker_seed}")
                worker_logger.debug(f"🔍 ModelConfig grid_size: {model_config.grid_size}")
                
                # CRITICAL FIX: Apply parameter values to ModelConfig
                for param_name, param_value in parameter_values.items():
                    if hasattr(model_config, param_name):
                        setattr(model_config, param_name, param_value)
                        worker_logger.debug(f"   🔧 Applied {param_name} = {param_value}")
                    else:
                        worker_logger.warning(f"   ⚠️ Parameter {param_name} not found in ModelConfig")
                
                worker_logger.debug(f"🔍 ModelConfig grid_size after parameter application: {model_config.grid_size}")
                
                # Store timeout for later use
                if timeout_minutes is not None:
                    model_config._simulation_timeout_minutes = timeout_minutes
                
                # CRITICAL FIX: Add aggressive optimizations for massive grids
                grid_size = model_config.grid_size
                if isinstance(grid_size, (tuple, list)) and len(grid_size) == 2:
                    total_cells = grid_size[0] * grid_size[1]
                    if total_cells > 10_000_000:  # 10M+ cells
                        worker_logger.debug(f"🚨 MASSIVE GRID DETECTED: {total_cells:,} cells - applying smart optimizations")
                        
                        # Scale max_steps based on grid size (conservative scaling for accuracy)
                        if hasattr(model_config, 'max_steps') and model_config.max_steps > 150:
                            original_steps = model_config.max_steps
                            if total_cells > 50_000_000:  # 50M+ cells - moderate scaling
                                model_config.max_steps = min(200, int(model_config.max_steps * 0.8))
                            elif total_cells > 20_000_000:  # 20M+ cells - light scaling
                                model_config.max_steps = min(250, int(model_config.max_steps * 0.9))
                            else:  # 10-20M cells - minimal scaling
                                model_config.max_steps = min(280, int(model_config.max_steps * 0.95))
                            worker_logger.debug(f"🚨 Scaled max_steps from {original_steps} to {model_config.max_steps} based on grid size")
                        
                        # Enable early termination
                        if hasattr(model_config, 'stop_when_fire_extinguished'):
                            model_config.stop_when_fire_extinguished = True
                            worker_logger.debug("🚨 Enabled early termination for massive grid")
                        
                        # Reduce memory usage
                        if hasattr(model_config, 'memory_optimization_level'):
                            model_config.memory_optimization_level = 3  # Maximum optimization
                            worker_logger.debug("🚨 Set maximum memory optimization level")
                        
                        # Force sparse storage
                        if hasattr(model_config, 'use_sparse_storage'):
                            model_config.use_sparse_storage = True
                            worker_logger.debug("🚨 Forced sparse storage for massive grid")
                
                # CRITICAL FIX: Add timeout for shared terrain loading to prevent hangs
                if hasattr(model_config, 'shared_terrain_info') and model_config.shared_terrain_info:
                    worker_logger.debug("Shared terrain info detected, adding timeout protection")
                    
                    # Set a timeout for shared terrain loading in the forest model
                    terrain_loaded = threading.Event()
                    terrain_error = None
                    
                    def load_terrain_with_timeout():
                        nonlocal terrain_error
                        try:
                            # This will be handled by the forest model's _try_load_shared_terrain method
                            # We just need to ensure it doesn't hang indefinitely
                            worker_logger.debug("Shared terrain loading started")
                            # The actual loading happens in forest model initialization
                            terrain_loaded.set()
                        except Exception as e:
                            terrain_error = e
                            terrain_loaded.set()
                    
                    # Start terrain loading in a separate thread
                    terrain_thread = threading.Thread(target=load_terrain_with_timeout)
                    terrain_thread.daemon = True
                    terrain_thread.start()
                    
                    # Wait for terrain loading with timeout (30 seconds)
                    if not terrain_loaded.wait(timeout=30.0):
                        worker_logger.warning("⚠️  Shared terrain loading timed out after 30 seconds, continuing without shared terrain")
                        # Disable shared terrain to prevent hangs
                        model_config.shared_terrain_info = None
                    elif terrain_error:
                        worker_logger.warning(f"⚠️  Shared terrain loading failed: {terrain_error}, continuing without shared terrain")
                        model_config.shared_terrain_info = None
                    else:
                        worker_logger.debug("Shared terrain loading completed successfully")
                else:
                    worker_logger.debug("No shared terrain info - will load individually")
                
                # Create forest model with proper parameters and timeout protection
                worker_logger.debug("🌲 Creating forest model...")
                
                # Add timeout for forest model creation
                forest_model = None
                forest_ready = threading.Event()
                forest_error = None
                
                def create_forest_with_timeout():
                    nonlocal forest_model, forest_error
                    try:
                        worker_logger.info(f"🌲 Worker {worker_id}: Starting forest model creation...")
                        worker_logger.info(f"🌲 Worker {worker_id}: Grid size: {model_config.grid_size}")
                        worker_logger.info(f"🌲 Worker {worker_id}: LiDAR enabled: {getattr(model_config, 'use_lidar', False)}")
                        
                        # 🚨 CRITICAL FIX: Use SAME forest model as validation script (which works!)
                        from src.core.optimized_forest_model import OptimizedMemoryOptimizedForestModel
                        forest_model = OptimizedMemoryOptimizedForestModel(
                            grid_size=model_config.grid_size,
                            num_layers=model_config.num_layers,
                            layer_height_meters=model_config.layer_height,
                            model_resolution=model_config.model_resolution,
                            initial_fuel_load=model_config.initial_fuel_load,
                            config=model_config
                        )
                        
                        worker_logger.info(f"✅ Worker {worker_id}: Forest model created successfully: {type(forest_model)}")
                        
                        forest_ready.set()
                    except Exception as e:
                        forest_error = e
                        worker_logger.error(f"Forest model creation failed: {e}")
                        forest_ready.set()
                
                # Start forest model creation in a separate thread
                forest_thread = threading.Thread(target=create_forest_with_timeout)
                forest_thread.daemon = True
                forest_thread.start()
                
                # Calculate forest model creation timeout based on grid size
                grid_size = model_config.grid_size
                if isinstance(grid_size, (tuple, list)) and len(grid_size) == 2:
                    total_cells = grid_size[0] * grid_size[1]
                    if total_cells > 50_000_000:  # 50M+ cells
                        forest_timeout = 5400.0  # 1.5 hours for massive grids
                    elif total_cells > 20_000_000:  # 20M+ cells
                        forest_timeout = 5400.0  # 1.5 hours for large grids
                    elif total_cells > 10_000_000:  # 10M+ cells
                        forest_timeout = 5400.0  # 1.5 hours for medium grids
                    else:
                        forest_timeout = 5400.0   # 1.5 hours for smaller grids
                else:
                    forest_timeout = 5400.0  # Default 1.5 hours
                
                worker_logger.debug(f"⏱️  Forest model creation timeout: {forest_timeout} seconds")
                
                # Wait for forest model creation with dynamic timeout
                if not forest_ready.wait(timeout=forest_timeout):
                     worker_logger.warning(f"⏰ Forest model creation timed out after {forest_timeout} seconds")
                     return {
                         'parameter_values': parameter_values,
                         'objective_result': ObjectiveResult(
                             value=0.0,
                             components={},
                             is_valid=False,
                             error_message=f"Forest model creation timed out after {forest_timeout} seconds - no partial results available"
                         ),
                         'simulation_stats': {'forest_model_timeout': True},
                         'evaluation_time': time.time()
                     }
                if forest_error:
                    worker_logger.error(f"❌ Forest model creation failed: {forest_error}")
                    return {
                        'parameter_values': parameter_values,
                        'objective_result': ObjectiveResult(
                            value=0.0,
                            components={},
                            is_valid=False,
                            error_message=f"Forest model creation failed: {forest_error}"
                        ),
                        'simulation_stats': {},
                        'evaluation_time': time.time()
                    }

                
                if forest_model is None:
                    worker_logger.error("❌ Forest model is None after creation")
                    return {
                        'parameter_values': parameter_values,
                        'objective_result': ObjectiveResult(
                            value=0.0,
                            components={},
                            is_valid=False,
                            error_message="Forest model is None after creation"
                        ),
                        'simulation_stats': {},
                        'evaluation_time': time.time()
                    }
                
                # Create simulation engine with timeout protection
                worker_logger.debug("Creating FireSimulationEngine...")
                
                # Add timeout for engine creation
                engine = None
                engine_ready = threading.Event()
                engine_error = None
                
                def create_engine_with_timeout():
                    nonlocal engine, engine_error
                    try:
                        worker_logger.debug("Creating FireSimulationEngine...")
                        
                        engine = FireSimulationEngine(forest_model=forest_model, config=model_config)
                        
                        worker_logger.debug(f"FireSimulationEngine created successfully: {type(engine)}")
                        engine_ready.set()
                    except Exception as e:
                        engine_error = e
                        worker_logger.error(f"Engine creation failed: {e}")
                        engine_ready.set()
                
                # Start engine creation in a separate thread
                engine_thread = threading.Thread(target=create_engine_with_timeout)
                engine_thread.daemon = True
                engine_thread.start()
                
                # Wait for engine creation with timeout (30 seconds)
                if not engine_ready.wait(timeout=30.0):
                     worker_logger.warning("⏰ Engine creation timed out after 30 seconds")
                     return {
                         'parameter_values': parameter_values,
                         'objective_result': ObjectiveResult(
                             value=0.0,
                             components={},
                             is_valid=False,
                             error_message="Engine creation timed out after 30 seconds - no partial results available"
                         ),
                         'simulation_stats': {'engine_creation_timeout': True},
                         'evaluation_time': time.time()
                     }
                if engine_error:
                    worker_logger.error(f"❌ Engine creation failed: {engine_error}")
                    return {
                        'parameter_values': parameter_values,
                        'objective_result': ObjectiveResult(
                            value=0.0,
                            components={},
                            is_valid=False,
                            error_message=f"Engine creation failed: {engine_error}"
                        ),
                        'simulation_stats': {},
                        'evaluation_time': time.time()
                    }
                
                if engine is None:
                    worker_logger.error("❌ Engine is None after creation")
                    return {
                        'parameter_values': parameter_values,
                        'objective_result': ObjectiveResult(
                            value=0.0,
                            components={},
                            is_valid=False,
                            error_message="Engine is None after creation"
                        ),
                        'simulation_stats': {},
                        'evaluation_time': time.time()
                    }
                
                # Set ignition points AFTER simulation engine is created (same as validation script)
                worker_logger.debug("Setting ignition points from config...")
                ignition_set = False
                try:
                    # CRITICAL DEBUG: Check config for ignition points
                    worker_logger.debug(f"🔍 DEBUG: model_config type: {type(model_config)}")
                    worker_logger.debug(f"🔍 DEBUG: hasattr ignition_points: {hasattr(model_config, 'ignition_points')}")
                    
                    # Try multiple ways to get ignition points
                    ignition_points = None
                    if hasattr(model_config, 'ignition_points') and model_config.ignition_points:
                        ignition_points = model_config.ignition_points
                        worker_logger.debug(f"✅ Found ignition_points in model_config: {ignition_points}")
                    elif isinstance(model_config, dict) and 'ignition_points' in model_config:
                        ignition_points = model_config['ignition_points']
                        worker_logger.debug(f"✅ Found ignition_points in config dict: {ignition_points}")
                    
                    if ignition_points:
                        for ignition_point in ignition_points:
                            forest_model.set_ignition(ignition_point[0], ignition_point[1], ignition_point[2])
                            worker_logger.debug(f"✅ Ignition point set from config: ({ignition_point[0]}, {ignition_point[1]}, {ignition_point[2]})")
                            
                            # Also set it in the simulation engine's active cells
                            if hasattr(engine, 'active_cells'):
                                engine.active_cells.add((ignition_point[0], ignition_point[1], ignition_point[2]))
                                worker_logger.debug(f"✅ Added ignition point to engine active cells: {ignition_point}")
                            ignition_set = True
                    
                    # CRITICAL FALLBACK: Always ensure ignition is set
                    if not ignition_set:
                        worker_logger.warning("⚠️ No ignition points found in config - using default")
                        default_x, default_y = 395, 377  # Center of 609×609 grid
                        forest_model.set_ignition(default_x, default_y, 0)
                        worker_logger.debug(f"✅ Default ignition point set: ({default_x}, {default_y}, 0)")
                        if hasattr(engine, 'active_cells'):
                            engine.active_cells.add((default_x, default_y, 0))
                        ignition_set = True
                    
                except Exception as ignition_error:
                    worker_logger.warning(f"⚠️ Failed to set ignition point: {ignition_error}")
                    # EMERGENCY FALLBACK
                    if not ignition_set:
                        try:
                            default_x, default_y = 395, 377
                            forest_model.set_ignition(default_x, default_y, 0)
                            worker_logger.debug(f"🚨 Emergency ignition point set: ({default_x}, {default_y}, 0)")
                            if hasattr(engine, 'active_cells'):
                                engine.active_cells.add((default_x, default_y, 0))
                        except Exception as emergency_error:
                            worker_logger.error(f"❌ Emergency ignition failed: {emergency_error}")
                
                # Run simulation with timeout protection
                worker_logger.debug("Starting simulation run...")
                
                simulation_result = None
                simulation_ready = threading.Event()
                simulation_error = None
                
                def run_simulation_with_timeout():
                    nonlocal simulation_result, simulation_error
                    try:
                        worker_logger.debug("Running simulation...")
                        
                        simulation_result = engine.run_simulation()
                        
                        worker_logger.debug("Simulation completed successfully")
                        simulation_ready.set()
                    except Exception as e:
                        simulation_error = e
                        worker_logger.error(f"Simulation failed: {e}")
                        simulation_ready.set()
                
                # Start simulation in a separate thread
                simulation_thread = threading.Thread(target=run_simulation_with_timeout)
                simulation_thread.daemon = True
                simulation_thread.start()
                
                # Calculate dynamic timeout based on grid size and configuration
                grid_size = model_config.grid_size
                if isinstance(grid_size, (tuple, list)) and len(grid_size) == 2:
                    total_cells = grid_size[0] * grid_size[1]
                    
                    # Check if timeout is specified in model_config (from calibration config)
                    config_timeout_minutes = getattr(model_config, '_simulation_timeout_minutes', None)
                    if config_timeout_minutes is not None:
                        timeout_seconds = config_timeout_minutes * 60.0  # Convert minutes to seconds
                        worker_logger.debug(f"⏱️  Using configured timeout: {config_timeout_minutes} minutes ({timeout_seconds} seconds)")
                    else:
                        # Fallback to grid-size based timeout
                        if total_cells > 50_000_000:  # 50M+ cells
                            timeout_seconds = 3600.0  # 1 hour for massive grids
                        elif total_cells > 20_000_000:  # 20M+ cells
                            timeout_seconds = 3600.0   # 1 hour for large grids
                        elif total_cells > 10_000_000:  # 10M+ cells
                            timeout_seconds = 3600.0   # 1 hour for medium grids
                        else:
                            timeout_seconds = 3600.0   # 1 hour for smaller grids
                        worker_logger.debug(f"⏱️  Using grid-size based timeout: {timeout_seconds} seconds for {total_cells:,} cells")
                else:
                    timeout_seconds = 300.0  # Default 5 minutes
                    worker_logger.debug(f"⏱️  Using default timeout: {timeout_seconds} seconds")
                
                # Wait for simulation with dynamic timeout
                if not simulation_ready.wait(timeout=timeout_seconds):
                     worker_logger.warning(f"⏰ Simulation timed out after {timeout_seconds} seconds - storing partial results")
                     
                     # Try to get partial results from the simulation engine if available
                     partial_stats = {}
                     partial_objective = None
                     
                     if engine is not None:
                         try:
                             # Get current state from engine
                             if hasattr(engine, 'active_cells') and hasattr(engine, 'burned_cells'):
                                 active_count = len(engine.active_cells)
                                 burned_count = len(engine.burned_cells)
                                 partial_stats = {
                                     'total_burned_cells': burned_count,
                                     'final_active_cells': active_count,
                                     'steps': getattr(engine, 'current_step', 0),
                                     'timeout_occurred': True,
                                     'partial_results': True
                                 }
                                 
                                 # Create a partial fire perimeter for objective calculation
                                 if hasattr(engine, 'forest_model') and engine.forest_model is not None:
                                     try:
                                         # Get current state from forest model
                                         current_state = engine.forest_model.get_state()
                                         
                                         # Create partial simulation result
                                         partial_simulation_result = {
                                             'fire_perimeter': current_state,
                                             'stats': partial_stats,
                                             'partial_results': True
                                         }
                                         
                                         # Calculate objective with partial results
                                         objective_function = get_objective_function_by_name(objective_function_name)
                                         partial_objective = objective_function.evaluate(partial_simulation_result, target_data)
                                         
                                         worker_logger.info(f"✅ Stored partial results: {active_count} burning + {burned_count} burned cells")
                                         
                                     except Exception as obj_error:
                                         worker_logger.warning(f"⚠️ Could not calculate objective for partial results: {obj_error}")
                                         partial_objective = ObjectiveResult(
                                             value=0.0,
                                             components={},
                                             is_valid=False,
                                             error_message=f"Partial results available but objective calculation failed: {obj_error}"
                                         )
                                 else:
                                     partial_objective = ObjectiveResult(
                                         value=0.0,
                                         components={},
                                         is_valid=False,
                                         error_message=f"Simulation timed out after {timeout_seconds} seconds - partial results available"
                                     )
                             else:
                                 partial_objective = ObjectiveResult(
                                     value=0.0,
                                     components={},
                                     is_valid=False,
                                     error_message=f"Simulation timed out after {timeout_seconds} seconds - no partial results available"
                                 )
                         except Exception as partial_error:
                             worker_logger.warning(f"⚠️ Error getting partial results: {partial_error}")
                             partial_objective = ObjectiveResult(
                                 value=0.0,
                                 components={},
                                 is_valid=False,
                                 error_message=f"Simulation timed out after {timeout_seconds} seconds - error getting partial results: {partial_error}"
                             )
                     else:
                         partial_objective = ObjectiveResult(
                             value=0.0,
                             components={},
                             is_valid=False,
                             error_message=f"Simulation timed out after {timeout_seconds} seconds - no engine available"
                         )
                     
                     worker_logger.warning(f"⏰ Returning partial results after {timeout_seconds} second timeout")
                     return {
                         'parameter_values': parameter_values,
                         'objective_result': partial_objective,
                         'simulation_stats': partial_stats,
                         'evaluation_time': time.time(),
                         'vertical_fire_spread': None
                     }
                if simulation_error:
                    worker_logger.error(f"❌ Simulation failed: {simulation_error}")
                    return {
                        'parameter_values': parameter_values,
                        'objective_result': ObjectiveResult(
                            value=0.0,
                            components={},
                            is_valid=False,
                            error_message=f"Simulation failed: {simulation_error}"
                        ),
                        'simulation_stats': {},
                        'evaluation_time': time.time()
                    }
                
                if simulation_result is None:
                    worker_logger.error("❌ Simulation result is None")
                    return {
                        'parameter_values': parameter_values,
                        'objective_result': ObjectiveResult(
                            value=0.0,
                            components={},
                            is_valid=False,
                            error_message="Simulation result is None"
                        ),
                        'simulation_stats': {},
                        'evaluation_time': time.time()
                    }
                
                # Log simulation results for debugging
                stats = simulation_result.get('stats', {})
                burned_cells = stats.get('total_burned_cells', 0)
                burning_cells = stats.get('final_active_cells', 0)  # Add this line
                steps_completed = stats.get('steps', 0)
                max_steps = config_dict.get('max_steps', 'N/A')
                
                print(f"🔥 Simulation completed: {burning_cells} burning + {burned_cells} burned = {burning_cells + burned_cells} total cells, ended at step {steps_completed}/{max_steps}")
                
        # Calculate objective value
                objective_function = get_objective_function_by_name(objective_function_name)
                
                # CRITICAL DEBUG: Check target data and simulation result format
                worker_logger.debug(f"🔍 DEBUG: target_data type: {type(target_data)}")
                worker_logger.debug(f"🔍 DEBUG: target_data keys: {list(target_data.keys()) if target_data else 'None'}")
                worker_logger.debug(f"🔍 DEBUG: simulation_result type: {type(simulation_result)}")
                
                # CRITICAL FIX: Ensure target data has correct format
                if target_data is None:
                    worker_logger.error("❌ target_data is None - objective evaluation will fail")
                    objective_result = ObjectiveResult(
                        value=999.0,
                        components={},
                        is_valid=False,
                        error_message="Target data is None"
                    )
                elif 'fire_perimeter' not in target_data and 'fire_perimeter_dense' not in target_data and 'target_fire_perimeter' not in target_data:
                    worker_logger.error(f"❌ No fire perimeter data found in target_data keys: {list(target_data.keys())}")
                    objective_result = ObjectiveResult(
                        value=999.0,
                        components={},
                        is_valid=False,
                        error_message="Missing fire perimeter data in target_data"
                    )
                else:
                    # CRITICAL FIX: Ensure simulation result has correct format for objective function
                    if not isinstance(simulation_result, dict):
                        # Convert to dict format expected by objective function
                        simulation_result = {'forest_model': forest_model}
                        worker_logger.debug("🔧 Converted simulation_result to dict format with forest_model")
                    
                    objective_result = objective_function.evaluate(simulation_result, target_data)
                    worker_logger.debug(f"✅ Objective evaluation: value={objective_result.value}, valid={objective_result.is_valid}")
                
                # Extract values from ObjectiveResult object
                objective_value = objective_result.value if objective_result.is_valid else 0.0
                objective_components = objective_result.components if objective_result.is_valid else {}
                
                if not objective_result.is_valid:
                    worker_logger.error(f"❌ Objective evaluation failed: {objective_result.error_message}")
                else:
                    worker_logger.debug(f"✅ Valid objective: {objective_value}")
                
                # Extract vertical fire spread statistics
                vertical_spread_stats = None
                if forest_model and hasattr(forest_model, 'spread_stats') and forest_model.spread_stats:
                    stats = forest_model.spread_stats
                    
                    # Calculate key metrics
                    total_spread = sum(stats.values())
                    vertical_spread = stats.get('vertical_spread', 0)
                    horizontal_spread = stats.get('horizontal_spread', 0)
                    ember_spread = stats.get('ember_spread', 0)
                    total_ignitions = stats.get('total_ignitions', 0)
                    
                    # Calculate percentages
                    vertical_percentage = (vertical_spread / total_spread * 100) if total_spread > 0 else 0
                    horizontal_percentage = (horizontal_spread / total_spread * 100) if total_spread > 0 else 0
                    ember_percentage = (ember_spread / total_spread * 100) if total_spread > 0 else 0
                    
                    # Calculate efficiency
                    vertical_efficiency = (vertical_spread / total_ignitions * 100) if total_ignitions > 0 else 0
                    
                    # Calculate ratio
                    vertical_horizontal_ratio = vertical_spread / horizontal_spread if horizontal_spread > 0 else 0
                    
                    # Classify vertical spread behavior
                    if vertical_horizontal_ratio > 0.1:
                        spread_classification = "High vertical spread - strong convection"
                    elif vertical_horizontal_ratio > 0.05:
                        spread_classification = "Moderate vertical spread - normal behavior"
                    else:
                        spread_classification = "Low vertical spread - primarily horizontal"
                    
                    vertical_spread_stats = {
                        'total_spread_events': total_spread,
                        'vertical_spread_events': vertical_spread,
                        'vertical_spread_percentage': vertical_percentage,
                        'horizontal_spread_events': horizontal_spread,
                        'horizontal_spread_percentage': horizontal_percentage,
                        'ember_spread_events': ember_spread,
                        'ember_spread_percentage': ember_percentage,
                        'total_ignitions': total_ignitions,
                        'vertical_efficiency': vertical_efficiency,
                        'vertical_horizontal_ratio': vertical_horizontal_ratio,
                        'spread_classification': spread_classification
                    }
                
                worker_result = {
                    'parameter_values': parameter_values,
                    'objective_result': objective_result,
                    'simulation_stats': simulation_result.get('stats', {}),
                    'vertical_fire_spread': vertical_spread_stats,
                    'evaluation_time': time.time()
                }
                
                # Validate that we have a proper result before returning
                if worker_result is None:
                    worker_logger.error("❌ CRITICAL: worker_result is None - this should never happen")
                    worker_result = {
                        'parameter_values': parameter_values,
                        'objective_result': ObjectiveResult(
                            value=0.0,
                            components={},
                            is_valid=False,
                            error_message="Worker result is None - critical error"
                        ),
                        'simulation_stats': {},
                        'vertical_fire_spread': None,
                        'evaluation_time': time.time()
                    }
                
                worker_logger.info(f"✅ Worker completed successfully - returning result with objective value: {objective_result.value}")
                return worker_result
                
            except Exception as e:
                worker_logger.error(f"🔍 DEBUG: Simulation failed with error: {type(e)} = {e}")
                worker_logger.error("🔍 DEBUG: Error occurred in simulation run")
                worker_logger.error(f"🔍 DEBUG: parameter_values: {parameter_values}")
                worker_logger.error(f"🔍 DEBUG: config_dict type: {type(config_dict)}")
                
                # CRITICAL FIX: Add specific KeyError 7 and 11 handling
                if isinstance(e, KeyError) and e.args[0] == 7:
                    worker_logger.error("🔍 CRITICAL: KeyError 7 detected - likely fuel type/category mapping issue")
                elif isinstance(e, KeyError) and e.args[0] == 11:
                    worker_logger.error("🔍 CRITICAL: KeyError 11 detected - likely fuel type/category mapping issue")
                    worker_logger.error("🔍 This suggests a fuel type dictionary is missing key 7")
                    worker_logger.error("🔍 Checking for fuel type mappings in forest model...")
                    
                    if forest_model:
                        worker_logger.error(f"🔍 Fuel load shape: {forest_model.fuel_load.shape if hasattr(forest_model, 'fuel_load') else 'No fuel_load'}")
                        worker_logger.error(f"🔍 State shape: {forest_model.state.shape if hasattr(forest_model, 'state') else 'No state'}")
                        worker_logger.error(f"🔍 Fuel-related attributes: {[attr for attr in dir(forest_model) if 'fuel' in attr.lower()]}")
                
                import traceback
                worker_logger.error("🔍 DEBUG: Simulation traceback: " + traceback.format_exc())
                
                worker_error = e
                worker_result = {
                    'parameter_values': parameter_values,
                    'objective_result': ObjectiveResult(
                        value=0.0,
                        components={},
                        is_valid=False,
                        error_message=str(e)
                    ),
                    'simulation_stats': {},
                    'vertical_fire_spread': None,
                    'evaluation_time': time.time()
                }
            
            finally:
                worker_ready.set()
        
        # Start worker execution in a separate thread with timeout
        worker_thread = threading.Thread(target=run_worker_with_timeout)
        worker_thread.daemon = True
        worker_thread.start()
        
        # Calculate worker execution timeout based on grid size
        grid_size = config_dict.get('grid_size', (100, 100))
        if isinstance(grid_size, (tuple, list)) and len(grid_size) == 2:
            total_cells = grid_size[0] * grid_size[1]
            if total_cells > 50_000_000:  # 50M+ cells
                worker_timeout = 5400.0  # 1.5 hours for massive grids
            elif total_cells > 20_000_000:  # 20M+ cells
                worker_timeout = 5400.0  # 1.5 hours for large grids
            elif total_cells > 10_000_000:  # 10M+ cells
                worker_timeout = 5400.0   # 1.5 hours for medium grids
            else:
                worker_timeout = 5400.0   # 1.5 hours for smaller grids
        else:
            worker_timeout = 5400.0  # Default 1.5 hours
        
        worker_logger.debug(f"⏱️  Setting worker execution timeout to {worker_timeout} seconds for {total_cells:,} cells")
        
        # Wait for worker completion with dynamic timeout
        if not worker_ready.wait(timeout=worker_timeout):
             worker_logger.warning(f"⏰ Worker execution timed out after {worker_timeout} seconds - attempting to recover partial results")
             
             # Try to get partial results if available
             partial_stats = {}
             partial_objective = None
             
             if worker_result is not None:
                 # Worker completed but we didn't get the result in time
                 worker_logger.info("✅ Worker completed but result retrieval timed out - using available result")
                 return worker_result
             elif engine is not None:
                 # Try to get partial results from engine
                 try:
                     if hasattr(engine, 'active_cells') and hasattr(engine, 'burned_cells'):
                         active_count = len(engine.active_cells)
                         burned_count = len(engine.burned_cells)
                         partial_stats = {
                             'total_burned_cells': burned_count,
                             'final_active_cells': active_count,
                             'steps': getattr(engine, 'current_step', 0),
                             'worker_timeout_occurred': True,
                             'partial_results': True
                         }
                         
                         # Try to get current state for objective calculation
                         if hasattr(engine, 'forest_model') and engine.forest_model is not None:
                             try:
                                 current_state = engine.forest_model.get_state()
                                 partial_simulation_result = {
                                     'fire_perimeter': current_state,
                                     'stats': partial_stats,
                                     'partial_results': True
                                 }
                                 
                                 objective_function = get_objective_function_by_name(objective_function_name)
                                 partial_objective = objective_function.evaluate(partial_simulation_result, target_data)
                                 
                                 worker_logger.info(f"✅ Recovered partial results from worker timeout: {active_count} burning + {burned_count} burned cells")
                                 
                             except Exception as obj_error:
                                 worker_logger.warning(f"⚠️ Could not calculate objective for recovered partial results: {obj_error}")
                                 partial_objective = ObjectiveResult(
                                     value=0.0,
                                     components={},
                                     is_valid=False,
                                     error_message=f"Worker timeout - partial results available but objective calculation failed: {obj_error}"
                                 )
                         else:
                             partial_objective = ObjectiveResult(
                                 value=0.0,
                                 components={},
                                 is_valid=False,
                                 error_message=f"Worker execution timed out after {worker_timeout} seconds - partial results available"
                             )
                     else:
                         partial_objective = ObjectiveResult(
                             value=0.0,
                             components={},
                             is_valid=False,
                             error_message=f"Worker execution timed out after {worker_timeout} seconds - no partial results available"
                         )
                 except Exception as partial_error:
                     worker_logger.warning(f"⚠️ Error recovering partial results from worker timeout: {partial_error}")
                     partial_objective = ObjectiveResult(
                         value=0.0,
                         components={},
                         is_valid=False,
                         error_message=f"Worker execution timed out after {worker_timeout} seconds - error recovering partial results: {partial_error}"
                     )
             else:
                 partial_objective = ObjectiveResult(
                     value=0.0,
                     components={},
                     is_valid=False,
                     error_message=f"Worker execution timed out after {worker_timeout} seconds - no engine available for partial results"
                 )
             
             return {
                 'parameter_values': parameter_values,
                 'objective_result': partial_objective,
                 'simulation_stats': partial_stats,
                 'evaluation_time': time.time()
             }
        
        if worker_error:
            worker_logger.error(f"❌ Worker execution failed: {worker_error}")
            return worker_result
        
        if worker_result is None:
            worker_logger.error("❌ Worker result is None - returning error result")
            none_objective = ObjectiveResult(
                value=0.0,
                components={},
                is_valid=False,
                error_message="Worker result is None"
            )
            
            return {
                'parameter_values': parameter_values,
                'objective_result': none_objective,  # ← FIXED!
                'simulation_stats': {},
                'evaluation_time': time.time()
            }
        
        return worker_result
        
    except Exception as e:
        worker_logger.error(f"❌ Critical error in worker function: {e}")
        return {
            'parameter_values': parameter_values,
            'objective_result': ObjectiveResult(
                value=0.0,
                components={},
                is_valid=False,
                error_message=f"Critical error: {str(e)}"
            ),
            'simulation_stats': {},
            'evaluation_time': time.time()
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
        self.max_workers = max_workers or min(4, mp.cpu_count() or 1)  # REDUCED to prevent hanging  # Reduced from 70 to 16
        self.bypass_worker_limit = bypass_worker_limit
        
        # Track if user explicitly specified workers (for respecting user choice)
        self._user_specified_workers = max_workers is not None
        
        # Create parameter space
        self.parameter_space = self._create_parameter_space()
        
        # CRITICAL FIX: Ensure parameter space is not cached/shared between instances
        # Parameter space debug info suppressed
        
        # CRITICAL FIX: Validate parameter space is not empty
        if not self.parameter_space:
            logger.error("❌ CRITICAL ERROR: Parameter space is empty!")
            logger.error(f"   Calibration parameters: {self.config.get_calibration_parameter_names()}")
            logger.error(f"   Parameter bounds keys: {list(self.parameter_bounds.keys())}")
            raise ValueError("Parameter space is empty - cannot proceed with calibration")
        
        # Calculate total combinations
        self.total_combinations = self._calculate_total_combinations()
        
        # CRITICAL FIX: Validate total combinations is correct
        if self.total_combinations == 0:
            logger.error("❌ CRITICAL ERROR: Total combinations is 0!")
            logger.error(f"   Parameter space: {self.parameter_space}")
            raise ValueError("Total combinations is 0 - cannot proceed with calibration")
        
        logger.info(f"✅ Parameter space created successfully: {self.total_combinations} combinations")
        
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
        
        # Parameter space creation debug info suppressed
        
        for param_name in self.config.get_calibration_parameter_names():
            if param_name not in self.parameter_bounds:
                logger.warning(f"No bounds defined for parameter {param_name}, skipping")
                continue
            
            bounds = self.parameter_bounds[param_name]
            
            # Generate grid points for this parameter
            grid_points = bounds.generate_grid_points(self.config.grid_search_points)
            parameter_space[param_name] = grid_points
            
            # Parameter grid points debug info suppressed
        
        # Final parameter space debug info suppressed
        
        # CRITICAL VALIDATION: Ensure parameter space is not empty and has multiple values per parameter
        if not parameter_space:
            logger.error("❌ CRITICAL ERROR: Parameter space is empty!")
            raise ValueError("Parameter space is empty - no parameters to calibrate")
        
        for param_name, values in parameter_space.items():
            if len(values) < 2:
                logger.error(f"❌ CRITICAL ERROR: Parameter {param_name} has only {len(values)} value(s)!")
                logger.error(f"   Values: {values}")
                raise ValueError(f"Parameter {param_name} must have at least 2 values for grid search")
        
        logger.info(f"✅ Parameter space validation passed: {len(parameter_space)} parameters with multiple values each")
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
        
        # Parameter combination generation debug info suppressed
        
        # CRITICAL FIX: Create a fresh list of combinations to avoid iterator reuse issues
        all_combinations = list(itertools.product(*param_value_lists))
        # Raw combinations debug info suppressed
        
        # CRITICAL VALIDATION: Ensure we have the expected number of combinations
        expected_combinations = 1
        for values in param_value_lists:
            expected_combinations *= len(values)
        
        if len(all_combinations) != expected_combinations:
            logger.error(f"❌ CRITICAL ERROR: Expected {expected_combinations} combinations but got {len(all_combinations)}!")
            logger.error(f"   Parameter value lists: {param_value_lists}")
            raise ValueError(f"Combination count mismatch: expected {expected_combinations}, got {len(all_combinations)}")
        
        logger.info(f"✅ Combination count validation passed: {len(all_combinations)} combinations")
        
        combination_count = 0
        first_combinations = []  # Store first few combinations for validation
        
        for combination in all_combinations:
            # CRITICAL FIX: Ensure we always yield a dictionary
            param_dict = dict(zip(param_names, combination))
            # Validate that we have a proper dictionary
            if not isinstance(param_dict, dict):
                logger.error(f"Generated parameter combination is not a dictionary: {type(param_dict)} = {param_dict}")
                # Fallback to empty dictionary
                param_dict = {}
            
            combination_count += 1
            if combination_count <= 3:  # Log first 3 combinations
                # Individual combination debug info suppressed
                first_combinations.append(param_dict)
            
            yield param_dict
        
        # CRITICAL VALIDATION: Ensure first few combinations are different
        if len(first_combinations) >= 2:
            if first_combinations[0] == first_combinations[1]:
                logger.error(f"❌ CRITICAL ERROR: First two combinations are identical!")
                logger.error(f"   First: {first_combinations[0]}")
                logger.error(f"   Second: {first_combinations[1]}")
                logger.error(f"   Parameter space: {self.parameter_space}")
                raise ValueError("First two parameter combinations are identical - parameter space is wrong")
            else:
                logger.info(f"✅ First two combinations are different: {first_combinations[0]} vs {first_combinations[1]}")
        
        # Total combinations debug info suppressed
    
    def _evaluate_single_combination(self, parameter_values: Dict[str, float],
                                   target_data: Optional[Dict[str, Any]] = None) -> GridSearchResult:
        """
        Evaluate a single parameter combination with optimized serialization and performance optimizations.
        """
        start_time = time.time()
        
        try:
            import gc
            gc.disable()  # Disable GC during critical evaluation
            
            # Create config variant with parameters
            config = self.config.create_config_variant(parameter_values)
            
            # Try to use optimized components if available
            try:
                from src.core.optimization_factory import (
                    create_optimized_fire_simulation_engine,
                    create_optimized_forest_model
                )
                
                # Create optimized forest model
                forest_model = create_optimized_forest_model(
                    grid_size=config.grid_size,
                    num_layers=config.num_layers,
                    config=config,
                    force_optimization=True
                )
                
                # Create optimized simulation engine
                engine = create_optimized_fire_simulation_engine(
                    forest_model=forest_model,
                    config=config,
                    force_optimization=True
                )
                
            except ImportError as e:
                # Fallback to standard components - USE SAME MODEL AS VALIDATION
                from src.core.optimized_forest_model import OptimizedMemoryOptimizedForestModel
                forest_model = OptimizedMemoryOptimizedForestModel(
                    grid_size=config.grid_size,
                    num_layers=config.num_layers,
                    layer_height_meters=config.layer_height,
                    model_resolution=config.model_resolution,
                    initial_fuel_load=config.initial_fuel_load,
                    config=config
                )
                engine = FireSimulationEngine(forest_model=forest_model, config=config)
            except Exception as e:
                # Fallback to standard components - USE SAME MODEL AS VALIDATION
                from src.core.optimized_forest_model import OptimizedMemoryOptimizedForestModel
                forest_model = OptimizedMemoryOptimizedForestModel(
                    grid_size=config.grid_size,
                    num_layers=config.num_layers,
                    layer_height_meters=config.layer_height,
                    model_resolution=config.model_resolution,
                    initial_fuel_load=config.initial_fuel_load,
                    config=config
                )
                engine = FireSimulationEngine(forest_model=forest_model, config=config)
            
            # Set ignition points BEFORE running simulation (same as validation script)
            try:
                # Use ignition points from config (same as validation script)
                if hasattr(config, 'ignition_points') and config.ignition_points:
                    for ignition_point in config.ignition_points:
                        forest_model.set_ignition(ignition_point[0], ignition_point[1], ignition_point[2])
                        logger.debug(f"✅ Ignition point set from config: ({ignition_point[0]}, {ignition_point[1]}, {ignition_point[2]})")
                        
                        # Also set it in the simulation engine's active cells
                        if hasattr(engine, 'active_cells'):
                            engine.active_cells.add((ignition_point[0], ignition_point[1], ignition_point[2]))
                            logger.debug(f"✅ Added ignition point to engine active cells: {ignition_point}")
                else:
                    # Fallback to default ignition point
                    default_x, default_y = 395, 377  # Center of 609×609 grid
                    forest_model.set_ignition(default_x, default_y, 0)
                    logger.debug(f"✅ Default ignition point set: ({default_x}, {default_y}, 0)")
                    if hasattr(engine, 'active_cells'):
                        engine.active_cells.add((default_x, default_y, 0))
                
            except Exception as ignition_error:
                logger.warning(f"⚠️ Failed to set ignition point: {ignition_error}")
            
            # Run simulation
            simulation_result = engine.run_simulation()
            
            # Get target data from shared memory if not provided
            if target_data is None:
                target_data = get_shared_target_data()
                if target_data is None:
                    logger.warning("No target data available - using synthetic target")
            
            # Calculate objective value
            objective_result = self.objective_function.evaluate(simulation_result, target_data)
            
            evaluation_time = time.time() - start_time
            
            # Extract vertical fire spread statistics
            vertical_spread_stats = None
            if forest_model and hasattr(forest_model, 'spread_stats') and forest_model.spread_stats:
                stats = forest_model.spread_stats
                
                # Calculate key metrics
                total_spread = sum(stats.values())
                vertical_spread = stats.get('vertical_spread', 0)
                horizontal_spread = stats.get('horizontal_spread', 0)
                ember_spread = stats.get('ember_spread', 0)
                total_ignitions = stats.get('total_ignitions', 0)
                
                # Calculate percentages
                vertical_percentage = (vertical_spread / total_spread * 100) if total_spread > 0 else 0
                horizontal_percentage = (horizontal_spread / total_spread * 100) if total_spread > 0 else 0
                ember_percentage = (ember_spread / total_spread * 100) if total_spread > 0 else 0
                
                # Calculate efficiency
                vertical_efficiency = (vertical_spread / total_ignitions * 100) if total_ignitions > 0 else 0
                
                # Calculate ratio
                vertical_horizontal_ratio = vertical_spread / horizontal_spread if horizontal_spread > 0 else 0
                
                # Classify vertical spread behavior
                if vertical_horizontal_ratio > 0.1:
                    spread_classification = "High vertical spread - strong convection"
                elif vertical_horizontal_ratio > 0.05:
                    spread_classification = "Moderate vertical spread - normal behavior"
                else:
                    spread_classification = "Low vertical spread - primarily horizontal"
                
                vertical_spread_stats = {
                    'total_spread_events': total_spread,
                    'vertical_spread_events': vertical_spread,
                    'vertical_spread_percentage': vertical_percentage,
                    'horizontal_spread_events': horizontal_spread,
                    'horizontal_spread_percentage': horizontal_percentage,
                    'ember_spread_events': ember_spread,
                    'ember_spread_percentage': ember_percentage,
                    'total_ignitions': total_ignitions,
                    'vertical_efficiency': vertical_efficiency,
                    'vertical_horizontal_ratio': vertical_horizontal_ratio,
                    'spread_classification': spread_classification
                }
            
            # Create result using composition
            result = GridSearchResult(
                parameter_values=parameter_values.copy(),
                objective_result=objective_result,  # Use the ObjectiveResult directly
                simulation_stats=simulation_result.get('stats', {}),
                evaluation_time=evaluation_time,
                vertical_fire_spread=vertical_spread_stats
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
            
            # Create error result using composition
            error_objective = ObjectiveResult(
                value=0.0,
                components={},
                is_valid=False,
                error_message=str(e)
            )
            return GridSearchResult(
                parameter_values=parameter_values.copy(),
                objective_result=error_objective,
                simulation_stats={},
                evaluation_time=evaluation_time,
                vertical_fire_spread=None
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
                
                # CRITICAL FIX: Handle sparse arrays properly
                if 'fire_perimeter' in target_data:
                    fire_perimeter = target_data['fire_perimeter']
                    try:
                        from scipy.sparse import issparse
                        if issparse(fire_perimeter):
                            # For sparse arrays, use getnnz() to get number of non-zero elements
                            size_info = f"{fire_perimeter.getnnz()} non-zero cells (sparse)"
                        else:
                            # For dense arrays, use len() or shape
                            if hasattr(fire_perimeter, 'shape'):
                                size_info = f"{fire_perimeter.shape[0] * fire_perimeter.shape[1]} cells (dense)"
                            else:
                                size_info = f"{len(fire_perimeter)} cells"
                    except ImportError:
                        # Fallback if scipy is not available
                        if hasattr(fire_perimeter, 'shape'):
                            size_info = f"{fire_perimeter.shape[0] * fire_perimeter.shape[1]} cells"
                        else:
                            size_info = f"{len(fire_perimeter)} cells"
                else:
                    size_info = "0 cells"
                
                logger.debug(f"📦 Set shared target data for multiprocessing (size: {size_info})")
            
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
                    logger.debug(f"🎛️  CLI Override: Respecting user-specified {self.max_workers} workers")
                    if available_memory_gb < 32 and total_model_cells > 10_000_000_000:
                        logger.error(f"🚨 CRITICAL: Extremely large grid on very low memory - forcing sequential despite CLI override")
                        should_run_parallel = False
                    else:
                        logger.debug(f"✅ Proceeding with parallel execution as requested")
                else:
                    # Auto-detection mode - use intelligent thresholds
                    if available_memory_gb >= 120:  # High-memory HPC environment
                        # REDUCED: Allow parallel processing for large grids (up to 5B cells)
                        if total_model_cells > 5_000_000_000:
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
                logger.info(f"Best objective value: {best_value:.8f}")
            else:
                logger.info(f"Best objective value: None (no valid results)")
            # Don't duplicate best parameters - they're shown by the calling script
            
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
            
            # Periodic logging (reduced to avoid duplication with progress callback)
            if (i + 1) % max(1, self.total_combinations // 10) == 0:  # Less frequent updates
                progress = (i + 1) / self.total_combinations * 100
                logger.info(f"Progress: {progress:.1f}% ({i + 1}/{self.total_combinations})")
        
        return results
    
    def _run_parallel_calibration(self, 
                                target_data: Optional[Dict[str, Any]],
                                progress_callback: Optional[callable],
                                results: GridSearchResults) -> GridSearchResults:
        """
        Run parallel calibration with optimized serialization.
        """
        logger.info(f"🚀 Starting parallel calibration with {self.total_combinations} combinations using {self.max_workers} workers")
        
        # Add progress tracking
        completed_combinations = 0
        total_combinations = self.total_combinations
        progress_interval = max(1, total_combinations // 20)  # Progress update every 5%
        
        # Calculate optimal worker count
        if not self.bypass_worker_limit:
            optimal_workers = self._calculate_hpc_optimal_workers()
            
            # CRITICAL FIX: Adjust workers for massive grids based on system capacity
            grid_size = self._get_grid_size_from_config(self.config)
            if isinstance(grid_size, (tuple, list)) and len(grid_size) == 2:
                total_cells = grid_size[0] * grid_size[1]
                if total_cells > 10_000_000:  # 10M+ cells
                    logger.warning(f"🚨 MASSIVE GRID: {total_cells:,} cells - optimizing workers for performance")
                    
                    # Scale workers based on grid size and available memory
                    try:
                        import psutil
                        memory_gb = psutil.virtual_memory().total / (1024**3)
                        
                        if memory_gb >= 200:  # High-memory HPC (200GB+)
                            max_workers_for_grid = 16  # Reduced from 64 to 16
                        elif memory_gb >= 100:  # Medium-high memory HPC (100-200GB)
                            max_workers_for_grid = 12  # Reduced from 48 to 12
                        elif memory_gb >= 60:   # Medium memory HPC (60-100GB)
                            max_workers_for_grid = 8   # Reduced from 32 to 8
                        else:  # Lower memory systems
                            max_workers_for_grid = 4   # Reduced from 16 to 4
                        
                        # RESPECT USER CHOICE: Only adjust if user didn't explicitly specify workers
                        if hasattr(self, '_user_specified_workers') and self._user_specified_workers:
                            logger.info(f"🎛️  RESPECTING USER CHOICE: Keeping {self.max_workers} workers (user-specified)")
                            optimal_workers = self.max_workers
                        else:
                            optimal_workers = min(optimal_workers, max_workers_for_grid)
                            logger.warning(f"🚨 Adjusted workers to {optimal_workers} for massive grid (max allowed: {max_workers_for_grid} for {memory_gb:.1f}GB system)")
                    except Exception as e:
                        # Fallback if psutil fails
                        optimal_workers = min(optimal_workers, 16)  # Reduced from 64 to 16
                        logger.warning(f"🚨 Using conservative worker limit: {optimal_workers} (psutil error: {e})")
            
            # CRITICAL FIX: Only apply HPC optimization if user didn't explicitly specify workers
            if self.max_workers > optimal_workers and not self._user_specified_workers:
                logger.warning(f"🧠 HPC OPTIMIZATION: Reducing workers from {self.max_workers} to {optimal_workers} for memory bandwidth")
                self.max_workers = optimal_workers
            elif self._user_specified_workers:
                logger.info(f"🎛️  RESPECTING USER CHOICE: Keeping {self.max_workers} workers (user-specified, bypassing HPC optimization)")
        
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
        
        # Convert generator to list for parallel processing
        # CRITICAL FIX: Convert generator to list before parallel processing to avoid pickling errors
        combinations_list = list(self._generate_parameter_combinations())
        logger.info(f"Generated {len(combinations_list)} parameter combinations")
        
        # CRITICAL FIX: Move pre-optimization AFTER generating combinations list
        # This prevents the generator from being consumed before the main processing
        # self._pre_optimize_for_workers_from_list(combinations_list[:10])  # Skip pre-optimization to fix hang
        
        # CRITICAL FIX: Validate parameter space BEFORE starting workers
        if len(combinations_list) == 0:
            logger.error("❌ CRITICAL ERROR: No parameter combinations generated!")
            logger.error(f"   Parameter space: {self.parameter_space}")
            logger.error(f"   Parameter bounds: {self.parameter_bounds}")
            raise ValueError("No parameter combinations generated - cannot proceed")
        
        if len(combinations_list) == 1:
            logger.error("❌ CRITICAL ERROR: Only one parameter combination generated!")
            logger.error(f"   Combination: {combinations_list[0]}")
            logger.error(f"   Parameter space: {self.parameter_space}")
            raise ValueError("Only one parameter combination generated - grid search will fail")
        
        # CRITICAL FIX: Check first few combinations are different
        first_combo = combinations_list[0]
        for i, combo in enumerate(combinations_list[1:4]):  # Check first 4 combinations
            if combo == first_combo:
                logger.error(f"❌ CRITICAL ERROR: Combination {i+1} is identical to first combination!")
                logger.error(f"   First: {first_combo}")
                logger.error(f"   {i+1}th: {combo}")
                logger.error(f"   Parameter space: {self.parameter_space}")
                raise ValueError(f"Combination {i+1} is identical to first - parameter space is wrong")
        
        # CRITICAL DEBUG: Log first few combinations to verify uniqueness
        logger.info(f"✅ Parameter validation passed: {len(combinations_list)} unique combinations")
        logger.info(f"✅ First 3 combinations are different: {[combinations_list[i] for i in range(min(3, len(combinations_list)))]}")
        
        # CRITICAL DEBUG: Validate combinations_list
        logger.debug(f"combinations_list type: {type(combinations_list)}")
        logger.debug(f"combinations_list length: {len(combinations_list)}")
        if len(combinations_list) > 0:
            logger.debug(f"First combination type: {type(combinations_list[0])}")
            logger.debug(f"First combination value: {combinations_list[0]}")
        
        # Prepare configuration and objective function name for workers
        # CRITICAL FIX: Ensure config_dict is properly created
        try:
            logger.info(f"🔍 Creating base_config_variant...")
            base_config_variant = self.config.create_config_variant({})
            logger.info(f"🔍 base_config_variant type: {type(base_config_variant)}")
            logger.info(f"🔍 base_config_variant: {base_config_variant}")
            
            # CRITICAL FIX: Handle ModelConfig object returned by create_config_variant
            if hasattr(base_config_variant, '__dict__'):
                # If it's a ModelConfig object, use asdict() to convert to dictionary
                try:
                    from dataclasses import asdict
                    config_dict = asdict(base_config_variant)
                    logger.info(f"✅ Converted ModelConfig to dictionary using asdict()")
                    logger.info(f"✅ ModelConfig grid_size: {base_config_variant.grid_size}")
                except Exception as asdict_error:
                    logger.warning(f"asdict() failed, using __dict__: {asdict_error}")
                    config_dict = base_config_variant.__dict__
            elif isinstance(base_config_variant, dict):
                config_dict = base_config_variant
            elif isinstance(base_config_variant, (list, tuple)) and len(base_config_variant) > 0:
                # If it's a list/tuple, take the first item if it's a dict
                if isinstance(base_config_variant[0], dict):
                    config_dict = base_config_variant[0]
                    logger.warning(f"Using first item from config_variant list/tuple")
                else:
                    logger.error(f"config_variant is list/tuple but first item is not a dict: {type(base_config_variant[0])}")
                    config_dict = {}
            else:
                logger.error(f"Unexpected config_variant type: {type(base_config_variant)} = {base_config_variant}")
                config_dict = {}
            
            # CRITICAL FIX: Ensure config_dict is actually a dictionary
            if not isinstance(config_dict, dict):
                logger.error(f"config_dict is still not a dictionary after processing: {type(config_dict)} = {config_dict}")
                config_dict = {}
            
            logger.debug(f"config_dict type: {type(config_dict)}")
            logger.debug(f"config_dict keys: {list(config_dict.keys()) if isinstance(config_dict, dict) else 'not a dict'}")
            
            # CRITICAL FIX: Ensure essential keys are present
            essential_keys = ['grid_size', 'num_layers', 'max_steps', 'simulation_type']
            missing_keys = [key for key in essential_keys if key not in config_dict]
            if missing_keys:
                logger.warning(f"Missing essential keys in config_dict: {missing_keys}")
                # Add default values for missing keys
                defaults = {
                    'grid_size': (100, 100),
                    'num_layers': 10,
                    'max_steps': 100,
                    'simulation_type': 'memory_optimized'
                }
                for key in missing_keys:
                    if key in defaults:
                        config_dict[key] = defaults[key]
                        logger.debug(f"Added default value for {key}: {defaults[key]}")
            
            # CRITICAL FIX: Add timeout from calibration config to config_dict
            if hasattr(self.config, 'simulation_timeout_minutes'):
                config_dict['simulation_timeout_minutes'] = self.config.simulation_timeout_minutes
                logger.debug(f"Added simulation_timeout_minutes to config_dict: {self.config.simulation_timeout_minutes} minutes")
            else:
                logger.warning("No simulation_timeout_minutes found in calibration config, using grid-size based timeout")
            
            # 🚨 CRITICAL FIX: Add ignition_points to config_dict for workers
            if hasattr(self.config, 'base_config') and hasattr(self.config.base_config, 'ignition_points') and self.config.base_config.ignition_points:
                config_dict['ignition_points'] = self.config.base_config.ignition_points
                logger.info(f"✅ Added ignition_points from base_config to config_dict: {self.config.base_config.ignition_points}")
            elif 'ignition_points' not in config_dict:
                # Ensure ignition_points are ALWAYS present
                config_dict['ignition_points'] = [(395, 377, 0)]  # Default Tenerife ignition
                logger.warning(f"⚠️  No ignition_points found in config - added default: {config_dict['ignition_points']}")
            else:
                logger.info(f"✅ ignition_points already in config_dict: {config_dict['ignition_points']}")
            
            # CRITICAL FIX: Add shared terrain info to config_dict for worker processes
            if hasattr(self.config, 'shared_terrain_info') and self.config.shared_terrain_info:
                config_dict['shared_terrain_info'] = self.config.shared_terrain_info
                logger.info(f"✅ Added shared terrain info to config_dict for {self.max_workers} workers")
            elif hasattr(self.config, 'base_config') and hasattr(self.config.base_config, 'shared_terrain_info') and self.config.base_config.shared_terrain_info:
                config_dict['shared_terrain_info'] = self.config.base_config.shared_terrain_info
                logger.info(f"✅ Added shared terrain info from base_config to config_dict for {self.max_workers} workers")
            else:
                logger.warning("⚠️  No shared terrain info found - workers will load terrain individually!")
            
        except Exception as e:
            logger.error(f"Error creating config_dict: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Create a minimal fallback config_dict
            config_dict = {
                'grid_size': (609, 609),  # 🚨 FIX: Use correct Tenerife grid size
                'num_layers': 20,         # 🚨 FIX: Use correct layer count
                'max_steps': 100,
                'simulation_type': 'memory_optimized',
                'spread_probability': 0.8,
                'fuel_consumption_rate': 0.01,
                'ignition_threshold': 0.1,
                'stop_when_fire_extinguished': False,
                'simulation_timeout_minutes': 60.0,  # Default 60 minutes
                
                # 🚨 CRITICAL FIX: Add ignition_points to fallback config
                'ignition_points': [(395, 377, 0)],  # Center of 609×609 grid (Arafo highlands)
                
                # Add missing required parameters
                'ember_probability': 0.3,
                'ember_ignition': 0.3,
                'slope_influence': 0.3,
                'wind_influence_on_spread': 0.5,
                'min_fuel_value': 0.02,
                'fuel_moisture_baseline': 0.3,
                'wind_speed': 5.0,
                'wind_direction': 0.0,
                'temperature': 25.0,
                'humidity': 30.0,
                'reference_wind_speed': 10.0,
                'terrain_effect_strength': 0.6,
                'barranco_threshold': 30.0,
                'barranco_amplification': 2.0,
                'barranco_direction_weight': 0.8,
                'min_depression_depth': 5.0,
                'min_depression_area': 4,
                'ember_distance': 5,
                'ember_height_factor': 0.2,
                'ember_rise': 2,
                'ember_wind_factor': 0.4,
                'memory_optimization_level': 0,
                'use_disk_storage': False,
                'use_sparse_storage': True,
                'disk_storage_dir': "temp_simulation_states",
                'bytes_per_cell': 10,
                'tile_size': 200,
                'chunk_size': 1000,
                'history_keyframe_interval': 10,
                'engine_logging_interval': 100,
                'crs': "EPSG:32628",
                'extinction_coefficient': 0.5,
                'pad_bin_size': 2.0,
                'exclude_ground_layer': True,
                'use_lidar': False,
                'auto_size_from_lidar': False,
                'max_vegetation_height_m': 50.0,
                'use_tiling': False,
                'use_parallel': True,
                'tile_overlap_ratio': 0.1,
                'fuel_load_method': "random",
                'save_visualizations': True
            }
            logger.debug(f"Using fallback config_dict with {len(config_dict)} keys")
        
        objective_function_name = self.objective_function.__class__.__name__
        
        # EMERGENCY FIX: Add timeout for ProcessPoolExecutor initialization
        import threading
        import time
        
        executor = None
        executor_ready = threading.Event()
        executor_error = None
        
        def create_executor_with_timeout():
            nonlocal executor, executor_error
            try:
                logger.info(f"🚀 Creating ProcessPoolExecutor with {self.max_workers} workers...")
                # CRITICAL FIX: Force exact user-specified worker count
                if self._user_specified_workers:
                    logger.info(f'  FORCING USER-SPECIFIED WORKER COUNT: {self.max_workers}')
                    actual_workers = self.max_workers
                else:
                    actual_workers = self.max_workers
                executor = ProcessPoolExecutor(max_workers=actual_workers)
                logger.info(f"✅ ProcessPoolExecutor created successfully")
                executor_ready.set()
            except Exception as e:
                logger.error(f"❌ Failed to create ProcessPoolExecutor: {e}")
                executor_error = e
                executor_ready.set()
        
        # Start executor creation in a separate thread with timeout
        executor_thread = threading.Thread(target=create_executor_with_timeout)
        executor_thread.daemon = True
        executor_thread.start()
        
        # Wait for executor creation with timeout (30 seconds) - REDUCED
        if not executor_ready.wait(timeout=30.0):
            logger.error("❌ ProcessPoolExecutor creation timed out after 30 seconds")
            logger.error("🚨 EMERGENCY: Falling back to sequential execution")
            return self._run_sequential_calibration(target_data, progress_callback, results)
        
        if executor_error:
            logger.error(f"❌ ProcessPoolExecutor creation failed: {executor_error}")
            logger.error("🚨 EMERGENCY: Falling back to sequential execution")
            return self._run_sequential_calibration(target_data, progress_callback, results)
        
        if executor is None:
            logger.error("❌ ProcessPoolExecutor is None after creation")
            logger.error("🚨 EMERGENCY: Falling back to sequential execution")
            return self._run_sequential_calibration(target_data, progress_callback, results)
        
        try:
            with executor:
                # CRITICAL: Check for workers per simulation configuration
                workers_per_sim = getattr(self.config, 'workers_per_simulation', 1)
                if workers_per_sim > 1:
                    logger.info(f"🔧 Multi-worker mode: {workers_per_sim} workers per simulation")
                    # Adjust batch size for multi-worker simulations
                    batch_size = max(1, min(5, self.max_workers // workers_per_sim))
                else:
                    # Submit jobs in batches to prevent resource contention
                    batch_size = min(2, self.max_workers)  # REDUCED to prevent hanging
                all_futures = []
                
                # CRITICAL FIX: Assign unique worker IDs and ensure each worker gets different parameter combinations
                worker_counter = 0
                logger.info(f"🎯 Starting grid search with {len(combinations_list)} parameter combinations")
                logger.info(f"📊 Parameter space: {list(self.parameter_space.keys())}")
                
                # CRITICAL FIX: Validate combinations are different and unique
                if len(combinations_list) > 1:
                    # Check first few combinations for uniqueness
                    unique_combinations = set()
                    duplicate_found = False
                    
                    for i, combo in enumerate(combinations_list[:10]):  # Check first 10
                        combo_tuple = tuple(sorted(combo.items()))  # Convert to tuple for hashing
                        if combo_tuple in unique_combinations:
                            logger.error(f"❌ CRITICAL ERROR: Duplicate combination found at index {i}!")
                            logger.error(f"   Duplicate: {combo}")
                            logger.error(f"   Parameter space: {self.parameter_space}")
                            logger.error(f"   Total combinations: {self.total_combinations}")
                            duplicate_found = True
                            break
                        unique_combinations.add(combo_tuple)
                    
                    if duplicate_found:
                        raise ValueError("Duplicate parameter combinations found - grid search will fail")
                    else:
                        logger.info(f"✅ First 10 combinations are unique")
                        
                    # Also check first two are different (original check)
                    first_combo = combinations_list[0]
                    second_combo = combinations_list[1]
                    if first_combo == second_combo:
                        logger.error("❌ CRITICAL ERROR: First two combinations are identical!")
                        logger.error(f"   First: {first_combo}")
                        logger.error(f"   Second: {second_combo}")
                        logger.error(f"   Parameter space: {self.parameter_space}")
                        logger.error(f"   Total combinations: {self.total_combinations}")
                        raise ValueError("Parameter combinations are identical - grid search will fail")
                    else:
                        logger.info(f"✅ First two combinations are different: {first_combo} vs {second_combo}")
                else:
                    logger.error("❌ CRITICAL ERROR: Only one combination generated!")
                    logger.error(f"   Combinations: {combinations_list}")
                    logger.error(f"   Parameter space: {self.parameter_space}")
                    raise ValueError("Only one parameter combination generated - grid search will fail")
                
                for i in range(0, len(combinations_list), batch_size):
                    batch = combinations_list[i:i + batch_size]
                    logger.info(f"📦 Batch {i//batch_size + 1}: {len(batch)} combinations (workers {worker_counter} to {worker_counter + len(batch) - 1})")
                    
                    # CRITICAL FIX: Ensure each worker gets a unique combination by adding worker_id to the combo
                    batch_futures = {}
                    for batch_idx, combo in enumerate(batch):
                        worker_id = ((worker_counter + batch_idx) % self.max_workers) + 1  # Cycle through actual worker processes
                        
                        # CRITICAL FIX: DO NOT modify the parameter combination - pass it as-is
                        # Each worker should test DIFFERENT parameter combinations for grid search
                        # The worker_id is passed separately to the worker function
                        
                        # Only log first assignment to avoid spam
                        if worker_id < 1:
                            logger.info(f"🔍 DEBUG: Worker {worker_id} gets combination: {combo}")
                        
                        # Add small delay to prevent simultaneous imports
                        if worker_id > 0:
                            time.sleep(0.1)  # 100ms delay between workers
                        future = executor.submit(evaluate_worker_function, combo, target_data, config_dict, objective_function_name, worker_id)
                        batch_futures[future] = combo
                    worker_counter += len(batch)
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
                
                # Process results with progress updates
                completed = 0
                for future in as_completed(all_futures):
                    try:
                        # Get result with timeout - this is where worker results are retrieved
                        result_dict = future.result(timeout=300)  # 5 minute timeout per evaluation
                        
                        # Check if result_dict is None (worker crashed or returned None)
                        if result_dict is None:
                            logger.error("❌ Worker result is None - worker likely crashed or timed out")
                            results.add_timeout()
                            continue
                        
                        # Convert dictionary result to GridSearchResult
                        result = GridSearchResult(**result_dict)
                        results.add_result(result)
                        completed += 1
                        
                        # Progress updates every 2% or every 5 evaluations (more frequent)
                        if completed % progress_interval == 0 or completed % 5 == 0:
                            progress_percent = (completed / total_combinations) * 100
                            logger.info(f"📊 Progress: {progress_percent:.1f}% ({completed}/{total_combinations})")
                        
                        if progress_callback:
                            progress_callback(completed, len(combinations_list), result)
                        
                        # CRITICAL FIX: Periodic memory cleanup to prevent accumulation
                        if completed % 5 == 0:  # Every 5 evaluations
                            import gc
                            collected = gc.collect()
                            if collected > 0:
                                logger.debug(f"🧹 Periodic cleanup freed {collected} objects after {completed} evaluations")
                        
                    except TimeoutError:
                        logger.warning("⏰ Evaluation timed out - partial results may be available")
                        # The worker function now returns partial results instead of timing out completely
                        # So we should still process the result
                        try:
                            # Try to get the result anyway - it might contain partial data
                            result_dict = future.result(timeout=60)  # Short timeout for result retrieval
                            if result_dict is None:
                                logger.error("❌ Worker result is None after timeout - worker crashed")
                                results.add_timeout()
                            else:
                                result = GridSearchResult(**result_dict)
                                results.add_result(result)
                                completed += 1
                                logger.info(f"✅ Retrieved partial results from timed out evaluation")
                        except Exception as timeout_error:
                            logger.error(f"❌ Could not retrieve partial results: {timeout_error}")
                            results.add_timeout()
                    except Exception as e:
                        logger.error(f"❌ Evaluation failed: {e}")
                        results.add_error()
        
        except Exception as e:
            logger.error(f"❌ ProcessPoolExecutor execution failed: {e}")
            logger.error("🚨 EMERGENCY: Falling back to sequential execution")
            return self._run_sequential_calibration(target_data, progress_callback, results)
        
        return results
    
    def _optimize_config_for_worker(self, parameter_values: Dict[str, float], cache_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Unified method to optimize configuration for worker processes.
        
        Args:
            parameter_values: Parameter values for this worker
            cache_key: Optional cache key for storing optimized config
            
        Returns:
            Optimized configuration dictionary ready for worker use
        """
        try:
            # Create config variant with parameter values
            config_variant = self.config.create_config_variant(parameter_values)
            
            # Optimize for serialization
            optimized_config = self.serialization_optimizer.optimize_config_for_serialization(
                config_variant.__dict__ if hasattr(config_variant, '__dict__') else config_variant
            )
            
            # Cache if key provided
            if cache_key:
                self.serialization_optimizer.cache_serialized_object(cache_key, optimized_config)
                logger.debug(f"📦 Cached optimized config: {cache_key}")
            
            return optimized_config
            
        except Exception as e:
            logger.warning(f"⚠️  Config optimization failed: {e}")
            # Fallback to base optimized config
            return self.optimized_config
    
    def _pre_optimize_for_workers_from_list(self, combinations_list: List[Dict[str, float]]):
        """Pre-optimize configurations for worker processes using a list of combinations."""
        try:
            # Cache frequently used configurations using unified method
            common_configs = {}
            
            # Take first 10 combinations from the provided list
            for i, combo in enumerate(combinations_list[:10]):
                config_key = f"config_{hash(str(combo))}"
                
                # Use unified optimization method
                optimized_config = self._optimize_config_for_worker(combo, cache_key=config_key)
                common_configs[config_key] = optimized_config
            
            logger.debug(f"📦 Pre-cached {len(common_configs)} configurations for workers")
                    
        except Exception as e:
            logger.warning(f"⚠️  Pre-optimization failed: {e}")
    
    def _pre_optimize_for_workers(self):
        """Pre-optimize configurations and data for worker processes."""
        # DEPRECATED: This method consumes the generator and causes parameter combination issues
        # Use _pre_optimize_for_workers_from_list instead
        logger.warning("⚠️  _pre_optimize_for_workers is deprecated - use _pre_optimize_for_workers_from_list")
        try:
            # Cache frequently used configurations using unified method
            common_configs = {}
            
            # Take first 10 combinations from generator
            for i, combo in enumerate(self._generate_parameter_combinations()):
                if i >= 10:  # Only cache first 10
                    break
                config_key = f"config_{hash(str(combo))}"
                
                # Use unified optimization method
                optimized_config = self._optimize_config_for_worker(combo, cache_key=config_key)
                common_configs[config_key] = optimized_config
            
            logger.debug(f"📦 Pre-cached {len(common_configs)} configurations for workers")
                    
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
            optimal_workers = min(optimal_workers, 16)  # Reduced from 64 to 16
            
            logger.debug(f"🧠 HPC worker calculation: memory={memory_based_workers}, cpu={cpu_based_workers}, numa={numa_workers} -> optimal={optimal_workers}")
            
            return optimal_workers
            
        except Exception as e:
            logger.warning(f"🧠 Could not calculate HPC optimal workers: {e}")
            return 16  # Conservative default

    def _create_forest_model_with_optimized_config(self, parameter_values: Dict[str, float]):
        """
        Create forest model with optimized configuration and serialization.
        """
        # CRITICAL FIX: Ensure parameter_values is a dictionary before processing
        if not isinstance(parameter_values, dict):
            logger.error(f"parameter_values is not a dictionary: {type(parameter_values)} = {parameter_values}")
            # Convert to dictionary if it's a list/tuple or use empty dict as fallback
            if isinstance(parameter_values, (list, tuple)) and len(parameter_values) > 0:
                # Try to convert list to dict using parameter names
                param_names = list(self.parameter_space.keys())
                if len(parameter_values) == len(param_names):
                    parameter_values = dict(zip(param_names, parameter_values))
                else:
                    parameter_values = {}
            else:
                parameter_values = {}
        
        # Use unified optimization method to get optimized config
        config_variant = self._optimize_config_for_worker(parameter_values)
        
        # Create a copy for modification
        config_variant = copy.deepcopy(config_variant)
        
        # Use unified forest model creation
        from src.core.calibration.calibration_utils import create_unified_forest_model
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
                
                # Use unified forest model creation
                forest_model = create_unified_forest_model(clean_config, model_type=simulation_type)
            else:
                # CRITICAL FIX: Ensure simulation_type is set for ModelConfig objects
                if hasattr(config_variant, 'simulation_type') and config_variant.simulation_type != 'memory_optimized':
                    logger.warning(f"⚠️  Forcing simulation_type to 'memory_optimized' for sparse storage")
                    config_variant.simulation_type = 'memory_optimized'
                
                # Use unified forest model creation
                forest_model = create_unified_forest_model(
                    config_variant, 
                    model_type=getattr(config_variant, 'simulation_type', 'memory_optimized')
                )
            return forest_model
        finally:
            gc.enable()


def create_progress_callback(verbose: bool = True) -> callable:
    """Create a progress callback function for grid search."""
    from src.core.calibration.calibration_utils import create_unified_progress_callback
    return create_unified_progress_callback(verbose=verbose)


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