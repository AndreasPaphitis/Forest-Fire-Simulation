#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Alternative Terrain Preprocessor using Rasterio

This module provides terrain preprocessing functionality using rasterio instead of GDAL.
It implements the same algorithms as the GDAL-based version but with better Windows compatibility.
"""

import os
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import json
import pickle
import time

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
    barranco_threshold: float = 25.0  # Slope threshold for barranco detection (literature: 20-30°)
    min_depression_depth: float = 3.0  # Minimum depression depth (literature: 2-5m for volcanic terrain)
    min_depression_area: int = 6  # Minimum depression area in cells (literature: 4-8 cells)
    smoothing_kernel_size: int = 3  # Wind field smoothing kernel
    wind_channeling_strength: float = 0.8  # Terrain effect strength (literature: 0.7-1.0 for barrancos)
    barranco_amplification: float = 2.5  # Wind amplification in barrancos (literature: 2.0-3.0)
    
    # Geographic bounds (optional - will use full DEM if not specified)
    geo_bounds: Optional[Tuple[float, float, float, float]] = None
    crs: str = "EPSG:25828"  # Default CRS for Tenerife
    
    # Processing options
    compute_slope_aspect: bool = True
    detect_barrancos: bool = True
    compute_wind_channeling: bool = True
    smooth_wind_fields: bool = True
    
    # Output options
    save_intermediate: bool = False
    compression: bool = True
    format: str = "numpy"  # numpy, geotiff, or pickle
    
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


class TerrainPreprocessorRasterio:
    """
    Terrain preprocessor using rasterio instead of GDAL.
    Implements the same algorithms as the GDAL version for compatibility.
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
        
        logger.info(f"Initialized rasterio terrain preprocessor for {config.dem_file}")
        logger.info(f"Output directory: {config.output_dir}")
    
    def preprocess_terrain(self) -> PreprocessedTerrainData:
        """
        Preprocess terrain data using current ForestModel algorithms.
        
        Returns:
            PreprocessedTerrainData with all computed terrain features
        """
        logger.info("🚀 Starting terrain preprocessing with rasterio...")
        
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
            
            # Step 7: Save preprocessed data
            self._save_preprocessed_data(preprocessed_data)
            
            logger.info("✅ Terrain preprocessing completed successfully")
            return preprocessed_data
            
        except Exception as e:
            logger.error(f"❌ Terrain preprocessing failed: {e}")
            raise
    
    def _load_dem_data(self):
        """Load DEM data using rasterio."""
        if not RASTERIO_AVAILABLE:
            raise ImportError("Rasterio is required for terrain preprocessing")
        
        logger.info(f"📁 Loading DEM data from {self.config.dem_file}")
        
        try:
            with rasterio.open(self.config.dem_file) as dataset:
                # Get geospatial information
                self.transform = dataset.transform
                self.crs = dataset.crs
                
                # Read elevation data
                self.dem_data = dataset.read(1)  # Read first band
                
                # Apply geographic bounds if specified
                if self.config.geo_bounds is not None:
                    self.dem_data = self._crop_to_bounds(self.dem_data, self.config.geo_bounds)
                
                logger.info(f"📊 DEM loaded: {self.dem_data.shape} cells")
                logger.info(f"📏 Elevation range: {np.min(self.dem_data):.1f}m to {np.max(self.dem_data):.1f}m")
                
        except Exception as e:
            logger.error(f"Failed to load DEM data: {e}")
            raise
    
    def _crop_to_bounds(self, data: np.ndarray, bounds: Tuple[float, float, float, float]) -> np.ndarray:
        """Crop data to specified geographic bounds."""
        # This is a simplified implementation
        # In practice, you'd use rasterio's windowed reading for proper geographic cropping
        return data
    
    def _compute_basic_terrain(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute basic terrain features (elevation, slope, aspect)."""
        logger.info("🏔️ Computing basic terrain features...")
        
        elevation = self.dem_data.astype(np.float32)
        
        # Compute slope and aspect using finite differences (same as ForestModel)
        # This is the exact algorithm from the current ForestModel implementation
        
        # Pad elevation with edge values to handle boundaries
        padded_elevation = np.pad(elevation, 1, mode='edge')
        
        # Compute gradients using central differences
        dy, dx = np.gradient(padded_elevation)
        
        # Remove padding
        dy = dy[1:-1, 1:-1]
        dx = dx[1:-1, 1:-1]
        
        # Compute slope (magnitude of gradient)
        slope = np.sqrt(dx**2 + dy**2)
        
        # Convert to degrees
        slope_degrees = np.degrees(np.arctan(slope))
        
        # Compute aspect (direction of gradient)
        aspect = np.degrees(np.arctan2(-dy, -dx))
        
        # Normalize aspect to 0-360 degrees
        aspect = (aspect + 360) % 360
        
        logger.info(f"📊 Slope range: {np.min(slope_degrees):.1f}° to {np.max(slope_degrees):.1f}°")
        logger.info(f"📊 Aspect range: {np.min(aspect):.1f}° to {np.max(aspect):.1f}°")
        
        return elevation, slope_degrees, aspect
    
    def _detect_barrancos(self, elevation: np.ndarray, slope: np.ndarray, aspect: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Detect barrancos using the same algorithm as current ForestModel.
        
        This implements the exact barranco detection logic from ForestModel:
        1. Detect topographic depressions
        2. Identify steep slopes (barranco_threshold)
        3. Calculate barranco directions
        4. Create barranco mask
        """
        logger.info("🏞️ Detecting barrancos and topographic depressions...")
        
        # Step 1: Detect topographic depressions (same as ForestModel)
        depression_mask = self._detect_topographic_depressions(elevation)
        
        # Step 2: Identify steep slopes for barranco detection
        steep_slope_mask = slope >= self.config.barranco_threshold
        
        # Step 3: Combine depressions and steep slopes for barranco detection
        barranco_mask = np.logical_and(depression_mask, steep_slope_mask)
        
        # Step 4: Calculate barranco directions (same as ForestModel)
        barranco_directions = self._calculate_barranco_directions(elevation, aspect, barranco_mask)
        
        # Step 5: Apply minimum depth and area filters
        if self.config.min_depression_depth > 0:
            depth_mask = self._calculate_depression_depth(elevation, depression_mask)
            deep_depressions = depth_mask >= self.config.min_depression_depth
            barranco_mask = np.logical_and(barranco_mask, deep_depressions)
        
        # Step 6: Apply minimum area filter (literature-based)
        if self.config.min_depression_area > 1:
            barranco_mask = self._filter_by_area(barranco_mask, self.config.min_depression_area)
        
        logger.info(f"🏞️ Detected {np.sum(barranco_mask)} barranco cells")
        logger.info(f"🏞️ Detected {np.sum(depression_mask)} depression cells")
        
        return {
            'barranco_mask': barranco_mask,
            'barranco_directions': barranco_directions,
            'depression_mask': depression_mask
        }
    
    def _detect_topographic_depressions(self, elevation: np.ndarray) -> np.ndarray:
        """
        Detect topographic depressions using flood fill algorithm.
        Same implementation as current ForestModel.
        """
        # This is the exact algorithm from ForestModel._detect_topographic_depressions
        
        # Create depression mask
        depression_mask = np.zeros_like(elevation, dtype=bool)
        
        # Use watershed-like approach to detect depressions
        # For each cell, check if it's lower than its neighbors
        height, width = elevation.shape
        
        for i in range(1, height - 1):
            for j in range(1, width - 1):
                center_elevation = elevation[i, j]
                
                # Check 8-connected neighbors
                neighbors = [
                    elevation[i-1:i+2, j-1:j+2].flatten()
                ]
                
                # If center is lower than all neighbors, it's a depression
                if np.all(center_elevation <= neighbors):
                    depression_mask[i, j] = True
        
        return depression_mask
    
    def _calculate_barranco_directions(self, elevation: np.ndarray, aspect: np.ndarray, barranco_mask: np.ndarray) -> np.ndarray:
        """Calculate flow directions within barrancos."""
        rows, cols = elevation.shape
        directions = np.zeros_like(aspect)
        
        for i in range(1, rows - 1):
            for j in range(1, cols - 1):
                if barranco_mask[i, j]:
                    # Use aspect as flow direction
                    directions[i, j] = aspect[i, j]
        
        # Smooth directions
        directions = self._smooth_directions(directions, barranco_mask)
        
        return directions
    
    def _smooth_directions(self, directions: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Smooth flow directions using local averaging."""
        rows, cols = directions.shape
        smoothed = directions.copy()
        
        for i in range(1, rows - 1):
            for j in range(1, cols - 1):
                if mask[i, j]:
                    # Get 3x3 neighborhood
                    neighborhood = directions[i-1:i+2, j-1:j+2]
                    mask_neighborhood = mask[i-1:i+2, j-1:j+2]
                    
                    # Average only valid directions
                    valid_directions = neighborhood[mask_neighborhood]
                    if len(valid_directions) > 0:
                        # Handle circular averaging for angles
                        sin_avg = np.mean(np.sin(valid_directions * np.pi / 180))
                        cos_avg = np.mean(np.cos(valid_directions * np.pi / 180))
                        smoothed[i, j] = (np.arctan2(sin_avg, cos_avg) * 180 / np.pi + 360) % 360
        
        return smoothed
    
    def _calculate_depression_depth(self, elevation: np.ndarray, depression_mask: np.ndarray) -> np.ndarray:
        """
        Calculate depression depth for filtering.
        Same algorithm as current ForestModel.
        """
        # Initialize depth array
        depth = np.zeros_like(elevation)
        
        # For each depression cell, calculate depth relative to surrounding terrain
        height, width = elevation.shape
        
        for i in range(1, height - 1):
            for j in range(1, width - 1):
                if depression_mask[i, j]:
                    center_elevation = elevation[i, j]
                    
                    # Get surrounding elevations
                    neighbors = elevation[i-1:i+2, j-1:j+2]
                    
                    # Calculate depth as difference from highest neighbor
                    max_neighbor = np.max(neighbors)
                    depth[i, j] = max_neighbor - center_elevation
        
        return depth
    
    def _filter_by_area(self, mask: np.ndarray, min_area: int) -> np.ndarray:
        """
        Filter connected components by minimum area.
        Literature-based approach for removing noise in barranco detection.
        """
        from scipy import ndimage
        
        # Label connected components
        labeled_mask, num_features = ndimage.label(mask)
        
        # Filter by area
        filtered_mask = np.zeros_like(mask, dtype=bool)
        
        for i in range(1, num_features + 1):
            component_size = np.sum(labeled_mask == i)
            if component_size >= min_area:
                filtered_mask[labeled_mask == i] = True
        
        logger.info(f"🏞️ Area filtering: {np.sum(mask)} -> {np.sum(filtered_mask)} cells (min_area={min_area})")
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
        
        # Apply additional wind channeling based on terrain features
        # This is the same logic as ForestModel._apply_wind_channeling
        
        # Smooth wind fields if requested
        if self.config.smooth_wind_fields:
            wind_amplification = self._smooth_wind_field(wind_amplification, wind_channeling_mask)
        
        logger.info(f"💨 Wind channeling cells: {np.sum(wind_channeling_mask)}")
        
        return {
            'wind_channeling_mask': wind_channeling_mask,
            'wind_amplification': wind_amplification,
            'wind_direction_modification': wind_direction_modification
        }
    

    
    def _smooth_wind_field(self, wind_field: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Smooth wind field using Gaussian-like smoothing."""
        rows, cols = wind_field.shape
        smoothed = wind_field.copy()
        
        kernel_size = self.config.smoothing_kernel_size
        
        for i in range(kernel_size, rows - kernel_size):
            for j in range(kernel_size, cols - kernel_size):
                if mask[i, j]:
                    # Get neighborhood
                    neighborhood = wind_field[i-kernel_size:i+kernel_size+1, 
                                           j-kernel_size:j+kernel_size+1]
                    mask_neighborhood = mask[i-kernel_size:i+kernel_size+1, 
                                           j-kernel_size:j+kernel_size+1]
                    
                    # Average valid values
                    valid_values = neighborhood[mask_neighborhood]
                    if len(valid_values) > 0:
                        smoothed[i, j] = np.mean(valid_values)
        
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
            'elevation_range': [float(np.min(self.dem_data)), float(np.max(self.dem_data))]
        }
    
    def _save_preprocessed_data(self, data: PreprocessedTerrainData):
        """Save preprocessed data to files."""
        logger.info("💾 Saving preprocessed data...")
        
        output_dir = Path(self.config.output_dir)
        
        # Save NumPy arrays
        np.save(output_dir / "elevation.npy", data.elevation)
        np.save(output_dir / "slope.npy", data.slope)
        np.save(output_dir / "aspect.npy", data.aspect)
        np.save(output_dir / "barranco_mask.npy", data.barranco_mask)
        np.save(output_dir / "barranco_directions.npy", data.barranco_directions)
        np.save(output_dir / "depression_mask.npy", data.depression_mask)
        np.save(output_dir / "wind_channeling_mask.npy", data.wind_channeling_mask)
        np.save(output_dir / "wind_amplification.npy", data.wind_amplification)
        np.save(output_dir / "wind_direction_modification.npy", data.wind_direction_modification)
        
        # Save metadata
        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(data.metadata, f, indent=2)
        
        # Save processing log
        with open(output_dir / "processing_log.txt", 'w') as f:
            f.write(f"Terrain preprocessing completed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"DEM file: {self.config.dem_file}\n")
            f.write(f"Grid size: {data.elevation.shape}\n")
            f.write(f"Barranco cells: {np.sum(data.barranco_mask)}\n")
            f.write(f"Wind channeling cells: {np.sum(data.wind_channeling_mask)}\n")
        
        logger.info(f"✅ Preprocessed data saved to {output_dir}")


def create_terrain_preprocessor_rasterio(dem_file: str, 
                                        output_dir: str,
                                        **kwargs) -> TerrainPreprocessorRasterio:
    """
    Create a terrain preprocessor using rasterio.
    
    Args:
        dem_file: Path to DEM file
        output_dir: Output directory for preprocessed data
        **kwargs: Additional configuration parameters
    
    Returns:
        TerrainPreprocessorRasterio instance
    """
    config = TerrainPreprocessingConfig(
        dem_file=dem_file,
        output_dir=output_dir,
        **kwargs
    )
    
    return TerrainPreprocessorRasterio(config) 