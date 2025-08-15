#!/usr/bin/env python3
"""
Shared terrain data utilities for memory-efficient parallel processing.

This module provides functionality to load terrain data once and share it
across multiple worker processes using shared memory, dramatically reducing
memory usage in parallel sensitivity analysis.
"""

import numpy as np
import multiprocessing as mp
import sys
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import json
import os

# Check for shared_memory availability (Python 3.8+)
try:
    from multiprocessing import shared_memory
    HAS_SHARED_MEMORY = True
except ImportError:
    HAS_SHARED_MEMORY = False
    shared_memory = None

from src.utils.logging_utils import get_logger
logger = get_logger(__name__)

class SharedTerrainManager:
    """
    Manages shared terrain data across multiple processes.
    
    This class handles loading terrain data once and sharing it across
    worker processes using Python's shared_memory module.
    """
    
    def __init__(self):
        self.shared_blocks = {}
        self.terrain_shapes = {}
        self.terrain_dtypes = {}
        self.is_loaded = False
        
    def load_terrain_data(self, preprocessed_dir: str, target_shape: Tuple[int, int]) -> bool:
        """
        Load terrain data into shared memory.
        
        Args:
            preprocessed_dir: Directory containing preprocessed terrain files
            target_shape: Target shape for terrain data (height, width)
            
        Returns:
            True if successful, False otherwise
        """
        # Check if the target grid is too large for shared memory
        total_cells = target_shape[0] * target_shape[1]
        # Correct memory calculation: 6 float32 layers (4 bytes) + 3 uint8 layers (1 byte)
        estimated_memory_gb = total_cells * (6 * 4 + 3 * 1) / (1024**3)  # ~27 bytes per cell
        
        if estimated_memory_gb > 200:  # More than 200GB (increased limit for full Tenerife)
            logger.warning(f"⚠️  Target grid too large for shared memory: {target_shape}")
            logger.warning(f"   Estimated memory: {estimated_memory_gb:.1f} GB")
            logger.warning(f"   Disabling shared terrain to prevent memory issues")
            return False
        elif estimated_memory_gb > 100:
            logger.info(f"🗺️  Large domain detected: {target_shape}")
            logger.info(f"   Estimated shared terrain memory: {estimated_memory_gb:.1f} GB")
            logger.info(f"   Enabling shared terrain for full Tenerife domain")
            logger.info(f"   This will significantly reduce per-worker memory usage")
        # Check for shared memory availability
        if not HAS_SHARED_MEMORY:
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            logger.warning(f"⚠️  Shared memory not available on Python {python_version}. Requires Python 3.8+.")
            logger.warning("   Falling back to individual terrain loading (higher memory usage)")
            return False
            
        try:
            preprocessed_path = Path(preprocessed_dir)
            
            # Required terrain files
            terrain_files = [
                'elevation.npy',
                'slope.npy', 
                'aspect.npy',
                'barranco_mask.npy',
                'barranco_directions.npy',
                'depression_mask.npy',
                'wind_channeling_mask.npy',
                'wind_amplification.npy',
                'wind_direction_modification.npy'
            ]
            
            logger.info(f"🔄 Loading terrain data into shared memory from {preprocessed_dir}")
            
            for filename in terrain_files:
                file_path = preprocessed_path / filename
                if not file_path.exists():
                    logger.warning(f"⚠️  Terrain file not found: {filename}")
                    continue
                    
                # Load terrain data
                terrain_data = np.load(file_path)
                
                # Handle different grid sizes intelligently
                if terrain_data.shape != target_shape:
                    # Check if this is a full Tenerife domain request
                    if target_shape[0] > 10000 and target_shape[1] > 10000:
                        # Full Tenerife domain - ensure terrain matches exactly
                        logger.info(f"🗺️  Full Tenerife domain requested: {target_shape}")
                        if terrain_data.shape == target_shape:
                            logger.info(f"✅ Terrain data already matches full domain")
                        else:
                            logger.warning(f"⚠️  Terrain shape {terrain_data.shape} doesn't match full domain {target_shape}")
                            # For full domain, we need exact match or we skip shared terrain
                            if terrain_data.shape[0] >= target_shape[0] and terrain_data.shape[1] >= target_shape[1]:
                                # Crop to exact size if terrain is larger
                                terrain_data = terrain_data[:target_shape[0], :target_shape[1]]
                                logger.info(f"✅ Cropped terrain to exact domain size: {terrain_data.shape}")
                            else:
                                logger.error(f"❌ Terrain too small for full domain - skipping shared terrain for {filename}")
                                continue
                    else:
                        # Smaller domain - use subset for memory efficiency
                        logger.info(f"🔄 Subsetting {filename} from {terrain_data.shape} to {target_shape}")
                        logger.info(f"🏔️ Targeting Teide Southern Slopes (Pine Forest Belt) - 25% down, 40% across")
                        # Target Teide Southern Slopes (Pine Forest Belt) instead of geometric center
                        start_row = terrain_data.shape[0] // 4          # 25% down = ~3780 (southern slopes)
                        end_row = start_row + target_shape[0]           # +target_size
                        start_col = int(terrain_data.shape[1] * 0.4)    # 40% across = ~9896 (pine forests)
                        end_col = start_col + target_shape[1]           # +target_size
                        
                        # Ensure we don't exceed bounds
                        if end_row > terrain_data.shape[0]:
                            start_row = terrain_data.shape[0] - target_shape[0]
                            end_row = terrain_data.shape[0]
                        if end_col > terrain_data.shape[1]:
                            start_col = terrain_data.shape[1] - target_shape[1]
                            end_col = terrain_data.shape[1]
                        
                        terrain_data = terrain_data[start_row:end_row, start_col:end_col]
                
                # Create shared memory block
                terrain_name = filename.replace('.npy', '')
                nbytes = terrain_data.nbytes
                
                shm = shared_memory.SharedMemory(create=True, size=nbytes, name=f"terrain_{terrain_name}")
                
                # Copy data to shared memory
                shared_array = np.ndarray(terrain_data.shape, dtype=terrain_data.dtype, buffer=shm.buf)
                shared_array[:] = terrain_data[:]
                
                # Store references
                self.shared_blocks[terrain_name] = shm
                self.terrain_shapes[terrain_name] = terrain_data.shape
                self.terrain_dtypes[terrain_name] = terrain_data.dtype
                
                logger.info(f"✅ Loaded {terrain_name} into shared memory: {terrain_data.shape}, {nbytes/1024/1024:.1f} MB")
            
            self.is_loaded = True
            logger.info(f"✅ All terrain data loaded into shared memory")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading terrain data into shared memory: {e}")
            self.cleanup()
            return False
    
    def get_shared_terrain_info(self) -> Dict[str, Any]:
        """
        Get information about shared terrain data for worker processes.
        
        Returns:
            Dictionary containing shared memory names, shapes, and dtypes
        """
        return {
            'shared_names': {name: shm.name for name, shm in self.shared_blocks.items()},
            'shapes': self.terrain_shapes.copy(),
            'dtypes': {name: str(dtype) for name, dtype in self.terrain_dtypes.items()},
            'is_loaded': self.is_loaded
        }
    
    def cleanup(self):
        """Clean up shared memory blocks."""
        if not self.shared_blocks:
            logger.debug("No shared memory blocks to clean up")
            return
            
        for name, shm in list(self.shared_blocks.items()):
            try:
                # Validate that the shared memory block still exists
                if hasattr(shm, 'name') and hasattr(shm, 'size'):
                    shm.close()
                    shm.unlink()
                    logger.info(f"🧹 Cleaned up shared memory for {name}")
                else:
                    logger.warning(f"⚠️  Invalid shared memory block for {name}")
            except FileNotFoundError:
                # Shared memory block already cleaned up
                logger.debug(f"Shared memory block {name} already cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error cleaning up shared memory for {name}: {e}")
        
        self.shared_blocks.clear()
        self.terrain_shapes.clear()
        self.terrain_dtypes.clear()
        self.is_loaded = False


def load_shared_terrain_data(shared_info: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """
    Load terrain data from shared memory in a worker process.
    
    Args:
        shared_info: Information about shared terrain data
        
    Returns:
        Dictionary of terrain arrays
    """
    terrain_data = {}
    
    try:
        if not shared_info.get('is_loaded', False):
            logger.warning("No shared terrain data available")
            return terrain_data
            
        shared_names = shared_info['shared_names']
        shapes = shared_info['shapes']
        dtypes = shared_info['dtypes']
        
        for terrain_name, shm_name in shared_names.items():
            try:
                # Connect to existing shared memory
                shm = shared_memory.SharedMemory(name=shm_name)
                
                # Create numpy array view
                shape = shapes[terrain_name]
                dtype = np.dtype(dtypes[terrain_name])
                
                shared_array = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
                
                # CRITICAL FIX: Use shared memory directly instead of copying
                # This prevents doubling memory usage per worker process
                terrain_data[terrain_name] = shared_array
                
                # Keep reference to shared memory to prevent cleanup during use
                terrain_data[f"_shm_ref_{terrain_name}"] = shm
                
            except Exception as e:
                logger.warning(f"⚠️  Could not load shared terrain data for {terrain_name}: {e}")
                
        logger.info(f"✅ Loaded {len(terrain_data)} terrain arrays from shared memory")
        return terrain_data
        
    except Exception as e:
        logger.error(f"❌ Error loading shared terrain data: {e}")
        return terrain_data


# Global shared terrain manager instance
_shared_terrain_manager = None

def get_shared_terrain_manager() -> SharedTerrainManager:
    """Get the global shared terrain manager instance."""
    global _shared_terrain_manager
    if _shared_terrain_manager is None:
        _shared_terrain_manager = SharedTerrainManager()
    return _shared_terrain_manager


def cleanup_shared_terrain():
    """Clean up the global shared terrain manager."""
    global _shared_terrain_manager
    if _shared_terrain_manager is not None:
        try:
            _shared_terrain_manager.cleanup()
            _shared_terrain_manager = None
            logger.info("🧹 Global shared terrain manager cleaned up")
        except Exception as e:
            logger.warning(f"⚠️  Error cleaning up global shared terrain manager: {e}")
            _shared_terrain_manager = None


def emergency_cleanup_shared_memory():
    """Emergency cleanup of leaked shared memory objects."""
    try:
        import gc
        # Force garbage collection
        gc.collect()
        
        # Try to clean up any remaining shared memory blocks
        cleanup_shared_terrain()
        
        logger.info("🚨 Emergency shared memory cleanup completed")
        
    except Exception as e:
        logger.warning(f"⚠️  Emergency cleanup failed: {e}")
    global _shared_terrain_manager
    if _shared_terrain_manager is not None:
        _shared_terrain_manager.cleanup()
        _shared_terrain_manager = None