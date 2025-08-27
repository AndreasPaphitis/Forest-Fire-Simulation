#!/usr/bin/env python3
"""
Sparse terrain data utilities for ultra-memory-efficient parallel processing.

This module provides functionality to load terrain data in sparse format and share it
across multiple worker processes, dramatically reducing memory usage.
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

# Check for SciPy sparse support
try:
    from scipy.sparse import csr_matrix, csc_matrix, lil_matrix
    from scipy.sparse import save_npz, load_npz
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from src.utils.logging_utils import get_logger
logger = get_logger(__name__)

class SparseTerrainManager:
    """
    Manages sparse terrain data across multiple processes.
    
    This class handles loading terrain data in sparse format and sharing it across
    worker processes using Python's shared_memory module.
    """
    
    def __init__(self):
        self.shared_blocks = {}
        self.terrain_shapes = {}
        self.terrain_dtypes = {}
        self.sparse_formats = {}
        self.is_loaded = False
        
    def load_terrain_data(self, preprocessed_dir: str, target_shape: Tuple[int, int], 
                         fire_bounds: Optional[Tuple[float, float, float, float]] = None,
                         sparsity_threshold: float = 0.1) -> bool:
        """
        Load terrain data into sparse shared memory for ultra-efficient multi-process access.
        
        Args:
            preprocessed_dir: Directory containing preprocessed terrain files
            target_shape: Target shape for terrain data (height, width)
            fire_bounds: Optional fire bounds [minx, miny, maxx, maxy] in meters (EPSG:25828)
            sparsity_threshold: Threshold for converting to sparse (0.1 = 10% non-zero values)
            
        Returns:
            True if successful, False otherwise
        """
        if not HAS_SCIPY:
            logger.error("❌ SciPy required for sparse terrain - install: pip install scipy")
            return False
            
        # Check for shared memory availability
        if not HAS_SHARED_MEMORY:
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            logger.warning(f"⚠️  Shared memory not available on Python {python_version}. Requires Python 3.8+.")
            logger.warning("   Falling back to individual terrain loading (higher memory usage)")
            return False
        
        # Clean up any existing shared memory files first
        self._cleanup_existing_shared_memory()
            
        try:
            preprocessed_path = Path(preprocessed_dir)
            
            # Load terrain metadata for proper coordinate transformation
            metadata_file = preprocessed_path / "metadata.json"
            terrain_transform = None
            terrain_crs = None
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    terrain_crs = metadata.get('crs', 'EPSG:25828')
                    transform_str = metadata.get('transform', '')
                    
                    # Parse transform string
                    import re
                    transform_lines = transform_str.strip().split('\n')
                    if len(transform_lines) >= 2:
                        # Parse pixel sizes and origin
                        line1 = transform_lines[0].strip()
                        line2 = transform_lines[1].strip()
                        
                        # Extract values using regex
                        pixel_x_match = re.search(r'(\d+\.?\d*)', line1)
                        origin_x_match = re.search(r'(\d+\.?\d*)', line1.split(',')[-1])
                        pixel_y_match = re.search(r'(-?\d+\.?\d*)', line2)
                        origin_y_match = re.search(r'(\d+\.?\d*)', line2.split(',')[-1])
                        
                        if all([pixel_x_match, origin_x_match, pixel_y_match, origin_y_match]):
                            terrain_transform = {
                                'pixel_size_x': float(pixel_x_match.group(1)),
                                'pixel_size_y': abs(float(pixel_y_match.group(1))),  # Take absolute value
                                'origin_x': float(origin_x_match.group(1)),
                                'origin_y': float(origin_y_match.group(1))
                            }
                            logger.info(f"✅ Terrain transform parsed: {terrain_transform}")
                        else:
                            logger.warning(f"⚠️  Could not parse terrain transform: {transform_str}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to parse terrain metadata: {e}")
            
            # Load terrain files
            terrain_files = {
                'elevation': 'elevation.npy',
                'slope': 'slope.npy', 
                'aspect': 'aspect.npy',
                'barranco_mask': 'barranco_mask.npy',
                'barranco_directions': 'barranco_directions.npy',
                'depression_mask': 'depression_mask.npy',
                'wind_channeling_mask': 'wind_channeling_mask.npy',
                'wind_amplification': 'wind_amplification.npy',
                'wind_direction_modification': 'wind_direction_modification.npy'
            }
            
            total_sparse_memory = 0
            total_dense_memory = 0
            
            for terrain_type, filename in terrain_files.items():
                file_path = preprocessed_path / filename
                if not file_path.exists():
                    logger.warning(f"⚠️  Terrain file not found: {filename}")
                    continue
                    
                # Load terrain data
                terrain_data = np.load(str(file_path))
                total_dense_memory += terrain_data.nbytes
                
                # Apply subsetting and resampling (same logic as before)
                if fire_bounds and terrain_transform:
                    # Calculate fire bounds in terrain grid coordinates
                    fire_minx, fire_miny, fire_maxx, fire_maxy = fire_bounds
                    
                    # Simplified fix for NumPy array comparison
                    pixel_size_x_val = float(pixel_size_x) if pixel_size_x is not None else 0
                    pixel_size_y_val = float(pixel_size_y) if pixel_size_y is not None else 0

                    if pixel_size_x_val == 0 or pixel_size_y_val == 0:
                        raise ValueError("Terrain transform has invalid pixel sizes")

                    fire_min_col = int((fire_minx - terrain_transform['origin_x']) / terrain_transform['pixel_size_x'])
                    fire_max_col = int((fire_maxx - terrain_transform['origin_x']) / terrain_transform['pixel_size_x'])
                    fire_min_row = int((terrain_transform['origin_y'] - fire_maxy) / terrain_transform['pixel_size_y'])
                    fire_max_row = int((terrain_transform['origin_y'] - fire_miny) / terrain_transform['pixel_size_y'])
                    
                    # Calculate required subset size for proper resampling
                    target_height, target_width = target_shape
                    required_subset_height = int(target_height / 0.25)  # 0.25 = 5m/20m resampling factor
                    required_subset_width = int(target_width / 0.25)

                    # Calculate fire area center
                    fire_center_col = (fire_min_col + fire_max_col) // 2
                    fire_center_row = (fire_min_row + fire_max_row) // 2

                    # Use required subset size
                    subset_height = required_subset_height
                    subset_width = required_subset_width
                    
                    # Calculate start positions
                    start_row = fire_center_row - (subset_height // 2)
                    start_col = fire_center_col - (subset_width // 2)

                    # Ensure we don't exceed bounds
                    if start_row < 0: start_row = 0
                    if start_col < 0: start_col = 0
                    if start_row + subset_height > terrain_data.shape[0]:
                        start_row = terrain_data.shape[0] - subset_height
                    if start_col + subset_width > terrain_data.shape[1]:
                        start_col = terrain_data.shape[1] - subset_width
                    
                    end_row = start_row + subset_height
                    end_col = start_col + subset_width
                    
                    terrain_data = terrain_data[start_row:end_row, start_col:end_col]
                    
                    # Resample from 5m to 20m resolution
                    # Simplified fix for NumPy array comparison
                    pixel_size_x = terrain_transform.get('pixel_size_x') if terrain_transform else None
                    is_5m_resolution = float(pixel_size_x) == 5.0 if pixel_size_x is not None else False

                    if is_5m_resolution:
                        from scipy.ndimage import zoom
                        resample_factor = 5.0 / 20.0  # 0.25
                        terrain_data = zoom(terrain_data, resample_factor, order=1)
                    else:
                        # Fallback to estimated percentages
                        full_height, full_width = terrain_data.shape
                        target_height, target_width = target_shape
                            
                    fire_center_row = int(full_height * 0.35)
                    fire_center_col = int(full_width * 0.45)
                    
                    # Simplified fix for NumPy array comparison
                    pixel_size_x = terrain_transform.get('pixel_size_x') if terrain_transform else None
                    is_5m_resolution = float(pixel_size_x) == 5.0 if pixel_size_x is not None else False

                    subset_height = int(target_height / 0.25) if is_5m_resolution else target_height
                    subset_width = int(target_width / 0.25) if is_5m_resolution else target_width
                    
                    start_row = fire_center_row - (subset_height // 2)
                    start_col = fire_center_col - (subset_width // 2)
                    
                    if start_row < 0: start_row = 0
                    if start_col < 0: start_col = 0
                    if start_row + subset_height > terrain_data.shape[0]:
                        start_row = terrain_data.shape[0] - subset_height
                    if start_col + subset_width > terrain_data.shape[1]:
                        start_col = terrain_data.shape[1] - subset_width
                    
                    end_row = start_row + subset_height
                    end_col = start_col + subset_width
                        
                    terrain_data = terrain_data[start_row:end_row, start_col:end_col]
                    
                    # Resample if needed
                    # Simplified fix for NumPy array comparison
                    pixel_size_x = terrain_transform.get('pixel_size_x') if terrain_transform else None
                    is_5m_resolution = float(pixel_size_x) == 5.0 if pixel_size_x is not None else False

                    if is_5m_resolution:
                        from scipy.ndimage import zoom
                        resample_factor = 5.0 / 20.0
                        terrain_data = zoom(terrain_data, resample_factor, order=1)
                
                # CRITICAL: Convert to sparse format
                logger.info(f"🔄 Converting {terrain_type} to sparse format...")
                
                # Calculate sparsity
                non_zero_ratio = np.count_nonzero(terrain_data) / terrain_data.size
                logger.info(f"   Non-zero ratio: {non_zero_ratio:.3f} ({non_zero_ratio*100:.1f}%)")
                
                # Convert to sparse format
                if non_zero_ratio < sparsity_threshold or terrain_type in ['barranco_mask', 'depression_mask', 'wind_channeling_mask']:
                    # Use CSR format for efficient access
                    sparse_terrain = csr_matrix(terrain_data)
                    sparse_format = 'csr'
                    memory_reduction = (1 - sparse_terrain.data.nbytes / terrain_data.nbytes) * 100
                    logger.info(f"✅ {terrain_type} converted to CSR sparse: {memory_reduction:.1f}% memory reduction")
                else:
                    # Keep as dense for high-density data
                    sparse_terrain = terrain_data
                    sparse_format = 'dense'
                    memory_reduction = 0
                    logger.info(f"ℹ️  {terrain_type} kept as dense (high density: {non_zero_ratio*100:.1f}%)")
                
                # Store in shared memory
                terrain_name = terrain_type
                
                if sparse_format == 'csr':
                    # Store sparse matrix components
                    data_name = f"terrain_{terrain_name}_data"
                    indices_name = f"terrain_{terrain_name}_indices"
                    indptr_name = f"terrain_{terrain_name}_indptr"
                    
                    # Create shared memory for sparse components
                    data_shm = shared_memory.SharedMemory(create=True, size=sparse_terrain.data.nbytes, name=data_name)
                    indices_shm = shared_memory.SharedMemory(create=True, size=sparse_terrain.indices.nbytes, name=indices_name)
                    indptr_shm = shared_memory.SharedMemory(create=True, size=sparse_terrain.indptr.nbytes, name=indptr_name)
                    
                    # Copy data to shared memory
                    data_array = np.ndarray(sparse_terrain.data.shape, dtype=sparse_terrain.data.dtype, buffer=data_shm.buf)
                    indices_array = np.ndarray(sparse_terrain.indices.shape, dtype=sparse_terrain.indices.dtype, buffer=indices_shm.buf)
                    indptr_array = np.ndarray(sparse_terrain.indptr.shape, dtype=sparse_terrain.indptr.dtype, buffer=indptr_shm.buf)
                    
                    data_array[:] = sparse_terrain.data[:]
                    indices_array[:] = sparse_terrain.indices[:]
                    indptr_array[:] = sparse_terrain.indptr[:]
                
                # Store references
                self.shared_blocks[f"{terrain_name}_data"] = data_shm
                self.shared_blocks[f"{terrain_name}_indices"] = indices_shm
                self.shared_blocks[f"{terrain_name}_indptr"] = indptr_shm
                
                total_sparse_memory += sparse_terrain.data.nbytes + sparse_terrain.indices.nbytes + sparse_terrain.indptr.nbytes
                
            else:
                # Store dense array
                nbytes = sparse_terrain.nbytes
                shm = shared_memory.SharedMemory(create=True, size=nbytes, name=f"terrain_{terrain_name}")
                
                shared_array = np.ndarray(sparse_terrain.shape, dtype=sparse_terrain.dtype, buffer=shm.buf)
                shared_array[:] = sparse_terrain[:]
                
                self.shared_blocks[terrain_name] = shm
                total_sparse_memory += nbytes
                
                # Store metadata
                self.terrain_shapes[terrain_name] = terrain_data.shape
                self.terrain_dtypes[terrain_name] = terrain_data.dtype
                self.sparse_formats[terrain_name] = sparse_format
                
                logger.debug(f"✅ Loaded {terrain_name} ({sparse_format}): {terrain_data.shape}")
            
            # Log memory savings
            total_memory_reduction = (1 - total_sparse_memory / total_dense_memory) * 100
            logger.info(f"🎯 Sparse terrain memory optimization:")
            logger.info(f"   Dense memory: {total_dense_memory/1024/1024:.1f} MB")
            logger.info(f"   Sparse memory: {total_sparse_memory/1024/1024:.1f} MB")
            logger.info(f"   Memory reduction: {total_memory_reduction:.1f}%")
            
            self.is_loaded = True
            logger.info(f"✅ All terrain data loaded into sparse shared memory successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load terrain data into sparse shared memory: {e}")
            self._cleanup_existing_shared_memory()
            return False
    
    def get_shared_terrain_info(self) -> Dict[str, Any]:
        """
        Get information about shared sparse terrain data for worker processes.
        
        Returns:
            Dictionary containing shared memory names, shapes, dtypes, and sparse formats
        """
        return {
            'shared_names': {name: shm.name for name, shm in self.shared_blocks.items()},
            'shapes': self.terrain_shapes.copy(),
            'dtypes': {name: str(dtype) for name, dtype in self.terrain_dtypes.items()},
            'sparse_formats': self.sparse_formats.copy(),
            'is_loaded': self.is_loaded
        }
    
    def cleanup(self):
        """Clean up shared memory blocks."""
        if not self.shared_blocks:
            logger.debug("No shared memory blocks to clean up")
            return
            
        for name, shm in list(self.shared_blocks.items()):
            try:
                if hasattr(shm, 'name') and hasattr(shm, 'size'):
                    shm.close()
                    shm.unlink()
                    logger.info(f"🧹 Cleaned up shared memory for {name}")
                else:
                    logger.warning(f"⚠️  Invalid shared memory block for {name}")
            except FileNotFoundError:
                logger.debug(f"Shared memory block {name} already cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error cleaning up shared memory for {name}: {e}")
        
        self.shared_blocks.clear()
        self.terrain_shapes.clear()
        self.terrain_dtypes.clear()
        self.sparse_formats.clear()
        self.is_loaded = False
    
    def _cleanup_existing_shared_memory(self):
        """Clean up any existing shared memory files that might conflict."""
        if not HAS_SHARED_MEMORY:
            return
            
        # List of terrain names that might have existing shared memory
        terrain_names = [
            'elevation', 'slope', 'aspect', 'barranco_mask', 
            'barranco_directions', 'depression_mask', 
            'wind_channeling_mask', 'wind_amplification', 
            'wind_direction_modification'
        ]
        
        for terrain_name in terrain_names:
            # Clean up both dense and sparse shared memory
            for suffix in ['', '_data', '_indices', '_indptr']:
                try:
                    existing_shm = shared_memory.SharedMemory(name=f"terrain_{terrain_name}{suffix}")
                    existing_shm.close()
                    existing_shm.unlink()
                    logger.debug(f"🧹 Cleaned up existing shared memory: terrain_{terrain_name}{suffix}")
                except FileNotFoundError:
                    pass
                except Exception as e:
                    logger.debug(f"Could not clean up terrain_{terrain_name}{suffix}: {e}")

# Global instance for shared terrain manager
_shared_terrain_manager_instance = None

def get_shared_terrain_manager():
    """
    Get or create a global shared terrain manager instance.
        
    Returns:
        SparseTerrainManager instance
    """
    global _shared_terrain_manager_instance
    if _shared_terrain_manager_instance is None:
        _shared_terrain_manager_instance = SparseTerrainManager()
    return _shared_terrain_manager_instance

def reset_shared_terrain_logging():
    """
    Reset shared terrain logging for worker processes.
    This function is called by worker processes to reset logging state.
    """
    # This is a no-op function for compatibility with the grid search
    # The actual logging reset is handled by the logger configuration
    pass

def load_shared_terrain_data(shared_info: Dict[str, Any]) -> Optional[Dict[str, np.ndarray]]:
    """
    Load terrain data from shared memory using shared info.
    
    Args:
        shared_info: Dictionary containing shared memory information
        
    Returns:
        Dictionary of terrain arrays if successful, None otherwise
    """
    if not HAS_SHARED_MEMORY:
        logger.warning("Shared memory not available")
        return None
        
    try:
        terrain_data = {}
        
        # Load terrain data from shared memory
        for terrain_type in ['elevation', 'slope', 'aspect', 'barranco_mask', 
                           'barranco_directions', 'depression_mask', 
                           'wind_channeling_mask', 'wind_amplification', 
                           'wind_direction_modification']:
            
            if terrain_type not in shared_info.get('sparse_formats', {}):
                continue
                
            sparse_format = shared_info['sparse_formats'][terrain_type]
            shape = shared_info['shapes'][terrain_type]
            dtype_str = shared_info['dtypes'][terrain_type]
            
            if sparse_format == 'csr':
                # Load sparse matrix components
                data_name = shared_info['shared_names'][f"{terrain_type}_data"]
                indices_name = shared_info['shared_names'][f"{terrain_type}_indices"]
                indptr_name = shared_info['shared_names'][f"{terrain_type}_indptr"]
                
                # Attach to shared memory
                data_shm = shared_memory.SharedMemory(name=data_name)
                indices_shm = shared_memory.SharedMemory(name=indices_name)
                indptr_shm = shared_memory.SharedMemory(name=indptr_name)
                
                # Create numpy arrays from shared memory
                data_array = np.ndarray(shape=(len(data_shm.buf)//4,), dtype=np.float32, buffer=data_shm.buf)
                indices_array = np.ndarray(shape=(len(indices_shm.buf)//4,), dtype=np.int32, buffer=indices_shm.buf)
                indptr_array = np.ndarray(shape=(len(indptr_shm.buf)//4,), dtype=np.int32, buffer=indptr_shm.buf)
                
                # Reconstruct sparse matrix
                from scipy.sparse import csr_matrix
                terrain_data[terrain_type] = csr_matrix((data_array, indices_array, indptr_array), shape=shape)
                
            else:
                # Load dense array
                shared_name = shared_info['shared_names'][terrain_type]
                shm = shared_memory.SharedMemory(name=shared_name)
                
                # Create numpy array from shared memory
                terrain_data[terrain_type] = np.ndarray(shape, dtype=np.dtype(dtype_str), buffer=shm.buf)
        
        logger.info(f"✅ Loaded {len(terrain_data)} terrain arrays from shared memory")
        return terrain_data
        
    except Exception as e:
        logger.error(f"❌ Failed to load shared terrain data: {e}")
        return None