#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simulation Utilities Module

This module provides specialized utility functions for forest fire simulation.
It builds upon the shared_utilities.py module for core functionality while
adding simulation-specific utilities.
"""

import os
# import sys # Removed, does not appear to be used
import time
# import logging # Replaced by get_logger
import numpy as np
from typing import Dict, Any, Optional, Union, Tuple, List

# Import standardized logger
from src.utils.logging_utils import get_logger
logger = get_logger(__name__) # Use module name for logger

# Direct import of shared utilities and config tools
# SHARED_IMPORTS_SUCCESS flag and try-except blocks are removed.
from src.utils.shared_utilities import (
    log_once,
    # get_config_value, # This should be replaced by ModelConfig access
    calculate_memory_requirements,
    get_progress_iterator,
    error_handler
)
from src.core.forest_model import MinimalForestModelStub
from src.config.config_tools import get_global_config, ModelConfig # get_constant is deprecated, ModelConfig is the source of truth
logger.info("Successfully imported shared utilities and config tools.")

# Constants (MODEL_RESOLUTION, LAYER_HEIGHT_METERS, DEFAULT_NUM_LAYERS) are no longer imported or defined here.
# Functions requiring these will need to accept them as parameters or get them from a ModelConfig instance.
# CONSTANTS_IMPORTED flag and try-except blocks are removed.

# Simulation-specific utility functions

def generate_wind_field(
    grid_size: Union[int, Tuple[int, int]],
    wind_direction: float = 0.0,
    wind_strength: float = 5.0,
    terrain_height: Optional[np.ndarray] = None,
    terrain_effect: float = 0.5
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate a wind field for the simulation.
    
    This function creates directional and strength arrays for wind.
    Terrain effects have been removed.
    
    Args:
        grid_size: Size of the grid (int or tuple)
        wind_direction: Base wind direction in degrees (0=N, 90=E)
        wind_strength: Base wind strength in m/s
        terrain_height: Parameter retained for compatibility but no longer used
        terrain_effect: Parameter retained for compatibility but no longer used
        
    Returns:
        Tuple of (wind_direction, wind_strength) arrays
    """
    # Handle grid_size as tuple or single value
    if isinstance(grid_size, tuple):
        width, height = grid_size
    else:
        width = height = grid_size
    
    # Create base wind arrays (uniform wind field)
    direction = np.ones((width, height), dtype=np.float32) * wind_direction
    strength = np.ones((width, height), dtype=np.float32) * wind_strength
    
    # Terrain effects have been removed
    
    return direction, strength

def calculate_spread_probabilities(
    fuel_load: np.ndarray,
    wind_direction: np.ndarray,
    wind_strength: np.ndarray,
    # model_config: ModelConfig, # Consider passing ModelConfig for parameters
    slope: Optional[np.ndarray] = None,
    moisture: Optional[np.ndarray] = None,
    wind_influence: float = 1.0, # Default, can be overridden by config
    slope_influence: float = 0.5, # Default, can be overridden by config
    threshold: float = 0.1 # Default, can be overridden by config
) -> np.ndarray:
    """
    Calculate fire spread probabilities for each cell.
    
    This function computes the probability of fire spreading from each cell
    to its neighbors based on fuel, wind, slope, and moisture.
    
    Args:
        fuel_load: 3D array of fuel load values
        wind_direction: 2D array of wind direction in degrees
        wind_strength: 2D array of wind strength
        slope: Optional 2D array of terrain slope
        moisture: Optional 2D array of fuel moisture content
        wind_influence: Factor for wind effect on spread (0-2)
        slope_influence: Factor for slope effect on spread (0-1)
        threshold: Minimum probability threshold
        
    Returns:
        4D array of spread probabilities (x, y, z, direction)
    """
    # Get dimensions
    if len(fuel_load.shape) == 3:
        # Heuristic: if the first dimension is much smaller than the other two, assume (L,W,H)
        # and that width, height for wind arrays correspond to fuel_load.shape[1] and fuel_load.shape[2]
        if fuel_load.shape[0] < fuel_load.shape[1] and fuel_load.shape[0] < fuel_load.shape[2] and fuel_load.shape[0] < 10: # Max 9 layers for this heuristic
            layers_dim_resolved, width_dim_resolved, height_dim_resolved = fuel_load.shape
            _is_layers_first_shape = True
        else: # Assume (W,H,L) convention for fuel_load
            width_dim_resolved, height_dim_resolved, layers_dim_resolved = fuel_load.shape
            _is_layers_first_shape = False
    else:
        # This case should ideally be validated before calling or raise a clearer error.
        # For now, try to handle as if it might be 2D fuel load for a single layer.
        if len(fuel_load.shape) == 2:
            width_dim_resolved, height_dim_resolved = fuel_load.shape
            layers_dim_resolved = 1
            fuel_load = fuel_load.reshape((width_dim_resolved, height_dim_resolved, 1)) # Make it 3D (W,H,1)
            _is_layers_first_shape = False # Now effectively (W,H,L)
        else:
            raise ValueError(f"fuel_load has unhandled shape: {fuel_load.shape}. Expected 3D or 2D.")

    # Initialize spread probability array (W, H, L, 8)
    # wind_direction and wind_strength are expected to be (W,H)
    # If fuel_load was (L,W,H), then width_dim_resolved, height_dim_resolved are W, H from fuel_load.
    spread_prob = np.zeros((width_dim_resolved, height_dim_resolved, layers_dim_resolved, 8), dtype=np.float32)

    # Base probability from fuel load (normalized)
    max_fuel = np.max(fuel_load) if np.max(fuel_load) > 0 else 1.0
    base_prob_source = fuel_load / max_fuel # Has shape of original fuel_load

    # Apply moisture effect if provided
    # Ensure moisture_3d has the same (W,H,L) or (L,W,H) convention as base_prob_source to allow broadcasting
    if moisture is not None:
        if _is_layers_first_shape: # base_prob_source is (L,W,H)
            if len(moisture.shape) == 2: # moisture is (W,H)
                moisture_shaped = np.repeat(moisture[np.newaxis, :, :], layers_dim_resolved, axis=0) # to (L,W,H)
            elif moisture.shape == base_prob_source.shape: # moisture is (L,W,H)
                moisture_shaped = moisture
            else:
                raise ValueError(f"Moisture shape {moisture.shape} incompatible with fuel (L,W,H) {base_prob_source.shape}")
        else: # base_prob_source is (W,H,L) or became (W,H,1)
            if len(moisture.shape) == 2: # moisture is (W,H)
                moisture_shaped = np.repeat(moisture[:, :, np.newaxis], layers_dim_resolved, axis=2) # to (W,H,L)
            elif moisture.shape == base_prob_source.shape: # moisture is (W,H,L)
                moisture_shaped = moisture
            else:
                raise ValueError(f"Moisture shape {moisture.shape} incompatible with fuel (W,H,L) {base_prob_source.shape}")
        
        moisture_factor = 1.0 - np.clip(moisture_shaped, 0, 1) * 0.8
        base_prob_source *= moisture_factor # Element-wise with original shape

    # Direction vectors (8 directions)
    directions = [
        (0, -1),  # N
        (1, -1),  # NE
        (1, 0),   # E
        (1, 1),   # SE
        (0, 1),   # S
        (-1, 1),  # SW
        (-1, 0),  # W
        (-1, -1)  # NW
    ]
    
    # Direction angles in degrees
    dir_angles = [0, 45, 90, 135, 180, 225, 270, 315]
    
    # Process each layer
    for z_idx in range(layers_dim_resolved):
        # For each direction
        for i_dir, (dx, dy) in enumerate(directions):
            # Correctly slice base_prob_source to get a (W,H) view for the current layer
            if _is_layers_first_shape: # fuel_load was (L,W,H), base_prob_source is (L,W,H)
                current_base_prob_slice = base_prob_source[z_idx, :, :].copy()
            else: # fuel_load was (W,H,L) or (W,H) made (W,H,1), base_prob_source is (W,H,L)
                current_base_prob_slice = base_prob_source[:, :, z_idx].copy()
            
            # current_base_prob_slice is now (W,H)
            # spread_prob slice is (W,H)
            # wind_direction and wind_strength are (W,H)
            spread_prob[:, :, z_idx, i_dir] = current_base_prob_slice

            # Apply wind effect
            if wind_influence > 0:
                # Calculate angle difference between wind and spread direction
                # wind_direction is (W,H), dir_angles[i_dir] is scalar
                angle_diff = np.abs(wind_direction - dir_angles[i_dir]) % 360
                angle_diff = np.minimum(angle_diff, 360 - angle_diff)
                
                # Wind factor is highest when direction matches wind
                wind_factor = np.cos(np.radians(angle_diff))
                
                # Scale by wind strength and influence
                wind_effect = wind_factor * wind_strength * wind_influence / 10.0
                
                # Apply wind effect (can increase or decrease probability)
                spread_prob[:, :, z_idx, i_dir] *= (1.0 + wind_effect)
            
            # Apply slope effect if provided
            if slope is not None and slope_influence > 0:
                # Calculate slope in direction of spread
                if dx != 0 or dy != 0:
                    # Compute directional slope
                    dir_slope = np.zeros((width_dim_resolved, height_dim_resolved), dtype=np.float32)
                    
                    # Valid cells (not edge cells)
                    valid = np.ones((width_dim_resolved, height_dim_resolved), dtype=bool)
                    if dx > 0:
                        valid[-1, :] = False
                    elif dx < 0:
                        valid[0, :] = False
                    if dy > 0:
                        valid[:, -1] = False
                    elif dy < 0:
                        valid[:, 0] = False
                    
                    # Calculate height difference in direction
                    for x in range(width_dim_resolved):
                        for y in range(height_dim_resolved):
                            if valid[x, y]:
                                nx, ny = x + dx, y + dy
                                if 0 <= nx < width_dim_resolved and 0 <= ny < height_dim_resolved:
                                    dir_slope[x, y] = slope[nx, ny] - slope[x, y]
                    
                    # Slope effect (positive slope = higher probability)
                    slope_effect = dir_slope * slope_influence
                    
                    # Apply slope effect
                    spread_prob[:, :, z_idx, i_dir] *= (1.0 + slope_effect)
    
    # Apply threshold and normalize
    spread_prob = np.maximum(spread_prob, threshold)
    
    return spread_prob

def optimize_grid_parameters(
    geographic_extent: Tuple[float, float, float, float],
    target_resolution: float, # This was MODEL_RESOLUTION
    memory_limit_mb: float,
    num_layers: int, # This was DEFAULT_NUM_LAYERS
    # model_config: Optional[ModelConfig] = None # Option to pass config
) -> Dict[str, Any]:
    """
    Optimize grid parameters based on extent, resolution, and memory.

    Args:
        geographic_extent: Geographic extent (min_x, min_y, max_x, max_y).
        target_resolution: Desired resolution in meters.
        memory_limit_mb: Available memory in MB.
        num_layers: Number of vertical layers.
        # model_config: Optional ModelConfig instance for more detailed params.

    Returns:
        Dictionary with optimized grid parameters.
    """
    # if model_config is None:
    #     model_config = get_global_config()
    # target_resolution = getattr(model_config, 'model_resolution', target_resolution) # Prioritize passed arg
    # num_layers = getattr(model_config, 'num_layers', num_layers) # Prioritize passed arg

    min_x, min_y, max_x, max_y = geographic_extent
    width_m = max_x - min_x
    height_m = max_y - min_y
    
    # Calculate grid dimensions at target resolution
    grid_width = int(width_m / target_resolution)
    grid_height = int(height_m / target_resolution)
    
    # Calculate memory requirements
    mem_req = calculate_memory_requirements(
        grid_size=(grid_width, grid_height),
        num_layers=num_layers,
        # Add default values for missing parameters required by calculate_memory_requirements
        memory_optimization_level=0, # Default to no optimization
        store_full_states=True,      # Default assumption
        use_differential_history=False,# Default assumption
        save_interval=1,             # Default assumption
        bytes_per_cell=4,            # Default for float32 state/fuel arrays
        use_multi_resolution=False,  # Default assumption
        max_resolution_levels=1      # Default assumption
    )
    total_mb = mem_req["total_estimated_in_memory_mb"]
    
    # Check if we need to adjust resolution
    if total_mb <= memory_limit_mb:
        # We can use target resolution directly
        return {
            "grid_size": (grid_width, grid_height),
            "resolution": target_resolution,
            "memory_mb": total_mb,
            "use_tiling": False,
            "tile_size": None,
            "overlap": None
        }
    
    # We need to use tiling
    # Calculate tile size to fit in memory (with 20% buffer)
    memory_per_cell_mb = total_mb / (grid_width * grid_height * num_layers)
    cells_per_tile = int((memory_limit_mb * 0.8) / (memory_per_cell_mb * num_layers))
    tile_size = int(np.sqrt(cells_per_tile))
    
    # Calculate overlap (5% of tile size)
    overlap = max(1, int(tile_size * 0.05))
    
    return {
        "grid_size": (grid_width, grid_height),
        "resolution": target_resolution,
        "memory_mb": total_mb,
        "use_tiling": True,
        "tile_size": tile_size,
        "overlap": overlap
    }

# Fallback utility definitions are removed as shared_utilities are now directly imported.
# if not SHARED_IMPORTS_SUCCESS:
#     ... 