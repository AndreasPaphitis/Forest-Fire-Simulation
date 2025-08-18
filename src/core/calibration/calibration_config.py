#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Calibration Configuration Module

This module extends the existing ModelConfig system with calibration-specific
configuration options, methods, and validation logic.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import json
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Tuple
from dataclasses import dataclass, field, asdict

from src.config.config_tools import ModelConfig, load_config, save_config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CalibrationMethod(Enum):
    """Available calibration methods."""
    GRID_SEARCH = "grid_search"
    SENSITIVITY_ANALYSIS = "sensitivity_analysis"


class CalibrationObjective(Enum):
    """Available calibration objectives."""
    SPATIAL_SIMILARITY = "spatial_similarity"
    FIRE_BEHAVIOR = "fire_behavior"
    CUSTOM = "custom"


@dataclass
class CalibrationTarget:
    """Configuration for calibration target data."""
    fire_perimeter_path: str = ""
    fire_progression_data: Optional[str] = None
    observed_fire_behavior: Optional[Dict[str, Any]] = None
    target_metrics: Dict[str, float] = field(default_factory=dict)
    weight: float = 1.0


@dataclass
class CalibrationConfig:
    """
    Configuration class for calibration experiments.
    
    This class extends the base ModelConfig with calibration-specific parameters
    and methods for managing calibration experiments.
    """
    
    # === BASE SIMULATION CONFIG ===
    base_config: Optional[ModelConfig] = None
    
    # === CALIBRATION METHOD ===
    method: CalibrationMethod = CalibrationMethod.GRID_SEARCH
    objective: CalibrationObjective = CalibrationObjective.SPATIAL_SIMILARITY
    
    # === PARAMETER SELECTION ===
    calibration_parameters: List[str] = field(default_factory=lambda: [
        # ✅ COMPLETE LIST OF IMPLEMENTED PARAMETERS - Updated based on thorough analysis
        # Core Fire Mechanics
        'spread_probability',      # ✅ Used in base probability calculation (line 906)
        'fuel_consumption_rate',   # ✅ Used in fuel consumption (line 824)
        'ignition_threshold',      # ✅ Used in ignition check (line 1050)
        
        # Environmental Interactions  
        'wind_influence_on_spread', # ✅ Used in wind factor calculation (line 990)
        'slope_influence',         # ✅ Used in slope factor calculation (line 1114)
        
        # Ember Mechanics
        'ember_probability',       # ✅ Used in ember generation (line 1250)
        'ember_distance',          # ✅ Used in ember landing (line 1284, 1401)
        'ember_ignition',          # ✅ Used in ember ignition (line 1374)
        'ember_height_factor',     # ✅ Used in ember height calculation (line 1254)
        'ember_wind_factor',       # ✅ Used in ember wind strength (line 1301)
        'ember_rise'               # ✅ Used in ember height change (line 1314)
        
        # ❌ REMOVED UNIMPLEMENTED PARAMETERS:
        # 'terrain_effect_strength' - NOT IMPLEMENTED in simulation engine
        # 'barranco_amplification' - NOT IMPLEMENTED in simulation engine  
        # 'barranco_direction_weight' - NOT IMPLEMENTED in simulation engine
        # 'wind_speed' - Only used in ember calculations, not main fire spread
        # 'wind_direction' - Only used in ember calculations, not main fire spread
    ])
    
    # === CALIBRATION TARGETS ===
    calibration_targets: List[CalibrationTarget] = field(default_factory=list)
    
    # === OPTIMIZATION SETTINGS ===
    max_iterations: int = 100
    convergence_tolerance: float = 1e-6
    cross_validation_folds: int = 5
    
    # === GRID SEARCH SETTINGS ===
    grid_search_points: int = 5  # Points per parameter dimension
    grid_search_method: str = "uniform"  # uniform, log_uniform, custom
    
    # === OBJECTIVE FUNCTION WEIGHTS ===
    spatial_similarity_weight: float = 0.6
    fire_behavior_weight: float = 0.4
    jaccard_weight: float = 0.4
    dice_weight: float = 0.3
    sorensen_weight: float = 0.3
    
    # === VALIDATION SETTINGS ===
    validation_split: float = 0.2
    test_split: float = 0.1
    stratify_by_fire_size: bool = True
    
    # === OUTPUT SETTINGS ===
    results_dir: str = "calibration_results"
    save_intermediate_results: bool = True
    save_all_simulations: bool = False
    generate_plots: bool = True
    verbose: bool = True
    
    # === PERFORMANCE SETTINGS ===
    parallel_execution: bool = True
    max_workers: int = 28  # Default to 28 for HPC consistency
    memory_limit_gb: float = 8.0
    simulation_timeout_minutes: float = 30.0
    
    # === SHARED TERRAIN CONFIGURATION ===
    shared_terrain_info: Optional[Dict[str, Any]] = None  # CRITICAL: Shared terrain data for memory efficiency
    
    # === GEOGRAPHIC AND LIDAR CONFIGURATION ===
    # Geographic bounds for simulation area [min_x, min_y, max_x, max_y]
    geo_bounds: Optional[Tuple[float, float, float, float]] = None
    # Coordinate reference system (e.g., "EPSG:25828" for Tenerife)
    crs: str = "EPSG:32628"
    # Model resolution in meters per grid cell
    model_resolution: float = 5.0
    
    # LiDAR data configuration
    use_lidar_data: bool = False
    lidar_data_dir: Optional[str] = None
    auto_size_from_lidar: bool = False
    extinction_coefficient: float = 0.5
    pad_bin_size: float = 2.0
    exclude_ground_layer: bool = True
    max_vegetation_height_m: float = 50.0
    
    # Terrain file parameters
    use_terrain: bool = True  # Changed from False to True - terrain effects are essential for realistic fire simulation
    dem_file: Optional[str] = "Data/DTM/Merged_DTM.tif"
    use_preprocessed_terrain: bool = True  # Changed from False to True - use preprocessed terrain by default
    preprocessed_terrain_dir: Optional[str] = "/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain"  # HPC path for preprocessed terrain
    
    # Memory and processing for LiDAR calibration
    tile_size: int = 200
    tile_overlap_ratio: float = 0.1
    memory_optimization_level: int = 0
    max_parallel_tiles: int = 10
    
    # === EXPERIMENT METADATA ===
    experiment_name: str = "calibration_experiment"
    experiment_description: str = ""
    experiment_tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize and validate configuration after creation."""
        # Create base config if not provided
        if self.base_config is None:
            self.base_config = ModelConfig()
            logger.info("Created default base configuration for calibration")
        
        # Ensure results directory exists
        self.results_dir = Path(self.results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate the calibration configuration."""
        errors = []
        
        # Validate method is implemented
        implemented_methods = [CalibrationMethod.GRID_SEARCH, CalibrationMethod.SENSITIVITY_ANALYSIS]
        if self.method not in implemented_methods:
            errors.append(f"Calibration method {self.method.value} is not implemented. "
                         f"Available methods: {[m.value for m in implemented_methods]}")
        
        # Validate method-specific settings
        if self.method == CalibrationMethod.GRID_SEARCH and self.grid_search_points < 2:
            errors.append("Grid search requires at least 2 points per parameter")
        
        # Validate calibration parameters
        if not self.calibration_parameters:
            errors.append("At least one calibration parameter must be specified")
        
        # Validate reasonable parameter count
        if len(self.calibration_parameters) > 10:
            logger.warning(f"Large number of parameters ({len(self.calibration_parameters)}) may lead to slow calibration")
        

        
        # Validate calibration targets
        if not self.calibration_targets:
            logger.warning("No calibration targets specified - using synthetic validation")
        
        # Validate file paths in targets
        for i, target in enumerate(self.calibration_targets):
            if target.fire_perimeter_path and not os.path.exists(target.fire_perimeter_path):
                errors.append(f"Fire perimeter file not found for target {i}: {target.fire_perimeter_path}")
        
        # Validate splits
        total_split = self.validation_split + self.test_split
        if total_split >= 1.0:
            errors.append(f"Validation + test split must be < 1.0, got {total_split}")
        
        # Validate LiDAR configuration
        if self.use_lidar_data:
            if not self.lidar_data_dir:
                errors.append("lidar_data_dir must be specified when use_lidar_data is True")
            elif not os.path.exists(self.lidar_data_dir):
                errors.append(f"LiDAR data directory not found: {self.lidar_data_dir}")
            
            if self.model_resolution <= 0:
                errors.append("model_resolution must be positive")
            
            if self.tile_size <= 0:
                errors.append("tile_size must be positive")
            
            if not (0.0 <= self.tile_overlap_ratio <= 1.0):
                errors.append("tile_overlap_ratio must be between 0.0 and 1.0")
        
        # Validate terrain configuration
        if self.use_terrain:
            # Check if using preprocessed terrain
            if hasattr(self, 'use_preprocessed_terrain') and self.use_preprocessed_terrain:
                if not self.preprocessed_terrain_dir:
                    errors.append("preprocessed_terrain_dir must be specified when use_preprocessed_terrain is True")
                elif not os.path.exists(self.preprocessed_terrain_dir):
                    # TEMPORARY: Allow missing preprocessed terrain directory for testing
                    logger.warning(f"Preprocessed terrain directory not found: {self.preprocessed_terrain_dir}")
                    logger.warning("Continuing without terrain validation for testing purposes")
            else:
                # Legacy DEM file validation (only if not using preprocessed terrain)
                if not self.dem_file:
                    errors.append("dem_file must be specified when use_terrain is True and not using preprocessed terrain")
                elif not os.path.exists(self.dem_file):
                    # TEMPORARY: Allow missing DEM file for testing
                    logger.warning(f"DEM file not found: {self.dem_file}")
                    logger.warning("Continuing without terrain validation for testing purposes")
        
        # Validate geographic bounds if provided
        if self.geo_bounds is not None:
            if len(self.geo_bounds) != 4:
                errors.append("geo_bounds must be a tuple of 4 values (min_x, min_y, max_x, max_y)")
            else:
                min_x, min_y, max_x, max_y = self.geo_bounds
                if min_x >= max_x:
                    errors.append("geo_bounds: min_x must be less than max_x")
                if min_y >= max_y:
                    errors.append("geo_bounds: min_y must be less than max_y")
        
        if errors:
            error_msg = "Calibration configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
        
        logger.info("Calibration configuration validation passed")
    
    def get_base_config(self) -> ModelConfig:
        """Get the base simulation configuration."""
        return self.base_config
    
    def create_config_variant(self, parameter_values: Dict[str, Any]) -> ModelConfig:
        """
        Create a simulation configuration with modified parameter values.
        
        Args:
            parameter_values: Dictionary of parameter names and values to modify
            
        Returns:
            ModelConfig instance with modified parameters
        """
        # Create a copy of the base config
        config_dict = asdict(self.base_config)
        
        # Update with new parameter values
        for param_name, param_value in parameter_values.items():
            if param_name in self.calibration_parameters:
                config_dict[param_name] = param_value
            else:
                logger.warning(f"Parameter {param_name} not in calibration parameters list")
        
        # Override with calibration-specific geographic and LiDAR settings if provided
        if self.geo_bounds is not None:
            config_dict['geo_bounds'] = self.geo_bounds
        if self.crs:
            config_dict['crs'] = self.crs
        if self.model_resolution:
            config_dict['model_resolution'] = self.model_resolution
        if self.use_lidar_data:
            config_dict['auto_size_from_lidar'] = self.auto_size_from_lidar
            config_dict['lidar_data_dir'] = self.lidar_data_dir
            config_dict['extinction_coefficient'] = self.extinction_coefficient
            config_dict['pad_bin_size'] = self.pad_bin_size
            config_dict['exclude_ground_layer'] = self.exclude_ground_layer
            config_dict['max_vegetation_height_m'] = self.max_vegetation_height_m
            config_dict['tile_size'] = self.tile_size
            config_dict['tile_overlap_ratio'] = self.tile_overlap_ratio
            config_dict['memory_optimization_level'] = self.memory_optimization_level
            config_dict['max_parallel_tiles'] = self.max_parallel_tiles
        if self.use_terrain:
            config_dict['dem_file'] = self.dem_file
            config_dict['use_preprocessed_terrain'] = self.use_preprocessed_terrain
            config_dict['preprocessed_terrain_dir'] = self.preprocessed_terrain_dir
        
        # Create new ModelConfig instance
        try:
            new_config = ModelConfig(**config_dict)
            
            # CRITICAL FIX: Pass shared terrain info from calibration config to worker config
            if self.shared_terrain_info is not None:
                new_config.shared_terrain_info = self.shared_terrain_info
                logger.debug(f"✅ Passing shared terrain info to worker config")
            elif hasattr(self.base_config, 'shared_terrain_info') and self.base_config.shared_terrain_info:
                new_config.shared_terrain_info = self.base_config.shared_terrain_info
                logger.debug(f"✅ Passing shared terrain info from base config to worker config")
            else:
                logger.debug(f"⚠️  No shared terrain info available for worker config")
            
            return new_config
            
        except Exception as e:
            logger.error(f"Error creating config variant: {e}")
            raise
    
    def add_calibration_target(self, 
                             fire_perimeter_path: str,
                             weight: float = 1.0,
                             fire_progression_data: Optional[str] = None,
                             target_metrics: Optional[Dict[str, float]] = None) -> None:
        """
        Add a calibration target to the configuration.
        
        Args:
            fire_perimeter_path: Path to fire perimeter data (shapefile or GeoTIFF)
            weight: Weight for this target in multi-target calibration
            fire_progression_data: Optional path to temporal fire progression data
            target_metrics: Optional target values for specific metrics
        """
        target = CalibrationTarget(
            fire_perimeter_path=fire_perimeter_path,
            fire_progression_data=fire_progression_data,
            target_metrics=target_metrics or {},
            weight=weight
        )
        
        self.calibration_targets.append(target)
        logger.info(f"Added calibration target: {fire_perimeter_path}")
    
    def get_calibration_parameter_names(self) -> List[str]:
        """Get the list of parameters to be calibrated."""
        return self.calibration_parameters.copy()
    
    @property
    def grid_size(self) -> Optional[Tuple[int, int]]:
        """Get grid size from base_config."""
        if self.base_config is not None:
            return getattr(self.base_config, 'grid_size', None)
        return None
    
    @property
    def num_layers(self) -> Optional[int]:
        """Get number of layers from base_config."""
        if self.base_config is not None:
            return getattr(self.base_config, 'num_layers', None)
        return None
    
    def set_calibration_parameters(self, parameter_names: List[str]) -> None:
        """
        Set the list of parameters to be calibrated.
        
        Args:
            parameter_names: List of parameter names to calibrate
        """
        # Validate that parameters exist in base config
        base_config_dict = asdict(self.base_config)
        invalid_params = [p for p in parameter_names if p not in base_config_dict]
        
        if invalid_params:
            raise ValueError(f"Invalid calibration parameters: {invalid_params}")
        
        self.calibration_parameters = parameter_names
        logger.info(f"Set calibration parameters: {parameter_names}")
    
    def save_config(self, filepath: Union[str, Path]) -> None:
        """
        Save the calibration configuration to a JSON file.
        
        Args:
            filepath: Path to save the configuration
        """
        filepath = Path(filepath)
        
        # Convert to dictionary for serialization
        config_dict = asdict(self)
        
        # Handle enum serialization
        config_dict['method'] = self.method.value
        config_dict['objective'] = self.objective.value
        
        # Handle base_config serialization
        if self.base_config:
            config_dict['base_config'] = asdict(self.base_config)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
        
        logger.info(f"Saved calibration configuration to {filepath}")
    
    @classmethod
    def load_config(cls, filepath: Union[str, Path]) -> 'CalibrationConfig':
        """
        Load calibration configuration from a JSON file.
        
        Args:
            filepath: Path to the configuration file
            
        Returns:
            CalibrationConfig instance
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        
        # Handle enum deserialization
        if 'method' in config_dict:
            config_dict['method'] = CalibrationMethod(config_dict['method'])
        if 'objective' in config_dict:
            config_dict['objective'] = CalibrationObjective(config_dict['objective'])
        
        # Handle base_config deserialization
        if 'base_config' in config_dict and config_dict['base_config']:
            config_dict['base_config'] = ModelConfig(**config_dict['base_config'])
        
        # Handle calibration targets
        if 'calibration_targets' in config_dict:
            targets = []
            for target_dict in config_dict['calibration_targets']:
                targets.append(CalibrationTarget(**target_dict))
            config_dict['calibration_targets'] = targets
        
        logger.info(f"Loaded calibration configuration from {filepath}")
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config_dict = asdict(self)
        config_dict['method'] = self.method.value
        config_dict['objective'] = self.objective.value
        return config_dict
    
    def summary(self) -> str:
        """Generate a summary string of the calibration configuration."""
        summary_lines = [
            f"Calibration Configuration: {self.experiment_name}",
            f"Method: {self.method.value}",
            f"Objective: {self.objective.value}",
            f"Parameters to calibrate ({len(self.calibration_parameters)}): {', '.join(self.calibration_parameters)}",
            f"Number of targets: {len(self.calibration_targets)}",
            f"Max iterations: {self.max_iterations}",
            f"Parallel execution: {self.parallel_execution} (workers: {self.max_workers})",
            f"Results directory: {self.results_dir}",
        ]
        
        if self.method == CalibrationMethod.GRID_SEARCH:
            total_combinations = self.grid_search_points ** len(self.calibration_parameters)
            summary_lines.append(f"Grid search points per parameter: {self.grid_search_points}")
            summary_lines.append(f"Total parameter combinations: {total_combinations}")
        
        # Add LiDAR and geographic configuration summary
        if self.use_lidar_data:
            summary_lines.append(f"LiDAR data: {self.lidar_data_dir}")
            summary_lines.append(f"Model resolution: {self.model_resolution}m")
            if self.geo_bounds:
                summary_lines.append(f"Geographic bounds: {self.geo_bounds}")
            summary_lines.append(f"CRS: {self.crs}")
            summary_lines.append(f"Tile size: {self.tile_size}")
        
        if self.use_terrain:
            summary_lines.append(f"Terrain data: {self.dem_file}")
        
        return "\n".join(summary_lines)


def create_default_calibration_config(
    experiment_name: str = "default_calibration",
    method: CalibrationMethod = CalibrationMethod.GRID_SEARCH,
    base_config: Optional[ModelConfig] = None
) -> CalibrationConfig:
    """
    Create a default calibration configuration.
    
    Args:
        experiment_name: Name for the calibration experiment
        method: Calibration method to use
        base_config: Base simulation configuration (uses default if None)
        
    Returns:
        CalibrationConfig instance with sensible defaults
    """
    if base_config is None:
        base_config = ModelConfig()
    
    config = CalibrationConfig(
        experiment_name=experiment_name,
        method=method,
        base_config=base_config,
        objective=CalibrationObjective.SPATIAL_SIMILARITY
    )
    
    logger.info(f"Created default calibration configuration: {experiment_name}")
    return config


def create_calibration_from_production_config(
    production_config_path: Union[str, Path],
    experiment_name: str = "lidar_calibration",
    method: CalibrationMethod = CalibrationMethod.GRID_SEARCH,
    calibration_parameters: Optional[List[str]] = None
) -> CalibrationConfig:
    """
    Create a calibration configuration from an existing production configuration file.
    
    This allows you to use the same geographic bounds, LiDAR data sources, and 
    simulation settings as your production runs for calibration.
    
    Args:
        production_config_path: Path to existing production configuration JSON file
        experiment_name: Name for the calibration experiment
        method: Calibration method to use
        calibration_parameters: List of parameters to calibrate (uses defaults if None)
        
    Returns:
        CalibrationConfig instance configured for LiDAR data use
        
    Example:
        config = create_calibration_from_production_config(
            production_config_path="hpc_deployment/Forest_Fire_Simulation_production_test.json",
            experiment_name="tenerife_calibration",
            calibration_parameters=['fuel_consumption_rate', 'terrain_effect_strength']
        )
    """
    production_config_path = Path(production_config_path)
    
    if not production_config_path.exists():
        raise FileNotFoundError(f"Production config file not found: {production_config_path}")
    
    # Load the production configuration
    with open(production_config_path, 'r') as f:
        prod_config_dict = json.load(f)
    
    # Create base ModelConfig from production settings
    base_config = ModelConfig.from_dict(prod_config_dict)
    
    # Set default calibration parameters if not provided
    if calibration_parameters is None:
            calibration_parameters = [
                'wind_influence_on_spread',
                'fuel_consumption_rate',
                'terrain_effect_strength',
                'barranco_amplification',
                'barranco_direction_weight',
                'slope_influence',
                'ember_height_factor',
                'wind_speed',
                'wind_direction',
                'ember_distance',
                'ember_probability',
                'ember_ignition',
                'ember_generation'
            ]
    
    # Extract key configuration elements from production config
    use_lidar = prod_config_dict.get('vegetation', {}).get('use_lidar', False)
    lidar_data_dir = prod_config_dict.get('vegetation', {}).get('lidar_data_dir')
    use_terrain = prod_config_dict.get('terrain', {}).get('use_terrain', False)
    dem_file = prod_config_dict.get('terrain', {}).get('dem_file')
    
    # Create calibration configuration
    calib_config = CalibrationConfig(
        experiment_name=experiment_name,
        method=method,
        base_config=base_config,
        calibration_parameters=calibration_parameters,
        
        # Geographic and spatial settings from production config
        geo_bounds=base_config.geo_bounds,
        crs=base_config.crs,
        model_resolution=base_config.model_resolution,
        
        # LiDAR configuration from production config
        use_lidar_data=use_lidar,
        lidar_data_dir=lidar_data_dir,
        auto_size_from_lidar=base_config.auto_size_from_lidar,
        extinction_coefficient=base_config.extinction_coefficient,
        pad_bin_size=base_config.pad_bin_size,
        exclude_ground_layer=base_config.exclude_ground_layer,
        max_vegetation_height_m=base_config.max_vegetation_height_m,
        
        # Terrain configuration from production config
        use_terrain=use_terrain,
        dem_file=dem_file,
        
        # Processing settings from production config (HPC section)
        tile_size=prod_config_dict.get('hpc', {}).get('tile_size', 200),
        tile_overlap_ratio=prod_config_dict.get('hpc', {}).get('tile_overlap_ratio', 0.1),
        memory_optimization_level=prod_config_dict.get('hpc', {}).get('memory_optimization_level', 0),
        max_parallel_tiles=prod_config_dict.get('hpc', {}).get('max_parallel_tiles', 10),
        
        # Calibration-specific settings
        results_dir=f"calibration_results/{experiment_name}",
        grid_search_points=5,  # Conservative for initial calibration
        max_workers=4,  # Conservative for calibration
        verbose=True
    )
    
    logger.info(f"Created calibration configuration from production config: {production_config_path}")
    logger.info(f"LiDAR data enabled: {use_lidar}")
    logger.info(f"Terrain data enabled: {use_terrain}")
    logger.info(f"Geographic bounds: {base_config.geo_bounds}")
    
    return calib_config


if __name__ == "__main__":
    # Example usage
    print("Creating example calibration configuration...")
    
    # Create a calibration config
    calib_config = create_default_calibration_config(
        experiment_name="example_calibration",
        method=CalibrationMethod.GRID_SEARCH
    )
    
    # Print summary
    print(calib_config.summary())
    
    # Save and load example
    calib_config.save_config("example_calibration_config.json")
    loaded_config = CalibrationConfig.load_config("example_calibration_config.json")
    
    print("Configuration saved and loaded successfully!") 