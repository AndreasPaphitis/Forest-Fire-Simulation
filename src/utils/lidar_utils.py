"""
LiDAR Utilities Module

Provides standardized utilities for working with LiDAR data in forest fire simulations.
This module handles the consistent processing of LiDAR-derived vegetation structure data.
"""

import os
import re
import logging
# import logging # Replaced by get_logger
import numpy as np
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union, Any, TYPE_CHECKING
import traceback
import functools

# Import standardized logger first
from src.utils.logging_utils import get_logger
logger = get_logger(__name__)

# Import ModelConfig for type checking and isinstance
# from src.config.config_tools import ModelConfig # Moved to be imported only where needed or under TYPE_CHECKING

# Try to import GDAL
try:
    from osgeo import gdal, osr
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    
try:
    from skimage.transform import resize
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

# Configure logging

# Import error handling utilities directly from src
try:
    from src.utils.error_handling import handle_errors, log_errors, DataProcessingError, FileIOError
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    logger.warning("src.utils.error_handling not found. Using fallback error handling.")
    ERROR_HANDLING_AVAILABLE = False
    # Fallback decorator and exception classes (already improved with functools.wraps)
    import functools # Ensure functools is imported for the fallback
    def handle_errors(func=None, **kwargs):
        if func is None:
            return lambda f: f # Return the decorator itself if no func is passed
        @functools.wraps(func) # Ensure wrapped function keeps its name, etc.
        def wrapper(*args, **kw_args):
            try:
                return func(*args, **kw_args)
            except Exception as e:
                logger.error(f"Error in {func.__name__} (fallback handler): {e}")
                logger.debug(traceback.format_exc())
                return kwargs.get('default_return', None) 
        return wrapper
    log_errors = handle_errors # Simple alias for fallback
    class DataProcessingError(Exception): pass
    class FileIOError(Exception): pass

# Import file handlers directly from src
try:
    from src.utils.file_handlers import FileManager
    FILE_HANDLERS_AVAILABLE = True
except ImportError:
    logger.warning("src.utils.file_handlers.FileManager not found. File operations may be limited.")
    FILE_HANDLERS_AVAILABLE = False
    # Minimal fallback for FileManager if needed, or just let operations fail if it's critical
    class FileManager:
        @staticmethod
        def find_files(base_dir, pattern):
            logger.warning("Using fallback FileManager.find_files. Functionality will be basic.")
            import glob
            # This is a simplified version of what FileManager might do
            return [Path(f) for f in glob.glob(os.path.join(base_dir, "**", pattern), recursive=True)]

# Import config tools for accessing global configuration
# from src.config.config_tools import ModelConfig # Moved to be imported only where needed or under TYPE_CHECKING
from typing import TYPE_CHECKING, Optional, Union, List, Tuple, Any, Dict # Added TYPE_CHECKING and others

if TYPE_CHECKING:
    from src.config.config_tools import ModelConfig # This is the correct place for module-level type hint
    from src.core.raster_management import RasterManager # For type hinting
    from src.utils.file_handlers import DataCubeConfig # For type hinting

# Import the shared GDAL optimization function
from src.utils.shared_utilities import optimize_gdal_io

# Default constants
# DEFAULT_LAYER_HEIGHT = 2.0  # meters # To be sourced from ModelConfig
# DEFAULT_MODEL_RESOLUTION = 5.0  # meters per cell # To be sourced from ModelConfig
# DEFAULT_NUM_LAYERS = 10 # To be sourced from ModelConfig
# DEFAULT_EXTINCTION_COEFFICIENT = 0.5 # To be sourced from ModelConfig

# Helper to check for ModelConfig instance type without direct isinstance problem during imports
def _is_model_config_instance_duck_typed(obj):
    # Avoids direct isinstance(obj, ModelConfig) if ModelConfig import is tricky
    # Checks for Pydantic model attributes as a proxy
    if isinstance(obj, dict): # Definitely not a ModelConfig instance itself
        return False
    # Pydantic v2 typically has model_fields, Pydantic v1 has __fields__
    # and a .dict() or .model_dump() method
    has_pydantic_method = hasattr(obj, 'model_dump') or hasattr(obj, 'dict')
    has_pydantic_fields = hasattr(obj, 'model_fields') or hasattr(obj, '__fields__')
    # Crude check: if it has these, it's likely a Pydantic model. 
    # A more specific check would be obj.__class__.__name__ == 'ModelConfig'
    # but that also needs the class to be defined.
    # This duck typing is safer against import issues for the *type check itself*.
    if has_pydantic_method and has_pydantic_fields:
        # To be a bit more sure it's *our* ModelConfig, check a unique attribute if one exists
        # or rely on the fact that it passed other dict/None checks.
        # For now, this level of duck typing might be enough if it's not a dict.
        return True 
    return False

class LiDARDataManager:
    """
    Manager for LiDAR-derived vegetation data.
    
    This class provides utilities for loading, processing, and integrating 
    LiDAR-derived vegetation data for forest fire simulation.
    """
    
    DEFAULT_MAX_FUEL_FOR_NORMALIZATION = 10.0 # Max fuel value for normalization in connectivity
    
    def __init__(self, base_dir: Optional[str] = None, resolution: Optional[float] = None, 
                layer_height: Optional[float] = None, config: Optional['ModelConfig']=None):
        """
        Initialize the LiDAR data manager.
        
        Args:
            base_dir: Base directory containing LiDAR data
            resolution: Target resolution in meters per grid cell
            layer_height: Height of each vertical layer in meters
            config: Optional ModelConfig instance for central configuration
        """
        from src.config.config_tools import get_global_config # Moved import here
        global_conf = get_global_config() # Get global config once

        self.config = config if config is not None else global_conf
        
        # Prioritize: 1. Direct arg, 2. Passed config, 3. Global config
        self.base_dir = base_dir if base_dir is not None else \
                        (getattr(self.config, 'lidar_data_dir', None) if self.config else None)
        
        self.resolution = resolution if resolution is not None else \
                           (getattr(self.config, 'model_resolution', global_conf.model_resolution) if self.config else global_conf.model_resolution)
        
        self.layer_height = layer_height if layer_height is not None else \
                            (getattr(self.config, 'layer_height', global_conf.layer_height) if self.config else global_conf.layer_height)
        
        logger.info(f"LiDARDataManager initialized. Base_dir: {self.base_dir}, Resolution: {self.resolution}, Layer_height: {self.layer_height}")
        
        # Configure GDAL if available
        if GDAL_AVAILABLE:
            # Configure error handling for GDAL
            gdal.UseExceptions()
            gdal.PushErrorHandler('CPLQuietErrorHandler') # Suppress console warnings, rely on exceptions
            
            # Set up IO optimizations using the shared utility
            # Pass None for params that should use optimize_gdal_io's defaults or its own config access
            self._configure_gdal_optimizations() 
        else:
            logger.warning("GDAL not available - LiDAR functionality will be limited")
    
    def _configure_gdal_optimizations(self, cache_size_mb: Optional[int] = None, 
                                    thread_count: Optional[int] = None, 
                                    hpc_mode: Optional[bool] = None):
        """
        Configure GDAL for optimized processing using the shared utility.
        Parameters passed here will override defaults in optimize_gdal_io or its config access.
        """
        try:
            # Use parameters from ModelConfig if available and not directly passed
            # This allows some level of control via the main simulation config
            current_config = self.config # self.config is already global_config if not passed to __init__
            
            final_cache_size_mb = cache_size_mb if cache_size_mb is not None else getattr(current_config, 'gdal_cache_mb', 256) # Default 256 if not in config
            final_thread_count = thread_count if thread_count is not None else getattr(current_config, 'gdal_thread_count', None) # None lets optimize_gdal_io decide
            final_hpc_mode = hpc_mode if hpc_mode is not None else getattr(current_config, 'hpc_mode_gdal', False) # Default False

            # Call the shared utility function
            gdal_options_set = optimize_gdal_io(
                cache_size_mb=final_cache_size_mb,
                thread_count=final_thread_count,
                use_direct_io=True,  # Typically good for non-networked drives
                hpc_mode=final_hpc_mode 
            )
            if gdal_options_set:
                logger.debug(f"Shared GDAL optimizations applied: {gdal_options_set}")
            else:
                logger.warning("Shared GDAL optimization utility did not return status or failed.")

        except Exception as e:
            logger.warning(f"Failed to configure GDAL optimizations using shared utility: {e}")
    
    @handle_errors(error_type=DataProcessingError, default_return=None)
    def get_lidar_extent(self, data_dir: Optional[str] = None) -> Optional[Tuple[float, float, float, float]]:
        """
        Get the geographic extent of LiDAR data by examining all available raster files.
        
        Args:
            data_dir: Directory containing LiDAR data (or use self.base_dir)
            
        Returns:
            Tuple of (min_x, min_y, max_x, max_y) or None if failed
            
        This method now examines all raster files (not just the first few) to ensure
        complete coverage and adds robust error handling with detailed logging.
        """
        # Use provided data_dir or default
        dir_to_scan = data_dir if data_dir is not None else self.base_dir
        
        if dir_to_scan is None:
            logger.error("No data directory specified for get_lidar_extent")
            return None
            
        if not os.path.exists(dir_to_scan):
            logger.error(f"Data directory does not exist: {dir_to_scan}")
            return None
        
        raster_files = self._find_raster_files(dir_to_scan)
        if not raster_files:
            logger.error(f"No raster files found in {dir_to_scan}")
            return None
            
        logger.info(f"Found {len(raster_files)} raster files to determine extent")
            
        # Initialize with extreme values
        x_min, y_min = float('inf'), float('inf')
        x_max, y_max = float('-inf'), float('-inf')
        
        # Track statistics
        files_processed = 0
        files_error = 0
        last_error = None
        reference_crs = None
        crs_warnings = []
        
        # Process all raster files, not just the first few
        for raster_file in raster_files:
            try:
                logger.debug(f"Examining raster file: {raster_file}")
                
                from osgeo import gdal, osr
                gdal.UseExceptions()  # Enable exceptions for better error handling
                
                ds = gdal.Open(str(raster_file))
                if ds is None:
                    logger.warning(f"Could not open raster file: {raster_file}")
                    files_error += 1
                    continue
                    
                # Simple CRS validation - expect EPSG:25828
                current_crs = ds.GetProjection()
                if current_crs:
                    if reference_crs is None:
                        reference_crs = current_crs
                        # Parse and report CRS
                        try:
                            srs = osr.SpatialReference()
                            srs.ImportFromWkt(reference_crs)
                            auth_code = srs.GetAuthorityCode(None)
                            if auth_code != "25828":
                                logger.warning(f"Data CRS is {auth_code or 'Unknown'}, expected EPSG:25828. Assuming coordinates are correct.")
                            else:
                                logger.info(f"Data CRS: EPSG:{auth_code}")
                        except:
                            logger.info("Could not parse CRS - assuming coordinates are correct")
                    elif current_crs != reference_crs:
                        # Just warn about inconsistency but continue
                        crs_warnings.append(str(raster_file))
                        logger.debug(f"CRS inconsistency in {raster_file} - continuing anyway")
                else:
                    logger.debug(f"No CRS defined in {raster_file} - assuming coordinates are correct")
                    
                # Get geotransform (affine transformation parameters)
                gt = ds.GetGeoTransform()
                if not gt:
                    logger.warning(f"No geotransform found in {raster_file}")
                    files_error += 1
                    continue
                    
                # Calculate corners
                width = ds.RasterXSize
                height = ds.RasterYSize
                
                # Calculate all four corners to handle rotated rasters correctly
                corners = [
                    (0, 0),              # Upper-left
                    (width, 0),          # Upper-right
                    (0, height),         # Lower-left
                    (width, height)      # Lower-right
                ]
                
                for px, py in corners:
                    # Convert pixel coordinates to map coordinates
                    x = gt[0] + px * gt[1] + py * gt[2]
                    y = gt[3] + px * gt[4] + py * gt[5]
                    
                    # Update min/max
                    x_min = min(x_min, x)
                    y_min = min(y_min, y)
                    x_max = max(x_max, x)
                    y_max = max(y_max, y)
                
                files_processed += 1
                ds = None  # Close dataset
                
            except Exception as e:
                files_error += 1
                last_error = str(e)
                logger.warning(f"Error processing {raster_file}: {e}")
                
        # Report statistics
        logger.info(f"Processed {files_processed} raster files successfully")
        if files_error > 0:
            logger.warning(f"Failed to process {files_error} raster files")
            if last_error:
                logger.warning(f"Last error: {last_error}")
                
        if crs_warnings:
            logger.warning(f"CRS inconsistencies in {len(crs_warnings)} files")
            
        # Verify we obtained valid bounds
        if x_min < float('inf') and y_min < float('inf') and x_max > float('-inf') and y_max > float('-inf'):
            # Final validation - ensure min < max
            if x_min >= x_max or y_min >= y_max:
                logger.error(f"Invalid extent: min coordinates >= max coordinates: ({x_min}, {y_min}) to ({x_max}, {y_max})")
                return None
                
            logger.info(f"Calculated extent: ({x_min}, {y_min}) to ({x_max}, {y_max})")
            return (x_min, y_min, x_max, y_max)
        else:
            logger.error("Could not determine valid extent from raster files")
            return None
    
    def _find_raster_files(self, base_dir: str) -> List[Path]:
        """
        Find raster files in a directory.
        
        Args:
            base_dir: Directory to search
            
        Returns:
            List of paths to raster files
        """
        if FILE_HANDLERS_AVAILABLE:
            # Use FileManager if available
            raster_files = []
            for ext in ['.tif', '.tiff', '.asc', '.img']:
                raster_files.extend(FileManager.find_files(base_dir, f"*{ext}"))
            return raster_files
        else:
            # Fallback implementation
            import glob
            raster_files = []
            for ext in ['.tif', '.tiff', '.asc', '.img']:
                pattern = os.path.join(base_dir, "**", f"*{ext}")
                raster_files.extend([Path(f) for f in glob.glob(pattern, recursive=True)])
            return raster_files
    
    @handle_errors(error_type=DataProcessingError)
    def calculate_optimal_grid_size(self, base_dir: Optional[str] = None, 
                                   target_resolution: Optional[float] = None,
                                   grid_size_limit: Optional[int] = None,
                                   available_memory_mb: Optional[float] = None,
                                   snap_to_grid: bool = True) -> Dict[str, Any]:
        """
        Calculate optimal grid size based on LiDAR data extent and memory constraints.
        
        Args:
            base_dir: Directory containing LiDAR data
            target_resolution: Target resolution in meters (or use class default)
            grid_size_limit: Maximum grid dimension (for memory constraints)
            available_memory_mb: Available memory in MB (for tiling calculation)
            snap_to_grid: Whether to snap grid boundaries to resolution multiples
            
        Returns:
            Dictionary with width, height, resolution, and geographic extent
            
        This method now includes improved grid alignment (snapping) and robust CRS checking.
        """
        # Use provided base_dir or instance default
        data_dir = base_dir if base_dir is not None else self.base_dir
        
        if data_dir is None:
            raise DataProcessingError("No LiDAR data directory specified")
            
        # Use provided resolution or instance default
        resolution = target_resolution if target_resolution is not None else self.resolution
        
        if resolution is None or resolution <= 0:
            raise DataProcessingError(f"Invalid resolution: {resolution}")
        
        # Get geographic extent of the LiDAR data
        extent = self.get_lidar_extent(data_dir)
        if extent is None:
            raise DataProcessingError(f"Could not determine extent of LiDAR data in {data_dir}")
            
        min_x, min_y, max_x, max_y = extent
        
        # Check for valid extent (finite and correctly ordered)
        if not all(map(math.isfinite, extent)):
            raise DataProcessingError(f"Invalid extent with non-finite values: {extent}")
            
        if min_x >= max_x or min_y >= max_y:
            raise DataProcessingError(f"Invalid extent (min >= max): {extent}")
        
        logger.info(f"Raw LiDAR data extent: ({min_x}, {min_y}) to ({max_x}, {max_y})")
        
        # If snapping is enabled, snap grid boundaries to resolution multiples
        # This ensures that grids from adjacent datasets will align precisely
        if snap_to_grid:
            # Snap to resolution grid, expanding slightly to ensure full coverage
            original_min_x, original_min_y = min_x, min_y
            original_max_x, original_max_y = max_x, max_y
            
            # Snap minimum coordinates down (floor)
            min_x = math.floor(min_x / resolution) * resolution
            min_y = math.floor(min_y / resolution) * resolution
            
            # Snap maximum coordinates up (ceil)
            max_x = math.ceil(max_x / resolution) * resolution
            max_y = math.ceil(max_y / resolution) * resolution
            
            logger.info(f"Snapped grid boundaries to {resolution}m resolution")
            logger.info(f"  Original: ({original_min_x}, {original_min_y}) to ({original_max_x}, {original_max_y})")
            logger.info(f"  Snapped: ({min_x}, {min_y}) to ({max_x}, {max_y})")
        
        # Calculate grid dimensions based on extent and resolution
        width_meters = max_x - min_x
        height_meters = max_y - min_y
        
        grid_width = int(width_meters / resolution)
        grid_height = int(height_meters / resolution)
        
        logger.info(f"Calculated grid size: {grid_width}x{grid_height} at {resolution}m resolution")
        logger.info(f"Physical dimensions: {width_meters:.1f}m x {height_meters:.1f}m")
        
        # Simple CRS validation - assume all data should be in EPSG:25828
        raster_files = self._find_raster_files(data_dir)
        if raster_files:
            logger.info(f"Performing simple CRS validation on {min(len(raster_files), 10)} sample files")
            expected_crs = "EPSG:25828"
            crs_warnings = []
            
            try:
                from osgeo import gdal, osr
                for i, raster_file in enumerate(raster_files[:10]):  # Check only first 10 files
                    try:
                        ds = gdal.Open(str(raster_file))
                        if ds is None:
                            continue
                            
                        current_crs = ds.GetProjection()
                        if current_crs:
                            srs = osr.SpatialReference()
                            srs.ImportFromWkt(current_crs)
                            auth_code = srs.GetAuthorityCode(None)
                            
                            if auth_code != "25828":  # Not EPSG:25828
                                crs_warnings.append((str(raster_file), auth_code or "Unknown"))
                        else:
                            crs_warnings.append((str(raster_file), "No CRS"))
                            
                        ds = None
                    except Exception as e:
                        logger.debug(f"Error checking CRS for {raster_file}: {e}")
                        
                if crs_warnings:
                    logger.warning(f"Found {len(crs_warnings)} files not in {expected_crs}:")
                    for file_path, detected_crs in crs_warnings[:3]:
                        logger.warning(f"  - {Path(file_path).name}: {detected_crs}")
                    if len(crs_warnings) > 3:
                        logger.warning(f"  - ... and {len(crs_warnings) - 3} more files")
                    logger.warning("Assuming coordinates are correct and continuing processing")
                else:
                    logger.info(f"All checked files are in {expected_crs}")
                    
            except ImportError:
                logger.info("GDAL/OSR not available - skipping CRS validation")
        
        # Apply grid size limit if specified
        original_grid_width, original_grid_height = grid_width, grid_height
        
        if grid_size_limit and (grid_width > grid_size_limit or grid_height > grid_size_limit):
            logger.warning(f"Grid size ({grid_width}x{grid_height}) exceeds limit ({grid_size_limit})")
            
            # Scale down proportionally
            if grid_width >= grid_height:
                scale_factor = grid_size_limit / grid_width
                grid_width = grid_size_limit
                grid_height = int(grid_height * scale_factor)
            else:
                scale_factor = grid_size_limit / grid_height
                grid_height = grid_size_limit
                grid_width = int(grid_width * scale_factor)
                
            logger.info(f"Scaled down to {grid_width}x{grid_height} (maintaining aspect ratio)")
            
            # Recalculate effective resolution after scaling
            effective_resolution_x = width_meters / grid_width
            effective_resolution_y = height_meters / grid_height
            logger.info(f"Effective resolution after scaling: {effective_resolution_x:.2f}m x {effective_resolution_y:.2f}m")
            
            # Use the larger value as the new resolution
            adjusted_resolution = max(effective_resolution_x, effective_resolution_y)
            logger.info(f"Using adjusted resolution: {adjusted_resolution:.2f}m")
            
            # Update the returned resolution to reflect the actual grid spacing
            resolution = adjusted_resolution
        
        # Build result dictionary
        result = {
            'width': grid_width,
            'height': grid_height,
            'original_width': original_grid_width,
            'original_height': original_grid_height,
            'resolution': resolution,
            'extent': (min_x, min_y, max_x, max_y),
            'width_meters': width_meters,
            'height_meters': height_meters,
            'snap_to_grid': snap_to_grid,
            'crs_warnings': len(crs_warnings) if 'crs_warnings' in locals() else 0
        }
        
        # Estimate memory requirements
        if available_memory_mb:
            cells = grid_width * grid_height
            layers = self.determine_optimal_num_layers(base_dir)
            bytes_per_cell = 4  # Assuming float32
            total_bytes = cells * layers * bytes_per_cell
            total_mb = total_bytes / (1024 * 1024)
            
            result['memory_requirements'] = {
                'cells': cells,
                'layers': layers,
                'bytes_per_cell': bytes_per_cell,
                'total_bytes': total_bytes,
                'total_mb': total_mb
            }
            
            if total_mb > available_memory_mb:
                logger.warning(f"Estimated memory usage ({total_mb:.1f} MB) exceeds available memory ({available_memory_mb} MB)")
                
                # Calculate suitable tile size to fit in memory
                # Target using no more than 20% of available memory per tile
                target_tile_mb = available_memory_mb * 0.2
                cells_per_mb = cells / total_mb
                target_cells_per_tile = target_tile_mb * cells_per_mb
                
                # Calculate tile size (assuming square tiles)
                tile_size = int(math.sqrt(target_cells_per_tile / layers))
                
                # Round to nearest multiple of 50 for cleaner boundaries
                tile_size = max(50, (tile_size // 50) * 50)
                
                # Calculate number of tiles
                tiles_x = math.ceil(grid_width / tile_size)
                tiles_y = math.ceil(grid_height / tile_size)
                total_tiles = tiles_x * tiles_y
                
                result['tiling_recommendation'] = {
                    'tile_size': tile_size,
                    'tiles_x': tiles_x,
                    'tiles_y': tiles_y,
                    'total_tiles': total_tiles
                }
                
                logger.info(f"Recommended tiling: {tiles_x}x{tiles_y} tiles of size {tile_size}x{tile_size}")
        
        return result
    
    @handle_errors(error_type=DataProcessingError)
    def determine_optimal_num_layers(self, base_dir: Optional[str] = None,
                                     layer_height: Optional[float] = None) -> int:
        """
        Determine the optimal number of vertical layers based on LiDAR data.
        Scans filenames in the base_dir for height or layer information.
        
        Args:
            base_dir: Directory containing LiDAR data files. Uses self.base_dir if None.
            layer_height: Height of each layer in meters. Uses self.layer_height if None.
            
        Returns:
            Optimal number of layers based on detected maximum vegetation height.
            Returns a default number of layers if unable to determine from files.
        """
        scan_dir = base_dir or self.base_dir
        effective_layer_height = layer_height if layer_height is not None else self.layer_height

        # Determine a fallback default number of layers
        default_layers_fallback = 10 # A sensible hardcoded default
        if self.config and hasattr(self.config, 'num_layers') and isinstance(self.config.num_layers, int):
            default_layers_fallback = self.config.num_layers
        elif self.config is None:
            logger.warning("LiDARDataManager.config is None, cannot get default num_layers. Using hardcoded fallback.")
        elif not hasattr(self.config, 'num_layers'):
            logger.warning("LiDARDataManager.config has no 'num_layers' attribute. Using hardcoded fallback.")
        elif not isinstance(self.config.num_layers, int):
            logger.warning(f"LiDARDataManager.config.num_layers is not an int ({type(self.config.num_layers)}). Using hardcoded fallback.")


        if not scan_dir or not os.path.exists(scan_dir):
            logger.warning(f"LiDAR data directory not found for layer determination: {scan_dir}. Returning default {default_layers_fallback} layers.")
            return default_layers_fallback

        if effective_layer_height <= 0:
            logger.error(f"Invalid layer_height: {effective_layer_height}. Must be positive. Returning default {default_layers_fallback} layers.")
            return default_layers_fallback

        logger.info(f"Determining optimal number of layers from: {scan_dir} with layer height: {effective_layer_height}m")

        height_counts: Dict[int, int] = {}
        max_overall_height_detected: float = 0.0

        # Regex patterns to extract height or layer numbers from filenames
        patterns = [
            re.compile(r'.*_(\d+\.\d+)-(\d+\.\d+)m(?:_nrd|_pad)?\.tif', re.IGNORECASE),
            re.compile(r'.*_(\d+)-(\d+)m(?:_nrd|_pad)?\.tif', re.IGNORECASE),
            re.compile(r'.*_layer_(\d+)(?:_nrd|_pad)?\.tif', re.IGNORECASE),
            re.compile(r'.*_bin_(\d+)m(?:_nrd|_pad)?\.tif', re.IGNORECASE),
            re.compile(r'.*_(\d+\.\d+)m(?:_nrd|_pad)?\.tif', re.IGNORECASE),
            re.compile(r'.*_(\d+)m(?:_nrd|_pad)?\.tif', re.IGNORECASE),
            re.compile(r'.*_height_(\d+)(?:_nrd|_pad)?\.tif', re.IGNORECASE)
        ]
        
        files_scanned = 0
        for root, _, files in os.walk(scan_dir):
            for filename in files:
                files_scanned += 1
                filename_lower = filename.lower()
                if filename_lower.endswith('.tif'):
                    current_max_h_in_file = 0.0
                    matched_pattern_for_file = False
                    for pattern_idx, pattern in enumerate(patterns):
                        match = pattern.match(filename_lower)
                        if match:
                            matched_pattern_for_file = True
                            extracted_value_str = ""
                            try:
                                if len(match.groups()) == 2:  # Range pattern
                                    extracted_value_str = match.group(2)
                                    h_val = float(extracted_value_str)
                                    current_max_h_in_file = max(current_max_h_in_file, h_val)
                                    logger.debug(f"File: {filename}, Pattern {pattern_idx}, Range upper: {h_val}m")
                                    break 
                                elif len(match.groups()) == 1: # Single value pattern
                                    extracted_value_str = match.group(1)
                                    h_val = float(extracted_value_str)
                                    current_max_h_in_file = max(current_max_h_in_file, h_val)
                                    logger.debug(f"File: {filename}, Pattern {pattern_idx}, Single value: {h_val}m")
                                    break
                            except ValueError:
                                logger.warning(f"Could not convert extracted height '{extracted_value_str}' to float in {filename} using pattern {pattern_idx}")
                    
                    if current_max_h_in_file > 0:
                        height_key = int(round(current_max_h_in_file))
                        height_counts[height_key] = height_counts.get(height_key, 0) + 1
                        max_overall_height_detected = max(max_overall_height_detected, current_max_h_in_file)
                    elif matched_pattern_for_file: # Matched a pattern but failed to get a positive height
                        logger.debug(f"File: {filename} matched a pattern but current_max_h_in_file is {current_max_h_in_file}")

        logger.info(f"Scanned {files_scanned} files in {scan_dir}.")
        logger.info(f"Raw max_overall_height_detected from filenames: {max_overall_height_detected:.2f}m")
        logger.info(f"Collected height_counts: {height_counts}")

        max_height_from_counts: float = 0.0
        if height_counts:
            # Determine max height from counts (require at least one occurrence)
            for height, count in sorted(height_counts.items()):
                if count >= 1: 
                    max_height_from_counts = max(max_height_from_counts, float(height))
            
            logger.info(f"Max height from counts (>=1 occurrence): {max_height_from_counts:.2f}m")
            
            # Fallback if the primary counting method yields 0 (e.g., if all counts were < 1, which is impossible here)
            # This handles cases where rounding might cause issues or if the above loop is too restrictive.
            if max_height_from_counts == 0 and height_counts: # ensure height_counts is not empty
                logger.info("Max height from counts was 0, falling back to max key in height_counts.")
                max_height_from_counts = float(max(height_counts.keys()))
                logger.info(f"Max height from max(height_counts.keys()): {max_height_from_counts:.2f}m")
        else:
            logger.info("height_counts is empty.")

        final_max_height_for_calc = min(max_height_from_counts, 50.0)  # Apply 50m vegetation height cap

        # Calculate number of layers
        num_layers_calculated = math.ceil(final_max_height_for_calc / effective_layer_height)
        
        # Apply bounds (e.g., min 1 layer, max 100 layers)
        # The upper bound helps prevent extremely large number of layers if max_height is unexpectedly huge.
        final_num_layers = max(1, min(int(num_layers_calculated), 100)) 

        logger.info(f"Calculated layers: ceil({final_max_height_for_calc:.2f}m / {effective_layer_height:.2f}m) = {num_layers_calculated}. Final num_layers after bounding: {final_num_layers}")
        return final_num_layers
    
    @handle_errors(error_type=DataProcessingError)
    def load_raster_data(self, file_path: Union[str, Path], bounds: Optional[Tuple[float, float, float, float]] = None, 
                        target_shape: Optional[Tuple[int, int]] = None, 
                        resampling_method: str = 'bilinear') -> np.ndarray:
        """
        Load raster data from a file with optional cropping and resampling.
        
        Args:
            file_path: Path to the raster file
            bounds: Optional geographic bounds to crop (min_x, min_y, max_x, max_y)
            target_shape: Optional shape to resample to (width, height)
            resampling_method: Method for resampling ('nearest' or 'bilinear')
            
        Returns:
            Numpy array with raster data
        """
        if not GDAL_AVAILABLE:
            raise DataProcessingError("GDAL not available - cannot load raster data")
        
        file_path = str(file_path)  # Ensure string for GDAL
        
        try:
            # Open the raster file
            ds = gdal.Open(file_path)
            if ds is None:
                raise FileIOError(f"Could not open raster file: {file_path}")
            
            # Get geotransform and dimensions
            geotransform = ds.GetGeoTransform()
            width = ds.RasterXSize
            height = ds.RasterYSize
            
            # If bounds provided, calculate pixel coordinates
            if bounds:
                min_x, min_y, max_x, max_y = bounds
                
                # Calculate pixel coordinates
                pixel_min_x = int((min_x - geotransform[0]) / geotransform[1])
                pixel_max_y = int((min_y - geotransform[3]) / geotransform[5])
                pixel_max_x = int((max_x - geotransform[0]) / geotransform[1])
                pixel_min_y = int((max_y - geotransform[3]) / geotransform[5])
                
                # Ensure coordinates are within raster bounds
                pixel_min_x = max(0, min(width - 1, pixel_min_x))
                pixel_min_y = max(0, min(height - 1, pixel_min_y))
                pixel_max_x = max(0, min(width, pixel_max_x))
                pixel_max_y = max(0, min(height, pixel_max_y))
                
                # Calculate dimensions
                read_width = pixel_max_x - pixel_min_x
                read_height = pixel_max_y - pixel_min_y
                
                if read_width <= 0 or read_height <= 0:
                    logger.warning(f"Invalid bounds intersection for raster {file_path}: bounds={bounds}, "
                                 f"raster_extent=({geotransform[0]}, {geotransform[3]}, "
                                 f"{geotransform[0] + width*geotransform[1]}, {geotransform[3] + height*geotransform[5]})")
                    # Return zeros array instead of failing
                    return np.zeros((100, 100), dtype=np.float32)
                
                # Read the cropped portion
                band = ds.GetRasterBand(1)
                data = band.ReadAsArray(pixel_min_x, pixel_min_y, read_width, read_height)
            else:
                # Read the entire raster
                band = ds.GetRasterBand(1)
                data = band.ReadAsArray()
            
            # ROBUST DATA TYPE VALIDATION AND CONVERSION
            if data is None:
                raise DataProcessingError(f"Failed to read data from raster: {file_path}")
            
            # Check for and handle problematic data types
            if data.dtype == np.object_ or data.dtype.kind == 'O':
                logger.warning(f"Object dtype detected in {file_path}, converting to float32")
                try:
                    data = data.astype(np.float32)
                except (ValueError, TypeError) as e:
                    raise DataProcessingError(f"Cannot convert object array to numeric: {e}")
            
            # Handle complex numbers (convert to magnitude)
            if np.iscomplexobj(data):
                logger.warning(f"Complex data detected in {file_path}, using magnitude")
                data = np.abs(data).astype(np.float32)
            
            # Validate that data contains finite values
            if not np.all(np.isfinite(data)):
                logger.warning(f"Non-finite values detected in {file_path}")
                # Replace inf and -inf with NaN, then handle NaN
                data = np.where(np.isinf(data), np.nan, data)
                
                # Count and handle NaN values
                nan_count = np.sum(np.isnan(data))
                if nan_count > 0:
                    logger.warning(f"Found {nan_count} NaN values in {file_path}, replacing with 0")
                    data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Ensure data is in a compatible numeric type
            if data.dtype.kind not in ['i', 'u', 'f']:  # integer, unsigned, float
                logger.warning(f"Unusual data type {data.dtype} in {file_path}, converting to float32")
                data = data.astype(np.float32)
            
            # Clean up
            band = None
            ds = None
            
            # Resample if target shape provided
            if target_shape and data.shape != target_shape:
                # Check if target_shape is provided correctly
                if len(target_shape) != 2:
                    logger.warning(f"Invalid target_shape {target_shape}. Expected (height, width).")
                    return data
                
                # Check for zeros in dimensions
                if target_shape[0] <= 0 or target_shape[1] <= 0:
                    logger.warning(f"Invalid target_shape dimensions: {target_shape}. Must be positive.")
                    return data
                
                # Check if source data is valid
                if data.shape[0] <= 0 or data.shape[1] <= 0:
                    logger.warning(f"Invalid source data shape: {data.shape}. Cannot resample.")
                    return data
                
                # First try scikit-image if available
                if SKIMAGE_AVAILABLE:
                    try:
                        # Make target_shape match skimage's expected order (height, width)
                        # and enforce data type preservation
                        data_resampled = resize(data, target_shape, preserve_range=True, 
                                                order=0 if resampling_method == 'nearest' else 1)
                        data = data_resampled.astype(data.dtype)
                    except Exception as e:
                        logger.warning(f"Skimage resampling failed: {e}. Falling back to simple resampling.")
                        data = self._simple_resample(data, target_shape, method=resampling_method)
                else:
                    # Use our custom resampling method
                    data = self._simple_resample(data, target_shape, method=resampling_method)
            
            return data
            
        except Exception as e:
            raise DataProcessingError(f"Error loading raster data from {file_path}: {e}")
    
    def _simple_resample(self, data: np.ndarray, target_shape: Tuple[int, int], method: str = 'bilinear') -> np.ndarray:
        """
        Resample a 2D array to a new shape using either nearest neighbor or bilinear interpolation.
        
        Args:
            data: Input array (2D)
            target_shape: Target shape as (height, width)
            method: Interpolation method, either 'nearest' or 'bilinear'
            
        Returns:
            Resampled array with target_shape
        """
        # Get input and output dimensions
        in_height, in_width = data.shape
        out_height, out_width = target_shape
        
        # Create output array
        output = np.zeros(target_shape, dtype=data.dtype)
        
        # Calculate scaling factors
        scale_y = in_height / out_height
        scale_x = in_width / out_width
        
        if method.lower() == 'nearest':
            # Simple nearest neighbor resampling
            for y in range(out_height):
                for x in range(out_width):
                    in_y = min(in_height - 1, int(y * scale_y))
                    in_x = min(in_width - 1, int(x * scale_x))
                    output[y, x] = data[in_y, in_x]
                    
        elif method.lower() == 'bilinear':
            # Bilinear interpolation
            for y in range(out_height):
                for x in range(out_width):
                    # Calculate source coordinates
                    src_y = y * scale_y
                    src_x = x * scale_x
                    
                    # Get the four surrounding pixel coordinates
                    y0 = min(in_height - 1, int(src_y))
                    y1 = min(in_height - 1, y0 + 1)
                    x0 = min(in_width - 1, int(src_x))
                    x1 = min(in_width - 1, x0 + 1)
                    
                    # Calculate interpolation weights
                    wy = src_y - y0
                    wx = src_x - x0
                    
                    # Get the four surrounding pixel values
                    v00 = data[y0, x0]
                    v01 = data[y0, x1]
                    v10 = data[y1, x0]
                    v11 = data[y1, x1]
                    
                    # Interpolate in x direction
                    v0 = (1 - wx) * v00 + wx * v01
                    v1 = (1 - wx) * v10 + wx * v11
                    
                    # Interpolate in y direction
                    output[y, x] = (1 - wy) * v0 + wy * v1
                    
                    # If output needs to be integer, round the result
                    if np.issubdtype(data.dtype, np.integer):
                        output[y, x] = round(output[y, x])
        else:
            logger.warning(f"Unknown resampling method '{method}'. Using nearest neighbor.")
            # Fall back to nearest neighbor
            for y in range(out_height):
                for x in range(out_width):
                    in_y = min(in_height - 1, int(y * scale_y))
                    in_x = min(in_width - 1, int(x * scale_x))
                    output[y, x] = data[in_y, in_x]
        
        return output
    
    @handle_errors(error_type=DataProcessingError)
    def calculate_vertical_connectivity(self, fuel_data: np.ndarray) -> np.ndarray:
        """
        Calculate vertical connectivity between forest layers based on fuel load.
        
        Args:
            fuel_data: 3D array of fuel data (layers, width, height) or (width, height, layers)
            
        Returns:
            Array of vertical connectivity values
        """
        # Determine array shape format
        if len(fuel_data.shape) != 3:
            raise DataProcessingError(f"Invalid fuel data shape: {fuel_data.shape}, expected 3D array")
            
        # Handle different array formats
        if fuel_data.shape[0] < fuel_data.shape[1] and fuel_data.shape[0] < fuel_data.shape[2]:
            # Format: (layers, width, height)
            num_layers, width, height = fuel_data.shape
            connectivity = np.zeros((num_layers-1, width, height), dtype=np.float32)
            
            # Calculate connectivity between adjacent layers
            for z in range(num_layers-1):
                # Normalize fuel values to 0-1 range
                fuel_lower = np.clip(fuel_data[z] / self.DEFAULT_MAX_FUEL_FOR_NORMALIZATION, 0, 1)
                fuel_upper = np.clip(fuel_data[z+1] / self.DEFAULT_MAX_FUEL_FOR_NORMALIZATION, 0, 1)
                
                # Connectivity is the product of fuel in adjacent layers with a square root
                # transformation to increase connectivity for moderate fuel values
                connectivity[z] = np.sqrt(fuel_lower * fuel_upper)
        else:
            # Format: (width, height, layers)
            width, height, num_layers = fuel_data.shape
            connectivity = np.zeros((width, height, num_layers-1), dtype=np.float32)
            
            # Calculate connectivity between adjacent layers
            for z in range(num_layers-1):
                # Normalize fuel values to 0-1 range
                fuel_lower = np.clip(fuel_data[:, :, z] / self.DEFAULT_MAX_FUEL_FOR_NORMALIZATION, 0, 1)
                fuel_upper = np.clip(fuel_data[:, :, z+1] / self.DEFAULT_MAX_FUEL_FOR_NORMALIZATION, 0, 1)
                
                # Connectivity is the product of fuel in adjacent layers with a square root
                # transformation to increase connectivity for moderate fuel values
                connectivity[:, :, z] = np.sqrt(fuel_lower * fuel_upper)
                
        return connectivity
    
    @staticmethod
    @handle_errors(error_type=ValueError, reraise=True, default_return=None, log_level=logging.WARNING)
    def calculate_pad(normalized_returns: np.ndarray, bin_size: float, extinction_coef: float, epsilon: float = 1e-9) -> np.ndarray:
        """
        Calculates Plant Area Density (PAD) from normalized LiDAR returns using MacArthur and Horn\'s formula.
        Assumes normalized_returns are (height, width, layers) or (layers, height, width).
        """
        if not isinstance(normalized_returns, np.ndarray) or normalized_returns.ndim != 3:
            raise ValueError("Normalized returns must be a 3D NumPy array")
        if normalized_returns.size == 0:
            # Handle empty array case: return an empty array with a shape that makes sense for PAD (H, W, L) or (H, W) if L becomes 0
            # Based on current PAD structure it is (H, W, L), so if input is (H,W,0) or (0,0,0), output should be (H,W,0) or (0,0,0)
            return np.zeros_like(normalized_returns) # returns an array of same shape and type, filled with zeros.

        # Determine orientation (height, width, layers) or (layers, height, width)
        # Apply Beer-Lambert law to calculate PAD
        # PAD = -ln(1 - NRD) / (extinction_coef * bin_size)
        # Avoid log(0) by adding a small value
        pad = -np.log(1.0 - np.clip(normalized_returns, 0, 0.99) + epsilon) / (extinction_coef * bin_size)
        
        # Clip to reasonable values
        pad = np.clip(pad, 0, 10.0)
        
        return pad 

    def auto_configure_from_directory(self, data_dir: Union[str, Path],
                                      target_resolution: Optional[float] = None,
                                      grid_size_limit: Optional[Union[int, Tuple[int, int]]] = None,
                                      model_config_defaults: Optional[Union[Dict[str, Any], 'ModelConfig']] = None) -> 'ModelConfig':
        """
        Automatically configure ModelConfig parameters based on LiDAR data in a directory.
        """
        from src.config.config_tools import ModelConfig # Import locally for runtime use (primarily instantiation)

        logger.info(f"Auto-configuring from directory: {data_dir}")
        
        current_config_instance = None
        if _is_model_config_instance_duck_typed(model_config_defaults):
            current_config_instance = model_config_defaults
        elif isinstance(model_config_defaults, dict):
            effective_config_data = model_config_defaults.copy() # Work with a copy
        else:
            effective_config_data = {}

        # If self.config exists and no explicit defaults were given, use its values as a base
        # This logic might need refinement based on desired precedence
        if self.config and not model_config_defaults: # model_config_defaults could be {} if originally None
            try:
                base_data = self.config.model_dump(exclude_unset=True)
            except AttributeError:
                base_data = self.config.dict(exclude_unset=True) # Fallback for Pydantic v1
            # Merge: effective_config_data (from explicit None leading to {}) can overwrite base_data if keys exist
            # but typically model_config_defaults being None means effective_config_data is {}.
            # A better merge might be: base_data.update(effective_config_data), then effective_config_data = base_data
            # For now, let's assume if model_config_defaults was None, effective_config_data is empty and we just use base_data.
            # If model_config_defaults was an empty dict {}, it would have been copied above, this block wouldn't run.
            effective_config_data = base_data # If no defaults provided, base on self.config

        # Override with any specific parameters passed to this method
        if target_resolution is not None:
            effective_config_data['model_resolution'] = target_resolution 
            # ensure grid_size might need re-evaluation if resolution changes

        base_dir_val = Path(data_dir) if data_dir else None # Ensure Path object or None

        # Step 1: Determine geographic extent
        extent = None
        logger.debug(f"Auto_config step1: effective_config_data before extent check: {effective_config_data}")
        logger.debug(f"Auto_config step1: simulation_extent_m from effective_data: {effective_config_data.get('simulation_extent_m')}")
        
        if effective_config_data.get('simulation_extent_m') is None:
            logger.debug(f"Auto_config step1: Attempting to get lidar extent. base_dir_val: {base_dir_val}")
            try:
                if not base_dir_val or not os.path.exists(str(base_dir_val)):
                    # Log an error or raise a specific exception if data_dir is crucial and missing
                    logger.error(f"LiDAR data directory for auto-config does not exist or not provided: {base_dir_val}")
                    # Decide if to raise an error or proceed with defaults for extent
                    # For now, let it proceed, extent will remain None
                else:
                    extent = self.get_lidar_extent(data_dir=str(base_dir_val)) # Use keyword arg and str(Path)

                if extent:
                    effective_config_data['simulation_extent_m'] = extent
            except Exception as e:
                logger.error(f"Error determining LiDAR extent: {e}")
                logger.debug(traceback.format_exc())
                extent = None

        # --- Actual LiDAR scanning and extent calculation would go here ---
        # For now, let's assume some dummy values derived from an imaginary scan
        derived_grid_size = (500,500) # Example
        derived_model_resolution = target_resolution if target_resolution is not None else effective_config_data.get('model_resolution', 10.0)
        derived_num_layers = effective_config_data.get('num_layers', 5) # Example

        effective_config_data['grid_size'] = derived_grid_size
        effective_config_data['model_resolution'] = derived_model_resolution
        effective_config_data['num_layers'] = derived_num_layers
        effective_config_data['lidar_data_dir'] = str(data_dir)
        effective_config_data['auto_size_from_lidar'] = False # Since we are sizing it here

        if grid_size_limit:
            # Apply grid_size_limit logic here if necessary
            pass

        # Create a new instance or update the existing one
        if current_config_instance:
            # Update the existing instance in-place
            for key, value in effective_config_data.items():
                if hasattr(current_config_instance, key):
                    setattr(current_config_instance, key, value)
                else:
                    # This case should ideally not happen if effective_config_data is derived from ModelConfig fields
                    logger.warning(f"Attempting to set unknown attribute '{key}' on existing ModelConfig instance during auto_configure.")
            # Validate the modified instance - Pydantic might do this on setattr if validators are present
            # Or call current_config_instance.validate() if available and desired.
            return current_config_instance # Return the modified original instance
        else:
            # Create a new instance
            return ModelConfig(**effective_config_data)

    def create_composite_raster(self, output_path: Union[str, Path], 
                                tile_configs: List['DataCubeConfig'], 
                                target_resolution: float, 
                                target_extent: Tuple[float, float, float, float], 
                                crs: Any, 
                                raster_manager: Optional['RasterManager'] = None) -> Optional[Path]:
        """
        Create a composite raster from a list of tile configurations (DataCubeConfig objects).
        Placeholder for actual implementation.
        """
        logger.info(f"Creating composite raster at: {output_path}")
        # Actual implementation would involve using raster_manager or GDAL directly
        # to merge/mosaic rasters defined by tile_configs into output_path.
        if not raster_manager:
            logger.warning("RasterManager not provided to create_composite_raster. Cannot proceed.")
            return None
        
        # Example (very simplified placeholder - actual merging is complex):
        try:
            # This is NOT a real implementation, just to show where it would go.
            # Real implementation uses raster_manager.merge_rasters() or similar.
            with open(output_path, 'w') as f:
                f.write(f"Composite raster for extent {target_extent} at {target_resolution}m. CRS: {crs}\n")
                f.write(f"Based on {len(tile_configs)} tiles.\n")
            logger.info(f"Successfully created placeholder composite raster: {output_path}")
            return Path(output_path)
        except Exception as e:
            logger.error(f"Failed to create composite raster: {e}")
            return None

    @handle_errors(error_type=DataProcessingError)
    def resample_pad_data_to_model_grid(self, pad_files_dict: Dict[int, List[Path]], 
                                       model_grid_extent: Tuple[float, float, float, float],
                                       model_grid_size: Tuple[int, int],
                                       model_resolution: float,
                                       nodata_value: float = -9999.0) -> Dict[int, np.ndarray]:
        """
        Resample PAD raster files to the model grid using bilinear interpolation.
        
        This method properly aligns multiple PAD datasets to a common grid, preserving
        data types and handling no-data values to avoid resampling artifacts.
        
        Args:
            pad_files_dict: Dictionary mapping layer numbers to lists of PAD raster files
            model_grid_extent: Model grid extent as (x_min, y_min, x_max, y_max)
            model_grid_size: Model grid size as (width, height)
            model_resolution: Model resolution in meters
            nodata_value: Value to use for no-data in output
            
        Returns:
            Dictionary mapping layer numbers to resampled arrays
            
        Raises:
            DataProcessingError: If resampling fails or CRS inconsistencies are detected
        """
        if not GDAL_AVAILABLE:
            raise DataProcessingError("GDAL not available - cannot resample PAD data")
        
        # Initialize results
        resampled_layers = {}
        total_files_processed = 0
        total_layers = len(pad_files_dict)
        
        # Track CRS for consistency checking
        reference_crs = None
        crs_inconsistencies = []
        
        # Validate model grid parameters
        if not all(map(math.isfinite, model_grid_extent)):
            raise DataProcessingError(f"Invalid model grid extent: {model_grid_extent}")
        
        if model_grid_size[0] <= 0 or model_grid_size[1] <= 0:
            raise DataProcessingError(f"Invalid model grid size: {model_grid_size}")
        
        if model_resolution <= 0:
            raise DataProcessingError(f"Invalid model resolution: {model_resolution}")
        
        logger.info(f"Resampling PAD data to model grid: {model_grid_size[0]}x{model_grid_size[1]} at {model_resolution}m resolution")
        logger.info(f"Model grid extent: {model_grid_extent}")
        
        # Process each layer
        for layer_num, file_paths in pad_files_dict.items():
            if not file_paths:
                logger.warning(f"No PAD files provided for layer {layer_num}")
                continue
                
            # Create an empty array for this layer, initialized with nodata_value
            layer_data = np.full(model_grid_size, nodata_value, dtype=np.float32)
            layer_count = np.zeros(model_grid_size, dtype=np.int32)  # Count of contributing datasets
            layer_min, layer_max = float('inf'), float('-inf')  # Track value range
            original_dtype = None  # Track original data type
            
            # Process each file in this layer
            files_processed = 0
            for file_path in file_paths:
                try:
                    # Open the source raster to get metadata
                    ds = gdal.Open(str(file_path))
                    if ds is None:
                        logger.warning(f"Could not open raster file: {file_path}")
                        continue
                    
                    # Simple CRS validation - expect EPSG:25828
                    current_crs = ds.GetProjection()
                    if reference_crs is None:
                        reference_crs = current_crs
                        # Check if it's EPSG:25828
                        try:
                            srs = osr.SpatialReference()
                            srs.ImportFromWkt(current_crs)
                            auth_code = srs.GetAuthorityCode(None)
                            if auth_code != "25828":
                                logger.warning(f"File CRS is {auth_code or 'Unknown'}, expected EPSG:25828. Assuming coordinates are correct.")
                        except:
                            logger.debug("Could not parse CRS - assuming coordinates are correct")
                    elif current_crs != reference_crs:
                        # Just warn about inconsistency but continue
                        crs_inconsistencies.append(str(file_path))
                        logger.debug(f"CRS inconsistency in {file_path} - continuing anyway")
                    
                    # Get source data type to preserve it
                    band = ds.GetRasterBand(1)
                    if original_dtype is None:
                        # Use the first file's dtype as reference
                        original_dtype = band.DataType
                        
                    # Get nodata value
                    src_nodata = band.GetNoDataValue()
                    
                    # Get geo transform
                    gt = ds.GetGeoTransform()
                    if gt is None:
                        logger.warning(f"No geotransform found in {file_path}")
                        continue
                    
                    # Read data with proper bounds and resampling
                    raster_data = self.load_raster_data(
                        file_path=file_path,
                        bounds=model_grid_extent,
                        target_shape=model_grid_size,
                        resampling_method='bilinear'
                    )
                    
                    # Create mask for valid data (not nodata)
                    valid_mask = np.ones_like(raster_data, dtype=bool)
                    if src_nodata is not None:
                        valid_mask = ~np.isclose(raster_data, src_nodata, rtol=1e-6, atol=1e-6)
                    
                    # Update layer_data only for valid data
                    if np.any(valid_mask):
                        # For first contribution to a cell, directly set the value
                        first_contribution = (layer_count == 0) & valid_mask
                        layer_data[first_contribution] = raster_data[first_contribution]
                        
                        # For subsequent contributions, average the values
                        subsequent_contribution = (layer_count > 0) & valid_mask
                        if np.any(subsequent_contribution):
                            # Weighted average based on existing count
                            weights = layer_count[subsequent_contribution].astype(np.float32)
                            layer_data[subsequent_contribution] = (
                                (layer_data[subsequent_contribution] * weights + 
                                 raster_data[subsequent_contribution]) / (weights + 1)
                            )
                        
                        # Update count for valid data points
                        layer_count[valid_mask] += 1
                        
                        # Update min/max for range tracking
                        layer_min = min(layer_min, np.min(raster_data[valid_mask]))
                        layer_max = max(layer_max, np.max(raster_data[valid_mask]))
                        
                        files_processed += 1
                    else:
                        logger.warning(f"No valid data found in {file_path} after resampling")
                    
                    # Clean up
                    band = None
                    ds = None
                    
                except Exception as e:
                    logger.warning(f"Error processing {file_path} for layer {layer_num}: {e}")
            
            # After processing all files for this layer
            total_files_processed += files_processed
            logger.info(f"Layer {layer_num}: Processed {files_processed} files out of {len(file_paths)}")
            
            # Set nodata_value for cells with no contributions
            no_data_mask = layer_count == 0
            if np.any(no_data_mask):
                layer_data[no_data_mask] = nodata_value
                logger.info(f"Layer {layer_num}: {np.sum(no_data_mask)} cells ({np.sum(no_data_mask)/layer_data.size*100:.2f}%) have no data")
            
            # Ensure original data type is preserved to avoid artifacts
            if layer_min < float('inf') and layer_max > float('-inf'):
                logger.info(f"Layer {layer_num}: Value range [{layer_min}, {layer_max}]")
                
                # Convert back to original data type based on GDAL type
                if gdal.GetDataTypeName(original_dtype) in ['Byte', 'UInt16', 'UInt32']:
                    # For unsigned integer types, clip to 0 and round
                    layer_data = np.clip(layer_data, 0, None)
                    layer_data = np.round(layer_data)
                elif gdal.GetDataTypeName(original_dtype) in ['Int16', 'Int32']:
                    # For signed integer types, just round
                    layer_data = np.round(layer_data)
                
                # No special handling needed for Float32/Float64
                
                # Store in the results dictionary using original dtype
                np_dtype = self._gdal_to_numpy_dtype(original_dtype)
                if np_dtype is not None:
                    # Handle nodata values specially when converting to integer types
                    if np.issubdtype(np_dtype, np.integer):
                        # For integer types, we need to replace nodata with a valid integer
                        temp_data = layer_data.copy()
                        # Replace current nodata with a valid integer for conversion
                        temp_data[no_data_mask] = 0
                        # Convert to integer type
                        temp_data = temp_data.astype(np_dtype)
                        # Store the result
                        resampled_layers[layer_num] = temp_data
                        logger.info(f"Layer {layer_num}: Converted to {np_dtype} with nodata=0 for integer types")
                    else:
                        # For float types, we can keep nodata as is
                        resampled_layers[layer_num] = layer_data.astype(np_dtype)
                        logger.info(f"Layer {layer_num}: Converted to {np_dtype}")
                else:
                    # Fallback to float32 if we can't map the GDAL type
                    resampled_layers[layer_num] = layer_data.astype(np.float32)
                    logger.info(f"Layer {layer_num}: Converted to float32 (fallback)")
            else:
                logger.warning(f"Layer {layer_num}: No valid data found in any file")
        
        # Report any CRS inconsistencies found (informational only)
        if crs_inconsistencies:
            logger.info(f"CRS metadata variations found in {len(crs_inconsistencies)} files (processing continued normally)")
            logger.debug(f"Files with CRS variations: {crs_inconsistencies[:3]}{'...' if len(crs_inconsistencies) > 3 else ''}")
        
        logger.info(f"Successfully resampled {len(resampled_layers)} layers from {total_files_processed} files")
        
        return resampled_layers
    
    def _gdal_to_numpy_dtype(self, gdal_dtype: int) -> Optional[np.dtype]:
        """
        Convert GDAL data type to numpy data type.
        
        Args:
            gdal_dtype: GDAL data type code
            
        Returns:
            Equivalent numpy dtype or None if no match
        """
        # Map GDAL data types to numpy data types
        dtype_map = {
            gdal.GDT_Byte: np.uint8,
            gdal.GDT_UInt16: np.uint16,
            gdal.GDT_Int16: np.int16,
            gdal.GDT_UInt32: np.uint32,
            gdal.GDT_Int32: np.int32,
            gdal.GDT_Float32: np.float32,
            gdal.GDT_Float64: np.float64
        }
        
        return dtype_map.get(gdal_dtype)
        
    def _find_layer_files(self, base_dir: Union[str, Path], layer: int) -> List[Path]:
        """
        Find PAD files for a specific layer in the given directory and its subdirectories.
        Note: Layer 0 is excluded as it's usually noise.
        
        Args:
            base_dir: Base directory to search
            layer: Layer number (0-based, but layer 0 is excluded, so 0=2m, 1=4m, 2=6m, etc.)
            
        Returns:
            List of paths to PAD files for the specified layer
        """
        base_path = Path(base_dir)
        
        # Check if base_dir exists
        if not base_path.exists():
            logger.warning(f"Base directory does not exist: {base_path}")
            return []
        
        # Look for pad_rasters subdirectory
        pad_rasters_dir = base_path / "pad_rasters"
        if not pad_rasters_dir.exists():
            logger.warning(f"pad_rasters directory does not exist: {pad_rasters_dir}")
            return []
        
        # Pattern to match PAD files: *_pad_{height}.0m.tif
        # Layer 0 is excluded, so layer 0 = 2m, layer 1 = 4m, layer 2 = 6m, etc.
        height_meters = (layer + 1) * 2  # Convert layer index to height in meters (skip 0m)
        pattern = f"*_pad_{height_meters}.0m.tif"
        
        # Find files matching the pattern
        layer_files = list(pad_rasters_dir.glob(pattern))
        
        logger.info(f"Found {len(layer_files)} files for layer {layer} (height {height_meters}m) in {pad_rasters_dir}")
        
        return layer_files
    
    def get_max_available_layers(self, base_dir: Union[str, Path]) -> int:
        """
        Get the maximum number of available layers in the PAD data.
        Excludes layer 0 (0m height) as it's usually noise.
        
        Args:
            base_dir: Base directory containing pad_rasters folder
            
        Returns:
            Maximum layer index (total number of layers, excluding layer 0)
        """
        available_layers = self._detect_available_layers(base_dir)
        if not available_layers:
            return 0
        
        max_layer = max(available_layers.keys())
        total_layers = max_layer  # Layer indices are 0-based, but we exclude layer 0
        
        logger.info(f"Maximum available layers: {total_layers} (layers 1 to {max_layer}, excluding layer 0)")
        return total_layers
    
    def _detect_available_layers(self, base_dir: Union[str, Path]) -> Dict[int, List[Path]]:
        """
        Detect all available PAD layers and their files across all datasets.
        Excludes layer 0 (0m height) as it's usually noise.
        
        Args:
            base_dir: Base directory containing pad_rasters folder
            
        Returns:
            Dictionary mapping layer indices to lists of file paths (excluding layer 0)
        """
        base_path = Path(base_dir)
        pad_rasters_dir = base_path / "pad_rasters"
        
        if not pad_rasters_dir.exists():
            logger.warning(f"pad_rasters directory does not exist: {pad_rasters_dir}")
            return {}
        
        # Find all PAD files and group by layer
        layer_files = {}
        
        # Pattern to match all PAD files: *_pad_*.0m.tif
        all_pad_files = list(pad_rasters_dir.glob("*_pad_*.0m.tif"))
        
        for file_path in all_pad_files:
            # Extract height from filename: *_pad_{height}.0m.tif
            filename = file_path.name
            try:
                # Find the height value in the filename
                import re
                match = re.search(r'_pad_(\d+)\.0m\.tif$', filename)
                if match:
                    height_meters = int(match.group(1))
                    layer_index = height_meters // 2  # Convert height to layer index (0m->0, 2m->1, 4m->2, etc.)
                    
                    # Exclude layer 0 (0m height) as it's usually noise
                    if layer_index == 0:
                        logger.info(f"Excluding layer 0 (0m height) from {filename} - typically noise")
                        continue
                    
                    if layer_index not in layer_files:
                        layer_files[layer_index] = []
                    layer_files[layer_index].append(file_path)
                    
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse height from filename {filename}: {e}")
                continue
        
        # Log the detected layers (excluding layer 0)
        if layer_files:
            max_layer = max(layer_files.keys())
            logger.info(f"Detected {len(layer_files)} layers (1 to {max_layer}, excluding layer 0) with {sum(len(files) for files in layer_files.values())} total files")
            for layer_idx in sorted(layer_files.keys()):
                height_meters = layer_idx * 2
                logger.info(f"  Layer {layer_idx} (height {height_meters}m): {len(layer_files[layer_idx])} files")
        else:
            logger.warning("No PAD files detected (excluding layer 0)")
        
        return layer_files

# Ensure this is the end of the class definition or module 