#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Memory Management Utilities Module

Provides standardized memory usage tracking and optimization functions for the Forest Fire Simulation Framework.
This consolidates memory-related code that was previously scattered across the codebase.
"""

import os
import logging
import math
import numpy as np
from typing import Dict, Any, Optional, Union, List, Tuple
from pathlib import Path

# Setup logger
logger = logging.getLogger(__name__)

# Try importing psutil, but provide a fallback
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil module not found. Memory usage tracking will use fallback mechanisms.")

# Memory optimization levels
MEMORY_OPTIMIZATION_LEVELS = {
    0: "None - Full memory usage",
    1: "Low - Basic memory optimization",
    2: "Medium - Aggressive memory optimization with tiling",
    3: "High - Maximum memory optimization with minimal storage"
}

class MemoryTracker:
    """
    Tracks memory usage across the application.
    """
    
    def __init__(self):
        """Initialize the memory tracker."""
        self.memory_usage_history = []
        self.memory_usage_steps = []
        self.initial_memory = self.get_current_memory_usage()
        self.memory_usage_history.append(self.initial_memory)
        self.memory_usage_steps.append(0)
        
        logger.info(f"Memory tracker initialized. Initial memory usage: {self.initial_memory:.2f}MB")
    
    def track_step(self, step: int) -> Dict[str, float]:
        """
        Track memory usage at a specific step.
        
        Args:
            step: Current simulation step
            
        Returns:
            Dictionary with current memory stats
        """
        current_memory = self.get_current_memory_usage()
        self.memory_usage_history.append(current_memory)
        self.memory_usage_steps.append(step)
        
        # Calculate memory change from initial and previous
        memory_delta = current_memory - self.initial_memory
        
        # Calculate change from previous if available
        prev_delta = 0
        percent_change = 0
        if len(self.memory_usage_history) >= 2:
            prev_memory = self.memory_usage_history[-2]
            prev_delta = current_memory - prev_memory
            percent_change = ((current_memory - prev_memory) / prev_memory) * 100
            
            # Log significant memory changes
            if percent_change > 5:
                logger.warning(f"Memory usage increased by {percent_change:.1f}% at step {step}: " +
                              f"{prev_memory:.1f}MB → {current_memory:.1f}MB")
        
        return {
            "current_mb": current_memory,
            "initial_mb": self.initial_memory,
            "delta_mb": memory_delta,
            "delta_percent": (memory_delta / self.initial_memory) * 100 if self.initial_memory > 0 else 0,
            "prev_delta_mb": prev_delta,
            "prev_delta_percent": percent_change
        }
    
    def get_report(self) -> Dict[str, Any]:
        """
        Generate a memory usage report.
        
        Returns:
            Dictionary with memory usage statistics
        """
        if not self.memory_usage_history:
            return {"error": "No memory history available"}
        
        final_memory = self.memory_usage_history[-1]
        peak_memory = max(self.memory_usage_history)
        initial_memory = self.memory_usage_history[0]
        memory_change = final_memory - initial_memory
        
        return {
            "steps": self.memory_usage_steps,
            "memory_mb": self.memory_usage_history,
            "peak_mb": peak_memory,
            "initial_mb": initial_memory,
            "final_mb": final_memory,
            "delta_mb": memory_change,
            "delta_percent": (memory_change / initial_memory) * 100 if initial_memory > 0 else 0
        }
    
    def save_report(self, output_dir: Union[str, Path]) -> str:
        """
        Save memory usage report to a file.
        
        Args:
            output_dir: Directory to save the report
            
        Returns:
            Path to the saved report file
        """
        import json
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        report_file = output_path / "memory_usage.json"
        
        try:
            with open(report_file, "w") as f:
                json.dump(self.get_report(), f, indent=2)
            logger.info(f"Memory usage data saved to {report_file}")
            return str(report_file)
        except Exception as e:
            logger.warning(f"Could not save memory usage data: {e}")
            return ""

    @staticmethod
    def get_current_memory_usage() -> float:
        """
        Get current memory usage in MB.
        
        Returns:
            Current memory usage in MB
        """
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert to MB
        except Exception as e:
            logger.warning(f"Error getting memory usage: {e}")
            return 0.0
    
    @staticmethod
    def get_system_memory() -> float:
        """
        Get total system memory in MB.
        
        Returns:
            Total system memory in MB
        """
        if not PSUTIL_AVAILABLE:
            # Fallback if psutil is not available
            logger.warning("psutil not available, using default system memory estimate")
            return 16384  # Assume 16GB
        
        try:
            return psutil.virtual_memory().total / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Error getting system memory: {e}")
            return 16384  # Assume 16GB as fallback

def optimize_for_memory(config: Any, memory_limit_gb: Optional[float] = None) -> Dict[str, Any]:
    """
    Optimize configuration for available memory.
    
    Args:
        config: Configuration object or dictionary
        memory_limit_gb: Memory limit in GB (None = auto-detect)
        
    Returns:
        Dictionary of optimized parameters
    """
    # Convert config to dict if it's not already
    config_dict = config.to_dict() if hasattr(config, 'to_dict') else config
    
    # Get memory limit (auto-detect if not specified)
    if memory_limit_gb is None:
        system_memory_mb = MemoryTracker.get_system_memory()
        # Use 80% of available memory as a safe default
        memory_limit_gb = system_memory_mb * 0.8 / 1024
    
    logger.info(f"Optimizing configuration for {memory_limit_gb:.2f}GB memory limit")
    
    # Extract key parameters
    grid_width, grid_height = _extract_grid_size(config_dict)
    num_layers = config_dict.get('num_layers', 10)
    
    # Calculate base memory requirements
    # Each cell typically requires multiple arrays (fuel, temperature, ignition state, etc.)
    bytes_per_cell = _estimate_bytes_per_cell(config_dict)
    total_cells = grid_width * grid_height * num_layers
    estimated_memory_gb = (total_cells * bytes_per_cell) / (1024 * 1024 * 1024)
    
    logger.info(f"Estimated memory without optimization: {estimated_memory_gb:.2f}GB "
                f"({grid_width}x{grid_height}x{num_layers} grid, {bytes_per_cell} bytes/cell)")
    
    # If estimated memory exceeds limit, optimize
    optimized = {}
    if estimated_memory_gb > memory_limit_gb:
        # Calculate optimization required
        reduction_factor = memory_limit_gb / estimated_memory_gb
        logger.info(f"Memory optimization needed. Reduction factor: {reduction_factor:.2f}")
        
        if reduction_factor < 0.9:
            # Significant reduction needed
            if reduction_factor < 0.5:
                # Very significant reduction - use aggressive tiling with level 2 optimization
                optimized['memory_optimization_level'] = 2  # Cap at level 2
                optimized['use_tiling'] = True
                
                # Set tile size based on available memory
                optimal_tile_size = _calculate_optimal_tile_size(grid_width, grid_height, memory_limit_gb)
                optimized['tile_size'] = optimal_tile_size
                
                # Note: Resolution reduction removed - rely on tiling and memory compression only
                logger.info("Using aggressive memory optimization (level 2) with tiling while preserving spatial resolution")
            else:
                # Moderate reduction - use basic memory optimization
                optimized['memory_optimization_level'] = 1
    else:
        logger.info("No memory optimization needed")
    
    # Return optimized parameters
    return optimized

def _extract_grid_size(config: Dict[str, Any]) -> Tuple[int, int]:
    """
    Extract grid width and height from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple of (grid_width, grid_height)
    """
    grid_size = config.get('grid_size', 100)
    
    if isinstance(grid_size, tuple) and len(grid_size) == 2:
        return grid_size
    elif isinstance(grid_size, int):
        return grid_size, grid_size
    else:
        # Default
        logger.warning(f"Invalid grid_size format: {grid_size}, using default 100x100")
        return 100, 100

def _estimate_bytes_per_cell(config: Dict[str, Any]) -> int:
    """
    Estimate memory usage per cell based on configuration.
    
    This function provides realistic memory estimates for HPC environments,
    accounting for all data structures used in the simulation.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Estimated bytes per cell (realistic for production use)
    """
    
    # Core simulation data per cell:
    base_bytes = 0
    
    # Essential arrays (always present):
    base_bytes += 4   # fuel_load (float32)
    base_bytes += 1   # state (int8: NOT_BURNING, BURNING, BURNED_OUT)
    base_bytes += 4   # temperature (float32)
    base_bytes += 4   # moisture_content (float32) 
    base_bytes += 4   # vertical_connectivity (float32)
    
    # Wind and terrain effects:
    base_bytes += 4   # wind_speed_factor (float32)
    base_bytes += 4   # terrain_elevation (float32)
    base_bytes += 4   # slope_factor (float32)
    base_bytes += 4   # aspect_factor (float32)
    
    # Fire spread mechanics:
    base_bytes += 4   # spread_probability (float32)
    base_bytes += 4   # ignition_threshold (float32)
    
    # Ember transport (if enabled):
    if config.get('ember_probability', 0) > 0:
        base_bytes += 2   # ember_count (int16)
        base_bytes += 4   # ember_accumulation (float32)
    
    # Terrain features (if terrain is enabled):
    if config.get('terrain', {}).get('use_terrain', False):
        base_bytes += 4   # barranco_factor (float32)
        base_bytes += 4   # depression_factor (float32)
    
    # LiDAR vegetation data (if enabled):
    if config.get('vegetation', {}).get('use_lidar', False):
        base_bytes += 4   # pad_density (float32)
        base_bytes += 4   # canopy_height (float32)
        base_bytes += 4   # extinction_coefficient (float32)
    
    # History tracking overhead:
    if config.get('store_full_states', True):
        # Additional memory for storing previous states
        base_bytes += 8   # History tracking overhead
    
    # Visualization data (if enabled):
    if config.get('save_visualizations', True):
        base_bytes += 4   # Visualization buffer overhead
    
    # Memory optimization adjustments:
    optimization_level = config.get('memory_optimization_level', 0)
    if optimization_level >= 2:
        # Sparse storage can reduce memory significantly for sparse data
        if config.get('use_sparse_storage', False):
            # Sparse storage efficiency depends on data density
            # For fire simulations, typically 10-30% of cells are active
            sparsity_factor = 0.3  # Assume 30% density
            base_bytes = int(base_bytes * sparsity_factor)
    
    # HPC safety factor (account for Python object overhead, fragmentation, etc.)
    safety_factor = 1.4
    
    # Minimum realistic value for HPC environments
    realistic_minimum = 25
    
    final_estimate = max(realistic_minimum, int(base_bytes * safety_factor))
    
    # Log the breakdown for debugging
    logger.debug(f"Memory per cell breakdown: base={base_bytes}, "
                f"safety_factor={safety_factor}, final={final_estimate}")
    
    return final_estimate

def _calculate_optimal_tile_size(grid_width: int, grid_height: int, memory_limit_gb: float) -> int:
    """
    Calculate optimal tile size based on grid dimensions and memory limit.
    
    Args:
        grid_width: Grid width
        grid_height: Grid height
        memory_limit_gb: Memory limit in GB
        
    Returns:
        Optimal tile size
    """
    # Target memory per tile in GB (with overhead for processing)
    target_tile_memory_gb = memory_limit_gb * 0.4
    
    # Calculate cells based on target memory
    # Assume ~50 bytes per cell total memory usage including overhead
    cells_per_tile = int((target_tile_memory_gb * 1024 * 1024 * 1024) / 50)
    
    # Calculate tile size (square tile)
    tile_size = int(math.sqrt(cells_per_tile))
    
    # Ensure tile size is reasonable
    tile_size = min(tile_size, min(grid_width, grid_height))
    tile_size = max(tile_size, 100)  # Minimum tile size for efficiency
    
    logger.info(f"Calculated optimal tile size: {tile_size}")
    return tile_size

def estimate_memory_requirements(config: Dict[str, Any]) -> Dict[str, float]:
    """
    Estimate memory requirements for a given configuration.
    
    DEPRECATED: This function is deprecated. Use shared_utilities.calculate_memory_requirements() directly.
    This wrapper is maintained for backward compatibility.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary of memory estimates
    """
    try:
        from src.utils.shared_utilities import calculate_memory_requirements
        
        # Extract parameters from config
        grid_size = config.get('grid_size', (100, 100))
        if isinstance(grid_size, int):
            grid_size = (grid_size, grid_size)
        
        # Use the standardized function
        result = calculate_memory_requirements(
            grid_size=grid_size,
            num_layers=config.get('num_layers', 10),
            memory_optimization_level=config.get('memory_optimization_level', 0),
            store_full_states=config.get('store_full_states', True),
            use_differential_history=config.get('use_differential_history', False),
            save_interval=config.get('save_interval', 5),
            bytes_per_cell=config.get('bytes_per_cell', 10)
        )
        
        # Map to legacy format for backward compatibility
        return {
            'grid_size_x': result['grid_size'][0],
            'grid_size_y': result['grid_size'][1],
            'num_layers': result.get('num_layers', config.get('num_layers', 10)),
            'total_cells': result['total_cells'],
            'bytes_per_cell': result['bytes_per_cell'],
            'model_memory_mb': result['total_grid_data_mb'],
            'overhead_memory_mb': result['other_overheads_mb'],
            'results_memory_mb': result['history_buffer_mb'],
            'total_memory_mb': result['total_estimated_in_memory_mb'],
            'total_memory_gb': result['total_estimated_in_memory_mb'] / 1024
        }
        
    except ImportError:
        logger.warning("Could not import shared_utilities. Using legacy calculation.")
        # Fallback to simplified calculation
        grid_width, grid_height = _extract_grid_size(config)
        num_layers = config.get('num_layers', 10)
        total_cells = grid_width * grid_height * num_layers
        bytes_per_cell = _estimate_bytes_per_cell(config)
        model_memory_mb = (total_cells * bytes_per_cell) / (1024 * 1024)
        
        return {
            'grid_size_x': grid_width,
            'grid_size_y': grid_height,
            'num_layers': num_layers,
            'total_cells': total_cells,
            'bytes_per_cell': bytes_per_cell,
            'model_memory_mb': model_memory_mb,
            'overhead_memory_mb': 200,  # Fixed overhead
            'results_memory_mb': 10,    # Fixed results memory
            'total_memory_mb': model_memory_mb + 210,
            'total_memory_gb': (model_memory_mb + 210) / 1024
        }

def get_optimal_thread_count(memory_limit_gb: Optional[float] = None) -> int:
    """
    Calculate optimal thread count based on system resources.
    
    Args:
        memory_limit_gb: Memory limit in GB (None = auto-detect)
        
    Returns:
        Optimal thread count
    """
    # Get available CPU cores
    try:
        available_cores = os.cpu_count() or 4
    except:
        available_cores = 4
    
    # Start with CPU count
    optimal_threads = max(1, available_cores - 1)  # Leave one core for system
    
    # Adjust based on memory if specified
    if memory_limit_gb is not None and PSUTIL_AVAILABLE:
        try:
            # Get total system memory
            total_memory_gb = psutil.virtual_memory().total / (1024 * 1024 * 1024)
            
            # If memory is constrained relative to cores, reduce threads
            memory_per_core_gb = total_memory_gb / available_cores
            
            if memory_per_core_gb < 2.0:  # Less than 2GB per core
                # Reduce threads based on available memory
                memory_factor = min(1.0, memory_per_core_gb / 2.0)
                optimal_threads = max(1, int(optimal_threads * memory_factor))
                
                logger.info(f"Limiting threads due to memory constraints: {optimal_threads} "
                            f"(Memory per core: {memory_per_core_gb:.2f}GB)")
        except Exception as e:
            logger.warning(f"Error calculating memory-based thread count: {e}")
    
    logger.info(f"Optimal thread count: {optimal_threads}")
    return optimal_threads

def calculate_optimal_hpc_config(config: Dict[str, Any], 
                                available_memory_gb: float,
                                available_cores: int,
                                target_efficiency: float = 0.85) -> Dict[str, Any]:
    """
    Calculate optimal HPC configuration for large-scale simulations.
    
    This function addresses resource allocation mismatch and conservative 
    parallelization by optimizing tile size, parallelization, and memory usage.
    
    Args:
        config: Current configuration dictionary
        available_memory_gb: Available memory in GB (from SLURM allocation)
        available_cores: Available CPU cores
        target_efficiency: Target memory efficiency (0.0-1.0)
        
    Returns:
        Dictionary with optimized HPC parameters
    """
    logger.info(f"Calculating optimal HPC config for {available_memory_gb}GB memory, {available_cores} cores")
    
    # Extract grid parameters
    grid_width, grid_height = _extract_grid_size(config)
    num_layers = config.get('num_layers', 10)
    total_cells = grid_width * grid_height * num_layers
    
    # Calculate realistic memory requirements
    bytes_per_cell = _estimate_bytes_per_cell(config)
    
    # Usable memory (leave buffer for OS and overhead)
    usable_memory_gb = available_memory_gb * target_efficiency
    
    logger.info(f"Grid: {grid_width}x{grid_height}x{num_layers} = {total_cells:,} cells")
    logger.info(f"Estimated: {bytes_per_cell} bytes/cell = {(total_cells * bytes_per_cell) / (1024**3):.2f}GB total")
    logger.info(f"Usable memory: {usable_memory_gb:.1f}GB ({target_efficiency*100:.0f}% of {available_memory_gb}GB)")
    
    # Calculate if we need tiling
    total_memory_gb = (total_cells * bytes_per_cell) / (1024**3)
    needs_tiling = total_memory_gb > usable_memory_gb
    
    optimal_config = {}
    
    if needs_tiling:
        logger.info("Grid requires tiling for memory efficiency")
        
        # Calculate optimal tile size based on memory per tile
        # Reserve cores for I/O and system processes
        reserve_cores = min(4, max(1, available_cores // 8))
        worker_cores = available_cores - reserve_cores
        
        # Memory per worker (leaving some for coordination overhead)
        memory_per_worker_gb = (usable_memory_gb * 0.9) / worker_cores
        
        # Calculate cells per tile based on available memory per worker
        cells_per_tile = int((memory_per_worker_gb * 1024**3) / bytes_per_cell)
        
        # For square tiles in 2D (layers processed per tile)
        cells_per_layer_per_tile = cells_per_tile // num_layers
        tile_size = int(math.sqrt(cells_per_layer_per_tile))
        
        # Ensure tile size is reasonable
        tile_size = max(50, min(tile_size, min(grid_width, grid_height)))
        
        # Calculate number of tiles
        tiles_x = math.ceil(grid_width / tile_size)
        tiles_y = math.ceil(grid_height / tile_size)
        total_tiles = tiles_x * tiles_y
        
        # Optimize parallel workers
        max_parallel_tiles = min(worker_cores, total_tiles)
        
        # Calculate tile batch size (how many tiles per worker before coordination)
        tiles_per_worker = total_tiles / max_parallel_tiles
        tile_batch_size = max(1, min(4, int(tiles_per_worker / 4)))
        
        optimal_config.update({
            'use_tiling': True,
            'tile_size': tile_size,
            'max_parallel_tiles': max_parallel_tiles,
            'tile_batch_size': tile_batch_size,
            'reserve_cpus': reserve_cores,
            'memory_optimization_level': 2,  # Cap at level 2 instead of 3
            'use_sparse_storage': True,
            'enable_memory_cleanup': True,
            'gc_frequency': max(1, max_parallel_tiles // 4)
        })
        
        logger.info(f"Tiling config: {tile_size}x{tile_size} tiles, "
                   f"{tiles_x}x{tiles_y} = {total_tiles} total, "
                   f"{max_parallel_tiles} parallel workers")
                   
    else:
        logger.info("Grid fits in memory without tiling")
        
        # Still use some parallelization for processing efficiency
        reserve_cores = min(2, available_cores // 4)
        max_workers = available_cores - reserve_cores
        
        optimal_config.update({
            'use_tiling': False,
            'max_workers': max_workers,
            'reserve_cpus': reserve_cores,
            'memory_optimization_level': 2,  # Use level 2 instead of 1 for non-tiling scenarios
            'use_sparse_storage': config.get('use_sparse_storage', True),
            'enable_memory_cleanup': True
        })
    
    # Memory allocation settings
    optimal_config.update({
        'memory_limit_per_node': available_memory_gb * 0.95,  # Use 95% of allocated
        'bytes_per_cell': bytes_per_cell,  # Realistic estimate
        'gdal_cache_mb': min(4096, int(available_memory_gb * 1024 * 0.1)),  # 10% for GDAL cache
        'io_block_size': 16384,  # Larger I/O blocks for HPC storage
    })
    
    # Disk storage settings  
    if config.get('use_disk_storage', False):
        optimal_config.update({
            'checkpoint_interval': min(1000, max(100, total_cells // 10000)),  # Adaptive checkpointing
            'force_sequential_tiles': False  # Allow parallel I/O
        })
    
    # Log final configuration
    estimated_memory_gb = (total_cells * bytes_per_cell) / (1024**3)
    logger.info(f"Final memory estimate: {estimated_memory_gb:.2f}GB")
    logger.info(f"Memory efficiency: {(estimated_memory_gb / available_memory_gb) * 100:.1f}%")
    
    return optimal_config 