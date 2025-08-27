#!/usr/bin/env python3
"""
LiDAR Preprocessor Module

This module preprocesses LiDAR/PAD data to NumPy arrays for fast loading
during calibration runs. Uses existing LiDARDataManager architecture.

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
import time

from src.utils.logging_utils import get_logger
from src.utils.lidar_utils import LiDARDataManager

logger = get_logger(__name__)

@dataclass
class LiDARPreprocessingConfig:
    """Configuration for LiDAR preprocessing."""
    
    # Input configuration
    lidar_data_dir: str
    fire_bounds: Tuple[float, float, float, float]  # [min_x, min_y, max_x, max_y]
    
    # Processing configuration
    resolution: float = 20.0
    num_layers: int = 25
    nodata_value: float = 0.0
    
    # Output configuration
    output_dir: str = "preprocessed_lidar"
    
    def __post_init__(self):
        """Validate and create output directory."""
        if not Path(self.lidar_data_dir).exists():
            raise ValueError(f"LiDAR data directory does not exist: {self.lidar_data_dir}")
        
        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

@dataclass
class PreprocessedLiDARData:
    """Container for preprocessed LiDAR data."""
    
    # Layer data (mapping layer index to NumPy array)
    layer_data: Dict[int, np.ndarray]
    
    # Grid information
    grid_size: Tuple[int, int]
    resolution: float
    fire_bounds: Tuple[float, float, float, float]
    
    # Metadata
    metadata: Dict[str, Any]
    
    # File paths for saved data
    file_paths: Dict[str, str] = None
    
    def __post_init__(self):
        """Initialize file paths if not provided."""
        if self.file_paths is None:
            self.file_paths = {}

class LiDARPreprocessor:
    """
    LiDAR preprocessor that uses existing LiDARDataManager architecture
    to convert PAD files to optimized NumPy arrays.
    """
    
    def __init__(self, config: LiDARPreprocessingConfig):
        """
        Initialize LiDAR preprocessor.
        
        Args:
            config: LiDAR preprocessing configuration
        """
        self.config = config
        
        # Calculate grid size from fire bounds
        width_m = config.fire_bounds[2] - config.fire_bounds[0]
        height_m = config.fire_bounds[3] - config.fire_bounds[1]
        self.grid_width = int(width_m / config.resolution)
        self.grid_height = int(height_m / config.resolution)
        self.grid_size = (self.grid_width, self.grid_height)
        
        # Initialize LiDAR manager (using existing architecture)
        self.lidar_manager = LiDARDataManager(
            base_dir=config.lidar_data_dir,
            resolution=config.resolution
        )
        
        # Set geo_bounds for proper layer detection
        self.lidar_manager.geo_bounds = config.fire_bounds
        
        logger.info(f"Initialized LiDAR preprocessor:")
        logger.info(f"  Grid size: {self.grid_width} × {self.grid_height}")
        logger.info(f"  Resolution: {config.resolution}m")
        logger.info(f"  Layers: {config.num_layers}")
        logger.info(f"  Output: {config.output_dir}")
    
    def preprocess_lidar(self) -> PreprocessedLiDARData:
        """
        Preprocess LiDAR data using existing LiDARDataManager architecture.
        
        Returns:
            PreprocessedLiDARData with all layer arrays
        """
        logger.info("🚀 Starting LiDAR preprocessing...")
        start_time = time.time()
        
        try:
            # Step 1: Detect available layers (using existing method)
            logger.info("🔍 Detecting available PAD layers...")
            available_layers = self.lidar_manager._detect_available_layers(self.config.lidar_data_dir)
            
            if not available_layers:
                raise ValueError("No PAD layers found in LiDAR directory")
            
            logger.info(f"Found {len(available_layers)} PAD layers")
            
            # Step 2: Resample all layers (using existing method)
            logger.info("🔄 Resampling PAD data to model grid...")
            resampled_layers = self.lidar_manager.resample_pad_data_to_model_grid(
                pad_files_dict=available_layers,
                model_grid_extent=self.config.fire_bounds,
                model_grid_size=self.grid_size,
                model_resolution=self.config.resolution,
                nodata_value=self.config.nodata_value
            )
            
            if not resampled_layers:
                raise ValueError("Failed to resample PAD data")
            
            logger.info(f"Successfully resampled {len(resampled_layers)} layers")
            
            # Step 3: Create metadata
            metadata = self._create_metadata(available_layers, resampled_layers)
            
            # Step 4: Create preprocessed data container
            preprocessed_data = PreprocessedLiDARData(
                layer_data=resampled_layers,
                grid_size=self.grid_size,
                resolution=self.config.resolution,
                fire_bounds=self.config.fire_bounds,
                metadata=metadata
            )
            
            # Step 5: Save preprocessed data
            self._save_preprocessed_data(preprocessed_data)
            
            runtime = time.time() - start_time
            logger.info(f"✅ LiDAR preprocessing completed in {runtime:.1f}s")
            logger.info(f"  Processed {len(resampled_layers)} layers")
            logger.info(f"  Output: {self.config.output_dir}")
            
            return preprocessed_data
            
        except Exception as e:
            logger.error(f"❌ LiDAR preprocessing failed: {e}")
            raise
    
    def _create_metadata(self, available_layers: Dict[int, List[Path]], 
                        resampled_layers: Dict[int, np.ndarray]) -> Dict[str, Any]:
        """Create metadata for preprocessed data."""
        metadata = {
            'fire_bounds': self.config.fire_bounds,
            'grid_size': self.grid_size,
            'resolution': self.config.resolution,
            'num_layers': self.config.num_layers,
            'nodata_value': self.config.nodata_value,
            'available_layers': list(available_layers.keys()),
            'processed_layers': list(resampled_layers.keys()),
            'timestamp': time.time(),
            'layer_statistics': {}
        }
        
        # Add statistics for each layer
        for layer_idx, layer_data in resampled_layers.items():
            metadata['layer_statistics'][layer_idx] = {
                'shape': layer_data.shape,
                'dtype': str(layer_data.dtype),
                'min': float(np.min(layer_data)),
                'max': float(np.max(layer_data)),
                'mean': float(np.mean(layer_data)),
                'std': float(np.std(layer_data)),
                'non_zero_count': int(np.count_nonzero(layer_data))
            }
        
        return metadata
    
    def _save_preprocessed_data(self, data: PreprocessedLiDARData):
        """Save preprocessed data to disk."""
        output_dir = Path(self.config.output_dir)
        
        # Save metadata
        metadata_path = output_dir / 'lidar_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(data.metadata, f, indent=2)
        
        # Save each layer as NumPy array
        for layer_idx, layer_data in data.layer_data.items():
            layer_path = output_dir / f"layer_{layer_idx:02d}.npy"
            np.save(layer_path, layer_data)
            data.file_paths[f"layer_{layer_idx}"] = str(layer_path)
        
        # Save file paths
        paths_path = output_dir / 'file_paths.json'
        with open(paths_path, 'w') as f:
            json.dump(data.file_paths, f, indent=2)
        
        logger.info(f"Saved {len(data.layer_data)} layers to {output_dir}")

def create_lidar_preprocessor_from_fire_bounds(lidar_dir: str, 
                                             fire_bounds: Tuple[float, float, float, float],
                                             output_dir: str = "preprocessed_lidar",
                                             resolution: float = 20.0,
                                             num_layers: int = 25) -> LiDARPreprocessor:
    """
    Create LiDAR preprocessor from fire bounds (following existing pattern).
    
    Args:
        lidar_dir: LiDAR data directory
        fire_bounds: Fire area bounds [min_x, min_y, max_x, max_y]
        output_dir: Output directory for preprocessed data
        resolution: Target resolution in meters
        num_layers: Number of layers to process
        
    Returns:
        LiDARPreprocessor instance
    """
    config = LiDARPreprocessingConfig(
        lidar_data_dir=lidar_dir,
        fire_bounds=fire_bounds,
        output_dir=output_dir,
        resolution=resolution,
        num_layers=num_layers
    )
    
    return LiDARPreprocessor(config)
