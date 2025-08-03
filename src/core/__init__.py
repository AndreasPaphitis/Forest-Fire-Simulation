"""
Core simulation modules for forest fire modeling.

This package contains the main simulation components:
- fire_simulation_engine: Core fire spread simulation logic
- forest_model: 3D forest structure and data management  
- core_simulation_framework: Shared constants and base classes
- vegetation_data_integration: LiDAR data processing and integration
- run_fire_simulation: User-friendly simulation runner interface
"""

# Import key classes for convenient access
from .fire_simulation_engine import FireSimulationEngine
from .forest_model import ForestModel, MemoryOptimizedForestModel, create_forest_model
from .core_simulation_framework import CellState

__all__ = [
    'FireSimulationEngine',
    'ForestModel', 
    'MemoryOptimizedForestModel',
    'create_forest_model',
    'CellState'
] 