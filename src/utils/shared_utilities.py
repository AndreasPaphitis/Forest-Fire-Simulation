#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Shared Utilities Module

This module provides common utility functions used across the forest fire simulation codebase.
It centralizes shared functionality to avoid code duplication and ensure consistency.

KEY COMPONENTS:
- Centralized constants used throughout the simulation system (sourced from config_tools.ModelConfig)
- Utility functions for memory calculation, progress tracking, error handling
- Common logging and configuration utilities
- Fallback implementations for critical functionality (minimized)

This module serves as a provider of utility functions, relying on config_tools for centralized configuration.
"""

import os
# import sys # No longer needed for sys.path manipulation
import time
import logging
import traceback
import functools
import numpy as np
from typing import Dict, List, Tuple, Union, Optional, Any, Callable, Iterable

# Minimal dependency section for safe utilities
# This must come before any imports that could cause circular dependencies

def log_once(log_func, message):
    """
    Log a message only once per process.
    Args:
        log_func: The logging function to use (e.g., logger.warning)
        message: The message to log
    """
    if not hasattr(log_once, '_logged_messages'):
        log_once._logged_messages = set()
    if message not in log_once._logged_messages:
        log_func(message)
        log_once._logged_messages.add(message)

# Removed manual sys.path manipulation. Ensure PYTHONPATH is set correctly or handled by entry scripts.

# Standardized logging
from src.utils.logging_utils import get_logger # Assuming this is the correct path
logger = get_logger('shared_utilities')

# Import configuration tools directly - they are now essential
# Ensure these can be imported. If not, it's an environment/setup issue.
try:
    from src.config.config_tools import ModelConfig, get_global_config # get_constant is deprecated
    logger.info("Successfully imported ModelConfig and config tools from src.config.config_tools.")
except ImportError:
    # Fallback for environments where src. is not the base, e.g. running script directly in utils
    try:
        from config.config_tools import ModelConfig, get_global_config
        logger.info("Successfully imported ModelConfig and config tools from config.config_tools (fallback path).")
    except ImportError:
        logger.critical("CRITICAL: ModelConfig and config tools not found in src.config or config. Fallback values will be used.")
        ModelConfig = None # type: ignore
        get_global_config = None # type: ignore


# =======================================================================
# CORE CONSTANTS (Non-configurable, enum-like)
# =======================================================================
# Cell states for the simulation grid (DEPRECATED - Use FrameworkCellState from core_simulation_framework.py)
# NOT_BURNING = 0 # Removed
# BURNING = 1 # Removed
# BURNED_OUT = 2 # Removed

# Other constants previously defined here (DEFAULT_MODEL_RESOLUTION, MIN_FUEL_VALUE, etc.)
# are now sourced from ModelConfig defaults via get_global_config() or get_constant().

# HPC_CONFIG dictionary is removed. Parameters are now part of ModelConfig.

# =======================================================================
# SHARED UTILITY FUNCTIONS
# =======================================================================

def get_project_root(current_file: str = __file__) -> str:
    """
    Returns the absolute path to the project root directory,
    assuming the standard project structure where the file is located at .../src/<module>/<file.py>
    
    Args:
        current_file: File path to calculate from, defaults to this file
        
    Returns:
        Absolute path to the project root directory
    """
    # Correcting assumption: this file is in /src/utils. Project root is one level above /src.
    current_dir_abs = os.path.dirname(os.path.abspath(current_file)) # .../src/utils
    src_dir = os.path.dirname(current_dir_abs) # .../src
    project_root_val = os.path.dirname(src_dir) # .../ (project root)
    return project_root_val

# get_config_value function is removed. Use direct attribute access on ModelConfig instance.

def get_system_memory_mb() -> Optional[float]:
    """
    Attempts to get the total system memory in MB.
    Placeholder implementation. A robust solution would use a library like psutil.
    """
    try:
        # Try to import psutil for a more robust memory check
        import psutil
        total_memory_bytes = psutil.virtual_memory().total
        total_memory_mb = total_memory_bytes / (1024 * 1024)
        logger.info(f"System total memory (via psutil): {total_memory_mb:.2f} MB")
        return total_memory_mb
    except ImportError:
        log_once(logger.warning, "psutil library not found. Cannot accurately determine system memory. "
                               "Falling back to OS-specific commands or a default.")
        # Try OS-specific commands as a fallback (less reliable and portable)
        try:
            if os.name == 'posix': # Linux, macOS
                # Using `free -m` or `sysctl hw.memsize`
                # Example: `free -m` output parsing can be complex, `vm_stat` on macOS
                # This is a very simplified approach for POSIX
                mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
                mem_mb = mem_bytes / (1024**2)
                if mem_mb > 0:
                    logger.info(f"System total memory (via os.sysconf): {mem_mb:.2f} MB")
                    return mem_mb
            elif os.name == 'nt': # Windows
                # Using `wmic OS get TotalVisibleMemorySize`
                # This requires parsing command output, can be slow or fail.
                # import subprocess
                # try:
                #     output = subprocess.check_output(['wmic', 'OS', 'get', 'TotalVisibleMemorySize']).decode()
                #     mem_kb = int(output.split()[-1]) # Last number is memory in KB
                #     mem_mb = mem_kb / 1024
                #     if mem_mb > 0:
                #         logger.info(f"System total memory (via wmic): {mem_mb:.2f} MB")
                #         return mem_mb
                # except Exception as e:
                #     logger.warning(f"Failed to get memory via wmic on Windows: {e}")
                pass # wmic is often too slow or permission issues
        except Exception as e:
            logger.warning(f"Failed to determine system memory via OS commands: {e}")

    default_memory_mb = 4096  # Default to 4GB if undetectable
    log_once(logger.warning, f"get_system_memory_mb: Could not determine system memory. Returning default: {default_memory_mb} MB. "
                           "Consider installing psutil for accurate memory detection.")
    return default_memory_mb

def calculate_memory_requirements(
    grid_size: Union[int, Tuple[int, int]],
    num_layers: int, # Now required
    memory_optimization_level: int, # Now required
    store_full_states: bool, # Now required
    use_differential_history: bool, # Now required
    save_interval: int, # Now required
    bytes_per_cell: int, # Now required
    use_multi_resolution: bool = False, # Now has default for compatibility 
    max_resolution_levels: int = 1 # Now has default for compatibility
) -> Dict[str, float]:
    """
    Calculate memory requirements for a forest fire simulation.
    
    Note: use_multi_resolution and max_resolution_levels params are kept for compatibility
    with existing code but are ignored as multi-resolution functionality is disabled.
    """
    # Parameter validation (basic checks, detailed validation should be in ModelConfig)
    if not all(isinstance(p, bool) for p in [store_full_states, use_differential_history]):
        raise ValueError("Boolean parameters must be bool.")
    if not all(isinstance(p, int) for p in [num_layers, memory_optimization_level, save_interval, bytes_per_cell]):
        raise ValueError("Integer parameters must be int.")
    
    if isinstance(grid_size, int):
        width, height = grid_size, grid_size
    elif isinstance(grid_size, tuple) and len(grid_size) == 2 and all(isinstance(x, int) for x in grid_size):
        width, height = grid_size
    else:
        raise ValueError("grid_size must be an int or a tuple of two ints.")

    if width <= 0 or height <= 0 or num_layers <= 0 or bytes_per_cell <= 0 or save_interval <= 0:
        # More specific checks can be added if needed
        raise ValueError("Numeric parameters must be positive.")
    if not (0 <= memory_optimization_level <= 2):
         raise ValueError("memory_optimization_level must be between 0 and 2.")

    # Ensure memory_optimization_level is within valid range (0-2)
    if memory_optimization_level > 2:
        logger.warning(f"Invalid memory_optimization_level: {memory_optimization_level}. Using maximum supported level (2).")
        memory_optimization_level = 2

    # Calculate base memory requirements
    base_layer_cells = width * height
    total_cells_all_layers = base_layer_cells * num_layers
    base_data_mb = (total_cells_all_layers * bytes_per_cell) / (1024 * 1024)

    # Multi-resolution is no longer supported, so set this to 0
    multi_res_overhead_mb = 0.0
    
    total_grid_data_mb = base_data_mb

    # Calculate history buffer
    history_buffer_mb = 0.0
    if store_full_states:
        num_in_memory_states = 2 
        if use_differential_history:
            history_buffer_mb = (base_data_mb * 0.20) * num_in_memory_states # Example: 20% of full state for diff
        else:
            history_buffer_mb = base_data_mb * num_in_memory_states
    
    # Other overheads
    other_overheads_mb_base = 50.0 # Fixed base overhead
    other_overheads_mb_variable = total_grid_data_mb * 0.1 # Variable part
    other_overheads_mb = other_overheads_mb_base + other_overheads_mb_variable

    # Apply memory optimization level reduction factors
    reduction_factor = 1.0
    if memory_optimization_level == 1:
        reduction_factor = 0.7  # 30% reduction
    elif memory_optimization_level == 2:
        reduction_factor = 0.4  # 60% reduction

    # Apply reduction
    if memory_optimization_level > 0:
        total_grid_data_mb *= reduction_factor
        history_buffer_mb *= reduction_factor
        other_overheads_mb_variable *= reduction_factor
        other_overheads_mb = other_overheads_mb_base + other_overheads_mb_variable

    # Total memory estimate
    total_estimated_mb = total_grid_data_mb + history_buffer_mb + other_overheads_mb

    # Return detailed breakdown
    return {
        "grid_size": (width, height),
        "grid_dimensions": f"{width}x{height}x{num_layers}",
        "total_cells": total_cells_all_layers,
        "base_data_mb": base_data_mb,
        "multi_res_overhead_mb": multi_res_overhead_mb,  # Always 0 now
        "total_grid_data_mb": total_grid_data_mb,
        "history_buffer_mb": history_buffer_mb,
        "other_overheads_mb": other_overheads_mb,
        "memory_optimization_level": memory_optimization_level,
        "reduction_factor": reduction_factor,
        "total_estimated_in_memory_mb": total_estimated_mb,
        "bytes_per_cell": bytes_per_cell
    }

def get_progress_iterator(iterable: Iterable, desc: Optional[str] = None, **kwargs) -> Iterable:
    """
    Get a progress iterator that works with or without tqdm.
    """
    try:
        from tqdm import tqdm
        return tqdm(iterable, desc=desc, **kwargs)
    except ImportError:
        # Fallback to a simpler progress indicator if tqdm is not available
        logger.info("tqdm not found, using basic progress indicator.")
        return _ProgressIndicator(iterable, desc, **kwargs)

class _ProgressIndicator:
    """
    Simple progress indicator for when tqdm is not available.
    """
    def __init__(self, iterable, desc=None, **kwargs):
        self.iterable = iterable
        self.desc = desc or "Processing"
        try:
            self.total = len(iterable)
        except TypeError:
            self.total = None # Cannot determine total length
        self.current_count = 0
        self.start_time = time.time()
        # Print initial message
        if self.total:
            logger.info(f"{self.desc}: Starting {self.total} items.")
        else:
            logger.info(f"{self.desc}: Starting...")

    def __iter__(self):
        for item in self.iterable:
            yield item
            self.current_count += 1
            if self.total and self.current_count % max(1, self.total // 20) == 0: # Update ~20 times
                elapsed = time.time() - self.start_time
                percentage = (self.current_count / self.total) * 100
                logger.info(f"{self.desc}: {self.current_count}/{self.total} ({percentage:.1f}%) completed in {elapsed:.2f}s.")
        
        # Final message
        elapsed = time.time() - self.start_time
        logger.info(f"{self.desc}: Completed all items ({self.current_count}) in {elapsed:.2f}s.")

    def __len__(self):
        return self.total if self.total is not None else 0


def error_handler(func: Optional[Callable] = None, debug: bool = False, exit_on_error: bool = False) -> Callable:
    """
    Decorator to handle exceptions in functions.
    Logs exceptions and optionally re-raises them or exits.
    """
    if func is None: # Decorator called with arguments
        def decorator(f_decorated):
            @functools.wraps(f_decorated)
            def wrapper(*args, **kwargs):
                try:
                    return f_decorated(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Exception in {f_decorated.__name__}: {type(e).__name__} - {str(e)}")
                    if debug:
                        logger.error(traceback.format_exc())
                    if exit_on_error:
                        logger.critical(f"Exiting due to critical error in {f_decorated.__name__}.")
                        sys.exit(1) # Consider a more specific exit code
                    # Depending on desired behavior, could return None or a specific error indicator
                    return None # Or re-raise if not handled by exit_on_error
            return wrapper
        return decorator
    
    # Decorator called without arguments (func is the decorated function)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Exception in {func.__name__}: {type(e).__name__} - {str(e)}")
            if debug: # Assuming debug implies more detailed logging for direct @error_handler use
                logger.error(traceback.format_exc())
            # Default behavior for @error_handler without args: log and return None
            return None
    return wrapper


def optimize_numexpr_threading(max_threads: Optional[int] = None, force_threads: Optional[int] = None) -> Dict[str, Any]:
    """
    Optimize NumExpr threading for maximum performance on multi-core systems.
    
    Args:
        max_threads: Maximum threads to allow (defaults to min(64, cpu_count))
        force_threads: Force specific thread count (overrides max_threads)
        
    Returns:
        Dictionary with applied settings
    """
    try:
        import os
        
        # Get CPU count for optimization
        cpu_count = os.cpu_count() or 8
        
        if force_threads is not None:
            numexpr_threads = force_threads
        elif max_threads is not None:
            numexpr_threads = min(max_threads, cpu_count)
        else:
            # Default to 128 threads for HPC environments
            # Most HPC interactive nodes have 128+ cores
            numexpr_threads = 128
        
        # Set NumExpr environment variables
        os.environ['NUMEXPR_MAX_THREADS'] = str(numexpr_threads)
        os.environ['NUMEXPR_NUM_THREADS'] = str(numexpr_threads)
        
        logger.info(f"NumExpr optimized: max_threads={numexpr_threads} (CPU count: {cpu_count})")
        
        return {
            'numexpr_max_threads': numexpr_threads,
            'numexpr_num_threads': numexpr_threads,
            'cpu_count': cpu_count
        }
        
    except Exception as e:
        logger.warning(f"Failed to optimize NumExpr threading: {e}")
        return {'error': str(e)}


def optimize_gdal_io(cache_size_mb: int = 256, thread_count: Optional[int] = None, use_direct_io: bool = True, 
                     compression_options: Optional[List[str]] = None, hpc_mode: bool = False) -> Optional[Dict[str, Any]]:
    """
    Configure GDAL for optimized I/O operations.
    """
    try:
        from osgeo import gdal
        gdal.UseExceptions()
        gdal.PushErrorHandler('CPLQuietErrorHandler')
        
        # CRITICAL FIX: Handle case where get_global_config is None
        config = get_global_config() if get_global_config is not None else None

        # Use parameters from ModelConfig, allowing overrides via function arguments
        effective_cache_size_mb = cache_size_mb if cache_size_mb is not None else (getattr(config, 'gdal_cache_mb', 256) if config else 256)
        effective_thread_count = thread_count if thread_count is not None else (getattr(config, 'gdal_thread_count', 4) if config else 4)
        effective_compression_options = compression_options # Keep explicit override if passed
        hpc_mode_active = hpc_mode if hpc_mode is not None else (getattr(config, 'hpc_mode_gdal', False) if config else False) # Check explicit then config for hpc_mode_gdal

        if hpc_mode_active: # If HPC mode is active (either by param or config.hpc_mode_gdal)
            # Override with HPC specific values from config if not explicitly passed to function
            effective_cache_size_mb = cache_size_mb if cache_size_mb is not None else (getattr(config, 'hpc_io_block_size', 512) if config else 512) # Assuming hpc_io_block_size is for cache in HPC
            if effective_thread_count is None:
                effective_thread_count = min(16, os.cpu_count() if hasattr(os, 'cpu_count') else 8) # Default HPC threads
            if effective_compression_options is None:
                effective_compression_options = ['COMPRESS=DEFLATE', 'PREDICTOR=2', 'ZLEVEL=1', 'BIGTIFF=YES']
        else: # Non-HPC mode
            if effective_thread_count is None:
                effective_thread_count = min(4, os.cpu_count() if hasattr(os, 'cpu_count') else 2) # Default non-HPC threads
            if effective_compression_options is None:
                effective_compression_options = ['COMPRESS=DEFLATE', 'PREDICTOR=2', 'ZLEVEL=1']
        
        gdal.SetCacheMax(effective_cache_size_mb * 1024 * 1024)
        gdal.SetConfigOption('GDAL_NUM_THREADS', str(effective_thread_count))
        if use_direct_io:
            os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'TRUE'
        else:
            os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'FALSE' # Explicitly set if not using
        
        logger.info(f"GDAL I/O optimized: cache={effective_cache_size_mb}MB, threads={effective_thread_count}, HPC mode: {hpc_mode}, DirectIO: {use_direct_io}")
        
        return {
            'cache_size_mb': effective_cache_size_mb,
            'thread_count': effective_thread_count,
            'use_direct_io': use_direct_io,
            'compression_options': effective_compression_options,
            'hpc_mode': hpc_mode
        }
    except ImportError:
        logger.warning("GDAL not available, I/O optimization skipped.")
        return None
    except Exception as e:
        logger.warning(f"Error optimizing GDAL I/O: {e}")
        return None

def monitor_memory_usage(memory_limit_gb: Optional[float] = None, warning_threshold: float = 0.9) -> Optional[float]:
    """
    Monitor current memory usage of the process.
    """
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_usage_gb = memory_info.rss / (1024**3)
        
        config = get_global_config() # Get the global config instance
        # Use memory_limit_per_node from ModelConfig, allow override via function argument
        limit_gb = memory_limit_gb if memory_limit_gb is not None else (getattr(config, 'hpc_memory_limit_per_node', 64) if config else 64)
        
        if memory_usage_gb > limit_gb * warning_threshold:
            logger.warning(f"Memory usage: {memory_usage_gb:.2f} GB (approaching limit of {limit_gb:.2f} GB at {warning_threshold*100}% threshold).")
        
        return memory_usage_gb
    except ImportError:
        logger.debug("psutil not available, cannot monitor memory usage.")
        return None
    except Exception as e:
        logger.warning(f"Error monitoring memory usage: {e}")
        return None 

def get_forest_model_factory() -> Callable[..., Any]:
    """
    Returns the primary forest model factory from src.core.forest_model.
    Raises ImportError if the factory cannot be imported, indicating a critical setup issue.
    """
    # Try to import the primary factory LOCALLY
    from src.core.forest_model import create_forest_model # Allow ImportError to propagate
    logger.info("Successfully imported primary_factory (create_forest_model) from src.core.forest_model.")
    return create_forest_model
    # Fallback logic removed - if create_forest_model is not found, it's a critical issue. 

def calculate_wind_factor(terrain_elevation, terrain_slope, terrain_aspect, x, y, z):
    """
    Calculate wind factor based on terrain characteristics.
    Works with both dense arrays and sparse matrices.
    
    Args:
        terrain_elevation: Elevation data (dense array or sparse matrix)
        terrain_slope: Slope data (dense array or sparse matrix)  
        terrain_aspect: Aspect data (dense array or sparse matrix)
        x, y, z: Cell coordinates
        
    Returns:
        Wind factor (float) - multiplier for wind effects
    """
    try:
        # Check if terrain data is available
        if (terrain_elevation is None or terrain_slope is None or terrain_aspect is None):
            return 1.0  # Default wind factor when terrain data unavailable
        
        # Handle sparse matrices vs dense arrays
        def get_terrain_value(terrain_data, x, y):
            if terrain_data is None:
                return 0.0
            try:
                # Check if it's a sparse matrix
                if hasattr(terrain_data, 'toarray'):
                    # Sparse matrix - convert to dense for this calculation
                    dense_data = terrain_data.toarray()
                    if x < dense_data.shape[0] and y < dense_data.shape[1]:
                        return dense_data[x, y]
                    else:
                        return 0.0
                else:
                    # Dense array
                    if x < terrain_data.shape[0] and y < terrain_data.shape[1]:
                        return terrain_data[x, y]
                    else:
                        return 0.0
            except:
                return 0.0
        
        # Get terrain values
        elevation = get_terrain_value(terrain_elevation, x, y)
        slope = get_terrain_value(terrain_slope, x, y)
        aspect = get_terrain_value(terrain_aspect, x, y)
        
        # Calculate wind factor based on terrain
        # Higher elevation = stronger winds
        elevation_factor = 1.0 + (elevation / 1000.0) * 0.1  # 10% increase per 1000m
        
        # Steeper slopes = wind channeling
        slope_factor = 1.0 + slope * 0.5  # 50% increase for steep slopes
        
        # Aspect affects wind direction (simplified)
        aspect_factor = 1.0  # Could be enhanced with wind direction
        
        # Combine factors
        wind_factor = elevation_factor * slope_factor * aspect_factor
        
        # Clamp to reasonable range
        wind_factor = max(0.5, min(2.0, wind_factor))
        
        return wind_factor
        
    except Exception as e:
        # Log error and return default
        logger.warning(f"Wind factor calculation failed: {e}")
        return 1.0 

def get_terrain_value(terrain_data, x, y, default=0.0):
    """
    Safely get terrain value from sparse or dense arrays.
    
    Args:
        terrain_data: Sparse matrix or dense array
        x, y: Coordinates
        default: Default value if data unavailable
        
    Returns:
        Terrain value at (x, y)
    """
    if terrain_data is None:
        return default
    
    try:
        # Check if it's a sparse matrix
        if hasattr(terrain_data, 'toarray'):
            # Sparse matrix - convert to dense for this calculation
            dense_data = terrain_data.toarray()
            if x < dense_data.shape[0] and y < dense_data.shape[1]:
                return dense_data[x, y]
        else:
            # Dense array
            if x < terrain_data.shape[0] and y < terrain_data.shape[1]:
                return terrain_data[x, y]
    except:
        pass
    return default

def get_terrain_statistics(terrain_data, operation='min'):
    """
    Get statistics from sparse or dense terrain data.
    
    Args:
        terrain_data: Sparse matrix or dense array
        operation: 'min', 'max', 'mean', 'sum', 'any'
        
    Returns:
        Statistical value
    """
    if terrain_data is None:
        return 0.0
    
    try:
        # Convert sparse to dense for statistics
        if hasattr(terrain_data, 'toarray'):
            dense_data = terrain_data.toarray()
        else:
            dense_data = terrain_data
        
        if operation == 'min':
            return np.min(dense_data)
        elif operation == 'max':
            return np.max(dense_data)
        elif operation == 'mean':
            return np.mean(dense_data)
        elif operation == 'sum':
            return np.sum(dense_data)
        elif operation == 'any':
            return np.any(dense_data)
        else:
            return 0.0
    except:
        return 0.0

def create_sparse_terrain_array(shape, value=0.0, dtype=np.float32):
    """
    Create a sparse terrain array compatible with our system.
    
    Args:
        shape: Array shape (width, height)
        value: Default value
        dtype: Data type
        
    Returns:
        Sparse matrix or dense array depending on size
    """
    try:
        from scipy.sparse import lil_matrix
        # Use sparse for large arrays
        if shape[0] * shape[1] > 1_000_000:  # 1M+ cells
            sparse_array = lil_matrix(shape, dtype=dtype)
            if value != 0.0:
                # Fill with value (not memory efficient, but maintains compatibility)
                dense_temp = np.full(shape, value, dtype=dtype)
                sparse_array = lil_matrix(dense_temp)
            return sparse_array
        else:
            # Use dense for smaller arrays
            return np.full(shape, value, dtype=dtype)
    except ImportError:
        # Fallback to dense if SciPy not available
        return np.full(shape, value, dtype=dtype) 