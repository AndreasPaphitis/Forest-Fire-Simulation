"""
Memory Management Utilities for LiDAR Preprocessing

This module provides utilities for managing memory during LiDAR preprocessing operations.
It includes functions for estimating memory requirements, efficient array handling, and
chunked processing strategies.
"""

import os
import sys
import numpy as np
import psutil
import gc
import logging
import functools
import math
from typing import Dict, List, Tuple, Any, Optional, Union, Callable
import tempfile
import time

# Add parent directory to sys.path to enable relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import project utilities if available
try:
    from src.utils.logging_utils import get_logger
    from src.utils.memory_manager import estimate_memory_usage, get_available_memory
    logger = get_logger(__name__)
    UTILS_AVAILABLE = True
except ImportError:
    # Create fallback logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    UTILS_AVAILABLE = False
    
    # Simple fallback functions
    def estimate_memory_usage(shape, dtype=np.float32, num_arrays=1):
        """Estimate memory usage for numpy arrays"""
        try:
            element_size = np.dtype(dtype).itemsize
            return shape[0] * shape[1] * element_size * num_arrays
        except (TypeError, IndexError):
            try:
                # Handle 1D arrays
                return shape * element_size * num_arrays
            except TypeError:
                # Handle scalar shapes
                return element_size * num_arrays
    
    def get_available_memory():
        """Get available system memory in bytes"""
        return psutil.virtual_memory().available

# ========================================================================
# MEMORY MONITORING
# ========================================================================

def monitor_memory(label: str = "Memory Usage"):
    """
    Decorator to monitor memory usage before and after a function call.
    
    Args:
        label: Label for logging memory usage
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get memory usage before function call
            gc.collect()  # Force garbage collection
            mem_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
            
            # Call the function
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            # Get memory usage after function call
            gc.collect()  # Force garbage collection
            mem_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
            
            # Log memory usage and timing
            logger.info(f"{label}: {mem_before:.2f} MB → {mem_after:.2f} MB (Δ {mem_after - mem_before:.2f} MB, {elapsed_time:.2f}s)")
            
            return result
        return wrapper
    return decorator

# ========================================================================
# MEMORY ESTIMATION
# ========================================================================

def estimate_point_cloud_memory(num_points: int, num_attributes: int = 4, dtype=np.float32) -> float:
    """
    Estimate memory required for a point cloud.
    
    Args:
        num_points: Number of points in the cloud
        num_attributes: Number of attributes per point (x, y, z, etc.)
        dtype: Data type for the attributes
        
    Returns:
        Estimated memory usage in bytes
    """
    return num_points * num_attributes * np.dtype(dtype).itemsize

def estimate_grid_memory(width: int, height: int, num_layers: int = 1, dtype=np.float32) -> float:
    """
    Estimate memory required for a grid.
    
    Args:
        width: Width of the grid
        height: Height of the grid
        num_layers: Number of layers in the grid
        dtype: Data type for the grid cells
        
    Returns:
        Estimated memory usage in bytes
    """
    return width * height * num_layers * np.dtype(dtype).itemsize

def estimate_raster_operations_memory(raster_width: int, raster_height: int,
                                     num_layers: int, dtype=np.float32) -> Dict[str, float]:
    """
    Estimate memory requirements for various raster operations.
    
    Args:
        raster_width: Width of the raster in pixels
        raster_height: Height of the raster in pixels
        num_layers: Number of vertical layers
        dtype: Data type for the raster cells
        
    Returns:
        Dictionary of operation names and their memory requirements in bytes
    """
    cell_size = np.dtype(dtype).itemsize
    size_2d = raster_width * raster_height * cell_size
    size_3d = raster_width * raster_height * num_layers * cell_size
    
    return {
        "load_single_layer": size_2d,
        "load_all_layers": size_3d,
        "interpolation_temp": size_2d * 3,  # Original, intermediate, and result
        "filtering_temp": size_2d * 2,  # Original and filtered
        "nrd_calculation": size_3d * 2,  # Original and NRD values
        "pad_calculation": size_3d * 3,  # NRD, intermediate, and PAD values
    }

def check_memory_requirements(required_memory: Union[float, Dict[str, float]], 
                            available_memory: Optional[float] = None,
                            threshold_ratio: float = 0.8) -> Tuple[bool, float]:
    """
    Check if there's enough memory available for an operation.
    
    Args:
        required_memory: Required memory in bytes or dict of requirements
        available_memory: Available memory in bytes (defaults to system available memory)
        threshold_ratio: Maximum ratio of available memory to use
        
    Returns:
        Tuple of (has_enough_memory, available_memory)
    """
    if available_memory is None:
        available_memory = get_available_memory()
    
    max_usable_memory = available_memory * threshold_ratio
    
    if isinstance(required_memory, dict):
        max_required = max(required_memory.values())
        enough_memory = max_required <= max_usable_memory
    else:
        enough_memory = required_memory <= max_usable_memory
    
    return enough_memory, available_memory

# ========================================================================
# MEMORY-EFFICIENT PROCESSING
# ========================================================================

class MemoryEfficientChunkProcessor:
    """
    Process data in memory-efficient chunks.
    """
    
    def __init__(self, max_chunk_memory_mb: float = 1024):
        """
        Initialize the chunk processor.
        
        Args:
            max_chunk_memory_mb: Maximum memory per chunk in MB
        """
        self.max_chunk_memory_bytes = max_chunk_memory_mb * 1024 * 1024
    
    def calculate_chunk_size(self, width: int, height: int, 
                            bytes_per_pixel: int,
                            num_temp_arrays: int = 2) -> Tuple[int, int]:
        """
        Calculate optimal chunk size for processing.
        
        Args:
            width: Full width of the data
            height: Full height of the data
            bytes_per_pixel: Bytes per pixel (e.g. 4 for float32)
            num_temp_arrays: Number of temporary arrays needed for processing
            
        Returns:
            Tuple of (chunk_width, chunk_height)
        """
        total_pixels = width * height
        memory_per_pixel = bytes_per_pixel * num_temp_arrays
        max_pixels_per_chunk = self.max_chunk_memory_bytes / memory_per_pixel
        
        # If entire dataset fits in memory, use it all
        if total_pixels <= max_pixels_per_chunk:
            return width, height
        
        # Calculate chunk size maintaining aspect ratio
        aspect_ratio = width / height
        chunk_height = int(math.sqrt(max_pixels_per_chunk / aspect_ratio))
        chunk_width = int(chunk_height * aspect_ratio)
        
        # Ensure chunk size is at least 1
        chunk_width = max(1, chunk_width)
        chunk_height = max(1, chunk_height)
        
        # Ensure chunk size is not larger than the data
        chunk_width = min(chunk_width, width)
        chunk_height = min(chunk_height, height)
        
        return chunk_width, chunk_height
    
    def create_chunks(self, width: int, height: int,
                     bytes_per_pixel: int,
                     num_temp_arrays: int = 2) -> List[Tuple[int, int, int, int]]:
        """
        Create chunks for processing a large dataset.
        
        Args:
            width: Full width of the data
            height: Full height of the data
            bytes_per_pixel: Bytes per pixel
            num_temp_arrays: Number of temporary arrays needed for processing
            
        Returns:
            List of (start_x, start_y, chunk_width, chunk_height) tuples
        """
        chunk_width, chunk_height = self.calculate_chunk_size(
            width, height, bytes_per_pixel, num_temp_arrays
        )
        
        chunks = []
        for y in range(0, height, chunk_height):
            for x in range(0, width, chunk_width):
                # Handle edge cases where chunk goes beyond data boundaries
                actual_chunk_width = min(chunk_width, width - x)
                actual_chunk_height = min(chunk_height, height - y)
                chunks.append((x, y, actual_chunk_width, actual_chunk_height))
        
        return chunks
    
    @monitor_memory("Chunk processing")
    def process_in_chunks(self, data: Optional[np.ndarray],
                        process_func: Callable,
                        width: Optional[int] = None,
                        height: Optional[int] = None,
                        dtype=np.float32,
                        extra_args: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """
        Process data in chunks to minimize memory usage.
        
        Args:
            data: Input data array (or None if reading from disk)
            process_func: Function to process each chunk, should take 
                         (chunk_data, start_x, start_y, **extra_args)
            width: Width of the data (required if data is None)
            height: Height of the data (required if data is None)
            dtype: Data type of the result
            extra_args: Additional arguments for the processing function
            
        Returns:
            Processed data array
        """
        if data is not None:
            height, width = data.shape[:2]
        else:
            assert width is not None and height is not None, "Width and height required when data is None"
        
        # Calculate bytes per pixel
        bytes_per_pixel = np.dtype(dtype).itemsize
        if data is not None and len(data.shape) > 2:
            bytes_per_pixel *= data.shape[2]  # Multiple channels
        
        # Create output array (if processing in place, use temporary file)
        use_temp_file = (width * height * bytes_per_pixel > self.max_chunk_memory_bytes)
        
        if use_temp_file:
            # Use memory-mapped array for output
            logger.info("Using memory-mapped array for large output")
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.close()
            
            # Create memory-mapped output array
            shape = (height, width) if len(data.shape) == 2 else (height, width, data.shape[2])
            result = np.memmap(temp_file.name, dtype=dtype, mode='w+', shape=shape)
        else:
            # Use regular numpy array for output
            shape = (height, width) if data is None or len(data.shape) == 2 else (height, width, data.shape[2])
            result = np.zeros(shape, dtype=dtype)
        
        # Process data in chunks
        chunks = self.create_chunks(width, height, bytes_per_pixel, 3)  # Assume 3 arrays (input, temp, output)
        logger.info(f"Processing data in {len(chunks)} chunks")
        
        for i, (start_x, start_y, chunk_width, chunk_height) in enumerate(chunks):
            logger.debug(f"Processing chunk {i+1}/{len(chunks)}: ({start_x}, {start_y}, {chunk_width}, {chunk_height})")
            
            # Extract chunk data
            if data is not None:
                if len(data.shape) == 2:
                    chunk_data = data[start_y:start_y+chunk_height, start_x:start_x+chunk_width]
                else:
                    chunk_data = data[start_y:start_y+chunk_height, start_x:start_x+chunk_width, :]
            else:
                chunk_data = None
            
            # Process chunk
            args = extra_args or {}
            processed_chunk = process_func(chunk_data, start_x, start_y, **args)
            
            # Store processed chunk
            if len(result.shape) == 2:
                result[start_y:start_y+chunk_height, start_x:start_x+chunk_width] = processed_chunk
            else:
                result[start_y:start_y+chunk_height, start_x:start_x+chunk_width, :] = processed_chunk
            
            # Force garbage collection after each chunk
            gc.collect()
        
        # If we used a memory-mapped file, we need to clean up
        if use_temp_file:
            # Create a copy of the data in memory
            result_copy = np.array(result)
            
            # Close and delete the memory-mapped file
            if hasattr(result, '_mmap') and result._mmap is not None:
                result._mmap.close()
            del result
            os.unlink(temp_file.name)
            
            # Return the in-memory copy
            return result_copy
        else:
            return result

# ========================================================================
# MEMORY-EFFICIENT IO
# ========================================================================

def memory_efficient_raster_read(raster_file: str, 
                               chunk_size_mb: float = 256.0) -> np.ndarray:
    """
    Read a raster in a memory-efficient way using chunking.
    
    Args:
        raster_file: Path to the raster file
        chunk_size_mb: Maximum size of each chunk in MB
        
    Returns:
        The complete raster data as a numpy array
    """
    try:
        import gdal
        from osgeo import gdal as osgeo_gdal
        GDAL_AVAILABLE = True
    except ImportError:
        logger.error("GDAL not available - cannot read raster file")
        return None
    
    # Open the raster file
    ds = gdal.Open(raster_file)
    if ds is None:
        logger.error(f"Could not open raster file: {raster_file}")
        return None
    
    # Get raster dimensions and data type
    width = ds.RasterXSize
    height = ds.RasterYSize
    bands = ds.RasterCount
    
    # Get data type and determine bytes per pixel
    band = ds.GetRasterBand(1)
    dtype = gdal.GetDataTypeByName(gdal.GetDataTypeName(band.DataType))
    bytes_per_pixel = gdal.GetDataTypeSize(dtype) // 8 * bands
    
    # Calculate chunk size
    chunk_processor = MemoryEfficientChunkProcessor(max_chunk_memory_mb=chunk_size_mb)
    chunks = chunk_processor.create_chunks(width, height, bytes_per_pixel)
    
    # Create output array
    gdal_to_numpy_type = {
        gdal.GDT_Byte: np.uint8,
        gdal.GDT_UInt16: np.uint16,
        gdal.GDT_Int16: np.int16,
        gdal.GDT_UInt32: np.uint32,
        gdal.GDT_Int32: np.int32,
        gdal.GDT_Float32: np.float32,
        gdal.GDT_Float64: np.float64
    }
    numpy_dtype = gdal_to_numpy_type.get(dtype, np.float32)
    
    # Create output array
    if bands == 1:
        output = np.zeros((height, width), dtype=numpy_dtype)
    else:
        output = np.zeros((height, width, bands), dtype=numpy_dtype)
    
    # Read data in chunks
    logger.info(f"Reading raster {os.path.basename(raster_file)} in {len(chunks)} chunks")
    for i, (start_x, start_y, chunk_width, chunk_height) in enumerate(chunks):
        logger.debug(f"Reading chunk {i+1}/{len(chunks)}")
        
        # Read chunk
        if bands == 1:
            chunk_data = band.ReadAsArray(start_x, start_y, chunk_width, chunk_height)
            output[start_y:start_y+chunk_height, start_x:start_x+chunk_width] = chunk_data
        else:
            for b in range(bands):
                band = ds.GetRasterBand(b+1)
                chunk_data = band.ReadAsArray(start_x, start_y, chunk_width, chunk_height)
                output[start_y:start_y+chunk_height, start_x:start_x+chunk_width, b] = chunk_data
    
    # Close dataset
    ds = None
    
    return output

def memory_efficient_raster_write(data: np.ndarray, output_file: str,
                                geotransform: Optional[Tuple] = None,
                                projection: Optional[str] = None,
                                no_data_value: Optional[float] = None,
                                chunk_size_mb: float = 256.0) -> bool:
    """
    Write a raster in a memory-efficient way using chunking.
    
    Args:
        data: Data to write (2D or 3D array)
        output_file: Path to the output file
        geotransform: GDAL geotransform (6-tuple)
        projection: GDAL projection (WKT string)
        no_data_value: NoData value for the raster
        chunk_size_mb: Maximum size of each chunk in MB
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import gdal
        from osgeo import gdal as osgeo_gdal
        GDAL_AVAILABLE = True
    except ImportError:
        logger.error("GDAL not available - cannot write raster file")
        return False
    
    # Get data dimensions and type
    if len(data.shape) == 2:
        height, width = data.shape
        bands = 1
    elif len(data.shape) == 3:
        height, width, bands = data.shape
    else:
        logger.error(f"Unsupported data shape: {data.shape}")
        return False
    
    # Map numpy dtype to GDAL dtype
    numpy_to_gdal_type = {
        np.uint8: gdal.GDT_Byte,
        np.uint16: gdal.GDT_UInt16,
        np.int16: gdal.GDT_Int16,
        np.uint32: gdal.GDT_UInt32,
        np.int32: gdal.GDT_Int32,
        np.float32: gdal.GDT_Float32,
        np.float64: gdal.GDT_Float64
    }
    gdal_dtype = numpy_to_gdal_type.get(data.dtype.type, gdal.GDT_Float32)
    
    # Calculate bytes per pixel
    bytes_per_pixel = gdal.GetDataTypeSize(gdal_dtype) // 8 * bands
    
    # Create output file
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(
        output_file,
        width,
        height,
        bands,
        gdal_dtype,
        options=['COMPRESS=DEFLATE', 'TILED=YES', 'BIGTIFF=IF_SAFER']
    )
    
    if ds is None:
        logger.error(f"Could not create output file: {output_file}")
        return False
    
    # Set geotransform and projection if provided
    if geotransform is not None:
        ds.SetGeoTransform(geotransform)
    if projection is not None:
        ds.SetProjection(projection)
    
    # Calculate chunk size
    chunk_processor = MemoryEfficientChunkProcessor(max_chunk_memory_mb=chunk_size_mb)
    chunks = chunk_processor.create_chunks(width, height, bytes_per_pixel)
    
    # Write data in chunks
    logger.info(f"Writing raster {os.path.basename(output_file)} in {len(chunks)} chunks")
    for i, (start_x, start_y, chunk_width, chunk_height) in enumerate(chunks):
        logger.debug(f"Writing chunk {i+1}/{len(chunks)}")
        
        # Write chunk
        if bands == 1:
            band = ds.GetRasterBand(1)
            if no_data_value is not None:
                band.SetNoDataValue(no_data_value)
            chunk_data = data[start_y:start_y+chunk_height, start_x:start_x+chunk_width]
            band.WriteArray(chunk_data, start_x, start_y)
        else:
            for b in range(bands):
                band = ds.GetRasterBand(b+1)
                if no_data_value is not None:
                    band.SetNoDataValue(no_data_value)
                chunk_data = data[start_y:start_y+chunk_height, start_x:start_x+chunk_width, b]
                band.WriteArray(chunk_data, start_x, start_y)
    
    # Compute statistics
    if bands == 1:
        band = ds.GetRasterBand(1)
        band.ComputeStatistics(False)
    else:
        for b in range(bands):
            band = ds.GetRasterBand(b+1)
            band.ComputeStatistics(False)
    
    # Close dataset
    ds = None
    
    return True

# Example usage
if __name__ == "__main__":
    # Example: Check memory requirements for a grid
    grid_width = 10000
    grid_height = 10000
    num_layers = 10
    
    memory_required = estimate_grid_memory(grid_width, grid_height, num_layers)
    has_enough, available = check_memory_requirements(memory_required)
    
    print(f"Grid memory required: {memory_required / 1024 / 1024:.2f} MB")
    print(f"Memory available: {available / 1024 / 1024:.2f} MB")
    print(f"Has enough memory: {has_enough}")
    
    # Example: Process a large array in chunks
    chunk_processor = MemoryEfficientChunkProcessor(max_chunk_memory_mb=100)
    
    # Example processing function
    def example_process(chunk, start_x, start_y, factor=2.0):
        """Example processing function that multiplies values by a factor"""
        if chunk is None:
            # Generate data on the fly (when reading from disk)
            return np.ones((end_y - start_y, end_x - start_x)) * factor
        else:
            return chunk * factor
    
    # Create a test array
    test_array = np.ones((5000, 5000), dtype=np.float32)
    
    # Process in chunks
    result = chunk_processor.process_in_chunks(
        test_array, example_process, extra_args={"factor": 3.0}
    )
    
    print(f"Result shape: {result.shape}")
    print(f"Result mean: {result.mean()}")  # Should be 3.0 