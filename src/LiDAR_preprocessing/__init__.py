"""
LiDAR Preprocessing Package

This package contains modules for processing LiDAR data for forest fire simulation.
The preprocessing workflow consists of:
1. Height normalization (height_normalisation_all.py)
2. Normalized Return Density calculation (NRD_calculation.py)
3. Plant Area Density calculation (PAD_calculation.py)
"""

# Version information
__version__ = "1.0.0"

# Import commonly used functions for convenience
from pathlib import Path
import os

# Set up package-level variables
PACKAGE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_FILES_DIR = PACKAGE_DIR / "reference_files" 