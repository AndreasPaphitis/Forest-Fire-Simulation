import laspy
import numpy as np
import os
import csv
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import logging
from typing import List, Dict, Union, Optional, Tuple
import glob
import time
import sys
from scipy.stats import binned_statistic_2d

# Add parent directory to sys.path to enable relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Local imports from project
try:
    from src.utils.logging_utils import get_logger
    from src.utils.error_handling import handle_errors, log_errors, DataProcessingError, FileIOError
    from src.utils.file_handlers import FileManager
    logger = get_logger(__name__)
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    # Fallback to standard logging if project imports aren't available
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    ERROR_HANDLING_AVAILABLE = False

try:
    from osgeo import gdal, osr
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    logger.warning("GDAL not available - some functionality will be limited")

"""
Normalized Return Density (NRD) Calculation for LiDAR Data

This script calculates the Normalized Return Density (NRD) from LiDAR point cloud data,
which is a valuable metric for analyzing forest vertical structure. NRD represents the
proportion of LiDAR returns at a given height relative to all returns at that height 
and below, creating a vertical profile of vegetation density from the ground up.

Key features:
- Processes LiDAR point clouds (.las/.laz) with pre-normalized heights
- Extracts vegetation points based on classification codes
- Organizes points into customizable height bins
- Calculates NRD values for each height bin
- Generates visualizations of the vertical structure
- Exports results to CSV files for further analysis
- Creates raster files for each height bin (spatial distribution) using GDAL
- Applies statistical filtering to remove negative height artifacts from nearest neighbor normalization
- Supports batch processing of multiple LAZ files in a directory

The NRD concept is based on research in forest ecology and remote sensing,
providing insights into canopy structure, biomass distribution, and habitat complexity.

Usage:
    # Process a single file:
    python NRD_calculation.py --input <lidar_file> --output <output_dir> [options]
    
    # Process all files in a directory:
    python NRD_calculation.py --input_dir <directory_with_laz_files> --output_dir <base_output_dir> [options]
"""

# =========================================================================
# CONFIGURATION AND PARAMETERS
# =========================================================================

# ---------------------------------------------------------------------
# DEFAULT INPUT AND OUTPUT SETTINGS
# ---------------------------------------------------------------------
# These should point to where your LiDAR files are located and where to save NRD results
DEFAULT_INPUT_DIR = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\Analysis files\Processed\height_normalised_vegetation_pointclouds"
DEFAULT_OUTPUT_DIR = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\Analysis files\Processed\NRD Raster Layers"

# ---------------------------------------------------------------------
# LIDAR PROCESSING PARAMETERS
# ---------------------------------------------------------------------
# Default vegetation classes to extract (3=low veg, 4=medium veg, 5=high veg)
DEFAULT_VEGETATION_CLASSES = [3, 4, 5]

# ---------------------------------------------------------------------
# HEIGHT BINNING PARAMETERS
# ---------------------------------------------------------------------
# Default bin size in meters for vertical stratification
DEFAULT_BIN_SIZE = 2.0  # m

# Minimum percentage of total points required for a bin to be valid (0.1%)
DEFAULT_MIN_POINTS_PERCENT = 0.1

# ---------------------------------------------------------------------
# RASTER OUTPUT PARAMETERS
# ---------------------------------------------------------------------
# Default raster resolution in meters
DEFAULT_RASTER_RESOLUTION = 5.0  # m

# Whether to create raster files for each height bin
DEFAULT_CREATE_RASTERS = True

# ---------------------------------------------------------------------
# HEIGHT ARTIFACT FILTERING PARAMETERS
# ---------------------------------------------------------------------
# Whether to handle negative height values from normalization
DEFAULT_HANDLE_NEGATIVE_HEIGHTS = True

# Whether to filter out negative heights for NRD calculation
DEFAULT_FILTER_NEGATIVE_HEIGHTS = True

# Whether to apply statistical filtering to remove normalization artifacts
DEFAULT_FILTER_ARTIFACTS = True

# Method for artifact filtering
# Options: 'simple' (remove all negative heights),
#          'statistical' (use z-scores to identify outliers),
#          'local' (use spatial context and slope thresholds),
#          'combined' (apply both statistical and local filtering)
DEFAULT_FILTER_METHOD = 'statistical'

# Z-score threshold for statistical filtering
DEFAULT_Z_SCORE_THRESHOLD = 2.5

# Maximum allowed slope in degrees for local context filtering
DEFAULT_SLOPE_THRESHOLD = 45.0

# Minimum allowed height after filtering
DEFAULT_MIN_VALID_HEIGHT = -1.0

# ---------------------------------------------------------------------
# VISUALIZATION PARAMETERS
# ---------------------------------------------------------------------
# Whether to show cumulative height distribution in plots
DEFAULT_SHOW_CUMULATIVE = True

# ---------------------------------------------------------------------
# PERFORMANCE PARAMETERS
# ---------------------------------------------------------------------
# Whether to use parallel processing for multiple files
DEFAULT_PARALLEL_PROCESSING = True

# Maximum number of worker processes (None = use CPU count)
DEFAULT_MAX_WORKERS = 4
# ---------------------------------------------------------------------
# USER CONFIGURATION DICTIONARY
# ---------------------------------------------------------------------
def get_user_config():
    """
    Returns a dictionary of user configuration parameters.
    
    Edit these values to customize the NRD calculation process based on your data
    and analysis requirements.
    
    Returns:
        Dictionary of user configuration parameters
    """
    return {
        # DATA INPUT/OUTPUT
        # -----------------
        'input_directory': DEFAULT_INPUT_DIR,  # Directory with LiDAR files
        'output_directory': DEFAULT_OUTPUT_DIR,  # Directory to save results
        
        # POINT CLOUD PROCESSING
        # ----------------------
        'vegetation_classes': DEFAULT_VEGETATION_CLASSES,  # LiDAR classification codes to use
        'bin_size': DEFAULT_BIN_SIZE,  # Vertical interval for height bins in meters
        'raster_resolution': DEFAULT_RASTER_RESOLUTION,  # Horizontal resolution of output rasters in meters
        
        # HEIGHT ARTIFACT FILTERING
        # -------------------------
        'handle_negative_heights': DEFAULT_HANDLE_NEGATIVE_HEIGHTS,  # Whether to handle negative height values
        'filter_negative_heights': DEFAULT_FILTER_NEGATIVE_HEIGHTS,  # Whether to filter out negative heights
        'filter_artifacts': DEFAULT_FILTER_ARTIFACTS,  # Whether to apply statistical filtering
        'filter_method': DEFAULT_FILTER_METHOD,  # Filtering method
        'z_score_threshold': DEFAULT_Z_SCORE_THRESHOLD,  # Z-score threshold for statistical filtering
        'slope_threshold': DEFAULT_SLOPE_THRESHOLD,  # Maximum allowed slope in degrees
        'min_valid_height': DEFAULT_MIN_VALID_HEIGHT,  # Minimum allowed height after filtering
        
        # QUALITY CONTROL
        # ---------------
        'min_points_percent': DEFAULT_MIN_POINTS_PERCENT,  # Minimum percentage for bin validity
        
        # OUTPUT OPTIONS
        # --------------
        'create_rasters': DEFAULT_CREATE_RASTERS,  # Whether to create raster files
        'show_cumulative': DEFAULT_SHOW_CUMULATIVE,  # Whether to show cumulative distribution
        
        # PERFORMANCE SETTINGS
        # -------------------
        'parallel_processing': DEFAULT_PARALLEL_PROCESSING,  # Whether to use parallel processing
        'max_workers': DEFAULT_MAX_WORKERS,  # Maximum number of worker processes
    }

# -------------------------------------------------------------------------
# GLOSSARY AND PARAMETER DOCUMENTATION
# -------------------------------------------------------------------------
"""
GLOSSARY OF TERMS AND PARAMETERS
--------------------------------

LiDAR TERMINOLOGY:
-----------------
* LiDAR (Light Detection and Ranging): Remote sensing technology that uses laser pulses 
  to measure distances to objects and create detailed 3D representations of environments.
  
* Point Cloud: Collection of 3D points captured by LiDAR, representing the physical environment.
  Each point typically contains X, Y, Z coordinates and additional attributes.
  
* LAZ/LAS: Standard file formats for LiDAR point cloud data (LAZ is compressed).
  LAS (LiDAR Aerial Survey) is the industry standard format, while LAZ offers compression.
  
* Classification: Categorization of LiDAR points by type (ground, vegetation, buildings, etc.).
  The LAS format includes standardized classification codes for different feature types.
  
* Vegetation Classes: Standard LiDAR classification codes for vegetation:
  - Class 3: Low vegetation (<0.3m)
  - Class 4: Medium vegetation (0.3-2m)
  - Class 5: High vegetation (>2m)
  
* Height Normalization: Process of adjusting point heights relative to the ground surface.
  Raw LiDAR heights are usually referenced to an absolute elevation datum (e.g., sea level).
  For vegetation analysis, normalizing heights to the ground surface is necessary.
  
* PDAL: Point Data Abstraction Library, used for LiDAR processing. An open-source library 
  that provides tools for manipulating and processing point cloud data.

NRD CALCULATION CONCEPTS:
------------------------
* NRD (Normalized Return Density): Proportion of LiDAR returns at a given height relative 
  to all returns at that height and below. This metric provides insight into the vertical
  distribution of vegetation within a forest canopy.
  
* Height Bin: Vertical segment (e.g., 0-2m, 2-4m) used to group points by height.
  These bins form the basis for analyzing the vertical structure of vegetation.
  
* Beer-Lambert Law: Physical relationship used to convert NRD to Plant Area Density (PAD).
  The law describes light attenuation through a medium and is adapted for LiDAR analysis.
  
* PAD (Plant Area Density): Measure of vegetation density per unit volume (m²/m³).
  PAD quantifies the total one-sided area of plant material per unit volume.
  
* Bin Size: Vertical interval in meters for height stratification (default: 2.0m).
  Smaller bin sizes provide more detailed vertical profiles but may have fewer points per bin.
  
* Raster: Gridded geospatial data format used for visualization and analysis.
  Converts point data into a regular grid for spatial analysis and mapping.
  
* EPSG Code: Standardized identifier for coordinate reference systems.
  Ensures proper geospatial positioning and enables integration with other spatial data.

ALGORITHM PARAMETERS:
-------------------
* filter_method: Approach for filtering height artifacts:
  - 'simple': Removes all negative heights
  - 'statistical': Uses z-scores to identify outliers
  - 'local': Uses spatial context and slope thresholds
  - 'combined': Applies both statistical and local filtering
  
* z_score_threshold: Statistical threshold for identifying outliers (default: 2.5).
  Points with z-scores exceeding this threshold are considered outliers.
  
* slope_threshold: Maximum allowed slope in degrees for terrain (default: 45.0°).
  Used in local filtering to identify abrupt height changes inconsistent with natural terrain.
  
* min_valid_height: Minimum allowable height after filtering (default: -1.0m).
  Points below this threshold are excluded from analysis.
  
* min_points_percent: Minimum percentage of total points required for a bin to be valid (default: 0.1%).
  Bins with too few points are excluded to ensure statistical reliability.
  
* raster_resolution: Spatial resolution of output raster files in meters (default: 5.0m).
  Determines the cell size of output rasters - smaller values provide more detail but larger files.

OUTPUT FILES:
-----------
* CSV Files:
  - height_bins.csv: Raw point counts for each height bin
  - nrd_values.csv: Calculated NRD values for each height
  
* Raster Files:
  - NRD rasters (GeoTIFF): Contain true NRD values for each height bin
  - VRT files: Virtual raster tables that combine multiple raster layers
  
* Documentation:
  - README.txt: Instructions for visualizing and using NRD rasters in QGIS

USAGE NOTES:
-----------
* Input data must have heights normalized relative to ground level
* NRD values range from 0 to 1, with 1 indicating all points are in that height bin
* Higher resolution rasters (smaller numbers) provide more spatial detail but larger files
* Filtered bins exclude height bins with too few points to be statistically valid
* The script can process individual files or entire directories
* Processing time depends on file size, point density, and raster resolution
"""

# -------------------------------------------------------------------------
# LOGGING CONFIGURATION
# -------------------------------------------------------------------------

# Configure logging - this sets up the format and level of detail for log messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure GDAL error reporting - controls how GDAL library errors are handled
gdal.UseExceptions()  # Enable exceptions for GDAL
gdal.PushErrorHandler('CPLQuietErrorHandler')  # Redirect error messages

# =========================================================================
# FUNCTION DEFINITIONS
# =========================================================================

def filter_height_artifacts(x_coords: np.ndarray, y_coords: np.ndarray, heights: np.ndarray, 
                            filter_method: str = 'statistical', 
                            slope_threshold: float = 45.0,
                            z_score_threshold: float = 2.5,
                            min_valid_height: float = -1.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Filter out height normalization artifacts, particularly negative heights from
    nearest neighbor normalization in complex topography.
    
    This function implements multiple filtering methods to detect and remove artifacts
    without requiring reprocessing of the original data.
    
    Args:
        x_coords: Array of x coordinates
        y_coords: Array of y coordinates
        heights: Array of height values
        filter_method: Method for filtering ('simple', 'statistical', 'local', 'combined')
        slope_threshold: Maximum allowed slope in degrees for local context filtering
        z_score_threshold: Z-score threshold for statistical filtering
        min_valid_height: Minimum allowed height (any points below this will be filtered)
        
    Returns:
        Tuple of filtered (x_coords, y_coords, heights)
    """
    # Return immediately if no points to filter
    if len(heights) == 0:
        return x_coords, y_coords, heights
    
    # Create a copy of the arrays to avoid modifying the originals
    x_filtered = x_coords.copy()
    y_filtered = y_coords.copy()
    heights_filtered = heights.copy()
    
    # Count initial negative heights for reporting
    neg_mask = heights_filtered < 0
    initial_neg_count = np.sum(neg_mask)
    
    # Skip filtering if no negative heights found
    if initial_neg_count == 0:
        logger.info("No negative heights found, skipping artifact filtering")
        return x_coords, y_coords, heights
    
    logger.info(f"Filtering height normalization artifacts from {len(heights)} points")
    logger.info(f"Initial negative heights: {initial_neg_count} ({initial_neg_count/len(heights)*100:.2f}%)")
    
    # Apply the selected filtering method
    if filter_method == 'simple':
        # Simple threshold-based filtering (remove all negative heights)
        # This is the most straightforward approach but may remove valid points in complex terrain
        valid_mask = heights_filtered >= 0
        
    elif filter_method == 'statistical':
        # Statistical filtering using z-scores
        # More robust to variable terrain as it adapts to the data distribution
        # Calculate mean and standard deviation of heights
        height_mean = np.mean(heights_filtered)
        height_std = np.std(heights_filtered)
        
        if height_std > 0:
            # Calculate z-scores (number of standard deviations from the mean)
            z_scores = np.abs((heights_filtered - height_mean) / height_std)
            # Points are valid if either:
            # 1. They are >= min_valid_height (to keep reasonable negative values if specified)
            # 2. They are not statistical outliers based on z-score
            valid_mask = (heights_filtered >= min_valid_height) | (z_scores <= z_score_threshold)
        else:
            # If standard deviation is 0, just use the minimum height threshold
            valid_mask = heights_filtered >= min_valid_height
            
    elif filter_method == 'local' or filter_method == 'combined':
        # For local context filtering, we need to look at neighborhood relationships
        # This is more computationally intensive but can better distinguish real terrain variations
        from scipy.spatial import cKDTree
        
        # Build a KD-tree for efficient spatial queries
        tree = cKDTree(np.column_stack([x_filtered, y_filtered]))
        
        # Convert slope threshold to height difference
        # For simplicity, we'll use a fixed radius based on point density
        point_density = len(heights) / ((np.max(x_coords) - np.min(x_coords)) * 
                                        (np.max(y_coords) - np.min(y_coords)))
        search_radius = 1.0 / np.sqrt(point_density) * 3  # Use ~3x the average point spacing
        
        # Maximum height difference based on slope (tangent of slope angle in radians)
        max_height_diff = search_radius * np.tan(np.radians(slope_threshold))
        
        # Initialize valid mask - assume all points are valid initially
        valid_mask = np.ones_like(heights_filtered, dtype=bool)
        
        # Process in batches to avoid memory issues
        batch_size = 10000  # Adjust this value based on available memory
        for i in range(0, len(heights_filtered), batch_size):
            batch_end = min(i + batch_size, len(heights_filtered))
            
            # Find neighbors within search radius for each point
            for j in range(i, batch_end):
                if heights_filtered[j] < 0:  # Only process negative heights
                    # Find nearby points
                    indices = tree.query_ball_point([x_filtered[j], y_filtered[j]], search_radius)
                    
                    if len(indices) > 1:  # Need at least one neighbor besides the point itself
                        neighbor_heights = heights_filtered[indices]
                        # Calculate height differences
                        height_diffs = np.abs(neighbor_heights - heights_filtered[j])
                        
                        # If any height difference exceeds what's expected from the terrain slope,
                        # mark as invalid. This identifies abrupt changes not consistent with natural terrain.
                        if np.max(height_diffs) > max_height_diff:
                            valid_mask[j] = False
        
        # For combined method, also apply statistical filtering
        # This uses both local context and statistical properties for more robust filtering
        if filter_method == 'combined':
            height_mean = np.mean(heights_filtered)
            height_std = np.std(heights_filtered)
            
            if height_std > 0:
                z_scores = np.abs((heights_filtered - height_mean) / height_std)
                # Combine with statistical filtering - a point must pass both filters
                valid_mask = valid_mask & ((heights_filtered >= min_valid_height) | 
                                          (z_scores <= z_score_threshold))
            else:
                # If standard deviation is 0, just use the minimum height threshold
                valid_mask = valid_mask & (heights_filtered >= min_valid_height)
    
    else:
        # Unknown method - use minimum height threshold as fallback
        logger.warning(f"Unknown filter method '{filter_method}', falling back to minimum height threshold")
        valid_mask = heights_filtered >= min_valid_height
    
    # Apply the filtering by selecting only valid points
    x_filtered = x_filtered[valid_mask]
    y_filtered = y_filtered[valid_mask]
    heights_filtered = heights_filtered[valid_mask]
    
    # Count remaining negative heights after filtering to report effectiveness
    remaining_neg_count = np.sum(heights_filtered < 0)
    removed_points = len(heights) - len(heights_filtered)
    
    logger.info(f"Filtering removed {removed_points} artifactual points ({removed_points/len(heights)*100:.2f}% of total)")
    logger.info(f"Remaining negative heights: {remaining_neg_count}")
    
    return x_filtered, y_filtered, heights_filtered

def read_lidar_file(file_path: str, vegetation_classes: Optional[List[int]] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Optional[int]]:
    """
    Read a LiDAR file and extract the coordinates (x, y, z) of vegetation points.
    
    This function opens a LiDAR point cloud file, filters points based on their
    classification codes to extract only vegetation, and returns their coordinates.
    The heights (z) should already be normalized to ground level (using tools like
    PDAL's filters.hag) before processing.
    
    Args:
        file_path: Path to the LiDAR file (.laz or .las)
        vegetation_classes: List of classification codes for vegetation points:
                           3 = Low Vegetation
                           4 = Medium Vegetation
                           5 = High Vegetation
        
    Returns:
        Tuple of (x, y, z) arrays containing coordinates of normalized vegetation points (in meters)
        and the EPSG code if available
    """
    # Use default vegetation classes if none provided
    if vegetation_classes is None:
        vegetation_classes = [3, 4, 5]
        
    # Validate inputs to prevent errors
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"LiDAR file not found: {file_path}")
    
    if not isinstance(vegetation_classes, list) or not all(isinstance(c, int) for c in vegetation_classes):
        raise ValueError("vegetation_classes must be a list of integers")
        
    try:
        # Check if file is .laz and requires decompression
        # Different backends (lazrs, laszip) are attempted for maximum compatibility
        if file_path.lower().endswith('.laz'):
            logger.info("Reading compressed LAZ file with lazrs backend")
            try:
                # First try with lazrs backend (fastest)
                las = laspy.read(file_path, laz_backend=laspy.LazBackend.LazrsNative)
            except Exception as laz_err:
                logger.error(f"Error with lazrs backend: {str(laz_err)}")
                # Try alternative backends
                logger.info("Trying with laszip backend...")
                try:
                    # Install the laszip package if not already installed
                    import importlib.util
                    if importlib.util.find_spec("laszip") is None:
                        logger.warning("laszip package not found, processing may fail")
                    
                    las = laspy.read(file_path, laz_backend=laspy.LazBackend.Laszip)
                except Exception as laszip_err:
                    logger.error(f"Error with laszip backend: {str(laszip_err)}")
                    # Try with automatic backend selection
                    logger.info("Trying with automatic backend selection...")
                    las = laspy.read(file_path)
        else:
            # For uncompressed .las files
            las = laspy.read(file_path)
        
        # Extract CRS information from file if available
        # CRS (Coordinate Reference System) is essential for proper geospatial analysis
        epsg_code = None
        try:
            # Try to get CRS information from las file (if present)
            if hasattr(las, 'header') and hasattr(las.header, 'vlrs'):
                for vlr in las.header.vlrs:
                    if vlr.record_id == 4001:  # WKT OGC CS VLR record ID
                        try:
                            # Extract WKT string and try to parse it
                            wkt = vlr.parsed_body.decode('utf-8')
                            srs = osr.SpatialReference()
                            srs.ImportFromWkt(wkt)
                            # Try to get EPSG code
                            srs.AutoIdentifyEPSG()
                            epsg_code = int(srs.GetAuthorityCode(None))
                            logger.info(f"Extracted EPSG code from LiDAR file: {epsg_code}")
                            break
                        except Exception as e:
                            logger.warning(f"Could not extract CRS from WKT: {e}")
        except Exception as crs_err:
            logger.warning(f"Could not extract CRS information: {str(crs_err)}")
        
        # Create a mask for points with classification in vegetation_classes
        # This is a boolean array marking which points belong to vegetation classes
        vegetation_mask = np.isin(las.classification, vegetation_classes)
        total_veg_points = np.sum(vegetation_mask)
        
        # Handle case where no vegetation points are found
        if total_veg_points == 0:
            logger.warning(f"No vegetation points found with classes {vegetation_classes}.")
            logger.info(f"Available classes: {np.unique(las.classification)}")
            return np.array([]), np.array([]), np.array([]), epsg_code
        
        # Extract coordinates from vegetation points using the mask
        x_coords = las.x[vegetation_mask]
        y_coords = las.y[vegetation_mask]
        heights = las.z[vegetation_mask]
        
        logger.info(f"Extracted {len(heights)} vegetation points from classes {vegetation_classes}")
        logger.info(f"Height range of vegetation data: {np.min(heights):.1f}m - {np.max(heights):.1f}m")
        
        return np.array(x_coords), np.array(y_coords), np.array(heights), epsg_code
        
    except Exception as e:
        # Comprehensive error handling with detailed traceback for debugging
        logger.error(f"Error reading LiDAR file {file_path}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        # Print more detailed traceback
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return np.array([]), np.array([]), np.array([]), None

def categorize_points_into_bins(points: np.ndarray, bin_size: float = 5.0, 
                               handle_negative_heights: bool = True) -> Tuple[Dict[str, int], np.ndarray]:
    """
    Categorize normalized vegetation points into vertical height bins.
    
    This function organizes the vegetation height points into discrete vertical bins,
    which is essential for analyzing the forest's vertical structure. Each bin
    represents a horizontal slice of the forest at a specific height range.
    
    Args:
        points: List of normalized point heights (in meters)
        bin_size: Size of each vertical bin in meters (default: 5.0)
        handle_negative_heights: Whether to handle negative height values (default: True)
        
    Returns:
        Tuple containing:
          - Dictionary with bin ranges as keys (e.g., "0.0-5.0m") and point counts as values
          - Array of bin edge values
    """
    # Validate inputs
    if bin_size <= 0:
        raise ValueError("bin_size must be positive")
        
    if len(points) == 0:
        return {}, np.array([])
    
    # Handle height statistics and report
    min_height = np.min(points)
    max_height = np.max(points)
    mean_height = np.mean(points)
    
    logger.info(f"Height statistics: min={min_height:.2f}m, max={max_height:.2f}m, mean={mean_height:.2f}m")
    
    # Handle negative heights if requested
    if handle_negative_heights and min_height < 0:
        logger.info(f"Found negative height values (minimum: {min_height:.2f}m), likely from nearest neighbor normalization")
        neg_count = np.sum(points < 0)
        logger.info(f"Number of negative height points: {neg_count} ({neg_count/len(points)*100:.2f}% of total)")
        
        # Create appropriate bin edges that include negative values
        min_bin_edge = np.floor(min_height / bin_size) * bin_size
        max_bin_edge = np.ceil(max_height / bin_size) * bin_size
        bin_edges = np.arange(min_bin_edge, max_bin_edge + bin_size, bin_size)
    else:
        # Original behavior - start from 0
        bin_edges = np.arange(0, max_height + bin_size, bin_size)
    
    # Using numpy's histogram for better performance
    counts, _ = np.histogram(points, bins=bin_edges)
    
    # Create dictionary of bin ranges and counts
    bins_dict = {}
    for i in range(len(counts)):
        if counts[i] > 0:  # Only include non-empty bins
            bin_key = f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}m"
            bins_dict[bin_key] = int(counts[i])  # Convert to int for consistent output
    
    return bins_dict, bin_edges

def create_rasters_for_height_bins(x: np.ndarray, y: np.ndarray, z: np.ndarray, 
                                  bin_edges: np.ndarray, output_dir: str, 
                                  file_name: str, resolution: float = 1.0,
                                  epsg_code: Optional[int] = None) -> None:
    """
    Create raster files for each height bin in the point cloud using GDAL.
    
    This function generates a series of GeoTIFF raster files, with each file representing
    the point density within a specific height bin. The resulting rasters can be used
    for spatial analysis of vegetation structure at different height levels.
    
    Note: If bin_edges are filtered to exclude low-point bins, only the provided bins
    will be processed.
    
    Args:
        x: Array of x coordinates
        y: Array of y coordinates
        z: Array of height values
        bin_edges: Array of bin edge values defining the height bins
        output_dir: Directory to save the output raster files
        file_name: Base name for the output files
        resolution: Spatial resolution (pixel size) of the output rasters in meters
        epsg_code: Optional EPSG code for the coordinate reference system (if known)
    """
    if len(x) == 0 or len(y) == 0 or len(z) == 0:
        logger.warning("No points to create rasters from")
        return
    
    # Create raster directory
    raster_dir = os.path.join(output_dir, "rasters")
    os.makedirs(raster_dir, exist_ok=True)
    
    # Determine raster extent with padding for better visualization
    x_min, x_max = np.min(x), np.max(x)
    y_min, y_max = np.min(y), np.max(y)
    
    # Add padding (2% on each side)
    padding_x = (x_max - x_min) * 0.02
    padding_y = (y_max - y_min) * 0.02
    
    x_min -= padding_x
    x_max += padding_x
    y_min -= padding_y
    y_max += padding_y
    
    # Calculate grid dimensions - ensure we have a reasonably sized raster (at least 100x100 pixels)
    width = max(100, int(np.ceil((x_max - x_min) / resolution)))
    height = max(100, int(np.ceil((y_max - y_min) / resolution)))
    
    # Adjust resolution to maintain the extent with these dimensions
    actual_x_res = (x_max - x_min) / width
    actual_y_res = (y_max - y_min) / height
    
    # Create geotransform (GDAL format: [top-left x, pixel width, x-rotation, top-left y, y-rotation, pixel height])
    geotransform = (x_min, actual_x_res, 0, y_max, 0, -actual_y_res)
    
    logger.info(f"Creating rasters with dimensions: {width}x{height} pixels at {actual_x_res:.2f}x{actual_y_res:.2f}m resolution")
    
    # Prepare VRT (Virtual Raster) options for a combined view of all layers
    vrt_options = gdal.BuildVRTOptions(separate=True)
    vrt_sources = []
    
    # Output histogram of height values for debugging
    height_hist, _ = np.histogram(z, bins=bin_edges)
    logger.info(f"Height distribution across bins:")
    for i in range(len(height_hist)):
        if i < len(bin_edges) - 1:
            logger.info(f"  Bin {bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}m: {height_hist[i]} points")
    
    # Process each height bin
    for i in range(len(bin_edges) - 1):
        bin_min = bin_edges[i]
        bin_max = bin_edges[i+1]
        bin_name = f"{bin_min:.1f}-{bin_max:.1f}m"
        
        # Filter points in this height bin
        mask = (z >= bin_min) & (z < bin_max)
        point_count = np.sum(mask)
        
        if point_count == 0:
            logger.info(f"No points in height bin {bin_name}, skipping raster creation")
            continue
        
        logger.info(f"Creating raster for height bin {bin_name} with {point_count} points")
        
        # For sparse data, using a larger fixed kernel can help with visualization
        if point_count < 1000:  # If sparse data
            # Create a KDE-like point density map using a gaussian kernel
            logger.info(f"Using kernel density estimation for sparse points in bin {bin_name}")
            
            # First create an empty grid
            bin_count = np.zeros((height, width))
            
            # Convert point coordinates to grid indices
            grid_x = np.floor((x[mask] - x_min) / actual_x_res).astype(int)
            grid_y = np.floor((y_max - y[mask]) / actual_y_res).astype(int)
            
            # Clip indices to valid range
            grid_x = np.clip(grid_x, 0, width-1)
            grid_y = np.clip(grid_y, 0, height-1)
            
            # Add points to the grid
            for px, py in zip(grid_x, grid_y):
                bin_count[py, px] += 1
            
            # Apply a gaussian filter to spread points for better visibility
            from scipy.ndimage import gaussian_filter
            sigma = max(2, min(5, 1000 // point_count))  # Adaptive kernel size
            bin_count = gaussian_filter(bin_count, sigma=sigma)
            
            # Scale values to 0-255 range for Byte type (for SetColorTable compatibility)
            if np.max(bin_count) > 0:
                bin_count = (bin_count / np.max(bin_count) * 255).astype(np.uint8)
        else:
            # Use scipy's binned_statistic_2d for higher point counts
            bin_count, _, _, _ = binned_statistic_2d(
                x[mask], y[mask], 
                values=np.ones(point_count), 
                statistic='count',
                bins=[width, height],
                range=[[x_min, x_max], [y_min, y_max]]
            )
            
            # Transpose and flip the output to match GeoTIFF orientation
            bin_count = np.flipud(bin_count.T)
            
            # Scale values to 0-255 range for Byte type (for SetColorTable compatibility)
            if np.max(bin_count) > 0:
                bin_count = (bin_count / np.max(bin_count) * 255).astype(np.uint8)
        
        # Replace NaN values with 0
        bin_count = np.nan_to_num(bin_count)
        
        # Define a more descriptive raster file name
        raster_filename = f"{file_name}_height_{bin_min:.1f}m_to_{bin_max:.1f}m.tif"
        raster_path = os.path.join(raster_dir, raster_filename)
        vrt_sources.append(raster_path)
        
        # Always use BYTE data type for compatibility with SetColorTable
        gdal_dtype = gdal.GDT_Byte
        
        try:
            # Create the raster file with GDAL creation options for better QGIS compatibility
            creation_options = [
                'COMPRESS=DEFLATE',  # Use compression
                'TILED=YES',         # Use tiling for faster display
                'BIGTIFF=IF_SAFER',  # Use BigTIFF if needed
                'PREDICTOR=2'        # Use horizontal differencing for better compression
            ]
            
            driver = gdal.GetDriverByName('GTiff')
            dataset = driver.Create(
                raster_path,
                width,
                height,
                1,  # Number of bands
                gdal_dtype,
                options=creation_options
            )
            
            # Set the geotransform and projection
            dataset.SetGeoTransform(geotransform)
            
            # Set the coordinate reference system
            srs = osr.SpatialReference()
            if epsg_code is not None:
                srs.ImportFromEPSG(epsg_code)
                logger.info(f"Setting projection to EPSG:{epsg_code}")
            else:
                # Default to WGS84 if no EPSG provided
                srs.ImportFromEPSG(4326)  # WGS84
                logger.warning(f"No EPSG code provided, defaulting to WGS84 (EPSG:4326)")
            
            # Ensure we use the modern WKT1 format that QGIS prefers
            srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            dataset.SetProjection(srs.ExportToWkt())
            
            # Write the data to the raster band
            band = dataset.GetRasterBand(1)
            band.WriteArray(bin_count)
            
            # Add metadata
            band.SetDescription(f"Vegetation point density in height bin {bin_name}")
            
            # Explicitly set NoData value
            band.SetNoDataValue(0)
            
            # Set color interpretation (helps QGIS display it better)
            band.SetColorInterpretation(gdal.GCI_GrayIndex)
            
            # Create a default color table for better visualization
            colorTable = gdal.ColorTable()
            for i in range(256):
                colorTable.SetColorEntry(i, (0, i, 0, 255))  # Green gradient
            
            # Try-except block for setting color table
            try:
                band.SetColorTable(colorTable)
            except RuntimeError as e:
                logger.warning(f"Could not set color table: {e}")
                logger.info("Continuing without custom color table - you can set colors in QGIS")
            
            # Compute statistics for the raster (min, max, mean, stddev)
            band.ComputeStatistics(False)
            
            # Clean up to close the dataset
            band = None
            dataset = None
            
            # Create a .aux.xml file with visualization hints for QGIS
            with open(f"{raster_path}.aux.xml", 'w') as f:
                f.write(f"""<PAMDataset>
  <PAMRasterBand band="1">
    <Metadata>
      <MDI key="STATISTICS_MINIMUM">0</MDI>
      <MDI key="STATISTICS_MAXIMUM">255</MDI>
      <MDI key="STATISTICS_MEAN">{np.mean(bin_count):.6f}</MDI>
      <MDI key="STATISTICS_STDDEV">{np.std(bin_count):.6f}</MDI>
      <MDI key="DESCRIPTION">Vegetation point density in height bin {bin_name}</MDI>
    </Metadata>
    <GDALRasterAttributeTable>
      <FieldDefn index="0">
        <Name>Value</Name>
        <Type>0</Type>
        <Usage>0</Usage>
      </FieldDefn>
      <FieldDefn index="1">
        <Name>Count</Name>
        <Type>1</Type>
        <Usage>1</Usage>
      </FieldDefn>
    </GDALRasterAttributeTable>
  </PAMRasterBand>
</PAMDataset>""")
            
            logger.info(f"Raster created: {raster_path}")
            
        except Exception as e:
            logger.error(f"Error creating raster {raster_path}: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Create a VRT file for combined visualization of all height bins
    if len(vrt_sources) > 0:
        vrt_path = os.path.join(output_dir, f"{file_name}_all_height_bins.vrt")
        gdal.BuildVRT(vrt_path, vrt_sources, options=vrt_options)
        logger.info(f"Created combined VRT file for all height bins: {vrt_path}")
        
        # Create a simple README file with instructions
        readme_path = os.path.join(output_dir, "README_QGIS_VISUALIZATION.txt")
        with open(readme_path, 'w') as f:
            f.write(f"""QGIS VISUALIZATION INSTRUCTIONS
==============================

To visualize the NRD raster layers in QGIS:

1. Individual height bins: 
   - Open each .tif file in the 'rasters' folder
   - Right-click the layer and select 'Properties'
   - Go to 'Symbology' tab
   - Set Render type to 'Singleband pseudocolor'
   - Select a color ramp (e.g. Viridis, Greens, Spectral)
   - Click 'Apply' and 'OK'

2. Combined visualization:
   - Open the file "{file_name}_all_height_bins.vrt"
   - This contains all height bins as separate bands
   - Use the 'Multiband color' render type to create RGB composites of different height layers

UNDERSTANDING THE DATA:
---------------------
- Raster files: Contain normalized point densities (0-255) for each height bin.
  These represent the spatial distribution of vegetation at each height stratum.

- CSV files: 
  * {file_name}_height_bins.csv - Contains raw point counts for each height bin
  * {file_name}_nrd_values.csv - Contains Normalized Return Density (NRD) values
  
- NRD Calculation: NRD = (points in current bin) / (points in current bin and all bins BELOW it)
  This represents the proportion of vegetation at a specific height relative to
  all vegetation from the ground up to that height.

Note: If rasters appear blank, check that:
- You've zoomed to the layer extent (right-click layer > Zoom to Layer)
- Under Layer Properties > Symbology, try adjusting Min/Max values
- Try setting "Min/Max value settings" to "Cumulative count cut" with 2% - 98% range
""")
        logger.info(f"Created README file with QGIS visualization instructions: {readme_path}")
    else:
        logger.warning("No valid rasters were created for any height bin")

def create_true_nrd_rasters(x: np.ndarray, y: np.ndarray, z: np.ndarray, 
                           bin_edges: np.ndarray, output_dir: str, 
                           file_name: str, resolution: float = 1.0,
                           epsg_code: Optional[int] = None) -> None:
    """
    Create raster files with true NRD values for each height bin using GDAL.
    
    This function generates a series of GeoTIFF raster files, with each file representing
    the actual Normalized Return Density (NRD) at each location. These rasters contain 
    the true NRD values calculated as: points in bin / (points in bin and all bins below).
    
    These NRD rasters allow for direct application of the Beer-Lambert law for
    calculation of Plant Area Density (PAD).
    
    Args:
        x: Array of x coordinates
        y: Array of y coordinates
        z: Array of height values
        bin_edges: Array of bin edge values defining the height bins
        output_dir: Directory to save the output raster files
        file_name: Base name for the output files
        resolution: Spatial resolution (pixel size) of the output rasters in meters
        epsg_code: Optional EPSG code for the coordinate reference system (if known)
    """
    if len(x) == 0 or len(y) == 0 or len(z) == 0:
        logger.warning("No points to create NRD rasters from")
        return
    
    # Create NRD raster directory
    nrd_raster_dir = os.path.join(output_dir, "nrd_rasters")
    os.makedirs(nrd_raster_dir, exist_ok=True)
    
    # Determine raster extent with padding for better visualization
    x_min, x_max = np.min(x), np.max(x)
    y_min, y_max = np.min(y), np.max(y)
    
    # Add padding (2% on each side)
    padding_x = (x_max - x_min) * 0.02
    padding_y = (y_max - y_min) * 0.02
    
    x_min -= padding_x
    x_max += padding_x
    y_min -= padding_y
    y_max += padding_y
    
    # Calculate grid dimensions - NO MORE MINIMUM SIZE CONSTRAINT
    width = int(np.ceil((x_max - x_min) / resolution))
    height = int(np.ceil((y_max - y_min) / resolution))
    
    # Adjust resolution to maintain the extent with these dimensions
    actual_x_res = (x_max - x_min) / width
    actual_y_res = (y_max - y_min) / height
    
    # Create geotransform (GDAL format: [top-left x, pixel width, x-rotation, top-left y, y-rotation, pixel height])
    geotransform = (x_min, actual_x_res, 0, y_max, 0, -actual_y_res)
    
    logger.info(f"Creating true NRD rasters with dimensions: {width}x{height} pixels at {actual_x_res:.2f}x{actual_y_res:.2f}m resolution")
    logger.debug(f"Extent: X [{x_min:.2f}, {x_max:.2f}], Y [{y_min:.2f}, {y_max:.2f}]")
    logger.debug(f"Point cloud X range: [{np.min(x):.2f}, {np.max(x):.2f}], Y range: [{np.min(y):.2f}, {np.max(y):.2f}]")
    
    # Prepare VRT (Virtual Raster) options for a combined view of all layers
    vrt_options = gdal.BuildVRTOptions(separate=True)
    vrt_sources = []
    
    # Create a 3D grid to count points in each bin and cell
    grid_x = np.floor((x - x_min) / actual_x_res).astype(int)
    grid_y = np.floor((y_max - y) / actual_y_res).astype(int)
    
    # Clip indices to valid range
    grid_x = np.clip(grid_x, 0, width-1)
    grid_y = np.clip(grid_y, 0, height-1)
    
    # Initialize the bin count grid - dimensions: [height bin, y, x]
    num_bins = len(bin_edges) - 1
    bin_counts = np.zeros((num_bins, height, width), dtype=np.int32)
    
    # Assign points to bins and grid cells
    for i in range(len(x)):
        # Find the bin index for this point
        for bin_idx in range(num_bins):
            if bin_edges[bin_idx] <= z[i] < bin_edges[bin_idx+1]:
                # Increment the count for this bin and grid cell
                bin_counts[bin_idx, grid_y[i], grid_x[i]] += 1
                break
    
    # Calculate cumulative bin counts from bottom to top for each grid cell
    # This follows the correct NRD calculation as points in bin / (points in bin and all bins below)
    cumulative_counts = np.zeros_like(bin_counts, dtype=np.int32)
    for y_idx in range(height):
        for x_idx in range(width):
            # Calculate cumulative counts from bin 0 up to current bin
            running_sum = 0
            for bin_idx in range(num_bins):
                running_sum += bin_counts[bin_idx, y_idx, x_idx]
                cumulative_counts[bin_idx, y_idx, x_idx] = running_sum
    
    # Process each height bin to create NRD rasters
    for bin_idx in range(num_bins):
        bin_min = bin_edges[bin_idx]
        bin_max = bin_edges[bin_idx+1]
        bin_name = f"{bin_min:.1f}-{bin_max:.1f}m"
        
        # Calculate NRD values for this bin
        # NRD = points in bin / cumulative points up to and including this bin
        nrd_values = np.zeros((height, width), dtype=np.float32)
        mask = cumulative_counts[bin_idx, :, :] > 0
        nrd_values[mask] = bin_counts[bin_idx, :, :][mask].astype(np.float32) / cumulative_counts[bin_idx, :, :][mask].astype(np.float32)
        
        # Define a descriptive raster file name
        raster_filename = f"{file_name}_nrd_{bin_min:.1f}m_to_{bin_max:.1f}m.tif"
        raster_path = os.path.join(nrd_raster_dir, raster_filename)
        vrt_sources.append(raster_path)
        
        # Use Float32 data type for NRD values (0.0-1.0 range)
        gdal_dtype = gdal.GDT_Float32
        
        try:
            # Create the raster file with GDAL creation options
            creation_options = [
                'COMPRESS=DEFLATE',  # Use compression
                'TILED=YES',         # Use tiling for faster display
                'BIGTIFF=IF_SAFER',  # Use BigTIFF if needed
                'PREDICTOR=2'        # Use horizontal differencing for better compression
            ]
            
            driver = gdal.GetDriverByName('GTiff')
            dataset = driver.Create(
                raster_path,
                width,
                height,
                1,  # Number of bands
                gdal_dtype,
                options=creation_options
            )
            
            # Set the geotransform and projection
            dataset.SetGeoTransform(geotransform)
            
            # Set the coordinate reference system
            srs = osr.SpatialReference()
            if epsg_code is not None:
                srs.ImportFromEPSG(epsg_code)
                logger.info(f"Setting projection to EPSG:{epsg_code}")
            else:
                # Default to WGS84 if no EPSG provided
                srs.ImportFromEPSG(4326)  # WGS84
                logger.warning(f"No EPSG code provided, defaulting to WGS84 (EPSG:4326)")
            
            # Ensure we use the modern WKT1 format that QGIS prefers
            srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            dataset.SetProjection(srs.ExportToWkt())
            
            # Write the data to the raster band
            band = dataset.GetRasterBand(1)
            band.WriteArray(nrd_values)
            
            # Add metadata
            band.SetDescription(f"True NRD values for height bin {bin_name}")
            
            # Explicitly set NoData value
            band.SetNoDataValue(0)
            
            # Compute statistics for the raster (min, max, mean, stddev)
            band.ComputeStatistics(False)
            
            # Clean up to close the dataset
            band = None
            dataset = None
            
            logger.info(f"True NRD raster created: {raster_path}")
            
        except Exception as e:
            logger.error(f"Error creating NRD raster {raster_path}: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Create a VRT file for combined visualization of all NRD bins
    if len(vrt_sources) > 0:
        vrt_path = os.path.join(output_dir, f"{file_name}_all_nrd_bins.vrt")
        gdal.BuildVRT(vrt_path, vrt_sources, options=vrt_options)
        logger.info(f"Created combined VRT file for all NRD bins: {vrt_path}")
        
        # Create a simple README file with instructions
        readme_path = os.path.join(output_dir, "README_NRD_RASTERS.txt")
        with open(readme_path, 'w') as f:
            f.write(f"""NORMALIZED RETURN DENSITY (NRD) RASTERS
==============================

These rasters contain true Normalized Return Density (NRD) values calculated as:
NRD = (points in current bin) / (points in current bin and all bins BELOW it)

Each pixel value represents the actual NRD value (0.0-1.0) at that location.
These rasters are used as the primary input for Plant Area Density (PAD) calculation
using the Beer-Lambert law.

To visualize the NRD rasters in QGIS:
1. Open each .tif file in the 'nrd_rasters' folder
2. Right-click the layer and select 'Properties'
3. Go to 'Symbology' tab
4. Set Render type to 'Singleband pseudocolor'
5. Select a color ramp (e.g. Viridis, Spectral)
6. Set Min/Max values to 0-1 for consistent visualization
7. Click 'Apply' and 'OK'

Combined visualization:
- Open the file "{file_name}_all_nrd_bins.vrt"
- This contains all NRD values as separate bands
- Use the 'Multiband color' render type to create RGB composites of different height layers

UNDERSTANDING THE DATA:
---------------------
- NRD raster files: Contain true NRD values (0-1 range) for each height bin.
  These represent the proportion of vegetation at a given height relative to 
  all vegetation from the ground up to that height.

- CSV files: 
  * {file_name}_height_bins.csv - Contains raw point counts for each height bin
  * {file_name}_nrd_values.csv - Contains Normalized Return Density (NRD) values
  
- Processing workflow:
  1. These NRD rasters are used directly by PAD_calculation.py
  2. The Beer-Lambert law is applied to calculate PAD values
  3. PAD rasters are produced for use in forest fire modeling
""")
        logger.info(f"Created README file with NRD raster instructions: {readme_path}")
    else:
        logger.warning("No valid NRD rasters were created for any height bin")

def process_lidar_file(file_path: str, output_dir: str, bin_size: float = 5.0,
                      vegetation_classes: Optional[List[int]] = None,
                      show_cumulative: bool = True,
                      create_rasters: bool = True,
                      raster_resolution: float = 1.0,
                      epsg_code: Optional[int] = None,
                      handle_negative_heights: bool = True,
                      filter_negative_heights: bool = True,
                      filter_artifacts: bool = False,
                      filter_method: str = 'statistical',
                      z_score_threshold: float = 2.5,
                      slope_threshold: float = 45.0,
                      min_valid_height: float = -1.0,
                      min_points_percent: float = 0.1) -> None:
    """
    Process a LiDAR file to calculate NRD values and visualize them.
    
    The Normalized Return Density (NRD) is calculated as:
    NRD = (points in current bin) / (points in current bin and all bins BELOW it)
    
    This provides a measure of what proportion of all points up to a given height 
    are found in that specific height layer, representing forest structure from the ground up.
    
    Args:
        file_path: Path to the LiDAR file (.laz or .las)
        output_dir: Directory to save output files
        bin_size: Size of each height bin in meters (default: 5.0)
        vegetation_classes: List of classification codes for vegetation points (default: [3, 4, 5])
        show_cumulative: Whether to show cumulative height distribution (default: True)
        create_rasters: Whether to create raster files for each height bin (default: True)
        raster_resolution: Spatial resolution of output rasters in meters (default: 1.0)
        epsg_code: EPSG code to use for raster output (if None, will attempt to extract from LiDAR file)
        handle_negative_heights: Whether to handle negative height values from normalization (default: True)
        filter_negative_heights: Whether to filter out negative heights for NRD calculation (default: True)
        filter_artifacts: Whether to apply statistical filtering to remove normalization artifacts (default: False)
        filter_method: Method for artifact filtering ('simple', 'statistical', 'local', 'combined')
        z_score_threshold: Z-score threshold for statistical filtering (default: 2.5)
        slope_threshold: Maximum allowed slope in degrees for local context filtering (default: 45.0)
        min_valid_height: Minimum allowed height after filtering (default: -1.0)
        min_points_percent: Minimum percentage of total points required for a bin to be considered valid (default: 0.1%)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract file name without extension for output file naming
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Read LiDAR file and extract vegetation points
    logger.info(f"Reading LiDAR file: {file_path}")
    x_coords, y_coords, heights, extracted_epsg = read_lidar_file(file_path, vegetation_classes)
    
    if len(heights) == 0:
        logger.error("No vegetation points found in the LiDAR file. Cannot proceed.")
        return
    
    # Make copies of original data for raster creation
    original_x, original_y, original_heights = x_coords.copy(), y_coords.copy(), heights.copy()
    
    # Apply artifact filtering if requested (for BOTH analysis and visualization)
    if filter_artifacts:
        logger.info(f"Applying {filter_method} filtering to remove height normalization artifacts")
        x_coords, y_coords, heights = filter_height_artifacts(
            x_coords, y_coords, heights,
            filter_method=filter_method,
            z_score_threshold=z_score_threshold,
            slope_threshold=slope_threshold,
            min_valid_height=min_valid_height
        )
        
        # If no points remain after filtering, log error and exit
        if len(heights) == 0:
            logger.error("No points remain after artifact filtering. Cannot proceed.")
            return
            
        # Update original copies to use the filtered data for raster creation too
        original_x, original_y, original_heights = x_coords.copy(), y_coords.copy(), heights.copy()
    
    # Check for negative height values from normalization (separate from filtering for NRD calculation)
    neg_mask = heights < 0
    has_negative_heights = np.any(neg_mask)
    neg_count = np.sum(neg_mask)
    
    if has_negative_heights:
        min_height = np.min(heights)
        logger.info(f"Found {neg_count} negative height values (minimum: {min_height:.2f}m)")
        logger.info(f"These likely result from nearest neighbor normalization artifacts")
        logger.info(f"Negative points represent {neg_count/len(heights)*100:.2f}% of total points")
        
        if filter_negative_heights:
            # Create copies of coordinates for full dataset (including negatives) for raster creation
            full_x_coords, full_y_coords, full_heights = x_coords.copy(), y_coords.copy(), heights.copy()
            
            # Filter out negative heights for NRD calculation
            logger.info(f"Filtering out negative heights for NRD calculation (standard methodology)")
            x_coords = x_coords[~neg_mask]
            y_coords = y_coords[~neg_mask]
            heights = heights[~neg_mask]
            logger.info(f"Retained {len(heights)} points with non-negative heights for analysis")
    
    # Check for unusually low height range which may indicate issues with the data
    max_height = np.max(heights)
    if max_height < 1.0 and not has_negative_heights:  # Only warn if no negative heights and max is low
        logger.warning(f"WARNING: Maximum vegetation height is only {max_height:.2f}m")
        logger.warning("This is unusually low for vegetation and may indicate issues with:")
        logger.warning("1. Height normalization not correctly applied to the input data")
        logger.warning("2. LiDAR classification - wrong points may be classified as vegetation")
        logger.warning("3. Scale factors or units in the LiDAR file")
        logger.warning("Consider checking your LiDAR preprocessing workflow.")
    
    # If epsg_code is not provided, use the one extracted from the file
    if epsg_code is None and extracted_epsg is not None:
        epsg_code = extracted_epsg
        logger.info(f"Using EPSG code {epsg_code} extracted from LiDAR file")
    
    # Categorize points into height bins
    logger.info(f"Categorizing points into height bins with bin size {bin_size}m")
    bins_dict, bin_edges = categorize_points_into_bins(heights, bin_size, False)  # Don't include negative bins for NRD calculation
    
    # Calculate the minimum number of points required for a bin to be considered valid (0.1% of total points)
    total_points = sum(bins_dict.values())
    min_points_threshold = max(5, int(total_points * min_points_percent / 100))  # At least 5 points
    logger.info(f"Total points: {total_points}, minimum threshold: {min_points_threshold} points ({min_points_percent}% of total)")
    
    # Filter out bins with too few points
    original_bins_dict = bins_dict.copy()  # Keep original for reference
    filtered_bins_dict = {k: v for k, v in bins_dict.items() if v >= min_points_threshold}
    removed_bins = {k: v for k, v in bins_dict.items() if v < min_points_threshold}
    
    if removed_bins:
        logger.info(f"Removed {len(removed_bins)} height bins with fewer than {min_points_threshold} points:")
        for bin_key, count in removed_bins.items():
            logger.info(f"  - Bin {bin_key}: {count} points")
    
    # Update bins_dict to use filtered bins
    bins_dict = filtered_bins_dict
    
    if len(bins_dict) == 0:
        logger.error("No height bins remain after filtering. Cannot proceed.")
        return
    
    # Write all bins to CSV file (including filtered ones for reference)
    csv_output_path = os.path.join(output_dir, f"{file_name}_height_bins.csv")
    logger.info(f"Writing height bins to CSV: {csv_output_path}")
    with open(csv_output_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['Height Bin', 'Point Count', 'Status'])
        
        # Sort bins by height for better readability
        sorted_all_bins = sorted(original_bins_dict.keys(), key=lambda x: float(x.split('-')[0]))
        
        for bin_key in sorted_all_bins:
            count = original_bins_dict[bin_key]
            status = "Included" if bin_key in filtered_bins_dict else f"Excluded (<{min_points_threshold} points)"
            csv_writer.writerow([bin_key, count, status])
    
    # Calculate NRD values using only filtered bins
    logger.info("Calculating NRD values using filtered bins")
    nrd_data = []
    
    # Sort bin keys by lower height value for consistent processing (lowest to highest)
    sorted_bin_keys = sorted(bins_dict.keys(), 
                            key=lambda x: float(x.split('-')[0]))
    
    # Process each bin to calculate NRD
    for i, bin_key in enumerate(sorted_bin_keys):
        bin_min = float(bin_key.split('-')[0])
        points_in_bin = bins_dict[bin_key]
        
        # Sum points in this bin and all LOWER bins (i.e., from ground up to current height)
        # This uses slice [:i+1] which includes all bins from index 0 up to and including current bin i
        points_cumulative = sum([bins_dict[k] for k in sorted_bin_keys[:i+1]])
        
        # NRD calculation: points in current bin / total points up to and including this height
        # This represents the proportion of vegetation at this specific height relative to 
        # all vegetation from the ground up to this height
        if points_cumulative > 0:
            nrd = points_in_bin / points_cumulative
        else:
            nrd = 0
        
        nrd_data.append((bin_min, nrd))
    
    # Write NRD values to CSV
    nrd_csv_path = os.path.join(output_dir, f"{file_name}_nrd_values.csv")
    logger.info(f"Writing NRD values to CSV: {nrd_csv_path}")
    with open(nrd_csv_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['Height (m)', 'NRD Value'])
        csv_writer.writerow(['Note', 'NRD = (points in current bin) / (points in current bin and all bins BELOW it)'])
        csv_writer.writerow(['Threshold', f'Bins with <{min_points_threshold} points ({min_points_percent}% of total) were excluded'])
        for height, nrd in nrd_data:
            csv_writer.writerow([height, nrd])
    
    # Extract data for visualization
    heights_list = [float(k.split('-')[0]) for k in sorted_bin_keys]
    counts_list = [bins_dict[k] for k in sorted_bin_keys]
    nrd_heights = [h for h, _ in nrd_data]
    nrd_values = [n for _, n in nrd_data]
    
    # Calculate cumulative counts for visualization
        cumulative_counts = []
        running_total = 0
        for count in counts_list:
            running_total += count
            cumulative_counts.append(running_total)
        
    # 1. Create enhanced visualization with three panels
    plt.figure(figsize=(15, 8))
    
    # 1.1 Plot raw point counts (left panel)
    ax1 = plt.subplot(1, 3, 1)
    ax1.barh(heights_list, counts_list, height=bin_size*0.9, alpha=0.7, color='forestgreen')
    ax1.set_title('Raw Point Counts by Height')
    ax1.set_xlabel('Number of Points')
    ax1.set_ylabel('Height (m)')
    ax1.grid(True, alpha=0.3)
    # Add count labels to the bars
    for i, v in enumerate(counts_list):
        if v > 0:  # Only label non-zero bars
            ax1.text(v + max(counts_list)*0.01, heights_list[i], f"{v}", 
                    va='center', fontsize=8)
    
    # 1.2 Plot cumulative point counts (middle panel)
    ax2 = plt.subplot(1, 3, 2, sharey=ax1)
    ax2.barh(heights_list, cumulative_counts, height=bin_size*0.9, alpha=0.7, color='teal')
    ax2.set_title('Cumulative Point Counts\n(Ground to Height)')
    ax2.set_xlabel('Cumulative Number of Points')
    ax2.set_ylabel('')  # Hide y label since it's shared
    ax2.grid(True, alpha=0.3)
    # Add custom legend explaining the cumulative concept
    ax2.text(0.5, -0.1, 'Sum of all points from ground up to this height',
             ha='center', transform=ax2.transAxes, fontsize=9, style='italic')
    
    # 1.3 Plot NRD values as horizontal bars (right panel)
    ax3 = plt.subplot(1, 3, 3, sharey=ax1)
    bars = ax3.barh(nrd_heights, nrd_values, height=bin_size*0.9, alpha=0.8, color='royalblue')
    ax3.set_title('Normalized Return Density (NRD)')
    ax3.set_xlabel('NRD Value\n(points in current bin / points in current bin and all bins BELOW it)')
    ax3.set_ylabel('')  # Hide y label since it's shared
    ax3.set_xlim(0, 1)
    ax3.grid(True, alpha=0.3)
    # Add NRD value labels to the bars
    for i, v in enumerate(nrd_values):
        if v > 0:  # Only label non-zero bars
            ax3.text(v + 0.02, nrd_heights[i], f"{v:.2f}", va='center', fontsize=8)
    
    # Add overall title and NRD explanation
    plt.suptitle(f'Forest Vertical Structure Analysis - {file_name}', fontsize=14)
    plt.figtext(0.5, 0.01, 
                f"Note: NRD = (points in current bin) / (points in current bin and all bins BELOW it)\n"
                f"Bins with fewer than {min_points_threshold} points ({min_points_percent}% of total) were excluded", 
                ha='center', fontsize=9, style='italic')
    
    # Adjust layout and save the multi-panel plot
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])  # Adjust for suptitle and footer text
    multipanel_path = os.path.join(output_dir, f"{file_name}_nrd_multipanel.png")
    plt.savefig(multipanel_path, dpi=300, bbox_inches='tight')
    logger.info(f"Created multi-panel visualization: {multipanel_path}")
    plt.close()
    
    # 2. Create a forest structure visualization (stacked horizontal bars with forest layers)
    plt.figure(figsize=(12, 8))
    
    # Define standard forest stratum classifications
    # Heights depend on forest type, these are approximate for demonstration
    strata_colors = {
        'canopy': '#005c29',       # Dark green
        'subcanopy': '#088f41',    # Medium green
        'understory': '#7dcca4',   # Light green
        'shrub': '#aed9b7',        # Very light green
        'ground': '#e5f1e6'        # Almost white
    }
    
    # Prepare data for strata visualization
    heights_array = np.array(nrd_heights)
    
    # Function to categorize heights into forest strata
    def categorize_height(height):
        if height >= 20:
            return 'canopy'
        elif height >= 10:
            return 'subcanopy'
        elif height >= 5:
            return 'understory'
        elif height >= 1:
            return 'shrub'
        else:
            return 'ground'
    
    # Categorize each height bin
    strata = [categorize_height(h) for h in heights_array]
    
    # Plot NRD values as horizontal bars, colored by forest stratum
    for i, (height, nrd, stratum) in enumerate(zip(nrd_heights, nrd_values, strata)):
        plt.barh(height, nrd, height=bin_size*0.9, color=strata_colors[stratum], alpha=0.8)
        # Add labels for NRD values
        if nrd > 0.1:  # Only label bars with sufficient width
            plt.text(nrd - 0.05, height, f"{nrd:.2f}", va='center', ha='right', 
                    color='white', fontweight='bold', fontsize=9)
        else:
            plt.text(nrd + 0.02, height, f"{nrd:.2f}", va='center', fontsize=8)
    
    # Add forest stratum legend
    handles = [plt.Rectangle((0,0),1,1, color=color) for color in strata_colors.values()]
    labels = [f"{stratum.capitalize()}" for stratum in strata_colors.keys()]
    plt.legend(handles, labels, title="Forest Strata", bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Customize the plot
    plt.title(f'Forest Vertical Structure - NRD Profile\n{file_name}', fontsize=14)
    plt.xlabel('Normalized Return Density (NRD)')
    plt.ylabel('Height (m)')
    plt.xlim(0, 1)
    plt.grid(True, alpha=0.3)
    
    # Add explanatory notes
    plt.figtext(0.5, 0.01, 
                f"NRD = (points in current bin) / (points in current bin and all bins BELOW it)\n"
                f"Higher NRD values indicate denser vegetation at that height level relative to what's below",
                ha='center', fontsize=9, style='italic')
    
    # Adjust layout and save the forest structure plot
    plt.tight_layout(rect=[0, 0.03, 0.85, 0.97])  # Make room for legend and text
    structure_path = os.path.join(output_dir, f"{file_name}_forest_structure.png")
    plt.savefig(structure_path, dpi=300, bbox_inches='tight')
    logger.info(f"Created forest structure visualization: {structure_path}")
    plt.close()
    
    # 3. Create a minimal version of the original visualization for backward compatibility
    plt.figure(figsize=(10, 6))
    
    # Plot height bin distribution (modified from original)
    plt.subplot(1, 2, 1)
    
    if show_cumulative:
        plt.bar(heights_list, cumulative_counts, width=bin_size*0.9, alpha=0.7, color='green')
        plt.title('Cumulative Point Count by Height')
        plt.ylabel('Cumulative Point Count')
    else:
        plt.bar(heights_list, counts_list, width=bin_size*0.9, alpha=0.7, color='green')
        plt.title('Point Count by Height Bin')
        plt.ylabel('Point Count')
    
    plt.xlabel('Height (m)')
    plt.grid(True, alpha=0.3)
    
    # Plot NRD values (original format for compatibility)
    plt.subplot(1, 2, 2)
    plt.plot(nrd_values, nrd_heights, 'o-', color='blue', linewidth=2)
    plt.title('Normalized Return Density (NRD)')
    plt.xlabel('NRD Value')
    plt.ylabel('Height (m)')
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 1)
    
    # Add a note about the threshold
    plt.figtext(0.5, 0.01, f"Note: Bins with fewer than {min_points_threshold} points ({min_points_percent}% of total) were excluded", 
                ha='center', fontsize=9, style='italic')
    
    # Adjust layout and save the plot (original format)
    plt.tight_layout()
    plot_path = os.path.join(output_dir, f"{file_name}_nrd_visualization.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    logger.info(f"Created original visualization: {plot_path}")
    plt.close()
    
    # Create rasters for each height bin if requested
    if create_rasters:
        logger.info(f"Creating true NRD rasters with resolution {raster_resolution}m")
        
        # If artifact filtering was applied, we already have the filtered data in original_x/y/heights
        if has_negative_heights and filter_negative_heights and not filter_artifacts:
            logger.info(f"Using complete dataset for raster creation but only for filtered height bins")
            
            # Get the height ranges from the filtered bins
            filtered_height_ranges = []
            for bin_key in sorted_bin_keys:
                min_height = float(bin_key.split('-')[0])
                max_height = float(bin_key.split('-')[1].replace('m', ''))
                filtered_height_ranges.append((min_height, max_height))
            
            # Create custom bin edges for raster creation that only include filtered bins
            filtered_bin_edges = []
            for min_h, max_h in filtered_height_ranges:
                if not filtered_bin_edges or filtered_bin_edges[-1] != min_h:
                    filtered_bin_edges.append(min_h)
                filtered_bin_edges.append(max_h)
            
            filtered_bin_edges = np.array(filtered_bin_edges)
            
            # Create true NRD rasters with the filtered bins
            logger.info(f"Creating true NRD rasters for {len(filtered_height_ranges)} filtered height bins")
            create_true_nrd_rasters(
                original_x, original_y, original_heights, 
                filtered_bin_edges, output_dir, file_name, 
                resolution=raster_resolution,
                epsg_code=epsg_code
            )
        else:
            # Create custom bin edges from filtered bins
            filtered_height_ranges = []
            for bin_key in sorted_bin_keys:
                min_height = float(bin_key.split('-')[0])
                max_height = float(bin_key.split('-')[1].replace('m', ''))
                filtered_height_ranges.append((min_height, max_height))
            
            filtered_bin_edges = []
            for min_h, max_h in filtered_height_ranges:
                if not filtered_bin_edges or filtered_bin_edges[-1] != min_h:
                    filtered_bin_edges.append(min_h)
                filtered_bin_edges.append(max_h)
            
            filtered_bin_edges = np.array(filtered_bin_edges)
            
            # Create true NRD rasters with the filtered bins
            logger.info(f"Creating true NRD rasters for {len(filtered_height_ranges)} filtered height bins")
            create_true_nrd_rasters(
                original_x, original_y, original_heights, 
                filtered_bin_edges, output_dir, file_name, 
                resolution=raster_resolution,
                epsg_code=epsg_code
            )
    
    logger.info(f"Processing completed for {file_path}")

def process_directory(input_dir: str, output_base_dir: str, bin_size: float = 2.0,
                    vegetation_classes: Optional[List[int]] = None,
                    show_cumulative: bool = True,
                    create_rasters: bool = True,
                    raster_resolution: float = 5.0,
                    epsg_code: Optional[int] = None,
                    handle_negative_heights: bool = True,
                    filter_negative_heights: bool = True,
                    filter_artifacts: bool = False,
                    filter_method: str = 'statistical',
                    z_score_threshold: float = 2.5,
                    slope_threshold: float = 45.0,
                    min_valid_height: float = -1.0,
                    min_points_percent: float = 0.1) -> None:
    """
    Process all LiDAR files in a directory to calculate NRD values and visualize them.
    Creates a separate output folder for each input file.
    
    Args:
        input_dir: Directory containing LiDAR files (.laz or .las)
        output_base_dir: Base directory where output folders will be created
        bin_size: Size of each height bin in meters (default: 2.0)
        vegetation_classes: List of classification codes for vegetation points (default: [3, 4, 5])
        show_cumulative: Whether to show cumulative height distribution (default: True)
        create_rasters: Whether to create raster files for each height bin (default: True)
        raster_resolution: Spatial resolution of output rasters in meters (default: 5.0)
        epsg_code: EPSG code to use for raster output (if None, will attempt to extract from LiDAR file)
        handle_negative_heights: Whether to handle negative height values from normalization (default: True)
        filter_negative_heights: Whether to filter out negative heights for NRD calculation (default: True)
        filter_artifacts: Whether to apply statistical filtering to remove normalization artifacts (default: False)
        filter_method: Method for artifact filtering ('simple', 'statistical', 'local', 'combined')
        z_score_threshold: Z-score threshold for statistical filtering (default: 2.5)
        slope_threshold: Maximum allowed slope in degrees for local context filtering (default: 45.0)
        min_valid_height: Minimum allowed height after filtering (default: -1.0)
        min_points_percent: Minimum percentage of total points required for a bin to be considered valid (default: 0.1%)
    """
    # Find all LiDAR files in the input directory
    laz_files = glob.glob(os.path.join(input_dir, "*.laz"))
    las_files = glob.glob(os.path.join(input_dir, "*.las"))
    lidar_files = laz_files + las_files
    
    if not lidar_files:
        logger.error(f"No LiDAR files (*.laz, *.las) found in {input_dir}")
        return
    
    logger.info(f"Found {len(lidar_files)} LiDAR files to process")
    
    # Create base output directory if it doesn't exist
    os.makedirs(output_base_dir, exist_ok=True)
    
    # Process each file
    start_time = time.time()
    
    for i, file_path in enumerate(lidar_files):
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        logger.info(f"Processing file {i+1}/{len(lidar_files)}: {file_name}")
        
        # Create a dedicated output directory for this file
        file_output_dir = os.path.join(output_base_dir, file_name)
        os.makedirs(file_output_dir, exist_ok=True)
        
        try:
            # Process the individual file
            process_lidar_file(
                file_path=file_path,
                output_dir=file_output_dir,
                bin_size=bin_size,
                vegetation_classes=vegetation_classes,
                show_cumulative=show_cumulative,
                create_rasters=create_rasters,
                raster_resolution=raster_resolution,
                epsg_code=epsg_code,
                handle_negative_heights=handle_negative_heights,
                filter_negative_heights=filter_negative_heights,
                filter_artifacts=filter_artifacts,
                filter_method=filter_method,
                z_score_threshold=z_score_threshold,
                slope_threshold=slope_threshold,
                min_valid_height=min_valid_height,
                min_points_percent=min_points_percent
            )
            logger.info(f"Successfully processed {file_name}")
        except Exception as e:
            logger.error(f"Error processing {file_name}: {str(e)}")
            logger.error(f"Moving on to next file")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Calculate and display processing time
    elapsed_time = time.time() - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    logger.info(f"All files processed. Total processing time: {int(hours):02}:{int(minutes):02}:{seconds:.2f}")

def explain_nrd_calculation():
    """
    Prints an explanation of the Normalized Return Density (NRD) calculation method
    used in this script. This is helpful for users to understand the methodology.
    """
    explanation = """
    NORMALIZED RETURN DENSITY (NRD) CALCULATION
    ===========================================
    
    NRD represents the proportion of LiDAR returns at a given height relative to 
    all returns at that height and BELOW it.
    
    Formula: NRD = (points in current bin) / (points in current bin and all bins BELOW it)
    
    For example, if we have height bins:
    - 0-2m: 100 points
    - 2-4m: 50 points
    - 4-6m: 25 points
    
    The NRD values would be:
    - 0-2m: 100/100 = 1.0 (100% of points from 0-2m are in the 0-2m bin)
    - 2-4m: 50/(50+100) = 0.33 (33% of points from 0-4m are in the 2-4m bin)
    - 4-6m: 25/(25+50+100) = 0.14 (14% of points from 0-6m are in the 4-6m bin)
    
    This method provides a vertical profile of vegetation structure from the ground up,
    indicating what proportion of all vegetation (from ground to a given height) 
    exists in each vertical stratum.
    """
    print(explanation)
    return explanation

# =============================================================================
# USER CONFIGURATION SECTION
# =============================================================================
# This section defines parameters that can be customized by users at runtime.
# These parameters control the behavior of the NRD calculation algorithm.
# =============================================================================

def get_user_config():
    """
    Returns a dictionary of user configuration parameters.
    
    Edit these values to customize the NRD calculation process based on your data
    and analysis requirements.
    
    Returns:
        Dictionary of user configuration parameters
    """
    return {
        # DATA INPUT/OUTPUT
        # -----------------
        'input_directory': DEFAULT_INPUT_DIR,  # Directory with LiDAR files
        'output_directory': DEFAULT_OUTPUT_DIR,  # Directory to save results
        
        # POINT CLOUD PROCESSING
        # ----------------------
        'vegetation_classes': DEFAULT_VEGETATION_CLASSES,  # LiDAR classification codes to use
        'bin_size': DEFAULT_BIN_SIZE,  # Vertical interval for height bins in meters
        'raster_resolution': DEFAULT_RASTER_RESOLUTION,  # Horizontal resolution of output rasters in meters
        
        # HEIGHT ARTIFACT FILTERING
        # -------------------------
        'handle_negative_heights': DEFAULT_HANDLE_NEGATIVE_HEIGHTS,  # Whether to handle negative height values
        'filter_negative_heights': DEFAULT_FILTER_NEGATIVE_HEIGHTS,  # Whether to filter out negative heights
        'filter_artifacts': DEFAULT_FILTER_ARTIFACTS,  # Whether to apply statistical filtering
        'filter_method': DEFAULT_FILTER_METHOD,  # Filtering method
        'z_score_threshold': DEFAULT_Z_SCORE_THRESHOLD,  # Z-score threshold for statistical filtering
        'slope_threshold': DEFAULT_SLOPE_THRESHOLD,  # Maximum allowed slope in degrees
        'min_valid_height': DEFAULT_MIN_VALID_HEIGHT,  # Minimum allowed height after filtering
        
        # QUALITY CONTROL
        # ---------------
        'min_points_percent': DEFAULT_MIN_POINTS_PERCENT,  # Minimum percentage for bin validity
        
        # OUTPUT OPTIONS
        # --------------
        'create_rasters': DEFAULT_CREATE_RASTERS,  # Whether to create raster files
        'show_cumulative': DEFAULT_SHOW_CUMULATIVE,  # Whether to show cumulative distribution
        
        # PERFORMANCE SETTINGS
        # -------------------
        'parallel_processing': DEFAULT_PARALLEL_PROCESSING,  # Whether to use parallel processing
        'max_workers': DEFAULT_MAX_WORKERS,  # Maximum number of worker processes
    }

# If this file is run directly (not imported), execute the main function
if __name__ == "__main__":
    # Get user configuration
    USER_CONFIG = get_user_config()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Calculate Normalized Return Density (NRD) from LiDAR data')
    
    # Input/output options
    parser.add_argument('--input', type=str, default=None,
                        help='Path to input LiDAR file (.laz/.las)')
    parser.add_argument('--output', type=str, default=None,
                        help='Path to output directory')
    parser.add_argument('--input_dir', type=str, default=USER_CONFIG['input_directory'],
                        help='Path to directory containing LiDAR files')
    parser.add_argument('--output_dir', type=str, default=USER_CONFIG['output_directory'],
                        help='Path to base output directory')
    
    # Processing parameters (load defaults from USER_CONFIG)
    parser.add_argument('--bin_size', type=float, default=USER_CONFIG['bin_size'],
                        help=f'Height bin size in meters (default: {USER_CONFIG["bin_size"]})')
    parser.add_argument('--raster_resolution', type=float, default=USER_CONFIG['raster_resolution'],
                        help=f'Output raster resolution in meters (default: {USER_CONFIG["raster_resolution"]})')
    parser.add_argument('--min_points_percent', type=float, default=USER_CONFIG['min_points_percent'],
                        help=f'Minimum percent of total points for bin validity (default: {USER_CONFIG["min_points_percent"]})')
    
    # Filtering options
    parser.add_argument('--filter_artifacts', action='store_true', default=USER_CONFIG['filter_artifacts'],
                        help='Apply artifact filtering to remove normalization errors')
    parser.add_argument('--filter_method', type=str, default=USER_CONFIG['filter_method'],
                        choices=['simple', 'statistical', 'local', 'combined'],
                        help=f'Artifact filtering method (default: {USER_CONFIG["filter_method"]})')
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Process single file or directory based on arguments
    if args.input is not None:
        # Process a single file
        if not os.path.exists(args.input):
            logger.error(f"Input file not found: {args.input}")
            sys.exit(1)
            
        output_dir = args.output if args.output is not None else args.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Processing single file: {args.input}")
        logger.info(f"Output directory: {output_dir}")
        
        # Call the processing function with arguments and USER_CONFIG values
        process_lidar_file(
            args.input, 
            output_dir,
            bin_size=args.bin_size,
            vegetation_classes=USER_CONFIG['vegetation_classes'],
            show_cumulative=USER_CONFIG['show_cumulative'],
            create_rasters=USER_CONFIG['create_rasters'],
            raster_resolution=args.raster_resolution,
            epsg_code=None,  # Will attempt to extract from file
            handle_negative_heights=True,
            filter_negative_heights=USER_CONFIG['filter_negative_heights'],
            filter_artifacts=args.filter_artifacts,
            filter_method=args.filter_method,
            z_score_threshold=USER_CONFIG['z_score_threshold'],
            slope_threshold=USER_CONFIG['slope_threshold'],
            min_valid_height=USER_CONFIG['min_valid_height'],
            min_points_percent=args.min_points_percent
        )
        
    else:
        # Process all files in a directory
        if not os.path.exists(args.input_dir):
            logger.error(f"Input directory not found: {args.input_dir}")
                sys.exit(1)
                
        logger.info(f"Processing all LiDAR files in: {args.input_dir}")
        logger.info(f"Output base directory: {args.output_dir}")
        
        # Process the directory using USER_CONFIG values
            process_directory(
            args.input_dir, 
            args.output_dir,
            bin_size=args.bin_size,
            vegetation_classes=USER_CONFIG['vegetation_classes'],
            show_cumulative=USER_CONFIG['show_cumulative'],
            create_rasters=USER_CONFIG['create_rasters'],
            raster_resolution=args.raster_resolution,
            epsg_code=None,  # Will attempt to extract from file
            handle_negative_heights=True,
            filter_negative_heights=USER_CONFIG['filter_negative_heights'],
            filter_artifacts=args.filter_artifacts,
            filter_method=args.filter_method,
            z_score_threshold=USER_CONFIG['z_score_threshold'],
            slope_threshold=USER_CONFIG['slope_threshold'],
            min_valid_height=USER_CONFIG['min_valid_height'],
            min_points_percent=args.min_points_percent
            )
    