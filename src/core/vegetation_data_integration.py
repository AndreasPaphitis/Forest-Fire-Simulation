"""
Vegetation Data Integration Module

This module provides functionality for integrating LiDAR-derived vegetation data with forest fire simulations.
It implements a tiled approach for efficient memory management when processing large-scale geographic areas,
allowing high-resolution forest fire simulations with realistic 3D vegetation structure.

PURPOSE:
This module serves as the bridge between pre-processed vegetation structural data and the forest fire
simulation engine. It handles the critical task of efficiently integrating large-scale, spatially-explicit
vegetation data into the simulation framework while managing memory constraints that would otherwise limit
the scale and resolution of simulations.

KEY CAPABILITIES:
- Tiled approach for memory-efficient handling of large geographic areas
- Integration of terrain data (DEM) with vegetation structure
- Optimized memory management techniques for high-resolution simulations
- Conversion between geographic and grid coordinates
- Calculation of vertical connectivity between forest layers based on vegetation structure

INTEGRATION WITH OTHER MODULES:
- Depends on core_simulation_framework.py for base class definitions and utility functions
- Provides processed vegetation data to fire_simulation_engine.py for fire behavior simulation
- Called by simulation_runner.py when initializing simulation environments

The TiledLiDARIntegration class represents the primary interface for this module, handling the
efficient integration of vegetation data with strict memory management for resource-constrained systems.

Resolution Handling:
- The target_resolution parameter specifies the desired cell size in meters
- Unlike traditional approaches, resolution is maintained for large areas by creating more tiles
- Grid size is calculated by dividing geographic extent by resolution
- Memory requirements scale quadratically with resolution changes

Tiling Parameters:
- tile_size: Number of grid cells per tile (not meters)
- overlap: Number of overlapping grid cells between adjacent tiles (not meters)
- For example: At 5m resolution, a tile_size of 100 = 500m×500m physical area

Memory Management:
- Memory usage (MB) ≈ (grid_size² × num_layers × 5 bytes) / (1024 × 1024)
- Layer grouping processes vertical structure in manageable chunks
- Super-tiling enables hierarchical processing for very large areas

Author: Andreas Paphitis
Date: 2025
Version: 1.1
"""

import os
import sys
import glob
import logging
import time
import numpy as np
import json
import pickle
import math
import traceback
import functools
from typing import List, Dict, Tuple, Optional, Union, Callable, Any
from osgeo import gdal, osr
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.cm as cm
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import re
from skimage.transform import resize

# Import base model and shared functionality
try:
    # Import from the centralized base module
    from core_simulation_framework import (
        BaseForestModel, CellState, ModelConfig,
        calculate_memory_requirements, get_progress_iterator, error_handler
    )
    
    # Get module-specific configuration
    config = ModelConfig.get_module_config('lidar_integration')
    
    # Extract configuration values
    MODEL_RESOLUTION = config['MODEL_RESOLUTION']
    LAYER_HEIGHT_METERS = config['LAYER_HEIGHT_METERS']
    DEFAULT_NUM_LAYERS = config['DEFAULT_NUM_LAYERS']
    MIN_FUEL_VALUE = config['MIN_FUEL_VALUE']
    MAX_FUEL_VALUE = config['MAX_FUEL_VALUE']
    DEFAULT_TILE_SIZE = config['DEFAULT_TILE_SIZE']
    DEFAULT_TILE_OVERLAP = config['DEFAULT_TILE_OVERLAP']
    MAX_GRID_SIZE = config['MAX_GRID_SIZE']
    BYTES_PER_CELL = config['BYTES_PER_CELL']
    
    BASE_MODEL_IMPORTED = True
    logger = logging.getLogger(__name__)
    
except ImportError:
    # Fall back to default values if base module is not available
    logging.warning("Could not import core_simulation_framework, using fallback values")
    MODEL_RESOLUTION = 5.0
    LAYER_HEIGHT_METERS = 2.0
    DEFAULT_NUM_LAYERS = 10
    MIN_FUEL_VALUE = 0.1
    MAX_FUEL_VALUE = 10.0
    DEFAULT_TILE_SIZE = 100
    DEFAULT_TILE_OVERLAP = 10
    MAX_GRID_SIZE = 1000
    BYTES_PER_CELL = 15
    BASE_MODEL_IMPORTED = False
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Simple stand-in for error_handler
    def error_handler(func=None, debug=False):
        if func is None:
            def decorator(f):
                def wrapper(*args, **kwargs):
                    try:
                        return f(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Error in {f.__name__}: {str(e)}")
                        if debug:
                            logger.error(traceback.format_exc())
                        raise
                return wrapper
            return decorator
        
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                if debug:
                    logger.error(traceback.format_exc())
                raise
        return wrapper
    
    # Use the get_progress_iterator from BaseModule if available
    def get_progress_iterator(iterable, desc=None, **kwargs):
        try:
            from tqdm import tqdm
            return tqdm(iterable, desc=desc, **kwargs)
        except ImportError:
            # Simple progress indicator
            print(f"Processing {desc}...")
            return iterable

# Use the unified model creation system
def _import_forest_model():
    """
    Import the ForestModel class using the factory method from the base module.
    
    Returns:
        ForestModel class if successful, BaseForestModel as fallback
    """
    try:
        # Try to import BaseForestModel
        from core_simulation_framework import BaseForestModel
        # Try to use the factory method
        return BaseForestModel.create_model(model_type='full')
    except (ImportError, AttributeError):
        # If that fails, try direct import
        try:
            from fire_simulation_engine import ForestModel
            return ForestModel
        except ImportError:
            logger.warning("Could not import ForestModel, using fallback")
            # Create a minimal stub implementation
            class MinimalForestModelStub:
                def __init__(self, grid_size=100, num_layers=DEFAULT_NUM_LAYERS, 
                             layer_height_meters=LAYER_HEIGHT_METERS):
                    """Minimal forest model stub for integration testing."""
                    if isinstance(grid_size, tuple):
                        self.grid_size_x, self.grid_size_y = grid_size
                    else:
                        self.grid_size_x = self.grid_size_y = grid_size
                    
                    self.grid_size = max(self.grid_size_x, self.grid_size_y)
                    self.num_layers = num_layers
                    self.layer_height_meters = layer_height_meters
                    
                    # Basic state arrays
                    self.fuel_load = np.zeros((self.grid_size_x, self.grid_size_y, num_layers), dtype=np.float32)
                    self.vertical_connectivity = np.ones((self.grid_size_x, self.grid_size_y, num_layers), dtype=np.float32) * 0.5
                    self.MIN_FUEL_VALUE = MIN_FUEL_VALUE
                    self.MAX_FUEL_VALUE = MAX_FUEL_VALUE
                
                def set_ignition(self, x, y, z=0):
                    """Stub for setting ignition points."""
                    logger.info(f"Setting ignition at ({x}, {y}, {z}) [STUB]")
                
                def run_simulation(self, max_steps=100, store_full_states=False):
                    """Stub for running simulation."""
                    logger.info(f"Running simulation for {max_steps} steps [STUB]")
                    return {"steps": 0, "burned_cells": 0, "max_fire_extent": 0}
                
                def calculate_vertical_connectivity(self):
                    """Stub for vertical connectivity calculation."""
                    if BASE_MODEL_IMPORTED:
                        # Use the base implementation if available
                        try:
                            from core_simulation_framework import BaseForestModel
                            BaseForestModel.calculate_vertical_connectivity(self)
                        except:
                            pass
                    return self.vertical_connectivity
            
            return MinimalForestModelStub

class TiledLiDARIntegration:
    """
    Integration framework for LiDAR-derived vegetation data with forest fire simulations.
    
    This class efficiently processes large geographic areas by dividing them into manageable tiles,
    each with a portion of the overall simulation space. It handles memory constraints through
    tiling strategies and layer grouping.
    """
    
    def __init__(self, forest_model, base_dir: str, 
                tile_size: int = DEFAULT_TILE_SIZE, 
                overlap: int = DEFAULT_TILE_OVERLAP,
                debug: bool = False):
        """
        Initialize the integration framework.
        
        Args:
            forest_model: The forest model instance to populate
            base_dir: Base directory containing PAD/fuel raster files
            tile_size: Size of each processing tile in grid cells (not meters)
            overlap: Overlap between tiles in grid cells (not meters)
            debug: Whether to enable debug output
        """
        self.forest_model = forest_model
        self.base_dir = os.path.abspath(base_dir)
        self.tile_size = tile_size
        self.overlap = overlap
        self.debug = debug
        
        # Get core dimensions from forest model
        self.grid_size = forest_model.grid_size
        self.num_layers = forest_model.num_layers
        self.layer_height_meters = forest_model.layer_height_meters
        
        # Initialize tracking variables
        self.geo_bounds = None  # Will be populated during initialization
        self.reset_stats()
        
        # Validate base directory
        if not os.path.exists(self.base_dir):
            raise ValueError(f"Base directory does not exist: {self.base_dir}")
        
        logger.info(f"Initialized TiledLiDARIntegration with base_dir: {self.base_dir}")
        logger.info(f"Forest model grid size: {self.grid_size}x{self.grid_size}")
        logger.info(f"Number of layers: {self.num_layers}")
        logger.info(f"Tile size: {self.tile_size} grid cells")
        logger.info(f"Overlap: {self.overlap} grid cells")
    
    def reset_stats(self):
        """Reset the integration statistics."""
        self.stats = {
            'num_tiles': 0,
            'num_rasters': 0,
            'cells_populated': 0,
            'used_rasters': 0,
            'empty_tiles': 0,
            'processing_time': 0
        }
    
    @staticmethod
    @error_handler
    def calculate_optimal_grid_size(base_dir: str, target_resolution: float = None, 
                                  grid_size_limit: int = None,
                                  interactive: bool = True) -> Tuple[int, Tuple[float, float, float, float], float]:
        """
        Calculate optimal grid size based on geographic extent and target resolution.
        
        Args:
            base_dir: Base directory containing raster files
            target_resolution: Desired spatial resolution in meters per cell
            grid_size_limit: Maximum allowed grid size (default: None = no limit)
            interactive: Whether to interactively prompt for resolution choices
            
        Returns:
            Tuple of (grid_size, geo_bounds, resolution)
        """
        # Default values
        if target_resolution is None:
            target_resolution = MODEL_RESOLUTION
        
        if grid_size_limit is None:
            grid_size_limit = MAX_GRID_SIZE
        
        # Create a temporary integration object
        temp_integ = TiledLiDARIntegration(
            forest_model=type('obj', (object,), {
                'grid_size': 100, 
                'num_layers': DEFAULT_NUM_LAYERS,
                'layer_height_meters': LAYER_HEIGHT_METERS
            }),
            base_dir=base_dir
        )
        
        # Estimate geographic bounds
        geo_bounds = temp_integ._estimate_simulation_geographic_bounds()
        if not geo_bounds:
            raise ValueError("Could not determine geographic bounds from raster files")
        
        x_min, y_min, x_max, y_max = geo_bounds
        x_extent = x_max - x_min
        y_extent = y_max - y_min
        
        # Calculate grid size based on extent and resolution
        grid_width = int(np.ceil(x_extent / target_resolution))
        grid_height = int(np.ceil(y_extent / target_resolution))
        grid_size = max(grid_width, grid_height)
        
        logger.info(f"Geographic extent: {x_extent:.1f}m x {y_extent:.1f}m")
        logger.info(f"Target resolution: {target_resolution:.1f}m per cell")
        logger.info(f"Calculated grid size: {grid_width} x {grid_height} cells")
        
        # Check if grid size exceeds limit
        if grid_size > grid_size_limit:
            warning_msg = (
                f"WARNING: Calculated grid size ({grid_size}) exceeds recommended limit ({grid_size_limit}).\n"
                f"This would require approximately {calculate_memory_requirements(grid_size, DEFAULT_NUM_LAYERS)['total']:.1f} MB of memory.\n"
            )
            logger.warning(warning_msg)
            
            if interactive:
                # Offer alternative resolutions
                print(warning_msg)
                resolution = select_resolution_interactive(
                    geo_bounds, 
                    suggested_resolutions=[5.0, 10.0, 20.0, 50.0],
                    num_layers=DEFAULT_NUM_LAYERS
                )
                
                # Recalculate grid size with selected resolution
                grid_width = int(np.ceil(x_extent / resolution))
                grid_height = int(np.ceil(y_extent / resolution))
                grid_size = max(grid_width, grid_height)
                target_resolution = resolution
                
                logger.info(f"Using selected resolution: {resolution:.1f}m per cell")
                logger.info(f"New grid size: {grid_width} x {grid_height} cells")
            else:
                # Auto-adjust resolution to fit within limit
                scaling_factor = grid_size / grid_size_limit
                adjusted_resolution = target_resolution * scaling_factor
                
                # Round to nearest 0.5
                adjusted_resolution = np.ceil(adjusted_resolution * 2) / 2
                
                grid_width = int(np.ceil(x_extent / adjusted_resolution))
                grid_height = int(np.ceil(y_extent / adjusted_resolution))
                grid_size = max(grid_width, grid_height)
                target_resolution = adjusted_resolution
                
                logger.warning(f"Auto-adjusted resolution to {adjusted_resolution:.1f}m per cell")
                logger.warning(f"New grid size: {grid_width} x {grid_height} cells")
        
        # Calculate actual grid size (may be rectangular)
        grid_size = (grid_width, grid_height)
        
        # Return grid size, geographic bounds, and final resolution
        return grid_size, geo_bounds, target_resolution
    
    @classmethod
    @error_handler
    def create_model_from_rasters(cls, base_dir: str, target_resolution: float = MODEL_RESOLUTION,
                                 num_layers: int = 40, grid_size: tuple = None,
                                 tile_size: int = DEFAULT_TILE_SIZE, 
                                 overlap: int = DEFAULT_TILE_OVERLAP,
                                 debug: bool = False):
        """
        Create and initialize a forest model from PAD rasters.
        
        Args:
            base_dir: Base directory containing PAD/fuel raster files
            target_resolution: Desired spatial resolution in meters per cell
            num_layers: Number of vertical layers
            grid_size: Optional explicit grid size (if None, calculated from rasters)
            tile_size: Size of each processing tile in grid cells
            overlap: Overlap between tiles in grid cells
            debug: Whether to enable debug output
            
        Returns:
            Initialized forest model instance
        """
        logger.info(f"Creating forest model from rasters in {base_dir}")
        
        # Calculate optimal grid size if not provided
        if grid_size is None:
            grid_size, geo_bounds, actual_resolution = cls.calculate_optimal_grid_size(
                base_dir, target_resolution, interactive=True
            )
            if actual_resolution != target_resolution:
                logger.info(f"Using resolution {actual_resolution:.1f}m instead of requested {target_resolution:.1f}m")
                target_resolution = actual_resolution
        
        # Ensure grid_size is a tuple
        if isinstance(grid_size, int):
            grid_size = (grid_size, grid_size)
        
        # Get ForestModel class
        ForestModel = _import_forest_model()
        
        # Create forest model
        logger.info(f"Creating forest model with grid size {grid_size[0]}x{grid_size[1]}, {num_layers} layers")
        forest_model = ForestModel(
            grid_size=grid_size,
            num_layers=num_layers,
            layer_height_meters=LAYER_HEIGHT_METERS
        )
        
        # Create tiled integration
        integration = cls(
            forest_model=forest_model,
            base_dir=base_dir,
            tile_size=tile_size,
            overlap=overlap,
            debug=debug
        )
        
        # Initialize tiled environment
        integration.initialize_tiled_environment()
        
        # Calculate vertical connectivity
        logger.info("Calculating vertical connectivity based on vegetation structure")
        forest_model.calculate_vertical_connectivity()
        
        logger.info("Forest model creation complete")
        return forest_model
        
    @error_handler
    def initialize_tiled_environment(self):
        """
        Initialize the forest model using tiled processing for memory efficiency.
        
        This method divides the forest model grid into manageable tiles, processes each tile
        independently, and then combines the results. This approach dramatically reduces peak
        memory usage compared to processing the entire grid at once.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        start_time = time.time()
        logger.info("Initializing tiled environment...")
        
        # Create tile grid
        tiles = self._create_tile_grid()
        logger.info(f"Created {len(tiles)} tiles")
        self.stats['num_tiles'] = len(tiles)
        
        # Find raster files
        all_raster_files = self._find_all_raster_files()
        logger.info(f"Found {len(all_raster_files)} raster files")
        self.stats['num_rasters'] = len(all_raster_files)
        
        # Assign rasters to tiles
        tiles = self._assign_rasters_to_tiles(tiles, all_raster_files)
        tiles_with_rasters = sum(1 for tile in tiles if tile['rasters'])
        logger.info(f"{tiles_with_rasters}/{len(tiles)} tiles have assigned rasters")
        
        # Initialize all tiles
        self._initialize_all_tiles(tiles)
        
        # Blend overlapping regions
        self._blend_tile_overlaps(tiles)
        
        # Calculate processing time
        total_time = time.time() - start_time
        self.stats['processing_time'] = total_time
        
        # Log statistics
        logger.info(f"Tiled initialization complete in {total_time:.1f} seconds")
        logger.info(f"Used {self.stats['used_rasters']}/{len(all_raster_files)} raster files")
        logger.info(f"Populated {self.stats['cells_populated']} cells")
        logger.info(f"Empty tiles: {self.stats['empty_tiles']}")
        
        return True
    
    @error_handler
    def process_region_with_layer_groups(self, region_bounds, layer_group_size=10):
        """
        Process a region using layer grouping for memory efficiency.
        
        This method divides the vertical layers into manageable groups (e.g., 10 layers per group),
        processing each group sequentially. This dramatically reduces peak memory usage while
        maintaining high vertical resolution.
        
        Args:
            region_bounds: Tuple (start_x, start_y, end_x, end_y) defining region
            layer_group_size: Number of layers to process in each group
            
        Returns:
            Dict with processing statistics
        """
        start_time = time.time()
        
        # Get region bounds
        start_x, start_y, end_x, end_y = region_bounds
        region_width = end_x - start_x
        region_height = end_y - start_y
        
        # Validate layer group size
        layer_group_size = min(layer_group_size, self.num_layers)
        
        # Divide layers into groups
        num_groups = math.ceil(self.num_layers / layer_group_size)
        layer_groups = []
        for i in range(num_groups):
            start_layer = i * layer_group_size
            end_layer = min((i + 1) * layer_group_size, self.num_layers)
            layer_groups.append((start_layer, end_layer))
        
        logger.info(f"Processing region with dimensions {region_width}x{region_height}")
        logger.info(f"Using {num_groups} layer groups of size {layer_group_size}")
        
        # Initialize statistics
        stats = {
            'processed_layer_groups': 0,
            'total_cells_processed': 0,
            'processing_time_seconds': 0
        }
        
        # Process each layer group
        for group_idx, (start_layer, end_layer) in enumerate(layer_groups):
            logger.info(f"Processing layer group {group_idx+1}/{num_groups}: layers {start_layer}-{end_layer-1}")
            
            # Determine tiles that cover this region
            tiles = self._create_tiles_for_region(region_bounds)
            
            # We need to process each tile for this layer group
            for tile_idx, tile in enumerate(tiles):
                tile_start_x = tile['start_x']
                tile_start_y = tile['start_y']
                tile_end_x = tile['end_x']
                tile_end_y = tile['end_y']
                
                # Initialize model for this tile
                forest_model = self._create_forest_model_for_tile(tile)
                tile['forest_model'] = forest_model
                
                # Find rasters that overlap this tile
                raster_files = self._find_rasters_for_tile(tile)
                tile['raster_files'] = raster_files
                
                # Process only the layers in this group
                for z in range(start_layer, end_layer):
                    # Find raster file for this layer
                    layer_idx = z  # Map layer index to raster file index
                    
                    if layer_idx < len(raster_files) and raster_files[layer_idx]:
                        raster_path = raster_files[layer_idx]
                        logger.debug(f"Loading layer {z} from {os.path.basename(raster_path)}")
                        
                        # Load and process raster for this layer
                        self._load_and_process_raster(
                            raster_path=raster_path,
                            target_layer=z,
                            tile_bounds=(tile_start_x, tile_start_y, tile_end_x, tile_end_y),
                            forest_model=forest_model
                        )
                        
                        # Track cells processed
                        tile_cells = (tile_end_x - tile_start_x) * (tile_end_y - tile_start_y)
                        stats['total_cells_processed'] += tile_cells
                
                # Calculate vertical connectivity for this tile if we've processed the last layer group
                if group_idx == num_groups - 1:
                    self._calculate_vertical_connectivity_for_tile(tile)
                
                # Transfer data to global forest model
                self._transfer_tile_data_to_model(
                    tile,
                    layer_range=(start_layer, end_layer)
                )
            
            stats['processed_layer_groups'] += 1
        
        # Calculate total processing time
        stats['processing_time_seconds'] = time.time() - start_time
        
        logger.info(f"Processed {stats['processed_layer_groups']} layer groups in {stats['processing_time_seconds']:.1f} seconds")
        logger.info(f"Total cells processed: {stats['total_cells_processed']}")
        
        return stats
    
    def _create_tiles_for_region(self, region_bounds):
        """
        Create tiles that cover the specified region.
        
        Args:
            region_bounds: Tuple (start_x, start_y, end_x, end_y) defining region
            
        Returns:
            List of tile dictionaries with bounds information
        """
        start_x, start_y, end_x, end_y = region_bounds
        
        # Calculate number of tiles needed
        region_width = end_x - start_x
        region_height = end_y - start_y
        
        num_tiles_x = math.ceil(region_width / (self.tile_size - self.overlap))
        num_tiles_y = math.ceil(region_height / (self.tile_size - self.overlap))
        
        # Create tiles
        tiles = []
        
        for j in range(num_tiles_y):
            for i in range(num_tiles_x):
                # Calculate tile bounds with overlap
                tile_start_x = start_x + i * (self.tile_size - self.overlap)
                tile_start_y = start_y + j * (self.tile_size - self.overlap)
                
                # Ensure tiles don't exceed region bounds
                tile_end_x = min(tile_start_x + self.tile_size, end_x)
                tile_end_y = min(tile_start_y + self.tile_size, end_y)
                
                # Create tile dictionary
                tile = {
                    'index': (i, j),
                    'start_x': tile_start_x,
                    'start_y': tile_start_y,
                    'end_x': tile_end_x,
                    'end_y': tile_end_y,
                }
                
                tiles.append(tile)
        
        logger.info(f"Created {len(tiles)} tiles for region")
        return tiles
    
    def _create_forest_model_for_tile(self, tile):
        """
        Create a forest model instance for a specific tile.
        
        Args:
            tile: Tile dictionary with bounds information
            
        Returns:
            Forest model instance
        """
        # Import forest model on demand
        ForestModel = _import_forest_model()
        
        # Calculate tile dimensions
        tile_width = tile['end_x'] - tile['start_x']
        tile_height = tile['end_y'] - tile['start_y']
        
        # Create forest model for this tile
        forest_model = ForestModel(
            grid_size=(tile_width, tile_height),
            num_layers=self.num_layers,
            layer_height_meters=self.layer_height_meters
        )
        
        return forest_model
    
    def _transfer_tile_data_to_model(self, tile, layer_range=None):
        """
        Transfer data from a tile's forest model to the main model.
        
        Args:
            tile: Tile dictionary with forest model
            layer_range: Optional tuple (start_layer, end_layer) to transfer only a range of layers
        """
        if 'forest_model' not in tile:
            return
        
        # Extract tile bounds and forest model
        tile_start_x = tile['start_x']
        tile_start_y = tile['start_y']
        tile_end_x = tile['end_x']
        tile_end_y = tile['end_y']
        tile_model = tile['forest_model']
        
        # Determine layer range to transfer
        if layer_range:
            start_layer, end_layer = layer_range
        else:
            start_layer, end_layer = 0, self.num_layers
        
        # Transfer fuel load data for the specified layers
        for z in range(start_layer, end_layer):
            # Calculate source and target dimensions
            source_width = tile_end_x - tile_start_x
            source_height = tile_end_y - tile_start_y
            
            # Source is the tile model's fuel load data
            source_data = tile_model.fuel_load[:source_width, :source_height, z]
            
            # Target is the main model's fuel load data at the corresponding position
            self.forest_model.fuel_load[tile_start_x:tile_end_x, tile_start_y:tile_end_y, z] = source_data
        
        # If we're transferring all layers, also transfer vertical connectivity
        if layer_range is None or (layer_range[0] == 0 and layer_range[1] == self.num_layers):
            # Transfer vertical connectivity data
            for z in range(1, self.num_layers):  # Skip first layer (no connectivity below)
                source_connectivity = tile_model.vertical_connectivity[:source_width, :source_height, z]
                self.forest_model.vertical_connectivity[tile_start_x:tile_end_x, tile_start_y:tile_end_y, z] = source_connectivity
    
    def _calculate_vertical_connectivity_for_tile(self, tile):
        """
        Calculate vertical connectivity between layers based on PAD values.
        
        This method uses the PAD-derived fuel values to create a 3D connectivity array
        that represents how easily fire can spread vertically between layers based on
        vegetation structure.
        
        Args:
            tile: Dictionary containing tile data and forest model
        """
        forest_model = tile.get('forest_model')
        if forest_model is None:
            return
        
        # Use the base implementation if available
        if BASE_MODEL_IMPORTED:
            try:
                # Try to use the base model's implementation
                forest_model.calculate_vertical_connectivity()
                logger.info(f"Calculated vertical connectivity for tile based on PAD values using base implementation")
                return
            except Exception as e:
                logger.warning(f"Failed to use base implementation for vertical connectivity: {e}")
                # Fall back to local implementation
                pass
        
        # Local implementation for when base module is not available
        # Get dimensions
        grid_size_x, grid_size_y, num_layers = forest_model.fuel_load.shape
        
        # Initialize 3D connectivity array (same shape as the fuel grid)
        # This allows for spatially-varying vertical connectivity
        forest_model.vertical_connectivity = np.ones((grid_size_x, grid_size_y, num_layers), 
                                                  dtype=np.float32) * 0.1  # Minimum connectivity
        
        # For each pair of adjacent layers
        for z in range(num_layers-1):
            # Get fuel values for current layer and layer above
            current_layer_fuel = forest_model.fuel_load[:,:,z]
            above_layer_fuel = forest_model.fuel_load[:,:,z+1]
            
            # Convert normalized fuel back to approximate PAD values
            # Assuming fuel is normalized PAD with a MAX_PAD_VALUE of 10.0
            pad_current = current_layer_fuel * 10.0
            pad_above = above_layer_fuel * 10.0
            
            # 1. Calculate base connectivity using minimum of adjacent PADs
            # This ensures connectivity requires vegetation in both layers
            min_pad = np.minimum(pad_current, pad_above)
            
            # 2. Calculate continuity factor - higher when PAD values are similar
            # This represents structural continuity between layers
            pad_sum = np.maximum(pad_current + pad_above, 1e-6)  # Avoid division by zero
            continuity = 1.0 - np.clip(np.abs(pad_current - pad_above) / pad_sum, 0, 1)
            
            # 3. Calculate transmittance-based connectivity
            # Higher PAD = lower transmittance = vegetation blocks more light
            transmittance_current = np.exp(-0.5 * pad_current * self.layer_height_meters)
            transmittance_above = np.exp(-0.5 * pad_above * self.layer_height_meters)
            transmittance_connectivity = 1.0 - np.abs(transmittance_current - transmittance_above)
            
            # 4. Combine factors with appropriate weights
            connectivity = (0.4 * min_pad/10.0 +          # Normalized vegetation amount 
                           0.4 * continuity +              # Structural continuity  
                           0.2 * transmittance_connectivity) # Transmittance similarity
            
            # Scale to appropriate range [0.1, 0.9]
            connectivity = 0.1 + 0.8 * connectivity
            
            # Set connectivity for this layer transition
            forest_model.vertical_connectivity[:,:,z+1] = connectivity
        
        logger.info(f"Calculated vertical connectivity for tile based on PAD values")
        logger.info(f"  Min: {forest_model.vertical_connectivity.min():.4f}")
        logger.info(f"  Max: {forest_model.vertical_connectivity.max():.4f}")
        logger.info(f"  Mean: {forest_model.vertical_connectivity.mean():.4f}")
    
    def _find_rasters_for_tile(self, tile):
        """
        Find raster files that overlap with the specified tile.
        
        Args:
            tile: Tile dictionary with bounds information
            
        Returns:
            List of raster file paths for each layer
        """
        # Calculate tile bounds in grid coordinates
        tile_start_x = tile['start_x']
        tile_start_y = tile['start_y']
        tile_end_x = tile['end_x']
        tile_end_y = tile['end_y']
        
        # Find all raster files in the base directory
        raster_files = glob.glob(os.path.join(self.base_dir, "**", "*.tif"), recursive=True)
        
        if not raster_files:
            logger.warning(f"No raster files found in {self.base_dir}")
            return [None] * self.num_layers
        
        # Sort raster files by layer index (assuming naming convention like 'layer_01.tif', 'layer_02.tif', etc.)
        # Alternative is to use the height bin as the layer index
        layer_rasters = [None] * self.num_layers
        
        # Process each raster file
        for raster_path in raster_files:
            try:
                # Extract layer index from filename or path
                # This implementation assumes files are named with layer index or height bin
                filename = os.path.basename(raster_path)
                
                # Method 1: Try to extract layer number from filename like 'layer_01.tif'
                layer_match = re.search(r'layer_(\d+)', filename, re.IGNORECASE)
                if layer_match:
                    layer_idx = int(layer_match.group(1)) - 1  # Convert to 0-based index
                else:
                    # Method 2: Try to extract height bin number from filename like 'bin_02m.tif'
                    bin_match = re.search(r'bin_(\d+)m', filename, re.IGNORECASE)
                    if bin_match:
                        bin_height = int(bin_match.group(1))
                        # Map bin height to layer index (assuming LAYER_HEIGHT_METERS is known)
                        layer_idx = int(bin_height / self.layer_height_meters)
                    else:
                        # Method 3: Try to extract numeric value from filename
                        num_match = re.search(r'(\d+)', filename)
                        if num_match:
                            layer_idx = int(num_match.group(1)) - 1
                        else:
                            # If all methods fail, skip this file
                            logger.warning(f"Could not determine layer index for {raster_path}")
                            continue
                
                # Ensure layer index is within bounds
                if layer_idx < 0 or layer_idx >= self.num_layers:
                    logger.warning(f"Layer index {layer_idx+1} from {filename} is out of bounds (1-{self.num_layers})")
                    continue
                
                # Assign raster to layer
                layer_rasters[layer_idx] = raster_path
                
            except Exception as e:
                logger.warning(f"Error processing {raster_path}: {e}")
                continue
        
        # Count how many layers have assigned rasters
        layers_with_rasters = sum(1 for r in layer_rasters if r is not None)
        logger.info(f"Found rasters for {layers_with_rasters}/{self.num_layers} layers")
        
        return layer_rasters
    
    def _load_and_process_raster(self, raster_path, target_layer, tile_bounds, forest_model):
        """
        Load and process a single raster file for a specific layer in a tile.
        
        Args:
            raster_path: Path to the raster file
            target_layer: Layer index to load data into
            tile_bounds: Tuple (start_x, start_y, end_x, end_y) defining tile bounds
            forest_model: Forest model to load data into
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract tile bounds
            tile_start_x, tile_start_y, tile_end_x, tile_end_y = tile_bounds
            
            # Calculate tile dimensions
            tile_width = tile_end_x - tile_start_x
            tile_height = tile_end_y - tile_start_y
            
            # Open the raster file
            raster = gdal.Open(raster_path)
            if raster is None:
                logger.warning(f"Could not open {raster_path}")
                return False
            
            # Read raster data
            band = raster.GetRasterBand(1)
            data = band.ReadAsArray()
            
            # Get no-data value
            no_data_value = band.GetNoDataValue()
            if no_data_value is None:
                no_data_value = -9999
            
            # Replace no-data values with zeros
            data = np.where(data == no_data_value, 0, data)
            
            # Normalize data to range [0, MAX_FUEL_VALUE]
            # This assumes PAD values are already in a reasonable range (e.g., 0-10)
            min_val = np.min(data)
            max_val = np.max(data)
            
            if max_val > min_val:
                # Normalize to [0, MAX_FUEL_VALUE]
                normalized_data = (data - min_val) / (max_val - min_val) * MAX_FUEL_VALUE
            else:
                # If all values are the same, set to zero (no vegetation)
                normalized_data = np.zeros_like(data)
            
            # Resize to match tile dimensions
            # Use bilinear interpolation for smooth transitions
            resized_data = resize(normalized_data, (tile_width, tile_height), order=1)
            
            # Store in the forest model
            forest_model.fuel_load[:, :, target_layer] = resized_data
            
            logger.debug(f"Loaded layer {target_layer} from {os.path.basename(raster_path)}")
            return True
            
        except Exception as e:
            logger.warning(f"Error loading layer {target_layer} from {raster_path}: {e}")
            return False

def example_usage():
    """
    Example of how to use the TiledLiDARIntegration class with a forest model.
    """
    print("TiledLiDARIntegration module imported.")
    print("To use this module with your forest model:")
    print("\nfrom LiDAR_Tiled_Integration import TiledLiDARIntegration")
    print("\n# Initialize tiled integration with your forest model")
    print("tiled_lidar = TiledLiDARIntegration(")
    print("    forest_model=my_forest_model,")
    print("    base_dir='path/to/lidar/rasters',")
    print("    tile_size=50,")
    print("    overlap=5")
    print(")")
    print("\n# Initialize the forest environment")
    print("tiled_lidar.initialize_tiled_environment()")
    print("\n# Visualize the result")
    print("tiled_lidar.visualize_initialization()")


if __name__ == "__main__":
    example_usage()
    
    print("\nTo process Tenerife at exactly 5m resolution:")
    print("from LiDAR_Tiled_Integration import process_tenerife_at_5m")
    print("\n# Process Tenerife at exactly 5m resolution")
    print("model_data = process_tenerife_at_5m(")
    print("    base_dir='path/to/tenerife/lidar/data',")
    print("    output_dir='path/to/output',")
    print("    num_layers=80,")
    print("    layer_group_size=10")
    print(")")
    print("\n# Merge tiles into comprehensive GeoTIFFs")
    print("merged_data = merge_tenerife_subtiles(")
    print("    model_data=model_data,")
    print("    output_path='path/to/merged/outputs',")
    print("    decimation_factor=5  # Optional: create 25m overview for visualization")
    print(")")