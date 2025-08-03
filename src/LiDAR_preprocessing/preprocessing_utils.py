"""
Common utility functions for LiDAR preprocessing

This module contains shared functions and utilities used across the LiDAR preprocessing pipeline.
It helps eliminate code duplication between the height normalization, NRD calculation,
and PAD calculation modules.
"""

import os
import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union, Any
import logging
import json
import time
from datetime import datetime
import traceback
import functools
import glob

# Add parent directory to sys.path to enable relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import project utilities if available
try:
    from src.utils.logging_utils import get_logger
    from src.utils.error_handling import handle_errors, log_errors, DataProcessingError, FileIOError
    logger = get_logger(__name__)
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    # Create fallback logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    ERROR_HANDLING_AVAILABLE = False
    
    # Fallback error handling decorator
    def handle_errors(func=None, **kwargs):
        if func is None:
            return lambda f: handle_errors(f, **kwargs)
        @functools.wraps(func)
        def wrapper(*args, **kw_args):
            try:
                return func(*args, **kw_args)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                logger.debug(traceback.format_exc())
                if kwargs.get('reraise', False):
                    raise
                return kwargs.get('default_return', None)
        return wrapper
    
    log_errors = handle_errors  # Simple alias
    class DataProcessingError(Exception): pass
    class FileIOError(Exception): pass

# Try to import GDAL
try:
    from osgeo import gdal, osr
    GDAL_AVAILABLE = True
    
    # Configure GDAL
    gdal.UseExceptions()
    gdal.PushErrorHandler('CPLQuietErrorHandler')
except ImportError:
    GDAL_AVAILABLE = False
    logger.warning("GDAL not available - some functionality will be limited")

# =========================================================================
# SHARED UTILITY FUNCTIONS
# =========================================================================

@handle_errors(error_type=FileIOError)
def ensure_directory_exists(directory_path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        Path object for the directory
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path

@handle_errors(error_type=DataProcessingError)
def filter_height_artifacts(x_coords: np.ndarray, y_coords: np.ndarray, heights: np.ndarray, 
                       filter_method: str = 'statistical', 
                       slope_threshold: float = 45.0,
                       z_score_threshold: float = 2.5,
                       min_valid_height: float = -1.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Filter height artifacts in LiDAR point cloud data.
    
    Args:
        x_coords: X coordinates of points
        y_coords: Y coordinates of points
        heights: Heights of points
        filter_method: Method for artifact filtering ('simple', 'statistical', 'local', 'combined')
        slope_threshold: Maximum allowed slope in degrees for local context filtering
        z_score_threshold: Z-score threshold for statistical filtering
        min_valid_height: Minimum allowed height after filtering
        
    Returns:
        Tuple of filtered (x_coords, y_coords, heights)
    """
    if filter_method == 'simple':
        # Simple filtering removes all negative heights
        valid_idx = heights >= min_valid_height
        return x_coords[valid_idx], y_coords[valid_idx], heights[valid_idx]
    
    elif filter_method == 'statistical':
        # Statistical filtering removes outliers based on z-scores
        mean_height = np.mean(heights)
        std_height = np.std(heights)
        
        if std_height == 0:  # Avoid division by zero
            valid_idx = heights >= min_valid_height
        else:
            z_scores = np.abs((heights - mean_height) / std_height)
            valid_idx = (z_scores < z_score_threshold) & (heights >= min_valid_height)
            
        return x_coords[valid_idx], y_coords[valid_idx], heights[valid_idx]
    
    elif filter_method == 'local' or filter_method == 'combined':
        # Local filtering checks neighborhood points for drastic changes
        # This is a simplified implementation - a real one would need spatial indexing
        # or more sophisticated methods to identify neighboring points
        logger.warning("Complex local filtering not fully implemented - using simple filter")
        valid_idx = heights >= min_valid_height
        return x_coords[valid_idx], y_coords[valid_idx], heights[valid_idx]
    
    else:
        logger.warning(f"Unknown filter method '{filter_method}' - no filtering applied")
        return x_coords, y_coords, heights

def create_metadata_record(processed_file: str, 
                          parameters: Dict[str, Any], 
                          stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a standardized metadata record for processed files.
    
    Args:
        processed_file: Name of the processed file
        parameters: Processing parameters used
        stats: Optional statistics about the processing
        
    Returns:
        Metadata dictionary
    """
    metadata = {
        "file_name": os.path.basename(processed_file),
        "processing_date": datetime.now().isoformat(),
        "parameters": parameters,
    }
    
    if stats:
        metadata["statistics"] = stats
        
    return metadata

def save_metadata(metadata: Dict[str, Any], output_file: Union[str, Path]) -> None:
    """
    Save metadata to a JSON file.
    
    Args:
        metadata: Metadata dictionary
        output_file: Path to save the metadata
    """
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=4)

class ProgressTracker:
    """
    Track progress of long-running operations with consistent reporting.
    """
    
    def __init__(self, total_items: int, description: str = "Processing", 
                 log_interval: int = 10, log_function=None):
        """
        Initialize the progress tracker.
        
        Args:
            total_items: Total number of items to process
            description: Description of the operation
            log_interval: How often to log progress (percentage)
            log_function: Function to use for logging (defaults to logger.info)
        """
        self.total = total_items
        self.description = description
        self.completed = 0
        self.start_time = time.time()
        self.last_log_percent = 0
        self.log_interval = log_interval
        self.log_function = log_function or logger.info
        
        # Initial log
        self.log_function(f"Starting {description} of {total_items} items...")
    
    def update(self, increment: int = 1, item_description: str = "") -> None:
        """
        Update progress.
        
        Args:
            increment: Number of items completed in this update
            item_description: Optional description of current item
        """
        self.completed += increment
        
        # Calculate progress
        if self.total <= 0:
            percent_complete = 100
        else:
            percent_complete = int((self.completed / self.total) * 100)
        
        # Log if we've passed an interval or completed
        if (percent_complete >= 100 or
            percent_complete - self.last_log_percent >= self.log_interval):
            
            elapsed = time.time() - self.start_time
            
            if self.completed >= self.total:
                self.log_function(f"{self.description} complete! Processed {self.completed} items in {elapsed:.2f} seconds")
            else:
                if item_description:
                    self.log_function(f"{self.description}: {percent_complete}% complete ({self.completed}/{self.total}) - Current: {item_description}")
                else:
                    self.log_function(f"{self.description}: {percent_complete}% complete ({self.completed}/{self.total})")
                    
            self.last_log_percent = percent_complete
    
    def complete(self) -> Dict[str, Any]:
        """
        Mark the operation as complete and return statistics.
        
        Returns:
            Dictionary of statistics about the operation
        """
        elapsed = time.time() - self.start_time
        self.log_function(f"{self.description} complete! Processed {self.completed} items in {elapsed:.2f} seconds")
        
        return {
            "total_items": self.total,
            "completed_items": self.completed,
            "elapsed_seconds": elapsed,
            "items_per_second": self.completed / elapsed if elapsed > 0 else 0
        } 