#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration management tools for forest fire simulation systems.

This module provides utilities for creating, validating, saving, and loading
simulation configurations, as well as for estimating memory requirements and
optimizing configurations for specific simulation scenarios.
"""

import os
import json
import logging
import math
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Tuple
from dataclasses import dataclass, field, asdict

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("config_tools")

@dataclass
class ModelConfig:
    """
    Configuration class for forest fire simulation parameters.
    Centralized configuration management to ensure consistency across
    all components of the simulation system.
    """
    # -------------------------------------------------------------------------
    # SPATIAL CONFIGURATION
    # -------------------------------------------------------------------------
    model_resolution: float = 5.0  # meters per grid cell
    """
    Spatial resolution in meters per grid cell. Determines the level of detail in the simulation.
    Lower values provide higher detail but require more memory (quadratic relationship).
    Used for converting between geographic coordinates and grid cells:
    cell_count = physical_distance / model_resolution
    """
    
    num_layers: int = 8  # number of vertical layers
    """
    Number of vertical layers in the forest model. Determines the vertical resolution of the 3D forest.
    More layers provide better representation of vertical vegetation structure but increase memory usage linearly.
    Each layer represents a height stratum in the forest from ground level to canopy top.
    """
    
    layer_height: float = 1.0  # meters per layer
    """
    Height of each vertical layer in meters. Should match height bins used in LiDAR preprocessing.
    Total forest height = num_layers * layer_height
    """
    
    # -------------------------------------------------------------------------
    # FIRE BEHAVIOR PARAMETERS
    # -------------------------------------------------------------------------
    spread_probability: float = 0.3
    """
    Base probability of fire spreading horizontally to adjacent cells.
    This value is modified by factors like wind, slope, fuel moisture, and fuel load.
    In the simulation, actual spread probability to a cell is calculated as:
    P(spread) = spread_probability * wind_factor * slope_factor * (1 - moisture_factor) * fuel_load_factor
    """
    
    vertical_spread: float = 0.2
    """
    Base probability of fire spreading upward to cells in the layer above.
    Vertical spread is typically lower than horizontal spread but is enhanced by vertical connectivity.
    Actual vertical spread probability:
    P(vertical_spread) = vertical_spread * vertical_connectivity * (1 + ember_factor)
    """
    
    downward_spread: float = 0.15
    """
    Base probability of fire spreading downward to cells in the layer below.
    Downward spread is usually less likely than upward spread due to convection physics.
    P(downward_spread) = downward_spread * vertical_connectivity * terrain_factor
    """
    
    diagonal_factor: float = 0.707  # sqrt(2)/2
    """
    Factor reducing spread probability for diagonally adjacent cells. 
    Default is sqrt(2)/2 ≈ 0.707, representing increased distance to diagonal neighbors.
    P(diagonal_spread) = P(horizontal_spread) * diagonal_factor
    """
    
    # -------------------------------------------------------------------------
    # EMBER PARAMETERS
    # -------------------------------------------------------------------------
    ember_probability: float = 0.05
    """
    Base probability of a burning cell generating an ember in each time step.
    Embers enable long-distance fire spread. Higher values create more spotting behavior.
    Actual ember generation probability is modified by height and wind:
    P(ember) = ember_probability * height_factor * wind_speed_factor
    """
    
    ember_distance: int = 5  # cells
    """
    Mean travel distance for embers in grid cells.
    Actual distance is sampled from a distribution with this mean.
    Physical distance = ember_distance * model_resolution
    """
    
    ember_rise: int = 2  # layers
    """
    Number of layers embers typically rise during transport.
    Higher values allow embers to travel over barriers like ridges.
    """
    
    ember_ignition: float = 0.3
    """
    Probability of an ember successfully igniting unburned fuel upon landing.
    Modified by local fuel moisture and fuel load:
    P(ignition) = ember_ignition * (1 - local_moisture) * fuel_load_factor
    """
    
    # -------------------------------------------------------------------------
    # ENVIRONMENTAL CONDITIONS
    # -------------------------------------------------------------------------
    wind_speed: float = 5.0  # m/s
    """
    Wind speed in meters per second. Affects fire spread direction and ember transport.
    Higher values create more directional spread patterns.
    Used in wind factor calculation: wind_factor = 1 + (wind_speed * wind_influence * direction_alignment)
    """
    
    wind_direction: float = 0.0  # degrees (0 = north, 90 = east)
    """
    Wind direction in degrees (meteorological convention):
    0 = north, 90 = east, 180 = south, 270 = west
    Used to calculate the directional component of fire spread.
    """
    
    wind_influence: float = 0.5
    """
    Scaling factor for wind effects on fire spread (0-1).
    Higher values make wind more influential in determining spread patterns.
    Used in: wind_factor = 1 + (wind_speed * wind_influence * direction_alignment)
    """
    
    slope_influence: float = 0.3
    """
    Scaling factor for terrain slope effects on fire spread (0-1).
    Higher values make slope more influential in determining spread patterns.
    Used in: slope_factor = 1 + (slope_percent * slope_influence * upslope_alignment)
    """
    
    fuel_moisture_baseline: float = 0.3  # default fuel moisture
    """
    Default fuel moisture content as a proportion (0-1).
    Higher values reduce fire spread probability.
    Used when specific fuel moisture data is not available.
    Affects spread through: moisture_factor = fuel_moisture_baseline * moisture_influence
    """
    
    moisture_influence: float = 0.6
    """
    Scaling factor for moisture effects on fire spread (0-1).
    Higher values make fuel moisture more limiting to fire spread.
    Used in: effective_spread = spread_probability * (1 - moisture_factor)
    """
    
    # -------------------------------------------------------------------------
    # FUEL PARAMETERS
    # -------------------------------------------------------------------------
    min_fuel_value: float = 0.1
    """
    Minimum fuel value for a cell to be combustible.
    Cells with less fuel than this won't burn regardless of other factors.
    Used as a threshold in ignition calculations.
    """
    
    max_fuel_value: float = 10.0
    """
    Maximum fuel value, used for normalization.
    Plant Area Density (PAD) values are typically scaled to this range.
    """
    
    fuel_consumption_rate: float = 0.2
    """
    Rate at which fuel is consumed by fire per time step (proportion).
    Affects how long a cell remains in the burning state.
    Time burning (steps) ≈ 1 / fuel_consumption_rate
    """
    
    # -------------------------------------------------------------------------
    # MEMORY MANAGEMENT
    # -------------------------------------------------------------------------
    tile_size: int = 200  # cells per side
    """
    Size of processing tiles in grid cells (not meters).
    Larger tiles process more area at once but use more memory.
    Physical tile size = tile_size * model_resolution
    """
    
    tile_overlap: int = 20  # cells
    """
    Overlap between adjacent tiles in grid cells.
    Ensures smooth transitions and prevents edge artifacts during tiled processing.
    Effective grid cells processed: (tile_size - 2 * tile_overlap)² per tile
    """
    
    memory_limit_mb: int = 4000  # MB
    """
    Memory limit in megabytes for simulation processing.
    Used to automatically determine optimal tiling strategy.
    If estimated memory exceeds this, tiling will be automatically configured.
    """
    
    bytes_per_cell: int = 15
    """
    Estimated memory usage per cell in bytes.
    Used for memory requirement calculations.
    Total memory ≈ grid_size_x * grid_size_y * num_layers * bytes_per_cell bytes
    """
    
    # -------------------------------------------------------------------------
    # SIMULATION CONTROL
    # -------------------------------------------------------------------------
    max_steps: int = 200
    """
    Maximum number of simulation steps. Prevents indefinite execution.
    The simulation may end earlier if fire is extinguished.
    """
    
    save_interval: int = 10
    """
    Interval between saving full simulation states for analysis.
    Lower values provide more detailed history but use more memory.
    """
    
    random_seed: Optional[int] = None
    """
    Seed for random number generation. Set for reproducible results.
    If None, a random seed will be used, producing different results each run.
    """
    
    stop_when_fire_extinguished: bool = True
    """
    Whether to automatically end the simulation when no cells are burning.
    Setting to False will always run for max_steps regardless of fire state.
    """
    
    # -------------------------------------------------------------------------
    # OUTPUT CONFIGURATION
    # -------------------------------------------------------------------------
    output_dir: str = "results"
    """
    Directory to save simulation results and visualizations.
    Will be created if it doesn't exist.
    """
    
    save_visualizations: bool = True
    """
    Whether to generate and save visualization outputs automatically.
    Set to False to reduce disk usage for batch processing.
    """
    
    # -------------------------------------------------------------------------
    # VISUALIZATION PARAMETERS
    # -------------------------------------------------------------------------
    viz_frame_interval_ms: int = 200
    """
    Milliseconds between frames in animated visualizations.
    Lower values create smoother but faster animations.
    """
    
    viz_elevation_factor: float = 1.5
    """
    Vertical exaggeration factor for 3D visualizations.
    Enhances visibility of vertical structure.
    """
    
    # -------------------------------------------------------------------------
    # PAD PARAMETERS
    # -------------------------------------------------------------------------
    extinction_coefficient: float = 0.5
    """
    Extinction coefficient for Beer-Lambert law in PAD calculations.
    Species-specific parameter affecting plant area density estimates:
    PAD = -ln(1 - NRD) / (extinction_coefficient * bin_size)
    
    Typical values:
    - Coniferous forests: 0.5-0.7
    - Deciduous forests: 0.4-0.6
    - Mixed forests: ~0.5
    - Shrublands: 0.3-0.5
    """
    
    pad_bin_size: float = 2.0
    """
    Vertical bin size in meters used in Plant Area Density calculations.
    Should match the layer_height or be a multiple of it.
    Used in: PAD = -ln(1 - NRD) / (extinction_coefficient * pad_bin_size)
    """
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self) -> List[str]:
        """
        Validate configuration parameters and return list of warnings.
        
        Returns:
            List[str]: List of warning messages
        """
        warnings = []
        
        # Validate spatial configuration
        if self.model_resolution <= 0:
            warnings.append(f"Invalid model_resolution: {self.model_resolution}. Must be positive.")
        
        if self.num_layers <= 0:
            warnings.append(f"Invalid num_layers: {self.num_layers}. Must be positive.")
        
        if self.layer_height <= 0:
            warnings.append(f"Invalid layer_height: {self.layer_height}. Must be positive.")
        
        # Validate fire behavior parameters
        if not 0 <= self.spread_probability <= 1:
            warnings.append(f"Invalid spread_probability: {self.spread_probability}. Must be between 0 and 1.")
        
        if not 0 <= self.vertical_spread <= 1:
            warnings.append(f"Invalid vertical_spread: {self.vertical_spread}. Must be between 0 and 1.")
            
        if not 0 <= self.downward_spread <= 1:
            warnings.append(f"Invalid downward_spread: {self.downward_spread}. Must be between 0 and 1.")
        
        if self.diagonal_factor < 0:
            warnings.append(f"Invalid diagonal_factor: {self.diagonal_factor}. Must be non-negative.")
        
        # Validate ember parameters
        if not 0 <= self.ember_probability <= 1:
            warnings.append(f"Invalid ember_probability: {self.ember_probability}. Must be between 0 and 1.")
            
        if not 0 <= self.ember_ignition <= 1:
            warnings.append(f"Invalid ember_ignition: {self.ember_ignition}. Must be between 0 and 1.")
        
        if self.ember_distance < 0:
            warnings.append(f"Invalid ember_distance: {self.ember_distance}. Must be non-negative.")
            
        if self.ember_rise < 0:
            warnings.append(f"Invalid ember_rise: {self.ember_rise}. Must be non-negative.")
        
        # Validate environmental conditions
        if self.wind_speed < 0:
            warnings.append(f"Invalid wind_speed: {self.wind_speed}. Must be non-negative.")
            
        if not 0 <= self.wind_influence <= 1:
            warnings.append(f"Invalid wind_influence: {self.wind_influence}. Must be between 0 and 1.")
            
        if not 0 <= self.slope_influence <= 1:
            warnings.append(f"Invalid slope_influence: {self.slope_influence}. Must be between 0 and 1.")
        
        if not 0 <= self.fuel_moisture_baseline <= 1:
            warnings.append(f"Invalid fuel_moisture_baseline: {self.fuel_moisture_baseline}. Must be between 0 and 1.")
            
        if not 0 <= self.moisture_influence <= 1:
            warnings.append(f"Invalid moisture_influence: {self.moisture_influence}. Must be between 0 and 1.")
        
        # Validate fuel parameters
        if self.min_fuel_value < 0:
            warnings.append(f"Invalid min_fuel_value: {self.min_fuel_value}. Must be non-negative.")
            
        if self.max_fuel_value <= self.min_fuel_value:
            warnings.append(f"Invalid max_fuel_value: {self.max_fuel_value}. Must be greater than min_fuel_value.")
            
        if not 0 < self.fuel_consumption_rate <= 1:
            warnings.append(f"Invalid fuel_consumption_rate: {self.fuel_consumption_rate}. Must be between 0 and 1.")
        
        # Validate memory management
        if self.tile_size <= 0:
            warnings.append(f"Invalid tile_size: {self.tile_size}. Must be positive.")
        
        if self.tile_overlap < 0:
            warnings.append(f"Invalid tile_overlap: {self.tile_overlap}. Must be non-negative.")
            
        if self.tile_size <= 2 * self.tile_overlap:
            warnings.append(f"Invalid tile configuration: tile_size ({self.tile_size}) must be greater than 2 * tile_overlap ({2 * self.tile_overlap}).")
        
        if self.memory_limit_mb <= 0:
            warnings.append(f"Invalid memory_limit_mb: {self.memory_limit_mb}. Must be positive.")
            
        if self.bytes_per_cell <= 0:
            warnings.append(f"Invalid bytes_per_cell: {self.bytes_per_cell}. Must be positive.")
        
        # Validate simulation control
        if self.max_steps <= 0:
            warnings.append(f"Invalid max_steps: {self.max_steps}. Must be positive.")
            
        if self.save_interval <= 0:
            warnings.append(f"Invalid save_interval: {self.save_interval}. Must be positive.")
            
        # Validate visualization parameters
        if self.viz_frame_interval_ms <= 0:
            warnings.append(f"Invalid viz_frame_interval_ms: {self.viz_frame_interval_ms}. Must be positive.")
            
        if self.viz_elevation_factor <= 0:
            warnings.append(f"Invalid viz_elevation_factor: {self.viz_elevation_factor}. Must be positive.")
            
        # Validate PAD parameters
        if self.extinction_coefficient <= 0:
            warnings.append(f"Invalid extinction_coefficient: {self.extinction_coefficient}. Must be positive.")
            
        if self.pad_bin_size <= 0:
            warnings.append(f"Invalid pad_bin_size: {self.pad_bin_size}. Must be positive.")
        
        return warnings
    
    def validate(self, raise_exception: bool = False) -> bool:
        """
        Validate the configuration and return True if valid.
        Optionally raise an exception with all validation errors.
        
        Args:
            raise_exception (bool): Whether to raise an exception on validation failure
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValueError: If raise_exception is True and configuration is invalid
        """
        warnings = self._validate()
        
        if warnings:
            if raise_exception:
                raise ValueError(f"Invalid configuration:\n" + "\n".join(warnings))
            else:
                for warning in warnings:
                    logger.warning(warning)
                return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ModelConfig':
        """Create config from dictionary."""
        # Filter out any keys that aren't in the dataclass
        valid_keys = {f.name for f in field(cls)}
        filtered_dict = {k: v for k, v in config_dict.items() if k in valid_keys}
        return cls(**filtered_dict)


def create_config(**kwargs) -> ModelConfig:
    """
    Create a simulation configuration with optional parameter overrides.
    
    Args:
        **kwargs: Configuration parameters to override defaults
        
    Returns:
        ModelConfig: The configuration object
    """
    config = ModelConfig(**kwargs)
    logger.debug(f"Created configuration with resolution {config.model_resolution}m")
    return config


def validate_config(config: ModelConfig, strict: bool = False) -> bool:
    """
    Validate a simulation configuration.
    
    Args:
        config (ModelConfig): The configuration to validate
        strict (bool): Whether to raise exceptions for invalid configs
        
    Returns:
        bool: True if configuration is valid
    """
    return config.validate(raise_exception=strict)


def save_config(config: ModelConfig, filepath: Union[str, Path]) -> None:
    """
    Save a configuration to a JSON file.
    
    Args:
        config (ModelConfig): The configuration to save
        filepath (Union[str, Path]): Path to save the configuration to
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(config.to_dict(), f, indent=2)
    
    logger.info(f"Saved configuration to {filepath}")


def load_config(filepath: Union[str, Path]) -> ModelConfig:
    """
    Load a configuration from a JSON file.
    
    Args:
        filepath (Union[str, Path]): Path to load the configuration from
        
    Returns:
        ModelConfig: The loaded configuration
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        ValueError: If the configuration file is invalid
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        config_dict = json.load(f)
    
    config = ModelConfig.from_dict(config_dict)
    logger.info(f"Loaded configuration from {filepath}")
    
    return config


def estimate_memory(
    config: ModelConfig, 
    width_cells: int, 
    height_cells: int
) -> Dict[str, Any]:
    """
    Estimate memory requirements for a forest fire simulation.
    
    Args:
        config (ModelConfig): Configuration to use for estimation
        width_cells (int): Grid width in cells
        height_cells (int): Grid height in cells
        
    Returns:
        Dict with memory estimates and tiling information
    """
    # Import calculate_memory_requirements from core_simulation_framework
    # This is the canonical implementation
    try:
        from core_simulation_framework import calculate_memory_requirements
        
        # Get memory estimates with advanced parameters
        memory_details = calculate_memory_requirements(
            grid_size=max(width_cells, height_cells),
            num_layers=config.num_layers,
            storage_optimization_level=getattr(config, 'storage_optimization_level', 2),
            store_full_states=getattr(config, 'store_full_states', False),
            use_differential_history=getattr(config, 'use_differential_history', True),
            save_interval=getattr(config, 'history_save_interval', 10)
        )
        
        # Extract total memory
        total_mb = memory_details['total']
    except (ImportError, KeyError):
        # Fallback calculation if core module not available
        total_cells = width_cells * height_cells * config.num_layers
        bytes_per_cell = config.bytes_per_cell
        total_mb = (total_cells * bytes_per_cell) / (1024 * 1024)
    
    # Populate result dictionary
    result = {
        "width_cells": width_cells,
        "height_cells": height_cells,
        "total_cells": width_cells * height_cells * config.num_layers,
        "total_mb": total_mb,
        "num_layers": config.num_layers,
        "bytes_per_cell": config.bytes_per_cell
    }
    
    # Check if tiling is needed
    if total_mb > config.memory_limit_mb:
        # Calculate the tile size that would fit into memory
        cells_per_tile = config.memory_limit_mb * (1024 * 1024) / config.bytes_per_cell
        
        # Adjust for layers to get 2D cell count
        cells_per_layer = cells_per_tile / config.num_layers
        
        # Square tile side length
        tile_side = int(math.sqrt(cells_per_layer))
        
        # Limit to configured maximum tile size
        tile_side = min(tile_side, config.tile_size)
        
        # Calculate number of tiles needed with overlap consideration
        effective_tile_size = tile_side - (2 * config.tile_overlap)
        tiles_x = math.ceil(width_cells / effective_tile_size)
        tiles_y = math.ceil(height_cells / effective_tile_size)
        
        # Calculate actual memory per tile
        actual_tile_cells = tile_side * tile_side * config.num_layers
        memory_per_tile_mb = (actual_tile_cells * config.bytes_per_cell) / (1024 * 1024)
        
        result.update({
            "tiling_required": True,
            "tile_side": tile_side,
            "tiles_x": tiles_x,
            "tiles_y": tiles_y,
            "num_tiles": tiles_x * tiles_y,
            "memory_per_tile_mb": memory_per_tile_mb,
            "effective_tile_size": effective_tile_size
        })
    else:
        result.update({
            "tiling_required": False
        })
    
    return result


def optimize_config(
    config: ModelConfig,
    width_m: float,
    height_m: float,
    max_memory_mb: Optional[int] = None
) -> ModelConfig:
    """
    Optimize a configuration for an area with specific dimensions and
    memory constraints.
    
    Args:
        config (ModelConfig): Base configuration to optimize
        width_m (float): Width of the area in meters
        height_m (float): Height of the area in meters
        max_memory_mb (Optional[int]): Maximum memory in MB, or None to use
            config.memory_limit_mb
            
    Returns:
        ModelConfig: Optimized configuration
    """
    # Create a copy of the configuration
    optimized = ModelConfig(**config.to_dict())
    
    # Use provided memory limit or default from config
    memory_limit = max_memory_mb if max_memory_mb is not None else config.memory_limit_mb
    optimized.memory_limit_mb = memory_limit
    
    # Convert physical dimensions to grid cells
    width_cells = int(width_m / optimized.model_resolution)
    height_cells = int(height_m / optimized.model_resolution)
    
    # Estimate memory requirements
    memory = estimate_memory(optimized, width_cells, height_cells)
    
    # If memory exceeds limit, try these optimizations in sequence:
    if memory["total_mb"] > memory_limit:
        logger.info(f"Memory requirements ({memory['total_mb']:.2f} MB) exceed limit ({memory_limit} MB)")
        
        # 1. First, try to enable memory optimization features
        if not hasattr(optimized, 'storage_optimization_level') or optimized.storage_optimization_level < 2:
            optimized.storage_optimization_level = 2
            optimized.use_differential_history = True
            optimized.store_full_states = False
            optimized.history_save_interval = 20
            
            # Re-estimate with optimizations
            memory = estimate_memory(optimized, width_cells, height_cells)
            logger.info(f"Applied storage optimizations: {memory['total_mb']:.2f} MB")
        
        # 2. If still exceeds, adjust resolution
        if memory["total_mb"] > memory_limit:
            original_resolution = optimized.model_resolution
            max_resolution = original_resolution * 2  # Don't increase resolution too much
            
            while (memory["total_mb"] > memory_limit and 
                   optimized.model_resolution < max_resolution):
                # Increase resolution by 0.5m increments
                optimized.model_resolution += 0.5
                
                # Recalculate grid dimensions
                width_cells = int(width_m / optimized.model_resolution)
                height_cells = int(height_m / optimized.model_resolution)
                
                # Recalculate memory
                memory = estimate_memory(optimized, width_cells, height_cells)
                
                logger.debug(f"Adjusted resolution to {optimized.model_resolution}m: {memory['total_mb']:.2f} MB")
            
            logger.info(f"Adjusted resolution from {original_resolution}m to {optimized.model_resolution}m")
        
        # 3. If still exceeds, consider reducing vertical layers
        if memory["total_mb"] > memory_limit and optimized.num_layers > 5:
            original_layers = optimized.num_layers
            min_layers = 5  # Don't go below this
            
            while (memory["total_mb"] > memory_limit and 
                   optimized.num_layers > min_layers):
                # Reduce layers by 1
                optimized.num_layers -= 1
                
                # Recalculate memory
                memory = estimate_memory(optimized, width_cells, height_cells)
                
                logger.debug(f"Reduced layers to {optimized.num_layers}: {memory['total_mb']:.2f} MB")
            
            logger.info(f"Reduced vertical layers from {original_layers} to {optimized.num_layers}")
        
        # 4. Finally, configure for tiled processing
        if memory["total_mb"] > memory_limit:
            logger.info(f"Resolution and layer adjustments insufficient, configuring for tiled processing")
            
            # Determine optimal tile size
            if not memory.get("tiling_required", False):
                # Should not happen, but just in case
                optimized.tile_size = min(optimized.tile_size, 100)
            else:
                optimized.tile_size = memory["tile_side"]
            
            # Ensure tile size is not too small
            optimized.tile_size = max(optimized.tile_size, 50)
            
            # Adjust overlap based on tile size (10% of tile size)
            optimized.tile_overlap = min(int(optimized.tile_size * 0.1), optimized.tile_overlap)
            
            logger.info(f"Optimized for tiled processing: {optimized.tile_size}x{optimized.tile_size} cells "
                       f"with {optimized.tile_overlap} cell overlap")
            
            # Enable lazy loading for tiled processing
            optimized.use_lazy_loading = True
    
    return optimized


class ConfigurationManager:
    """
    Manage configuration presets and create configurations.
    """
    
    def __init__(self, presets_file: Optional[Union[str, Path]] = None):
        """
        Initialize the configuration manager.
        
        Args:
            presets_file (Optional[Union[str, Path]]): Path to presets file
        """
        self.presets = self._get_default_presets()
        
        if presets_file:
            self.load_presets(presets_file)
    
    def _get_default_presets(self) -> Dict[str, Dict[str, Any]]:
        """
        Get default configuration presets.
        
        Returns:
            Dict[str, Dict[str, Any]]: Default presets
        """
        return {
            "default": {
                "model_resolution": 5.0,
                "num_layers": 8,
                "spread_probability": 0.3,
                "vertical_spread": 0.2,
                "wind_speed": 5.0,
                "wind_direction": 0.0,
                "tile_size": 200,
                "max_steps": 200
            },
            "high_resolution": {
                "model_resolution": 2.0,
                "num_layers": 12,
                "spread_probability": 0.28,
                "vertical_spread": 0.22,
                "wind_speed": 5.0,
                "wind_direction": 0.0,
                "tile_size": 150,
                "max_steps": 300
            },
            "large_area": {
                "model_resolution": 10.0,
                "num_layers": 6,
                "spread_probability": 0.35,
                "vertical_spread": 0.18,
                "wind_speed": 5.0,
                "wind_direction": 0.0,
                "tile_size": 300,
                "max_steps": 150
            },
            "windy_conditions": {
                "model_resolution": 5.0,
                "num_layers": 8,
                "spread_probability": 0.4,
                "vertical_spread": 0.25,
                "ember_probability": 0.08,
                "ember_distance": 8,
                "wind_speed": 12.0,
                "wind_direction": 90.0,
                "tile_size": 200,
                "max_steps": 250
            }
        }
    
    def save_presets(self, filepath: Union[str, Path]) -> None:
        """
        Save presets to a JSON file.
        
        Args:
            filepath (Union[str, Path]): Path to save presets to
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.presets, f, indent=2)
        
        logger.info(f"Saved presets to {filepath}")
    
    def load_presets(self, filepath: Union[str, Path]) -> None:
        """
        Load presets from a JSON file.
        
        Args:
            filepath (Union[str, Path]): Path to load presets from
            
        Raises:
            FileNotFoundError: If the presets file doesn't exist
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Presets file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            loaded_presets = json.load(f)
        
        # Merge with default presets (loaded presets take precedence)
        self.presets.update(loaded_presets)
        
        logger.info(f"Loaded presets from {filepath}")
    
    def add_preset(self, name: str, preset: Dict[str, Any]) -> None:
        """
        Add a preset.
        
        Args:
            name (str): Preset name
            preset (Dict[str, Any]): Preset configuration
        """
        self.presets[name] = preset
        logger.info(f"Added preset '{name}'")
    
    def remove_preset(self, name: str) -> bool:
        """
        Remove a preset.
        
        Args:
            name (str): Preset name
            
        Returns:
            bool: True if preset was removed, False if it didn't exist
        """
        if name in self.presets:
            del self.presets[name]
            logger.info(f"Removed preset '{name}'")
            return True
        return False
    
    def get_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a preset by name.
        
        Args:
            name (str): Preset name
            
        Returns:
            Optional[Dict[str, Any]]: Preset configuration or None if not found
        """
        if name not in self.presets:
            logger.warning(f"Preset '{name}' not found, returning None")
            return None
        return self.presets[name]
    
    def create_config(self, preset_name: str = "default", **kwargs) -> ModelConfig:
        """
        Create a configuration from a preset with optional overrides.
        
        Args:
            preset_name (str): Preset name
            **kwargs: Configuration parameters to override
            
        Returns:
            ModelConfig: The configuration object
            
        Raises:
            ValueError: If the preset doesn't exist
        """
        preset = self.get_preset(preset_name)
        if preset is None:
            raise ValueError(f"Preset '{preset_name}' not found")
        
        # Merge preset with overrides
        config_dict = preset.copy()
        config_dict.update(kwargs)
        
        return create_config(**config_dict)


# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Forest fire simulation configuration tools")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a configuration")
    create_parser.add_argument("--output", "-o", type=str, required=True,
                              help="Output file path")
    create_parser.add_argument("--resolution", "-r", type=float, default=5.0,
                             help="Model resolution in meters per cell")
    create_parser.add_argument("--layers", "-l", type=int, default=8,
                             help="Number of vertical layers")
    create_parser.add_argument("--wind-speed", "-ws", type=float, default=5.0,
                             help="Wind speed in m/s")
    create_parser.add_argument("--wind-direction", "-wd", type=float, default=0.0,
                             help="Wind direction in degrees (0 = north, 90 = east)")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a configuration")
    validate_parser.add_argument("--input", "-i", type=str, required=True,
                               help="Input file path")
    
    # Optimize command
    optimize_parser = subparsers.add_parser("optimize", help="Optimize a configuration")
    optimize_parser.add_argument("--input", "-i", type=str, required=True,
                               help="Input file path")
    optimize_parser.add_argument("--output", "-o", type=str, required=True,
                               help="Output file path")
    optimize_parser.add_argument("--width", "-w", type=float, required=True,
                               help="Width of the area in meters")
    optimize_parser.add_argument("--height", "-h", type=float, required=True,
                               help="Height of the area in meters")
    optimize_parser.add_argument("--memory", "-m", type=int,
                               help="Maximum memory in MB")
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command == "create":
        config = create_config(
            model_resolution=args.resolution,
            num_layers=args.layers,
            wind_speed=args.wind_speed,
            wind_direction=args.wind_direction
        )
        save_config(config, args.output)
        print(f"Created configuration and saved to {args.output}")
    
    elif args.command == "validate":
        try:
            config = load_config(args.input)
            is_valid = validate_config(config, strict=False)
            if is_valid:
                print(f"Configuration {args.input} is valid")
            else:
                print(f"Configuration {args.input} has warnings (see log)")
        except Exception as e:
            print(f"Error validating configuration: {e}")
    
    elif args.command == "optimize":
        try:
            config = load_config(args.input)
            optimized = optimize_config(
                config, 
                width_m=args.width, 
                height_m=args.height,
                max_memory_mb=args.memory
            )
            save_config(optimized, args.output)
            print(f"Optimized configuration and saved to {args.output}")
        except Exception as e:
            print(f"Error optimizing configuration: {e}")
    
    else:
        parser.print_help() 