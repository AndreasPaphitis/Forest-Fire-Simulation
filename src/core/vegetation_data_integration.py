#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides functionality for integrating LiDAR-derived vegetation data with forest fire simulations.

It handles:
- Loading and preprocessing LiDAR data for use in forest fire simulations
- Calculating appropriate vegetation layers from height data
- Providing interfaces for integrating vegetation data with forest models
- Memory-efficient processing of large datasets using tiling

The TiledLiDARIntegration class represents the primary interface for this module, handling the
integration of LiDAR data with the forest model.
"""

import os
# import sys # Removed as it does not appear to be used
import numpy as np
from typing import Tuple, List, Dict, Any, Optional, Union, Set, Callable
import math
import traceback
import time
from dataclasses import fields, asdict # Added for ModelConfig introspection

# Import helpers for consistent module importing - To be replaced
# from src.utils.import_helpers import try_import, import_with_fallback # To be removed

# Set up logging using the standardized logging utils
from src.utils.logging_utils import get_logger
logger = get_logger('vegetation_data_integration')

# Import shared utilities (specific items, not defaults that are now in config)
from src.utils.shared_utilities import (
    log_once, 
    calculate_memory_requirements,
    get_progress_iterator,
    error_handler,
    # HPC_CONFIG, # Removed: HPC parameters are now in ModelConfig
    # DEFAULT_MODEL_RESOLUTION, # Removed
    # DEFAULT_LAYER_HEIGHT_METERS, # Removed
    # DEFAULT_NUM_LAYERS, # Removed
    # DEFAULT_TILE_SIZE, # Removed
    # DEFAULT_TILE_OVERLAP_RATIO, # Removed
    get_project_root
)

# Direct imports replacing import_with_fallback for utils
try:
    from src.utils.tiling_utils import TilingManager
except ImportError:
    TilingManager = None
    logger.warning("TilingManager not found from src.utils.tiling_utils. Tiling functionality will be unavailable.")
try:
    from src.utils.file_handlers import FileManager
except ImportError:
    FileManager = None
    logger.warning("FileManager not found from src.utils.file_handlers. File operations may be limited.")

# Remove HAS_UTILS flag and logic
# HAS_UTILS = all(v is not None for v in [
#     TilingManager, FileManager, LiDARDataManager # Check LiDARDataManager from this block if it was intended as a general util check
# ])

# Try to import GDAL
try:
    from osgeo import gdal, ogr, osr
    gdal.UseExceptions()  # Enable exceptions for GDAL errors
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    log_once(logger.warning, "GDAL not available - LiDAR processing functionality will be limited")

# Direct imports replacing import_with_fallback for config tools
try:
    from src.config.config_tools import get_global_config, ModelConfig
    # HAS_CONFIG = True # Replaced by direct check of imported names
except ImportError:
    get_global_config = None
    ModelConfig = None
    # HAS_CONFIG = False # Replaced
    log_once(logger.warning, "Configuration utilities (get_global_config, ModelConfig) not found from src.config.config_tools. Using default values will be problematic.")

# This specific import is critical for the class if the general one above is for a different purpose or might fail differently
from src.utils.lidar_utils import LiDARDataManager # This should be the primary one for the class member
from src.core.forest_model import ForestModel # Ensure ForestModel is imported for type hinting and instantiation

class TiledLiDARIntegration:
    """
    Class for integrating LiDAR-derived vegetation data with forest fire simulations.
    
    This class handles the efficient integration of large-scale LiDAR data into the forest fire model
    using a tile-based approach to manage memory use.
    """
    
    def __init__(
        self,
        config: Optional[Union[ModelConfig, Dict[str, Any]]] = None, # Updated signature
        forest_model: Optional[ForestModel] = None,
        **kwargs
    ):
        """
        Initialize the TiledLiDARIntegration instance.
        
        Args:
            config: ModelConfig instance or dict for central configuration.
                    If None, global configuration will be attempted.
            forest_model: Existing forest model instance, or None to create a new one.
            **kwargs: Additional parameters. Keywords matching ModelConfig fields will
                      override 'config'. Others are treated as operational parameters.
        """
        # 1. Establish base_config_dict from input 'config' or global_config
        base_config_dict = {}
        if isinstance(config, ModelConfig):
            base_config_dict = asdict(config) # Use asdict for dataclass
        elif isinstance(config, dict):
            base_config_dict = config.copy()
        elif get_global_config is not None:
            global_cfg_instance = get_global_config()
            if global_cfg_instance is not None:
                base_config_dict = asdict(global_cfg_instance)
            else:
                logger.warning("Global config instance is None. TiledLiDARIntegration will use default ModelConfig values for its base.")
        else:
            logger.warning("get_global_config utility not available. TiledLiDARIntegration will use default ModelConfig values for its base.")

        # 2. Separate kwargs into ModelConfig overrides and operational_kwargs
        self.operational_kwargs: Dict[str, Any] = {}
        if ModelConfig is not None: # Proceed if ModelConfig was successfully imported
            model_config_field_names = {f.name for f in fields(ModelConfig)}
            for key, value in kwargs.items():
                if key in model_config_field_names:
                    base_config_dict[key] = value # Override or add to config_dict
                else:
                    self.operational_kwargs[key] = value
        else: # ModelConfig is not available, treat all kwargs as operational (highly unlikely scenario)
            self.operational_kwargs = kwargs.copy()
            logger.error("ModelConfig type is not available. All kwargs treated as operational. Configuration will be default.")
        
        # 3. Create self.config as a ModelConfig instance
        if ModelConfig is not None:
            try:
                self.config = ModelConfig(**base_config_dict)
            except Exception as e:
                logger.error(f"Failed to create ModelConfig from resolved parameters: {e}. "
                             f"Parameters were: {base_config_dict}. Using a default ModelConfig instance.")
                self.config = ModelConfig() # Fallback to a default config
        else: # Should not happen if imports are correct
            logger.error("ModelConfig class not loaded. Cannot initialize TiledLiDARIntegration.config properly.")
            # Assign a placeholder or raise an error, as self.config is crucial.
            # For now, a default ModelConfig if the class itself was missing (edge case for robustness)
            # This path implies a severe setup issue.
            self.config = ModelConfig() if ModelConfig is not None else {} # type: ignore 

        self.forest_model = forest_model

        # 4. Initialize TiledLiDARIntegration attributes directly from the finalized self.config
        #    or from operational_kwargs if the parameter is not part of ModelConfig.
        self.base_dir = self.config.lidar_data_dir if hasattr(self.config, 'lidar_data_dir') else self.operational_kwargs.get('base_dir') # Fallback to operational if not in config
        self.output_dir = self.config.output_dir if hasattr(self.config, 'output_dir') else self.operational_kwargs.get('output_dir', 'output')
        self.target_resolution = self.config.model_resolution if hasattr(self.config, 'model_resolution') else self.operational_kwargs.get('target_resolution', 5.0)
        self.model_type = self.config.simulation_type if hasattr(self.config, 'simulation_type') else self.operational_kwargs.get('model_type', 'standard')
        
        # use_synthetic_data is a good candidate for an operational_kwarg if not in ModelConfig
        self.use_synthetic_data = self.operational_kwargs.get('use_synthetic_data', False)

        self.tile_size = self.config.tile_size if hasattr(self.config, 'tile_size') else 200 # Default if not in config for some reason
        self.overlap_ratio = self.config.tile_overlap_ratio if hasattr(self.config, 'tile_overlap_ratio') else 0.1
        self.overlap = int(self.tile_size * self.overlap_ratio)

        self.grid_size_limit = self.config.max_grid_size if hasattr(self.config, 'max_grid_size') else None
        self.parallel_processing = self.config.use_parallel if hasattr(self.config, 'use_parallel') else True
        self.geo_bounds = self.config.geo_bounds if hasattr(self.config, 'geo_bounds') else None # Already optional in ModelConfig
        
        config_name = getattr(self.config, 'config_name', 'Unnamed/Default Config')
        logger.info(f"TiledLiDARIntegration initialized. Effective configuration name: '{config_name}'.")
        if self.operational_kwargs:
            logger.info(f"Operational kwargs for TiledLiDARIntegration: {self.operational_kwargs}")
        
        self.project_root = get_project_root(__file__)
        
        if TilingManager is not None:
            self.tiling_manager = TilingManager(
                grid_size=(0, 0),
                tile_size=self.tile_size, # Use resolved tile_size
                overlap_ratio=self.overlap_ratio, # Use resolved overlap_ratio
                num_layers=self.config.num_layers if hasattr(self.config, 'num_layers') else 10,
                config=self.config
            )
        else:
            self.tiling_manager = None
        
        # Simpler FileManager instantiation
        # The previous complex check for 'config' in __init__.__code__.co_varnames is fragile.
        # Assuming FileManager can handle config=None or self.config is a valid ModelConfig instance.
        if FileManager is not None:
            try:
                self.file_manager = FileManager(config=self.config)
            except TypeError as e:
                logger.warning(f"FileManager could not be initialized with config: {e}. Attempting without config.")
                try:
                    self.file_manager = FileManager()
                except Exception as e_no_cfg:
                    logger.error(f"FileManager could not be initialized even without config: {e_no_cfg}")
                    self.file_manager = None
            except Exception as e_other:
                logger.error(f"Error initializing FileManager: {e_other}")
                self.file_manager = None
        else:
            self.file_manager = None

        self.lidar_processor = LiDARDataManager(config=self.config) if LiDARDataManager is not None else None
        
        if self.file_manager:
            self.file_manager.ensure_directory(self.output_dir)
        else:
            os.makedirs(self.output_dir, exist_ok=True) # Fallback direct call

        if LiDARDataManager is not None:
            self.lidar_manager = LiDARDataManager(
                base_dir=self.base_dir,
                resolution=self.target_resolution,
                layer_height=self.config.layer_height if hasattr(self.config, 'layer_height') else 2.0,
                config=self.config
            )
        else:
            self.lidar_manager = None # LiDARDataManager is essential, this path indicates a problem
            logger.error("LiDARDataManager is not available. TiledLiDARIntegration may not function correctly.")
    
    @error_handler()
    def calculate_optimal_grid_size(self, base_dir=None, target_resolution=None, grid_size_limit=None, available_memory_mb=None):
        """
        Calculate optimal grid size based on LiDAR data extent.
        Returns tuple (grid_size, geographic_bounds, actual_resolution) or raises error.
        """
        # Use config for defaults
        base_dir = base_dir or self.base_dir
        target_resolution = target_resolution or self.target_resolution
        grid_size_limit = grid_size_limit or self.grid_size_limit or getattr(self.config, 'max_grid_size', None)
        result = self.lidar_manager.calculate_optimal_grid_size(
            base_dir=base_dir,
            target_resolution=target_resolution,
            grid_size_limit=grid_size_limit,
            available_memory_mb=available_memory_mb
        )
        if result is None or not all(k in result for k in ('width', 'height', 'resolution', 'extent')):
            logger.error("Failed to calculate optimal grid size. Check your configuration and input data.")
            raise ValueError("Failed to calculate optimal grid size.")
        grid_size = (result['width'], result['height'])
        geo_bounds = result['extent']
        actual_resolution = result['resolution']
        return grid_size, geo_bounds, actual_resolution

    @error_handler(debug=False)
    def _determine_optimal_num_layers(self, base_dir):
        """
        Determine the optimal number of vertical layers based on LiDAR data.
        
        Args:
            base_dir: Directory containing LiDAR data
            
        Returns:
            Optimal number of layers based on vegetation height
        """
        # Use LiDARDataManager method
        return self.lidar_manager.determine_optimal_num_layers(base_dir)
        
    def initialize_forest_model(self):
        """Initialize the forest model with LiDAR data using a tiled approach."""
        if self.forest_model is None:
            # Directly use dimensions from self.config.
            # ModelConfig should be responsible for its own auto-sizing if auto_size_from_lidar was true.
            
            model_grid_size = self.config.grid_size
            # Ensure grid_size is a tuple if it was an int from an older config version or manual set
            if isinstance(model_grid_size, int):
                model_grid_size = (model_grid_size, model_grid_size)
            
            model_num_layers = self.config.num_layers
            actual_resolution = self.config.model_resolution
            model_geo_bounds = self.config.geo_bounds
            model_simulation_type = self.config.simulation_type # Ensure we use simulation_type from config

            # Log if any critical dimension is still None, indicating a potential config issue upstream
            if model_grid_size is None or model_num_layers is None or actual_resolution is None:
                logger.warning(f"ForestModel dimensions not fully specified in config: Grid {model_grid_size}, Layers {model_num_layers}, Res {actual_resolution}. Using ModelConfig defaults if applicable.")
                # Rely on ModelConfig defaults for any Nones passed to ForestModel constructor

            # Prepare parameters for ForestModel instantiation
            fm_init_params = {
                'grid_size': model_grid_size, # Should be a tuple
                'num_layers': model_num_layers,
                'resolution': actual_resolution, 
                'model_type': model_simulation_type, # Use simulation_type from config
                'geo_bounds': model_geo_bounds,
                'config': self.config, 
            }

            # Add operational_kwargs that ForestModel might accept and are not already in ModelConfig.
            # This assumes operational_kwargs only contains non-ModelConfig parameters by this point.
            operational_params_for_fm = {
                k: v for k, v in self.operational_kwargs.items() 
                if k not in fm_init_params # Avoid overriding keys already set from self.config
            }
            fm_init_params.update(operational_params_for_fm)
            
            logger.info(f"Initializing ForestModel with parameters from TiledLiDARIntegration: {fm_init_params}")
            self.forest_model = ForestModel(**fm_init_params)
            
            logger.info(f"ForestModel initialized using dimensions from self.config. Config name: '{self.config.config_name if hasattr(self.config, 'config_name') else 'N/A'}'")

        # Update TilingManager with definitive dimensions from ForestModel
        # Check for TilingManager existence and ForestModel initialization
        if self.tiling_manager is not None and self.forest_model is not None:
            self.tiling_manager.grid_width = self.forest_model.grid_size_x
            self.tiling_manager.grid_height = self.forest_model.grid_size_y
            self.tiling_manager.grid_size_tuple = (self.forest_model.grid_size_x, self.forest_model.grid_size_y)
            self.tiling_manager.num_layers = self.forest_model.num_layers
            
            effective_tile_size = max(1, self.tiling_manager.tile_size - self.tiling_manager.overlap)
            if effective_tile_size > 0 : # Avoid division by zero if tile_size <= overlap
                 self.tiling_manager.tiles_x = max(1, math.ceil(self.tiling_manager.grid_width / effective_tile_size))
                 self.tiling_manager.tiles_y = max(1, math.ceil(self.tiling_manager.grid_height / effective_tile_size))
            else:
                 logger.warning(f"Effective tile size is non-positive ({effective_tile_size}). Tiles_x/y calculation skipped.")
                 self.tiling_manager.tiles_x = 1
                 self.tiling_manager.tiles_y = 1

            logger.info(f"Updated TilingManager: Grid {self.tiling_manager.grid_width}x{self.tiling_manager.grid_height}, " +
                        f"Layers {self.tiling_manager.num_layers}, Tiles {self.tiling_manager.tiles_x}x{self.tiling_manager.tiles_y}")
        else:
            if self.tiling_manager is None:
                logger.warning("TilingManager not available. Cannot update TilingManager dimensions.")
            if self.forest_model is None: # This case should be less likely if the above block executed
                logger.warning("ForestModel not initialized. Cannot update TilingManager dimensions.")

        # Process tiles to load data
        # Store the result of _process_tiles to check for success
        processing_successful = self._process_tiles()
        
        if not processing_successful:
            logger.error("Tile processing failed. ForestModel fuel data may not be correctly initialized.")
            # Optionally, depending on desired behavior, you could:
            # 1. Raise an exception: raise DataProcessingError("Tile processing failed during ForestModel initialization")
            # 2. Set forest_model to None: self.forest_model = None
            # 3. Return None or an error status from this method (requires changing return type annotation)
            # For now, it logs an error, and the model will be returned potentially unpopulated.
            # The test script should verify the population of fuel_load.
            
        return self.forest_model
        
    @error_handler(debug=False)
    def _process_tiles(self):
        """
        Process all tiles in the LiDAR data.
        
        This method divides the grid into tiles, processes each tile to load LiDAR data,
        and integrates the result into the forest model.
        Returns True if processing seems to have been initiated correctly, False otherwise.
        """
        if self.forest_model is None:
            logger.error("Forest model must be initialized before processing tiles")
            # raise ValueError("Forest model must be initialized before processing tiles") # Or return False
            return False
        
        if self.tiling_manager is not None:
            if self.tiling_manager.grid_width == 0 or self.tiling_manager.grid_height == 0:
                 logger.warning(f"TilingManager grid dimensions appear uninitialized ({self.tiling_manager.grid_width}x{self.tiling_manager.grid_height}) before processing tiles. Attempting to process anyway.")
            
            checkpoint_dir = os.path.join(self.output_dir, "checkpoints")
            if self.file_manager is not None:
                self.file_manager.ensure_directory(checkpoint_dir)
            else:
                os.makedirs(checkpoint_dir, exist_ok=True)
            
            logger.info(f"Processing tiles using TilingManager.apply_function_to_tiles (Parallel: {self.parallel_processing})")
            try:
                # apply_function_to_tiles returns a dictionary of results, or raises an exception if it fails internally before calling process_func
                tile_results = self.tiling_manager.apply_function_to_tiles(
                    process_func=self._process_tile_callback,
                    parallel=self.parallel_processing
                )
                # Check if any tile processing failed (process_tile_callback returns None on error via its own error_handler or if _process_tile returns False)
                if tile_results is not None:
                    failed_tiles = [(tx, ty) for (tx, ty), result in tile_results.items() if result is None or result is False]
                    if failed_tiles:
                        logger.error(f"{len(failed_tiles)} tile(s) failed to process: {failed_tiles}")
                        return False # Indicate partial or full failure
                    logger.info("All tiles processed by TilingManager.")
                    return True # Indicate success
                else:
                    logger.error("TilingManager.apply_function_to_tiles returned None, indicating a major failure in dispatching tile processing.")
                    return False # Major failure
            except Exception as e:
                # This catches errors from apply_function_to_tiles itself (e.g., ProcessPoolExecutor issues)
                # The shared_utilities.error_handler on _process_tiles might also catch this if not handled here.
                logger.error(f"Exception during TilingManager.apply_function_to_tiles: {e}")
                logger.error(traceback.format_exc()) # Log full traceback for this specific error
                return False
            
        if self.tiling_manager is None:
            log_once(logger.warning, "TilingManager not available or not initialized. Cannot process tiles via TilingManager.")
            return False
        return False # Fallback path also indicates failure to use primary method

    def _process_tile_callback(self, tile_info):
        """Callback for processing a single tile through the tiling manager."""
        # tile_info from _execute_tile_processing_task is (tx, ty, x_start, y_start, x_end, y_end)
        try:
            tx, ty, x_start, y_start, x_end, y_end = tile_info
            # logger.debug(f"Processing tile ({tx}, {ty}) with bounds: ({x_start},{y_start})-({x_end},{y_end})") # Optional: for debugging
            result = self._process_tile(x_start, y_start, x_end, y_end, self.forest_model.num_layers)
            
            # Memory cleanup after tile processing
            import gc
            gc.collect()  # Force garbage collection
            
            # Clear GDAL cache if available
            try:
                from osgeo import gdal
                gdal.VSICurlClearCache()
            except:
                pass
            
            return result
        except ValueError as ve:
            logger.error(f"ValueError unpacking tile_info '{tile_info}' in _process_tile_callback: {ve}")
            return False # Indicate failure
        except Exception as e:
            # Log other unexpected errors during callback execution
            logger.error(f"Unexpected error in _process_tile_callback for tile_info '{tile_info}': {e}")
            logger.error(traceback.format_exc())
            return False # Indicate failure
    

    
    @error_handler()
    def _process_tile(self, x_start, y_start, x_end, y_end, num_layers):
        """
        Process a single tile and integrate LiDAR data.
        
        Args:
            x_start, y_start: Start coordinates of the tile
            x_end, y_end: End coordinates of the tile
            num_layers: Number of vertical layers
            
        Returns:
            True if processing was successful, False otherwise
        """
        # Check if forest model has fuel_load attribute
        if not hasattr(self.forest_model, 'fuel_load'):
            log_once(logger.warning, "Forest model does not have fuel_load attribute, cannot integrate LiDAR data")
            return False
        
        # Determine whether to use real or synthetic data
        if not self.use_synthetic_data:
            # Attempt to load LiDAR data for this tile
            tile_data = self._load_lidar_data_for_tile(x_start, y_start, x_end, y_end, num_layers)
            
            if tile_data is not None:
                # Handle both old list format and new dict format from _load_lidar_data_for_tile
                if isinstance(tile_data, dict):
                    # New approach with resampled_pad_data_to_model_grid (returns dict of layers)
                    for layer_idx, layer_data_2d in tile_data.items():
                        if layer_idx >= num_layers:
                            logger.warning(f"Layer index {layer_idx} exceeds num_layers {num_layers}, skipping")
                            continue
                            
                        if layer_data_2d is not None:
                            # PAD data is already normalized fuel values (0-1 range)
                            fuel_data_2d = layer_data_2d
                            
                            if fuel_data_2d is not None:
                                slice_width = x_end - x_start
                                slice_height = y_end - y_start
                                
                                # Check if shapes match and use safe tile setting method
                                if fuel_data_2d.shape == (slice_height, slice_width):
                                    # Already in correct orientation (height, width)
                                    data_to_set = fuel_data_2d.T
                                elif fuel_data_2d.shape == (slice_width, slice_height):
                                    # In (width, height) orientation
                                    data_to_set = fuel_data_2d
                                else:
                                    logger.warning(f"Shape mismatch for tile layer {layer_idx}, attempting resize...")
                                    data_to_set = None
                                
                                # Use safe tile setting method if available (for sparse storage)
                                if data_to_set is not None:
                                    if hasattr(self.forest_model, 'set_fuel_load_tile'):
                                        self.forest_model.set_fuel_load_tile(x_start, x_end, y_start, y_end, layer_idx, data_to_set)
                                    else:
                                        # Fallback to regular array slicing for non-sparse models
                                        self.forest_model.fuel_load[x_start:x_end, y_start:y_end, layer_idx] = data_to_set
                                else:
                                    logger.warning(f"Shape mismatch for tile ({x_start},{y_start})-({x_end},{y_end}) layer {layer_idx}. " +
                                                    f"Fuel load slice expects ({slice_width},{slice_height}), got {fuel_data_2d.shape}. Attempting resizing.")
                                    
                                    try:
                                        # Try to resize the data to match the expected shape
                                        from scipy.ndimage import zoom
                                        zoom_factor_x = slice_width / fuel_data_2d.shape[0]
                                        zoom_factor_y = slice_height / fuel_data_2d.shape[1]
                                        resized_data = zoom(fuel_data_2d, (zoom_factor_x, zoom_factor_y), order=1)
                                        
                                        # Double-check the resized shape
                                        if resized_data.shape == (slice_width, slice_height):
                                            self.forest_model.fuel_load[x_start:x_end, y_start:y_end, layer_idx] = resized_data
                                            logger.info(f"Successfully resized layer {layer_idx} data to match tile dimensions")
                                        else:
                                            logger.warning(f"Resized data still has incorrect shape: {resized_data.shape}, skipping layer {layer_idx}")
                                    except Exception as e:
                                        logger.error(f"Error during resizing of layer {layer_idx}: {e}")
                                        continue
                else:
                    # Legacy approach with list of arrays
                    for z, layer_data_2d in enumerate(tile_data):
                        if layer_data_2d is not None:
                            # PAD data is already normalized fuel values (0-1 range)
                            fuel_data_2d = layer_data_2d
                            
                            if fuel_data_2d is not None:
                                slice_width = x_end - x_start
                                slice_height = y_end - y_start

                                if fuel_data_2d.shape == (slice_height, slice_width):
                                    data_to_set = fuel_data_2d.T
                                elif fuel_data_2d.shape == (slice_width, slice_height):
                                    # This case implies layer_data_2d is already (width, height) for the tile
                                    data_to_set = fuel_data_2d
                                else:
                                    logger.warning(f"Shape mismatch for legacy tile layer {z}")
                                    continue
                                
                                # Use safe tile setting method if available
                                if hasattr(self.forest_model, 'set_fuel_load_tile'):
                                    self.forest_model.set_fuel_load_tile(x_start, x_end, y_start, y_end, z, data_to_set)
                                else:
                                    self.forest_model.fuel_load[x_start:x_end, y_start:y_end, z] = data_to_set
                return True
        
        # If no LiDAR data, use fallback initialization
        logger.warning(f"No LiDAR data available for tile ({x_start},{y_start})-({x_end},{y_end}), using default fuel values")
        self._initialize_tile_with_default_fuel(x_start, y_start, x_end, y_end, num_layers)
        return True
        
    @error_handler(debug=False)
    def _load_lidar_data_for_tile(self, x_start, y_start, x_end, y_end, num_layers):
        """
        Load LiDAR data for a specific tile using the improved resampling method.
        
        Args:
            x_start, y_start: Start coordinates of the tile
            x_end, y_end: End coordinates of the tile
            num_layers: Number of vertical layers
            
        Returns:
            Dictionary mapping layer numbers to resampled data arrays, or None if loading fails
        """
        # Store reference to the LiDAR manager
        lidar_manager = getattr(self, 'lidar_manager', None)
        if lidar_manager is None:
            # Try to create a LiDAR manager if not already present
            try:
                self.lidar_manager = LiDARDataManager(
                    base_dir=self.base_dir,
                    resolution=self.target_resolution,
                    config=self.config
                )
                lidar_manager = self.lidar_manager
                logger.info(f"Created LiDARDataManager for base_dir: {self.base_dir}")
            except Exception as e:
                logger.error(f"Failed to create LiDARDataManager: {e}")
                return None
                
        # Check if we're using the PAD structure with height-based layers
        pad_dir = self.base_dir
        if not os.path.exists(pad_dir):
            logger.error(f"PAD directory does not exist: {pad_dir}")
            return None
            
        # Prepare the model grid parameters for this tile
        # Get the geographic extent of this tile if geo_bounds is available
        model_grid_extent = None
        if self.geo_bounds is not None:
            # Calculate the subtile geographic extent
            full_grid_width, full_grid_height = self.forest_model.grid_size
            geo_min_x, geo_min_y, geo_max_x, geo_max_y = self.geo_bounds
            
            # Calculate geographic coordinates for this tile
            tile_min_x = geo_min_x + (x_start / full_grid_width) * (geo_max_x - geo_min_x)
            tile_max_x = geo_min_x + (x_end / full_grid_width) * (geo_max_x - geo_min_x)
            tile_min_y = geo_min_y + (y_start / full_grid_height) * (geo_max_y - geo_min_y)
            tile_max_y = geo_min_y + (y_end / full_grid_height) * (geo_max_y - geo_min_y)
            
            model_grid_extent = (tile_min_x, tile_min_y, tile_max_x, tile_max_y)
            logger.info(f"Tile geographic extent: {model_grid_extent}")
        else:
            # Use the entire LiDAR extent as fallback
            try:
                model_grid_extent = lidar_manager.get_lidar_extent(pad_dir)
                if model_grid_extent is None:
                    logger.warning("Could not determine LiDAR extent. Falling back to legacy loading method.")
                    return self._legacy_load_lidar_data_for_tile(x_start, y_start, x_end, y_end, num_layers)
            except Exception as e:
                logger.error(f"Error getting LiDAR extent: {e}")
                return None
                
        # Detect all available PAD layers and their files
        available_layers = lidar_manager._detect_available_layers(pad_dir)
        
        if not available_layers:
            logger.info(f"No PAD files found in {pad_dir}")
            logger.info("No LiDAR data available - creating bare area with default fuel")
            return self._create_bare_area_data(x_start, y_start, x_end, y_end, num_layers)
        
        # Use available layers up to the requested num_layers
        # Note: Layer 0 is excluded, so we start from layer 1
        num_available_layers = len(available_layers)  # Use count of available layers, not max index
        actual_layers_to_use = min(num_layers, num_available_layers)
        
        logger.info(f"Using {actual_layers_to_use} layers (requested: {num_layers}, available: {num_available_layers}, max layer index: {max_available_layer}, excluding layer 0)")
        
        # Create pad_files_dict with available layers (starting from layer 1)
        pad_files_dict = {}
        for layer in range(1, actual_layers_to_use + 1):  # Start from layer 1, exclude layer 0
            if layer in available_layers:
                pad_files_dict[layer - 1] = available_layers[layer]  # Map layer 1->0, layer 2->1, etc.
                logger.info(f"Layer {layer - 1} (height {layer * 2}m): {len(available_layers[layer])} files")
            else:
                logger.warning(f"No PAD files found for layer {layer} (height {layer * 2}m)")
                # Create empty layer for missing data
                pad_files_dict[layer - 1] = []
            
        # Use the new resampling method with robust error handling
        model_grid_size = (x_end - x_start, y_end - y_start)
        try:
            logger.info(f"Attempting to resample {len(pad_files_dict)} layers for tile ({x_start},{y_start})-({x_end},{y_end})")
            
            resampled_layers = lidar_manager.resample_pad_data_to_model_grid(
                pad_files_dict=pad_files_dict,
                model_grid_extent=model_grid_extent,
                model_grid_size=model_grid_size,
                model_resolution=self.target_resolution,
                nodata_value=0.0  # Use 0 as no-data value for fuel
            )
            
            if not resampled_layers:
                logger.warning("No layers were successfully resampled.")
                logger.info("No vegetation data available - creating bare area with default fuel")
                return self._create_bare_area_data(x_start, y_start, x_end, y_end, num_layers)
                
            logger.info(f"Successfully resampled {len(resampled_layers)} layers for tile ({x_start},{y_start})-({x_end},{y_end})")
            return resampled_layers
            
        except Exception as e:
            logger.error(f"Error resampling PAD data for tile ({x_start},{y_start})-({x_end},{y_end}): {e}")
            logger.info("LiDAR processing failed - creating bare area with default fuel")
            return self._create_bare_area_data(x_start, y_start, x_end, y_end, num_layers)
    
    def _legacy_load_lidar_data_for_tile(self, x_start, y_start, x_end, y_end, num_layers):
        """
        Legacy method to load LiDAR data for a specific tile using direct in-memory processing.
        This serves as a fallback if the new resampling method fails.
        
        Args:
            x_start, y_start: Start coordinates of the tile
            x_end, y_end: End coordinates of the tile
            num_layers: Number of vertical layers
            
        Returns:
            List of numpy arrays with fuel data for each layer, or None if loading fails
        """
        tile_data = []
        lidar_manager = getattr(self, 'lidar_manager', None)
        
        if lidar_manager is None:
            logger.error("LiDARDataManager not available for legacy loading")
            return None
            
        # Use values from config
        max_retries = getattr(self.config, 'lidar_load_max_retries', 3)
        retry_delay_seconds = getattr(self.config, 'lidar_load_retry_delay_seconds', 0.1)

        for z in range(num_layers):
            layer_file = os.path.join(self.base_dir, f"layer_{z:02d}.tif")
            file_found = False
            
            for attempt in range(max_retries + 1): # +1 to include initial attempt
                if os.path.exists(layer_file):
                    file_found = True
                    if attempt > 0: # Log if found on a retry
                        logger.info(f"LiDAR layer file {layer_file} found on attempt {attempt + 1}/{max_retries + 1}.")
                    break
                elif attempt < max_retries: # If not found and retries are left
                    logger.warning(f"LiDAR layer file not found: {layer_file}. Attempt {attempt + 1}/{max_retries + 1}. Retrying in {retry_delay_seconds}s...")
                    time.sleep(retry_delay_seconds)
                # If it's the last attempt and file is still not found, the outer 'if file_found:' will handle it
            
            if file_found:
                # Load the raster data for this tile
                data = lidar_manager.load_raster_data(
                    file_path=layer_file
                )
                if data is not None:
                    # Crop to the tile if needed
                    # Ensure bounds are within data shape
                    y_max = min(y_end, data.shape[0])
                    x_max = min(x_end, data.shape[1])
                    y_min = min(y_start, y_max) # Ensure y_min isn't greater than y_max if y_start > y_max
                    x_min = min(x_start, x_max) # Ensure x_min isn't greater than x_max if x_start > x_max
                    
                    # Ensure slice indices are valid (height, width)
                    actual_y_start = min(y_min, y_max)
                    actual_y_end = max(y_min, y_max)
                    actual_x_start = min(x_min, x_max)
                    actual_x_end = max(x_min, x_max)

                    # Check if the slice is valid before attempting
                    if actual_y_start < actual_y_end and actual_x_start < actual_x_end:
                        data_tile = data[actual_y_start:actual_y_end, actual_x_start:actual_x_end]
                        tile_data.append(data_tile)
                    else:
                        logger.warning(f"Invalid slice dimensions for {layer_file} on tile ({x_start},{y_start})-({x_end},{y_end}). " +
                                       f"Calculated slice: y({actual_y_start}:{actual_y_end}), x({actual_x_start}:{actual_x_end}). Appending None.")
                        tile_data.append(None)
                else:
                    logger.warning(f"Failed to load raster data for {layer_file} (load_raster_data returned None). Appending None.")
                    tile_data.append(None)
            else:
                # File still not found after all retries
                logger.warning(f"LiDAR layer file not found after {max_retries + 1} attempts: {layer_file}. Appending None.")
                tile_data.append(None)

        if all(d is None for d in tile_data):
            logger.info("No LiDAR data loaded for tile - creating bare area with default fuel")
            return self._create_bare_area_data(x_start, y_start, x_end, y_end, num_layers)
        return tile_data

    def _initialize_with_synthetic_data(self):
        # Original implementation
        # ...
        pass
        
    def _initialize_tile_with_default_fuel(self, x_start, y_start, x_end, y_end, num_layers):
        """
        Initialize a tile with default fuel values when LiDAR data is not available.
        
        Args:
            x_start, y_start: Start coordinates of the tile
            x_end, y_end: End coordinates of the tile
            num_layers: Number of vertical layers
        """
        try:
            # Get default fuel value from config
            default_fuel = getattr(self.config, 'initial_fuel_load', 5.0) if self.config else 5.0
            
            # Create fuel data for each layer
            tile_width = x_end - x_start
            tile_height = y_end - y_start
            
            for z in range(num_layers):
                # Create uniform fuel distribution with slight variation by layer
                layer_fuel_modifier = 1.0 - (z * 0.1)  # Decrease fuel with height
                layer_fuel_modifier = max(0.1, layer_fuel_modifier)  # Minimum 10% fuel
                
                fuel_data = np.full((tile_width, tile_height), 
                                  default_fuel * layer_fuel_modifier, 
                                  dtype=np.float32)
                
                # Set fuel data in the forest model
                if hasattr(self.forest_model, 'set_fuel_load_tile'):
                    self.forest_model.set_fuel_load_tile(x_start, x_end, y_start, y_end, z, fuel_data)
                else:
                    self.forest_model.fuel_load[x_start:x_end, y_start:y_end, z] = fuel_data
                    
            logger.info(f"Initialized tile ({x_start},{y_start})-({x_end},{y_end}) with default fuel values")
            
        except Exception as e:
            logger.error(f"Failed to initialize tile with default fuel: {e}")
            raise

    def _create_bare_area_data(self, x_start, y_start, x_end, y_end, num_layers):
        """
        Create bare area data with default fuel for areas with no LiDAR data.
        
        This method creates layers with default fuel values when no PAD data is available,
        ensuring fire can still spread in areas without LiDAR coverage.
        
        Args:
            x_start, y_start: Start coordinates of the tile
            x_end, y_end: End coordinates of the tile
            num_layers: Number of vertical layers
            
        Returns:
            List of numpy arrays with default fuel data for each layer
        """
        try:
            tile_width = x_end - x_start
            tile_height = y_end - y_start
            
            # Get default fuel value from config
            default_fuel = getattr(self.config, 'initial_fuel_load', 5.0) if self.config else 5.0
            
            # Create default fuel data for each layer (not zero!)
            bare_area_layers = []
            for z in range(num_layers):
                # Create array filled with default fuel (not zero)
                layer_data = np.full((tile_width, tile_height), default_fuel, dtype=np.float32)
                bare_area_layers.append(layer_data)
                
            logger.info(f"Created bare area data for tile ({x_start},{y_start})-({x_end},{y_end}) with {num_layers} layers using default fuel {default_fuel}")
            return bare_area_layers
            
        except Exception as e:
            logger.error(f"Failed to create bare area data for tile ({x_start},{y_start})-({x_end},{y_end}): {e}")
            return None