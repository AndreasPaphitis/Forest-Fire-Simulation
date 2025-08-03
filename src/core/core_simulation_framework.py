"""
Core Simulation Framework Module

This module provides the foundation for the forest fire simulation system, serving as the backbone
that unifies the entire framework. It establishes shared constants, data structures, and utility 
functions that ensure consistency across all other components of the simulation system.

PURPOSE:
The framework defines the core structure that enables 3D forest fire modeling with vertical vegetation
representation and realistic fire propagation. It implements a modular, extensible architecture where
specialized components build upon these fundamentals without code duplication.

KEY COMPONENTS:
- ModelConfig: Centralized configuration system serving as a single source of truth
- BaseForestModel: Abstract base class defining the common API for all fire model implementations
- CellState: Enumeration representing the possible states of cells in the simulation
- Utility functions: Memory calculation, progress tracking, and error handling

INTEGRATION POINTS:
- fire_simulation_engine.py builds upon this framework to implement fire propagation mechanics
- vegetation_data_integration.py uses these foundations to integrate LiDAR-derived data
- simulation_runner.py combines all components to execute simulations

UTILITY FUNCTIONS:
This module leverages a set of utility functions from other shared modules to provide common
capabilities across the entire simulation system. These include:
- Memory estimation (from src.utils.shared_utilities: calculate_memory_requirements)
- Progress tracking (from src.utils.shared_utilities: get_progress_iterator)
- Error handling decorators (from src.utils.shared_utilities: error_handler)
- Configuration loading/saving (from src.config.config_tools: load_config, save_config)

The modular design allows components to be developed independently while maintaining compatibility.
Parameter configurations are centralized to ensure consistency and facilitate experimentation with
different simulation scenarios.

Author: Forest Fire Model Development Team
Date: 2023
Version: 1.2
"""

# Standard imports
from enum import Enum
import math
import logging
import os
# import sys # sys is no longer needed for path manipulation here
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
import time
import traceback
import json
import pickle
import shutil
from collections import OrderedDict

# Fix import paths - remove manual sys.path manipulation
# current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)  # src directory
# project_root = os.path.dirname(parent_dir)  # project root

# # Add both src and project root to path
# if parent_dir not in sys.path:
#     sys.path.insert(0, parent_dir)
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

from src.utils.logging_utils import get_logger # Import for standardized logging
logger = get_logger(__name__) # Standardized logging

# Import shared utilities and configuration tools
from src.utils.shared_utilities import (
    log_once, 
    calculate_memory_requirements, 
    get_progress_iterator, 
    error_handler
)
from src.config.config_tools import get_global_config, ModelConfig, load_config as load_model_config, set_global_config

logger.info("Successfully imported shared utilities and config tools.")

# Constants are now primarily sourced from ModelConfig defaults via get_global_config()
# The block of constants previously defined here (BYTES_PER_CELL, MAX_STEPS, etc.) is removed.

# ===========================================================================
# CELLULAR AUTOMATA CORE ABSTRACTIONS
# ===========================================================================

class CellState(Enum):
    """
    Enumeration of possible cell states in the forest fire model.
    
    This enumeration defines the fundamental states that any cell in the 3D forest grid can have
    during simulation. These states form the basis of the cellular automata approach, where
    cell state transitions occur based on defined rules and neighboring cell interactions.
    
    States:
        UNBURNED (0): Cell contains unburned fuel, available for ignition.
                     Initial state for most cells at simulation start.
        
        BURNING (1):  Cell is currently burning and actively consuming fuel.
                     Can spread fire to neighboring cells based on fire spread rules.
                     Transitions to BURNED once fuel is consumed.
        
        BURNED (2):   Cell has completely burned and no fuel remains.
                     Terminal state; cannot ignite or spread fire to other cells.
    """
    UNBURNED = 0  # Cell contains unburned fuel
    BURNING = 1   # Cell is currently burning
    BURNED = 2    # Cell has completely burned and no fuel remains

# The BaseForestModel class definition previously here has been removed.
# The canonical BaseForestModel and its derived classes are in src.core.forest_model.py

# The create_model factory method previously here has been removed.
# The canonical create_forest_model factory is in src.core.forest_model.py

# Load configuration from file if specified in environment
if 'FOREST_MODEL_CONFIG' in os.environ:
    config_path = os.environ['FOREST_MODEL_CONFIG']
    try:
        loaded_config_instance = load_model_config(config_path) # Use the imported load_config
        set_global_config(loaded_config_instance) # Set it as the global instance
        logger.info(f"Loaded global configuration from {config_path}")
    except Exception as e:
        logger.error(f"Error loading global configuration from {config_path}: {e}")