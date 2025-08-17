#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simplified configuration management tools for forest fire simulation systems.

This module provides utilities for creating, validating, saving, and loading
simulation configurations with custom parameters.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Tuple
from dataclasses import dataclass, field, asdict, fields, MISSING

# Import standardized logger
try:
    from src.utils.logging_utils import get_logger
    logger = get_logger(__name__)
except ImportError:
    try:
        from utils.logging_utils import get_logger
        logger = get_logger(__name__)
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """
    Configuration class for forest fire simulation model.
    
    This class defines all parameters needed for the simulation, with sensible defaults.
    Using dataclass for automatic initialization, string representation, and parameter validation.
    """
    
    # === SIMULATION PARAMETERS ===
    max_steps: int = 20
    random_seed: int = 42
    debug: bool = False
    store_full_states: bool = True
    stop_when_fire_extinguished: bool = True
    
    # === GRID AND SPATIAL PARAMETERS ===
    grid_size: Union[int, Tuple[int, int]] = 100
    num_layers: int = 10
    layer_height: float = 2.0
    model_resolution: float = 5.0
    
    # === FIRE SPREAD PARAMETERS ===
    spread_probability: float = 0.4
    fuel_consumption_rate: float = 1.0
    ignition_threshold: float = 0.5
    min_fuel_value: float = 0.1
    max_fuel_value: float = 10.0
    initial_fuel_load: float = 0.0
    fuel_moisture_baseline: float = 0.3
    
    # === WEATHER PARAMETERS ===
    wind_speed: float = 5.0
    wind_direction: float = 0.0
    temperature: float = 25.0
    humidity: float = 30.0
    reference_wind_speed: float = 10.0
    wind_influence_on_spread: float = 0.5
    
    # === TERRAIN PARAMETERS ===
    slope_influence: float = 0.3
    terrain_effect_strength: float = 0.6
    barranco_threshold: float = 30.0
    barranco_amplification: float = 2.0
    barranco_direction_weight: float = 0.8
    min_depression_depth: float = 5.0
    min_depression_area: int = 4

    # === EMBER PARAMETERS ===
    ember_probability: float = 0.1
    ember_distance: int = 5
    ember_ignition: float = 0.3
    ember_height_factor: float = 0.2
    ember_rise: int = 2
    ember_wind_factor: float = 0.4

    # === MEMORY AND PERFORMANCE ===
    memory_optimization_level: int = 0
    use_disk_storage: bool = False
    use_sparse_storage: bool = True
    disk_storage_dir: str = "temp_simulation_states"
    bytes_per_cell: int = 10
    tile_size: int = 200
    chunk_size: int = 1000
    shared_terrain_info: Optional[Dict[str, Any]] = None

    # === VISUALIZATION AND OUTPUT ===
    simulation_type: str = "standard"
    output_dir: str = "results"
    results_output_dir: Optional[str] = None  # If None, uses output_dir/results  
    logs_output_dir: Optional[str] = None     # If None, uses output_dir/logs
    checkpoints_output_dir: Optional[str] = None  # If None, uses output_dir/checkpoints
    monitoring_output_dir: Optional[str] = None   # If None, uses output_dir/monitoring
    temp_storage_dir: Optional[str] = None    # If None, uses output_dir/temp
    history_keyframe_interval: int = 10
    engine_logging_interval: int = 100

    # === GEOGRAPHIC PARAMETERS ===
    geo_bounds: Optional[Tuple[float, float, float, float]] = None
    crs: str = "EPSG:32628"

    # === IGNITION PARAMETERS ===
    ignition_points: List[Tuple[int, int, int]] = field(default_factory=lambda: [(50, 50, 0)])

    # === CONFIGURATION METADATA ===
    config_name: str = "Custom_Config"
    config_version: str = "1.2"

    # === PAD PARAMETERS ===
    extinction_coefficient: float = 0.5
    pad_bin_size: float = 2.0
    exclude_ground_layer: bool = True

    # === LIDAR PARAMETERS ===
    use_lidar: bool = False
    auto_size_from_lidar: bool = False
    lidar_data_dir: Optional[str] = None
    max_grid_size: Optional[int] = None  # No grid size limit by default
    max_vegetation_height_m: float = 50.0  # Maximum realistic vegetation height in meters
    
    # === TILING AND PROCESSING ===
    use_tiling: bool = False
    use_parallel: bool = True
    tile_overlap_ratio: float = 0.1  # Overlap ratio between tiles
    
    # === FUEL LOADING ===
    fuel_load_method: str = "random"  # Options: "random", "tiled_lidar", "constant"
    
    # === VISUALIZATION ===
    save_visualizations: bool = True
    viz_frame_interval_ms: int = 200
    
    # === DIFFERENTIAL HISTORY ===
    use_differential_history: bool = False
    save_interval: int = 5
    
    # === LIDAR PROCESSING ===
    lidar_load_max_retries: int = 3
    lidar_load_retry_delay_seconds: float = 0.1

    # === TERRAIN FILE PARAMETERS ===
    use_terrain: bool = False
    dem_file: Optional[str] = "Data/DTM/Merged_DTM.tif"  # Updated to local path
    
    # === TERRAIN PREPROCESSING PARAMETERS ===
    use_preprocessed_terrain: bool = False
    preprocessed_terrain_dir: Optional[str] = None
    terrain_preprocessing_config: Optional[Dict[str, Any]] = None
    
    # === HPC Configuration Parameters ===
    hpc_io_block_size: int = 8192
    hpc_memory_limit_per_node: float = 200.0
    hpc_mode_gdal: bool = False
    gdal_cache_mb: int = 256
    gdal_thread_count: Optional[int] = None
    max_parallel_tiles: int = 10  # Maximum number of tiles to process in parallel
    reserve_cpus: int = 2  # Number of CPUs to reserve for system processes

    def __post_init__(self):
        """Post-initialization processing to setup internal state."""
        # Ensure grid_size is a tuple
        if isinstance(self.grid_size, list) and len(self.grid_size) == 2:
            self.grid_size = tuple(self.grid_size)
        elif isinstance(self.grid_size, list):
            raise ValueError(f"grid_size was a list but not of length 2: {self.grid_size}")
        elif isinstance(self.grid_size, int):
             logger.debug(f"grid_size was an int: {self.grid_size}. Converting to ({self.grid_size},{self.grid_size}).")
             self.grid_size = (self.grid_size, self.grid_size)
        elif not isinstance(self.grid_size, tuple):
            raise ValueError(f"grid_size must be a tuple or a list of two integers, got {self.grid_size} of type {type(self.grid_size)}")

        # Validate grid_size components
        if not (isinstance(self.grid_size[0], int) and self.grid_size[0] > 0 and
                  isinstance(self.grid_size[1], int) and self.grid_size[1] > 0):
            raise ValueError(f"grid_size dimensions must be positive integers, got {self.grid_size}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)
    
    def get_results_dir(self) -> Path:
        """Get the results output directory, using configured path or default subdirectory."""
        if self.results_output_dir:
            return Path(self.results_output_dir).expanduser().resolve()
        return Path(self.output_dir).expanduser().resolve() / "results"
    
    def get_logs_dir(self) -> Path:
        """Get the logs output directory, using configured path or default subdirectory."""
        if self.logs_output_dir:
            return Path(self.logs_output_dir).expanduser().resolve()
        return Path(self.output_dir).expanduser().resolve() / "logs"
    
    def get_checkpoints_dir(self) -> Path:
        """Get the checkpoints output directory, using configured path or default subdirectory."""
        if self.checkpoints_output_dir:
            return Path(self.checkpoints_output_dir).expanduser().resolve()
        return Path(self.output_dir).expanduser().resolve() / "checkpoints"
    
    def get_monitoring_dir(self) -> Path:
        """Get the monitoring output directory, using configured path or default subdirectory."""
        if self.monitoring_output_dir:
            return Path(self.monitoring_output_dir).expanduser().resolve()
        return Path(self.output_dir).expanduser().resolve() / "monitoring"
    
    def get_temp_storage_dir(self) -> Path:
        """Get the temporary storage directory, using configured path or default subdirectory."""
        if self.temp_storage_dir:
            return Path(self.temp_storage_dir).expanduser().resolve()
        return Path(self.output_dir).expanduser().resolve() / "temp"
    
    def get_output_dir(self) -> Path:
        """Get the main output directory."""
        return Path(self.output_dir).expanduser().resolve()
    
    def ensure_output_directories(self, create_dirs: bool = True) -> Dict[str, Path]:
        """
        Get all output directories and optionally create them.
        
        Args:
            create_dirs: Whether to create directories if they don't exist
            
        Returns:
            Dictionary mapping directory types to paths
        """
        directories = {
            'main_output': self.get_output_dir(),
            'results': self.get_results_dir(),
            'logs': self.get_logs_dir(),
            'checkpoints': self.get_checkpoints_dir(),
            'monitoring': self.get_monitoring_dir(),
            'temp_storage': self.get_temp_storage_dir()
        }
        
        if create_dirs:
            for dir_type, dir_path in directories.items():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Created {dir_type} directory: {dir_path}")
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not create {dir_type} directory {dir_path}: {e}")
        
        return directories
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ModelConfig':
        """Create config from dictionary, handling nested sections like terrain and vegetation."""
        valid_keys = {f.name for f in fields(cls)}
        flattened_dict = {}
        
        # Copy all top-level valid keys
        for k, v in config_dict.items():
            if k in valid_keys:
                flattened_dict[k] = v
        
        # Handle nested terrain configuration
        if 'terrain' in config_dict and isinstance(config_dict['terrain'], dict):
            terrain_mapping = {
                'use_terrain': 'use_terrain',
                'dem_file': 'dem_file', 
                'terrain_effect_strength': 'terrain_effect_strength',
                'slope_influence': 'slope_influence',
                'barranco_threshold': 'barranco_threshold',
                'barranco_amplification': 'barranco_amplification',
                'barranco_direction_weight': 'barranco_direction_weight',
                'min_depression_depth': 'min_depression_depth',
                'min_depression_area': 'min_depression_area'
            }
            for terrain_key, config_key in terrain_mapping.items():
                if terrain_key in config_dict['terrain'] and config_key in valid_keys:
                    flattened_dict[config_key] = config_dict['terrain'][terrain_key]
        
        # Handle nested vegetation configuration
        if 'vegetation' in config_dict and isinstance(config_dict['vegetation'], dict):
            vegetation_mapping = {
                'use_lidar': 'use_lidar',
                'auto_size_from_lidar': 'auto_size_from_lidar',
                'lidar_data_dir': 'lidar_data_dir',
                'extinction_coefficient': 'extinction_coefficient',
                'pad_bin_size': 'pad_bin_size',
                'exclude_ground_layer': 'exclude_ground_layer'
            }
            for veg_key, config_key in vegetation_mapping.items():
                if veg_key in config_dict['vegetation'] and config_key in valid_keys:
                    flattened_dict[config_key] = config_dict['vegetation'][veg_key]
        
        # Handle nested output configuration
        if 'output' in config_dict and isinstance(config_dict['output'], dict):
            output_mapping = {
                'output_dir': 'output_dir',
                'results_output_dir': 'results_output_dir',
                'logs_output_dir': 'logs_output_dir',
                'checkpoints_output_dir': 'checkpoints_output_dir',
                'monitoring_output_dir': 'monitoring_output_dir',
                'temp_storage_dir': 'temp_storage_dir',
                'store_full_states': 'store_full_states',
                'use_disk_storage': 'use_disk_storage',
                'checkpoint_interval': 'checkpoint_interval'
            }
            for output_key, config_key in output_mapping.items():
                if output_key in config_dict['output'] and config_key in valid_keys:
                    flattened_dict[config_key] = config_dict['output'][output_key]
        
        # Handle nested animation configuration
        if 'animation' in config_dict and isinstance(config_dict['animation'], dict):
            animation_mapping = {
                'enabled': 'save_visualizations'
            }
            for anim_key, config_key in animation_mapping.items():
                if anim_key in config_dict['animation'] and config_key in valid_keys:
                    flattened_dict[config_key] = config_dict['animation'][anim_key]
        
        return cls(**flattened_dict)


def create_config(**kwargs) -> ModelConfig:
    """
    Create a simulation configuration with optional parameter overrides.
    
    Args:
        **kwargs: Configuration parameters to override defaults
        
    Returns:
        ModelConfig: The configuration object
        
    Example:
        config = create_config(
            config_name="My_Simulation",
            model_resolution=5.0,
            grid_size=(2000, 2000),
            num_layers=15,
            wind_speed=8.0,
            wind_direction=45.0,
            max_steps=500
        )
    """
    config = ModelConfig(**kwargs)
    logger.debug(f"Created configuration '{config.config_name}' with resolution {config.model_resolution}m")
    return config


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


def validate_config(config: ModelConfig) -> Tuple[bool, List[str]]:
    """
    Validate a configuration for common issues.
    
    Args:
        config (ModelConfig): The configuration to validate
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_errors)
    """
    errors = []
    
    # Check grid size
    if isinstance(config.grid_size, tuple):
        if config.grid_size[0] <= 0 or config.grid_size[1] <= 0:
            errors.append("Grid size dimensions must be positive")
    else:
        errors.append("Grid size must be a tuple of two integers")
    
    # Check layer parameters
    if config.num_layers <= 0:
        errors.append("Number of layers must be positive")
    
    if config.layer_height <= 0:
        errors.append("Layer height must be positive")
    
    # Check model resolution
    if config.model_resolution <= 0:
        errors.append("Model resolution must be positive")
    
    # Check fuel parameters
    if config.min_fuel_value < 0:
        errors.append("Minimum fuel value cannot be negative")
    
    if config.max_fuel_value <= config.min_fuel_value:
        errors.append("Maximum fuel value must be greater than minimum fuel value")
    
    return len(errors) == 0, errors


def optimize_config(config: ModelConfig) -> ModelConfig:
    """
    Optimize configuration settings for better performance.
    
    Args:
        config (ModelConfig): The configuration to optimize
        
    Returns:
        ModelConfig: The optimized configuration
    """
    # Create a copy to avoid modifying the original
    optimized_dict = config.to_dict()
    
    # Calculate total cells
    if isinstance(config.grid_size, tuple):
        total_cells = config.grid_size[0] * config.grid_size[1] * config.num_layers
    else:
        total_cells = config.grid_size * config.grid_size * config.num_layers
    
    # Enable memory optimization for large grids
    if total_cells > 500000:
        optimized_dict['memory_optimization_level'] = max(optimized_dict['memory_optimization_level'], 1)
        logger.info("Enabled basic memory optimization for large grid")
    
    if total_cells > 2000000:
        optimized_dict['memory_optimization_level'] = max(optimized_dict['memory_optimization_level'], 2)
        optimized_dict['use_disk_storage'] = True
        logger.info("Enabled advanced memory optimization for very large grid")
    
    return ModelConfig.from_dict(optimized_dict)


# Global configuration management
_global_config: Optional[ModelConfig] = None

def get_global_config() -> Optional[ModelConfig]:
    return _global_config

def set_global_config(config: ModelConfig) -> None:
    global _global_config
    _global_config = config


if __name__ == "__main__":
    # ======================================================================
    # CONFIGURATION PARAMETERS
    # ======================================================================
    
    # Simulation parameters
    max_steps = 50
    random_seed = 42
    debug = False
    store_full_states = True
    stop_when_fire_extinguished = True
    
    # Grid and spatial parameters
    grid_size = (1000, 1000)
    num_layers = 10
    layer_height = 2.0
    model_resolution = 5.0
    
    # Fire spread parameters
    spread_probability = 0.4
    fuel_consumption_rate = 1.0
    min_fuel_value = 0.1
    max_fuel_value = 10.0
    initial_fuel_load = 0.0
    fuel_moisture_baseline = 0.3
    
    # Weather parameters
    wind_speed = 5.0
    wind_direction = 0.0
    temperature = 25.0
    humidity = 30.0
    reference_wind_speed = 10.0
    wind_influence_on_spread = 0.5
    
    # Terrain parameters
    slope_influence = 0.3
    terrain_effect_strength = 0.6
    barranco_threshold = 30.0
    barranco_amplification = 2.0
    barranco_direction_weight = 0.8
    min_depression_depth = 5.0
    min_depression_area = 4
    
    # Ember parameters
    ember_probability = 0.1
    ember_distance = 5
    ember_ignition = 0.3
    ember_height_factor = 0.2
    ember_rise = 2
    ember_wind_factor = 0.4
    
    # Memory and performance
    memory_optimization_level = 0
    use_disk_storage = False
    disk_storage_dir = "temp_simulation_states"
    bytes_per_cell = 10
    tile_size = 200
    chunk_size = 1000
    
    # Visualization and output
    simulation_type = "standard"
    output_dir = "results"
    results_output_dir = None  # If None, uses output_dir/results  
    logs_output_dir = None     # If None, uses output_dir/logs
    checkpoints_output_dir = None  # If None, uses output_dir/checkpoints
    monitoring_output_dir = None   # If None, uses output_dir/monitoring
    temp_storage_dir = None    # If None, uses output_dir/temp
    history_keyframe_interval = 10
    engine_logging_interval = 100
    
    # Geographic parameters
    geo_bounds = None
    crs = "EPSG:32628"
    
    # Ignition parameters
    ignition_points = [(500, 500, 0)]
    
    # Configuration metadata
    config_name = "Custom_Config"
    config_version = "1.2"
    
    # PAD parameters
    extinction_coefficient = 0.5
    pad_bin_size = 2.0
    exclude_ground_layer = True
    
    # LiDAR parameters
    auto_size_from_lidar = False
    lidar_data_dir = None
    max_grid_size = None
    
    # Terrain file parameters
    dem_file = "Data/DTM/Merged_DTM.tif"
    
    # HPC configuration parameters
    hpc_io_block_size = 8192
    hpc_memory_limit_per_node = 200.0
    hpc_mode_gdal = False
    gdal_cache_mb = 256
    gdal_thread_count = None
    
    # ======================================================================
    # CREATE AND SAVE CONFIGURATION
    # ======================================================================
    
    print(f"📋 Configuration: {config_name}")
    print(f"🎯 Resolution: {model_resolution}m per cell")
    print(f"📐 Grid size: {grid_size[0]} x {grid_size[1]} cells")
    print(f"📏 Physical area: {grid_size[0] * model_resolution:.0f}m x {grid_size[1] * model_resolution:.0f}m")
    print(f"🏔️  Vertical layers: {num_layers} (total height: {num_layers * layer_height:.0f}m)")
    print(f"💨 Wind: {wind_speed}m/s @ {wind_direction}°")
    print(f"🔥 Fire starts at: {ignition_points}")
    print(f"⏱️  Max steps: {max_steps}")
    print()
    
    # Create the configuration with ALL parameters
    config = create_config(
        max_steps=max_steps,
        random_seed=random_seed,
        debug=debug,
        store_full_states=store_full_states,
        stop_when_fire_extinguished=stop_when_fire_extinguished,
        grid_size=grid_size,
        num_layers=num_layers,
        layer_height=layer_height,
        model_resolution=model_resolution,
        spread_probability=spread_probability,
        fuel_consumption_rate=fuel_consumption_rate,
        min_fuel_value=min_fuel_value,
        max_fuel_value=max_fuel_value,
        initial_fuel_load=initial_fuel_load,
        fuel_moisture_baseline=fuel_moisture_baseline,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        temperature=temperature,
        humidity=humidity,
        reference_wind_speed=reference_wind_speed,
        wind_influence_on_spread=wind_influence_on_spread,
        slope_influence=slope_influence,
        terrain_effect_strength=terrain_effect_strength,
        barranco_threshold=barranco_threshold,
        barranco_amplification=barranco_amplification,
        barranco_direction_weight=barranco_direction_weight,
        min_depression_depth=min_depression_depth,
        min_depression_area=min_depression_area,
        dem_file=dem_file,
        ember_probability=ember_probability,
        ember_distance=ember_distance,
        ember_ignition=ember_ignition,
        ember_height_factor=ember_height_factor,
        ember_rise=ember_rise,
        ember_wind_factor=ember_wind_factor,
        memory_optimization_level=memory_optimization_level,
        use_disk_storage=use_disk_storage,
        disk_storage_dir=disk_storage_dir,
        bytes_per_cell=bytes_per_cell,
        tile_size=tile_size,
        chunk_size=chunk_size,
        simulation_type=simulation_type,
        output_dir=output_dir,
        results_output_dir=results_output_dir,
        logs_output_dir=logs_output_dir,
        checkpoints_output_dir=checkpoints_output_dir,
        monitoring_output_dir=monitoring_output_dir,
        temp_storage_dir=temp_storage_dir,
        history_keyframe_interval=history_keyframe_interval,
        engine_logging_interval=engine_logging_interval,
        geo_bounds=geo_bounds,
        crs=crs,
        ignition_points=ignition_points,
        config_name=config_name,
        config_version=config_version,
        extinction_coefficient=extinction_coefficient,
        pad_bin_size=pad_bin_size,
        exclude_ground_layer=exclude_ground_layer,
        auto_size_from_lidar=auto_size_from_lidar,
        lidar_data_dir=lidar_data_dir,
        max_grid_size=max_grid_size,
        hpc_io_block_size=hpc_io_block_size,
        hpc_memory_limit_per_node=hpc_memory_limit_per_node,
        hpc_mode_gdal=hpc_mode_gdal,
        gdal_cache_mb=gdal_cache_mb,
        gdal_thread_count=gdal_thread_count
    )
    
    # Create output path and save configuration
    output_path = Path(output_dir) / f"{config_name}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    save_config(config, output_path)
    
    # Calculate and display summary information
    total_cells = grid_size[0] * grid_size[1] * num_layers
    estimated_mb = (total_cells * bytes_per_cell) / (1024 * 1024)
    physical_area_km2 = (grid_size[0] * model_resolution * grid_size[1] * model_resolution) / 1_000_000
    
    print("✅ SUCCESS!")
    print(f"📁 Configuration saved to: {output_path}")
    print(f"📊 Total cells: {total_cells:,}")
    print(f"🗺️  Physical area: {physical_area_km2:.2f} km²")
    print(f"💾 Estimated memory: {estimated_mb:.1f} MB")
    if estimated_mb > 1000:
        print(f"⚠️  Large simulation - consider enabling memory optimization")
    print()
    print("🚀 Configuration ready for simulation!")