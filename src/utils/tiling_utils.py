"""
Tiling Utilities Module

Provides standardized utilities for working with tiled data processing.
"""

import logging
import numpy as np
import math
from typing import List, Dict, Tuple, Optional, Union, Any, Callable
import time
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Top-level function for multiprocessing to avoid pickling issues with instance methods or local functions
def _execute_tile_processing_task(task_args: Tuple) -> Tuple[Tuple[int, int], Any]:
    """
    Worker function to execute the processing for a single tile.
    This function is designed to be picklable for multiprocessing.
    
    Args:
        task_args: A tuple containing (tile_info, process_func, args_for_process_func, kwargs_for_process_func)
                   where tile_info is (tx, ty, x_start, y_start, x_end, y_end).

    Returns:
        A tuple: ((tx, ty), result_of_process_func)
    """
    tile_info, process_func, func_args, func_kwargs = task_args
    tx, ty, x_start, y_start, x_end, y_end = tile_info
    
    try:
        # Ensure logger is available in the spawned process if needed by process_func
        # (This might require passing a logger configuration or re-initializing it)
        # For now, assuming process_func handles its own logging or doesn't log extensively.
        # The process_func (e.g., _process_tile_callback) expects tile_info as its primary argument after self.
        result = process_func(tile_info, *func_args, **func_kwargs) # Pass tile_info directly
        return ((tx, ty), result)
    except Exception as e:
        # It's crucial to log errors here as they occur in a separate process
        # Using a basic print for now, or ideally, a logger that's safe for multiprocessing
        print(f"Error processing tile ({tx}, {ty}) in worker: {e}") # Changed to print for safety in multiprocessing
        # Consider using logging.getLogger and configuring it if more detailed logging is needed from workers.
        # logger.error(f"Error processing tile ({tx}, {ty}) in worker: {e}") 
        return ((tx, ty), None)

class TilingManager:
    """
    Utility class for managing tiled data processing.
    
    This class handles the creation and processing of data tiles,
    including overlap calculations and memory management.
    """
    
    def __init__(self, grid_size, tile_size, overlap_ratio, num_layers, config=None, **kwargs):
        self.config = config

        if isinstance(grid_size, tuple) and len(grid_size) == 2:
            self.grid_width, self.grid_height = grid_size
        elif isinstance(grid_size, int):
            self.grid_width = self.grid_height = grid_size
        else:
            # Try to get from config as a fallback if grid_size is not immediately valid
            # This handles cases where TilingManager might be initialized before full config resolution
            if config and hasattr(config, 'grid_size'):
                cfg_grid_size = getattr(config, 'grid_size')
                if isinstance(cfg_grid_size, tuple) and len(cfg_grid_size) == 2:
                    self.grid_width, self.grid_height = cfg_grid_size
                    logger.info(f"TilingManager using grid_size {cfg_grid_size} from provided config as initial grid_size argument was {grid_size}.")
                elif isinstance(cfg_grid_size, int):
                    self.grid_width = self.grid_height = cfg_grid_size
                    logger.info(f"TilingManager using grid_size {cfg_grid_size} from provided config as initial grid_size argument was {grid_size}.")
                else:
                    logger.warning(f"Initial grid_size '{grid_size}' is invalid, and config.grid_size '{cfg_grid_size}' is also invalid. Defaulting to 0x0, expecting update.")
                    self.grid_width, self.grid_height = 0, 0 # Default to 0, expecting update
            else:
                logger.warning(f"Initial grid_size '{grid_size}' is invalid and no valid config.grid_size fallback. Defaulting to 0x0, expecting update.")
                self.grid_width, self.grid_height = 0, 0 # Default to 0, expecting update
        
        self.grid_size_tuple = (self.grid_width, self.grid_height) # Store as a consistent tuple

        self.tile_size = tile_size if tile_size is not None else (getattr(config, 'tile_size', 200) if config else 200)
        self.overlap_ratio = overlap_ratio if overlap_ratio is not None else (getattr(config, 'tile_overlap_ratio', 0.1) if config else 0.1)
        self.num_layers = num_layers if num_layers is not None else (getattr(config, 'num_layers', 10) if config else 10)
        
        logger.info(f"TilingManager pre-initialization with config: {self.config}")
        if self.grid_width == 0 or self.grid_height == 0:
            logger.warning("TilingManager initialized with zero grid dimensions. These should be updated after ForestModel initialization.")
        
        self.overlap = int(self.tile_size * self.overlap_ratio)
        
        # Calculate number of tiles
        effective_tile_size = max(1, self.tile_size - self.overlap)
        # Ensure grid_width and grid_height are non-zero for division, or default to 1 tile
        self.tiles_x = max(1, math.ceil(self.grid_width / effective_tile_size)) if self.grid_width > 0 else 1
        self.tiles_y = max(1, math.ceil(self.grid_height / effective_tile_size)) if self.grid_height > 0 else 1
        
        logger.info(f"TilingManager initialized: Grid {self.grid_width}x{self.grid_height} -> {self.tiles_x}x{self.tiles_y} tiles "
                    f"(Tile size: {self.tile_size}, Overlap: {self.overlap} cells, Effective tile size: {effective_tile_size})")
        
    def get_tile_bounds(self, tx: int, ty: int) -> Tuple[int, int, int, int]:
        """
        Get the grid coordinates for a specific tile.
        
        Args:
            tx: Tile x-index
            ty: Tile y-index
            
        Returns:
            Tuple of (x_start, y_start, x_end, y_end)
        """
        # Calculate effective tile dimensions
        effective_tile_width = self.tile_size - self.overlap
        effective_tile_height = self.tile_size - self.overlap
        
        # Calculate tile boundaries
        x_start = min(self.grid_width - 1, max(0, tx * effective_tile_width))
        y_start = min(self.grid_height - 1, max(0, ty * effective_tile_height))
        
        # Calculate end coordinates, ensuring they don't exceed grid dimensions
        x_end = min(self.grid_width, x_start + self.tile_size)
        y_end = min(self.grid_height, y_start + self.tile_size)
        
        return (x_start, y_start, x_end, y_end)
    
    def iter_tiles(self) -> List[Tuple[int, int, int, int, int, int]]:
        """
        Generate a list of all tiles with their coordinates.
        
        Returns:
            List of tuples (tx, ty, x_start, y_start, x_end, y_end)
        """
        tiles = []
        for ty in range(self.tiles_y):
            for tx in range(self.tiles_x):
                x_start, y_start, x_end, y_end = self.get_tile_bounds(tx, ty)
                
                # Only include valid tiles (with positive dimensions)
                if x_end > x_start and y_end > y_start:
                    tiles.append((tx, ty, x_start, y_start, x_end, y_end))
        
        return tiles
    
    def apply_function_to_tiles(self, process_func: Callable, *args, parallel: bool = True, 
                              num_workers: Optional[int] = None, **kwargs) -> Dict[Tuple[int, int], Any]:
        """
        Apply a function to each tile, optionally in parallel.
        
        Args:
            process_func: Function that takes (x_start, y_start, x_end, y_end, *args, **kwargs)
            *args, **kwargs: Additional arguments for process_func
            parallel: Whether to process tiles in parallel
            num_workers: Number of worker processes (None = use all CPU cores)
            
        Returns:
            Dictionary mapping (tx, ty) to function results
        """
        results = {}
        tiles_info_list = self.iter_tiles() # List of (tx, ty, x_start, y_start, x_end, y_end)
        
        # Prepare tasks for the worker function
        # Each task will be a tuple: (tile_info_tuple, process_func_callable, args_tuple, kwargs_dict)
        tasks_for_workers = [
            (tile_info, process_func, args, kwargs) for tile_info in tiles_info_list
        ]

        # Process in parallel if requested
        if parallel and len(tiles_info_list) > 1:
            if num_workers is None:
                num_workers = max(1, min(cpu_count(), len(tiles_info_list)))
            
            logger.info(f"Processing {len(tiles_info_list)} tiles in parallel with {num_workers} workers using _execute_tile_processing_task")
            
            try:
                with ProcessPoolExecutor(max_workers=num_workers) as executor:
                    # executor.map will pass each element of tasks_for_workers to _execute_tile_processing_task
                    for (tx, ty), result in executor.map(_execute_tile_processing_task, tasks_for_workers):
                        results[(tx, ty)] = result
            except Exception as e:
                logger.error(f"Exception during TilingManager.apply_function_to_tiles parallel execution: {e}")
                # Fallback or re-raise, for now, just populate results with None for all tiles
                for tx, ty, _, _, _, _ in tiles_info_list:
                    results[(tx, ty)] = None
                    
        # Process sequentially
        else:
            logger.info(f"Processing {len(tiles_info_list)} tiles sequentially")
            for tile_info in tiles_info_list:
                tx, ty, _, _, _, _ = tile_info # Unpack tx, ty for keying results, rest are in tile_info
                try:
                    # Corrected: Pass the entire tile_info tuple as the first argument
                    results[(tx, ty)] = process_func(tile_info, *args, **kwargs)
                except Exception as e:
                    logger.error(f"Error processing tile ({tx}, {ty}) sequentially: {e}")
                    results[(tx, ty)] = None
        
        return results
    
    def merge_tile_data(self, 
                        tile_data: Dict[Tuple[int, int], Any], 
                        merge_func: Optional[Callable] = None) -> np.ndarray:
        """
        Merge data from tiles into a full grid.
        
        Args:
            tile_data: Dictionary mapping (tx, ty) to tile data
            merge_func: Function to merge overlapping data (default: take latest)
            
        Returns:
            Merged grid data
        """
        # Initialize empty grid with (height, width, layers) or (height, width)
        if self.num_layers > 1:
            grid = np.zeros((self.grid_height, self.grid_width, self.num_layers), dtype=np.float32)
        else:
            grid = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)
        
        # Simple merge function for overlapping data (default: take latest)
        if merge_func is None:
            def default_merge(existing, new_data):
                return new_data
            merge_func = default_merge
        
        # Apply each tile to the grid
        for (tx, ty), data in tile_data.items():
            if data is None:
                continue
                
            x_start, y_start, x_end, y_end = self.get_tile_bounds(tx, ty)
            
            # Get existing and new data
            # Slicing based on grid being (height, width, ...)
            if self.num_layers > 1:
                existing = grid[y_start:y_end, x_start:x_end, :]
            else:
                existing = grid[y_start:y_end, x_start:x_end]
            
            # Merge data
            merged = merge_func(existing, data)
            
            # Apply merged data back to grid
            # Slicing based on grid being (height, width, ...)
            if self.num_layers > 1:
                grid[y_start:y_end, x_start:x_end, :] = merged
            else:
                grid[y_start:y_end, x_start:x_end] = merged
        
        return grid

class SupertileManager:
    """
    Utility class for managing supertiles (larger processing units for parallel computation).
    
    This class provides a higher-level abstraction above the TilingManager for processing
    very large grids using two-level tiling (supertiles containing tiles).
    """
    
    def __init__(self, 
                 grid_size: Union[int, Tuple[int, int]],
                 supertile_size: int = 500,
                 supertile_overlap_ratio: float = 0.05,
                 tile_size: int = 200,
                 tile_overlap_ratio: float = 0.1,
                 num_layers: int = 1):
        """
        Initialize the supertile manager.
        
        Args:
            grid_size: Size of the full grid (int or tuple)
            supertile_size: Size of each supertile in cells
            supertile_overlap_ratio: Ratio of supertile size for overlap
            tile_size: Size of each tile in cells
            tile_overlap_ratio: Ratio of tile size for overlap
            num_layers: Number of vertical layers (for 3D data)
        """
        # Handle grid size as tuple or single value
        if isinstance(grid_size, tuple):
            self.grid_width, self.grid_height = grid_size
        else:
            self.grid_width = self.grid_height = grid_size
        
        self.supertile_size = supertile_size
        self.supertile_overlap_ratio = supertile_overlap_ratio
        self.supertile_overlap = int(supertile_size * supertile_overlap_ratio)
        self.tile_size = tile_size
        self.tile_overlap_ratio = tile_overlap_ratio
        self.num_layers = num_layers
        
        # Create supertile manager
        self.supertile_manager = TilingManager(
            grid_size=(self.grid_width, self.grid_height),
            tile_size=supertile_size,
            overlap_ratio=supertile_overlap_ratio,
            num_layers=num_layers
        )
        
        logger.info(f"Initialized supertiling with {self.supertile_manager.tiles_x}x{self.supertile_manager.tiles_y} supertiles")
    
    def process_grid(self, 
                     process_func: Callable,
                     merge_func: Optional[Callable] = None,
                     num_workers: Optional[int] = None,
                     *args, **kwargs) -> np.ndarray:
        """
        Process the entire grid using supertiles and tiles.
        
        Args:
            process_func: Function to apply to each tile (takes x_start, y_start, x_end, y_end)
            merge_func: Function to merge overlapping data (default: take latest)
            num_workers: Number of worker processes (None = auto)
            *args, **kwargs: Additional arguments for process_func
            
        Returns:
            Processed grid data
        """
        start_time = time.time()
        logger.info(f"Starting grid processing with {self.supertile_manager.tiles_x}x{self.supertile_manager.tiles_y} supertiles")
        
        # Function to process a single supertile
        def process_supertile(x_start, y_start, x_end, y_end):
            # Create tile manager for this supertile
            tile_manager = TilingManager(
                grid_size=(x_end - x_start, y_end - y_start),
                tile_size=self.tile_size,
                overlap_ratio=self.tile_overlap_ratio,
                num_layers=self.num_layers
            )
            
            # Apply function to each tile within the supertile
            # Use sequential processing within each supertile (parallelism happens at supertile level)
            tile_results = {}
            for tx, ty, tile_x_start, tile_y_start, tile_x_end, tile_y_end in tile_manager.iter_tiles():
                # Convert supertile-relative coordinates to global coordinates
                global_x_start = x_start + tile_x_start
                global_y_start = y_start + tile_y_start
                global_x_end = x_start + tile_x_end
                global_y_end = y_start + tile_y_end
                
                # Process tile and store result
                try:
                    result = process_func(global_x_start, global_y_start, global_x_end, global_y_end, *args, **kwargs)
                    tile_results[(tx, ty)] = result
                except Exception as e:
                    logger.error(f"Error processing tile ({tx}, {ty}) in supertile: {e}")
                    tile_results[(tx, ty)] = None
            
            # Merge tiles into supertile result
            return tile_manager.merge_tile_data(tile_results, merge_func)
        
        # Process supertiles in parallel
        supertile_results = self.supertile_manager.apply_function_to_tiles(
            process_supertile,
            parallel=True,
            num_workers=num_workers
        )
        
        # Merge supertile results into final grid
        result = self.supertile_manager.merge_tile_data(supertile_results, merge_func)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Completed grid processing in {elapsed_time:.2f} seconds")
        
        return result 