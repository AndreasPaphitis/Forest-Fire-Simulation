"""
Core Simulation Framework Module

This module provides the foundation for the forest fire simulation system, serving as the backbone
that unifies the entire framework. It establishes shared constants, data structures, and utility 
functions that ensure consistency across all other components of the simulation system.

PURPOSE:
The framework defines the core structure that enables 3D forest fire modeling with vertical vegetation
representation and realistic fire propagation. It implements a modular, extensible architecture where
specialized components build upon these fundamentals without code duplication.

KEY COMPONENTS:
- ModelConfig: Centralized configuration system serving as a single source of truth
- BaseForestModel: Abstract base class defining the common API for all fire model implementations
- CellState: Enumeration representing the possible states of cells in the simulation
- Utility functions: Memory calculation, progress tracking, and error handling

INTEGRATION POINTS:
- fire_simulation_engine.py builds upon this framework to implement fire propagation mechanics
- vegetation_data_integration.py uses these foundations to integrate LiDAR-derived data
- simulation_runner.py combines all components to execute simulations

UTILITY FUNCTIONS:
This module provides a set of utility functions that serve as common capabilities across
the entire simulation system:
- calculate_memory_requirements: Estimates memory usage for model configurations
- get_progress_iterator: Provides standardized progress tracking with fallback for environments without tqdm
- error_handler: Decorator for consistent error handling and reporting
- load_config/save_config: Manages configuration files and environment variables

The modular design allows components to be developed independently while maintaining compatibility.
Parameter configurations are centralized to ensure consistency and facilitate experimentation with
different simulation scenarios.

Author: Forest Fire Model Development Team
Date: 2023
Version: 1.2
"""

import os
import numpy as np
import logging
import time
import traceback
import json
import pickle
import shutil
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
import math
from collections import OrderedDict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================================================================
# CONFIGURATION SYSTEM - Single source of truth for all modules
# ===========================================================================

class ModelConfig:
    """
    Centralized configuration system for the forest fire modeling framework.
    
    This class serves as the single source of truth for all configuration parameters across
    the entire simulation system. It implements a modular configuration approach where each
    component can access only the parameters relevant to its operation, while maintaining
    consistency across the system.
    
    The configuration system supports:
    - Default values for all parameters
    - Loading configurations from JSON files
    - Saving current configurations to JSON files
    - Module-specific parameter subsets
    - Environment variable overrides
    
    Configuration categories include:
    - Spatial resolution parameters
    - Vertical structure parameters
    - Fuel-related parameters
    - Tiling parameters for large-area processing
    - Simulation control parameters
    - Memory management settings
    - Fire spread behavior parameters
    - Environmental influence factors
    - Visualization settings
    
    Usage examples:
    - Load configuration: ModelConfig.load_config('config.json')
    - Get params for a module: config = ModelConfig.get_module_config('forest_model')
    - Save current config: ModelConfig.save_config('config_backup.json')
    - Access a parameter: resolution = ModelConfig.MODEL_RESOLUTION
    """
    # Default values for core parameters
    # These can be overridden via load_config()
    
    # Spatial resolution
    MODEL_RESOLUTION = 5.0  # Default spatial resolution in meters per cell

    # Vertical structure
    LAYER_HEIGHT_METERS = 2.0  # Default height of each vertical layer in meters
    DEFAULT_NUM_LAYERS = 10  # Default number of vertical layers

    # Fuel parameters
    MIN_FUEL_VALUE = 0.1  # Minimum fuel value (consistent across modules)
    MAX_FUEL_VALUE = 10.0  # Maximum fuel value (consistent across modules)
    DEFAULT_FUEL_MOISTURE = 0.3  # Default fuel moisture content

    # Tiling parameters
    DEFAULT_TILE_SIZE = 100  # Default size of processing tiles in grid cells
    DEFAULT_TILE_OVERLAP = 10  # Default overlap between tiles in grid cells

    # Simulation parameters
    MAX_STEPS = 100  # Default maximum simulation steps
    STORE_FULL_STATES = False  # Default setting for storing full grid states

    # Memory management
    BYTES_PER_CELL = 15  # Memory usage estimate per cell in bytes
    MAX_GRID_SIZE = 1000  # Maximum recommended grid size per dimension
    
    # Fire spread parameters
    HORIZONTAL_SPREAD_PROBABILITY = 0.4  # Base probability for horizontal spread
    VERTICAL_SPREAD_PROBABILITY = 0.3  # Base probability for upward spread
    DOWNWARD_SPREAD_PROBABILITY = 0.15  # Base probability for downward spread
    EMBER_GENERATION_PROBABILITY = 0.02  # Base probability for ember generation
    EMBER_IGNITION_PROBABILITY = 0.3  # Base probability for ignition upon landing
    
    # Environmental parameters
    WIND_INFLUENCE = 0.5  # Scaling factor for wind effects
    SLOPE_INFLUENCE = 0.3  # Scaling factor for terrain effects
    EMBER_WIND_FACTOR = 0.1  # Wind influence on ember trajectory
    EMBER_HEIGHT_FACTOR = 0.05  # Height influence on ember generation
    
    # Visualization parameters
    VIZ_FRAME_INTERVAL_MS = 200  # Default animation frame interval
    VIZ_ELEVATION_FACTOR = 1.5  # Default vertical exaggeration for 3D

    # Default memory management settings
    DEFAULT_MEMORY_OPTIMIZATION_LEVEL = 2  # Medium optimization by default
    MAX_MEMORY_PERCENT = 75  # Use at most 75% of system memory by default
    
    # New disk storage parameters
    USE_DISK_STORAGE = False  # Whether to use disk-based storage
    DISK_STORAGE_DIR = "./simulation_data"  # Default directory for disk storage
    CACHE_SIZE_MB = 1024  # Default memory cache size when using disk storage (1GB)
    COMPRESSION_LEVEL = 1  # Default compression level (0-9)
    
    # Tile management settings
    USE_TILING = False
    TILE_SIZE = 500  # Default size for each tile
    TILE_OVERLAP = 50  # Default overlap between tiles
    ACTIVE_TILES_BUFFER = 2  # Number of tiles to keep loaded around active area
    
    # Multi-resolution settings
    USE_MULTI_RESOLUTION = False
    MAX_RESOLUTION_LEVELS = 3  # Default number of resolution levels
    RESOLUTION_THRESHOLD = 0.1  # Fire activity threshold to determine resolution level

    @classmethod
    def load_config(cls, config_file=None):
        """
        Load configuration from a JSON file or dictionary.
        
        Args:
            config_file: Path to JSON configuration file or config dictionary
        
        Returns:
            Updated ModelConfig class
        """
        if config_file is None:
            logger.info("No config file provided, using default values")
            return cls
            
        config_data = {}
        
        if isinstance(config_file, dict):
            config_data = config_file
        elif isinstance(config_file, str) and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.error(f"Error loading config file {config_file}: {e}")
                logger.error(traceback.format_exc())
                return cls
        else:
            logger.warning(f"Config file {config_file} not found, using default values")
            return cls
            
        # Update config values from loaded data
        for key, value in config_data.items():
            if hasattr(cls, key):
                setattr(cls, key, value)
                logger.debug(f"Set {key} = {value}")
            else:
                logger.warning(f"Ignoring unknown config parameter: {key}")
                
        return cls
    
    @classmethod
    def save_config(cls, config_file):
        """
        Save current configuration to a JSON file.
        
        Args:
            config_file: Path to output JSON configuration file
        """
        config_data = {}
        
        # Get all uppercase attributes (convention for constants)
        for key in dir(cls):
            if key.isupper() and not key.startswith('_'):
                config_data[key] = getattr(cls, key)
                
        try:
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            logger.info(f"Saved configuration to {config_file}")
        except Exception as e:
            logger.error(f"Error saving config to {config_file}: {e}")
            logger.error(traceback.format_exc())
    
    @classmethod
    def get_module_config(cls, module_name):
        """
        Get configuration relevant to a specific module.
        This allows modules to only see parameters they need.
        
        Args:
            module_name: Name of the module ('forest_model', 'lidar_integration', etc.)
            
        Returns:
            Dict of configuration parameters relevant to that module
        """
        if module_name == 'forest_model':
            return {
                'MODEL_RESOLUTION': cls.MODEL_RESOLUTION,
                'LAYER_HEIGHT_METERS': cls.LAYER_HEIGHT_METERS,
                'DEFAULT_NUM_LAYERS': cls.DEFAULT_NUM_LAYERS,
                'MIN_FUEL_VALUE': cls.MIN_FUEL_VALUE,
                'MAX_FUEL_VALUE': cls.MAX_FUEL_VALUE,
                'DEFAULT_FUEL_MOISTURE': cls.DEFAULT_FUEL_MOISTURE,
                'MAX_STEPS': cls.MAX_STEPS,
                'STORE_FULL_STATES': cls.STORE_FULL_STATES,
                'HORIZONTAL_SPREAD_PROBABILITY': cls.HORIZONTAL_SPREAD_PROBABILITY,
                'VERTICAL_SPREAD_PROBABILITY': cls.VERTICAL_SPREAD_PROBABILITY,
                'DOWNWARD_SPREAD_PROBABILITY': cls.DOWNWARD_SPREAD_PROBABILITY,
                'EMBER_GENERATION_PROBABILITY': cls.EMBER_GENERATION_PROBABILITY,
                'EMBER_IGNITION_PROBABILITY': cls.EMBER_IGNITION_PROBABILITY,
                'WIND_INFLUENCE': cls.WIND_INFLUENCE,
                'SLOPE_INFLUENCE': cls.SLOPE_INFLUENCE,
                'EMBER_WIND_FACTOR': cls.EMBER_WIND_FACTOR,
                'EMBER_HEIGHT_FACTOR': cls.EMBER_HEIGHT_FACTOR
            }
        elif module_name == 'lidar_integration':
            return {
                'MODEL_RESOLUTION': cls.MODEL_RESOLUTION,
                'LAYER_HEIGHT_METERS': cls.LAYER_HEIGHT_METERS,
                'DEFAULT_NUM_LAYERS': cls.DEFAULT_NUM_LAYERS,
                'MIN_FUEL_VALUE': cls.MIN_FUEL_VALUE,
                'MAX_FUEL_VALUE': cls.MAX_FUEL_VALUE,
                'DEFAULT_TILE_SIZE': cls.DEFAULT_TILE_SIZE,
                'DEFAULT_TILE_OVERLAP': cls.DEFAULT_TILE_OVERLAP,
                'MAX_GRID_SIZE': cls.MAX_GRID_SIZE,
                'BYTES_PER_CELL': cls.BYTES_PER_CELL
            }
        elif module_name == 'visualization':
            return {
                'VIZ_FRAME_INTERVAL_MS': cls.VIZ_FRAME_INTERVAL_MS,
                'VIZ_ELEVATION_FACTOR': cls.VIZ_ELEVATION_FACTOR,
                'STORE_FULL_STATES': cls.STORE_FULL_STATES
            }
        else:
            # Return all configuration for unknown modules
            return {key: getattr(cls, key) for key in dir(cls) 
                   if key.isupper() and not key.startswith('_')}

# For backward compatibility, expose config values at module level
MODEL_RESOLUTION = ModelConfig.MODEL_RESOLUTION
LAYER_HEIGHT_METERS = ModelConfig.LAYER_HEIGHT_METERS
DEFAULT_NUM_LAYERS = ModelConfig.DEFAULT_NUM_LAYERS
MIN_FUEL_VALUE = ModelConfig.MIN_FUEL_VALUE
MAX_FUEL_VALUE = ModelConfig.MAX_FUEL_VALUE
DEFAULT_FUEL_MOISTURE = ModelConfig.DEFAULT_FUEL_MOISTURE
DEFAULT_TILE_SIZE = ModelConfig.DEFAULT_TILE_SIZE
DEFAULT_TILE_OVERLAP = ModelConfig.DEFAULT_TILE_OVERLAP
MAX_STEPS = ModelConfig.MAX_STEPS
STORE_FULL_STATES = ModelConfig.STORE_FULL_STATES
BYTES_PER_CELL = ModelConfig.BYTES_PER_CELL
MAX_GRID_SIZE = ModelConfig.MAX_GRID_SIZE

class CellState(Enum):
    """
    Enumeration of possible cell states in the forest fire model.
    
    This enumeration defines the fundamental states that any cell in the 3D forest grid can have
    during simulation. These states form the basis of the cellular automata approach, where
    cell state transitions occur based on defined rules and neighboring cell interactions.
    
    States:
        UNBURNED (0): Cell contains unburned fuel, available for ignition.
                     Initial state for most cells at simulation start.
        
        BURNING (1):  Cell is currently burning and actively consuming fuel.
                     Can spread fire to neighboring cells based on fire spread rules.
                     Transitions to BURNED once fuel is consumed.
        
        BURNED (2):   Cell has completely burned and no fuel remains.
                     Terminal state; cannot ignite or spread fire to other cells.
    
    The simulation uses integer values (0,1,2) internally for performance, while the enumeration
    provides readable names for code clarity. State transitions typically follow the sequence:
    UNBURNED -> BURNING -> BURNED
    """
    UNBURNED = 0  # Cell contains unburned fuel
    BURNING = 1   # Cell is currently burning
    BURNED = 2    # Cell has completely burned and no fuel remains

class BaseForestModel:
    """
    Abstract base class for forest fire simulation models.
    
    The BaseForestModel class establishes the core architecture for all forest fire models
    in the simulation system. It defines the fundamental data structures, initialization
    parameters, and API methods that all derived model classes must implement.
    
    Key features:
    - 3D cellular grid representation with customizable vertical layering
    - Memory-efficient state tracking using NumPy arrays
    - Standard methods for ignition, simulation stepping, and analysis
    - Abstract methods that must be implemented by concrete subclasses
    
    This base class enables consistent model interfaces while allowing flexibility
    in implementation details for different types of forest fire models.
    
    Memory optimization:
    The model is designed to balance memory usage and computational complexity.
    Memory requirements scale with grid size, number of layers, and tracked properties.
    Implementations should use the calculate_memory_requirements utility function
    to estimate memory needs before initializing large models.
    
    Usage pattern:
    1. Initialize with grid parameters
    2. Set initial states through implementation-specific methods
    3. Define ignition points with set_ignition()
    4. Run simulation with run_simulation()
    5. Access results through properties and analysis methods
    
    Attributes:
        grid_size (tuple): Size of the grid in cells (width, height)
        num_layers (int): Number of vertical layers in the model
        layer_height_meters (float): Height of each layer in meters
        
    """
    
    def __init__(self, grid_size=(100, 100), num_layers=10, layer_height_meters=2.0):
        """
        Initialize the base forest model.
        
        Args:
            grid_size (tuple or int): Size of the grid as (width, height) in cells or a single value for square grids
            num_layers (int): Number of vertical layers to model
            layer_height_meters (float): Height of each layer in meters
        """
        if isinstance(grid_size, tuple):
            self.grid_size_x, self.grid_size_y = grid_size
        else:
            self.grid_size_x = self.grid_size_y = grid_size
        
        self.grid_size = max(self.grid_size_x, self.grid_size_y)
        self.num_layers = num_layers
        self.layer_height_meters = layer_height_meters
        
        # Basic state arrays
        self.fuel_load = np.zeros((self.grid_size_x, self.grid_size_y, num_layers), dtype=np.float32)
        self.state = np.zeros((self.grid_size_x, self.grid_size_y, num_layers), dtype=np.int8)
        self.vertical_connectivity = np.ones((self.grid_size_x, self.grid_size_y, num_layers), dtype=np.float32) * 0.5
        
        # Minimal initialization of other attributes that both modules may expect
        self.wind_direction = np.zeros((self.grid_size_x, self.grid_size_y), dtype=np.float32)
        self.wind_strength = np.zeros((self.grid_size_x, self.grid_size_y), dtype=np.float32)  # Renamed from wind_speed for consistency
        self.terrain_height = np.zeros((self.grid_size_x, self.grid_size_y), dtype=np.float32)
        self.moisture = np.ones((self.grid_size_x, self.grid_size_y), dtype=np.float32) * DEFAULT_FUEL_MOISTURE
        
        # History tracking
        self.history = {}
        
        # Initialize class-level constants (consistent across all modules)
        self.MIN_FUEL_VALUE = MIN_FUEL_VALUE
        self.MAX_FUEL_VALUE = MAX_FUEL_VALUE
        
        # Additional flags
        self.debug = False  # Debug mode for detailed logging
    
    def set_ignition(self, x, y, z=0):
        """
        Set an ignition point in the forest.
        
        Args:
            x: X-coordinate
            y: Y-coordinate
            z: Z-coordinate (layer index, defaults to ground layer)
        """
        if (0 <= x < self.grid_size_x and 
            0 <= y < self.grid_size_y and 
            0 <= z < self.num_layers):
            self.state[x, y, z] = CellState.BURNING.value
    
    def run_simulation(self, max_steps=MAX_STEPS, store_full_states=STORE_FULL_STATES):
        """
        Base implementation of the simulation runner.
        This should be overridden by full implementation.
        
        Args:
            max_steps: Maximum number of simulation steps
            store_full_states: Whether to store complete states for visualization
            
        Returns:
            Dictionary with simulation results
        """
        # Base implementation just returns a placeholder
        return {"steps": 0, "burned_cells": 0, "max_fire_extent": 0}
    
    def calculate_vertical_connectivity(self):
        """
        Calculate 3D vertical connectivity based on fuel distribution.
        This method modifies self.vertical_connectivity in place.
        
        The connectivity value represents how easily fire can spread 
        between adjacent vertical layers based on vegetation structure.
        Higher values = easier vertical spread.
        """
        # Initialize with minimum connectivity
        self.vertical_connectivity = np.ones((self.grid_size_x, self.grid_size_y, self.num_layers), 
                                           dtype=np.float32) * 0.1
        
        # For each pair of adjacent layers
        for z in range(self.num_layers - 1):
            # Get fuel values for current layer and layer above
            current_layer_fuel = self.fuel_load[:, :, z]
            above_layer_fuel = self.fuel_load[:, :, z + 1]
            
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
            connectivity = (0.4 * min_pad / 10.0 +  # Normalized vegetation amount 
                           0.4 * continuity +  # Structural continuity  
                           0.2 * transmittance_connectivity)  # Transmittance similarity
            
            # Scale to appropriate range [0.1, 0.9]
            connectivity = 0.1 + 0.8 * connectivity
            
            # Set connectivity for this layer transition
            self.vertical_connectivity[:, :, z + 1] = connectivity
        
        # Log summary statistics
        logger.info(f"Calculated vertical connectivity for model")
        logger.info(f"  Min: {self.vertical_connectivity.min():.4f}")
        logger.info(f"  Max: {self.vertical_connectivity.max():.4f}")
        logger.info(f"  Mean: {self.vertical_connectivity.mean():.4f}")
        
        return self.vertical_connectivity

    @classmethod
    def create_model(cls, model_type='base', **kwargs):
        """
        Factory method to create forest model instances.
        This helps avoid circular imports and provides a unified interface.
        
        Args:
            model_type: Type of model to create ('base', 'full', 'stub')
            **kwargs: Parameters to pass to the model constructor
            
        Returns:
            Instance of the requested model type
        """
        if model_type == 'base':
            return cls(**kwargs)
        
        elif model_type == 'full':
            # Try to import ForestModel from fire_simulation_engine
            try:
                from fire_simulation_engine import ForestModel
                return ForestModel(**kwargs)
            except ImportError:
                logger.warning("Failed to import ForestModel from fire_simulation_engine.py")
                logger.warning("Falling back to BaseForestModel")
                return cls(**kwargs)
        
        elif model_type == 'stub':
            # Return a minimal stub model
            return cls(**kwargs)
        
        else:
            logger.warning(f"Unknown model type: {model_type}, using base model")
            return cls(**kwargs)

# ===========================================================================
# UTILITY FUNCTIONS - Shared across modules
# ===========================================================================

def calculate_memory_requirements(grid_size: int, num_layers: int = DEFAULT_NUM_LAYERS) -> Dict[str, float]:
    """
    Calculate detailed memory requirements for a forest model.
    
    Parameters
    ----------
    grid_size : int
        Size of the grid in cells per side
    num_layers : int, default=DEFAULT_NUM_LAYERS
        Number of vertical layers
        
    Returns
    -------
    dict
        Detailed memory requirements in MB by component and total
    """
    total_cells = grid_size * grid_size * num_layers
    grid_cells = grid_size * grid_size
    
    # Calculate memory for each component
    memory = {
        'fuel_load': (total_cells * 4) / (1024 * 1024),  # float32 array: 4 bytes per element
        'state': (total_cells * 1) / (1024 * 1024),      # int8 array: 1 byte per element
        'vertical_connectivity': (total_cells * 4) / (1024 * 1024),
        'wind_direction': (grid_cells * 4) / (1024 * 1024),
        'wind_strength': (grid_cells * 4) / (1024 * 1024),
        'terrain_height': (grid_cells * 4) / (1024 * 1024),
        'moisture': (grid_cells * 4) / (1024 * 1024),
        'history': max(100 * num_layers * 4, total_cells * 0.01) / (1024 * 1024),  # Estimate for history dict
        'other': total_cells * 1 / (1024 * 1024),       # Buffer for other data structures
    }
    
    memory['total'] = sum(memory.values())
    
    return memory

def get_progress_iterator(iterable, desc=None, **kwargs):
    """
    Get a progress iterator that works with or without tqdm.
    
    Parameters
    ----------
    iterable : iterable
        The iterable to wrap with progress tracking
    desc : str, optional
        Description for the progress bar
    **kwargs
        Additional arguments for tqdm
        
    Returns
    -------
    iterable
        Progress-tracking iterable
    """
    try:
        from tqdm import tqdm
        return tqdm(iterable, desc=desc, **kwargs)
    except ImportError:
        # Improved fallback implementation
        return _ProgressIndicator(iterable, desc, **kwargs)

class _ProgressIndicator:
    """Fallback progress indicator when tqdm is not available."""
    
    def __init__(self, iterable, desc=None, **kwargs):
        self.iterable = iterable
        self.desc = desc
        self.total = len(iterable) if hasattr(iterable, '__len__') else None
        self.update_interval = kwargs.get('update_interval', 10)  # Update every 10 items by default
        
        if desc:
            print(f"{desc}...")
        if self.total:
            print(f"Total items: {self.total}")
        
        self.start_time = time.time()
        
    def __iter__(self):
        for i, item in enumerate(self.iterable):
            # Print progress periodically
            if i > 0 and i % self.update_interval == 0 and self.total:
                elapsed = time.time() - self.start_time
                items_per_sec = i / max(elapsed, 0.001)
                eta = (self.total - i) / max(items_per_sec, 0.001)
                
                print(f"Progress: {i}/{self.total} ({i/self.total*100:.1f}%) "
                      f"[{elapsed:.1f}s elapsed, ETA: {eta:.1f}s, {items_per_sec:.1f} items/s]")
            
            yield item
            
        # Final update
        elapsed = time.time() - self.start_time
        print(f"Completed in {elapsed:.2f}s")

def error_handler(func=None, debug=False):
    """
    Decorator for consistent error handling across functions.
    Can be used with or without debug parameter.
    
    Example usage:
        @error_handler
        def my_function():
            ...
        
        @error_handler(debug=True)
        def my_debug_function():
            ...
    """
    # Handle being called as @error_handler(debug=...)
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
    
    # Handle being called as @error_handler
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            if debug:
                logger.error(traceback.format_exc())
            raise
    return wrapper

# Load configuration from file if specified in environment
if 'FOREST_MODEL_CONFIG' in os.environ:
    config_path = os.environ['FOREST_MODEL_CONFIG']
    ModelConfig.load_config(config_path)

# ===========================================================================
# PROGRESSIVE RESOLUTION PROCESSING
# ===========================================================================

class MultiResolutionGrid:
    """
    Implements a grid with multiple resolution levels to optimize memory usage.
    
    This class enables using different resolutions in different areas of the simulation:
    - Fine resolution near active fire fronts
    - Coarse resolution in inactive areas
    - Dynamic resolution adjustment based on fire activity
    
    This significantly reduces memory usage for large-scale simulations while
    maintaining high detail where it matters most.
    """
    
    def __init__(self, base_width: int, base_height: int, 
                 base_resolution: float = ModelConfig.MODEL_RESOLUTION,
                 num_layers: int = ModelConfig.DEFAULT_NUM_LAYERS,
                 max_resolution_levels: int = 3):
        """
        Initialize the multi-resolution grid.
        
        Args:
            base_width: Base grid width at the finest resolution (cells)
            base_height: Base grid height at the finest resolution (cells)
            base_resolution: Resolution in meters of the base grid
            num_layers: Number of vertical layers
            max_resolution_levels: Maximum number of resolution levels (1 = uniform grid)
        """
        self.base_width = base_width
        self.base_height = base_height
        self.base_resolution = base_resolution
        self.num_layers = num_layers
        self.max_resolution_levels = max_resolution_levels
        
        # Initialize resolution levels (powers of 2: 1x, 2x, 4x, etc.)
        self.resolution_levels = []
        for level in range(max_resolution_levels):
            scale_factor = 2 ** level
            level_info = {
                'scale_factor': scale_factor,
                'resolution': base_resolution * scale_factor,
                'width': base_width // scale_factor,
                'height': base_height // scale_factor,
                'grid': None  # Will be initialized on demand
            }
            self.resolution_levels.append(level_info)
        
        # Initialize the base grid (finest resolution)
        self._initialize_base_grid()
        
        # Tracking for active areas
        self.active_regions = []  # Regions with fire activity
        
        logger.info(f"Initialized MultiResolutionGrid with {max_resolution_levels} resolution levels")
        logger.info(f"Base resolution: {base_resolution}m, grid size: {base_width}x{base_height}")
    
    def _initialize_base_grid(self):
        """Initialize the base grid at the finest resolution."""
        # Initialize base grid for state
        base_grid = np.zeros(
            (self.base_width, self.base_height, self.num_layers),
            dtype=np.int8
        )
        self.resolution_levels[0]['grid'] = base_grid
        
        # Additional data structures
        self.fuel_load = np.zeros_like(base_grid, dtype=np.float32)
        self.vertical_connectivity = np.zeros_like(base_grid, dtype=np.float32)
        
        logger.debug(f"Base grid initialized with shape {base_grid.shape}")
    
    def update_resolution_map(self, fire_coordinates: List[Tuple[int, int, int]]):
        """
        Update the resolution map based on current fire activity.
        
        Args:
            fire_coordinates: List of (x, y, z) coordinates of burning cells
        """
        if not fire_coordinates:
            return
        
        # Reset active regions
        self.active_regions = []
        
        # Group fire coordinates into regions
        fire_points_2d = [(x, y) for x, y, _ in fire_coordinates]
        
        # Create high-resolution regions around fire activity
        for x, y in fire_points_2d:
            # Add a region around each fire point (buffer zone)
            buffer_size = 20  # cells at base resolution
            region = {
                'x_min': max(0, x - buffer_size),
                'y_min': max(0, y - buffer_size),
                'x_max': min(self.base_width - 1, x + buffer_size),
                'y_max': min(self.base_height - 1, y + buffer_size),
                'level': 0  # Use highest resolution for active fire
            }
            self.active_regions.append(region)
        
        # Merge overlapping regions
        self._merge_overlapping_regions()
        
        # Update coarser resolution grids
        self._update_coarse_grids()
        
        logger.debug(f"Updated resolution map with {len(self.active_regions)} active regions")
    
    def _merge_overlapping_regions(self):
        """Merge overlapping high-resolution regions."""
        if not self.active_regions:
            return
        
        merged = True
        while merged:
            merged = False
            i = 0
            while i < len(self.active_regions):
                j = i + 1
                while j < len(self.active_regions):
                    # Check if regions overlap
                    r1 = self.active_regions[i]
                    r2 = self.active_regions[j]
                    
                    overlap = (
                        r1['x_min'] <= r2['x_max'] and r1['x_max'] >= r2['x_min'] and
                        r1['y_min'] <= r2['y_max'] and r1['y_max'] >= r2['y_min']
                    )
                    
                    if overlap:
                        # Merge regions
                        r1['x_min'] = min(r1['x_min'], r2['x_min'])
                        r1['y_min'] = min(r1['y_min'], r2['y_min'])
                        r1['x_max'] = max(r1['x_max'], r2['x_max'])
                        r1['y_max'] = max(r1['y_max'], r2['y_max'])
                        
                        # Remove the second region
                        self.active_regions.pop(j)
                        merged = True
                    else:
                        j += 1
                i += 1
    
    def _update_coarse_grids(self):
        """Update coarser resolution grids based on active regions."""
        # Create or update coarser grids
        for level_idx in range(1, self.max_resolution_levels):
            level = self.resolution_levels[level_idx]
            
            # Initialize grid if needed
            if level['grid'] is None:
                level['grid'] = np.zeros(
                    (level['width'], level['height'], self.num_layers),
                    dtype=np.int8
                )
            
            # Downsample from the next finer level
            finer_level = self.resolution_levels[level_idx - 1]
            scale_factor = level['scale_factor'] // finer_level['scale_factor']
            
            # Use block_reduce or simple strided slicing for downsampling
            for z in range(self.num_layers):
                # Simple downsampling: take every nth cell
                level['grid'][:, :, z] = finer_level['grid'][::scale_factor, ::scale_factor, z]
    
    def get_cell_state(self, x: int, y: int, z: int) -> int:
        """
        Get the state of a cell at base resolution coordinates.
        
        Uses the highest resolution data available for that location.
        
        Args:
            x, y, z: Coordinates at base resolution
            
        Returns:
            Cell state (0=unburned, 1=burning, 2=burned)
        """
        # First check if point is in any high-resolution active region
        for region in self.active_regions:
            if (region['x_min'] <= x <= region['x_max'] and 
                region['y_min'] <= y <= region['y_max']):
                # Use highest resolution grid
                return self.resolution_levels[0]['grid'][x, y, z]
        
        # If not in active region, find appropriate resolution level
        for level_idx in range(1, self.max_resolution_levels):
            level = self.resolution_levels[level_idx]
            scale_factor = level['scale_factor']
            
            # Convert base coordinates to this level's coordinates
            level_x, level_y = x // scale_factor, y // scale_factor
            
            # Check if within bounds
            if (0 <= level_x < level['width'] and 
                0 <= level_y < level['height']):
                return level['grid'][level_x, level_y, z]
        
        # Fallback to base grid
        return self.resolution_levels[0]['grid'][x, y, z]
    
    def set_cell_state(self, x: int, y: int, z: int, state: int):
        """
        Set the state of a cell at base resolution coordinates.
        
        Updates all resolution levels that contain this cell.
        
        Args:
            x, y, z: Coordinates at base resolution
            state: New cell state
        """
        # Always update the base grid
        self.resolution_levels[0]['grid'][x, y, z] = state
        
        # Update coarser grids if the cell is represented there
        for level_idx in range(1, self.max_resolution_levels):
            level = self.resolution_levels[level_idx]
            scale_factor = level['scale_factor']
            
            # Convert base coordinates to this level's coordinates
            level_x, level_y = x // scale_factor, y // scale_factor
            
            # Check if within bounds
            if (0 <= level_x < level['width'] and 
                0 <= level_y < level['height']):
                level['grid'][level_x, level_y, z] = state
    
    def estimate_memory_usage(self) -> float:
        """
        Estimate memory usage of the multi-resolution grid in MB.
        
        Returns:
            Memory usage in MB
        """
        memory_bytes = 0
        
        # Calculate memory for each resolution level
        for level in self.resolution_levels:
            if level['grid'] is not None:
                grid_size = level['width'] * level['height'] * self.num_layers
                memory_bytes += grid_size  # 1 byte per cell for state
        
        # Add memory for base grid data structures
        base_grid_size = self.base_width * self.base_height * self.num_layers
        memory_bytes += base_grid_size * 8  # 4 bytes each for fuel and connectivity
        
        # Convert to MB
        return memory_bytes / (1024 * 1024)
    
    def get_resolution_level_at(self, x: int, y: int) -> int:
        """
        Get the resolution level used at a specific location.
        
        Args:
            x, y: Coordinates at base resolution
            
        Returns:
            Resolution level index (0 = finest)
        """
        # Check if in any active region
        for region in self.active_regions:
            if (region['x_min'] <= x <= region['x_max'] and 
                region['y_min'] <= y <= region['y_max']):
                return 0  # Highest resolution
        
        # Default to the coarsest level
        return self.max_resolution_levels - 1
    
    def get_memory_reduction_factor(self) -> float:
        """
        Calculate the memory reduction factor compared to a uniform high-resolution grid.
        
        Returns:
            Ratio of memory saved (e.g., 0.75 means 75% reduction)
        """
        uniform_size = self.base_width * self.base_height * self.num_layers
        actual_memory = sum(
            level['width'] * level['height'] * self.num_layers 
            for level in self.resolution_levels 
            if level['grid'] is not None
        )
        
        return 1.0 - (actual_memory / uniform_size)

# ===========================================================================
# MEMORY-OPTIMIZED TILE MANAGEMENT
# ===========================================================================

class TileManager:
    """
    Manages the loading, unloading, and processing of spatial data tiles.
    
    The TileManager is responsible for tracking which tiles are currently
    loaded in memory, determining which tiles should be activated or
    deactivated, and managing the loading and unloading of tile data.
    """
    
    def __init__(self, width, height, tile_size, overlap=1, 
                 memory_limit_mb=None, num_layers=1,
                 on_tile_unload=None, on_tile_load=None):
        """
        Initialize the TileManager with the specified dimensions and constraints.
        
        Args:
            width: Total width of the grid in cells
            height: Total height of the grid in cells
            tile_size: Size of each tile in cells (tiles are square)
            overlap: Number of cells that overlap between adjacent tiles
            memory_limit_mb: Maximum memory usage in megabytes
            num_layers: Number of data layers in each tile (for memory calculation)
            on_tile_unload: Callback function called when a tile is unloaded
            on_tile_load: Callback function called when a tile is loaded
        """
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.overlap = overlap
        self.memory_limit_mb = memory_limit_mb
        self.num_layers = num_layers
        
        # Calculate number of tiles in each dimension
        self.tiles_x = math.ceil(width / (tile_size - overlap))
        self.tiles_y = math.ceil(height / (tile_size - overlap))
        self.total_tiles = self.tiles_x * self.tiles_y
        
        # Initialize data structures
        self.active_tiles = set()  # Set of (x, y) tuples for active tiles
        self.tile_data = {}  # Dictionary mapping (x, y) to tile data
        self.tile_last_used = {}  # Dictionary tracking when tiles were last used
        
        # Set callbacks
        self.on_tile_unload = on_tile_unload
        self.on_tile_load = on_tile_load
        
        # Track current memory usage
        self.current_memory_usage_mb = 0
        
        # Memory per tile estimate (based on tile size and number of layers)
        self.memory_per_tile_mb = self._estimate_tile_memory_mb()
        
        # Initialize step counter
        self.current_step = 0
        
        logger.info(f"Initialized TileManager with {self.total_tiles} tiles "
                    f"({self.tiles_x}x{self.tiles_y}), {self.tile_size}x{self.tile_size} each")
        logger.info(f"Estimated memory per tile: {self.memory_per_tile_mb:.2f}MB")
        if memory_limit_mb:
            logger.info(f"Memory limit: {memory_limit_mb}MB (max ~{int(memory_limit_mb/self.memory_per_tile_mb)} tiles)")

    def _estimate_tile_memory_mb(self):
        """Estimate memory usage per tile in megabytes."""
        # Assume each cell uses 8 bytes (float64) per layer
        bytes_per_cell = 8 * self.num_layers
        cells_per_tile = self.tile_size * self.tile_size
        bytes_per_tile = bytes_per_cell * cells_per_tile
        
        # Convert to MB
        mb_per_tile = bytes_per_tile / (1024 * 1024)
        
        # Add some overhead for data structures
        return mb_per_tile * 1.1  # 10% overhead

    def activate_tile(self, tile_x, tile_y, tile_data=None):
        """
        Activate a tile, making it available for processing.
        
        If the tile data is provided, it will be used. Otherwise,
        the on_tile_load callback will be called to load the data.
        
        Args:
            tile_x: X-coordinate of the tile
            tile_y: Y-coordinate of the tile
            tile_data: Optional data for the tile
            
        Returns:
            True if activation was successful, False otherwise
        """
        # Check if the tile is already active
        if (tile_x, tile_y) in self.active_tiles:
            # Update last used time
            self.tile_last_used[(tile_x, tile_y)] = self.current_step
            return True
        
        # Check if activating this tile would exceed memory limits
        if (self.memory_limit_mb is not None and 
            self.current_memory_usage_mb + self.memory_per_tile_mb > self.memory_limit_mb):
            # Need to free up memory by deactivating tiles
            if not self._free_memory_for_new_tile():
                # Cannot free enough memory
                logger.warning(f"Cannot activate tile ({tile_x}, {tile_y}): memory limit would be exceeded")
                return False
        
        # Load tile data if not provided
        if tile_data is None and self.on_tile_load is not None:
            try:
                tile_data = self.on_tile_load(tile_x, tile_y)
                if tile_data is None:
                    logger.warning(f"Failed to load tile data for ({tile_x}, {tile_y})")
                    return False
            except Exception as e:
                logger.error(f"Error loading tile ({tile_x}, {tile_y}): {e}")
                return False
        
        # Store tile data
        self.tile_data[(tile_x, tile_y)] = tile_data
        self.active_tiles.add((tile_x, tile_y))
        self.tile_last_used[(tile_x, tile_y)] = self.current_step
        
        # Update memory usage
        self.current_memory_usage_mb += self.memory_per_tile_mb
        
        logger.debug(f"Activated tile ({tile_x}, {tile_y}), total active: {len(self.active_tiles)}")
        return True

    def deactivate_tile(self, tile_x, tile_y):
        """
        Deactivate a tile, removing it from active processing.
        
        This will call the on_tile_unload callback if provided.
        
        Args:
            tile_x: X-coordinate of the tile
            tile_y: Y-coordinate of the tile
            
        Returns:
            True if deactivation was successful, False otherwise
        """
        # Check if the tile is active
        if (tile_x, tile_y) not in self.active_tiles:
            return False
        
        # Get tile data
        tile_data = self.tile_data.get((tile_x, tile_y))
        
        # Call unload callback if provided
        if self.on_tile_unload is not None and tile_data is not None:
            try:
                self.on_tile_unload(tile_x, tile_y, tile_data)
            except Exception as e:
                logger.error(f"Error unloading tile ({tile_x}, {tile_y}): {e}")
                # Continue with deactivation despite error
        
        # Remove tile from active set and data dictionary
        self.active_tiles.remove((tile_x, tile_y))
        self.tile_data.pop((tile_x, tile_y), None)
        self.tile_last_used.pop((tile_x, tile_y), None)
        
        # Update memory usage
        self.current_memory_usage_mb -= self.memory_per_tile_mb
        
        logger.debug(f"Deactivated tile ({tile_x}, {tile_y}), total active: {len(self.active_tiles)}")
        return True

    def get_tile_data(self, tile_x, tile_y):
        """
        Get the data for a specific tile.
        
        Args:
            tile_x: X-coordinate of the tile
            tile_y: Y-coordinate of the tile
            
        Returns:
            The tile data, or None if the tile is not active
        """
        # Update last used time if tile is active
        if (tile_x, tile_y) in self.active_tiles:
            self.tile_last_used[(tile_x, tile_y)] = self.current_step
        
        return self.tile_data.get((tile_x, tile_y))

    def update_tile_data(self, tile_x, tile_y, new_data):
        """
        Update the data for a specific tile.
        
        Args:
            tile_x: X-coordinate of the tile
            tile_y: Y-coordinate of the tile
            new_data: New data for the tile
            
        Returns:
            True if update was successful, False otherwise
        """
        # Check if the tile is active
        if (tile_x, tile_y) not in self.active_tiles:
            return False
        
        # Update tile data
        self.tile_data[(tile_x, tile_y)] = new_data
        self.tile_last_used[(tile_x, tile_y)] = self.current_step
        
        return True

    def _free_memory_for_new_tile(self):
        """
        Free up memory by deactivating the least recently used tiles.
        
        Returns:
            True if enough memory was freed, False otherwise
        """
        # Sort tiles by last used time
        sorted_tiles = sorted(
            self.tile_last_used.items(),
            key=lambda x: x[1]
        )
        
        # Deactivate tiles until enough memory is freed
        for (tile_x, tile_y), _ in sorted_tiles:
            if self.current_memory_usage_mb + self.memory_per_tile_mb <= self.memory_limit_mb:
                # Enough memory has been freed
                return True
            
            # Deactivate this tile
            self.deactivate_tile(tile_x, tile_y)
        
        # Check if enough memory was freed
        return (self.current_memory_usage_mb + self.memory_per_tile_mb <= self.memory_limit_mb)

    def get_active_tiles(self):
        """
        Get the set of currently active tiles.
        
        Returns:
            Set of (x, y) tuples for active tiles
        """
        return self.active_tiles.copy()

    def increment_step(self):
        """
        Increment the current step counter.
        """
        self.current_step += 1

    def get_memory_usage_mb(self):
        """
        Get the current memory usage in megabytes.
        
        Returns:
            Current memory usage in MB
        """
        return self.current_memory_usage_mb

    def get_neighboring_tiles(self, tile_x, tile_y):
        """
        Get the coordinates of neighboring tiles.
        
        Args:
            tile_x: X-coordinate of the tile
            tile_y: Y-coordinate of the tile
            
        Returns:
            List of (x, y) tuples for neighboring tiles
        """
        neighbors = []
        
        # Check all 8 neighbors
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                # Skip the tile itself
                if dx == 0 and dy == 0:
                    continue
                
                # Calculate neighbor coordinates
                nx, ny = tile_x + dx, tile_y + dy
                
                # Check if neighbor is within bounds
                if 0 <= nx < self.tiles_x and 0 <= ny < self.tiles_y:
                    neighbors.append((nx, ny))
        
        return neighbors
    
    def activate_region(self, x, y, width, height):
        """
        Activate all tiles that overlap with the specified region.
        
        Args:
            x: X-coordinate of the region (in cells)
            y: Y-coordinate of the region (in cells)
            width: Width of the region (in cells)
            height: Height of the region (in cells)
            
        Returns:
            Number of newly activated tiles
        """
        # Calculate tile coordinates for the region
        start_tile_x = max(0, x // (self.tile_size - self.overlap))
        start_tile_y = max(0, y // (self.tile_size - self.overlap))
        
        end_tile_x = min(self.tiles_x - 1, (x + width) // (self.tile_size - self.overlap))
        end_tile_y = min(self.tiles_y - 1, (y + height) // (self.tile_size - self.overlap))
        
        # Activate all tiles in the region
        newly_activated = 0
        for tile_y in range(start_tile_y, end_tile_y + 1):
            for tile_x in range(start_tile_x, end_tile_x + 1):
                if (tile_x, tile_y) not in self.active_tiles:
                    if self.activate_tile(tile_x, tile_y):
                        newly_activated += 1
        
        logger.info(f"Activated {newly_activated} tiles in region ({x},{y})-({x+width},{y+height})")
        return newly_activated
    
    def initialize(self, initial_state=None):
        """
        Initialize the TileManager with an initial state.
        
        Args:
            initial_state: Initial state data for the entire grid (optional)
            
        Returns:
            True if initialization was successful, False otherwise
        """
        # Clear any existing data
        for tile_x, tile_y in list(self.active_tiles):
            self.deactivate_tile(tile_x, tile_y)
        
        self.active_tiles.clear()
        self.tile_data.clear()
        self.tile_last_used.clear()
        self.current_memory_usage_mb = 0
        self.current_step = 0
        
        # If no initial state provided, just return success
        if initial_state is None:
            logger.info("Initialized TileManager without initial state")
            return True
        
        # Initialize with the provided state by breaking it into tiles
        if hasattr(initial_state, 'shape'):
            # It's a NumPy array or similar
            total_height, total_width = initial_state.shape[:2]
            
            # Check if dimensions match
            if total_width != self.width or total_height != self.height:
                logger.warning(f"Initial state dimensions ({total_width}x{total_height}) "
                              f"don't match TileManager dimensions ({self.width}x{self.height})")
                # Continue anyway but log warning
            
            # Create tiles from the initial state
            for tile_y in range(self.tiles_y):
                for tile_x in range(self.tiles_x):
                    # Calculate tile boundaries
                    x_start = tile_x * (self.tile_size - self.overlap)
                    y_start = tile_y * (self.tile_size - self.overlap)
                    
                    x_end = min(x_start + self.tile_size, total_width)
                    y_end = min(y_start + self.tile_size, total_height)
                    
                    # Extract tile data
                    tile_data = initial_state[y_start:y_end, x_start:x_end]
                    
                    # Store tile data
                    self.tile_data[(tile_x, tile_y)] = tile_data
                    self.active_tiles.add((tile_x, tile_y))
                    self.tile_last_used[(tile_x, tile_y)] = self.current_step
                    
                    # Update memory usage
                    self.current_memory_usage_mb += self.memory_per_tile_mb
            
            logger.info(f"Initialized all {self.total_tiles} tiles from initial state")
            return True
        else:
            # It's a dictionary or other structure
            logger.info("Initialized TileManager with custom initial state")
            # Handle different types of initial state as needed
            return True

# ===========================================================================
# DISK-BASED STORAGE FOR LARGE SIMULATIONS
# ===========================================================================

class DiskStorageManager:
    """
    Manages offloading of simulation data to disk storage with optional in-memory caching.
    
    This class provides functionality to store and retrieve arbitrary data objects,
    with a configurable in-memory LRU cache to improve performance for frequently
    accessed items.
    """
    
    def __init__(self, base_dir="simulation_storage", cache_size_mb=256):
        """
        Initialize the DiskStorageManager.
        
        Args:
            base_dir (str): Base directory for storing data
            cache_size_mb (int): Maximum size of the in-memory cache in megabytes
        """
        self.base_dir = base_dir
        self.cache_size_mb = cache_size_mb
        self.cache = OrderedDict()  # LRU cache
        self.cache_usage_bytes = 0
        self.file_sizes = {}  # Track file sizes for statistics
        
        # Create storage directories
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            print(f"Created storage directory: {base_dir}")
        
        # Create metadata directory
        metadata_dir = os.path.join(base_dir, "_metadata")
        if not os.path.exists(metadata_dir):
            os.makedirs(metadata_dir)
        
        # Load existing file size data if available
        self.file_sizes_path = os.path.join(metadata_dir, "file_sizes.json")
        if os.path.exists(self.file_sizes_path):
            try:
                with open(self.file_sizes_path, 'r') as f:
                    self.file_sizes = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load file sizes metadata: {e}")
                self.file_sizes = {}
    
    def _get_file_path(self, key):
        """
        Get the file path for a given storage key.
        
        For tile data, creates a hierarchical structure based on tile coordinates.
        For other data, uses a flat structure.
        
        Args:
            key (str): The storage key
            
        Returns:
            str: The full file path
        """
        # If it's a tile key (format: tile_x_y_...), create a directory structure
        if key.startswith("tile_"):
            parts = key.split("_")
            if len(parts) >= 3:
                x_coord = parts[1]
                y_coord = parts[2]
                # Create a directory structure like: .../tiles/x_coord/y_coord/
                tile_dir = os.path.join(self.base_dir, "tiles", x_coord, y_coord)
                if not os.path.exists(tile_dir):
                    os.makedirs(tile_dir)
                return os.path.join(tile_dir, f"{key}.pickle")
        
        # For non-tile data, use a flat structure
        return os.path.join(self.base_dir, f"{key}.pickle")
    
    def store(self, key, data):
        """
        Store data to disk and optionally cache it.
        
        Args:
            key (str): Unique key to identify the data
            data: The data to store (must be pickle-serializable)
            
        Returns:
            bool: True if successful, False otherwise
        """
        file_path = self._get_file_path(key)
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Serialize and save the data
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
            
            # Get the file size and update tracking
            file_size = os.path.getsize(file_path)
            self.file_sizes[key] = file_size
            
            # Save updated file sizes
            with open(self.file_sizes_path, 'w') as f:
                json.dump(self.file_sizes, f)
            
            # Add to cache if it's not too big
            if file_size < self.cache_size_mb * 1024 * 1024 * 0.25:  # Limit single items to 25% of cache
                self._add_to_cache(key, data, file_size)
            
            return True
        except Exception as e:
            print(f"Error storing data for key '{key}': {e}")
            return False
    
    def retrieve(self, key):
        """
        Retrieve data from storage (first checks cache, then disk).
        
        Args:
            key (str): The key of the data to retrieve
            
        Returns:
            The retrieved data or None if not found or error occurs
        """
        # Check if the item is in the cache
        if key in self.cache:
            # Move the item to the end of the OrderedDict to mark it as recently used
            data = self.cache.pop(key)
            self.cache[key] = data
            return data
        
        # If not in cache, load from disk
        file_path = self._get_file_path(key)
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            # Add to cache
            file_size = os.path.getsize(file_path)
            self._add_to_cache(key, data, file_size)
            
            return data
        except Exception as e:
            print(f"Error retrieving data for key '{key}': {e}")
            return None
    
    def _add_to_cache(self, key, data, size_bytes):
        """
        Add an item to the in-memory cache, managing cache size.
        
        Args:
            key (str): The key of the data
            data: The data to cache
            size_bytes (int): Size of the data in bytes
        """
        # If this item is already in the cache, remove it first
        if key in self.cache:
            self.cache.pop(key)
            self.cache_usage_bytes -= size_bytes
        
        # Make space in the cache if needed
        while (self.cache_usage_bytes + size_bytes) > (self.cache_size_mb * 1024 * 1024) and self.cache:
            self._remove_lru_item()
        
        # Add the item to the cache if it fits
        if size_bytes <= (self.cache_size_mb * 1024 * 1024):
            self.cache[key] = data
            self.cache_usage_bytes += size_bytes
    
    def _remove_lru_item(self):
        """Remove the least recently used item from the cache."""
        if self.cache:
            # The first item in an OrderedDict is the oldest
            key, _ = next(iter(self.cache.items()))
            if key in self.file_sizes:
                self.cache_usage_bytes -= self.file_sizes[key]
            self.cache.pop(key)
    
    def clear_storage(self):
        """
        Clear all stored data and cache.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Clear cache
            self.cache.clear()
            self.cache_usage_bytes = 0
            
            # Delete all files except the metadata directory
            for item in os.listdir(self.base_dir):
                item_path = os.path.join(self.base_dir, item)
                if item != "_metadata":
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
            
            # Reset file sizes tracking
            self.file_sizes = {}
            with open(self.file_sizes_path, 'w') as f:
                json.dump(self.file_sizes, f)
            
            return True
        except Exception as e:
            print(f"Error clearing storage: {e}")
            return False
    
    def list_stored_items(self):
        """
        List all stored items.
        
        Returns:
            list: List of storage keys
        """
        return list(self.file_sizes.keys())
    
    def get_storage_info(self):
        """
        Get information about storage usage.
        
        Returns:
            dict: Dictionary with storage information
        """
        total_size_bytes = sum(self.file_sizes.values())
        return {
            'items_count': len(self.file_sizes),
            'disk_usage_bytes': total_size_bytes,
            'disk_usage_mb': total_size_bytes / (1024 * 1024),
            'cache_usage_bytes': self.cache_usage_bytes,
            'cache_usage_mb': self.cache_usage_bytes / (1024 * 1024),
            'cache_items_count': len(self.cache),
            'cache_size_mb': self.cache_size_mb
        }
    
    def delete_item(self, key):
        """
        Delete a specific item from storage and cache.
        
        Args:
            key (str): The key of the item to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Remove from cache if present
            if key in self.cache:
                self.cache_usage_bytes -= self.file_sizes.get(key, 0)
                self.cache.pop(key)
            
            # Remove from disk
            file_path = self._get_file_path(key)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Update tracking
            if key in self.file_sizes:
                del self.file_sizes[key]
                with open(self.file_sizes_path, 'w') as f:
                    json.dump(self.file_sizes, f)
            
            return True
        except Exception as e:
            print(f"Error deleting item '{key}': {e}")
            return False
    
    def get_item_info(self, key):
        """
        Get information about a specific stored item.
        
        Args:
            key (str): The key of the item
            
        Returns:
            dict: Information about the item or None if not found
        """
        if key not in self.file_sizes:
            return None
        
        return {
            'size_bytes': self.file_sizes[key],
            'size_mb': self.file_sizes[key] / (1024 * 1024),
            'in_cache': key in self.cache,
            'file_path': self._get_file_path(key)
        }

class TiledSimulationWithStorage:
    """
    Extends tiled simulation capabilities with disk-based storage for large simulations.
    
    This class provides a way to run simulations that are too large to fit in memory by:
    1. Using the TileManager to dynamically load/unload tiles based on fire activity
    2. Leveraging the DiskStorageManager to offload inactive tiles to disk
    3. Automatically managing memory usage during simulation
    
    Attributes:
        config (ModelConfig): Configuration object with simulation parameters
        grid_width (int): Width of the full simulation grid in cells
        grid_height (int): Height of the full simulation grid in cells
        tile_size (int): Size of each tile in cells
        storage_manager (DiskStorageManager): Manager for disk-based storage
        tile_manager (TileManager): Manager for tile loading/unloading
        active_tiles (set): Set of currently loaded tile coordinates
    """
    
    def __init__(self, config, grid_width, grid_height, tile_size=200, 
                 storage_cache_mb=512, storage_dir="simulation_storage"):
        """
        Initialize the tiled simulation with storage.
        
        Args:
            config (ModelConfig): Configuration object with simulation parameters
            grid_width (int): Width of the full simulation grid in cells
            grid_height (int): Height of the full simulation grid in cells
            tile_size (int): Size of each tile in cells
            storage_cache_mb (int): Size of memory cache for storage manager in MB
            storage_dir (str): Directory to store simulation data
        """
        self.config = config
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.tile_size = tile_size
        
        # Create storage manager
        self.storage_manager = DiskStorageManager(
            base_dir=storage_dir,
            cache_size_mb=storage_cache_mb
        )
        
        # Create tile manager with callback to handle unloaded tiles
        self.tile_manager = TileManager(
            width=grid_width,
            height=grid_height,
            tile_size=tile_size,
            on_tile_unload=self._handle_tile_unload
        )
        
        # Track active tiles (in memory)
        self.active_tiles = set()
        
        # Track simulation state
        self.current_step = 0
        self.simulation_running = False
        
        # Statistics tracking
        self.disk_operations = {'store': 0, 'retrieve': 0}
        self.memory_usage_history = []
        
        print(f"Initialized TiledSimulationWithStorage for {grid_width}x{grid_height} grid")
        print(f"Using {tile_size}x{tile_size} tiles with {storage_cache_mb}MB storage cache")
    
    def _handle_tile_unload(self, tile_x, tile_y, tile_data):
        """
        Callback for when a tile is unloaded from memory.
        
        Args:
            tile_x (int): Tile X coordinate
            tile_y (int): Tile Y coordinate
            tile_data (dict): Tile data to be stored
            
        Returns:
            bool: True if storage was successful
        """
        # Create a key for the tile
        key = f"tile_{tile_x}_{tile_y}_step_{self.current_step}"
        
        # Store tile data to disk
        success = self.storage_manager.store(key, tile_data)
        
        if success:
            # Track statistics
            self.disk_operations['store'] += 1
            # Remove from active tiles
            tile_key = (tile_x, tile_y)
            if tile_key in self.active_tiles:
                self.active_tiles.remove(tile_key)
                
        return success
    
    def _load_tile_from_storage(self, tile_x, tile_y):
        """
        Load a tile from disk storage into memory.
        
        Args:
            tile_x (int): Tile X coordinate
            tile_y (int): Tile Y coordinate
            
        Returns:
            dict: Tile data if found, None otherwise
        """
        # Create key for the most recent version of this tile
        key = f"tile_{tile_x}_{tile_y}_step_{self.current_step}"
        
        # Retrieve from storage
        tile_data = self.storage_manager.retrieve(key)
        
        if tile_data is not None:
            # Track statistics
            self.disk_operations['retrieve'] += 1
            # Add to active tiles
            self.active_tiles.add((tile_x, tile_y))
            
        return tile_data
    
    def initialize_simulation(self, initial_state=None, active_region=None):
        """
        Initialize the simulation with an initial state.
        
        Args:
            initial_state (dict, optional): Initial state for the simulation
            active_region (tuple, optional): Region to initially activate (x, y, width, height)
            
        Returns:
            bool: True if initialization was successful
        """
        import numpy as np
        import psutil
        
        try:
            # Reset simulation state
            self.current_step = 0
            self.active_tiles.clear()
            self.storage_manager.clear_storage()
            self.disk_operations = {'store': 0, 'retrieve': 0}
            self.memory_usage_history = []
            
            # Track memory usage
            current_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            self.memory_usage_history.append({
                'step': self.current_step,
                'memory_mb': current_memory,
                'active_tiles': len(self.active_tiles)
            })
            
            # If no initial state provided, create an empty one
            if initial_state is None:
                # Create a simple initial state with appropriate dimensions
                initial_state = {
                    'fire_state': np.zeros((self.grid_height, self.grid_width), dtype=np.uint8),
                    'vegetation': np.ones((self.grid_height, self.grid_width), dtype=np.float32),
                    'moisture': np.zeros((self.grid_height, self.grid_width), dtype=np.float32)
                }
                
                # You could randomly initialize some fires here
                # For example:
                center_x, center_y = self.grid_width // 2, self.grid_height // 2
                radius = min(10, self.grid_width // 20)
                for y in range(max(0, center_y - radius), min(self.grid_height, center_y + radius)):
                    for x in range(max(0, center_x - radius), min(self.grid_width, center_x + radius)):
                        if ((x - center_x) ** 2 + (y - center_y) ** 2) < radius ** 2:
                            initial_state['fire_state'][y, x] = 1
            
            # Initialize tile manager
            self.tile_manager.initialize(initial_state)
            
            # Activate initial region if specified
            if active_region:
                x, y, width, height = active_region
                self.tile_manager.activate_region(x, y, width, height)
            else:
                # Activate tiles based on fire locations
                fire_indices = np.where(initial_state['fire_state'] > 0)
                for y, x in zip(fire_indices[0], fire_indices[1]):
                    tile_x, tile_y = x // self.tile_size, y // self.tile_size
                    self.tile_manager.activate_tile(tile_x, tile_y)
                    self.active_tiles.add((tile_x, tile_y))
            
            # Store initial tiles to disk
            for tile_x, tile_y in self.tile_manager.get_active_tiles():
                tile_data = self.tile_manager.get_tile_data(tile_x, tile_y)
                key = f"tile_{tile_x}_{tile_y}_step_{self.current_step}"
                self.storage_manager.store(key, tile_data)
                self.disk_operations['store'] += 1
            
            self.simulation_running = True
            return True
            
        except Exception as e:
            print(f"Error initializing simulation: {str(e)}")
            self.simulation_running = False
            return False
    
    def run_step(self):
        """
        Run a single simulation step.
        
        Returns:
            dict: Dictionary with step results
        """
        import psutil
        
        if not self.simulation_running:
            print("Error: Simulation not initialized or already stopped")
            return {"status": "error", "message": "Simulation not running"}
            
        try:
            # Increment step counter
            self.current_step += 1
            
            # Get currently active tiles
            active_tiles = self.tile_manager.get_active_tiles()
            
            # Process each active tile
            updated_tiles = []
            for tile_x, tile_y in active_tiles:
                # Process this tile
                tile_data = self.tile_manager.get_tile_data(tile_x, tile_y)
                
                # Apply simulation logic to the tile (this would call the actual simulation code)
                updated_tile_data = self._process_tile(tile_x, tile_y, tile_data)
                
                # Update the tile in the manager
                self.tile_manager.update_tile_data(tile_x, tile_y, updated_tile_data)
                updated_tiles.append((tile_x, tile_y))
                
                # Store to disk immediately (for large simulations)
                key = f"tile_{tile_x}_{tile_y}_step_{self.current_step}"
                self.storage_manager.store(key, updated_tile_data)
                self.disk_operations['store'] += 1
            
            # Update tile activations based on fire spread
            potentially_new_active_tiles = self._get_potential_new_active_tiles(updated_tiles)
            
            # Activate new tiles as needed
            new_active_tiles = []
            for tile_x, tile_y in potentially_new_active_tiles:
                if self.tile_manager.should_activate_tile(tile_x, tile_y):
                    # Check if we need to load from storage
                    if not self.tile_manager.is_tile_active(tile_x, tile_y):
                        # Try to load from storage
                        tile_data = self._load_tile_from_storage(tile_x, tile_y)
                        
                        if tile_data is not None:
                            # Tile found in storage
                            self.tile_manager.activate_tile(tile_x, tile_y, tile_data)
                            new_active_tiles.append((tile_x, tile_y))
                        else:
                            # Tile not in storage, create new
                            self.tile_manager.activate_tile(tile_x, tile_y)
                            new_active_tiles.append((tile_x, tile_y))
                    else:
                        # Tile already active
                        pass
            
            # Update active tiles tracking
            self.active_tiles = set(self.tile_manager.get_active_tiles())
            
            # Track memory usage
            current_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            self.memory_usage_history.append({
                'step': self.current_step,
                'memory_mb': current_memory,
                'active_tiles': len(self.active_tiles)
            })
            
            # Potentially deactivate tiles not needed anymore
            inactive_tiles = self._identify_inactive_tiles()
            for tile_x, tile_y in inactive_tiles:
                if self.tile_manager.is_tile_active(tile_x, tile_y):
                    # Fetch the data before deactivating (so we can store it)
                    tile_data = self.tile_manager.get_tile_data(tile_x, tile_y)
                    # This will call our _handle_tile_unload callback
                    self.tile_manager.deactivate_tile(tile_x, tile_y)
            
            return {
                "status": "success",
                "step": self.current_step,
                "active_tiles": len(self.active_tiles),
                "updated_tiles": len(updated_tiles),
                "new_active_tiles": len(new_active_tiles),
                "deactivated_tiles": len(inactive_tiles),
                "memory_usage_mb": current_memory
            }
            
        except Exception as e:
            print(f"Error running simulation step: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _process_tile(self, tile_x, tile_y, tile_data):
        """
        Process a single tile's simulation logic.
        
        Args:
            tile_x (int): Tile X coordinate
            tile_y (int): Tile Y coordinate
            tile_data (dict): Current tile data
            
        Returns:
            dict: Updated tile data
        """
        import numpy as np
        
        # This is a placeholder for the actual simulation logic
        # In a real implementation, this would use the core simulation logic
        
        # Get neighboring tiles if they exist
        neighbors = {}
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = tile_x + dx, tile_y + dy
            if self.tile_manager.is_tile_active(nx, ny):
                neighbors[(dx, dy)] = self.tile_manager.get_tile_data(nx, ny)
            else:
                # Try to load from storage
                neighbor_data = self._load_tile_from_storage(nx, ny)
                if neighbor_data is not None:
                    neighbors[(dx, dy)] = neighbor_data
        
        # Create a deep copy of the tile data to avoid modifying the original
        updated_data = {}
        for key, array in tile_data.items():
            if isinstance(array, np.ndarray):
                updated_data[key] = array.copy()
            else:
                # For non-array data
                updated_data[key] = array
        
        # Here we would apply the fire propagation logic
        # For example, update fire_state based on the model's rules
        
        # Apply a simple cellular automaton rule as placeholder
        # Real implementation would use the actual fire model
        if 'fire_state' in updated_data:
            old_fire = tile_data['fire_state'].copy()
            
            # Simple rule: fire spreads to neighbors with vegetation
            for i in range(1, old_fire.shape[0]-1):
                for j in range(1, old_fire.shape[1]-1):
                    if old_fire[i, j] == 0:  # Not burning yet
                        # Check if any neighbors are burning
                        for ni, nj in [(i-1, j), (i+1, j), (i, j-1), (i, j+1)]:
                            if 0 <= ni < old_fire.shape[0] and 0 <= nj < old_fire.shape[1]:
                                if old_fire[ni, nj] == 1:  # Burning neighbor
                                    # Check if there's vegetation to burn
                                    if updated_data['vegetation'][i, j] > 0.2:
                                        # Probability of ignition based on vegetation density
                                        if np.random.random() < updated_data['vegetation'][i, j]:
                                            updated_data['fire_state'][i, j] = 1
                                            # Reduce vegetation
                                            updated_data['vegetation'][i, j] *= 0.8
                    elif old_fire[i, j] == 1:  # Currently burning
                        # Chance of burning out
                        if np.random.random() < 0.1:
                            updated_data['fire_state'][i, j] = 2  # Burned out
                            updated_data['vegetation'][i, j] = 0  # No vegetation left
        
        return updated_data
    
    def _get_potential_new_active_tiles(self, updated_tiles):
        """
        Get tiles that might need to be activated due to fire spread.
        
        Args:
            updated_tiles (list): List of tile coordinates that were updated
            
        Returns:
            set: Set of potential new active tile coordinates
        """
        potential_tiles = set()
        
        # For each updated tile, consider its neighbors
        for tile_x, tile_y in updated_tiles:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = tile_x + dx, tile_y + dy
                
                # Check if neighbor is within grid bounds
                if (0 <= nx < self.grid_width // self.tile_size and
                    0 <= ny < self.grid_height // self.tile_size):
                    potential_tiles.add((nx, ny))
        
        # Remove tiles that are already active
        return potential_tiles - self.active_tiles
    
    def _identify_inactive_tiles(self):
        """
        Identify tiles that can be deactivated and stored to disk.
        
        Returns:
            list: List of tile coordinates that can be deactivated
        """
        inactive_tiles = []
        
        # Get all active tiles
        active_tiles = list(self.active_tiles)
        
        # Check each tile for activity
        for tile_x, tile_y in active_tiles:
            # Check if this tile has fire activity
            tile_data = self.tile_manager.get_tile_data(tile_x, tile_y)
            
            if 'fire_state' in tile_data:
                # Check if there are any actively burning cells (value 1)
                has_active_fire = (tile_data['fire_state'] == 1).any()
                
                if not has_active_fire:
                    # Also check if the tile is adjacent to any active fire tiles
                    has_active_neighbor = False
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = tile_x + dx, tile_y + dy
                        if self.tile_manager.is_tile_active(nx, ny):
                            neighbor_data = self.tile_manager.get_tile_data(nx, ny)
                            if 'fire_state' in neighbor_data and (neighbor_data['fire_state'] == 1).any():
                                has_active_neighbor = True
                                break
                    
                    if not has_active_neighbor:
                        inactive_tiles.append((tile_x, tile_y))
                        
        return inactive_tiles
    
    def run_simulation(self, steps=100):
        """
        Run the simulation for a specified number of steps.
        
        Args:
            steps (int): Number of steps to run
            
        Returns:
            dict: Information about the simulation run
        """
        import psutil
        
        if not self.simulation_running:
            print("Error: Simulation not initialized or already stopped")
            return {"status": "error", "message": "Simulation not running"}
        
        results = []
        max_memory_usage = 0
        
        try:
            for _ in range(steps):
                step_result = self.run_step()
                results.append(step_result)
                
                # Check memory usage
                current_memory = step_result.get('memory_usage_mb', 0)
                max_memory_usage = max(max_memory_usage, current_memory)
                
                # Check if no more active tiles (simulation complete)
                if len(self.active_tiles) == 0:
                    print(f"Simulation completed early at step {self.current_step} - no active tiles remain")
                    break
            
            return {
                "status": "success",
                "steps_completed": len(results),
                "final_step": self.current_step,
                "active_tiles": len(self.active_tiles),
                "max_memory_usage_mb": max_memory_usage,
                "disk_operations": self.disk_operations,
                "final_memory_mb": psutil.Process().memory_info().rss / (1024 * 1024)
            }
            
        except Exception as e:
            print(f"Error running simulation: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_full_state(self):
        """
        Reconstruct the full simulation state from all tiles.
        
        Warning: This can be memory intensive for large simulations!
        
        Returns:
            dict: Full simulation state reconstructed from all tiles
        """
        import numpy as np
        
        try:
            # Create empty arrays for the full state
            full_state = {
                'fire_state': np.zeros((self.grid_height, self.grid_width), dtype=np.uint8),
                'vegetation': np.ones((self.grid_height, self.grid_width), dtype=np.float32),
                'moisture': np.zeros((self.grid_height, self.grid_width), dtype=np.float32)
            }
            
            # Get all tiles from the most recent step
            stored_keys = self.storage_manager.list_stored_items()
            step_keys = [k for k in stored_keys if f"_step_{self.current_step}" in k]
            
            # Process each tile
            for key in step_keys:
                # Extract tile coordinates from key
                parts = key.split('_')
                tile_x = int(parts[1])
                tile_y = int(parts[2])
                
                # Load tile data
                tile_data = self.storage_manager.retrieve(key)
                
                if tile_data is None:
                    continue
                
                # Determine tile dimensions and position
                x_start = tile_x * self.tile_size
                y_start = tile_y * self.tile_size
                
                # Copy data to the full state
                for data_key in ['fire_state', 'vegetation', 'moisture']:
                    if data_key in tile_data:
                        tile_array = tile_data[data_key]
                        t_height, t_width = tile_array.shape
                        
                        # Ensure we don't go out of bounds
                        x_end = min(x_start + t_width, self.grid_width)
                        y_end = min(y_start + t_height, self.grid_height)
                        
                        # Copy data to full state
                        full_state[data_key][y_start:y_end, x_start:x_end] = tile_array[:y_end-y_start, :x_end-x_start]
            
            return full_state
            
        except Exception as e:
            print(f"Error reconstructing full state: {str(e)}")
            return None
    
    def get_fire_front(self):
        """
        Extract just the fire front from the simulation.
        
        Returns:
            numpy.ndarray: Array with fire front marked as 1
        """
        import numpy as np
        
        try:
            # Create an empty array for the fire front
            fire_front = np.zeros((self.grid_height, self.grid_width), dtype=np.uint8)
            
            # Process active tiles first (they're in memory)
            for tile_x, tile_y in self.active_tiles:
                tile_data = self.tile_manager.get_tile_data(tile_x, tile_y)
                
                if 'fire_state' in tile_data:
                    # Get tile position in the grid
                    x_start = tile_x * self.tile_size
                    y_start = tile_y * self.tile_size
                    
                    # Get fire front (burning cells)
                    tile_front = (tile_data['fire_state'] == 1).astype(np.uint8)
                    t_height, t_width = tile_front.shape
                    
                    # Ensure we don't go out of bounds
                    x_end = min(x_start + t_width, self.grid_width)
                    y_end = min(y_start + t_height, self.grid_height)
                    
                    # Copy data to full state
                    fire_front[y_start:y_end, x_start:x_end] = tile_front[:y_end-y_start, :x_end-x_start]
            
            return fire_front
            
        except Exception as e:
            print(f"Error extracting fire front: {str(e)}")
            return None
    
    def get_performance_stats(self):
        """
        Get performance statistics for the simulation.
        
        Returns:
            dict: Performance statistics
        """
        # Calculate statistics from memory usage history
        if len(self.memory_usage_history) > 0:
            # Memory usage
            memory_values = [entry['memory_mb'] for entry in self.memory_usage_history]
            max_memory = max(memory_values)
            avg_memory = sum(memory_values) / len(memory_values)
            
            # Active tiles
            active_tiles_values = [entry['active_tiles'] for entry in self.memory_usage_history]
            max_active_tiles = max(active_tiles_values)
            avg_active_tiles = sum(active_tiles_values) / len(active_tiles_values)
            
            # Storage operations
            total_disk_ops = sum(self.disk_operations.values())
            
            return {
                'steps_completed': self.current_step,
                'max_memory_mb': max_memory,
                'avg_memory_mb': avg_memory,
                'max_active_tiles': max_active_tiles,
                'avg_active_tiles': avg_active_tiles,
                'total_disk_operations': total_disk_ops,
                'disk_operations': self.disk_operations,
                'storage_info': self.storage_manager.get_storage_info()
            }
        else:
            return {
                'steps_completed': 0,
                'status': 'No simulation data available'
            }
    
    def cleanup(self):
        """
        Clean up resources used by the simulation.
        """
        # Clear storage
        self.storage_manager.clear_storage()
        
        # Reset state
        self.simulation_running = False
        self.active_tiles.clear()