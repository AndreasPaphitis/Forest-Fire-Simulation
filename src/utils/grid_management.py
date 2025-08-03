#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Grid Management Utilities

This module centralizes grid management functionality for the Forest Fire Simulation Framework.
It handles operations related to grid manipulation, multi-resolution, and coordinate transformations.
"""

import logging
import math
import numpy as np
from typing import Dict, List, Tuple, Union, Optional, Any
from pathlib import Path

# Setup logger
logger = logging.getLogger(__name__)

class GridManager:
    """
    Centralized manager for grid operations in simulations.
    
    This class handles grid creation, transformation, and multi-resolution operations
    for forest fire simulations.
    """
    
    def __init__(self, 
                grid_size: Union[int, Tuple[int, int]], 
                num_layers: int = 1,
                model_resolution: float = 1.0,
                layer_height: float = 2.0,
                use_sparse: bool = False,
                geo_bounds: Optional[Dict[str, float]] = None):
        """
        Initialize the grid manager.
        
        Args:
            grid_size: Grid size as int (square) or tuple (width, height)
            num_layers: Number of vertical layers
            model_resolution: Resolution in meters per grid cell
            layer_height: Height of each layer in meters
            use_sparse: Whether to use sparse matrices for memory efficiency
            geo_bounds: Geographic bounds as {minx, miny, maxx, maxy}
        """
        # Set grid dimensions
        if isinstance(grid_size, int):
            self.grid_width = grid_size
            self.grid_height = grid_size
        elif isinstance(grid_size, tuple) and len(grid_size) == 2:
            self.grid_width, self.grid_height = grid_size
        else:
            raise ValueError("grid_size must be an int or a tuple of (width, height)")
        
        # Set other properties
        self.num_layers = num_layers
        self.model_resolution = model_resolution
        self.layer_height = layer_height
        self.use_sparse = use_sparse
        
        # Set geographic bounds if provided
        self.geo_bounds = geo_bounds
        
        # Calculate derived properties
        self.physical_width = self.grid_width * self.model_resolution
        self.physical_height = self.grid_height * self.model_resolution
        self.physical_depth = self.num_layers * self.layer_height
        
        logger.info(f"GridManager initialized with dimensions: {self.grid_width}x{self.grid_height}x{self.num_layers}")
        logger.info(f"Physical dimensions: {self.physical_width}m x {self.physical_height}m x {self.physical_depth}m")
    
    def create_grid(self, default_value: Any = 0) -> np.ndarray:
        """
        Create a new grid with the specified dimensions.
        
        Args:
            default_value: Default value to fill the grid with
            
        Returns:
            Numpy array with grid dimensions
        """
        if self.use_sparse and default_value == 0:
            try:
                from scipy import sparse
                return sparse.lil_matrix((self.grid_height, self.grid_width, self.num_layers), dtype=type(default_value))
            except ImportError:
                logger.warning("scipy.sparse not available. Using dense array instead.")
                # Fall through to dense implementation
        
        return np.full((self.grid_height, self.grid_width, self.num_layers), default_value)
    
    def create_layer_grid(self, layer: int, default_value: Any = 0) -> np.ndarray:
        """
        Create a 2D grid for a specific layer.
        
        Args:
            layer: Layer index
            default_value: Default value to fill the grid with
            
        Returns:
            2D numpy array for the specified layer
        """
        if layer < 0 or layer >= self.num_layers:
            raise ValueError(f"Layer {layer} out of range (0-{self.num_layers-1})")
        
        if self.use_sparse and default_value == 0:
            try:
                from scipy import sparse
                return sparse.lil_matrix((self.grid_height, self.grid_width), dtype=type(default_value))
            except ImportError:
                # Fall through to dense implementation
                pass
        
        return np.full((self.grid_height, self.grid_width), default_value)
    
    def world_to_grid(self, x: float, y: float, z: float = 0.0) -> Tuple[int, int, int]:
        """
        Convert world coordinates to grid coordinates.
        
        Args:
            x: X coordinate in world space (meters)
            y: Y coordinate in world space (meters)
            z: Z coordinate in world space (meters)
            
        Returns:
            Tuple of (grid_x, grid_y, layer)
        """
        # Check if geographic bounds are provided
        if self.geo_bounds is not None:
            # Convert from geographic to world coordinates first
            x, y = self.geo_to_world(x, y)
        
        # Convert world coordinates to grid coordinates
        grid_x = int(x / self.model_resolution)
        grid_y = int(y / self.model_resolution)
        layer = int(z / self.layer_height)
        
        # Clamp to grid bounds
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))
        layer = max(0, min(layer, self.num_layers - 1))
        
        return (grid_x, grid_y, layer)
    
    def grid_to_world(self, grid_x: int, grid_y: int, layer: int = 0) -> Tuple[float, float, float]:
        """
        Convert grid coordinates to world coordinates.
        
        Args:
            grid_x: X coordinate in grid space
            grid_y: Y coordinate in grid space
            layer: Layer index
            
        Returns:
            Tuple of (world_x, world_y, world_z) in meters
        """
        # Convert grid coordinates to world coordinates (cell centers)
        world_x = (grid_x + 0.5) * self.model_resolution
        world_y = (grid_y + 0.5) * self.model_resolution
        world_z = (layer + 0.5) * self.layer_height
        
        return (world_x, world_y, world_z)
    
    def geo_to_world(self, geo_x: float, geo_y: float) -> Tuple[float, float]:
        """
        Convert geographic coordinates to world coordinates.
        
        Args:
            geo_x: X coordinate in geographic space (e.g., longitude)
            geo_y: Y coordinate in geographic space (e.g., latitude)
            
        Returns:
            Tuple of (world_x, world_y) in meters
        """
        if self.geo_bounds is None:
            raise ValueError("Geographic bounds not set")
        
        # Extract bounds
        minx = self.geo_bounds['minx']
        miny = self.geo_bounds['miny']
        maxx = self.geo_bounds['maxx']
        maxy = self.geo_bounds['maxy']
        
        # Calculate normalized position (0-1) within bounds
        norm_x = (geo_x - minx) / (maxx - minx)
        norm_y = (geo_y - miny) / (maxy - miny)
        
        # Convert to world coordinates
        world_x = norm_x * self.physical_width
        world_y = norm_y * self.physical_height
        
        return (world_x, world_y)
    
    def world_to_geo(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        Convert world coordinates to geographic coordinates.
        
        Args:
            world_x: X coordinate in world space (meters)
            world_y: Y coordinate in world space (meters)
            
        Returns:
            Tuple of (geo_x, geo_y) in geographic space
        """
        if self.geo_bounds is None:
            raise ValueError("Geographic bounds not set")
        
        # Extract bounds
        minx = self.geo_bounds['minx']
        miny = self.geo_bounds['miny']
        maxx = self.geo_bounds['maxx']
        maxy = self.geo_bounds['maxy']
        
        # Calculate normalized position (0-1) within world space
        norm_x = world_x / self.physical_width
        norm_y = world_y / self.physical_height
        
        # Convert to geographic coordinates
        geo_x = minx + norm_x * (maxx - minx)
        geo_y = miny + norm_y * (maxy - miny)
        
        return (geo_x, geo_y)
    
    def is_valid_grid_point(self, grid_x: int, grid_y: int, layer: int = 0) -> bool:
        """
        Check if a grid point is within valid bounds.
        
        Args:
            grid_x: X coordinate in grid space
            grid_y: Y coordinate in grid space
            layer: Layer index
            
        Returns:
            True if the point is valid, False otherwise
        """
        return (0 <= grid_x < self.grid_width and 
                0 <= grid_y < self.grid_height and 
                0 <= layer < self.num_layers)
    
    def get_neighbors(self, 
                    grid_x: int, 
                    grid_y: int, 
                    layer: int = 0, 
                    include_diagonals: bool = True,
                    include_vertical: bool = True) -> List[Tuple[int, int, int]]:
        """
        Get neighboring grid cells.
        
        Args:
            grid_x: X coordinate in grid space
            grid_y: Y coordinate in grid space
            layer: Layer index
            include_diagonals: Whether to include diagonal neighbors
            include_vertical: Whether to include neighbors from adjacent layers
            
        Returns:
            List of (x, y, layer) tuples for valid neighbors
        """
        neighbors = []
        
        # Horizontal and vertical neighbors
        directions = [(0, 1, 0), (1, 0, 0), (0, -1, 0), (-1, 0, 0)]
        
        # Add diagonal neighbors if requested
        if include_diagonals:
            directions.extend([(1, 1, 0), (1, -1, 0), (-1, 1, 0), (-1, -1, 0)])
        
        # Add vertical neighbors if requested
        if include_vertical and self.num_layers > 1:
            directions.extend([(0, 0, 1), (0, 0, -1)])
        
        # Check each direction
        for dx, dy, dl in directions:
            nx, ny, nl = grid_x + dx, grid_y + dy, layer + dl
            
            # Add if valid
            if self.is_valid_grid_point(nx, ny, nl):
                neighbors.append((nx, ny, nl))
        
        return neighbors
    
    def create_multi_resolution_grid(self, levels: int, base_value: Any = 0) -> List[np.ndarray]:
        """
        Create a multi-resolution grid.
        
        Note: This function has been simplified to always use a single resolution level.
        The levels parameter is kept for compatibility but ignored.
        
        Args:
            levels: Ignored parameter kept for compatibility
            base_value: Default value to fill the grid with
            
        Returns:
            List containing a single grid at the base resolution
        """
        # Create a single grid at base resolution, ignoring levels parameter
        grids = [self.create_grid(default_value=base_value)]
        
        # Log that multi-resolution is disabled
        logger.info("Multi-resolution support is disabled. Using single resolution grid.")
        
        return grids
    
    def upsample(self, coarse_grid: np.ndarray, method: str = 'nearest') -> np.ndarray:
        """
        Upsample a coarse grid to the next finer resolution.
        
        Args:
            coarse_grid: Grid to upsample
            method: Upsampling method ('nearest', 'bilinear', 'average')
            
        Returns:
            Upsampled grid
        """
        # Get coarse grid dimensions
        c_height, c_width, c_layers = coarse_grid.shape
        
        # Calculate fine grid dimensions
        f_width = c_width * 2
        f_height = c_height * 2
        
        # Create fine grid
        if self.use_sparse and np.count_nonzero(coarse_grid) / coarse_grid.size < 0.1:
            try:
                from scipy import sparse
                fine_grid = sparse.lil_matrix((f_height, f_width, c_layers), 
                                            dtype=coarse_grid.dtype)
            except ImportError:
                fine_grid = np.zeros((f_height, f_width, c_layers), dtype=coarse_grid.dtype)
        else:
            fine_grid = np.zeros((f_height, f_width, c_layers), dtype=coarse_grid.dtype)
        
        # Upsample each layer
        for layer in range(c_layers):
            # Get 2D slices
            coarse_layer = coarse_grid[:, :, layer]
            fine_layer = fine_grid[:, :, layer]
            
            # Apply upsampling method
            if method == 'nearest':
                # Nearest neighbor upsampling
                for cy in range(c_height):
                    for cx in range(c_width):
                        value = coarse_layer[cy, cx]
                        fine_layer[cy*2:(cy+1)*2, cx*2:(cx+1)*2] = value
            
            elif method == 'bilinear':
                # Bilinear upsampling
                for cy in range(c_height-1):
                    for cx in range(c_width-1):
                        # Get values at corners
                        v00 = coarse_layer[cy, cx]
                        v01 = coarse_layer[cy, cx+1]
                        v10 = coarse_layer[cy+1, cx]
                        v11 = coarse_layer[cy+1, cx+1]
                        
                        # Compute interpolated values
                        fine_layer[cy*2, cx*2] = v00
                        fine_layer[cy*2, cx*2+1] = (v00 + v01) / 2
                        fine_layer[cy*2+1, cx*2] = (v00 + v10) / 2
                        fine_layer[cy*2+1, cx*2+1] = (v00 + v01 + v10 + v11) / 4
                
                # Handle border cases
                for cy in range(c_height-1):
                    fine_layer[cy*2, (c_width-1)*2] = coarse_layer[cy, c_width-1]
                    fine_layer[cy*2+1, (c_width-1)*2] = (coarse_layer[cy, c_width-1] + 
                                                       coarse_layer[cy+1, c_width-1]) / 2
                    fine_layer[cy*2, (c_width-1)*2+1] = coarse_layer[cy, c_width-1]
                    fine_layer[cy*2+1, (c_width-1)*2+1] = (coarse_layer[cy, c_width-1] + 
                                                         coarse_layer[cy+1, c_width-1]) / 2
                
                for cx in range(c_width-1):
                    fine_layer[(c_height-1)*2, cx*2] = coarse_layer[c_height-1, cx]
                    fine_layer[(c_height-1)*2, cx*2+1] = (coarse_layer[c_height-1, cx] + 
                                                        coarse_layer[c_height-1, cx+1]) / 2
                    fine_layer[(c_height-1)*2+1, cx*2] = coarse_layer[c_height-1, cx]
                    fine_layer[(c_height-1)*2+1, cx*2+1] = (coarse_layer[c_height-1, cx] + 
                                                          coarse_layer[c_height-1, cx+1]) / 2
                
                # Handle corner
                fine_layer[(c_height-1)*2, (c_width-1)*2] = coarse_layer[c_height-1, c_width-1]
                fine_layer[(c_height-1)*2, (c_width-1)*2+1] = coarse_layer[c_height-1, c_width-1]
                fine_layer[(c_height-1)*2+1, (c_width-1)*2] = coarse_layer[c_height-1, c_width-1]
                fine_layer[(c_height-1)*2+1, (c_width-1)*2+1] = coarse_layer[c_height-1, c_width-1]
            
            elif method == 'average':
                # Each fine cell gets the same value as its parent coarse cell
                for cy in range(c_height):
                    for cx in range(c_width):
                        fine_layer[cy*2:(cy+1)*2, cx*2:(cx+1)*2] = coarse_layer[cy, cx]
            
            else:
                raise ValueError(f"Unknown upsampling method: {method}")
            
            # Update fine grid layer
            fine_grid[:, :, layer] = fine_layer
        
        return fine_grid
    
    def downsample(self, fine_grid: np.ndarray, method: str = 'average') -> np.ndarray:
        """
        Downsample a fine grid to the next coarser resolution.
        
        Args:
            fine_grid: Grid to downsample
            method: Downsampling method ('max', 'min', 'average', 'median')
            
        Returns:
            Downsampled grid
        """
        # Get fine grid dimensions
        f_height, f_width, f_layers = fine_grid.shape
        
        # Calculate coarse grid dimensions
        c_width = max(1, f_width // 2)
        c_height = max(1, f_height // 2)
        
        # Create coarse grid
        coarse_grid = np.zeros((c_height, c_width, f_layers), dtype=fine_grid.dtype)
        
        # Downsample each layer
        for layer in range(f_layers):
            # Get 2D slices
            fine_layer = fine_grid[:, :, layer]
            coarse_layer = coarse_grid[:, :, layer]
            
            # Apply downsampling method
            for cy in range(c_height):
                for cx in range(c_width):
                    # Get the 2x2 block from the fine grid
                    y_slice = slice(cy*2, min(cy*2+2, f_height))
                    x_slice = slice(cx*2, min(cx*2+2, f_width))
                    block = fine_layer[y_slice, x_slice]
                    
                    # Compute the downsampled value based on the method
                    if method == 'max':
                        coarse_layer[cy, cx] = np.max(block)
                    elif method == 'min':
                        coarse_layer[cy, cx] = np.min(block)
                    elif method == 'average':
                        coarse_layer[cy, cx] = np.mean(block)
                    elif method == 'median':
                        coarse_layer[cy, cx] = np.median(block)
                    else:
                        raise ValueError(f"Unknown downsampling method: {method}")
            
            # Update coarse grid layer
            coarse_grid[:, :, layer] = coarse_layer
        
        return coarse_grid
    
    def align_to_grid(self, grid: np.ndarray, x_offset: float, y_offset: float) -> np.ndarray:
        """
        Align a grid with a specified offset.
        
        Args:
            grid: Grid to align
            x_offset: X offset in grid cells
            y_offset: Y offset in grid cells
            
        Returns:
            Aligned grid
        """
        # Get grid dimensions
        height, width, layers = grid.shape
        
        # Create aligned grid
        aligned_grid = np.zeros_like(grid)
        
        # Calculate integer offsets
        x_int = int(x_offset)
        y_int = int(y_offset)
        
        # Calculate fractional offsets for interpolation
        x_frac = x_offset - x_int
        y_frac = y_offset - y_int
        
        # Shift with interpolation for each layer
        for layer in range(layers):
            layer_grid = grid[:, :, layer]
            
            for y in range(height):
                for x in range(width):
                    # Calculate source coordinates
                    src_x = x - x_int
                    src_y = y - y_int
                    
                    # Skip if out of bounds
                    if src_x < 0 or src_x >= width-1 or src_y < 0 or src_y >= height-1:
                        continue
                    
                    # Bilinear interpolation
                    x0, y0 = int(src_x), int(src_y)
                    x1, y1 = min(x0 + 1, width - 1), min(y0 + 1, height - 1)
                    
                    # Get corner values
                    v00 = layer_grid[y0, x0]
                    v01 = layer_grid[y0, x1]
                    v10 = layer_grid[y1, x0]
                    v11 = layer_grid[y1, x1]
                    
                    # Interpolate
                    dx = src_x - x0
                    dy = src_y - y0
                    
                    # Interpolate along x
                    v0 = v00 * (1 - dx) + v01 * dx
                    v1 = v10 * (1 - dx) + v11 * dx
                    
                    # Interpolate along y
                    value = v0 * (1 - dy) + v1 * dy
                    
                    aligned_grid[y, x, layer] = value
        
        return aligned_grid

class MultiResolutionGrid:
    """
    Manager for grid management with compatibility for multi-resolution API.
    
    Note: This class has been simplified to always use a single resolution.
    The API is maintained for compatibility with existing code.
    """
    
    def __init__(self, 
                base_manager: GridManager, 
                levels: int = 3,
                default_value: Any = 0):
        """
        Initialize a grid with compatibility for multi-resolution API.
        
        Args:
            base_manager: Base grid manager for the resolution
            levels: Ignored parameter kept for compatibility
            default_value: Default value for all grid cells
        """
        self.base_manager = base_manager
        self.levels = 1  # Always set to 1 regardless of passed value
        
        # Create grid (always single-resolution)
        self.grids = base_manager.create_multi_resolution_grid(1, default_value)
        
        # Calculate properties for the single level
        self.level_properties = [{
            'width': base_manager.grid_width,
            'height': base_manager.grid_height,
            'resolution': base_manager.model_resolution
        }]
        
        logger.info("MultiResolutionGrid created with single resolution level (multi-resolution disabled)")
    
    def get_grid(self, level: int) -> np.ndarray:
        """
        Get the grid at a specific resolution level.
        
        Args:
            level: Resolution level (only 0 is valid)
            
        Returns:
            Grid at the base resolution
        """
        if level != 0:
            logger.warning(f"Requested grid level {level} but multi-resolution is disabled. Returning base grid (level 0).")
        
        return self.grids[0]
    
    def propagate_upward(self, method: str = 'average') -> None:
        """
        Compatibility method for upward propagation.
        
        This method is kept for API compatibility but has no effect.
        
        Args:
            method: Ignored parameter
        """
        logger.info("propagate_upward called but multi-resolution is disabled. No effect.")
        pass
    
    def propagate_downward(self, method: str = 'bilinear') -> None:
        """
        Compatibility method for downward propagation.
        
        This method is kept for API compatibility but has no effect.
        
        Args:
            method: Ignored parameter
        """
        logger.info("propagate_downward called but multi-resolution is disabled. No effect.")
        pass 