#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Terrain Preprocessor Module

This module preprocesses terrain data to extract slope, aspect, barranco detection,
and wind channeling effects. This avoids expensive runtime calculations during
fire simulation and significantly improves performance.

The preprocessor uses the same algorithms as the current ForestModel implementation
to ensure consistency and accuracy.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import json
import pickle
# Add import for scipy.ndimage for vectorized operations
import scipy.ndimage

try:
    from osgeo import gdal
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False

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
        def get_logger(name):
            return logging.getLogger(name)
        logger = get_logger(__name__)
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
    
    # Processing parameters (same as current ForestModel defaults)
    barranco_threshold: float = 30.0  # Slope threshold for barranco detection
    min_depression_depth: float = 5.0  # Minimum depression depth
    smoothing_kernel_size: int = 3  # Wind field smoothing kernel
    wind_channeling_strength: float = 0.6  # Terrain effect strength
    
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


class TerrainPreprocessor:
    """
    Terrain preprocessor that extracts current ForestModel terrain algorithms
    and applies them during preprocessing for improved performance.
    """
    
    def __init__(self, config: TerrainPreprocessingConfig):
        """
        Initialize terrain preprocessor.
        
        Args:
            config: Terrain preprocessing configuration
        """
        self.config = config
        self.dem_data = None
        self.geotransform = None
        self.projection = None
        
        logger.info(f"Initialized terrain preprocessor for {config.dem_file}")
        logger.info(f"Output directory: {config.output_dir}")
    
    def preprocess_terrain(self) -> PreprocessedTerrainData:
        """
        Preprocess terrain data using current ForestModel algorithms.
        
        Returns:
            PreprocessedTerrainData with all computed terrain features
        """
        logger.info("🚀 Starting terrain preprocessing...")
        
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
        """Load DEM data using GDAL (same as current ForestModel)."""
        if not GDAL_AVAILABLE:
            raise ImportError("GDAL is required for terrain preprocessing")
        
        logger.info(f"📁 Loading DEM data from {self.config.dem_file}")
        
        try:
            gdal.UseExceptions()
            dataset = gdal.Open(self.config.dem_file)
            
            if dataset is None:
                raise ValueError(f"Could not open DEM file: {self.config.dem_file}")
            
            # Get geospatial information
            self.geotransform = dataset.GetGeoTransform()
            self.projection = dataset.GetProjection()
            
            # Read elevation data (already masked, with NaNs for water)
            self.dem_data = band = dataset.GetRasterBand(1).ReadAsArray().astype(np.float32)
            
            # Diagnostic: print number of valid land cells and total cells
            num_valid_land = np.sum(~np.isnan(self.dem_data))
            total_cells = self.dem_data.size
            logger.info(f"✅ Number of valid (non-NaN) land cells: {num_valid_land}")
            logger.info(f"🔢 Total number of cells: {total_cells}")
            
            # Apply geographic bounds if specified
            if self.config.geo_bounds is not None:
                self.dem_data = self._crop_to_bounds(self.dem_data, self.config.geo_bounds)
            
            logger.info(f"📊 DEM loaded: {self.dem_data.shape} cells")
            logger.info(f"📏 Elevation range: {np.nanmin(self.dem_data):.1f}m to {np.nanmax(self.dem_data):.1f}m")
            
        except Exception as e:
            handle_terrain_error(e, "loading DEM data")
            raise
    
    def _crop_to_bounds(self, data: np.ndarray, bounds: Tuple[float, float, float, float]) -> np.ndarray:
        """Crop DEM data to specified geographic bounds."""
        min_x, min_y, max_x, max_y = bounds
        
        # Convert geographic coordinates to pixel coordinates
        # This is a simplified version - in production, use proper coordinate transformation
        pixel_size_x = abs(self.geotransform[1])
        pixel_size_y = abs(self.geotransform[5])
        
        # Calculate pixel offsets (simplified)
        offset_x = int((min_x - self.geotransform[0]) / pixel_size_x)
        offset_y = int((self.geotransform[3] - max_y) / pixel_size_y)
        
        width = int((max_x - min_x) / pixel_size_x)
        height = int((max_y - min_y) / pixel_size_y)
        
        # Ensure bounds are within data
        offset_x = max(0, min(offset_x, data.shape[1] - 1))
        offset_y = max(0, min(offset_y, data.shape[0] - 1))
        width = min(width, data.shape[1] - offset_x)
        height = min(height, data.shape[0] - offset_y)
        
        return data[offset_y:offset_y+height, offset_x:offset_x+width]
    
    def _compute_basic_terrain(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute slope and aspect using same algorithm as current ForestModel."""
        logger.info("🏔️ Computing slope and aspect...")
        
        elevation = self.dem_data
        
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
        
        # Step 5: Apply minimum depth filter
        if self.config.min_depression_depth > 0:
            depth_mask = self._calculate_depression_depth(elevation, depression_mask)
            deep_depressions = depth_mask >= self.config.min_depression_depth
            barranco_mask = np.logical_and(barranco_mask, deep_depressions)
        
        logger.info(f"🏞️ Detected {np.sum(barranco_mask)} barranco cells")
        logger.info(f"🏞️ Detected {np.sum(depression_mask)} depression cells")
        
        return {
            'barranco_mask': barranco_mask,
            'barranco_directions': barranco_directions,
            'depression_mask': depression_mask
        }
    
    def _detect_topographic_depressions(self, elevation: np.ndarray) -> np.ndarray:
        """
        Detect topographic depressions using a vectorized approach.
        A cell is a depression if it is the minimum in its 3x3 neighborhood.
        Water cells are not considered depressions.
        """
        min_neighbors = scipy.ndimage.minimum_filter(elevation, size=3, mode='nearest')
        depression_mask = (elevation <= min_neighbors) & (~np.isnan(elevation))
        return depression_mask
    
    def _calculate_barranco_directions(self, elevation: np.ndarray, aspect: np.ndarray, barranco_mask: np.ndarray) -> np.ndarray:
        """
        Calculate barranco flow directions using aspect analysis.
        Same algorithm as current ForestModel.
        """
        # Initialize barranco directions
        barranco_directions = np.zeros_like(aspect)
        
        # For barranco cells, use aspect as flow direction
        barranco_directions[barranco_mask] = aspect[barranco_mask]
        
        # Smooth barranco directions to create flow channels
        if self.config.smoothing_kernel_size > 1:
            barranco_directions = self._smooth_directions(barranco_directions, barranco_mask)
        
        return barranco_directions
    
    def _smooth_directions(self, directions: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Smooth directional data using circular mean.
        Same algorithm as current ForestModel.
        """
        # Convert to radians for circular operations
        directions_rad = np.radians(directions)
        
        # Create smoothed directions
        smoothed_directions = directions.copy()
        
        # Apply smoothing kernel
        kernel_size = self.config.smoothing_kernel_size
        half_kernel = kernel_size // 2
        
        height, width = directions.shape
        
        for i in range(half_kernel, height - half_kernel):
            for j in range(half_kernel, width - half_kernel):
                if mask[i, j]:  # Only smooth barranco cells
                    # Extract neighborhood
                    neighborhood = directions_rad[i-half_kernel:i+half_kernel+1, 
                                               j-half_kernel:j+half_kernel+1]
                    
                    # Calculate circular mean
                    sin_sum = np.sum(np.sin(neighborhood))
                    cos_sum = np.sum(np.cos(neighborhood))
                    
                    if sin_sum != 0 or cos_sum != 0:
                        mean_angle = np.arctan2(sin_sum, cos_sum)
                        smoothed_directions[i, j] = np.degrees(mean_angle)
        
        return smoothed_directions
    
    def _calculate_depression_depth(self, elevation: np.ndarray, depression_mask: np.ndarray) -> np.ndarray:
        """
        Vectorized calculation of depression depth for filtering.
        For each cell, depth = max(neighbor) - center_elevation in 3x3 neighborhood.
        """
        # Use maximum_filter to get the maximum in each 3x3 neighborhood
        max_neighbors = scipy.ndimage.maximum_filter(elevation, size=3, mode='nearest')
        depth = max_neighbors - elevation
        # Only keep depth for depression cells
        depth[~depression_mask] = 0
        return depth
    
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
        barranco_directions = barranco_results['barranco_directions']
        
        # Barranco cells have wind amplification
        wind_channeling_mask[barranco_mask] = True
        wind_amplification[barranco_mask] = 2.0  # Default amplification factor
        
        # Wind direction follows barranco direction
        wind_direction_modification[barranco_mask] = barranco_directions[barranco_mask]
        
        # Apply slope-based wind effects (same as ForestModel)
        steep_slopes = slope > 20.0  # Moderate slope threshold
        wind_channeling_mask[steep_slopes] = True
        
        # Slope-based amplification (gentle increase with slope)
        slope_amplification = 1.0 + (slope[steep_slopes] - 20.0) / 40.0  # 1.0 to 2.0 range
        wind_amplification[steep_slopes] = np.maximum(wind_amplification[steep_slopes], slope_amplification)
        
        # Apply terrain effect strength
        wind_amplification *= self.config.wind_channeling_strength
        
        # Smooth wind fields if requested
        if self.config.smooth_wind_fields:
            wind_amplification = self._smooth_wind_field(wind_amplification, wind_channeling_mask)
        
        logger.info(f"💨 Wind channeling applied to {np.sum(wind_channeling_mask)} cells")
        logger.info(f"💨 Amplification range: {np.min(wind_amplification):.2f}x to {np.max(wind_amplification):.2f}x")
        
        return {
            'wind_channeling_mask': wind_channeling_mask,
            'wind_amplification': wind_amplification,
            'wind_direction_modification': wind_direction_modification
        }
    
    def _smooth_wind_field(self, wind_field: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Smooth wind field using Gaussian filter.
        Same algorithm as current ForestModel.
        """
        # Apply smoothing to wind amplification field
        smoothed_field = wind_field.copy()
        
        # Use simple moving average for smoothing
        kernel_size = self.config.smoothing_kernel_size
        half_kernel = kernel_size // 2
        
        height, width = wind_field.shape
        
        for i in range(half_kernel, height - half_kernel):
            for j in range(half_kernel, width - half_kernel):
                if mask[i, j]:  # Only smooth wind channeling cells
                    # Extract neighborhood
                    neighborhood = wind_field[i-half_kernel:i+half_kernel+1, 
                                           j-half_kernel:j+half_kernel+1]
                    
                    # Calculate mean
                    smoothed_field[i, j] = np.mean(neighborhood)
        
        return smoothed_field
    
    def _create_metadata(self) -> Dict[str, Any]:
        """Create metadata for preprocessed terrain data."""
        metadata = {
            'preprocessing_config': {
                'barranco_threshold': self.config.barranco_threshold,
                'min_depression_depth': self.config.min_depression_depth,
                'smoothing_kernel_size': self.config.smoothing_kernel_size,
                'wind_channeling_strength': self.config.wind_channeling_strength,
                'crs': self.config.crs
            },
            'terrain_statistics': {
                'elevation_min': float(np.min(self.dem_data)),
                'elevation_max': float(np.max(self.dem_data)),
                'elevation_mean': float(np.mean(self.dem_data)),
                'grid_size': self.dem_data.shape,
                'cell_count': int(self.dem_data.size)
            },
            'processing_info': {
                'algorithm_version': '1.0',
                'source_algorithm': 'ForestModel terrain processing',
                'preprocessing_date': str(np.datetime64('now'))
            }
        }
        
        return metadata
    
    def _save_preprocessed_data(self, data: PreprocessedTerrainData):
        """Save preprocessed terrain data to files."""
        logger.info(f"💾 Saving preprocessed terrain data to {self.config.output_dir}")
        
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual arrays
        file_paths = {}
        
        if self.config.format == "numpy":
            # Save as numpy arrays
            arrays_to_save = {
                'elevation': data.elevation,
                'slope': data.slope,
                'aspect': data.aspect,
                'barranco_mask': data.barranco_mask,
                'barranco_directions': data.barranco_directions,
                'depression_mask': data.depression_mask,
                'wind_channeling_mask': data.wind_channeling_mask,
                'wind_amplification': data.wind_amplification,
                'wind_direction_modification': data.wind_direction_modification
            }
            
            for name, array in arrays_to_save.items():
                file_path = output_dir / f"{name}.npy"
                np.save(file_path, array)
                file_paths[name] = str(file_path)
                
                if self.config.compression:
                    # Also save compressed version
                    comp_path = output_dir / f"{name}_compressed.npz"
                    np.savez_compressed(comp_path, data=array)
                    file_paths[f"{name}_compressed"] = str(comp_path)
        
        elif self.config.format == "pickle":
            # Save as pickle file
            file_path = output_dir / "preprocessed_terrain.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
            file_paths['pickle'] = str(file_path)
        
        # Save metadata
        metadata_path = output_dir / "terrain_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(data.metadata, f, indent=2)
        file_paths['metadata'] = str(metadata_path)
        
        # Save configuration
        config_path = output_dir / "preprocessing_config.json"
        with open(config_path, 'w') as f:
            json.dump(self.config.__dict__, f, indent=2)
        file_paths['config'] = str(config_path)
        
        # Update file paths in data
        data.file_paths = file_paths
        
        logger.info(f"✅ Saved {len(file_paths)} terrain data files")
    
    def load_preprocessed_data(self, output_dir: str) -> Optional[PreprocessedTerrainData]:
        """
        Load preprocessed terrain data from files.
        
        Args:
            output_dir: Directory containing preprocessed data
            
        Returns:
            PreprocessedTerrainData if found, None otherwise
        """
        output_dir = Path(output_dir)
        
        if not output_dir.exists():
            logger.warning(f"Preprocessed terrain directory not found: {output_dir}")
            return None
        
        try:
            # Load metadata
            metadata_path = output_dir / "terrain_metadata.json"
            if not metadata_path.exists():
                logger.warning("Terrain metadata not found")
                return None
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Load arrays
            file_paths = {}
            arrays = {}
            
            array_names = [
                'elevation', 'slope', 'aspect', 'barranco_mask', 
                'barranco_directions', 'depression_mask', 'wind_channeling_mask',
                'wind_amplification', 'wind_direction_modification'
            ]
            
            for name in array_names:
                file_path = output_dir / f"{name}.npy"
                if file_path.exists():
                    arrays[name] = np.load(file_path)
                    file_paths[name] = str(file_path)
                else:
                    logger.warning(f"Array file not found: {file_path}")
                    return None
            
            # Create PreprocessedTerrainData object
            data = PreprocessedTerrainData(
                elevation=arrays['elevation'],
                slope=arrays['slope'],
                aspect=arrays['aspect'],
                barranco_mask=arrays['barranco_mask'],
                barranco_directions=arrays['barranco_directions'],
                depression_mask=arrays['depression_mask'],
                wind_channeling_mask=arrays['wind_channeling_mask'],
                wind_amplification=arrays['wind_amplification'],
                wind_direction_modification=arrays['wind_direction_modification'],
                metadata=metadata,
                file_paths=file_paths
            )
            
            logger.info(f"✅ Loaded preprocessed terrain data from {output_dir}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load preprocessed terrain data: {e}")
            return None


def create_terrain_preprocessor(dem_file: str, 
                              output_dir: str,
                              **kwargs) -> TerrainPreprocessor:
    """
    Convenience function to create a terrain preprocessor.
    
    Args:
        dem_file: Path to DEM file
        output_dir: Output directory for preprocessed data
        **kwargs: Additional configuration parameters
        
    Returns:
        TerrainPreprocessor instance
    """
    config = TerrainPreprocessingConfig(
        dem_file=dem_file,
        output_dir=output_dir,
        **kwargs
    )
    
    return TerrainPreprocessor(config)


def preprocess_terrain_batch(dem_files: List[str], 
                           output_base_dir: str,
                           **kwargs) -> Dict[str, PreprocessedTerrainData]:
    """
    Preprocess multiple DEM files in batch.
    
    Args:
        dem_files: List of DEM file paths
        output_base_dir: Base directory for outputs
        **kwargs: Configuration parameters
        
    Returns:
        Dictionary mapping DEM files to PreprocessedTerrainData
    """
    results = {}
    
    for dem_file in dem_files:
        logger.info(f"🔄 Processing {dem_file}")
        
        # Create output directory for this DEM
        dem_name = Path(dem_file).stem
        output_dir = Path(output_base_dir) / dem_name
        
        # Create preprocessor and process
        preprocessor = create_terrain_preprocessor(
            dem_file=dem_file,
            output_dir=str(output_dir),
            **kwargs
        )
        
        try:
            result = preprocessor.preprocess_terrain()
            results[dem_file] = result
            logger.info(f"✅ Completed {dem_file}")
        except Exception as e:
            logger.error(f"❌ Failed to process {dem_file}: {e}")
            results[dem_file] = None
    
    return results


if __name__ == "__main__":
    # Example usage
    print("Terrain Preprocessor Example")
    print("=" * 50)
    
    # Updated configuration for user
    config = TerrainPreprocessingConfig(
        dem_file="C:/Users/user/Desktop/UvA/YEAR 2/Thesis/LiDAR/DTM data/Merged_DTM.tif",
        output_dir="preprocessed_terrain",
        barranco_threshold=30.0,
        min_depression_depth=5.0,
        compute_slope_aspect=True,
        detect_barrancos=True,
        compute_wind_channeling=True
    )
    
    print(f"DEM file: {config.dem_file}")
    print(f"Output directory: {config.output_dir}")
    print(f"Barranco threshold: {config.barranco_threshold}°")
    print(f"Min depression depth: {config.min_depression_depth}m")
    
    # Create preprocessor
    preprocessor = TerrainPreprocessor(config)
    
    # Preprocess terrain
    try:
        result = preprocessor.preprocess_terrain()
        print(f"✅ Preprocessing completed successfully")
        print(f"📊 Grid size: {result.elevation.shape}")
        print(f"🏞️ Barranco cells: {np.sum(result.barranco_mask)}")
        print(f"💨 Wind channeling cells: {np.sum(result.wind_channeling_mask)}")
    except Exception as e:
        print(f"❌ Preprocessing failed: {e}") 