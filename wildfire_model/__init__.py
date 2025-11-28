"""
LiDAR-Integrated Cellular Automata Wildfire Model

A comprehensive wildfire simulation framework integrating LiDAR-derived vegetation
structure data with 3D cellular automata fire spread modeling, applied to the
2023 Tenerife wildfire case study.

Author: Andreas Paphitis
Institution: University of Amsterdam
Email: a.paphitis@student.uva.nl
License: MIT
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Andreas Paphitis"
__email__ = "a.paphitis@student.uva.nl"
__license__ = "MIT"

# Core modules
from .core import FireSimulation, FireSpreadModel
from .preprocessing import LidarProcessor, TerrainProcessor
from .calibration import CalibrationEngine, SensitivityAnalyzer
from .validation import ValidationFramework, MetricsCalculator
from .visualization import FireVisualizer, ResultsPlotter

# Utility modules
from .utils import DataLoader, ConfigManager, MemoryMonitor

__all__ = [
    # Core
    "FireSimulation",
    "FireSpreadModel",
    
    # Preprocessing
    "LidarProcessor", 
    "TerrainProcessor",
    
    # Calibration
    "CalibrationEngine",
    "SensitivityAnalyzer",
    
    # Validation
    "ValidationFramework",
    "MetricsCalculator",
    
    # Visualization
    "FireVisualizer",
    "ResultsPlotter",
    
    # Utils
    "DataLoader",
    "ConfigManager", 
    "MemoryMonitor",
]




















