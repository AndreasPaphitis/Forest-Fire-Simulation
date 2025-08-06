"""
Forest Model Module

This module provides the definitive implementation of the forest model classes
for fire simulation. It centralizes all forest model implementations into a single
hierarchy to eliminate redundancy and ensure consistency across the codebase.

The model hierarchy consists of:
- BaseForestModel: Abstract base class defining the API
- ForestModel: Standard implementation with full functionality
- MemoryOptimizedForestModel: Extends ForestModel with memory optimizations
- MinimalForestModelStub: Simplified implementation for testing/fallback

This module should be the single source of truth for forest model implementations.
All other modules should import from here rather than defining their own versions.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
# import sys # Removed sys.path manipulation
import time
# import logging # Replaced by get_logger
import numpy as np
import math
import functools # For fallback error handler
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, Union, Any, Callable

# Removed sys.path manipulation block
# current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)  # src directory
# project_root = os.path.dirname(parent_dir)  # project root
# if parent_dir not in sys.path:
#     sys.path.insert(0, parent_dir)
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

# Set up logging using standardized utility
from src.utils.logging_utils import get_logger
logger = get_logger(__name__)

# SciPy sparse matrix imports - MOVED AFTER LOGGER DEFINITION
try:
    from scipy.sparse import lil_matrix, dok_matrix, coo_matrix
    # import scipy # General import if needed for other scipy features, but sparse types are key here
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    # Define placeholders for type hinting or conditional logic if these names are used when HAS_SCIPY is False
    lil_matrix = type(None) # Placeholder if lil_matrix is referenced directly elsewhere
    dok_matrix = type(None) # Placeholder
    coo_matrix = type(None) # Placeholder
    logger.info("SciPy sparse modules (lil_matrix, etc.) not found. Sparse storage will be unavailable.")

# Removed import_helpers logic
# try:
#     from src.utils.import_helpers import try_import
#     HAS_IMPORT_HELPERS = True
# except ImportError:
#     HAS_IMPORT_HELPERS = False
#     logger.warning("import_helpers not available, using fallback import logic")

# Direct import for error handling utilities
try:
    from src.utils.error_handling import (
        handle_errors, 
        log_errors, 
        ModelError, 
        SimulationError,
        ErrorContext # Assuming ErrorContext is used, if not it can be removed from import
    )
    # HAS_ERROR_HANDLING = True # Flag not needed with direct imports
except ImportError:
    # HAS_ERROR_HANDLING = False # Flag not needed
    logger.warning("Core error handling utilities (src.utils.error_handling) not found. Using basic fallback error handling.")
    
    # Fallback error handler and basic error classes
    import logging  # Import logging for fallback error handler
    def handle_errors(func=None, error_type=Exception, default_return=None, log_level=logging.ERROR):
        def decorator(f):
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                try:
                    return f(*args, **kwargs)
                except error_type as e:
                    logger.error(f"Error in {f.__name__} (fallback): {str(e)}") # Adjusted log level
                    return default_return
            return wrapper
        return decorator(func) if func else decorator
        
    class ModelError(Exception): """Error in forest model operations"""
    class SimulationError(Exception): """Error in simulation execution"""
    class ErrorContext: # Dummy fallback
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, traceback): pass

# Direct imports for shared utilities (specific functions, not DEFAULT_ constants)
# and config tools. DEFAULT_ constants will be sourced from ModelConfig.
try:
    from src.utils.shared_utilities import (
        log_once, 
        calculate_memory_requirements, 
        get_progress_iterator,
        # error_handler, # error_handler is defined/imported above
        # Constants like NOT_BURNING will be imported separately or from a dedicated constants module
        # NOT_BURNING, # Removed
        # BURNING, # Removed
        # BURNED_OUT # Removed
    )
    from src.config.config_tools import get_global_config, ModelConfig # get_constant is deprecated
    logger.info("Successfully imported shared utilities and config tools.")
except ImportError as e:
    logger.critical(f"CRITICAL: Could not import core shared utilities or config tools: {e}. This is a fatal error.")
    # Raising the error or exiting might be appropriate here instead of defining fallbacks
    # For now, allow to proceed to see if this was masking the issue, but this block should be reviewed.
    # Fallback for cell states REMOVED - FrameworkCellState should be used or its import failure handled earlier.
    # NOT_BURNING = 0
    # BURNING = 1
    # BURNED_OUT = 2
    # Critical fallbacks for config if absolutely necessary (though program should ideally not run)
    get_global_config = None # type: ignore # Indicates config system is down
    ModelConfig = None # type: ignore # Indicates config system is down

# Import terrain preprocessing utilities
try:
    from src.utils.terrain_preprocessor_rasterio import TerrainPreprocessingConfig, TerrainPreprocessorRasterio
    HAS_TERRAIN_PREPROCESSING = True
except ImportError:
    HAS_TERRAIN_PREPROCESSING = False
    TerrainPreprocessingConfig = None
    TerrainPreprocessorRasterio = None
    logger.warning("Terrain preprocessing utilities not available. Preprocessed terrain loading will be disabled.")

# Removed redefinitions of DEFAULT_MODEL_RESOLUTION, DEFAULT_LAYER_HEIGHT_METERS, etc.
# These will be fetched from ModelConfig via get_global_config()

# Import the centralized CellState Enum from the framework
from src.core.core_simulation_framework import CellState as FrameworkCellState

# Cell states are now imported via FrameworkCellState
# NOT_BURNING = FrameworkCellState.NOT_BURNING.value # Example, actual usage below
# BURNING = FrameworkCellState.BURNING.value
# BURNED_OUT = FrameworkCellState.BURNED_OUT.value

# Import MinimalForestModelStub from core_simulation_framework (moved there)
# from src.core.core_simulation_framework import MinimalForestModelStub

class BaseForestModel(ABC):
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
    """
    
    def __init__(self, 
                 grid_size: Union[int, Tuple[int, int]] = (100, 100), 
                 num_layers: int = 10, 
                 layer_height_meters: float = 2.0, 
                 model_resolution: float = 5.0, 
                 initial_fuel_load: float = 0.0, # Changed default from 5.0 to 0.0
                 config: Optional[ModelConfig] = None, 
                 **kwargs):
        """
        Initialize the base forest model.
        
        Args:
            grid_size: Size of the grid as (width, height) in cells or a single value for square grids
            num_layers: Number of vertical layers to model
            layer_height_meters: Height of each layer in meters
            model_resolution: Spatial resolution in meters
            initial_fuel_load: Default initial fuel load for cells
            config: Optional ModelConfig instance.
            **kwargs: Additional parameters for derived classes (will also be checked for config values if config is None)
        """
        
        # Resolve configuration
        resolved_config = config
        if resolved_config is None:
            # Try to get from kwargs if a 'config' dict/ModelConfig was passed there
            resolved_config = kwargs.get('config') 
            if not isinstance(resolved_config, ModelConfig) and resolved_config is not None: # If it's a dict, try to make ModelConfig
                try:
                    resolved_config = ModelConfig(**resolved_config)
                except TypeError:
                    logger.warning("Could not create ModelConfig from kwargs['config'] dict. Using global config.")
                    resolved_config = None # Fallback to global
            
            if resolved_config is None and get_global_config is not None:
                 resolved_config = get_global_config()
            elif resolved_config is None:
                 logger.warning("No ModelConfig provided and get_global_config is not available. Using default literals.")
        
        self.config = resolved_config # Store the resolved config or None

        # Use config values if available, otherwise use provided arguments or literals
        if self.config:
            final_grid_size = getattr(self.config, 'grid_size', grid_size)
            self.num_layers = getattr(self.config, 'num_layers', num_layers)
            self.layer_height_meters = getattr(self.config, 'layer_height', layer_height_meters) # 'layer_height' in ModelConfig
            self.model_resolution = getattr(self.config, 'model_resolution', model_resolution)
            default_fuel = getattr(self.config, 'initial_fuel_load', initial_fuel_load) # Assuming 'initial_fuel_load' will be in ModelConfig
            default_moisture = getattr(self.config, 'fuel_moisture_baseline', 0.3)
            self.history_interval = getattr(self.config, 'history_keyframe_interval', kwargs.get('history_interval', 10))
            self.store_full_states = getattr(self.config, 'store_full_states', kwargs.get('store_full_states', False))
            self.debug = getattr(self.config, 'debug', kwargs.get('debug', False))
            self.geo_bounds = getattr(self.config, 'geo_bounds', kwargs.get('geo_bounds', None))
        else:
            final_grid_size = grid_size
            self.num_layers = num_layers
            self.layer_height_meters = layer_height_meters
            self.model_resolution = model_resolution
            default_fuel = initial_fuel_load
            default_moisture = kwargs.get('moisture_content', 0.3) # Keep kwarg for this if no config
            self.history_interval = kwargs.get('history_interval', 10)
            self.store_full_states = kwargs.get('store_full_states', False)
            self.debug = kwargs.get('debug', False)
            self.geo_bounds = kwargs.get('geo_bounds', None)

        # Handle grid size as tuple or single value
        if isinstance(final_grid_size, tuple):
            self.grid_size_x, self.grid_size_y = final_grid_size
            self.width, self.height = final_grid_size
        else:
            self.grid_size_x = self.grid_size_y = final_grid_size
            self.width = self.height = final_grid_size
        
        self.grid_size = (self.grid_size_x, self.grid_size_y) # Ensure self.grid_size is always a tuple
        
        # Initialize core data structures
        self.state = np.zeros((self.width, self.height, self.num_layers), dtype=np.int8)
        self.fuel_load = np.full((self.width, self.height, self.num_layers), default_fuel, dtype=np.float32)
        self.canopy_height = np.zeros((self.width, self.height), dtype=np.float32)
        self.moisture_content = np.full((self.width, self.height, self.num_layers), default_moisture, dtype=np.float32)
        self.temperature = np.full((self.width, self.height, self.num_layers), 25.0, dtype=np.float32)
        self.vertical_connectivity = np.ones((self.width, self.height, self.num_layers), dtype=np.float32) * 0.5
        
        # Minimal initialization of other attributes that both modules may expect
        self.wind_direction = np.zeros((self.width, self.height), dtype=np.float32)
        self.wind_speed = np.zeros((self.width, self.height), dtype=np.float32)
        self.terrain_elevation = np.zeros((self.width, self.height), dtype=np.float32)
        self.terrain_slope = np.zeros((self.width, self.height), dtype=np.float32)
        self.terrain_aspect = np.zeros((self.width, self.height), dtype=np.float32)
        
        # Track statistics
        self.stats = {'active_cells': 0, 'burned_cells': 0}
        self.current_step = 0
        
        # History tracking
        self.history = []
        
        # Additional flags
        self.debug = kwargs.get('debug', False)
    
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
            self.state[x, y, z] = FrameworkCellState.BURNING.value # Use FrameworkCellState
    
    @abstractmethod
    def run_simulation(self, max_steps=100, store_full_states=False, **kwargs):
        """
        Run the fire simulation for a specified number of steps.
        
        This is an abstract method that must be implemented by derived classes.
        
        Args:
            max_steps: Maximum number of simulation steps
            store_full_states: Whether to store complete states for visualization
            **kwargs: Additional parameters for derived implementations
            
        Returns:
            Dictionary with simulation results
        """
        pass
    
    @abstractmethod
    def calculate_vertical_connectivity(self):
        """Abstract method to calculate vertical fire spread connectivity."""
        pass

    @abstractmethod
    def initialize_wind(self, wind_direction_deg: float, wind_speed_ms: float):
        """Abstract method to initialize a uniform wind field."""
        pass

    # Decorate with error handling if available
    @handle_errors(error_type=Exception, log_level='ERROR', default_return=False)
    def load_terrain_data(self, dem_file):
        """
        Load terrain data, prioritizing preprocessed terrain data.
        
        Args:
            dem_file: Path to the DEM file (used as fallback only)
            
        Returns:
            True if successful, False otherwise. Will return False if an exception occurs due to the decorator.
        """
        # ALWAYS try preprocessed terrain data first
        if hasattr(self, 'config') and self.config:
            preprocessed_dir = getattr(self.config, 'preprocessed_terrain_dir', None)
            if preprocessed_dir and os.path.exists(preprocessed_dir):
                logger.info("🔄 Using preprocessed terrain data")
                return self._load_preprocessed_terrain_data(preprocessed_dir)
        
        # Only fall back to DEM loading if no preprocessed data available AND DEM file exists
        if dem_file and os.path.exists(dem_file):
            logger.warning("No preprocessed terrain data found, falling back to DEM loading")
            return self._load_dem_terrain_data(dem_file)
        else:
            logger.warning("No terrain data available (no preprocessed terrain or DEM file), using flat terrain")
            return True  # Continue with flat terrain (no terrain elevation data)
    
    def _try_load_shared_terrain(self) -> Optional[Dict[str, np.ndarray]]:
        """
        Try to load terrain data from shared memory.
        
        Returns:
            Dictionary of terrain arrays if available, None otherwise
        """
        try:
            # Check if shared terrain info is available in config
            if hasattr(self, 'config') and self.config and hasattr(self.config, 'shared_terrain_info'):
                from src.utils.shared_terrain import load_shared_terrain_data
                shared_info = self.config.shared_terrain_info
                return load_shared_terrain_data(shared_info)
        except Exception as e:
            logger.debug(f"No shared terrain data available: {e}")
        
        return None
    
    def _load_preprocessed_terrain_data(self, preprocessed_dir: str) -> bool:
        """
        Load preprocessed terrain data from the terrain preprocessor.
        
        Args:
            preprocessed_dir: Directory containing preprocessed terrain data
            
        Returns:
            True if successful, False otherwise
        """
        # Check if terrain preprocessing is available
        if not HAS_TERRAIN_PREPROCESSING:
            logger.error("Terrain preprocessing utilities not available")
            return False
        
        try:
            # Check for shared terrain data first (for memory-efficient parallel processing)
            shared_terrain_data = self._try_load_shared_terrain()
            
            if shared_terrain_data:
                logger.info("✅ Using shared terrain data from memory")
                elevation = shared_terrain_data['elevation']
                slope = shared_terrain_data['slope']
                aspect = shared_terrain_data['aspect']
                barranco_mask = shared_terrain_data['barranco_mask']
                barranco_directions = shared_terrain_data['barranco_directions']
                depression_mask = shared_terrain_data['depression_mask']
                wind_channeling_mask = shared_terrain_data['wind_channeling_mask']
                wind_amplification = shared_terrain_data['wind_amplification']
                wind_direction_modification = shared_terrain_data['wind_direction_modification']
            else:
                # Load the preprocessed data directly from numpy files (no preprocessor needed)
                import numpy as np
                from pathlib import Path
                
                preprocessed_path = Path(preprocessed_dir)
                
                # Load all terrain data
                elevation = np.load(preprocessed_path / "elevation.npy")
                slope = np.load(preprocessed_path / "slope.npy")
                aspect = np.load(preprocessed_path / "aspect.npy")
                barranco_mask = np.load(preprocessed_path / "barranco_mask.npy")
                barranco_directions = np.load(preprocessed_path / "barranco_directions.npy")
                depression_mask = np.load(preprocessed_path / "depression_mask.npy")
                wind_channeling_mask = np.load(preprocessed_path / "wind_channeling_mask.npy")
                wind_amplification = np.load(preprocessed_path / "wind_amplification.npy")
                wind_direction_modification = np.load(preprocessed_path / "wind_direction_modification.npy")
            
            # Load metadata
            metadata_file = preprocessed_path / "metadata.json"
            if metadata_file.exists():
                import json
                with open(metadata_file, 'r') as f:
                    self.terrain_metadata = json.load(f)
            else:
                self.terrain_metadata = {}
            
            # Check if spatial subsetting is needed
            target_shape = (self.height, self.width)  # Model expects (height, width)
            current_shape = elevation.shape
            
            logger.info(f"📊 Preprocessed terrain size: {current_shape[0]} × {current_shape[1]} cells")
            logger.info(f"📊 Target simulation size: {target_shape[0]} × {target_shape[1]} cells")
            
            if current_shape != target_shape:
                logger.info(f"🔄 Extracting {target_shape[0]}×{target_shape[1]} subset from full terrain (preserving ~5m resolution)...")
                
                # Calculate subset boundaries (take center region for representative terrain)
                start_row = (current_shape[0] - target_shape[0]) // 2
                end_row = start_row + target_shape[0]
                start_col = (current_shape[1] - target_shape[1]) // 2  
                end_col = start_col + target_shape[1]
                
                # Ensure boundaries are valid
                start_row = max(0, start_row)
                start_col = max(0, start_col)
                end_row = min(current_shape[0], end_row)
                end_col = min(current_shape[1], end_col)
                
                logger.info(f"📍 Extracting region: rows {start_row}:{end_row}, cols {start_col}:{end_col}")
                
                # Extract subset from all terrain data (preserves original resolution)
                elevation = elevation[start_row:end_row, start_col:end_col]
                slope = slope[start_row:end_row, start_col:end_col]
                aspect = aspect[start_row:end_row, start_col:end_col]
                barranco_mask = barranco_mask[start_row:end_row, start_col:end_col]
                barranco_directions = barranco_directions[start_row:end_row, start_col:end_col]
                depression_mask = depression_mask[start_row:end_row, start_col:end_col]
                wind_channeling_mask = wind_channeling_mask[start_row:end_row, start_col:end_col]
                wind_amplification = wind_amplification[start_row:end_row, start_col:end_col]
                wind_direction_modification = wind_direction_modification[start_row:end_row, start_col:end_col]
                
                final_shape = elevation.shape
                logger.info(f"✅ Successfully extracted terrain subset: {final_shape[0]} × {final_shape[1]} cells")
                logger.info(f"🎯 Preserved original ~5m cell resolution for LiDAR compatibility")
            else:
                logger.info(f"✅ Terrain data size matches simulation grid - no subsetting needed")
            
            # Load the terrain data into the model (transpose to match coordinate system)
            self.terrain_elevation = elevation.T
            self.terrain_slope = slope.T
            self.terrain_aspect = aspect.T
            
            # Load barranco detection results
            self.barranco_mask = barranco_mask.T
            self.barranco_directions = barranco_directions.T
            self.depression_mask = depression_mask.T
            
            # Load wind channeling data
            self.wind_channeling_mask = wind_channeling_mask.T
            self.wind_amplification = wind_amplification.T
            self.wind_direction_modification = wind_direction_modification.T
            
            logger.info(f"✅ Successfully loaded preprocessed terrain data from {preprocessed_dir}")
            logger.info(f"📊 Final grid size: {self.terrain_elevation.shape}")
            logger.info(f"🏞️ Barranco cells: {np.sum(self.barranco_mask)}")
            logger.info(f"💨 Wind channeling cells: {np.sum(self.wind_channeling_mask)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading preprocessed terrain data: {e}")
            return False
    
    def _load_dem_terrain_data(self, dem_file: str) -> bool:
        """
        Load terrain data from a digital elevation model file (original method).
        
        Args:
            dem_file: Path to the DEM file
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(dem_file):
            error_msg = f"DEM file not found: {dem_file}"
            logger.error(error_msg)
            return False
            
        # Attempt to load the DEM file using GDAL
        try:
            from osgeo import gdal
            gdal.UseExceptions()
            
            ds = gdal.Open(dem_file)
            if ds is None:
                error_msg = f"Failed to open DEM file: {dem_file}"
                logger.error(error_msg)
                return False
                
            # Read the elevation data
            band = ds.GetRasterBand(1)
            elevation = band.ReadAsArray()
            
            # Resize to match our grid
            if elevation.shape != (self.height, self.width):
                from skimage.transform import resize
                elevation = resize(elevation, (self.height, self.width), 
                                   preserve_range=True, mode='constant')
            
            # Store the elevation data
            self.terrain_elevation = elevation.T  # Transpose to match our coordinate system
            
            # Calculate slope and aspect (fallback only)
            self._calculate_slope_aspect()
            
            logger.info(f"Successfully loaded terrain data from {dem_file}")
            return True
            
        except ImportError:
            logger.error("GDAL or skimage not available - cannot load terrain data")
            return False
        except Exception as e:
            error_msg = f"Error loading terrain data: {str(e)}"
            logger.error(error_msg)
            return False
    
    def _calculate_slope_aspect(self):
        """
        Calculate slope and aspect from elevation data (FALLBACK ONLY).
        
        This method computes the terrain slope (steepness) and aspect (direction)
        from the digital elevation model data. This should only be used as a fallback
        when preprocessed terrain data is not available.
        
        NOTE: Preprocessed terrain data should be used instead when available.
        """
        # Check if terrain elevation data is available
        if np.all(self.terrain_elevation == 0):
            logger.warning("No terrain elevation data available, skipping slope/aspect calculation")
            return
        
        try:
            # Calculate x and y gradients using central differences
            dy, dx = np.gradient(self.terrain_elevation)
            
            # Convert to slope in degrees and handle division by zero
            slope = np.arctan(np.sqrt(dx**2 + dy**2)) * (180/np.pi)
            self.terrain_slope = slope
            
            # Calculate aspect (direction of slope in degrees) - FIXED FORMULA
            aspect = np.arctan2(-dy, -dx) * (180/np.pi)
            aspect = (aspect + 360) % 360  # Normalize to 0-360 degrees
            self.terrain_aspect = aspect
            
            logger.info("Successfully calculated slope and aspect from terrain data")
            
        except Exception as e:
            logger.error(f"Error calculating slope and aspect: {e}")
    
    def initialize_terrain_wind(self, wind_direction, wind_speed, terrain_effect_strength=None):
        """
        Initialize wind field with terrain effects including barranco detection.
        
        This method creates realistic wind patterns that account for:
        - Basic terrain slope effects
        - Barranco (ravine) detection and wind channeling
        - Wind speed amplification in steep valleys
        - Wind direction alignment with terrain features
        
        Args:
            wind_direction: Base wind direction in degrees (meteorological convention)
            wind_speed: Base wind speed in m/s
            terrain_effect_strength: Override for config terrain_effect_strength
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use config value or provided override
            if terrain_effect_strength is None:
                terrain_effect_strength = getattr(self.config, 'terrain_effect_strength', 0.6) if self.config else 0.6
            
            # OPTIMIZATION: Check if we can use cached results
            cache_key = (wind_direction, wind_speed, terrain_effect_strength)
            if hasattr(self, '_wind_cache') and cache_key in self._wind_cache:
                cached_wind = self._wind_cache[cache_key]
                self.wind_direction = cached_wind['direction'].copy()
                self.wind_speed = cached_wind['speed'].copy()
                self.base_wind_direction = cached_wind['base_direction']
                self.base_wind_speed = cached_wind['base_speed']
                if 'barranco_mask' in cached_wind:
                    self.barranco_mask = cached_wind['barranco_mask'].copy()
                if 'depression_mask' in cached_wind:
                    self.depression_mask = cached_wind['depression_mask'].copy()
                logger.debug("Using cached terrain wind field")
                return True
            
            # Initialize base wind field
            self.wind_direction = np.ones((self.width, self.height)) * wind_direction
            self.wind_speed = np.ones((self.width, self.height)) * wind_speed
            
            # Store original values for reference
            self.base_wind_direction = wind_direction
            self.base_wind_speed = wind_speed
            
            # If no terrain effects desired, return early
            if terrain_effect_strength <= 0:
                logger.info("Initialized uniform wind field (no terrain effects)")
                # Cache the uniform wind field
                self._cache_wind_field(cache_key, uniform_only=True)
                return True
                
            # Check if terrain data is available
            if not hasattr(self, 'terrain_elevation') or self.terrain_elevation is None:
                logger.warning("No terrain elevation data available for terrain wind effects")
                logger.info("Initialized uniform wind field (no elevation data)")
                # Cache the uniform wind field
                self._cache_wind_field(cache_key, uniform_only=True)
                return True
                
            # Ensure slope and aspect are available (should be loaded from preprocessed data)
            if not hasattr(self, 'terrain_slope') or self.terrain_slope is None:
                logger.warning("Terrain slope not available - terrain data may not be properly loaded")
                return False
            
            # Detect barrancos (ravines) and apply wind modifications
            self._detect_and_process_barrancos(terrain_effect_strength)
            
            # Apply general terrain effects (beyond barrancos)
            self._apply_general_terrain_effects(terrain_effect_strength)
            
            # OPTIMIZATION: Cache the computed wind field
            self._cache_wind_field(cache_key)
            
            logger.info(f"Successfully initialized terrain-modified wind field with strength {terrain_effect_strength}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing terrain wind field: {e}")
            # Fallback to uniform wind field
            self.wind_direction = np.ones((self.width, self.height)) * wind_direction
            self.wind_speed = np.ones((self.width, self.height)) * wind_speed
            return False
    
    def _cache_wind_field(self, cache_key, uniform_only=False):
        """
        Cache the computed wind field for reuse.
        
        Args:
            cache_key: Tuple of (wind_direction, wind_speed, terrain_effect_strength)
            uniform_only: Whether this is a uniform wind field (no terrain effects)
        """
        # Initialize cache if it doesn't exist
        if not hasattr(self, '_wind_cache'):
            self._wind_cache = {}
            self._wind_cache_max_size = 5  # Keep only last 5 wind configurations
        
        # Create cache entry
        cache_entry = {
            'direction': self.wind_direction.copy(),
            'speed': self.wind_speed.copy(),
            'base_direction': self.base_wind_direction,
            'base_speed': self.base_wind_speed
        }
        
        # Add terrain-specific data if available
        if not uniform_only:
            if hasattr(self, 'barranco_mask') and self.barranco_mask is not None:
                cache_entry['barranco_mask'] = self.barranco_mask.copy()
            if hasattr(self, 'depression_mask') and self.depression_mask is not None:
                cache_entry['depression_mask'] = self.depression_mask.copy()
        
        # Add to cache
        self._wind_cache[cache_key] = cache_entry
        
        # OPTIMIZATION: Limit cache size to prevent memory issues
        if len(self._wind_cache) > self._wind_cache_max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._wind_cache))
            del self._wind_cache[oldest_key]
    
    def _detect_and_process_barrancos(self, terrain_effect_strength):
        """
        Detect barrancos using both topographic depressions and slope thresholds.
        This hybrid approach is more accurate than slope-only detection.
        
        Args:
            terrain_effect_strength: Master scaling factor for terrain effects
        """
        # Get barranco parameters from config
        barranco_threshold = getattr(self.config, 'barranco_threshold', 30.0) if self.config else 30.0
        barranco_amplification = getattr(self.config, 'barranco_amplification', 2.0) if self.config else 2.0
        barranco_direction_weight = getattr(self.config, 'barranco_direction_weight', 0.8) if self.config else 0.8
        
        # NEW: Add depression detection parameters
        min_depression_depth = getattr(self.config, 'min_depression_depth', 5.0) if self.config else 5.0  # meters
        min_depression_area = getattr(self.config, 'min_depression_area', 4) if self.config else 4  # cells
        
        # 1. DEPRESSION DETECTION - Use preprocessed data if available
        if hasattr(self, 'depression_mask') and self.depression_mask is not None:
            # Use preprocessed depression mask
            depression_mask = self.depression_mask
            logger.info("Using preprocessed depression mask")
        else:
            # Fallback to calculation (should not happen with proper preprocessed data)
            logger.warning("No preprocessed depression mask found, calculating...")
            depression_mask = self._detect_topographic_depressions(min_depression_depth, min_depression_area)
        
        # 2. SLOPE DETECTION - Find steep areas  
        slope_mask = self.terrain_slope >= barranco_threshold
        
        # 3. COMBINED DETECTION - Use preprocessed barranco mask if available
        if hasattr(self, 'barranco_mask') and self.barranco_mask is not None:
            # Use preprocessed barranco mask
            barranco_mask = self.barranco_mask
            logger.info("Using preprocessed barranco mask")
        else:
            # Fallback to calculation (should not happen with proper preprocessed data)
            logger.warning("No preprocessed barranco mask found, calculating...")
            # Barrancos are depressions WITH steep sides
            # Option B: Relaxed - Depression OR (steep slopes near depressions)
            # This catches cases where depression center isn't steep but sides are
            steep_near_depression = self._dilate_mask(depression_mask, radius=2) & slope_mask
            barranco_mask = depression_mask | steep_near_depression
        
        if not np.any(barranco_mask):
            logger.info(f"No barrancos detected (threshold {barranco_threshold}°, min depth {min_depression_depth}m)")
            return
        
        # Log detection results
        depression_count = np.sum(depression_mask)
        slope_count = np.sum(slope_mask) 
        barranco_count = np.sum(barranco_mask)
        total_cells = self.width * self.height
        
        logger.info(f"Barranco detection results:")
        logger.info(f"  Depressions: {depression_count} cells ({depression_count/total_cells*100:.1f}%)")
        logger.info(f"  Steep slopes: {slope_count} cells ({slope_count/total_cells*100:.1f}%)")
        logger.info(f"  Combined barrancos: {barranco_count} cells ({barranco_count/total_cells*100:.1f}%)")
        
        # Calculate ravine orientation for detected barrancos
        if hasattr(self, 'barranco_directions') and self.barranco_directions is not None:
            # Use preprocessed barranco directions
            ravine_directions = self.barranco_directions
            logger.info("Using preprocessed barranco directions")
        else:
            # Fallback to calculation (should not happen with proper preprocessed data)
            logger.warning("No preprocessed barranco directions found, calculating...")
            ravine_directions = self._calculate_ravine_direction(barranco_mask)
        
        # Apply wind speed amplification in barrancos
        amplification_factor = 1.0 + (barranco_amplification - 1.0) * terrain_effect_strength
        self.wind_speed[barranco_mask] *= amplification_factor
        
        # Apply wind direction alignment with ravine orientation
        if barranco_direction_weight > 0:
            effective_weight = barranco_direction_weight * terrain_effect_strength
            
            # Blend original wind direction with ravine direction
            original_direction_rad = np.radians(self.wind_direction[barranco_mask])
            ravine_direction_rad = np.radians(ravine_directions[barranco_mask])
            
            # Calculate weighted average of directions (handling circular nature)
            # Convert to cartesian, average, convert back
            orig_x = np.cos(original_direction_rad)
            orig_y = np.sin(original_direction_rad)
            ravine_x = np.cos(ravine_direction_rad) 
            ravine_y = np.sin(ravine_direction_rad)
            
            # Weighted average
            new_x = (1 - effective_weight) * orig_x + effective_weight * ravine_x
            new_y = (1 - effective_weight) * orig_y + effective_weight * ravine_y
            
            # Convert back to degrees
            new_direction_rad = np.arctan2(new_y, new_x)
            new_direction_deg = np.degrees(new_direction_rad) % 360
            
            self.wind_direction[barranco_mask] = new_direction_deg
        
        # Store barranco mask for visualization and analysis
        self.barranco_mask = barranco_mask
        self.depression_mask = depression_mask  # Store for analysis
        
        avg_amplification = np.mean(self.wind_speed[barranco_mask]) / self.base_wind_speed
        logger.info(f"Applied barranco effects: avg wind amplification = {avg_amplification:.2f}x")
    
    def _calculate_ravine_direction(self, barranco_mask):
        """
        Calculate the primary orientation (direction) of ravines.
        
        Uses the aspect (slope direction) to determine ravine orientation.
        Ravines typically run perpendicular to their steepest slope direction.
        
        Args:
            barranco_mask: Boolean mask indicating barranco locations
            
        Returns:
            Array of ravine directions in degrees for all grid points
        """
        # OPTIMIZATION: Early return if no barrancos detected
        if not np.any(barranco_mask):
            return np.zeros_like(self.terrain_aspect)
        
        # Initialize with aspect (slope direction)
        ravine_directions = np.copy(self.terrain_aspect)
        
        # OPTIMIZATION: Vectorized calculation for barranco areas only
        barranco_indices = np.where(barranco_mask)
        if len(barranco_indices[0]) > 0:
            # For steep areas (barrancos), the ravine runs perpendicular to the aspect
            # Aspect points downslope, ravine runs along the valley floor
            ravine_directions[barranco_mask] = (self.terrain_aspect[barranco_mask] + 90) % 360
            
            # Apply smoothing to avoid abrupt direction changes
            # Use a simple averaging filter for neighboring barranco cells
            ravine_directions = self._optimized_smooth_ravine_directions(ravine_directions, barranco_mask)
        
        return ravine_directions
    
    def _optimized_smooth_ravine_directions(self, directions, mask, kernel_size=3):
        """
        Optimized smoothing of ravine directions to avoid abrupt changes between neighboring cells.
        
        Args:
            directions: Array of directions in degrees
            mask: Boolean mask indicating which cells to smooth
            kernel_size: Size of smoothing kernel (must be odd)
            
        Returns:
            Smoothed direction array
        """
        # OPTIMIZATION: Early return if no cells to smooth
        if not np.any(mask):
            return directions
        
        try:
            from scipy import ndimage
            has_scipy = True
        except ImportError:
            has_scipy = False
            logger.warning("SciPy not available for direction smoothing, using simple averaging")
        
        smoothed = np.copy(directions)
        
        # OPTIMIZATION: Convert to cartesian for averaging (vectorized)
        x_comp = np.cos(np.radians(directions))
        y_comp = np.sin(np.radians(directions))
        
        if has_scipy:
            # OPTIMIZATION: Use scipy for more sophisticated smoothing
            kernel = np.ones((kernel_size, kernel_size)) / (kernel_size ** 2)
            
            # OPTIMIZATION: Apply smoothing only to masked areas
            # Create a mask for the border around barranco areas to ensure proper smoothing
            from scipy.ndimage import binary_dilation
            extended_mask = binary_dilation(mask, iterations=1)
            
            # Smooth x and y components separately
            x_smooth = ndimage.convolve(x_comp, kernel, mode='constant', cval=0)
            y_smooth = ndimage.convolve(y_comp, kernel, mode='constant', cval=0)
            
            # Convert back to degrees (vectorized)
            smooth_directions = np.degrees(np.arctan2(y_smooth, x_smooth)) % 360
            
            # Only update masked areas
            smoothed[mask] = smooth_directions[mask]
        else:
            # OPTIMIZATION: Improved fallback smoothing using numpy
            # Process only the masked cells and their immediate neighbors
            from scipy.ndimage import binary_dilation
            try:
                extended_mask = binary_dilation(mask, iterations=1)
            except ImportError:
                # Manual dilation fallback
                extended_mask = self._dilate_mask(mask, radius=1)
            
            # OPTIMIZATION: Pre-calculate neighbor offsets for better performance
            neighbor_offsets = [
                (-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1)
            ]
            
            # Process only cells that need smoothing
            cells_to_smooth = np.where(extended_mask)
            
            for i, j in zip(cells_to_smooth[0], cells_to_smooth[1]):
                if mask[i, j]:  # Only smooth barranco cells
                    # Collect valid neighbor values
                    neighbor_x = []
                    neighbor_y = []
                    
                    for di, dj in neighbor_offsets:
                        ni, nj = i + di, j + dj
                        if (0 <= ni < self.width and 0 <= nj < self.height and 
                            extended_mask[ni, nj]):
                            neighbor_x.append(x_comp[ni, nj])
                            neighbor_y.append(y_comp[ni, nj])
                    
                    # Add current cell value
                    neighbor_x.append(x_comp[i, j])
                    neighbor_y.append(y_comp[i, j])
                    
                    # Calculate average
                    if neighbor_x:  # Ensure we have neighbors
                        avg_x = np.mean(neighbor_x)
                        avg_y = np.mean(neighbor_y)
                        
                        # Convert back to degrees
                        smooth_direction = np.degrees(np.arctan2(avg_y, avg_x)) % 360
                        smoothed[i, j] = smooth_direction
        
        return smoothed
    
    def _smooth_ravine_directions(self, directions, mask, kernel_size=3):
        """
        Legacy method - now calls optimized version.
        Kept for backward compatibility.
        """
        return self._optimized_smooth_ravine_directions(directions, mask, kernel_size)
    
    def _apply_general_terrain_effects(self, terrain_effect_strength):
        """
        Apply general terrain effects beyond barranco-specific modifications.
        
        This includes:
        - Slope-based wind deflection
        - Ridge acceleration
        - Valley deceleration
        - Wind channeling effects (from preprocessed data)
        
        Args:
            terrain_effect_strength: Master scaling factor for terrain effects
        """
        if terrain_effect_strength <= 0:
            return
        
        # Use preprocessed wind channeling data if available
        if hasattr(self, 'wind_amplification') and self.wind_amplification is not None:
            # Apply preprocessed wind amplification
            self.wind_speed *= self.wind_amplification
            logger.info("Applied preprocessed wind amplification")
        else:
            # Fallback to calculation (should not happen with proper preprocessed data)
            logger.warning("No preprocessed wind amplification found, calculating...")
            # Calculate terrain modification factors
            slope_factor = self._calculate_slope_wind_factor()
            elevation_factor = self._calculate_elevation_wind_factor()
            
            # Apply modifications with terrain_effect_strength scaling
            self.wind_speed *= (1.0 + (slope_factor - 1.0) * terrain_effect_strength)
            self.wind_speed *= (1.0 + (elevation_factor - 1.0) * terrain_effect_strength)
        
        # Apply wind direction modifications if available
        if hasattr(self, 'wind_direction_modification') and self.wind_direction_modification is not None:
            # Apply preprocessed wind direction modifications
            self.wind_direction += self.wind_direction_modification
            self.wind_direction = self.wind_direction % 360  # Normalize to 0-360
            logger.info("Applied preprocessed wind direction modifications")
        
        # Ensure wind speed doesn't become negative
        self.wind_speed = np.maximum(self.wind_speed, 0.1)
        
        logger.debug("Applied general terrain effects to wind field")
    
    def _calculate_slope_wind_factor(self):
        """
        Calculate wind speed modification based on slope.
        Steeper slopes generally increase wind speed due to acceleration.
        
        Returns:
            Array of wind speed factors (1.0 = no change, >1.0 = acceleration)
        """
        # Normalize slope to 0-1 range (assuming max realistic slope of 60°)
        max_slope = 60.0
        normalized_slope = np.clip(self.terrain_slope / max_slope, 0, 1)
        
        # Moderate acceleration on slopes (10-30% increase)
        slope_factor = 1.0 + 0.3 * normalized_slope
        
        return slope_factor
    
    def _calculate_elevation_wind_factor(self):
        """
        Calculate wind speed modification based on relative elevation.
        Higher elevations typically have higher wind speeds.
        
        Returns:
            Array of wind speed factors (1.0 = no change, >1.0 = acceleration)
        """
        if np.all(self.terrain_elevation == 0):
            return np.ones((self.width, self.height))
            
        # Normalize elevation to 0-1 range
        min_elev = np.min(self.terrain_elevation)
        max_elev = np.max(self.terrain_elevation)
        
        if max_elev <= min_elev:
            return np.ones((self.width, self.height))
            
        normalized_elevation = (self.terrain_elevation - min_elev) / (max_elev - min_elev)
        
        # Moderate elevation effect (up to 20% increase at highest points)
        elevation_factor = 1.0 + 0.2 * normalized_elevation
        
        return elevation_factor

    def _detect_topographic_depressions(self, min_depth_m, min_area_cells):
        """
        Detect topographic depressions (valleys/ravines) in the DEM (REDUNDANT).
        
        This method is redundant when using preprocessed terrain data, as depression
        detection is already performed during terrain preprocessing.
        
        Args:
            min_depth_m: Minimum depression depth in meters
            min_area_cells: Minimum depression area in cells
        
        Returns:
            Boolean mask of depression areas
            
        NOTE: This method should not be called when using preprocessed terrain data.
        """
        try:
            from scipy.ndimage import label, minimum_filter
            HAS_SCIPY = True
        except ImportError:
            HAS_SCIPY = False
            logger.warning("SciPy not available for depression detection, using fallback method")
        
        if not HAS_SCIPY:
            # Fallback: simple local minima detection without scipy
            return self._simple_depression_detection(min_depth_m, min_area_cells)
        
        # OPTIMIZATION: Use larger kernel for better performance with large grids
        kernel_size = min(5, max(3, min(self.width, self.height) // 20))  # Adaptive kernel size
        
        # 1. Find local minima using minimum filter (vectorized)
        local_minima = minimum_filter(self.terrain_elevation, size=kernel_size)
        is_local_minimum = (self.terrain_elevation == local_minima)
        
        # OPTIMIZATION: Early termination if no local minima found
        if not np.any(is_local_minimum):
            return np.zeros_like(self.terrain_elevation, dtype=bool)
        
        # 2. Calculate depression depth for each potential depression
        depression_mask = np.zeros_like(self.terrain_elevation, dtype=bool)
        
        # Label connected minimum regions (vectorized)
        labeled_minima, num_labels = label(is_local_minimum)
        
        # OPTIMIZATION: Process only if we have reasonable number of labels
        if num_labels > 1000:  # Too many small regions, use simplified approach
            logger.warning(f"Too many depression regions ({num_labels}), using simplified detection")
            return self._simplified_depression_detection(min_depth_m, min_area_cells)
        
        # OPTIMIZATION: Pre-calculate elevation statistics for faster processing
        elevation_min = np.min(self.terrain_elevation)
        elevation_max = np.max(self.terrain_elevation)
        elevation_range = elevation_max - elevation_min
        
        # Skip if terrain is too flat
        if elevation_range < min_depth_m:
            return np.zeros_like(self.terrain_elevation, dtype=bool)
        
        for label_id in range(1, num_labels + 1):
            # Get this depression region
            region_mask = (labeled_minima == label_id)
            region_size = np.sum(region_mask)
            
            # OPTIMIZATION: Early skip for small regions
            if region_size < min_area_cells:
                continue
            
            # OPTIMIZATION: Use vectorized operations for elevation calculations
            region_elevations = self.terrain_elevation[region_mask]
            min_elevation = np.min(region_elevations)
            
            # Find surrounding elevation (expand region and take border)
            expanded_mask = self._dilate_mask(region_mask, radius=2)
            border_mask = expanded_mask & ~region_mask
            
            if not np.any(border_mask):
                continue  # No border found
            
            # OPTIMIZATION: Vectorized border elevation calculation
            border_elevations = self.terrain_elevation[border_mask]
            surrounding_elevation = np.mean(border_elevations)
            depression_depth = surrounding_elevation - min_elevation
            
            # Keep if deep enough
            if depression_depth >= min_depth_m:
                depression_mask[region_mask] = True
        
        return depression_mask

    def _simplified_depression_detection(self, min_depth_m, min_area_cells):
        """
        Simplified depression detection for large grids with many small regions.
        Uses gradient-based approach for better performance.
        """
        # OPTIMIZATION: Use gradient-based detection for large grids
        try:
            from scipy.ndimage import sobel
            # Calculate gradient magnitude
            grad_x = sobel(self.terrain_elevation, axis=1)
            grad_y = sobel(self.terrain_elevation, axis=0)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            # Find areas with low gradient (potential depressions)
            low_gradient_threshold = np.percentile(gradient_magnitude, 25)  # Bottom 25%
            potential_depressions = gradient_magnitude < low_gradient_threshold
            
            # Filter by minimum depth using local statistics
            from scipy.ndimage import uniform_filter
            local_mean = uniform_filter(self.terrain_elevation, size=5)
            depth_map = local_mean - self.terrain_elevation
            
            # Combine conditions
            depression_mask = potential_depressions & (depth_map >= min_depth_m)
            
            # Area filtering
            if min_area_cells > 1:
                labeled_depressions, num_regions = label(depression_mask)
                for region_id in range(1, num_regions + 1):
                    region_size = np.sum(labeled_depressions == region_id)
                    if region_size < min_area_cells:
                        depression_mask[labeled_depressions == region_id] = False
            
            return depression_mask
            
        except ImportError:
            # Fallback to simple method
            return self._simple_depression_detection(min_depth_m, min_area_cells)

    def _simple_depression_detection(self, min_depth_m, min_area_cells):
        """
        Simple depression detection fallback when SciPy is not available.
        OPTIMIZED: Uses vectorized operations where possible.
        """
        # OPTIMIZATION: Pre-calculate elevation statistics
        elevation_min = np.min(self.terrain_elevation)
        elevation_max = np.max(self.terrain_elevation)
        
        # Skip if terrain is too flat
        if (elevation_max - elevation_min) < min_depth_m:
            return np.zeros_like(self.terrain_elevation, dtype=bool)
        
        depression_mask = np.zeros_like(self.terrain_elevation, dtype=bool)
        
        # OPTIMIZATION: Use vectorized neighbor comparison where possible
        # Create padded elevation array for efficient neighbor access
        padded_elevation = np.pad(self.terrain_elevation, 1, mode='edge')
        
        # OPTIMIZATION: Process in blocks for better cache performance
        block_size = 50  # Process 50x50 blocks at a time
        
        for block_i in range(0, self.width, block_size):
            for block_j in range(0, self.height, block_size):
                end_i = min(block_i + block_size, self.width)
                end_j = min(block_j + block_size, self.height)
                
                # Get block coordinates (skip borders)
                for i in range(max(1, block_i), min(end_i, self.width - 1)):
                    for j in range(max(1, block_j), min(end_j, self.height - 1)):
                        center_elev = self.terrain_elevation[i, j]
                        
                        # OPTIMIZATION: Use pre-padded array for faster neighbor access
                        neighbors = padded_elevation[i:i+3, j:j+3]
                        neighbor_mean = np.mean(neighbors[neighbors != center_elev])
                        
                        # Check if this is a depression
                        depth = neighbor_mean - center_elev
                        if depth >= min_depth_m:
                            depression_mask[i, j] = True
        
        # OPTIMIZATION: Use vectorized area filtering if possible
        if min_area_cells > 1:
            try:
                from scipy.ndimage import label
                labeled_depressions, num_regions = label(depression_mask)
                
                # OPTIMIZATION: Vectorized size calculation
                region_sizes = np.bincount(labeled_depressions.ravel())[1:]  # Skip background
                valid_regions = np.where(region_sizes >= min_area_cells)[0] + 1
                
                # Create final mask
                result_mask = np.zeros_like(depression_mask)
                for region_id in valid_regions:
                    result_mask[labeled_depressions == region_id] = True
                
                depression_mask = result_mask
                
            except ImportError:
                # Fallback to manual flood fill
                depression_mask = self._manual_area_filtering(depression_mask, min_area_cells)
        
        return depression_mask

    def _manual_area_filtering(self, mask, min_area_cells):
        """
        Manual area filtering using optimized flood fill.
        OPTIMIZED: Uses stack-based flood fill with early termination.
        """
        result_mask = np.zeros_like(mask)
        visited = np.zeros_like(mask, dtype=bool)
        
        # OPTIMIZATION: Pre-allocate stack for better performance
        max_stack_size = min_area_cells * 4  # Estimate maximum stack size
        stack = []
        
        for i in range(self.width):
            for j in range(self.height):
                if mask[i, j] and not visited[i, j]:
                    # OPTIMIZATION: Use stack-based flood fill with early termination
                    component_size = self._optimized_flood_fill_count(mask, visited, i, j, max_stack_size)
                    if component_size >= min_area_cells:
                        # Mark this component as valid
                        self._optimized_flood_fill_mark(mask, result_mask, i, j, max_stack_size)
        
        return result_mask

    def _optimized_flood_fill_count(self, mask, visited, start_i, start_j, max_stack_size):
        """
        Optimized flood fill count with early termination and efficient stack management.
        """
        # OPTIMIZATION: Use list as stack for better performance than deque for small components
        stack = [(start_i, start_j)]
        count = 0
        
        # OPTIMIZATION: Early termination if component is too small
        while stack and count < max_stack_size:
            i, j = stack.pop()
            
            # OPTIMIZATION: Combined boundary and visited check
            if (i < 0 or i >= self.width or j < 0 or j >= self.height or 
                visited[i, j] or not mask[i, j]):
                continue
            
            visited[i, j] = True
            count += 1
            
            # OPTIMIZATION: Add neighbors in order for better cache locality
            # Add 8-connected neighbors in a predictable order
            neighbors = [
                (i-1, j-1), (i-1, j), (i-1, j+1),
                (i, j-1),             (i, j+1),
                (i+1, j-1), (i+1, j), (i+1, j+1)
            ]
            
            for ni, nj in neighbors:
                if (0 <= ni < self.width and 0 <= nj < self.height and 
                    not visited[ni, nj] and mask[ni, nj]):
                    stack.append((ni, nj))
        
        return count

    def _optimized_flood_fill_mark(self, source_mask, target_mask, start_i, start_j, max_stack_size):
        """
        Optimized flood fill mark with efficient stack management.
        """
        stack = [(start_i, start_j)]
        
        while stack:
            i, j = stack.pop()
            
            # OPTIMIZATION: Combined boundary and target check
            if (i < 0 or i >= self.width or j < 0 or j >= self.height or 
                target_mask[i, j] or not source_mask[i, j]):
                continue
            
            target_mask[i, j] = True
            
            # OPTIMIZATION: Add neighbors in order for better cache locality
            neighbors = [
                (i-1, j-1), (i-1, j), (i-1, j+1),
                (i, j-1),             (i, j+1),
                (i+1, j-1), (i+1, j), (i+1, j+1)
            ]
            
            for ni, nj in neighbors:
                if (0 <= ni < self.width and 0 <= nj < self.height and 
                    not target_mask[ni, nj] and source_mask[ni, nj]):
                    stack.append((ni, nj))

    def _dilate_mask(self, mask, radius=1):
        """
        Optimized mask dilation with vectorized operations.
        """
        try:
            from scipy.ndimage import binary_dilation
            
            # OPTIMIZATION: Use smaller kernel for better performance
            if radius > 3:
                # For large radius, use multiple small dilations
                result = mask.copy()
                for _ in range(radius):
                    result = binary_dilation(result)
                return result
            else:
                # Create circular kernel
                y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
                kernel = x*x + y*y <= radius*radius
                
                return binary_dilation(mask, structure=kernel)
        except ImportError:
            # Fallback without scipy
            return self._optimized_simple_dilate(mask, radius)

    def _optimized_simple_dilate(self, mask, radius):
        """
        Optimized simple dilation without scipy.
        OPTIMIZATION: Uses vectorized operations and efficient memory access.
        """
        # OPTIMIZATION: Early return for empty mask
        if not np.any(mask):
            return np.zeros_like(mask)
        
        result = np.copy(mask)
        
        # OPTIMIZATION: Pre-calculate kernel coordinates
        kernel_coords = []
        for di in range(-radius, radius + 1):
            for dj in range(-radius, radius + 1):
                if di*di + dj*dj <= radius*radius:  # Circular kernel
                    kernel_coords.append((di, dj))
        
        # OPTIMIZATION: Process only cells that are True in the original mask
        true_indices = np.where(mask)
        
        for i, j in zip(true_indices[0], true_indices[1]):
            # Apply kernel to this cell
            for di, dj in kernel_coords:
                ni, nj = i + di, j + dj
                if 0 <= ni < self.width and 0 <= nj < self.height:
                    result[ni, nj] = True
        
        return result


class ForestModel(BaseForestModel):
    """
    Standard implementation of the forest model.
    
    This class provides a complete implementation of the BaseForestModel interface
    with all required functionality for fire simulation. It serves as the standard
    implementation that balances functionality and performance.
    """
    
    def __init__(self, 
                 grid_size: Union[int, Tuple[int, int]] = (100, 100), 
                 num_layers: int = 10, 
                 layer_height_meters: float = 2.0, 
                 model_resolution: float = 5.0,
                 initial_fuel_load: float = 0.0,
                 config: Optional[ModelConfig] = None,
                 **kwargs):
        """
        Initialize the forest model.
        
        Args:
            grid_size: Size of the grid in cells (grid is square by default)
            num_layers: Number of vertical layers
            layer_height_meters: Height of each layer in meters
            model_resolution: Spatial resolution in meters
            initial_fuel_load: Default initial fuel load for cells
            config: Optional ModelConfig instance
            **kwargs: Additional parameters
        """
        # Pass config explicitly to parent if provided, else parent will try to get global
        # Ensure kwargs are passed for other potential base initializations
        all_params = {**kwargs, 'config': config, 'grid_size': grid_size, 'num_layers': num_layers, 
                      'layer_height_meters': layer_height_meters, 'model_resolution': model_resolution, 
                      'initial_fuel_load': initial_fuel_load}
        super().__init__(**all_params)
        
        # Initialize additional attributes specific to ForestModel
        self._initialize_attributes(**kwargs)
        # Wind fields are initialized by initialize_wind or initialize_terrain_wind
    
    def _initialize_attributes(self, **kwargs):
        """Initialize model attributes like state, fuel, canopy, etc."""
        # Initialize fire spread parameters
        self.ignition_temperature = kwargs.get('ignition_temperature', 300.0)  # Celsius
        self.ambient_temperature = kwargs.get('ambient_temperature', 25.0)  # Celsius
        self.relative_humidity = kwargs.get('relative_humidity', 30.0)  # %
        
        # Initialize simulation parameters
        self.time_step_seconds = kwargs.get('time_step_seconds', 60.0)
        self.max_simulation_time = kwargs.get('max_simulation_time', 24.0 * 3600)  # 24 hours in seconds
        
        # Initialize visualization parameters
        self.visualization_config = kwargs.get('visualization_config', {
            'color_map': 'hot',
            'show_terrain': True,
            'show_wind': True,
            'show_3d': False
        })
        
        # Initialize attributes needed for visualization and analysis
        self._initialize_visualization_attributes()
    
    def _initialize_visualization_attributes(self):
        """
        Initialize attributes required for visualization and simulation tracking.
        This ensures the model has all necessary attributes for the visualization system.
        """
        # Initialize fire history tracking
        if not hasattr(self, 'fire_history'):
            self.fire_history = []
        
        # Initialize spread statistics tracking
        if not hasattr(self, 'spread_stats'):
            self.spread_stats = {
                'horizontal_spread': 0,
                'vertical_spread': 0,
                'ember_spread': 0,
                'ember_ignitions': 0,
                'total_ignitions': 0,
                'wind_assisted_spread': 0,
                'slope_assisted_spread': 0,
                'barranco_assisted_spread': 0
            }
        
        # Initialize simulation statistics tracking
        if not hasattr(self, 'stats'):
            self.stats = {
                'active_cells': 0,
                'burned_cells': 0,
                'total_cells': 0,
                'max_active_cells': 0,
                'simulation_steps': 0
            }
        
        # Ensure wind attributes exist (even if not set)
        if not hasattr(self, 'wind_speed'):
            self.wind_speed = 0.0
        if not hasattr(self, 'wind_direction'):
            self.wind_direction = 0.0
        
        # Reference to simulation engine for access to detailed history
        self.simulation_engine = None
        
        logger.debug("Visualization attributes initialized for ForestModel")
    
    def set_simulation_engine(self, engine):
        """
        Set reference to the simulation engine for access to detailed tracking.
        
        Args:
            engine: FireSimulationEngine instance
        """
        self.simulation_engine = engine
        logger.debug("Simulation engine reference set for ForestModel")
    
    def update_stats(self, active_cells=None, burned_cells=None, step=None):
        """
        Update simulation statistics for tracking and visualization.
        
        Args:
            active_cells: Number of currently active (burning) cells
            burned_cells: Number of burned out cells  
            step: Current simulation step
        """
        if active_cells is not None:
            self.stats['active_cells'] = active_cells
            # Use get() with default to handle missing key
            current_max = self.stats.get('max_active_cells', 0)
            self.stats['max_active_cells'] = max(current_max, active_cells)
        
        if burned_cells is not None:
            self.stats['burned_cells'] = burned_cells
            
        if step is not None:
            self.stats['simulation_steps'] = step
            
        # Calculate total affected cells with safe access
        active = self.stats.get('active_cells', 0)
        burned = self.stats.get('burned_cells', 0)
        self.stats['total_cells'] = active + burned
    
    def add_history_entry(self, step, active_cells, burned_cells, state=None):
        """
        Add an entry to the fire history for visualization.
        
        Args:
            step: Simulation step number
            active_cells: Number of active cells at this step
            burned_cells: Number of burned cells at this step
            state: Optional state array (can be None for memory optimization)
        """
        entry = {
            'step': step,
            'active_cells': active_cells,
            'burned_cells': burned_cells,
            'state': state
        }
        
        self.fire_history.append(entry)
        
        # Keep history size manageable (keep last 1000 entries)
        if len(self.fire_history) > 1000:
            self.fire_history = self.fire_history[-1000:]
    
    def increment_spread_stat(self, spread_type):
        """
        Increment a specific spread statistic counter.
        
        Args:
            spread_type: Type of spread ('horizontal_spread', 'vertical_spread', etc.)
        """
        if spread_type in self.spread_stats:
            self.spread_stats[spread_type] += 1
        else:
            logger.warning(f"Unknown spread type: {spread_type}")
    
    def get_visualization_data(self):
        """
        Get all data needed for visualization in a standardized format.
        
        Returns:
            Dictionary containing all visualization data
        """
        return {
            'state': getattr(self, 'state', None),
            'fire_history': getattr(self, 'fire_history', []),
            'spread_stats': getattr(self, 'spread_stats', {}),
            'stats': getattr(self, 'stats', {}),
            'wind_speed': getattr(self, 'wind_speed', 0.0),
            'wind_direction': getattr(self, 'wind_direction', 0.0),
            'grid_size': (getattr(self, 'width', 0), getattr(self, 'height', 0)),
            'num_layers': getattr(self, 'num_layers', 1),
            'model_resolution': getattr(self, 'model_resolution', 1.0)
        }
    
    def get_barranco_analysis(self):
        """
        Get comprehensive analysis of detected barrancos for visualization and research.
        
        Returns:
            Dictionary containing barranco detection results and statistics
        """
        if not hasattr(self, 'barranco_mask') or self.barranco_mask is None:
            return {
                'detected': False,
                'message': 'No barranco detection has been performed. Run initialize_terrain_wind() first.'
            }
        
        analysis = {
            'detected': True,
            'total_cells': np.sum(self.barranco_mask),
            'percentage_of_terrain': (np.sum(self.barranco_mask) / (self.width * self.height)) * 100,
            'barranco_mask': self.barranco_mask.copy(),
            'config_parameters': {}
        }
        
        # Add depression analysis if available
        if hasattr(self, 'depression_mask') and self.depression_mask is not None:
            analysis['depression_analysis'] = {
                'total_depression_cells': np.sum(self.depression_mask),
                'percentage_depressions': (np.sum(self.depression_mask) / (self.width * self.height)) * 100,
                'depression_mask': self.depression_mask.copy(),
                'overlap_with_barrancos': np.sum(self.depression_mask & self.barranco_mask),
                'depression_only': np.sum(self.depression_mask & ~self.barranco_mask)
            }
        
        # Add configuration parameters if available
        if self.config:
            analysis['config_parameters'] = {
                'barranco_threshold': getattr(self.config, 'barranco_threshold', 'N/A'),
                'barranco_amplification': getattr(self.config, 'barranco_amplification', 'N/A'),
                'barranco_direction_weight': getattr(self.config, 'barranco_direction_weight', 'N/A'),
                'terrain_effect_strength': getattr(self.config, 'terrain_effect_strength', 'N/A'),
                'min_depression_depth': getattr(self.config, 'min_depression_depth', 'N/A'),
                'min_depression_area': getattr(self.config, 'min_depression_area', 'N/A')
            }
        
        # Calculate wind modifications if available
        if hasattr(self, 'base_wind_speed') and hasattr(self, 'wind_speed'):
            wind_amplification = self.wind_speed[self.barranco_mask] / self.base_wind_speed
            analysis['wind_modifications'] = {
                'mean_amplification': np.mean(wind_amplification),
                'max_amplification': np.max(wind_amplification),
                'min_amplification': np.min(wind_amplification),
                'std_amplification': np.std(wind_amplification)
            }
        
        # Calculate terrain characteristics in barranco areas
        if hasattr(self, 'terrain_slope') and self.terrain_slope is not None:
            barranco_slopes = self.terrain_slope[self.barranco_mask]
            analysis['terrain_characteristics'] = {
                'mean_slope_degrees': np.mean(barranco_slopes),
                'max_slope_degrees': np.max(barranco_slopes),
                'min_slope_degrees': np.min(barranco_slopes),
                'std_slope_degrees': np.std(barranco_slopes)
            }
        
        # Calculate elevation characteristics if available
        if hasattr(self, 'terrain_elevation') and self.terrain_elevation is not None:
            barranco_elevations = self.terrain_elevation[self.barranco_mask]
            analysis['elevation_characteristics'] = {
                'mean_elevation': np.mean(barranco_elevations),
                'max_elevation': np.max(barranco_elevations),
                'min_elevation': np.min(barranco_elevations),
                'elevation_range': np.max(barranco_elevations) - np.min(barranco_elevations)
            }
            
            # Add depression depth analysis if depression mask is available
            if hasattr(self, 'depression_mask') and self.depression_mask is not None:
                depression_elevations = self.terrain_elevation[self.depression_mask]
                if len(depression_elevations) > 0:
                    analysis['depression_characteristics'] = {
                        'mean_depression_elevation': np.mean(depression_elevations),
                        'min_depression_elevation': np.min(depression_elevations),
                        'max_depression_elevation': np.max(depression_elevations)
                    }
        
        # Calculate spatial distribution statistics
        barranco_indices = np.where(self.barranco_mask)
        if len(barranco_indices[0]) > 0:
            analysis['spatial_distribution'] = {
                'center_x': np.mean(barranco_indices[1]),  # Note: indices are (y, x)
                'center_y': np.mean(barranco_indices[0]),
                'extent_x': np.max(barranco_indices[1]) - np.min(barranco_indices[1]),
                'extent_y': np.max(barranco_indices[0]) - np.min(barranco_indices[0]),
                'bbox': {
                    'min_x': np.min(barranco_indices[1]),
                    'max_x': np.max(barranco_indices[1]),
                    'min_y': np.min(barranco_indices[0]),
                    'max_y': np.max(barranco_indices[0])
                }
            }
        
        return analysis
    
    def run_simulation(self, max_steps=100, store_full_states=False, **kwargs):
        """
        Run the fire simulation for the given number of steps.
        
        Args:
            max_steps: Maximum number of steps to simulate
            store_full_states: Whether to store the history of fire states
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with simulation results
        """
        logger.info(f"Running simulation for {max_steps} steps")
        
        # Implementation would typically:
        # 1. Initialize tracking variables
        # 2. Run the simulation loop, processing each step
        # 3. Return results
        
        # This is a placeholder - full implementation would be in fire_simulation_engine.py
        self.current_step = max_steps
        
        # Placeholder for simulation results
        results = {
            'steps_completed': max_steps,
            'active_cells': self.stats.get('active_cells', 0),
            'burned_cells': self.stats.get('burned_cells', 0),
            'model': self
        }
        
        return results
    
    def calculate_vertical_connectivity(self):
        """
        Calculate vertical connectivity between layers based on fuel load.
        
        Returns:
            Numpy array of vertical connectivity values
        """
        logger.info("Calculating vertical connectivity between layers")
        
        # Get max_fuel_value from config
        max_fuel = getattr(self.config, 'max_fuel_value', 10.0) if self.config else 10.0
        if max_fuel <= 0: max_fuel = 10.0 # Prevent division by zero if config is bad

        # Calculate vertical connectivity based on fuel load in adjacent layers
        for z in range(self.num_layers - 1):
            # Normalize fuel load for calculation
            fuel_lower = np.clip(self.fuel_load[:, :, z] / max_fuel, 0, 1)
            fuel_upper = np.clip(self.fuel_load[:, :, z+1] / max_fuel, 0, 1)
            
            # Connectivity is the product of fuel availability in adjacent layers
            # More fuel in both layers = better connectivity
            self.vertical_connectivity[:, :, z] = np.sqrt(fuel_lower * fuel_upper)
        
        return self.vertical_connectivity

    def initialize_wind(self, wind_direction_deg: float, wind_speed_ms: float):
        """Initialize a uniform wind field across the model."""
        logger.info(f"Initializing uniform wind: Speed {wind_speed_ms} m/s, Direction {wind_direction_deg}°")
        if not hasattr(self, 'wind_speed_ms') or self.wind_speed_ms is None or \
           self.wind_speed_ms.shape != (self.grid_size_x, self.grid_size_y):
            self.wind_speed_ms = np.full((self.grid_size_x, self.grid_size_y), wind_speed_ms, dtype=np.float32)
        else:
            self.wind_speed_ms.fill(wind_speed_ms)

        if not hasattr(self, 'wind_direction_rad') or self.wind_direction_rad is None or \
           self.wind_direction_rad.shape != (self.grid_size_x, self.grid_size_y):
            self.wind_direction_rad = np.full((self.grid_size_x, self.grid_size_y), math.radians(wind_direction_deg), dtype=np.float32)
        else:
            self.wind_direction_rad.fill(math.radians(wind_direction_deg))
        logger.debug("Uniform wind field initialized.")


class SparseLayerAccessor:
    """
    Provides numpy-like array access to sparse storage layers.
    This allows existing code to work transparently with sparse storage.
    """
    
    def __init__(self, sparse_layers, width, height, num_layers, default_value=0):
        self.sparse_layers = sparse_layers
        self.width = width
        self.height = height
        self.num_layers = num_layers
        self.default_value = default_value
    
    def __getitem__(self, key):
        """Support array-like indexing."""
        if isinstance(key, tuple) and len(key) == 3:
            x, y, z = key
            if isinstance(z, int) and 0 <= z < self.num_layers:
                if 0 <= x < self.width and 0 <= y < self.height:
                    # For lil_matrix, check if the row has any data for this column
                    sparse_matrix = self.sparse_layers[z]
                    if x < len(sparse_matrix.rows) and y in sparse_matrix.rows[x]:
                        # Cell was explicitly set, return actual value (even if 0)
                        return sparse_matrix[x, y]
                    else:
                        # Cell was never set, return default
                        return self.default_value
                return self.default_value
            else:
                raise IndexError(f"Layer index {z} out of range")
        elif isinstance(key, tuple) and len(key) == 2:
            # Handle 2D access for single layer
            x, y = key
            if 0 <= x < self.width and 0 <= y < self.height and len(self.sparse_layers) > 0:
                sparse_matrix = self.sparse_layers[0]
                if x < len(sparse_matrix.rows) and y in sparse_matrix.rows[x]:
                    return sparse_matrix[x, y]
                else:
                    return self.default_value
            return self.default_value
        else:
            # Handle slice access
            if isinstance(key, slice) or (isinstance(key, tuple) and any(isinstance(k, slice) for k in key)):
                return self._handle_slice_access(key)
            return self.default_value
    
    def __setitem__(self, key, value):
        """Support array-like assignment."""
        if isinstance(key, tuple) and len(key) == 3:
            x, y, z = key
            if isinstance(z, int) and 0 <= z < self.num_layers:
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.sparse_layers[z][x, y] = value
        elif isinstance(key, tuple) and len(key) == 2:
            x, y = key
            if len(self.sparse_layers) > 0 and 0 <= x < self.width and 0 <= y < self.height:
                self.sparse_layers[0][x, y] = value
        else:
            # Handle slice assignment
            if isinstance(key, slice) or (isinstance(key, tuple) and any(isinstance(k, slice) for k in key)):
                self._handle_slice_assignment(key, value)
    
    def _handle_slice_access(self, key):
        """
        Handle slice access with memory-efficient implementations for common patterns.
        
        Supports specific slice patterns used in the codebase:
        - Layer slicing: [:, :, layer_idx] 
        - Rectangular regions: [x_start:x_end, y_start:y_end, z] or [x_start:x_end, y_start:y_end]
        - Full layer access: [:, :, z]
        
        Args:
            key: Slice key (tuple of slices/indices)
            
        Returns:
            numpy.ndarray: Sliced data with appropriate dimensions
            
        Raises:
            NotImplementedError: For unsupported slice patterns that could cause memory issues
        """
        if not isinstance(key, tuple):
            key = (key,)
        
        # Normalize key to have exactly 3 dimensions (pad with full slices)
        normalized_key = list(key)
        while len(normalized_key) < 3:
            normalized_key.append(slice(None))
        
        x_slice, y_slice, z_slice = normalized_key[:3]
        
        # Handle common patterns efficiently
        
        # Pattern 1: Full layer access [:, :, layer_idx] - very common in visualization
        if (x_slice == slice(None) and y_slice == slice(None) and isinstance(z_slice, int)):
            if 0 <= z_slice < self.num_layers:
                return self._get_full_layer(z_slice)
            else:
                raise IndexError(f"Layer index {z_slice} out of range [0, {self.num_layers})")
        
        # Pattern 2: Rectangular region with specific layer [x_start:x_end, y_start:y_end, z]
        if (isinstance(x_slice, slice) and isinstance(y_slice, slice) and isinstance(z_slice, int)):
            if 0 <= z_slice < self.num_layers:
                return self._get_rectangular_region(x_slice, y_slice, z_slice)
            else:
                raise IndexError(f"Layer index {z_slice} out of range [0, {self.num_layers})")
        
        # Pattern 3: Rectangular region across all layers [x_start:x_end, y_start:y_end, :]
        if (isinstance(x_slice, slice) and isinstance(y_slice, slice) and z_slice == slice(None)):
            return self._get_rectangular_region_all_layers(x_slice, y_slice)
        
        # Pattern 4: 2D slice (assumes first layer) [x_start:x_end, y_start:y_end]
        if len(key) == 2 and isinstance(key[0], slice) and isinstance(key[1], slice):
            if len(self.sparse_layers) > 0:
                return self._get_rectangular_region(key[0], key[1], 0)
            else:
                return np.full((0, 0), self.default_value)
        
        # Unsupported patterns that could cause memory explosion
        logger.warning(f"Unsupported slice pattern: {key}")
        raise NotImplementedError(
            f"Slice pattern {key} is not supported. "
            f"Supported patterns: [:, :, layer], [x1:x2, y1:y2, layer], [x1:x2, y1:y2, :], [x1:x2, y1:y2]"
        )
    
    def _get_full_layer(self, layer_idx):
        """Extract a complete layer as a dense 2D array."""
        sparse_matrix = self.sparse_layers[layer_idx]
        
        # For efficiency, check if we can convert the entire sparse layer
        # This is safe for layer access as it's only 2D
        if sparse_matrix.nnz == 0:
            # Empty layer - return default values
            return np.full((self.width, self.height), self.default_value, dtype=np.float32)
        else:
            # Convert sparse layer to dense - this is safe for 2D layers
            dense_layer = sparse_matrix.toarray().astype(np.float32)
            
            # Fill unset elements with default value
            if self.default_value != 0:
                # Create mask for elements that were never set
                set_mask = np.zeros((self.width, self.height), dtype=bool)
                for i in range(min(len(sparse_matrix.rows), self.width)):
                    if sparse_matrix.rows[i]:  # If row has any elements
                        for j in sparse_matrix.rows[i]:
                            if j < self.height:
                                set_mask[i, j] = True
                
                # Apply default value to unset elements
                dense_layer[~set_mask] = self.default_value
            
            return dense_layer
    
    def _get_rectangular_region(self, x_slice, y_slice, layer_idx):
        """Extract a rectangular region from a specific layer."""
        # Resolve slice bounds
        x_start, x_stop, x_step = x_slice.indices(self.width)
        y_start, y_stop, y_step = y_slice.indices(self.height)
        
        # Validate step size (only support step=1 for now)
        if x_step != 1 or y_step != 1:
            raise NotImplementedError("Step size != 1 not supported for sparse slicing")
        
        # Calculate result dimensions
        result_width = x_stop - x_start
        result_height = y_stop - y_start
        
        if result_width <= 0 or result_height <= 0:
            return np.full((result_width, result_height), self.default_value, dtype=np.float32)
        
        # Create result array with default values
        result = np.full((result_width, result_height), self.default_value, dtype=np.float32)
        
        # Fill with actual values from sparse matrix
        sparse_matrix = self.sparse_layers[layer_idx]
        
        for local_x in range(result_width):
            global_x = x_start + local_x
            if global_x < len(sparse_matrix.rows) and sparse_matrix.rows[global_x]:
                for global_y in sparse_matrix.rows[global_x]:
                    if y_start <= global_y < y_stop:
                        local_y = global_y - y_start
                        result[local_x, local_y] = sparse_matrix[global_x, global_y]
        
        return result
    
    def _get_rectangular_region_all_layers(self, x_slice, y_slice):
        """Extract a rectangular region across all layers."""
        # Resolve slice bounds
        x_start, x_stop, x_step = x_slice.indices(self.width)
        y_start, y_stop, y_step = y_slice.indices(self.height)
        
        # Validate step size
        if x_step != 1 or y_step != 1:
            raise NotImplementedError("Step size != 1 not supported for sparse slicing")
        
        # Calculate result dimensions
        result_width = x_stop - x_start
        result_height = y_stop - y_start
        
        if result_width <= 0 or result_height <= 0:
            return np.full((result_width, result_height, self.num_layers), self.default_value, dtype=np.float32)
        
        # Create result array
        result = np.full((result_width, result_height, self.num_layers), self.default_value, dtype=np.float32)
        
        # Fill each layer
        for z in range(self.num_layers):
            result[:, :, z] = self._get_rectangular_region(x_slice, y_slice, z)
        
        return result

    def _handle_slice_assignment(self, key, value):
        """
        Handle slice assignment with memory-efficient implementations for common patterns.
        
        Supports the same slice patterns as _handle_slice_access but for assignment.
        
        Args:
            key: Slice key (tuple of slices/indices)
            value: Value(s) to assign (scalar or array)
        """
        if not isinstance(key, tuple):
            key = (key,)
        
        # Normalize key to have exactly 3 dimensions
        normalized_key = list(key)
        while len(normalized_key) < 3:
            normalized_key.append(slice(None))
        
        x_slice, y_slice, z_slice = normalized_key[:3]
        
        # Convert value to numpy array for consistent handling
        if not isinstance(value, np.ndarray):
            value = np.asarray(value)
        
        # Pattern 1: Full layer assignment [:, :, layer_idx] = value
        if (x_slice == slice(None) and y_slice == slice(None) and isinstance(z_slice, int)):
            if 0 <= z_slice < self.num_layers:
                self._set_full_layer(z_slice, value)
                return
            else:
                raise IndexError(f"Layer index {z_slice} out of range [0, {self.num_layers})")
        
        # Pattern 2: Rectangular region assignment [x_start:x_end, y_start:y_end, z] = value
        if (isinstance(x_slice, slice) and isinstance(y_slice, slice) and isinstance(z_slice, int)):
            if 0 <= z_slice < self.num_layers:
                self._set_rectangular_region(x_slice, y_slice, z_slice, value)
                return
            else:
                raise IndexError(f"Layer index {z_slice} out of range [0, {self.num_layers})")
        
        # Pattern 3: Rectangular region across all layers [x_start:x_end, y_start:y_end, :] = value
        if (isinstance(x_slice, slice) and isinstance(y_slice, slice) and z_slice == slice(None)):
            self._set_rectangular_region_all_layers(x_slice, y_slice, value)
            return
        
        # Pattern 4: 2D assignment [x_start:x_end, y_start:y_end] = value (first layer)
        if len(key) == 2 and isinstance(key[0], slice) and isinstance(key[1], slice):
            if len(self.sparse_layers) > 0:
                self._set_rectangular_region(key[0], key[1], 0, value)
                return
        
        # Unsupported patterns
        logger.warning(f"Unsupported slice assignment pattern: {key}")
        raise NotImplementedError(
            f"Slice assignment pattern {key} is not supported. "
            f"Supported patterns: [:, :, layer], [x1:x2, y1:y2, layer], [x1:x2, y1:y2, :], [x1:x2, y1:y2]"
        )
    
    def _set_full_layer(self, layer_idx, value):
        """Set values for a complete layer."""
        sparse_matrix = self.sparse_layers[layer_idx]
        
        if np.isscalar(value):
            # Scalar assignment - only set non-default values to save memory
            if value != self.default_value:
                # Set all positions to the scalar value
                for x in range(self.width):
                    for y in range(self.height):
                        sparse_matrix[x, y] = float(value)
            else:
                # Setting to default value - clear the sparse matrix
                sparse_matrix.data.clear()
                sparse_matrix.rows = [[] for _ in range(self.width)]
        else:
            # Array assignment
            value = np.asarray(value)
            if value.shape != (self.width, self.height):
                # Try to reshape or broadcast
                try:
                    value = np.broadcast_to(value, (self.width, self.height))
                except ValueError:
                    raise ValueError(f"Cannot assign array of shape {value.shape} to layer of shape ({self.width}, {self.height})")
            
            # Clear existing data
            sparse_matrix.data.clear()
            sparse_matrix.rows = [[] for _ in range(self.width)]
            
            # Set non-default values only
            for x in range(self.width):
                for y in range(self.height):
                    val = float(value[x, y])
                    if val != self.default_value:
                        sparse_matrix[x, y] = val
    
    def _set_rectangular_region(self, x_slice, y_slice, layer_idx, value):
        """Set values for a rectangular region in a specific layer."""
        # Resolve slice bounds
        x_start, x_stop, x_step = x_slice.indices(self.width)
        y_start, y_stop, y_step = y_slice.indices(self.height)
        
        if x_step != 1 or y_step != 1:
            raise NotImplementedError("Step size != 1 not supported for sparse slice assignment")
        
        result_width = x_stop - x_start
        result_height = y_stop - y_start
        
        if result_width <= 0 or result_height <= 0:
            return  # Nothing to assign
        
        sparse_matrix = self.sparse_layers[layer_idx]
        
        if np.isscalar(value):
            # Scalar assignment
            if value != self.default_value:
                for x in range(x_start, x_stop):
                    for y in range(y_start, y_stop):
                        sparse_matrix[x, y] = float(value)
            else:
                # Setting to default - remove entries in this region
                for x in range(x_start, x_stop):
                    if x < len(sparse_matrix.rows):
                        sparse_matrix.rows[x] = [y for y in sparse_matrix.rows[x] if not (y_start <= y < y_stop)]
                        # Also clear corresponding data entries - note: this is approximate for lil_matrix
        else:
            # Array assignment
            value = np.asarray(value)
            if value.shape != (result_width, result_height):
                try:
                    value = np.broadcast_to(value, (result_width, result_height))
                except ValueError:
                    raise ValueError(f"Cannot assign array of shape {value.shape} to region of shape ({result_width}, {result_height})")
            
            # Set values
            for local_x in range(result_width):
                for local_y in range(result_height):
                    global_x = x_start + local_x
                    global_y = y_start + local_y
                    val = float(value[local_x, local_y])
                    if val != self.default_value:
                        sparse_matrix[global_x, global_y] = val
                    # Note: For lil_matrix, setting to 0 doesn't automatically remove the entry
                    # This is acceptable as it's still memory efficient for sparse data
    
    def _set_rectangular_region_all_layers(self, x_slice, y_slice, value):
        """Set values for a rectangular region across all layers."""
        if np.isscalar(value):
            # Scalar assignment to all layers
            for z in range(self.num_layers):
                self._set_rectangular_region(x_slice, y_slice, z, value)
        else:
            # Array assignment
            value = np.asarray(value)
            if value.ndim == 2:
                # 2D array - broadcast to all layers
                for z in range(self.num_layers):
                    self._set_rectangular_region(x_slice, y_slice, z, value)
            elif value.ndim == 3:
                # 3D array - assign layer by layer
                if value.shape[2] != self.num_layers:
                    raise ValueError(f"Array has {value.shape[2]} layers but grid has {self.num_layers} layers")
                for z in range(self.num_layers):
                    self._set_rectangular_region(x_slice, y_slice, z, value[:, :, z])
            else:
                raise ValueError(f"Cannot assign {value.ndim}D array to 3D region")
    
    @property
    def shape(self):
        """Return the shape of the array."""
        return (self.width, self.height, self.num_layers)
    
    def set_tile_data(self, x_start, x_end, y_start, y_end, layer_idx, data):
        """
        Special method for tile-based data setting optimized for sparse storage.
        
        This method is more efficient than slice assignment for tile operations
        as it can directly set values without creating intermediate arrays.
        """
        if layer_idx < len(self.sparse_layers):
            # Use the new rectangular region assignment for efficiency
            x_slice = slice(x_start, x_end)
            y_slice = slice(y_start, y_end)
            self._set_rectangular_region(x_slice, y_slice, layer_idx, data)


class MemoryOptimizedForestModel(ForestModel):
    """
    Memory-optimized version of the ForestModel for large simulations.
    
    This class extends the standard ForestModel with various memory optimization
    techniques to handle large-scale forest fire simulations efficiently.
    """
    
    def __init__(self, 
                 grid_size: Union[int, Tuple[int, int]] = (100, 100), 
                 num_layers: int = 10, 
                 layer_height_meters: float = 2.0, 
                 model_resolution: float = 5.0,
                 initial_fuel_load: float = 0.0,
                 config: Optional[ModelConfig] = None,
                 **kwargs):
        """
        Initialize a memory-optimized forest model.
        
        Args:
            grid_size: Size of the grid in cells (grid is square by default)
            num_layers: Number of vertical layers
            layer_height_meters: Height of each layer in meters
            model_resolution: Spatial resolution in meters
            initial_fuel_load: Default initial fuel load for cells
            config: Optional ModelConfig instance
            **kwargs: Additional parameters
        """
        # Memory optimization parameters MUST be set before calling super().__init__
        # because the parent class initialization may trigger property setters that check these
        self.use_sparse_storage = kwargs.get('use_sparse_storage', True)
        self.use_tiling = kwargs.get('use_tiling', True)
        self.tile_size = kwargs.get('tile_size', 200)
        self.overlap = kwargs.get('overlap', int(kwargs.get('tile_size', 200) * 0.1))
        
        all_params = {**kwargs, 'config': config, 'grid_size': grid_size, 'num_layers': num_layers, 
                      'layer_height_meters': layer_height_meters, 'model_resolution': model_resolution, 
                      'initial_fuel_load': initial_fuel_load}
        super().__init__(**all_params)
        
        # Initialize sparse storage if needed
        if self.use_sparse_storage:
            self._initialize_sparse_storage()
    
    def _convert_dense_to_sparse_fuel(self, dense_array):
        """Convert dense fuel array to sparse storage."""
        for z in range(self.num_layers):
            if z < dense_array.shape[2]:
                self.fuel_load_layers[z] = lil_matrix(dense_array[:, :, z])
    
    def _convert_dense_to_sparse_state(self, dense_array):
        """Convert dense state array to sparse storage."""
        for z in range(self.num_layers):
            if z < dense_array.shape[2]:
                self.state_layers[z] = lil_matrix(dense_array[:, :, z].astype(np.int8))
    
    def _initialize_sparse_storage(self):
        """
        Initialize sparse storage for fuel_load, state, etc.
        This method is called if use_sparse_storage is True and SciPy is available.
        """
        if not HAS_SCIPY:
            logger.warning("SciPy not available. Cannot use sparse storage. Falling back to dense arrays.")
            # Fallback to dense arrays if SciPy is not available.
            default_fuel = getattr(self.config, 'initial_fuel_load', 0.0) if self.config else 0.0
            default_moisture = getattr(self.config, 'fuel_moisture_baseline', 0.3) if self.config else 0.3

            # Store dense arrays with different names to avoid conflicts
            self._fuel_load_dense = np.full((self.width, self.height, self.num_layers), default_fuel, dtype=np.float32)
            self._state_dense = np.zeros((self.width, self.height, self.num_layers), dtype=np.int8)
            self.moisture_content = np.full((self.width, self.height, self.num_layers), default_moisture, dtype=np.float32)
            self.vertical_connectivity = np.ones((self.width, self.height, self.num_layers), dtype=np.float32) * 0.5
            self.use_sparse_storage = False # Ensure this flag is updated
            logger.info("Fell back to dense storage due to SciPy unavailability.")
            return

        logger.info(f"Initializing sparse storage for grid {self.width}x{self.height}x{self.num_layers}")
        
        # Store original dense arrays before converting to sparse
        # Access the base class attributes directly to avoid triggering properties
        original_fuel_load = None
        original_state = None
        if hasattr(super(MemoryOptimizedForestModel, self), 'fuel_load'):
            # Get the actual dense array from the base class, not the property
            base_fuel_load = object.__getattribute__(self, 'fuel_load')
            if isinstance(base_fuel_load, np.ndarray):
                original_fuel_load = base_fuel_load.copy()
        if hasattr(super(MemoryOptimizedForestModel, self), 'state'):
            # Get the actual dense array from the base class, not the property  
            base_state = object.__getattribute__(self, 'state')
            if isinstance(base_state, np.ndarray):
                original_state = base_state.copy()
        
        # Initialize sparse storage lists
        self.fuel_load_layers = []
        self.state_layers = []

        default_fuel = getattr(self.config, 'initial_fuel_load', 0.0) if self.config else 0.0
        
        for z in range(self.num_layers):
            # Initialize fuel load layer
            if original_fuel_load is not None:
                # Convert existing data to sparse
                fuel_layer = lil_matrix(original_fuel_load[:, :, z])
            else:
                # Create new EMPTY sparse layer - don't fill with defaults to save memory
                # DON'T fill with default values - this defeats the purpose of sparse storage
                # Default values will be returned by the accessor when cells are not set
                fuel_layer = lil_matrix((self.width, self.height), dtype=np.float32)
            self.fuel_load_layers.append(fuel_layer)

            # Initialize state layer
            if original_state is not None:
                # Convert existing data to sparse
                state_layer = lil_matrix(original_state[:, :, z].astype(np.int8))
            else:
                # Create new sparse layer (starts as zeros, which is efficient for sparse)
                state_layer = lil_matrix((self.width, self.height), dtype=np.int8)
            self.state_layers.append(state_layer)

        # Store references to original dense arrays (already copied above)
        self._original_fuel_load = original_fuel_load
        self._original_state = original_state
        # Don't delete the base class attributes - let the property handle access
        
        logger.info(f"Sparse storage initialized. {self.num_layers} layers converted to sparse matrices.")
        
        # Calculate and log memory savings
        try:
            total_sparse_bytes = 0
            for layer in self.fuel_load_layers:
                total_sparse_bytes += layer.data.nbytes + sum(len(row) * 4 for row in layer.rows)  # Approximate
            for layer in self.state_layers:
                total_sparse_bytes += layer.data.nbytes + sum(len(row) * 4 for row in layer.rows)  # Approximate

            sparse_size_mb = total_sparse_bytes / (1024**2)
            
            dense_fuel_bytes = self.width * self.height * self.num_layers * 4  # float32
            dense_state_bytes = self.width * self.height * self.num_layers * 1  # int8
            dense_size_mb = (dense_fuel_bytes + dense_state_bytes) / (1024**2)

            logger.info(f"Memory usage: Dense={dense_size_mb:.1f}MB, Sparse={sparse_size_mb:.1f}MB")
            if dense_size_mb > 0:
                reduction_percent = (1 - sparse_size_mb / dense_size_mb) * 100
                logger.info(f"Memory reduction: {reduction_percent:.1f}%")
        except Exception as e:
            logger.warning(f"Could not calculate memory savings: {e}")

    @property
    def fuel_load(self):
        """Access fuel load data - returns sparse or dense depending on storage mode."""
        if self.use_sparse_storage and hasattr(self, 'fuel_load_layers'):
            # Ensure consistent default fuel value between sparse and dense
            default_fuel = getattr(self.config, 'initial_fuel_load', 0.0) if self.config else 0.0
            return SparseLayerAccessor(self.fuel_load_layers, self.width, self.height, self.num_layers, default_value=default_fuel)
        else:
            # Access the dense storage or create default array
            if hasattr(self, '_fuel_load_dense'):
                return self._fuel_load_dense
            else:
                # Create a default fuel load array if nothing exists
                default_fuel = getattr(self.config, 'initial_fuel_load', 0.0) if self.config else 0.0
                return np.full((self.width, self.height, self.num_layers), default_fuel, dtype=np.float32)
    
    @fuel_load.setter
    def fuel_load(self, value):
        """Set fuel load data."""
        if self.use_sparse_storage and hasattr(self, 'fuel_load_layers'):
            # If setting from dense array, convert to sparse
            if isinstance(value, np.ndarray):
                self._convert_dense_to_sparse_fuel(value)
        else:
            self._fuel_load_dense = value
    
    @property
    def state(self):
        """Access state data - returns sparse or dense depending on storage mode."""
        if self.use_sparse_storage and hasattr(self, 'state_layers'):
            return SparseLayerAccessor(self.state_layers, self.width, self.height, self.num_layers, default_value=0)
        else:
            # Access the dense storage or create default array
            if hasattr(self, '_state_dense'):
                return self._state_dense
            else:
                # Create a default state array if nothing exists
                return np.zeros((self.width, self.height, self.num_layers), dtype=np.int8)
    
    @state.setter
    def state(self, value):
        """Set state data."""
        if self.use_sparse_storage and hasattr(self, 'state_layers'):
            # If setting from dense array, convert to sparse
            if isinstance(value, np.ndarray):
                self._convert_dense_to_sparse_state(value)
        else:
            self._state_dense = value
    
    def set_fuel_load_tile(self, x_start, x_end, y_start, y_end, layer_idx, data):
        """Set fuel load data for a tile region - optimized for sparse storage."""
        if self.use_sparse_storage and hasattr(self, 'fuel_load_layers'):
            # Use the SparseLayerAccessor's tile method
            fuel_accessor = self.fuel_load
            if hasattr(fuel_accessor, 'set_tile_data'):
                fuel_accessor.set_tile_data(x_start, x_end, y_start, y_end, layer_idx, data)
            else:
                # Fallback to element-by-element setting
                for local_x in range(data.shape[0]):
                    for local_y in range(data.shape[1]):
                        global_x = x_start + local_x
                        global_y = y_start + local_y
                        if (0 <= global_x < self.width and 0 <= global_y < self.height and
                            layer_idx < self.num_layers):
                            self.fuel_load[global_x, global_y, layer_idx] = float(data[local_x, local_y])
        else:
            # Dense storage - use regular array slicing
            if hasattr(self, '_fuel_load_dense'):
                self._fuel_load_dense[x_start:x_end, y_start:y_end, layer_idx] = data
            else:
                # Create dense array if needed
                default_fuel = getattr(self.config, 'initial_fuel_load', 0.0) if self.config else 0.0
                self._fuel_load_dense = np.full((self.width, self.height, self.num_layers), default_fuel, dtype=np.float32)
                self._fuel_load_dense[x_start:x_end, y_start:y_end, layer_idx] = data


class MinimalForestModelStub(BaseForestModel):
    """
    Minimal stub implementation of ForestModel for testing and fallback scenarios,
    inheriting from the BaseForestModel in this module.
    """
    
    def __init__(self, 
                 grid_size: Union[int, Tuple[int, int]] = (100, 100), 
                 num_layers: int = 10, 
                 layer_height_meters: float = 2.0, 
                 model_resolution: float = 5.0,
                 initial_fuel_load: float = 0.0,
                 config: Optional[ModelConfig] = None,
                 **kwargs):
        """
        Initialize a minimal forest model stub.
        """
        all_params = {**kwargs, 'config': config, 'grid_size': grid_size, 'num_layers': num_layers, 
                      'layer_height_meters': layer_height_meters, 'model_resolution': model_resolution, 
                      'initial_fuel_load': initial_fuel_load}
        super().__init__(**all_params)
    
    def run_simulation(self, max_steps=100, store_full_states=False, **kwargs):
        """
        Stub for running simulation.
        """
        logger.info(f"MinimalForestModelStub: Would run simulation for {max_steps} steps")
        self.current_step = max_steps
        return {
            'steps_completed': max_steps,
            'active_cells': 0,
            'burned_cells': 0,
            'model': self
        }
    
    def calculate_vertical_connectivity(self):
        """
        Stub for calculating vertical connectivity.
        """
        logger.info("MinimalForestModelStub: Calculate vertical connectivity")
        # Ensure vertical_connectivity is initialized correctly for BaseForestModel expectations
        if self.num_layers > 0:
            self.vertical_connectivity = np.ones((self.width, self.height, self.num_layers -1 if self.num_layers > 0 else 0), dtype=np.float32) * 0.5
        else: # Handle case of 0 layers if it can occur
            self.vertical_connectivity = np.empty((self.width, self.height, 0), dtype=np.float32)
        return self.vertical_connectivity


def create_forest_model(model_type='standard', **kwargs):
    """
    Factory function to create the appropriate forest model instance.
    
    This function centralizes model creation decisions and ensures the right type
    of model is created based on simulation requirements.
    
    Args:
        model_type: Type of model to create ('standard', 'memory_optimized', 'minimal')
        **kwargs: Parameters to pass to the model constructor
        
    Returns:
        An instance of the appropriate forest model class
    """
    logger.info(f"Creating {model_type} forest model")
    
    # Resolve configuration to get parameters like num_layers, grid_size
    config_arg = kwargs.get('config')
    if isinstance(config_arg, ModelConfig):
        current_config = config_arg
    elif isinstance(config_arg, dict):
        try:
            current_config = ModelConfig(**config_arg)
        except TypeError:
            logger.warning("Dict passed as config to create_forest_model is not a valid ModelConfig. Using global.")
            current_config = get_global_config() if get_global_config is not None else None
    else:
        current_config = get_global_config() if get_global_config is not None else None

    # Get parameters from kwargs first, then from resolved config, then literals
    grid_size_val = kwargs.get('grid_size', getattr(current_config, 'grid_size', 100) if current_config else 100)
    num_layers_val = kwargs.get('num_layers', getattr(current_config, 'num_layers', 10) if current_config else 10)
    
    # Calculate memory requirements (ensure calculate_memory_requirements is available)
    memory_estimate_mb = 0
    try:
        # Ensure grid_size_val is a tuple for calculate_memory_requirements if it expects one
        gs_for_mem_calc = grid_size_val
        if not isinstance(gs_for_mem_calc, tuple):
            gs_for_mem_calc = (gs_for_mem_calc, gs_for_mem_calc)
        
        # Pass other relevant params from config if available
        mem_calc_params = {
            'memory_optimization_level': getattr(current_config, 'memory_optimization_level', 0) if current_config else 0,
            'store_full_states': getattr(current_config, 'store_full_states', True) if current_config else True,
            'use_differential_history': getattr(current_config, 'use_differential_history', False) if current_config else False,
            'save_interval': getattr(current_config, 'save_interval', 5) if current_config else 5,
            'bytes_per_cell': getattr(current_config, 'bytes_per_cell', 10) if current_config else 10
        }

        mem_req = calculate_memory_requirements(grid_size=gs_for_mem_calc, num_layers=num_layers_val, **mem_calc_params)
        memory_estimate_mb = mem_req.get('total_estimated_in_memory_mb', mem_req.get('total_mb', 0)) # check for different possible keys
    except (NameError, TypeError) as e: # If calculate_memory_requirements not imported or bad args
        logger.warning(f"Could not estimate memory requirements in create_forest_model: {e}. Using simple estimate.")
        # Simple memory estimate if shared utilities not available or fail
        gs_x, gs_y = (grid_size_val, grid_size_val) if not isinstance(grid_size_val, tuple) else grid_size_val
        cells = gs_x * gs_y * num_layers_val
        memory_estimate_mb = cells * (getattr(current_config, 'bytes_per_cell', 10) if current_config else 10) / (1024 * 1024)
    
    # Auto-select memory optimized for large grids
    if model_type == 'auto':
        if memory_estimate_mb > 1000:  # 1GB threshold
            model_type = 'memory_optimized'
        else:
            model_type = 'standard'
    
    # Create the appropriate model type
    if model_type == 'memory_optimized':
        logger.info("Creating MemoryOptimizedForestModel for memory-efficient processing")
        return MemoryOptimizedForestModel(**kwargs)
    elif model_type == 'minimal' or model_type == 'stub':
        return MinimalForestModelStub(**kwargs)
    else:  # standard
        return ForestModel(**kwargs) 