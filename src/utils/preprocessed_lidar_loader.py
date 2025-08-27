#!/usr/bin/env python3
"""
Fast LiDAR loading from preprocessed NumPy arrays.

This module provides fast, GDAL-free loading of preprocessed LiDAR data
that has been converted to NumPy arrays.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import json

from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

class PreprocessedLiDARLoader:
    """
    Fast loader for preprocessed LiDAR data.
    
    This class loads preprocessed LiDAR data from NumPy arrays (.npy files)
    without requiring GDAL, providing fast access during simulation runs.
    """
    
    def __init__(self, preprocessed_dir: Union[str, Path]):
        """
        Initialize the preprocessed LiDAR loader.
        
        Args:
            preprocessed_dir: Directory containing preprocessed LiDAR data
        """
        self.preprocessed_dir = Path(preprocessed_dir)
        
        if not self.preprocessed_dir.exists():
            raise ValueError(f"Preprocessed directory does not exist: {preprocessed_dir}")
        
        # Load metadata
        self.metadata = self._load_metadata()
        if not self.metadata:
            raise ValueError(f"Failed to load metadata from {preprocessed_dir}")
        
        logger.info(f"Initialized preprocessed LiDAR loader: {preprocessed_dir}")
        logger.info(f"Available layers: {len(self.metadata.get('processed_layers', []))}")
    
    def _load_metadata(self) -> Optional[Dict[str, Any]]:
        """Load metadata from lidar_metadata.json."""
        metadata_path = self.preprocessed_dir / 'lidar_metadata.json'
        
        if not metadata_path.exists():
            logger.error(f"Metadata file not found: {metadata_path}")
            return None
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return metadata
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None
    
    def load_layer(self, layer_idx: int) -> Optional[np.ndarray]:
        """
        Load a specific layer from preprocessed data.
        
        Args:
            layer_idx: Layer index to load
            
        Returns:
            NumPy array for the layer, or None if not found
        """
        layer_path = self.preprocessed_dir / f"layer_{layer_idx:02d}.npy"
        
        if not layer_path.exists():
            logger.warning(f"Layer file not found: {layer_path}")
            return None
        
        try:
            layer_data = np.load(layer_path)
            logger.debug(f"Loaded layer {layer_idx}: {layer_data.shape}")
            return layer_data
        except Exception as e:
            logger.error(f"Failed to load layer {layer_idx}: {e}")
            return None
    
    def load_all_layers(self) -> Dict[int, np.ndarray]:
        """
        Load all available layers from preprocessed data.
        
        Returns:
            Dictionary mapping layer indices to NumPy arrays
        """
        processed_layers = self.metadata.get('processed_layers', [])
        layer_data = {}
        
        logger.info(f"Loading {len(processed_layers)} layers...")
        
        for layer_idx in processed_layers:
            layer_array = self.load_layer(layer_idx)
            if layer_array is not None:
                layer_data[layer_idx] = layer_array
        
        logger.info(f"Successfully loaded {len(layer_data)} layers")
        return layer_data
    
    def get_grid_info(self) -> Tuple[Tuple[int, int], float]:
        """
        Get grid information from metadata.
        
        Returns:
            Tuple of (grid_size, resolution)
        """
        grid_size = self.metadata.get('grid_size', (0, 0))
        resolution = self.metadata.get('resolution', 0.0)
        return grid_size, resolution
    
    def get_fire_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get fire bounds from metadata.
        
        Returns:
            Fire bounds as (min_x, min_y, max_x, max_y)
        """
        return tuple(self.metadata.get('fire_bounds', (0.0, 0.0, 0.0, 0.0)))
    
    def get_layer_statistics(self) -> Dict[int, Dict[str, Any]]:
        """
        Get layer statistics from metadata.
        
        Returns:
            Dictionary of layer statistics
        """
        return self.metadata.get('layer_statistics', {})
    
    def get_available_layers(self) -> List[int]:
        """
        Get list of available layer indices.
        
        Returns:
            List of available layer indices
        """
        return self.metadata.get('processed_layers', [])
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get full metadata.
        
        Returns:
            Complete metadata dictionary
        """
        return self.metadata.copy()

def load_preprocessed_lidar(preprocessed_dir: Union[str, Path]) -> Optional[Dict[int, np.ndarray]]:
    """
    Convenience function to load all preprocessed LiDAR data.
    
    Args:
        preprocessed_dir: Directory containing preprocessed LiDAR data
        
    Returns:
        Dictionary mapping layer indices to NumPy arrays, or None if failed
    """
    try:
        loader = PreprocessedLiDARLoader(preprocessed_dir)
        return loader.load_all_layers()
    except Exception as e:
        logger.error(f"Failed to load preprocessed LiDAR: {e}")
        return None
