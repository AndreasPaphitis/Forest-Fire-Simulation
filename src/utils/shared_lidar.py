# src/utils/shared_lidar.py
#!/usr/bin/env python3
"""
Shared LiDAR data utilities for memory-efficient parallel processing.

This module provides functionality to load LiDAR/PAD data once and share it
across multiple worker processes, dramatically reducing memory usage and
eliminating GDAL contention issues.
"""

import numpy as np
import multiprocessing as mp
import sys
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import json
import os
import logging

# Check for shared_memory availability (Python 3.8+)
try:
    from multiprocessing import shared_memory
    HAS_SHARED_MEMORY = True
except ImportError:
    HAS_SHARED_MEMORY = False
    shared_memory = None

from src.utils.logging_utils import get_logger
logger = get_logger(__name__)

class SharedLiDARManager:
    """
    Manages LiDAR data across multiple processes using shared memory.
    
    This class handles loading LiDAR/PAD data once and sharing it across
    worker processes using Python's shared_memory module.
    """
    
    def __init__(self):
        self.shared_blocks = {}
        self.lidar_shapes = {}
        self.lidar_dtypes = {}
        self.shared_names = {}
        self.is_loaded = False
        
    def load_lidar_data(self, lidar_dir: str, fire_bounds: Tuple[float, float, float, float],
                       resolution: float = 20.0, num_layers: int = 25) -> bool:
        """
        Load LiDAR data into shared memory for multi-process access.
        
        Args:
            lidar_dir: Directory containing PAD files
            fire_bounds: [min_x, min_y, max_x, max_y] in UTM coordinates
            resolution: Model resolution in meters
            num_layers: Number of vertical layers
            
        Returns:
            True if successful, False otherwise
        """
        if not HAS_SHARED_MEMORY:
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            logger.warning(f"⚠️  Shared memory not available on Python {python_version}. Requires Python 3.8+.")
            logger.warning("   Falling back to individual LiDAR loading (higher memory usage)")
            return False
        
        # Clean up any existing shared memory files first
        self._cleanup_existing_shared_memory()
            
        try:
            from src.utils.lidar_utils import LiDARDataManager
            
            logger.info(f"�� Loading LiDAR data for fire bounds: {fire_bounds}")
            logger.info(f"   Resolution: {resolution}m, Layers: {num_layers}")
            
            # Create single LiDAR manager (main process only)
            lidar_manager = LiDARDataManager(
                base_dir=lidar_dir,
                resolution=resolution
            )
            
            # Load PAD data for fire area
            pad_data = lidar_manager.load_fire_area_data(
                fire_bounds=fire_bounds,
                num_layers=num_layers
            )
            
            if not pad_data:
                logger.error("❌ Failed to load PAD data from LiDAR manager")
                return False
            
            logger.info(f"✅ Loaded {len(pad_data)} PAD layers, storing in shared memory...")
            
            # Store in shared memory
            for layer_idx, layer_data in pad_data.items():
                shared_name = f"lidar_layer_{layer_idx}"
                
                # Create shared memory block
                shm = shared_memory.SharedMemory(
                    name=shared_name, 
                    create=True, 
                    size=layer_data.nbytes
                )
                
                # Copy data to shared memory
                shared_array = np.ndarray(
                    layer_data.shape, 
                    dtype=layer_data.dtype, 
                    buffer=shm.buf
                )
                shared_array[:] = layer_data[:]
                
                # Store references
                self.shared_blocks[layer_idx] = shm
                self.lidar_shapes[layer_idx] = layer_data.shape
                self.lidar_dtypes[layer_idx] = layer_data.dtype
                self.shared_names[layer_idx] = shared_name
                
                logger.debug(f"✅ Stored layer {layer_idx}: {layer_data.shape} in shared memory")
                
            self.is_loaded = True
            logger.info(f"✅ LiDAR data loaded into shared memory: {len(self.shared_blocks)} layers")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load shared LiDAR data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_shared_lidar_info(self) -> Dict[str, Any]:
        """
        Get shared LiDAR information for passing to worker processes.
        
        Returns:
            Dictionary containing shared memory information
        """
        if not self.is_loaded:
            return None
            
        return {
            'shared_names': self.shared_names,
            'shapes': self.lidar_shapes,
            'dtypes': self.lidar_dtypes,
            'num_layers': len(self.shared_blocks)
        }
    
    def _cleanup_existing_shared_memory(self):
        """Clean up any existing shared memory blocks."""
        try:
            for layer_idx, shm in self.shared_blocks.items():
                try:
                    shm.close()
                    shm.unlink()
                except Exception as e:
                    logger.debug(f"Could not cleanup shared memory for layer {layer_idx}: {e}")
            
            self.shared_blocks.clear()
            self.lidar_shapes.clear()
            self.lidar_dtypes.clear()
            self.shared_names.clear()
            self.is_loaded = False
            
        except Exception as e:
            logger.warning(f"Error during shared memory cleanup: {e}")
    
    def cleanup(self):
        """Clean up all shared memory resources."""
        self._cleanup_existing_shared_memory()

# Global instance for easy access
_shared_lidar_manager = None

def get_shared_lidar_manager() -> SharedLiDARManager:
    """Get the global shared LiDAR manager instance."""
    global _shared_lidar_manager
    if _shared_lidar_manager is None:
        _shared_lidar_manager = SharedLiDARManager()
    return _shared_lidar_manager

def load_shared_lidar_data(shared_info: Dict[str, Any]) -> Optional[Dict[int, np.ndarray]]:
    """
    Load LiDAR data from shared memory in worker processes.
    
    Args:
        shared_info: Shared LiDAR information from main process
        
    Returns:
        Dictionary mapping layer indices to numpy arrays, or None if failed
    """
    if not shared_info or not HAS_SHARED_MEMORY:
        return None
        
    try:
        lidar_data = {}
        
        for layer_idx in range(shared_info['num_layers']):
            if layer_idx not in shared_info['shared_names']:
                continue
                
            shared_name = shared_info['shared_names'][layer_idx]
            shape = shared_info['shapes'][layer_idx]
            dtype = shared_info['dtypes'][layer_idx]
            
            # Attach to shared memory
            shm = shared_memory.SharedMemory(name=shared_name)
            
            # Create numpy array from shared memory
            layer_data = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
            
            # Store reference to shared memory for cleanup
            if not hasattr(load_shared_lidar_data, '_attached_shm'):
                load_shared_lidar_data._attached_shm = []
            load_shared_lidar_data._attached_shm.append(shm)
            
            lidar_data[layer_idx] = layer_data
            
        logger.info(f"✅ Loaded {len(lidar_data)} LiDAR layers from shared memory")
        return lidar_data
        
    except Exception as e:
        logger.error(f"❌ Failed to load shared LiDAR data: {e}")
        return None
