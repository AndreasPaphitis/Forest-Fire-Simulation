#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixed Terrain Preprocessor using Rasterio

This module provides terrain preprocessing functionality using rasterio with fixes for large datasets.
It implements the same algorithms as the GDAL-based version but with better Windows compatibility
and improved memory management for large datasets.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.1 - Fixed for large datasets
"""

import os
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import json
import pickle
import time
import gc

try:
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

try:
    from src.utils.logging_utils import get_logger
    from src.utils.error_handling import handle_terrain_error
except ImportError:
    try:
        from utils.logging_utils import get_logger
        from utils.error_handling import handle_terrain_error
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        def handle_terrain_error(error, context=""):
            logger.error(f"Terrain error {context}: {error}")
            return False

logger = get_logger(__name__)


@dataclass
class TerrainPreprocessingConfig:
    """Configuration for terrain preprocessing."""
    
    # Input/Output paths
    dem_file: str
    output_dir: str
    
    # Processing parameters (literature-based for volcanic terrain)
    barranco_threshold: float = 25.0  # Slope threshold for barranco detection (Menéndez et al., 2008)
    min_depression_depth: float = 3.0  # Minimum depression depth (Florinsky, 2016)
    min_depression_area: int = 6  # Minimum depression area in cells (Li et al., 2024)
    smoothing_kernel_size: int = 3  # Wind field smoothing kernel
    wind_channeling_strength: float = 0.8  # Terrain effect strength (Schmidli & Rotunno, 2012)
    barranco_amplification: float = 2.5  # Wind amplification in barrancos (Chock & Cochran, 2005)
    
    # Geographic bounds (optional - will use full DEM if not specified)
    geo_bounds: Optional[Tuple[float, float, float, float]] = None
    crs: str = "EPSG:25828"  # Default CRS for Tenerife
    
    # Processing options
    compute_slope_aspect: bool = True
    detect_barrancos: bool = True
    compute_wind_channeling: bool = True
    smooth_wind_fields: bool = False  # Disabled by default for large datasets
    
    # Output options
    save_intermediate: bool = False
    compression: bool = True
    format: str = "numpy"  # numpy, geotiff, or pickle
    
    # Memory management options
    chunk_size: int = 1000  # Process data in chunks for large datasets
    memory_limit_gb: float = 8.0  # Memory limit for processing
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not os.path.exists(self.dem_file):
            raise FileNotFoundError(f"DEM file not found: {self.dem_file}")
        
        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)


@dataclass
class PreprocessedTerrainData:
    """Container for preprocessed terrain data."""
    
    # Basic terrain data
    elevation: np.ndarray
    slope: np.ndarray
    aspect: np.ndarray
    
    # Barranco detection results
    barranco_mask: np.ndarray
    barranco_directions: np.ndarray
    depression_mask: np.ndarray
    
    # Wind channeling data
    wind_channeling_mask: np.ndarray
    wind_amplification: np.ndarray
    wind_direction_modification: np.ndarray
    
    # Metadata
    metadata: Dict[str, Any]
    
    # File paths for saved data
    file_paths: Dict[str, str] = None
    
    def __post_init__(self):
        """Initialize file paths if not provided."""
        if self.file_paths is None:
            self.file_paths = {}


class TerrainPreprocessorRasterioFixed:
    """
    Fixed terrain preprocessor using rasterio with improved memory management.
    """
    
    def __init__(self, config: TerrainPreprocessingConfig):
        """
        Initialize terrain preprocessor.
        
        Args:
            config: Terrain preprocessing configuration
        """
        self.config = config
        self.dem_data = None
        self.transform = None
        self.crs = None
        
        logger.info(f"Initialized fixed rasterio terrain preprocessor for {config.dem_file}")
        logger.info(f"Output directory: {config.output_dir}")
        logger.info(f"Memory limit: {config.memory_limit_gb} GB")
    
    def preprocess_terrain(self) -> PreprocessedTerrainData:
        """
        Preprocess terrain data using current ForestModel algorithms with improved memory management.
        
        Returns:
            PreprocessedTerrainData with all computed terrain features
        """
        logger.info("🚀 Starting terrain preprocessing with fixed rasterio...")
        
        try:
            # Step 1: Load DEM data
            self._load_dem_data()
            
            # Step 2: Compute basic terrain features
            elevation, slope, aspect = self._compute_basic_terrain()
            
            # Step 3: Detect barrancos (same algorithm as ForestModel)
            barranco_results = self._detect_barrancos(elevation, slope, aspect)
            
            # Step 4: Compute wind channeling effects
            wind_results = self._compute_wind_channeling(elevation, slope, aspect, barranco_results)
            
            # Step 5: Create metadata
            metadata = self._create_metadata()
            
            # Step 6: Create preprocessed data container
            preprocessed_data = PreprocessedTerrainData(
                elevation=elevation,
                slope=slope,
                aspect=aspect,
                barranco_mask=barranco_results['barranco_mask'],
                barranco_directions=barranco_results['barranco_directions'],
                depression_mask=barranco_results['depression_mask'],
                wind_channeling_mask=wind_results['wind_channeling_mask'],
                wind_amplification=wind_results['wind_amplification'],
                wind_direction_modification=wind_results['wind_direction_modification'],
                metadata=metadata
            )
            
            # Step 7: Save preprocessed data with improved memory management
            self._save_preprocessed_data_optimized(preprocessed_data)
            
            logger.info("✅ Terrain preprocessing completed successfully")
            return preprocessed_data
            
        except Exception as e:
            logger.error(f"❌ Terrain preprocessing failed: {e}")
            raise
    
    def _load_dem_data(self):
        """Load DEM data using rasterio with memory management and geographic subsetting."""
        if not RASTERIO_AVAILABLE:
            raise ImportError("Rasterio is required for terrain preprocessing")
        
        logger.info(f"📁 Loading DEM data from {self.config.dem_file}")
        
        try:
            with rasterio.open(self.config.dem_file) as dataset:
                # Get geospatial information
                self.transform = dataset.transform
                self.crs = dataset.crs
                
                # Check if we need to subset the data
                if self.config.geo_bounds is not None:
                    logger.info(f"🗺️ Subsetting DEM to bounds: {self.config.geo_bounds}")
                    
                    # Convert geographic bounds to pixel coordinates
                    from rasterio.windows import from_bounds
                    min_x, min_y, max_x, max_y = self.config.geo_bounds
                    window = from_bounds(min_x, min_y, max_x, max_y, dataset.transform)
                    
                    # Read the subset
                    self.dem_data = dataset.read(1, window=window)
                    
                    # Update transform for the subset
                    self.transform = rasterio.windows.transform(window, dataset.transform)
                    
                    logger.info(f"📊 DEM subset loaded: {self.dem_data.shape}, dtype: {self.dem_data.dtype}")
                    logger.info(f"📊 Subset bounds: {self.config.geo_bounds}")
                else:
                    logger.info("🌍 Loading entire DEM (no subsetting)")
                    # Read elevation data
                    self.dem_data = dataset.read(1)
                
                # Handle no-data values
                if dataset.nodata is not None:
                    self.dem_data[self.dem_data == dataset.nodata] = np.nan
                
                logger.info(f"📊 Elevation range: {np.nanmin(self.dem_data):.2f} to {np.nanmax(self.dem_data):.2f}")
                
        except Exception as e:
            logger.error(f"Error loading DEM: {e}")
            raise
    
    def _compute_basic_terrain(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute slope and aspect using numpy with memory management."""
        logger.info("🏔️ Computing slope and aspect...")
        
        try:
            from scipy.ndimage import sobel
            
            elevation = self.dem_data.copy()
            
            # Compute slope using Sobel operators
            # Get pixel size from transform
            pixel_size_x = abs(self.transform[0])
            pixel_size_y = abs(self.transform[4])
            
            # Compute gradients using Sobel operators
            grad_x = sobel(elevation, axis=1) / (2 * pixel_size_x)
            grad_y = sobel(elevation, axis=0) / (2 * pixel_size_y)
            
            # Compute slope (magnitude of gradient)
            slope = np.sqrt(grad_x**2 + grad_y**2)
            slope_degrees = np.arctan(slope) * 180 / np.pi
            
            # Compute aspect (direction of gradient)
            aspect = np.arctan2(-grad_y, grad_x) * 180 / np.pi
            aspect = (aspect + 360) % 360  # Convert to 0-360 degrees
            
            # Handle no-data values
            slope_degrees[np.isnan(elevation)] = 0
            aspect[np.isnan(elevation)] = 0
            
            logger.info(f"✅ Slope and aspect computed")
            logger.info(f"📊 Slope range: {np.nanmin(slope_degrees):.2f} to {np.nanmax(slope_degrees):.2f}")
            logger.info(f"📊 Aspect range: {np.nanmin(aspect):.2f} to {np.nanmax(aspect):.2f}")
            
            return elevation, slope_degrees, aspect
                
        except Exception as e:
            logger.error(f"Error computing slope/aspect: {e}")
            raise
    
    def _detect_barrancos(self, elevation: np.ndarray, slope: np.ndarray, aspect: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Detect barrancos using optimized algorithms for large datasets.
        """
        logger.info("🏞️ Detecting barrancos and topographic depressions...")
        
        # Step 1: Detect topographic depressions (optimized)
        logger.info("   Step 1: Detecting topographic depressions...")
        depression_mask = self._detect_topographic_depressions_optimized(elevation)
        logger.info(f"   ✅ Found {np.sum(depression_mask)} depression cells")
        
        # Step 2: Identify steep slopes for barranco detection
        logger.info("   Step 2: Identifying steep slopes...")
        steep_slope_mask = slope >= self.config.barranco_threshold
        logger.info(f"   ✅ Found {np.sum(steep_slope_mask)} steep slope cells")
        
        # Step 3: Combine depressions and steep slopes for barranco detection
        logger.info("   Step 3: Combining depressions and steep slopes...")
        barranco_mask = np.logical_and(depression_mask, steep_slope_mask)
        logger.info(f"   ✅ Initial barranco mask: {np.sum(barranco_mask)} cells")
        
        # Step 4: Calculate barranco directions (optimized)
        logger.info("   Step 4: Calculating barranco directions...")
        barranco_directions = self._calculate_barranco_directions_optimized(elevation, aspect, barranco_mask)
        logger.info("   ✅ Barranco directions calculated")
        
        # Step 5: Apply minimum depth and area filters (optimized)
        if self.config.min_depression_depth > 0:
            logger.info("   Step 5: Applying depth filter...")
            depth_mask = self._calculate_depression_depth_optimized(elevation, depression_mask)
            deep_depressions = depth_mask >= self.config.min_depression_depth
            barranco_mask = np.logical_and(barranco_mask, deep_depressions)
            logger.info(f"   ✅ After depth filter: {np.sum(barranco_mask)} cells")
        
        # Step 6: Apply minimum area filter (optimized)
        if self.config.min_depression_area > 1:
            logger.info("   Step 6: Applying area filter...")
            barranco_mask = self._filter_by_area_optimized(barranco_mask, self.config.min_depression_area)
            logger.info(f"   ✅ After area filter: {np.sum(barranco_mask)} cells")
        
        logger.info(f"🏞️ Final results: {np.sum(barranco_mask)} barranco cells, {np.sum(depression_mask)} depression cells")
        
        return {
            'barranco_mask': barranco_mask,
            'barranco_directions': barranco_directions,
            'depression_mask': depression_mask
        }
    
    def _detect_topographic_depressions_optimized(self, elevation: np.ndarray) -> np.ndarray:
        """Optimized: Detect topographic depressions using vectorized minimum filter."""
        from scipy.ndimage import minimum_filter
        
        logger.info("   Computing local minima...")
        # Use 3x3 neighborhood for local minima
        local_min = minimum_filter(elevation, size=3)
        depression_mask = (elevation <= local_min)
        
        # Remove edge cells
        depression_mask[0, :] = False
        depression_mask[-1, :] = False
        depression_mask[:, 0] = False
        depression_mask[:, -1] = False
        
        return depression_mask

    def _calculate_barranco_directions_optimized(self, elevation: np.ndarray, aspect: np.ndarray, barranco_mask: np.ndarray) -> np.ndarray:
        """Optimized: Calculate flow directions within barrancos (vectorized)."""
        directions = np.zeros_like(aspect)
        directions[barranco_mask] = aspect[barranco_mask]
        
        if np.any(barranco_mask):
            directions = self._smooth_directions_optimized(directions, barranco_mask)
        
        return directions

    def _smooth_directions_optimized(self, directions: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Optimized: Smooth flow directions using uniform filter and circular mean."""
        from scipy.ndimage import uniform_filter
        
        # Convert to radians
        sin_dir = np.sin(np.deg2rad(directions))
        cos_dir = np.cos(np.deg2rad(directions))
        
        # Smooth
        sin_smooth = uniform_filter(sin_dir, size=3)
        cos_smooth = uniform_filter(cos_dir, size=3)
        smoothed = (np.arctan2(sin_smooth, cos_smooth) * 180 / np.pi + 360) % 360
        
        # Only update masked areas
        result = directions.copy()
        result[mask] = smoothed[mask]
        
        return result

    def _calculate_depression_depth_optimized(self, elevation: np.ndarray, depression_mask: np.ndarray) -> np.ndarray:
        """Optimized: Calculate depression depth using maximum filter (vectorized)."""
        from scipy.ndimage import maximum_filter
        
        max_neighbors = maximum_filter(elevation, size=3)
        depth = max_neighbors - elevation
        depth[~depression_mask] = 0
        
        return depth
    
    def _filter_by_area_optimized(self, mask: np.ndarray, min_area: int) -> np.ndarray:
        """
        Optimized: Filter connected components by minimum area using vectorized operations.
        """
        from scipy import ndimage
        
        logger.info(f"   Labeling connected components...")
        # Label connected components
        labeled_mask, num_features = ndimage.label(mask)
        
        if num_features == 0:
            return mask
        
        logger.info(f"   Found {num_features} components, calculating sizes...")
        # Calculate component sizes using vectorized operations
        component_sizes = ndimage.sum(mask, labeled_mask, range(1, num_features + 1))
        
        # Create filter for components that meet minimum area
        valid_components = component_sizes >= min_area
        
        logger.info(f"   Filtering components (min_area={min_area})...")
        # Create output mask using vectorized operations
        filtered_mask = np.zeros_like(mask, dtype=bool)
        
        # Use advanced indexing to set valid components (optimized)
        valid_indices = np.where(valid_components)[0] + 1  # +1 because labels start at 1
        for idx in valid_indices:
            filtered_mask[labeled_mask == idx] = True
        
        logger.info(f"🏞️ Area filtering: {np.sum(mask)} -> {np.sum(filtered_mask)} cells")
        return filtered_mask

    def _compute_wind_channeling(self, elevation: np.ndarray, slope: np.ndarray,
                                aspect: np.ndarray, barranco_results: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Compute wind channeling effects using same algorithm as current ForestModel.
        """
        logger.info("💨 Computing wind channeling effects...")
        
        # Initialize wind channeling arrays
        wind_channeling_mask = np.zeros_like(elevation, dtype=bool)
        wind_amplification = np.ones_like(elevation, dtype=np.float32)
        wind_direction_modification = np.zeros_like(aspect, dtype=np.float32)
        
        # Apply barranco wind channeling (same as ForestModel)
        barranco_mask = barranco_results['barranco_mask']
        
        # Barrancos act as wind channels (literature-based amplification)
        wind_channeling_mask[barranco_mask] = True
        wind_amplification[barranco_mask] = self.config.barranco_amplification
        wind_direction_modification[barranco_mask] = barranco_results['barranco_directions'][barranco_mask]
        
        # Smooth wind fields if requested
        if self.config.smooth_wind_fields:
            wind_amplification = self._smooth_wind_field_optimized(wind_amplification, wind_channeling_mask)
        
        logger.info(f"💨 Wind channeling cells: {np.sum(wind_channeling_mask)}")
        
        return {
            'wind_channeling_mask': wind_channeling_mask,
            'wind_amplification': wind_amplification,
            'wind_direction_modification': wind_direction_modification
        }
    
    def _smooth_wind_field_optimized(self, wind_field: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Optimized: Smooth wind field using vectorized uniform filter."""
        from scipy.ndimage import uniform_filter
        
        # Only smooth areas where mask is True
        smoothed = wind_field.copy()
        
        # Apply uniform filter only to masked areas
        if np.any(mask):
            # Create a temporary array for smoothing
            temp_field = wind_field.copy()
            # Set non-masked areas to 0 for smoothing
            temp_field[~mask] = 0
            
            # Apply uniform filter
            kernel_size = self.config.smoothing_kernel_size
            smoothed_temp = uniform_filter(temp_field, size=kernel_size)
            
            # Only update masked areas
            smoothed[mask] = smoothed_temp[mask]
        
        return smoothed
    
    def _create_metadata(self) -> Dict[str, Any]:
        """Create metadata for the preprocessed data."""
        return {
            'dem_file': self.config.dem_file,
            'output_dir': self.config.output_dir,
            'processing_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'grid_size': self.dem_data.shape,
            'crs': str(self.crs) if self.crs else 'Unknown',
            'transform': str(self.transform) if self.transform else 'Unknown',
            'barranco_threshold': self.config.barranco_threshold,
            'min_depression_depth': self.config.min_depression_depth,
            'wind_channeling_strength': self.config.wind_channeling_strength,
            'elevation_range': [float(np.nanmin(self.dem_data)), float(np.nanmax(self.dem_data))]
        }
    
    def _save_preprocessed_data_optimized(self, data: PreprocessedTerrainData):
        """Save preprocessed data to files with improved memory management."""
        logger.info("💾 Saving preprocessed data with optimized memory management...")
        
        output_dir = Path(self.config.output_dir)
        
        # Clear existing files to avoid conflicts
        for file_pattern in ["*.npy", "*.json", "*.txt"]:
            for file_path in output_dir.glob(file_pattern):
                if file_path.name not in ["metadata.json", "processing_log.txt", "validation_report.json"]:
                    file_path.unlink()
        
        # Save NumPy arrays with memory management
        arrays_to_save = {
            "elevation.npy": data.elevation,
            "slope.npy": data.slope,
            "aspect.npy": data.aspect,
            "barranco_mask.npy": data.barranco_mask,
            "barranco_directions.npy": data.barranco_directions,
            "depression_mask.npy": data.depression_mask,
            "wind_channeling_mask.npy": data.wind_channeling_mask,
            "wind_amplification.npy": data.wind_amplification,
            "wind_direction_modification.npy": data.wind_direction_modification
        }
        
        for filename, array in arrays_to_save.items():
            logger.info(f"   Saving {filename}...")
            filepath = output_dir / filename
            
            try:
                # Save with memory-efficient method
                np.save(filepath, array, allow_pickle=False)
                logger.info(f"   ✅ Saved {filename} ({array.shape}, {array.dtype})")
                
                # Force garbage collection after each save
                del array
                gc.collect()
                
            except Exception as e:
                logger.error(f"   ❌ Failed to save {filename}: {e}")
                raise
        
        # Save metadata
        logger.info("   Saving metadata...")
        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(data.metadata, f, indent=2)
        
        # Save processing log
        logger.info("   Saving processing log...")
        with open(output_dir / "processing_log.txt", 'w') as f:
            f.write(f"Terrain preprocessing completed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"DEM file: {self.config.dem_file}\n")
            f.write(f"Grid size: {data.elevation.shape}\n")
            f.write(f"Barranco cells: {np.sum(data.barranco_mask)}\n")
            f.write(f"Wind channeling cells: {np.sum(data.wind_channeling_mask)}\n")
            f.write(f"Processing method: Fixed rasterio with memory optimization\n")
        
        logger.info(f"✅ Preprocessed data saved to {output_dir}")
        
        # Final garbage collection
        gc.collect()


def create_terrain_preprocessor_rasterio_fixed(dem_file: str, 
                                             output_dir: str,
                                             **kwargs) -> TerrainPreprocessorRasterioFixed:
    """
    Create a fixed terrain preprocessor using rasterio.
    
    Args:
        dem_file: Path to DEM file
        output_dir: Output directory for preprocessed data
        **kwargs: Additional configuration parameters
    
    Returns:
        TerrainPreprocessorRasterioFixed instance
    """
    config = TerrainPreprocessingConfig(
        dem_file=dem_file,
        output_dir=output_dir,
        **kwargs
    )
    
    return TerrainPreprocessorRasterioFixed(config) 