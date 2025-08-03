"""
Utilities package for Forest Fire Simulation.

This package contains utility functions and helpers used across the simulation codebase.
"""

from src.utils.shared_utilities import (
    log_once,
    calculate_memory_requirements,
    get_progress_iterator,
    error_handler,
    optimize_gdal_io,
    monitor_memory_usage
)

# Import utility modules directly (removed try-except blocks for core components)

# File Handling utilities
from src.utils.file_handlers import FileManager

# Memory management utilities
from src.utils.memory_manager import (
    MemoryTracker,
    optimize_for_memory,
    estimate_memory_requirements,
    get_optimal_thread_count,
    MEMORY_OPTIMIZATION_LEVELS
)

# Parameter validation utilities
from src.utils.parameter_validation import (
    validator,
    ValidationContext,
    verify_extents
)

# Error handling utilities
from src.utils.error_handling import (
    handle_errors,
    log_errors,
    deprecated,
    ErrorContext,
    SimulationError,
    ModelError,
    ConfigurationError,
    DataProcessingError,
    MemoryLimitError,
    FileIOError,
    ValidationError
)

# Grid management utilities
from src.utils.grid_management import (
    GridManager,
    MultiResolutionGrid
)

# Visualization utilities
from src.utils.visualization import (
    ForestFireVisualizer,
    generate_standard_visualizations
)

# Tiling utilities
from src.utils.tiling_utils import TilingManager, SupertileManager

# LiDAR utilities
from src.utils.lidar_utils import LiDARDataManager

__all__ = [
    # From shared_utilities
    'log_once',
    'calculate_memory_requirements',
    'get_progress_iterator',
    'error_handler',
    'optimize_gdal_io',
    'monitor_memory_usage',
    
    # File handling utilities
    'FileManager',
    
    # Memory management utilities
    'MemoryTracker',
    'optimize_for_memory',
    'estimate_memory_requirements',
    'get_optimal_thread_count',
    'MEMORY_OPTIMIZATION_LEVELS',
    
    # Parameter validation utilities
    'validator',
    'ValidationContext',
    'verify_extents',
    
    # Error handling utilities
    'handle_errors',
    'log_errors',
    'deprecated',
    'ErrorContext',
    'SimulationError',
    'ModelError',
    'ConfigurationError',
    'DataProcessingError',
    'MemoryLimitError',
    'FileIOError',
    'ValidationError',
    
    # Grid management utilities
    'GridManager',
    'MultiResolutionGrid',
    
    # Visualization utilities
    'ForestFireVisualizer',
    'generate_standard_visualizations',
    
    # Tiling utilities
    'TilingManager',
    'SupertileManager',
    
    # LiDAR utilities
    'LiDARDataManager'
] 