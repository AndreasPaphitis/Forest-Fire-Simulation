#!/usr/bin/env python
# ======================================================================
# FIRE SIMULATION ENGINE
# ======================================================================
"""
Fire Simulation Engine Module

This module implements the core fire propagation algorithms of the forest fire simulation system.
It builds upon the abstract foundation provided by core_simulation_framework.py to create a
complete 3D cellular automata model for realistic forest fire simulation.

PURPOSE:
The fire simulation engine implements the primary algorithms for simulating wildfire behavior
in three-dimensional forest environments. It extends the abstract base classes defined in the
core simulation framework to provide a complete, functional simulation model that captures
complex fire dynamics across varied terrain and vegetation structures.

KEY CAPABILITIES:
1. VERTICAL FOREST STRUCTURE
   - Implementation of a multi-layered forest representation
   - Vertical connectivity mechanisms between different height strata
   - Layer-specific fuel consumption and fire behavior

2. FIRE SPREAD MECHANICS
   - Sophisticated horizontal spread algorithms with probabilistic components
   - Vertical fire propagation through direct flame spread (primarily upward)
   - Ember generation and transport systems for long-distance fire spread
   - Advanced wind effects on directional spread probabilities

3. ENVIRONMENTAL FACTORS
   - Spatially heterogeneous wind patterns affected by topography
   - Fuel moisture representation and its effects on ignition probability
   - Terrain effects on fire spread through slope-based modifications
   - Variable meteorological conditions and their influence on fire behavior

4. VISUALIZATION AND ANALYSIS
   - 2D and 3D visualization tools for fire progression analysis
   - Interactive animation capabilities for educational and research purposes
   - Statistical analysis tools for quantifying fire behavior metrics

INTEGRATION WITH OTHER MODULES:
- Depends on core_simulation_framework.py for foundational data structures
- Compatible with vegetation_data_integration.py for processing LiDAR-derived fuel data
- Used by simulation_runner.py for executing complete fire simulations

This module contains the primary ForestModel class that implements the BaseForestModel interface
defined in the core framework, providing a complete implementation of all required methods for
running forest fire simulations with realistic fire behavior.

Author: Forest Fire Model Development Team
Date: 2023
Version: 2.0
"""
# ======================================================================

import os
import sys
import numpy as np
import logging
import time
import glob
import json
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D
from enum import Enum
from typing import List, Dict, Tuple, Optional, Union, Callable, Any

# Standard library imports
import random
import re
import traceback
from pathlib import Path  # For cross-platform path handling
from datetime import datetime
import math
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial

# Scientific and visualization libraries
import numpy as np               # For numerical and array operations
import matplotlib.pyplot as plt  # For visualization of the forest grid
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.lines import Line2D
from matplotlib import animation
from matplotlib.widgets import Button
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D  # For 3D visualization
from scipy.ndimage import zoom
from scipy.interpolate import griddata
from skimage.transform import resize
from osgeo import gdal

# Import from base module for consistent configuration and functionality
try:
    from core_simulation_framework import (
        BaseForestModel, CellState, ModelConfig,
        calculate_memory_requirements, get_progress_iterator, error_handler
    )
    # Get forest model specific configuration
    config = ModelConfig.get_module_config('forest_model')
    
    # Extract parameters from centralized configuration
    MODEL_RESOLUTION = config.get('MODEL_RESOLUTION', 5.0)
    LAYER_HEIGHT_METERS = config.get('LAYER_HEIGHT_METERS', 2.0)
    DEFAULT_NUM_LAYERS = config.get('DEFAULT_NUM_LAYERS', 10)
    MIN_FUEL_VALUE = config.get('MIN_FUEL_VALUE', 0.1)
    MAX_FUEL_VALUE = config.get('MAX_FUEL_VALUE', 10.0)
    DEFAULT_FUEL_MOISTURE = config.get('DEFAULT_FUEL_MOISTURE', 0.3)
    MAX_STEPS = config.get('MAX_STEPS', 100)
    STORE_FULL_STATES = config.get('STORE_FULL_STATES', False)
    HORIZONTAL_SPREAD_PROBABILITY = config.get('HORIZONTAL_SPREAD_PROBABILITY', 0.4)
    VERTICAL_SPREAD_PROBABILITY = config.get('VERTICAL_SPREAD_PROBABILITY', 0.3)
    DOWNWARD_SPREAD_PROBABILITY = config.get('DOWNWARD_SPREAD_PROBABILITY', 0.15)
    EMBER_GENERATION_PROBABILITY = config.get('EMBER_GENERATION_PROBABILITY', 0.02)
    EMBER_IGNITION_PROBABILITY = config.get('EMBER_IGNITION_PROBABILITY', 0.3)
    WIND_INFLUENCE = config.get('WIND_INFLUENCE', 0.5)
    SLOPE_INFLUENCE = config.get('SLOPE_INFLUENCE', 0.3)
    
    # Flag to indicate successful import
    BASE_MODULE_IMPORTED = True
    
except ImportError:
    # Fall back to locally defined constants if base module is not available
    BASE_MODULE_IMPORTED = False
    
    # Define CellState enum locally if not imported
    from enum import Enum
    class CellState(Enum):
        """Enumeration of possible cell states in the forest model."""
        UNBURNED = 0  # Cell contains unburned fuel
        BURNING = 1   # Cell is currently burning
        BURNED = 2    # Cell has completely burned and no fuel remains
    
    # Default configuration values
    MODEL_RESOLUTION = 5.0
    LAYER_HEIGHT_METERS = 2.0
    DEFAULT_NUM_LAYERS = 10
    MIN_FUEL_VALUE = 0.1
    MAX_FUEL_VALUE = 10.0
    DEFAULT_FUEL_MOISTURE = 0.3
    MAX_STEPS = 100
    STORE_FULL_STATES = False
    HORIZONTAL_SPREAD_PROBABILITY = 0.4
    VERTICAL_SPREAD_PROBABILITY = 0.3
    DOWNWARD_SPREAD_PROBABILITY = 0.15
    EMBER_GENERATION_PROBABILITY = 0.02
    EMBER_IGNITION_PROBABILITY = 0.3
    WIND_INFLUENCE = 0.5
    SLOPE_INFLUENCE = 0.3
    
    # Minimal error handler implementation if base module is not available
    def error_handler(func=None, debug=False):
        """
        Simple error handling decorator.
        """
        if func is None:
            def decorator(f):
                def wrapper(*args, **kwargs):
                    try:
                        return f(*args, **kwargs)
                    except Exception as e:
                        print(f"Error in {f.__name__}: {str(e)}")
                        if debug:
                            print(traceback.format_exc())
                        raise
                return wrapper
            return decorator
        
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"Error in {func.__name__}: {str(e)}")
                if debug:
                    print(traceback.format_exc())
                raise
        return wrapper

    # Minimal progress iterator if base module is not available
    def get_progress_iterator(iterable, desc=None, **kwargs):
        try:
            from tqdm import tqdm
            return tqdm(iterable, desc=desc, **kwargs)
        except ImportError:
            print(f"Processing {desc}...")
            return iterable

# Load TiledLiDARIntegration on demand to avoid circular imports
TiledLiDARIntegration = None

# Set random seed for reproducibility
np.random.seed(42)

# Suppress GDAL warnings
gdal.UseExceptions()
gdal.PushErrorHandler('CPLQuietErrorHandler')

print("\n===== Starting CELLULAR AUTOMATA THESIS.py =====")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Script path: {os.path.abspath(__file__)}")
print(f"Using base module: {BASE_MODULE_IMPORTED}")

# =====================================================================
# USER CONFIGURATION PARAMETERS
# =====================================================================
# Additional configuration parameters not provided by the base module
# =====================================================================

# ---------------------------------------------------------------------
# 1. FOREST MODEL STRUCTURE AND RESOLUTION
# ---------------------------------------------------------------------
# Grid dimensions
GRID_SIZE = 100                  # Number of cells in each dimension (x and y)
AREA_SIZE_METERS = None          # Optional: area size in meters (overrides GRID_SIZE if specified)

# Vertical forest structure
NUM_LAYERS = DEFAULT_NUM_LAYERS  # Number of vertical layers

# ---------------------------------------------------------------------
# 2. FUEL LOAD AND MOISTURE PARAMETERS
# ---------------------------------------------------------------------
# Options for fuel load and fuel moisture initialization

# Fuel load initialization method
FUEL_LOAD_METHOD = 'random'      # Options: 'random', 'constant', 'lidar_rasters', 'tiled_lidar'
                                 # 'random': Random values between MIN_FUEL_VALUE and MAX_FUEL_VALUE
                                 # 'constant': Constant value specified by CONSTANT_FUEL_VALUE
                                 # 'lidar_rasters': Use LiDAR-derived rasters
                                 # 'tiled_lidar': Use tiled LiDAR approach (preferred for large areas)

# Fuel load parameters for different methods
CONSTANT_FUEL_VALUE = 1.0        # Fuel load value if using 'constant' method
MIN_FUEL_VALUE = 0.1             # Minimum fuel value for random initialization
MAX_FUEL_VALUE = 10.0            # Maximum fuel value for random initialization

# Fuel moisture parameter (0.0 - 1.0)
FUEL_MOISTURE = DEFAULT_FUEL_MOISTURE  # Higher values make fire spread more difficult

# ---------------------------------------------------------------------
# 3. FILE PATHS AND DIRECTORY SETTINGS FOR LIDAR DATA
# ---------------------------------------------------------------------
# These settings are used when FUEL_LOAD_METHOD is 'lidar_rasters' or 'tiled_lidar'

# Base directory containing LiDAR-derived rasters
LIDAR_RASTER_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'lidar_rasters')

# Area name (subfolder within LIDAR_RASTER_BASE_DIR)
LIDAR_AREA_NAME = 'sample_area'

# Height bin size used in LiDAR processing
LIDAR_HEIGHT_BIN_SIZE = 2.0

# Full path to the LiDAR area
LIDAR_AREA_PATH = os.path.join(LIDAR_RASTER_BASE_DIR, LIDAR_AREA_NAME)

# Minimum and maximum PAD (Plant Area Density) values
MIN_PAD_VALUE = 0.0
MAX_PAD_VALUE = 10.0

# Tiled LiDAR processing parameters
TILE_SIZE = 100                  # Size of each tile in grid cells
TILE_OVERLAP = 5                 # Overlap between tiles in grid cells
MAX_MEMORY_GB = 4.0              # Maximum memory to use for processing (GB)

# ---------------------------------------------------------------------
# 4. INITIAL IGNITION PARAMETERS
# ---------------------------------------------------------------------
# Control where fires start in the model

# Ignition method
IGNITION_METHOD = 'corner'       # Options: 'center', 'corner', 'random', 'multiple', 'coordinates'

# Number of random ignition points (for 'random' and 'multiple' methods)
NUM_IGNITION_POINTS = 3

# Specific coordinates for ignition (for 'coordinates' method)
# Format: [(x1, y1, z1), (x2, y2, z2), ...]
IGNITION_COORDINATES = [(10, 10, 0), (50, 50, 0)]

# ---------------------------------------------------------------------
# 5. FIRE SPREAD PARAMETERS
# ---------------------------------------------------------------------
# Control how fire spreads through the model

# Base fire spread probabilities
HORIZONTAL_SPREAD_PROBABILITY = 0.4  # Probability of fire spreading horizontally
VERTICAL_SPREAD_PROBABILITY = 0.3    # Probability of fire spreading upward
DOWNWARD_SPREAD_PROBABILITY = 0.15   # Probability of fire spreading downward

# Ember generation and spotting parameters
EMBER_GENERATION_PROBABILITY = 0.02  # Probability of generating embers from burning cells
EMBER_TRAVEL_DISTANCE = 5           # Maximum travel distance of embers in cells
EMBER_IGNITION_PROBABILITY = 0.3    # Probability of embers igniting new fires

# ---------------------------------------------------------------------
# 6. ENVIRONMENTAL FACTORS
# ---------------------------------------------------------------------
# Environmental conditions that affect fire behavior

# Wind parameters
TRADE_WIND_DIRECTION = 45        # Wind direction in degrees (0 = north, 90 = east)
TRADE_WIND_STRENGTH = 0.5        # Wind strength (0.0 - 1.0)
WIND_GUST_FRACTION = 0.2         # Wind gusts as fraction of wind strength
WIND_INFLUENCE = 0.5             # How much wind affects fire spread (0.0 - 1.0)

# Terrain parameters
USE_DEM = False                 # Whether to use Digital Elevation Model
DEM_FILE_PATH = os.path.join(LIDAR_AREA_PATH, 'dem.tif')  # Path to DEM file
SLOPE_INFLUENCE = 0.3           # How much slope affects fire spread (0.0 - 1.0)

# ---------------------------------------------------------------------
# 7. SIMULATION PARAMETERS
# ---------------------------------------------------------------------
# Control the duration and behavior of the simulation

# Maximum number of simulation steps
MAX_STEPS = 100                 # Maximum number of steps to run

# Stopping conditions
STOP_WHEN_FIRE_EXTINGUISHED = True  # Stop if all fires are extinguished
MIN_ACTIVE_CELLS_FRACTION = 0.01    # Minimum fraction of active cells to continue

# Performance and memory optimization
STORE_FULL_STATES = False        # Whether to store all intermediate states (memory intensive)

# ---------------------------------------------------------------------
# 8. VISUALIZATION PARAMETERS
# ---------------------------------------------------------------------
# Control how the simulation is visualized

# Display options
SHOW_VISUALIZATION = True        # Whether to show visualization during simulation
SAVE_VISUALIZATION = True        # Whether to save visualization to files
VISUALIZATION_INTERVAL = 5       # Number of steps between visualization updates

# Output directory for saved visualizations
VISUALIZATION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs', 
                                'visualizations', datetime.now().strftime('%Y%m%d_%H%M%S'))

# Color maps for different cell states
UNBURNED_COLOR = 'darkgreen'
BURNING_COLOR = 'red'
BURNED_COLOR = 'black'
BACKGROUND_COLOR = 'white'

# 3D visualization parameters
SHOW_3D_VISUALIZATION = True     # Whether to show 3D visualization
LAYER_SPACING = 1.0              # Vertical spacing between layers in 3D view
POINT_SIZE = 20                  # Size of points in 3D visualization

# Visualization scalars for 3D view
VERTICAL_EXAGGERATION = 2.0      # Exaggeration factor for vertical dimension

# Animation parameters
CREATE_ANIMATION = True          # Whether to create animation of fire spread
ANIMATION_INTERVAL = 200         # Milliseconds between animation frames
SAVE_ANIMATION = True            # Whether to save animation to file
ANIMATION_FILENAME = 'fire_spread_animation.mp4'  # Filename for saved animation
DPI = 100                        # Resolution for saved images

# ---------------------------------------------------------------------
# 9. WIND AND TERRAIN PARAMETERS
# ---------------------------------------------------------------------
# Parameters for wind simulation and terrain effects

# Default wind parameters
TRADE_WIND_DIRECTION = 0.0       # Direction in radians (0 = East, π/2 = North)
TRADE_WIND_STRENGTH = 0.5        # Wind strength (0-1)
WIND_INFLUENCE = 0.5             # How strongly wind affects fire spread (0-1)

# Terrain effects
SLOPE_INFLUENCE = 0.3            # How strongly slope affects fire spread (0-1)
TERRAIN_EFFECT_STRENGTH = 0.5    # Impact of terrain on local wind patterns
BARRANCO_AMPLIFICATION = 1.5     # Wind amplification in ravines/channels

# ---------------------------------------------------------------------
# 10. EMBER TRANSPORT PARAMETERS
# ---------------------------------------------------------------------
# Parameters for long-distance fire spread through embers

EMBER_VERTICAL_DISTANCE = 3      # Maximum vertical distance (layers)
EMBER_IGNITION_PROB = 0.6        # Base ignition probability (0-1)
EMBERS_PER_CELL = 3              # Maximum embers per burning cell
EMBER_VERTICAL_PENALTY = 0.2     # Probability reduction per layer traveled
EMBER_MIN_PROBABILITY = 0.3      # Minimum probability after penalties
EMBER_FUEL_MULTIPLIER = 0.5      # Fuel load effect on ember ignition

# ---------------------------------------------------------------------
# 11. IGNITION PARAMETERS
# ---------------------------------------------------------------------
# How and where to start the fire

# Ignition method
# Options: 'center', 'random', 'edge'
IGNITION_METHOD = 'center'       # How to set initial ignition points

# Method-specific parameters
RANDOM_IGNITION_COUNT = 3        # Number of random ignition points
RANDOM_IGNITION_LAYERS = [0]     # Layers for random ignition
EDGE_IGNITION_PERCENT = 0.2      # Percentage of edge to ignite
CENTER_IGNITION_RADIUS = 3       # Radius of center ignition in cells

# ---------------------------------------------------------------------
# 12. SIMULATION CONTROL
# ---------------------------------------------------------------------
# Parameters controlling the simulation execution

MAX_STEPS = 20                 # Maximum simulation steps
STOP_AT_EDGE = True              # Whether to stop when fire reaches edge

# ---------------------------------------------------------------------
# 13. VISUALIZATION AND OUTPUT
# ---------------------------------------------------------------------
# How to display and save results

# Visualization options
# 'static_2d', 'static_3d', 'animation', 'animation_3d', 'interactive'
VISUALIZATION_MODE = 'animation_3d' # Type of visualization to generate

# Animation settings
ANIMATION_FRAME_INTERVAL_MS = 200  # Milliseconds between animation frames
ANIMATION_DISPLAY_LAYER = "composite"  # "composite" or layer number like "0" for bottom layer
ANIMATION_SHOW_STATS = True  # Whether to show statistics on the animation
ANIMATION_OPTIMIZE_STORAGE = False  # Use memory-efficient but less accurate visualization
STORE_FULL_STATES = True  # Store complete grid states (more accurate animation but more memory)
ANIMATION_3D_ELEVATION_FACTOR = 1.5  # Height factor for 3D animation (higher = more vertical separation)
ANIMATION_3D_VIEW_ANGLE = (30, 45)  # Initial view angle for 3D animation (elevation, azimuth) in degrees

# Output settings
SAVE_RESULTS = True             # Whether to save results to disk
RESULTS_DIR = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\Model Output\Simulation Results"  # Directory for saved results
VISUALIZATION_OUTPUT_DIR = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\Model Output\Simulation Results"  # For visualizations

# ---------------------------------------------------------------------
# 14. PARALLEL PROCESSING
# ---------------------------------------------------------------------
# Control parallel processing options

USE_PARALLEL_PROCESSING = True    # Whether to use parallel processing for fire spread
NUM_PARALLEL_WORKERS = None       # Number of worker processes (None = use all available CPU cores)
PARALLEL_TILE_SIZE = 50           # Size of each tile for parallel processing
PARALLEL_TILE_OVERLAP = 2         # Overlap between adjacent tiles to handle boundary effects

# END OF USER CONFIGURATION SECTION
# =====================================================================
# DO NOT MODIFY CODE BELOW THIS POINT UNLESS YOU KNOW WHAT YOU'RE DOING
# =====================================================================

# ======================================================================
# FILE PATHS AND DIRECTORIES
# ======================================================================
# NOTE: All user-configurable parameters have been moved to the 
# USER CONFIGURATION PARAMETERS section at the top of this file.
# ======================================================================

# ======================================================================
# INTERNAL CLASSES AND FUNCTIONS
# ======================================================================
# The following code implements the forest fire simulation model
# for initializing and updating the model.
# ======================================================================

# ======================================================================
# 1. CONFIGURATION PARAMETERS
# ======================================================================
# NOTE: All user-configurable parameters have been moved to the 
# USER CONFIGURATION PARAMETERS section at the top of this file.
# ======================================================================

# Internal state tracking enums and constants (not user configurable)
class CellState(Enum):
    """Enumeration of possible cell states in the forest model."""
    UNBURNED = 0  # Cell contains unburned fuel
    BURNING = 1   # Cell is currently burning
    BURNED = 2    # Cell has completely burned and no fuel remains

# ======================================================================
# 2. FOREST MODEL CLASS
# ======================================================================
# The ForestModel class encapsulates the entire forest fire simulation,
# including all environmental parameters, state variables, and methods
# for initializing and updating the model.
# ======================================================================

class ForestModel:
    """
    3D cellular automata model for simulating forest fire behavior.
    
    This model represents a 3D forest as a grid where each cell has
    properties like fuel load, burning status, and temperature.
    The model simulates fire spread through the forest based on
    physical rules and environmental conditions.
    """
    
    def __init__(self, grid_size=100, num_layers=10, layer_height_meters=LAYER_HEIGHT_METERS):
        """
        Initialize the forest model with specified dimensions.
        
        Args:
            grid_size (int or tuple): Size of the grid, either as a single integer for square grids
                                     or a tuple (width, height) for rectangular grids
            num_layers (int): Number of vertical layers
            layer_height_meters (float): Height of each layer in meters
        """
        # Process grid size - allow both int and tuple
        if isinstance(grid_size, tuple):
            self.grid_size_x, self.grid_size_y = grid_size
        else:
            self.grid_size_x = self.grid_size_y = grid_size
            
        # Use the larger dimension for compatibility with older code
        self.grid_size = max(self.grid_size_x, self.grid_size_y)
        
        # Set vertical dimensions
        self.num_layers = num_layers
        self.layer_height_meters = layer_height_meters
        
        # Calculate physical cell dimensions
        self.cell_area_meters = MODEL_RESOLUTION * MODEL_RESOLUTION
        
        # Initialize ember tracking
        self.active_embers = []  # List to store active embers and their properties
        self.ember_trajectories = []  # Track full ember paths for visualization
        self.ember_ignitions = np.zeros((self.grid_size_x, self.grid_size_y), dtype=np.int32)  # Count ember-caused ignitions
        
        # Create initial grid layers (3D grid represented as a list of 2D layers)
        # Each layer is a 2D numpy array where:
        # 0 = unburned, 1 = burning, 2 = burned
        self.layers = [np.zeros((grid_size, grid_size), dtype=np.int8) for _ in range(num_layers)]
        
        # Create fuel load matrix (3D grid)
        # Values range from 0 (no fuel) to 1 (maximum fuel)
        self.fuel_load = np.zeros((num_layers, grid_size, grid_size), dtype=np.float32)
        
        # Set initial default fuel load (can be overridden later)
        for z in range(num_layers):
            # Default pattern: decrease with height
            height_factor = 1.0 - (z / num_layers)
            self.fuel_load[z, :, :] = DEFAULT_FUEL_LOAD * height_factor
            
        # Set fuel consumption rates for each layer
        # Lower layers (surface) burn faster than upper layers (canopy)
        self.fuel_consumption_rates = np.zeros(num_layers, dtype=np.float32)
        for z in range(num_layers):
            # Default: decrease with height (surface fuels burn faster)
            height_factor = 1.0 - (z / num_layers) * 0.5  # Reduce by up to 50%
            self.fuel_consumption_rates[z] = BASE_FUEL_CONSUMPTION_RATE * height_factor
            
        # Initialize wind fields
        # Direction is in radians (0 = East, π/2 = North, etc.)
        # Speed is normalized (0-1)
        self.wind_direction = np.zeros((grid_size, grid_size), dtype=np.float32)
        self.wind_speed = np.zeros((grid_size, grid_size), dtype=np.float32)
        
        # Initialize wind vector components
        # These are derived from direction and speed
        self.wind_u = np.zeros((grid_size, grid_size), dtype=np.float32)  # East-West component
        self.wind_v = np.zeros((grid_size, grid_size), dtype=np.float32)  # North-South component
        
        # Set default fuel moisture
        self.fuel_moisture = DEFAULT_FUEL_MOISTURE
        
        # Set default vertical connectivity
        # This represents how easily fire can spread upward
        self.vertical_connectivity = np.ones(num_layers, dtype=np.float32) * VERTICAL_CONNECTIVITY
        
        # Initialize fire spread parameters
        self.fire_params = {
            'k': SIGMOID_STEEPNESS,      # Steepness of sigmoid curve
            'threshold': SIGMOID_THRESHOLD,  # Critical number of burning neighbors needed
            'spread_threshold': SPREAD_THRESHOLD  # Minimum probability to consider ignition
        }
        
        # History of grid states (for animation)
        self.history = []
        self.store_full_states = False
        
        # Statistics counters
        self.time_step = 0
        
        print(f"Forest model initialized with grid size {grid_size}x{grid_size}")
        print(f"Cell resolution: {MODEL_RESOLUTION}m")
        print(f"Total area: {self.cell_area_meters * grid_size**2 / 1000000:.2f} km²")
        print(f"Vertical extent: {self.num_layers} layers, {self.num_layers * self.layer_height_meters}m total height")
        
    def set_ignition(self, x, y, z):
        """
        Set ignition at a specific cell in the forest.
        
        Args:
            x (int): X-coordinate
            y (int): Y-coordinate
            z (int): Z-coordinate (layer)
        """
        if 0 <= x < self.grid_size and 0 <= y < self.grid_size and 0 <= z < self.num_layers:
            self.layers[z][y, x] = CellState.BURNING.value
            print(f"Ignition set at position ({x}, {y}, {z})")
        else:
            print(f"Invalid ignition position: ({x}, {y}, {z})")

    def record_state(self):
        """
        Record the current state of the forest for history and visualization.
        
        This method captures:
        - Cell state counts and areas for each layer
        - Active ember trajectories for visualization
        - Full grid states if requested (store_full_states=True)
        
        The history can be used for analysis and visualization after simulation.
        """
        # Create a state dictionary with counters for each state
        state = {
            'time_step': self.time_step,
            'unburned_count': [],
            'burning_count': [],
            'burned_count': [],
            'unburned_area': [],
            'burning_area': [],
            'burned_area': []
        }
        
        # Count states in each layer
        for z in range(self.num_layers):
            layer = self.layers[z]
            unburned = np.sum(layer == CellState.UNBURNED.value)
            burning = np.sum(layer == CellState.BURNING.value)
            burned = np.sum(layer == CellState.BURNED.value)
            
            # Store counts
            state['unburned_count'].append(int(unburned))
            state['burning_count'].append(int(burning))
            state['burned_count'].append(int(burned))
            
            # Calculate areas
            state['unburned_area'].append(unburned * self.cell_area_meters)
            state['burning_area'].append(burning * self.cell_area_meters)
            state['burned_area'].append(burned * self.cell_area_meters)
        
        # Add total counts
        state['total_unburned'] = sum(state['unburned_count'])
        state['total_burning'] = sum(state['burning_count'])
        state['total_burned'] = sum(state['burned_count'])
        
        # Add total areas
        state['total_unburned_area'] = sum(state['unburned_area'])
        state['total_burning_area'] = sum(state['burning_area'])
        state['total_burned_area'] = sum(state['burned_area'])
        
        # Store active ember trajectories
        state['active_embers'] = [ember.copy() for ember in self.active_embers]
        
        # Store number of ember ignitions this step
        state['ember_count'] = len(self.active_embers)
        state['ember_ignitions'] = sum(1 for ember in self.active_embers if ember['ignited'])
        
        # Optionally store full grid states (memory intensive but enables accurate animation)
        if self.store_full_states:
            # Make a deep copy of each layer to prevent reference issues
            grid_states = []
            for z in range(self.num_layers):
                grid_states.append(self.layers[z].copy())
            state['grid_states'] = grid_states
            
            # Also store a composite view for convenience
            composite = np.zeros((self.grid_size, self.grid_size), dtype=np.int8)
            for z in range(self.num_layers):
                composite = np.maximum(composite, self.layers[z])
            state['composite'] = composite
        
        # Add the state to history
        self.history.append(state)
        
    def run_simulation(self, max_steps=MAX_STEPS, stop_when_fire_extinguished=STOP_WHEN_FIRE_EXTINGUISHED):
        """
        Run the forest fire simulation for a specified number of steps or until the fire is extinguished.
        
        Parameters:
            max_steps (int): Maximum number of steps to simulate
            stop_when_fire_extinguished (bool): Whether to stop simulation when fire is extinguished
        
        Returns:
            dict: Simulation results and statistics
        """
        # Reset statistics
        self.simulation_results = {
            'total_steps': 0,
            'peak_active_cells': 0,
            'peak_active_step': 0,
            'total_cells_burned': 0,
            'final_active_cells': 0,
            'final_burned_cells': 0,
            'final_unburned_cells': 0,
            'final_active_fraction': 0.0,
            'final_burned_fraction': 0.0,
            'step_history': []
        }
        
        # Run the simulation
        for step in range(1, max_steps + 1):
            # Update one step
            stats = self.update_step()
            self.simulation_results['step_history'].append(stats)
            
            # Update peak stats
            if stats['active_cells'] > self.simulation_results['peak_active_cells']:
                self.simulation_results['peak_active_cells'] = stats['active_cells']
                self.simulation_results['peak_active_step'] = step
            
            # Stop if fire is extinguished and flag is set
            if stop_when_fire_extinguished and stats['active_cells'] == 0:
                print(f"Fire extinguished after {step} steps.")
                break
        
        # Update final statistics
        self.simulation_results['total_steps'] = self.current_step
        self.simulation_results['final_active_cells'] = self.active_cell_count
        self.simulation_results['final_burned_cells'] = self.burned_cell_count
        self.simulation_results['final_unburned_cells'] = self.unburned_cell_count
        self.simulation_results['final_active_fraction'] = self.active_cell_count / self.total_cells if self.total_cells > 0 else 0
        self.simulation_results['final_burned_fraction'] = self.burned_cell_count / self.total_cells if self.total_cells > 0 else 0
        self.simulation_results['total_cells_burned'] = self.active_cell_count + self.burned_cell_count
        
        # Print simulation summary
        print("\nSimulation Summary:")
        print(f"Total steps: {self.simulation_results['total_steps']}")
        print(f"Peak active cells: {self.simulation_results['peak_active_cells']} " 
              f"({self.simulation_results['peak_active_cells'] / self.total_cells * 100:.2f}%) " 
              f"at step {self.simulation_results['peak_active_step']}")
        print(f"Total cells burned: {self.simulation_results['total_cells_burned']} " 
              f"({self.simulation_results['total_cells_burned'] / self.total_cells * 100:.2f}%)")
        
        return self.simulation_results
    
    def visualize_fire_state(self, layer=None, state_type='current', ax=None, show=True, 
                             title=None, colormap='viridis', figsize=(10, 8)):
        """
        Visualize the current fire state for a specific layer or aggregated across layers.
        
        Parameters:
            layer (int): Layer to visualize (None = aggregate all layers)
            state_type (str): 'current', 'initial', or a specific step number
            ax (matplotlib.axes.Axes): Axes to plot on (None = create new)
            show (bool): Whether to show the plot
            title (str): Title for the plot (None = auto-generate)
            colormap (str): Matplotlib colormap to use
            figsize (tuple): Figure size for new figure
            
        Returns:
            tuple: Figure and axes objects
        """
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        
        # Determine the state to visualize
        if state_type == 'current':
            state = self.states
            step_text = f"Step {self.current_step}"
        elif state_type == 'initial' and len(self.cell_state_history) > 0:
            state = self.cell_state_history[0]
            step_text = "Initial State"
        elif isinstance(state_type, int) and 0 <= state_type < len(self.cell_state_history):
            state = self.cell_state_history[state_type]
            step_text = f"Step {state_type}"
        else:
            state = self.states
            step_text = f"Step {self.current_step}"
        
        # Create a figure if needed
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.figure
        
        # Prepare the visualization data
        if layer is not None:
            # Visualize a specific layer
            vis_data = state[:, :, layer].copy()
            layer_text = f"Layer {layer}"
        else:
            # Aggregate across all layers
            # For each x,y position, use the maximum state across all layers
            vis_data = np.max(state, axis=2)
            layer_text = "All Layers (Aggregated)"
        
        # Create custom colormap for fire states
        colors = [(0.0, 'forestgreen'),     # UNBURNED: Green
                 (0.33, 'yellow'),          # Transition
                 (0.66, 'red'),             # BURNING: Red
                 (1.0, 'black')]            # BURNED: Black
        
        cmap = mcolors.LinearSegmentedColormap.from_list('fire_cmap', colors)
        
        # Plot the data
        im = ax.imshow(vis_data.T, origin='lower', cmap=cmap, vmin=0, vmax=2)
        
        # Add a colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_ticks([0, 1, 2])
        cbar.set_ticklabels(['Unburned', 'Burning', 'Burned'])
        
        # Set title
        if title is None:
            title = f"Forest Fire Simulation - {step_text}, {layer_text}"
        ax.set_title(title)
        
        # Set labels
        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        
        # Show the plot if requested
        if show:
            plt.tight_layout()
            plt.show()
        
        return fig, ax
    
    def visualize_3d_fire(self, step=None, fig=None, show=True, title=None, 
                          colormap='viridis', figsize=(12, 10), alpha=0.5):
        """
        Create a 3D visualization of the fire state.
        
        Parameters:
            step (int): Step to visualize (None = current)
            fig (matplotlib.figure.Figure): Figure to plot on (None = create new)
            show (bool): Whether to show the plot
            title (str): Title for the plot (None = auto-generate)
            colormap (str): Matplotlib colormap to use
            figsize (tuple): Figure size for new figure
            alpha (float): Opacity for 3D voxels
            
        Returns:
            matplotlib.figure.Figure: Figure object
        """
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        
        # Determine the state to visualize
        if step is None:
            state = self.states
            step_text = f"Step {self.current_step}"
        elif step == 'initial' and len(self.cell_state_history) > 0:
            state = self.cell_state_history[0]
            step_text = "Initial State"
        elif isinstance(step, int) and 0 <= step < len(self.cell_state_history):
            state = self.cell_state_history[step]
            step_text = f"Step {step}"
        else:
            state = self.states
            step_text = f"Step {self.current_step}"
        
        # Create a figure if needed
        if fig is None:
            fig = plt.figure(figsize=figsize)
            ax = fig.add_subplot(111, projection='3d')
        else:
            ax = fig.gca(projection='3d')
        
        # Clear the current axes
        ax.clear()
        
        # Set title
        if title is None:
            title = f"3D Forest Fire Visualization - {step_text}"
        ax.set_title(title)
        
        # Set labels
        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        ax.set_zlabel("Z Coordinate (Layer)")
        
        # Define colors for each state
        colors = {
            CellState.UNBURNED: 'green',
            CellState.BURNING: 'red',
            CellState.BURNED: 'black'
        }
        
        # Downsample if the grid is too large
        max_display_size = 30
        if self.grid_size_x > max_display_size or self.grid_size_y > max_display_size:
            print(f"Grid is too large for detailed 3D visualization. Downsampling...")
            # Determine downsampling factor
            factor_x = max(1, self.grid_size_x // max_display_size)
            factor_y = max(1, self.grid_size_y // max_display_size)
            factor_z = max(1, self.num_layers // (max_display_size // 2))
            
            # Downsample the grid
            x_indices = np.arange(0, self.grid_size_x, factor_x)
            y_indices = np.arange(0, self.grid_size_y, factor_y)
            z_indices = np.arange(0, self.num_layers, factor_z)
        else:
            x_indices = np.arange(self.grid_size_x)
            y_indices = np.arange(self.grid_size_y)
            z_indices = np.arange(self.num_layers)
        
        # Plot each state separately
        for cell_state in [CellState.BURNING, CellState.BURNED]:
            # Find cells with this state
            x, y, z = np.where(state[np.ix_(x_indices, y_indices, z_indices)] == cell_state)
            
            # Scale coordinates back to original grid
            if self.grid_size_x > max_display_size or self.grid_size_y > max_display_size:
                x = x_indices[x]
                y = y_indices[y]
                z = z_indices[z]
            
            # Plot if any cells have this state
            if len(x) > 0:
                ax.scatter(x, y, z, c=colors[cell_state], alpha=alpha, label=str(cell_state))
        
        # Add a legend
        ax.legend()
        
        # Set axis limits
        ax.set_xlim(0, self.grid_size_x)
        ax.set_ylim(0, self.grid_size_y)
        ax.set_zlim(0, self.num_layers)
        
        # Show the plot if requested
        if show:
            plt.tight_layout()
            plt.show()
        
        return fig

    def _calculate_wind_factor(self, from_x, from_y, to_x, to_y):
        """
        Calculate the wind factor for fire spread.
        
        Parameters:
            from_x, from_y (int): Coordinates of the source cell
            to_x, to_y (int): Coordinates of the target cell
        
        Returns:
            float: Wind factor (1.0 = no effect, >1.0 = increased spread, <1.0 = decreased spread)
        """
        # If wind strength is zero, return neutral factor
        if self.wind_strength == 0:
            return 1.0
        
        # Calculate direction of spread
        dx = to_x - from_x
        dy = to_y - from_y
        
        # Calculate angle of spread (in degrees)
        if dx == 0 and dy == 0:
            return 1.0
        
        spread_angle = math.degrees(math.atan2(dy, dx))
        
        # Calculate difference between wind direction and spread direction
        angle_diff = abs((spread_angle - self.wind_direction + 180) % 360 - 180)
        
        # Calculate wind factor
        # When spread is in the same direction as wind: increase probability
        # When spread is against the wind: decrease probability
        # Maximum effect when angle difference is 0 or 180 degrees
        if angle_diff <= 90:
            # Spreading with the wind
            wind_factor = 1.0 + (self.wind_strength * (1.0 - angle_diff / 90))
        else:
            # Spreading against the wind
            wind_factor = 1.0 - (self.wind_strength * (angle_diff - 90) / 90)
            wind_factor = max(0.1, wind_factor)  # Ensure minimum probability
        
        return wind_factor
    
    def _calculate_terrain_factor(self, from_x, from_y, to_x, to_y):
        """
        Calculate the terrain factor for fire spread.
        
        Parameters:
            from_x, from_y (int): Coordinates of the source cell
            to_x, to_y (int): Coordinates of the target cell
        
        Returns:
            float: Terrain factor (1.0 = no effect, >1.0 = increased spread, <1.0 = decreased spread)
        """
        # If terrain influence is zero, return neutral factor
        if self.terrain_influence == 0 or self.slope is None:
            return 1.0
        
        # Calculate direction of spread
        dx = to_x - from_x
        dy = to_y - from_y
        
        # Calculate angle of spread (in degrees)
        if dx == 0 and dy == 0:
            return 1.0
        
        spread_angle = math.degrees(math.atan2(dy, dx))
        
        # Get the slope aspect (direction of steepest slope)
        # and slope magnitude at the source cell
        aspect = self.aspect[from_x, from_y]
        slope_mag = self.slope[from_x, from_y]
        
        # Calculate difference between slope aspect and spread direction
        angle_diff = abs((spread_angle - aspect + 180) % 360 - 180)
        
        # Calculate terrain factor
        # When spread is upslope: increase probability
        # When spread is downslope: decrease probability
        # Maximum effect when angle difference is 0 or 180 degrees
        if angle_diff <= 90:
            # Spreading upslope
            terrain_factor = 1.0 + (self.terrain_influence * slope_mag * (1.0 - angle_diff / 90))
        else:
            # Spreading downslope
            terrain_factor = 1.0 - (self.terrain_influence * slope_mag * (angle_diff - 90) / 90 * 0.5)
            terrain_factor = max(0.5, terrain_factor)  # Ensure minimum probability
        
        return terrain_factor
    
    def update_horizontal_spread(self):
        """
        Update fire spread horizontally within each layer.
        
        This method handles the spread of fire to neighboring cells within the same layer.
        It calculates ignition probabilities based on fuel load, wind direction and speed,
        and applies probabilistic ignition to unburned cells.
        """
        # Create a copy of the current state to avoid order effects
        new_layers = [layer.copy() for layer in self.layers]
        
        # Process each layer
        for z in range(self.num_layers):
            # Skip layers with no burning cells
            if not np.any(self.layers[z] == CellState.BURNING.value):
                continue
                
            # Process each cell in the layer
            for y in range(1, self.grid_size - 1):
                for x in range(1, self.grid_size - 1):
                    # Skip cells that are not burning
                    if self.layers[z][y, x] != CellState.BURNING.value:
                        continue
                        
                    # Consume fuel in the burning cell
                    self.fuel_load[z, y, x] -= self.fuel_consumption_rates[z]
                    
                    # If fuel is depleted, mark as burned
                    if self.fuel_load[z, y, x] <= 0:
                        new_layers[z][y, x] = CellState.BURNED.value
                        self.fuel_load[z, y, x] = 0
                        continue
                    
                    # Check neighbors for potential ignition
                    neighbors = [
                        (y-1, x),    # North
                        (y+1, x),    # South
                        (y, x-1),    # West
                        (y, x+1),    # East
                        (y-1, x-1),  # Northwest
                        (y-1, x+1),  # Northeast
                        (y+1, x-1),  # Southwest
                        (y+1, x+1)   # Southeast
                    ]
                    
                    # Get local wind vector
                    wind_u = self.wind_u[y, x]
                    wind_v = self.wind_v[y, x]
                    
                    # Count burning neighbors for each unburned cell in the neighborhood
                    for ny, nx in neighbors:
                        # Skip if neighbor is not unburned
                        if self.layers[z][ny, nx] != CellState.UNBURNED.value:
                            continue
                            
                        # Skip if neighbor has no fuel
                        if self.fuel_load[z, ny, nx] <= 0:
                            continue
                        
                        # Count burning neighbors for this unburned cell
                        n_burning = 0
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                if dy == 0 and dx == 0:
                                    continue  # Skip self
                                
                                neighbor_y, neighbor_x = ny + dy, nx + dx
                                
                                # Check if within bounds
                                if (0 <= neighbor_y < self.grid_size and 
                                    0 <= neighbor_x < self.grid_size):
                                    if self.layers[z][neighbor_y, neighbor_x] == CellState.BURNING.value:
                                        n_burning += 1
                        
                        # Calculate direction vector to neighbor
                        # Note: y-axis is inverted in grid coordinates compared to Cartesian
                        dx = nx - x
                        dy = y - ny  # Invert y-axis to match wind direction convention
                        
                        # Normalize the direction vector
                        dist = np.sqrt(dx*dx + dy*dy)
                        if dist > 0:
                            dx /= dist
                            dy /= dist
                        
                        # Calculate wind effect (dot product of wind and direction vectors)
                        # Higher values mean wind is pushing toward the neighbor
                        wind_effect = wind_u * dx + wind_v * dy
                        
                        # Adjust wind effect to be in range [0, WIND_EFFECT_MAX]
                        wind_effect = max(0, wind_effect) * WIND_EFFECT_MAX
                        
                        # Calculate base ignition probability using sigmoid function with burning neighbors
                        if not hasattr(self, 'fire_params'):
                            # If fire_params doesn't exist, create default values
                            self.fire_params = {
                                'k': 1.5,            # Steepness of sigmoid curve
                                'threshold': 1.0,    # Critical number of burning neighbors
                                'spread_threshold': 0.01  # Minimum probability to consider ignition
                            }
                            
                        base_prob = sigmoid_ignition_neighbors(
                            n_burning,
                            self.fire_params['k'],
                            self.fire_params['threshold']
                        )
                        
                        # Apply fuel load effect (more fuel = higher probability)
                        fuel_effect = self.fuel_load[z, ny, nx]
                        
                        # Apply wind effect
                        ignition_prob = base_prob * fuel_effect * (1 + wind_effect)
                        
                        # Apply fuel moisture penalty
                        ignition_prob *= (1 - self.fuel_moisture)
                        
                        # Apply distance penalty for diagonal neighbors
                        if abs(nx - x) + abs(ny - y) > 1:  # Diagonal neighbor
                            ignition_prob *= DIAGONAL_PENALTY
                        
                        # Check if ignition occurs (probabilistic)
                        if ignition_prob > self.fire_params['spread_threshold'] and random.random() < ignition_prob:
                            new_layers[z][ny, nx] = CellState.BURNING.value
        
        # Update all layers at once to prevent order effects
        self.layers = new_layers

    def update_vertical_spread(self):
        """
        Update fire spread vertically between layers.
        
        This method handles the spread of fire between adjacent vertical layers.
        It includes both upward spread (flames rising) and downward spread (embers falling).
        
        This method handles:
        1. Direct vertical spread to adjacent layers
        2. Ember generation and transport for longer-distance spot fires
        
        Ember trajectories are tracked and stored for visualization.
        """
        # First, create copies of the layers to update all at once (prevent order effects)
        new_layers = [layer.copy() for layer in self.layers]
        
        # Clear active embers list before generating new ones for this step
        self.active_embers = []
        
        # For each layer in the forest
        for z in range(self.num_layers):
            # Find all burning cells in this layer
            burning_cells = np.where(self.layers[z] == CellState.BURNING.value)
            burning_y, burning_x = burning_cells
            
            # For each burning cell
            for i, j in zip(burning_y, burning_x):
                # Skip cells at edges (they're handled specially)
                if (i == 0 or i == self.grid_size - 1 or 
                    j == 0 or j == self.grid_size - 1):
                    continue
                
                # 1. Upward spread (flames rising) - only if not at top layer
                if z < self.num_layers - 1:
                    # Check if the cell above is unburned and has fuel
                    if self.layers[z+1][i, j] == CellState.UNBURNED.value and self.fuel_load[z+1, i, j] > 0:
                        # Calculate upward spread probability
                        # This depends on vertical connectivity and fuel properties
                        upward_prob = self.vertical_connectivity[z] * (
                            1.0 - self.fuel_moisture) * self.fuel_load[z+1, i, j]
                        
                        # Adjust for crown fire effects
                        if z >= CANOPY_START_LAYER:
                            upward_prob *= CROWN_FIRE_MULTIPLIER
                            
                        # Apply probabilistic ignition
                        if random.random() < upward_prob:
                            new_layers[z+1][i, j] = CellState.BURNING.value
                
                # 2. Downward spread (dropped material) - only if not at bottom layer
                if z > 0:
                    # Check if the cell below is unburned and has fuel
                    if self.layers[z-1][i, j] == CellState.UNBURNED.value and self.fuel_load[z-1, i, j] > 0:
                        # Burning material tends to fall downward
                        downward_prob = DOWNWARD_SPREAD_PROBABILITY * self.fuel_load[z-1, i, j]
                        
                        # Apply probabilistic ignition
                        if random.random() < downward_prob:
                            new_layers[z-1][i, j] = CellState.BURNING.value
                
                # 3. Ember generation and transport
                if random.random() < self.ember_params['generation_rate']:
                    # Get local wind vector for ember direction
                    wind_direction = self.wind_direction[i, j]
                    wind_speed = self.wind_speed[i, j]
                    
                    # Stronger winds create more variation in angle
                    angle_std_dev = np.pi / 4  # 45 degrees standard deviation
                    
                    # Generate multiple embers
                    for _ in range(np.random.randint(1, self.ember_params['embers_per_cell'] + 1)):
                        # Determine ember travel direction (biased by wind direction)
                        # Higher wind speeds make ember direction more aligned with wind
                        ember_angle = np.random.normal(wind_direction, angle_std_dev * (1 - wind_speed))
                        
                        # Determine ember travel distance (influenced by wind speed)
                        # Embers travel farther in the direction of the wind
                        base_distance = self.ember_params['travel_distance']
                        # Calculate alignment of ember direction with wind direction
                        direction_alignment = np.cos(ember_angle - wind_direction)
                        
                        # Adjust distance based on wind speed and direction alignment
                        # Embers travel farther when wind is strong and in same direction
                        distance_multiplier = 1.0 + (wind_speed * direction_alignment)
                        distance = int(base_distance * distance_multiplier) + 1
                        distance = max(1, min(distance, 2 * base_distance))  # Limit maximum distance
                        
                        # Calculate target position
                        target_x = int(j + distance * np.cos(ember_angle))
                        target_y = int(i + distance * np.sin(ember_angle))
                        
                        # Check if target is within grid bounds
                        if (target_x < 0 or target_x >= self.grid_size or
                            target_y < 0 or target_y >= self.grid_size):
                            continue  # Ember lands outside the grid
                        
                        # Determine vertical travel (embers typically fall)
                        # Higher wind speeds can carry embers further horizontally before they fall
                        max_vertical = min(self.ember_params['vertical_distance'], z)
                        if max_vertical > 0:
                            # Weighted toward greater fall distance
                            vertical_travel = -np.random.randint(1, max_vertical + 1)
                        else:
                            vertical_travel = 0
                            
                        target_z = z + vertical_travel
                        
                        # Skip if target is not unburned or has no fuel
                        if self.layers[target_z][target_y, target_x] != CellState.UNBURNED.value or self.fuel_load[target_z, target_y, target_x] <= 0:
                            continue
                            
                        # Calculate ignition probability
                        ignition_prob = self.ember_params['ignition_prob']
                        
                        # Reduce probability based on horizontal distance traveled
                        distance_penalty = max(
                            self.ember_params['min_probability'],
                            1.0 - (distance / self.ember_params['travel_distance'])
                        )
                        
                        # Reduce probability based on vertical distance traveled
                        vertical_penalty = max(
                            self.ember_params['min_probability'],
                            1.0 - (vertical_travel * self.ember_params['vertical_penalty'])
                        )
                        
                        # Fuel load increases ignition probability
                        fuel_effect = (1.0 + self.fuel_load[target_z, target_y, target_x] * self.ember_params['fuel_multiplier'])
                        
                        # Calculate final ignition probability
                        final_prob = ignition_prob * distance_penalty * vertical_penalty * fuel_effect
                        
                        # Create ember trajectory data
                        ember_data = {
                            'source': (j, i, z),  # x, y, z of source
                            'target': (target_x, target_y, target_z),
                            'start_time': self.time_step,
                            'travel_time': max(1, int(distance/2)),  # Time in simulation steps to reach target
                            'angle': ember_angle,
                            'distance': distance,
                            'vertical_travel': vertical_travel,
                            'ignition_prob': final_prob,
                            'ignited': False,  # Will be set to True if ignition occurs
                            'current_pos': (j, i, z),  # Starting position
                            'velocity': (
                                (target_x - j) / max(1, int(distance/2)),
                                (target_y - i) / max(1, int(distance/2)),
                                vertical_travel / max(1, int(distance/2))
                            ),
                            'remaining_steps': max(1, int(distance/2))
                        }
                        
                        # Apply probabilistic ignition
                        if random.random() < final_prob:
                            new_layers[target_z][target_y, target_x] = CellState.BURNING.value
                            ember_data['ignited'] = True
                            
                        # Add ember to the active list
                        self.active_embers.append(ember_data)
                        
                        # Also add to the history for visualization later
                        self.ember_history.append(ember_data.copy())
        
        # Update all layers at once to prevent order effects
        self.layers = new_layers

    def initialize_wind(self, trade_wind_direction, trade_wind_strength):
        """
        Initialize a uniform wind field across the forest.
        
        Args:
            trade_wind_direction (float): Wind direction in radians (0 = East, π/2 = North)
            trade_wind_strength (float): Wind strength (0.0-1.0)
        """
        print(f"Initializing uniform wind field: Direction={trade_wind_direction*180/np.pi:.1f}°, Strength={trade_wind_strength:.2f}")
        
        # Set uniform wind direction and speed
        self.wind_direction.fill(trade_wind_direction)
        self.wind_speed.fill(trade_wind_strength)
        
        # Calculate wind vector components
        self.wind_u = self.wind_speed * np.cos(self.wind_direction)
        self.wind_v = self.wind_speed * np.sin(self.wind_direction)
        
        print(f"Wind field initialized with uniform values")

    def initialize_terrain_wind(self, trade_wind_direction, trade_wind_strength, 
                               terrain_effect_strength=0.5, barranco_threshold=5.0,
                               barranco_amplification=1.5):
        """
        Initialize wind direction and speed across the forest grid using terrain data.
        
        This method creates a wind field that starts with a uniform base wind (trade wind)
        and then applies terrain effects to modify both wind speed and direction.
        It also identifies barrancos features (ravines/depressions) and amplifies
        wind speed in those areas to simulate channeling effects.
        
        Args:
            trade_wind_direction (float): Base wind direction in radians (0 = East, π/2 = North)
            trade_wind_strength (float): Base wind strength (0.0-1.0)
            terrain_effect_strength (float): How strongly terrain affects wind (0.0-1.0)
            barranco_threshold (float): Elevation change to identify barrancos (meters)
            barranco_amplification (float): Factor to increase wind speed in barrancos
        """
        print(f"Initializing terrain-influenced wind field:")
        print(f"  Base direction: {trade_wind_direction*180/np.pi:.1f}°")
        print(f"  Base strength: {trade_wind_strength:.2f}")
        print(f"  Terrain effect strength: {terrain_effect_strength:.2f}")
        print(f"  Barranco threshold: {barranco_threshold:.1f}m")
        print(f"  Barranco amplification: {barranco_amplification:.2f}x")
        
        # Check if terrain data is available
        if not hasattr(self, 'terrain') or self.terrain is None:
            print("Warning: No terrain data available. Using uniform wind field instead.")
            self.initialize_wind(trade_wind_direction, trade_wind_strength)
            return
        
        # Start with uniform wind field
        self.wind_direction.fill(trade_wind_direction)
        self.wind_speed.fill(trade_wind_strength)
        
        # Calculate terrain gradients (slope and aspect)
        dy, dx = np.gradient(self.terrain)
        slope = np.sqrt(dx**2 + dy**2)  # Slope magnitude
        aspect = np.arctan2(dy, dx)     # Slope direction/aspect in radians
        
        # Create a mask for barrancos (depressions in the terrain)
        barranco_mask = np.zeros((self.grid_size, self.grid_size), dtype=bool)
        
        # Detect barrancos by analyzing elevation differences with neighbors
        print("Detecting barranco features...")
        for y in range(1, self.grid_size-1):
            for x in range(1, self.grid_size-1):
                # Calculate elevation differences to neighboring cells
                elev_diffs = [
                    self.terrain[y-1, x] - self.terrain[y, x],  # North
                    self.terrain[y+1, x] - self.terrain[y, x],  # South
                    self.terrain[y, x-1] - self.terrain[y, x],  # West
                    self.terrain[y, x+1] - self.terrain[y, x],  # East
                ]
                
                # Check for significant negative differences (depression)
                # and also some positive differences (one side of a ravine)
                neg_diffs = [d for d in elev_diffs if d < -barranco_threshold]
                pos_diffs = [d for d in elev_diffs if d > barranco_threshold]
                
                if len(neg_diffs) >= 1 and len(pos_diffs) >= 1:
                    barranco_mask[y, x] = True
        
        # Count detected barrancos
        barranco_count = np.sum(barranco_mask)
        print(f"Detected {barranco_count} barranco cells ({barranco_count/(self.grid_size*self.grid_size)*100:.1f}% of terrain)")
        
        # Apply terrain effects to wind
        print("Applying terrain effects to wind field...")
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                # Skip cells with no significant slope
                if slope[y, x] < 0.05:
                    continue
                
                # Calculate angle between wind direction and terrain aspect
                angle_diff = np.abs(self.wind_direction[y, x] - aspect[y, x]) % (2 * np.pi)
                if angle_diff > np.pi:
                    angle_diff = 2 * np.pi - angle_diff
                
                # Wind deflection based on terrain
                # Maximum deflection when wind is perpendicular to terrain
                deflection_strength = np.sin(angle_diff) * terrain_effect_strength
                
                # Apply deflection - wind partially follows terrain contours
                self.wind_direction[y, x] = (
                    (1 - deflection_strength) * self.wind_direction[y, x] + 
                    deflection_strength * aspect[y, x]
                ) % (2 * np.pi)
                
                # Modify wind speed based on terrain
                # Wind speeds up over ridges and slows in valleys
                wind_terrain_alignment = np.cos(self.wind_direction[y, x] - aspect[y, x])
                speed_modifier = 1.0 - (wind_terrain_alignment * slope[y, x] * terrain_effect_strength)
                self.wind_speed[y, x] *= max(0.5, min(1.5, speed_modifier))
                
                # Apply barranco amplification
                if barranco_mask[y, x]:
                    self.wind_speed[y, x] *= barranco_amplification
        
        # Calculate wind vector components
        self.wind_u = self.wind_speed * np.cos(self.wind_direction)
        self.wind_v = self.wind_speed * np.sin(self.wind_direction)
        
        # Print summary statistics
        print(f"Wind field initialized with terrain effects:")
        print(f"  Wind speed range: {np.min(self.wind_speed):.2f}-{np.max(self.wind_speed):.2f}")
        print(f"  Direction range: {np.min(self.wind_direction)*180/np.pi:.1f}°-{np.max(self.wind_direction)*180/np.pi:.1f}°")

    def load_terrain_data(self, terrain_file_path, no_data_value=-9999):
        """
        Load terrain elevation data from a raster file.
        
        Args:
            terrain_file_path (str): Path to the terrain raster file
            no_data_value (float): Value to consider as no data in the raster
            
        Returns:
            bool: True if loading was successful, False otherwise
        """
        try:
            print(f"Loading terrain data from: {terrain_file_path}")
            
            # Open the raster file
            raster = gdal.Open(terrain_file_path)
            if raster is None:
                print(f"Error: Could not open {terrain_file_path}")
                return False
                
            # Get raster dimensions
            raster_width = raster.RasterXSize
            raster_height = raster.RasterYSize
            
            # Get geotransform information
            geo_transform = raster.GetGeoTransform()
            self.terrain_geo_transform = geo_transform
            
            # Calculate geographic extent
            minx = geo_transform[0]
            maxy = geo_transform[3]
            maxx = minx + geo_transform[1] * raster_width
            miny = maxy + geo_transform[5] * raster_height
            self.terrain_extent = (minx, miny, maxx, maxy)
            
            # Read the raster band
            band = raster.GetRasterBand(1)
            data = band.ReadAsArray()
            
            # Replace no_data_value with a valid minimum value
            valid_mask = (data != no_data_value)
            if np.any(valid_mask):
                min_valid = np.min(data[valid_mask])
                data = np.where(valid_mask, data, min_valid)
            
            # Check if resampling is needed
            if data.shape[0] != self.grid_size or data.shape[1] != self.grid_size:
                print(f"Resampling terrain data from {data.shape} to match forest grid size {self.grid_size}x{self.grid_size}")
                
                # Resize using bilinear interpolation
                data = resize(data, (self.grid_size, self.grid_size), order=1)
            
            # Store the terrain data
            self.terrain = data
            
            # Calculate basic statistics
            self.terrain_min = np.min(data)
            self.terrain_max = np.max(data)
            self.terrain_mean = np.mean(data)
            
            print(f"Terrain data loaded successfully:")
            print(f"  Dimensions: {self.grid_size}x{self.grid_size}")
            print(f"  Elevation range: {self.terrain_min:.1f}m - {self.terrain_max:.1f}m")
            print(f"  Mean elevation: {self.terrain_mean:.1f}m")
            print(f"  Resolution: {MODEL_RESOLUTION}m per cell")
            print(f"  Geographic extent: {self.terrain_extent}")
            
            return True
            
        except Exception as e:
            print(f"Error loading terrain data: {str(e)}")
            traceback.print_exc()
            return False

    def save_results(self, output_dir):
        """
        Save comprehensive simulation results to disk for model calibration and analysis.
        
        This method saves:
        - Complete simulation history in numpy compressed format
        - Statistical summaries in CSV format
        - Ember trajectory data
        - Simulation parameters and metadata
        
        Args:
            output_dir (str): Directory where results will be saved
        """
        import os
        import json
        import csv
        import numpy as np
        from datetime import datetime
        
        print(f"Preparing to save results to: {output_dir}")
        
        # Create complete directory path (including parent directories)
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"Created directory: {output_dir}")
        except Exception as e:
            print(f"Warning: Could not create directory {output_dir}: {str(e)}")
            print("Will try using a fallback directory...")
            # Fallback to a directory in the current working directory
            output_dir = os.path.join(os.getcwd(), "simulation_results", 
                                      f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(output_dir, exist_ok=True)
            print(f"Using fallback directory: {output_dir}")
        
        # Check if we have any history to save
        if not self.history:
            print("Warning: No simulation history to save!")
            # Create a minimal history entry so we can still save parameters
            self.history = [{
                'time_step': 0,
                'burning_count': [0] * self.num_layers,
                'burned_count': [0] * self.num_layers,
                'unburned_count': [self.grid_size * self.grid_size] * self.num_layers,
                'burning_area': [0] * self.num_layers,
                'burned_area': [0] * self.num_layers,
                'unburned_area': [self.grid_size * self.grid_size * self.cell_area_meters] * self.num_layers,
                'total_burning': 0,
                'total_burned': 0,
                'total_unburned': self.grid_size * self.grid_size * self.num_layers,
                'total_burning_area': 0,
                'total_burned_area': 0,
                'total_unburned_area': self.grid_size * self.grid_size * self.num_layers * self.cell_area_meters
            }]
        
        print(f"Saving comprehensive simulation results to: {output_dir}")
        
        try:
            # 1. Save simulation history (compressed numpy format)
            history_file = os.path.join(output_dir, "simulation_history.npz")
            
            # Convert history to a format suitable for numpy storage
            # Extract key metrics for each timestep
            timesteps = []
            burning_counts = []
            burned_counts = []
            unburned_counts = []
            burning_areas = []
            burned_areas = []
            
            # If full states were stored, prepare them for saving
            grid_states = None
            if self.store_full_states and len(self.history) > 0 and 'grid_states' in self.history[0]:
                grid_states = [state['grid_states'] for state in self.history]
            
            # Extract statistics from history
            for state in self.history:
                timesteps.append(state.get('time_step', 0))
                
                # Use get() method to safely extract values or provide defaults
                burning_counts.append(state.get('burning_count', [0] * self.num_layers))
                burned_counts.append(state.get('burned_count', [0] * self.num_layers))
                unburned_counts.append(state.get('unburned_count', [0] * self.num_layers))
                
                burning_areas.append(state.get('burning_area', [0] * self.num_layers))
                burned_areas.append(state.get('burned_area', [0] * self.num_layers))
            
            # Create a compressed numpy archive with all history data
            np.savez_compressed(
                history_file,
                timesteps=np.array(timesteps),
                burning_counts=np.array(burning_counts),
                burned_counts=np.array(burned_counts),
                unburned_counts=np.array(unburned_counts),
                burning_areas=np.array(burning_areas, dtype=object),
                burned_areas=np.array(burned_areas, dtype=object),
                grid_states=grid_states
            )
            print(f"Saved simulation history to: {history_file}")
            
            # 2. Save ember trajectory data if available
            if hasattr(self, 'ember_history') and self.ember_history:
                try:
                    ember_file = os.path.join(output_dir, "ember_data.npz")
                    
                    # Extract key ember statistics
                    sources = []
                    targets = []
                    start_times = []
                    travel_times = []
                    distances = []
                    ignited = []
                    
                    for ember in self.ember_history:
                        sources.append(ember.get('source', (0, 0, 0)))
                        targets.append(ember.get('target', (0, 0, 0)))
                        start_times.append(ember.get('start_time', 0))
                        travel_times.append(ember.get('travel_time', 0))
                        distances.append(ember.get('distance', 0))
                        ignited.append(ember.get('ignited', False))
                    
                    # Save ember data
                    np.savez_compressed(
                        ember_file,
                        sources=np.array(sources),
                        targets=np.array(targets),
                        start_times=np.array(start_times),
                        travel_times=np.array(travel_times),
                        distances=np.array(distances),
                        ignited=np.array(ignited),
                        total_embers=len(self.ember_history),
                        ignition_count=sum(ignited)
                    )
                    print(f"Saved ember data to: {ember_file}")
                except Exception as e:
                    print(f"Warning: Could not save ember data: {str(e)}")
            else:
                print("No ember data available to save")
            
            # 3. Save statistical summary as CSV
            try:
                stats_file = os.path.join(output_dir, "statistics.csv")
                with open(stats_file, 'w', newline='') as csvfile:
                    # Set up CSV writer
                    csv_writer = csv.writer(csvfile)
                    
                    # Write header row
                    header = ['TimeStep', 'TotalBurning', 'TotalBurned', 'TotalUnburned', 
                              'BurningAreaM2', 'BurnedAreaM2', 'TotalBurnedPercentage']
                    
                    # Add layer-specific columns if we have layer data
                    if len(self.history) > 0 and len(self.history[0].get('burning_count', [])) > 0:
                        for layer in range(self.num_layers):
                            header.extend([f'Layer{layer}Burning', f'Layer{layer}Burned', f'Layer{layer}Percentage'])
                    
                    csv_writer.writerow(header)
                    
                    # Write data rows
                    for state in self.history:
                        time_step = state.get('time_step', 0)
                        total_burning = state.get('total_burning', 0)
                        total_burned = state.get('total_burned', 0)
                        total_unburned = state.get('total_unburned', 0)
                        burning_area = state.get('total_burning_area', 0)
                        burned_area = state.get('total_burned_area', 0)
                        
                        # Calculate total burned percentage
                        total_cells = total_burning + total_burned + total_unburned
                        if total_cells > 0:
                            burned_percentage = (total_burning + total_burned) / total_cells * 100
                        else:
                            burned_percentage = 0
                        
                        # Start with the common columns
                        row = [time_step, total_burning, total_burned, total_unburned,
                              burning_area, burned_area, burned_percentage]
                        
                        # Add layer-specific data
                        if 'burning_count' in state and len(state['burning_count']) > 0:
                            for layer in range(min(self.num_layers, len(state['burning_count']))):
                                layer_burning = state['burning_count'][layer]
                                layer_burned = state['burned_count'][layer] if layer < len(state['burned_count']) else 0
                                layer_unburned = state['unburned_count'][layer] if layer < len(state['unburned_count']) else 0
                                
                                layer_total = layer_burning + layer_burned + layer_unburned
                                if layer_total > 0:
                                    layer_percentage = (layer_burning + layer_burned) / layer_total * 100
                                else:
                                    layer_percentage = 0
                                
                                row.extend([layer_burning, layer_burned, layer_percentage])
                        
                        csv_writer.writerow(row)
                print(f"Saved statistical summary to: {stats_file}")
            except Exception as e:
                print(f"Warning: Could not save statistical summary: {str(e)}")
            
            # 4. Save model parameters and metadata
            try:
                params_file = os.path.join(output_dir, "parameters.json")
                
                # Helper function to make objects JSON serializable
                def make_serializable(obj):
                    if isinstance(obj, np.ndarray):
                        return obj.tolist()
                    elif isinstance(obj, np.integer):
                        return int(obj)
                    elif isinstance(obj, np.floating):
                        return float(obj)
                    elif isinstance(obj, dict):
                        return {k: make_serializable(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [make_serializable(item) for item in obj]
                    else:
                        return obj
                
                # Collect all relevant model parameters
                parameters = {
                    # Model dimensions
                    'grid_size': self.grid_size,
                    'num_layers': self.num_layers,
                    'layer_height_meters': self.layer_height_meters,
                    'model_resolution': self.model_resolution,
                    'cell_area_meters': self.cell_area_meters,
                    
                    # Simulation metadata
                    'simulation_time_steps': len(self.history),
                    'store_full_states': self.store_full_states,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    
                    # Fire behavior parameters
                    'fuel_moisture': self.fuel_moisture,
                }
                
                # Add optional parameters if they exist
                if hasattr(self, 'fuel_consumption_rates'):
                    parameters['fuel_consumption_rates'] = make_serializable(self.fuel_consumption_rates)
                
                if hasattr(self, 'vertical_connectivity'):
                    parameters['vertical_connectivity'] = make_serializable(self.vertical_connectivity)
                
                if hasattr(self, 'ember_params'):
                    parameters['ember_params'] = make_serializable(self.ember_params)
                
                # Results summary
                if self.history:
                    parameters['final_burned_cell_count'] = sum(self.history[-1].get('burned_count', [0]))
                    parameters['final_burned_area_m2'] = sum(self.history[-1].get('burned_area', [0]))
                
                if hasattr(self, 'ember_history'):
                    parameters['total_embers_generated'] = len(self.ember_history)
                
                # Wind field metadata
                parameters['has_wind_field'] = hasattr(self, 'wind_direction') and self.wind_direction is not None
                parameters['has_terrain'] = hasattr(self, 'terrain_elevation') and self.terrain_elevation is not None
                
                # Save parameters as JSON
                with open(params_file, 'w') as f:
                    json.dump(make_serializable(parameters), f, indent=4)
                print(f"Saved parameters to: {params_file}")
            except Exception as e:
                print(f"Warning: Could not save parameters: {str(e)}")
            
            # 5. Save a README with instructions for loading
            try:
                readme_file = os.path.join(output_dir, "README.txt")
                with open(readme_file, 'w') as f:
                    f.write("FOREST FIRE SIMULATION RESULTS\n")
                    f.write("==============================\n\n")
                    f.write(f"Simulation run on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("FILES INCLUDED:\n")
                    f.write("---------------\n")
                    f.write("simulation_history.npz: Complete simulation history in numpy compressed format\n")
                    f.write("statistics.csv: Statistical summary of simulation in CSV format\n")
                    if hasattr(self, 'ember_history') and self.ember_history:
                        f.write("ember_data.npz: Ember trajectory and ignition data\n")
                    f.write("parameters.json: Simulation parameters and metadata\n\n")
                    
                    f.write("LOADING INSTRUCTIONS:\n")
                    f.write("--------------------\n")
                    f.write("To load simulation history:\n")
                    f.write("```python\n")
                    f.write("import numpy as np\n")
                    f.write("data = np.load('simulation_history.npz', allow_pickle=True)\n")
                    f.write("timesteps = data['timesteps']\n")
                    f.write("burning_counts = data['burning_counts']\n")
                    f.write("burned_counts = data['burned_counts']\n")
                    f.write("# For full grid states (if stored):\n")
                    f.write("grid_states = data['grid_states']\n")
                    f.write("```\n\n")
                    
                    f.write("To load ember data:\n")
                    f.write("```python\n")
                    f.write("ember_data = np.load('ember_data.npz', allow_pickle=True)\n")
                    f.write("sources = ember_data['sources']\n")
                    f.write("targets = ember_data['targets']\n")
                    f.write("ignited = ember_data['ignited']\n")
                    f.write("```\n")
                print(f"Saved README to: {readme_file}")
            except Exception as e:
                print(f"Warning: Could not save README: {str(e)}")
            
            print(f"Results successfully saved to: {output_dir}")
            
        except Exception as e:
            print(f"Error saving results: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            print("Will attempt to create a minimal output file to record the error")
            
            # Try to save at least an error log
            try:
                error_log = os.path.join(output_dir, "error_log.txt")
                with open(error_log, 'w') as f:
                    f.write(f"Error occurred when saving results: {str(e)}\n\n")
                    f.write(f"Traceback:\n{traceback.format_exc()}")
                print(f"Error log saved to: {error_log}")
            except:
                print("Could not even save error log. Check directory permissions and path validity.")
            
        return output_dir

    def update_ember_transport(self):
        """
        Update ember generation, transport, and landing ignitions.
        
        This method:
        1. Updates positions of existing embers based on wind and gravity
        2. Processes landing embers for potential ignition
        3. Generates new embers from burning cells
        
        Ember tracking between simulation steps:
        - Active embers are stored in self.active_embers list (initialized in __init__)
        - Completed ember trajectories are stored in self.ember_trajectories
        - Ember-caused ignitions are counted in self.ember_ignitions
        """

def analyze_fire_spread(forest_model):
    """
    Analyze the fire spread patterns and calculate statistics.
    
    Args:
        forest_model (ForestModel): The forest model after simulation
        
    Returns:
        tuple: (fire_area, burn_pattern) where fire_area is the total burned area in square meters
               and burn_pattern is a string describing the burn pattern
    """
    # Calculate total burned area
    burned_cells = 0
    for z in range(forest_model.num_layers):
        burned_cells += np.sum(forest_model.layers[z] == CellState.BURNED.value)
        burned_cells += np.sum(forest_model.layers[z] == CellState.BURNING.value)
    
    # Convert to area in square meters
    fire_area = burned_cells * forest_model.cell_area_meters
    
    # Analyze burn pattern
    if burned_cells == 0:
        burn_pattern = "No fire spread"
    else:
        # Calculate percentage of forest burned
        total_cells = forest_model.grid_size * forest_model.grid_size * forest_model.num_layers
        percent_burned = (burned_cells / total_cells) * 100
        
        if percent_burned < 10:
            burn_pattern = "Limited spread"
        elif percent_burned < 30:
            burn_pattern = "Moderate spread"
        elif percent_burned < 60:
            burn_pattern = "Extensive spread"
        else:
            burn_pattern = "Catastrophic spread"
    
    return fire_area, burn_pattern

def visualize_fire_spread_2d(forest_model):
    """
    Create a 2D visualization of the fire spread.
    
    Args:
        forest_model (ForestModel): The forest model after simulation
    """
    # Create a figure with subplots for each layer
    fig, axes = plt.subplots(1, forest_model.num_layers, figsize=(4*forest_model.num_layers, 4))
    
    # If there's only one layer, axes won't be an array
    if forest_model.num_layers == 1:
        axes = [axes]
    
    # Define colors for each state
    cmap = colors.ListedColormap(['green', 'red', 'black'])
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = colors.BoundaryNorm(bounds, cmap.N)
    
    # Plot each layer
    for z, ax in enumerate(axes):
        im = ax.imshow(forest_model.layers[z], cmap=cmap, norm=norm)
        ax.set_title(f"Layer {z}")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
    
    # Add a colorbar
    cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(im, cax=cbar_ax)
    cbar.set_ticks([0, 1, 2])
    cbar.set_ticklabels(['Unburned', 'Burning', 'Burned'])
    
    # Add a title
    fig.suptitle(f"Fire Spread Simulation (Resolution: {MODEL_RESOLUTION}m)")
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 0.9, 0.95])
    
    # Show the plot
    plt.show()

def visualize_fire_spread_3d(forest_model):
    """
    Create a 3D visualization of the fire spread.
    
    Args:
        forest_model (ForestModel): The forest model after simulation
    """
    # Create a figure
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Define colors for each state
    colors_map = {
        CellState.UNBURNED.value: 'green',
        CellState.BURNING.value: 'red',
        CellState.BURNED.value: 'black'
    }
    
    # Create meshgrid for coordinates
    x = np.arange(forest_model.grid_size)
    y = np.arange(forest_model.grid_size)
    xx, yy = np.meshgrid(x, y)
    
    # Plot each layer
    for z in range(forest_model.num_layers):
        # Get the layer data
        layer = forest_model.layers[z]
        
        # Plot burning and burned cells
        for state in [CellState.BURNING.value, CellState.BURNED.value]:
            mask = (layer == state)
            if np.any(mask):
                ax.scatter(xx[mask], yy[mask], z * np.ones_like(xx)[mask],
                          c=colors_map[state], marker='s', alpha=0.7)
    
    # Set labels and title
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Layer')
    ax.set_title(f"3D Fire Spread Visualization (Resolution: {MODEL_RESOLUTION}m)")
    
    # Set axis limits
    ax.set_xlim(0, forest_model.grid_size-1)
    ax.set_ylim(0, forest_model.grid_size-1)
    ax.set_zlim(0, forest_model.num_layers-1)
    
    # Add a legend
    legend_elements = [
        Line2D([0], [0], marker='s', color='w', markerfacecolor='red', markersize=10, label='Burning'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='black', markersize=10, label='Burned')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    # Show the plot
    plt.tight_layout()
    plt.show()
    
    return fig

def visualize_fire_spread_animation(forest_model, frame_interval_ms=200, display_layer="composite", show_stats=True, optimize_storage=True):
    """
    Create an animation of the fire spread.
    
    Args:
        forest_model (ForestModel): The forest model after simulation
        frame_interval_ms (int): Milliseconds between animation frames
        display_layer (str): Which layer to display - "composite" for all layers combined, 
                           or a specific layer number like "0" for bottom layer
        show_stats (bool): Whether to display statistics on the animation
        optimize_storage (bool): If True, uses memory-efficient data representation
        
    Returns:
        animation.FuncAnimation: Animation object
    """
    # Check if we have history data
    if not forest_model.history:
        print("No history data available for animation")
        return None
    
    # Determine which layer(s) to display
    if display_layer == "composite":
        is_composite = True
        layer_idx = None
    else:
        try:
            layer_idx = int(display_layer)
            if layer_idx < 0 or layer_idx >= forest_model.num_layers:
                print(f"Layer {layer_idx} is out of range. Using composite view.")
                is_composite = True
                layer_idx = None
        except:
            print(f"Invalid layer specification '{display_layer}'. Using composite view.")
            is_composite = True
            layer_idx = None
    
    # Check if full states were stored
    has_full_states = forest_model.store_full_states and 'grid_states' in forest_model.history[0]
    if not has_full_states and not optimize_storage:
        print("Warning: Full states were not stored during simulation. Using statistical approximation.")
        optimize_storage = True
    
    # Create a figure with appropriate size based on grid dimensions
    # Scale figure size with grid size but cap at reasonable limits
    fig_size = min(14, max(8, forest_model.grid_size / 25))
    
    # Create figure with space for statistics panel if showing stats
    if show_stats:
        # Create figure with a grid layout to accommodate main plot and stats
        fig = plt.figure(figsize=(fig_size*1.2, fig_size))
        # Create main plot for the animation
        gs = gridspec.GridSpec(1, 4, figure=fig, width_ratios=[3, 1])
        ax = fig.add_subplot(gs[0, 0:3])  # Main plot takes 3/4 of the width
        stats_ax = fig.add_subplot(gs[0, 3])  # Stats panel takes 1/4 of the width
        stats_ax.axis('off')  # Hide axis for stats panel
    else:
        # Just create a regular figure with a single axis
        fig, ax = plt.subplots(figsize=(fig_size, fig_size))
    
    # Define colors for each state
    cmap = colors.ListedColormap(['green', 'red', 'black'])
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = colors.BoundaryNorm(bounds, cmap.N)
    
    # Pre-compute initial state
    if is_composite:
        if has_full_states and 'composite' in forest_model.history[0]:
            # Use precomputed composite if available
            initial_state = forest_model.history[0]['composite'].copy()
        else:
            # For composite view, take the maximum state value across all layers
            initial_state = np.zeros((forest_model.grid_size, forest_model.grid_size), dtype=np.int8)
            for z in range(forest_model.num_layers):
                initial_state = np.maximum(initial_state, forest_model.layers[z])
    else:
        if has_full_states:
            # Use stored layer state if available
            initial_state = forest_model.history[0]['grid_states'][layer_idx].copy()
        else:
            # For specific layer view
            initial_state = forest_model.layers[layer_idx].copy()
    
    # Initial plot
    im = ax.imshow(initial_state, cmap=cmap, norm=norm, interpolation='nearest')
    
    # Add colorbar with labels
    cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2])
    cbar.set_ticklabels(['Unburned', 'Burning', 'Burned'])
    
    # Create title with basic information
    title_text = f"Time Step: 0"
    title = ax.set_title(title_text, fontsize=10)
    
    # Set axis labels
    ax.set_xlabel(f"X (Resolution: {forest_model.model_resolution}m per cell)")
    ax.set_ylabel("Y")
    
    # Create stats display
    if show_stats:
        stats_text = stats_ax.text(0.5, 0.5, "", ha='center', va='center', fontsize=10, 
                                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                                   transform=stats_ax.transAxes)
        
        # Initialize with initial stats
        stats = forest_model.history[0]
        stats_info = get_formatted_stats(stats)
        stats_text.set_text(stats_info)
    
    # Precompute frame data if storage optimization is off and we don't have full states
    frame_data = []
    if not optimize_storage and not has_full_states:
        print("Precomputing animation frames...")
        for frame in range(len(forest_model.history)):
            # Calculate the burning/burned state based on prior time steps
            if frame == 0:
                # For the first frame, we use the initial state
                frame_data.append(initial_state.copy())
        else:
                # For subsequent frames, simulate the spreading fire based on counts
                prior_state = frame_data[frame-1].copy()
                
                # Calculate change in burning cells from prior frame to current frame
                current_stats = forest_model.history[frame]
                prior_stats = forest_model.history[frame-1]
                
                # This is a simplified approach - in a full implementation,
                # we'd need to store the actual cell states at each time step
                # for complete accuracy
                frame_data.append(prior_state)
        print("Precomputation complete.")
    
    # Helper function to format statistics
    def get_formatted_stats(stats):
        """Format statistics for display"""
        burned_percent = (stats['total_burned'] + stats['total_burning']) / (stats['total_burned'] + stats['total_burning'] + stats['total_unburned']) * 100
        burned_area = (stats['total_burned_area'] + stats['total_burning_area']) / 10000  # Convert to hectares
        active_area = stats['total_burning_area'] / 10000  # Convert to hectares
        
        stats_lines = [
            "SIMULATION STATISTICS",
            "-------------------",
            f"Time Step: {stats['time_step']}",
            f"Burned Area: {burned_area:.2f} ha",
            f"Percent Burned: {burned_percent:.1f}%",
            f"Active Fire Front: {active_area:.2f} ha",
            "-------------------",
            "Cell Counts:",
            f"Burning: {stats['total_burning']}",
            f"Burned: {stats['total_burned']}",
            f"Unburned: {stats['total_unburned']}"
        ]
        return "\n".join(stats_lines)
    
    # Animation update function
    def update(frame):
        # Get the data for this frame
        if has_full_states:
            # Use actual stored grid states (most accurate)
            stats = forest_model.history[frame]
            if is_composite and 'composite' in stats:
                # Use precomputed composite view
                frame_state = stats['composite']
            elif is_composite:
                # Create composite from layer states
                frame_state = np.zeros((forest_model.grid_size, forest_model.grid_size), dtype=np.int8)
                for z in range(forest_model.num_layers):
                    frame_state = np.maximum(frame_state, stats['grid_states'][z])
            else:
                # Use specific layer
                frame_state = stats['grid_states'][layer_idx]
        elif optimize_storage:
            # Use statistical data to approximate visualization
            # Calculate fire intensity and total burn area 
            stats = forest_model.history[frame]
            
            # For visualization purposes, we'll approximate using random distributions
            # This is not spatially accurate but gives a sense of fire spread
            if is_composite:
                # Create an approximated composite view
                frame_state = np.zeros((forest_model.grid_size, forest_model.grid_size), dtype=np.int8)
                
                # Calculate total cells in each state
                total_cells = forest_model.grid_size * forest_model.grid_size
                burning_frac = sum(stats['burning_count']) / (forest_model.num_layers * total_cells)
                burned_frac = sum(stats['burned_count']) / (forest_model.num_layers * total_cells)
                
                # Create a circular gradient from the center that grows with time
                y, x = np.ogrid[:forest_model.grid_size, :forest_model.grid_size]
                center = forest_model.grid_size // 2
                # Calculate distance from center scaled by time step
                max_radius = np.sqrt(2) * forest_model.grid_size / 2
                spread_factor = min(1.0, (frame + 1) / (len(forest_model.history) / 2))
                radius = max_radius * spread_factor
                
                # Create burning ring at the edge of the fire
                ring_width = max(2, int(forest_model.grid_size * 0.05))  # 5% of grid as ring width
                dist_from_center = np.sqrt((x - center)**2 + (y - center)**2)
                
                # Burning ring
                burning_mask = (dist_from_center <= radius) & (dist_from_center >= radius - ring_width)
                # Burned interior
                burned_mask = (dist_from_center < radius - ring_width)
                
                # Apply masks to frame state
                frame_state[burning_mask] = CellState.BURNING.value
                frame_state[burned_mask] = CellState.BURNED.value
            else:
                # Display specific layer with statistical approximation
                frame_state = np.zeros((forest_model.grid_size, forest_model.grid_size), dtype=np.int8)
                burning_count = stats['burning_count'][layer_idx]
                burned_count = stats['burned_count'][layer_idx]
                total_cells = forest_model.grid_size * forest_model.grid_size
                
                # Similar circular approximation but for specific layer
                y, x = np.ogrid[:forest_model.grid_size, :forest_model.grid_size]
                center = forest_model.grid_size // 2
                max_radius = np.sqrt(2) * forest_model.grid_size / 2
                spread_factor = min(1.0, (frame + 1) / (len(forest_model.history) / 2))
                radius = max_radius * spread_factor
                
                ring_width = max(2, int(forest_model.grid_size * 0.05))
                dist_from_center = np.sqrt((x - center)**2 + (y - center)**2)
                
                burning_mask = (dist_from_center <= radius) & (dist_from_center >= radius - ring_width)
                burned_mask = (dist_from_center < radius - ring_width)
                
                frame_state[burning_mask] = CellState.BURNING.value
                frame_state[burned_mask] = CellState.BURNED.value
        else:
            # Use precomputed frame data
            frame_state = frame_data[frame]
            stats = forest_model.history[frame]
        
        # Update the plot data
        im.set_array(frame_state)
        
        # Update title with basic information
        title.set_text(f"Time Step: {frame}")
        
        # Update statistics panel
        if show_stats:
            stats_info = get_formatted_stats(stats)
            stats_text.set_text(stats_info)
            
        return [im, title] + ([stats_text] if show_stats else [])
    
    # Create the animation
    ani = animation.FuncAnimation(fig, update, frames=len(forest_model.history),
                                 interval=frame_interval_ms, blit=True)
    
    # Show the animation
    plt.tight_layout()
    plt.show()
    
    return ani

def visualize_fire_spread_interactive(forest_model):
    """
    Create an interactive visualization of the fire spread.
    
    Args:
        forest_model (ForestModel): The forest model after simulation
    """
    # Create a figure with subplots
    fig = plt.figure(figsize=(12, 8))
    
    # Add a 2D view of the fire spread
    ax1 = fig.add_subplot(121)
    
    # Define colors for each state
    cmap = colors.ListedColormap(['green', 'red', 'black'])
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = colors.BoundaryNorm(bounds, cmap.N)
    
    # Create a composite view of all layers (maximum state value)
    composite = np.zeros((forest_model.grid_size, forest_model.grid_size), dtype=np.int8)
    for z in range(forest_model.num_layers):
        composite = np.maximum(composite, forest_model.layers[z])
    
    # Plot the composite view
    im = ax1.imshow(composite, cmap=cmap, norm=norm)
    ax1.set_title("Composite View (All Layers)")
    ax1.set_xlabel("X")
    ax1.set_ylabel("Y")
    
    # Add a 3D view of the fire spread
    ax2 = fig.add_subplot(122, projection='3d')
    
    # Define colors for each state
    colors_map = {
        CellState.UNBURNED.value: 'green',
        CellState.BURNING.value: 'red',
        CellState.BURNED.value: 'black'
    }
    
    # Create meshgrid for coordinates
    x = np.arange(forest_model.grid_size)
    y = np.arange(forest_model.grid_size)
    xx, yy = np.meshgrid(x, y)
    
    # Plot each layer
    for z in range(forest_model.num_layers):
        # Get the layer data
        layer = forest_model.layers[z]
        
        # Plot burning and burned cells
        for state in [CellState.BURNING.value, CellState.BURNED.value]:
            mask = (layer == state)
            if np.any(mask):
                ax2.scatter(xx[mask], yy[mask], z * np.ones_like(xx)[mask],
                           c=colors_map[state], marker='s', alpha=0.7)
    
    # Set labels and title
    ax2.set_xlabel('X')
    ax2.set_ylabel('Y')
    ax2.set_zlabel('Layer')
    ax2.set_title("3D View")
    
    # Set axis limits
    ax2.set_xlim(0, forest_model.grid_size-1)
    ax2.set_ylim(0, forest_model.grid_size-1)
    ax2.set_zlim(0, forest_model.num_layers-1)
    
    # Add a legend
    legend_elements = [
        Line2D([0], [0], marker='s', color='w', markerfacecolor='red', markersize=10, label='Burning'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='black', markersize=10, label='Burned')
    ]
    ax2.legend(handles=legend_elements, loc='upper right')
    
    # Add a title
    fig.suptitle(f"Fire Spread Simulation (Resolution: {MODEL_RESOLUTION}m)")
    
    # Adjust layout
    plt.tight_layout()
    
    # Show the plot
    plt.show()
    
    return fig

def visualize_terrain_and_wind(forest_model):
    """
    Visualize terrain elevation and wind field.
    
    Args:
        forest_model (ForestModel): The forest model with terrain and wind data
    """
    # Check if terrain data is available
    if not hasattr(forest_model, 'terrain') or forest_model.terrain is None:
        print("No terrain data available for visualization")
        return
    
    # Create a figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Plot terrain elevation
    terrain_plot = ax1.imshow(forest_model.terrain, cmap='terrain')
    ax1.set_title("Terrain Elevation")
    ax1.set_xlabel("X")
    ax1.set_ylabel("Y")
    
    # Add a colorbar for terrain
    cbar1 = fig.colorbar(terrain_plot, ax=ax1)
    cbar1.set_label("Elevation (m)")
    
    # Plot wind field
    # Subsample the wind field for better visualization
    skip = max(1, forest_model.grid_size // 20)
    x = np.arange(0, forest_model.grid_size, skip)
    y = np.arange(0, forest_model.grid_size, skip)
    X, Y = np.meshgrid(x, y)
    
    # Get wind components at subsampled points
    U = forest_model.wind_u[::skip, ::skip]
    V = forest_model.wind_v[::skip, ::skip]
    
    # Calculate wind speed for color mapping
    wind_speed = np.sqrt(U**2 + V**2)
    
    # Plot wind vectors
    wind_plot = ax2.quiver(X, Y, U, V, wind_speed, cmap='viridis',
                         scale=30, width=0.002, headwidth=3, headlength=4)
    ax2.set_title("Wind Field")
    ax2.set_xlabel("X")
    ax2.set_ylabel("Y")
    
    # Add a colorbar for wind speed
    cbar2 = fig.colorbar(wind_plot, ax=ax2)
    cbar2.set_label("Wind Speed")
    
    # Add a title
    fig.suptitle(f"Terrain and Wind Visualization (Resolution: {MODEL_RESOLUTION}m)")
    
    # Adjust layout
    plt.tight_layout()
    
    # Show the plot
    plt.show()

    return fig

def initialize_fuel_load(forest_model):
    """
    Initialize the fuel load in the forest model based on the specified method.
    
    Args:
        forest_model (ForestModel): The forest model to initialize
    """
    print(f"Initializing fuel load using method: {FUEL_LOAD_METHOD}")
    
    if FUEL_LOAD_METHOD == 'random':
        # Random fuel load distribution
        for z in range(forest_model.num_layers):
            forest_model.fuel_load[z] = np.random.uniform(
                MIN_FUEL_VALUE, MAX_FUEL_VALUE, 
                (forest_model.grid_size, forest_model.grid_size)
            )
        print(f"Initialized random fuel load: {MIN_FUEL_VALUE}-{MAX_FUEL_VALUE}")
        
    elif FUEL_LOAD_METHOD == 'gradient':
        # Gradient fuel load (decreasing with height)
        for z in range(forest_model.num_layers):
            # Calculate layer factor (decreasing with height)
            layer_factor = max(0.1, 1.0 - (z / forest_model.num_layers) * 0.8)
            forest_model.fuel_load[z] = np.random.uniform(
                MIN_FUEL_VALUE, MAX_FUEL_VALUE, 
                (forest_model.grid_size, forest_model.grid_size)
            ) * layer_factor
        print(f"Initialized gradient fuel load (decreasing with height)")
        
    elif FUEL_LOAD_METHOD == 'constant':
        # Constant fuel load
        for z in range(forest_model.num_layers):
            forest_model.fuel_load[z].fill(CONSTANT_FUEL_LOAD)
        print(f"Initialized constant fuel load: {CONSTANT_FUEL_LOAD}")
        
    elif FUEL_LOAD_METHOD == 'layer_specific':
        # Layer-specific fuel load
        for z in range(forest_model.num_layers):
            # Use the specified value for this layer, or the last defined value
            layer_value = LAYER_FUEL_LOADS[min(z, len(LAYER_FUEL_LOADS)-1)]
            forest_model.fuel_load[z].fill(layer_value)
        print(f"Initialized layer-specific fuel load: {LAYER_FUEL_LOADS}")
        
    else:
        # Default to random if method not recognized
        print(f"Unrecognized fuel load method: {FUEL_LOAD_METHOD}")
        print(f"Falling back to random fuel load")
        for z in range(forest_model.num_layers):
            forest_model.fuel_load[z] = np.random.uniform(
                MIN_FUEL_VALUE, MAX_FUEL_VALUE, 
                (forest_model.grid_size, forest_model.grid_size)
            )
    
    # Print fuel load statistics
    for z in range(forest_model.num_layers):
        min_fuel = np.min(forest_model.fuel_load[z])
        max_fuel = np.max(forest_model.fuel_load[z])
        mean_fuel = np.mean(forest_model.fuel_load[z])
        print(f"Layer {z}: Min={min_fuel:.2f}, Max={max_fuel:.2f}, Mean={mean_fuel:.2f}")

def sigmoid_ignition(fuel_load, k, threshold):
    """
    Calculate ignition probability using a sigmoid function.
    
    Args:
        fuel_load (float): Amount of fuel in the cell (0.0-1.0)
        k (float): Steepness of the sigmoid curve
        threshold (float): Inflection point of the sigmoid
        
    Returns:
        float: Ignition probability (0.0-1.0)
    """
    # Sigmoid function: 1 / (1 + e^(-k * (x - threshold)))
    return 1.0 / (1.0 + np.exp(-k * (fuel_load - threshold)))

def sigmoid_ignition_neighbors(n_burning, k, threshold):
    """
    Calculate ignition probability using a sigmoid function based on number of burning neighbors.
    
    Args:
        n_burning (int): Number of burning neighbors
        k (float): Steepness of the sigmoid curve
        threshold (float): Critical number of burning neighbors needed for significant probability
        
    Returns:
        float: Ignition probability (0.0-1.0)
    """
    # Sigmoid function: 1 / (1 + e^(-k * (N_burning - threshold)))
    return 1.0 / (1.0 + np.exp(-k * (n_burning - threshold)))

def main():
    """
    Run the forest fire cellular automata simulation.
    
    This function initializes the forest model, runs the simulation, analyzes results,
    and visualizes the fire spread.
    """
    # Make sure we're accessing the global variables
    global WIND_TYPE, FUEL_LOAD_METHOD  # Allow modifying these global variables if needed
    
    # ---------------------------------------------------------------------
    # Memory Management Parameters
    # ---------------------------------------------------------------------
    # Control memory optimization features for large simulations

    # Whether to use memory optimizations (False = use standard ForestModel)
    USE_MEMORY_OPTIMIZATIONS = False

    # Memory optimization level (0-3)
    # 0: No optimization (full memory usage)
    # 1: Basic optimization (30% reduction)
    # 2: Medium optimization (60% reduction)
    # 3: Maximum optimization (80-90% reduction)
    MEMORY_OPTIMIZATION_LEVEL = 2

    # Disk-based storage settings
    USE_DISK_STORAGE = False  # Whether to use disk-based storage for history
    DISK_STORAGE_DIR = "./simulation_data"  # Directory for disk storage
    CACHE_SIZE_MB = 1024  # Memory cache size when using disk storage (MB)

    # Multi-resolution grid settings
    USE_MULTI_RESOLUTION = False  # Whether to use multi-resolution grid
    MAX_RESOLUTION_LEVELS = 3  # Maximum number of resolution levels
    
    # Print a banner and key information
    print("\n" + "="*80)
    print("FOREST FIRE CELLULAR AUTOMATA SIMULATION".center(80))
    print("="*80)
    
    # Multi-dataset tiled LiDAR usage instructions
    if FUEL_LOAD_METHOD == 'tiled_lidar':
        print("\nMULTI-DATASET TILED LIDAR INTEGRATION MODE")
        print("-" * 50)
        print("This simulation will integrate multiple LiDAR datasets from:")
        print(f"  {LIDAR_RASTER_BASE_DIR}")
        print("\nEach subdirectory is treated as a separate LiDAR dataset.")
        print("The model will automatically:")
        print("  1. Find all raster files across all dataset folders")
        print("  2. Calculate the combined geographic extent")
        print("  3. Detect the maximum vegetation height and set layers accordingly")
        print("  4. Create a forest model covering this entire area")
        print("  5. Divide the area into tiles and assign data from the most appropriate dataset(s)")
        print("\nTo change the integrated area, modify:")
        print("  - LIDAR_RASTER_BASE_DIR: Parent directory containing all dataset folders")
        print("  - MODEL_RESOLUTION: Cell size in meters (larger = faster but less detail)")
        print("  - LAYER_HEIGHT_METERS: Height of each vegetation layer (affects vertical resolution)")
        print("  - TILED_LIDAR_TILE_SIZE: Size of each tile in meters")
        print("  - TILED_LIDAR_OVERLAP: Overlap between tiles in meters")
        print("-" * 50 + "\n")
    
    # Print current parameters
    print("\nCurrent parameters:")
    print(f"GRID_SIZE: {GRID_SIZE}")
    print(f"NUM_LAYERS: {NUM_LAYERS}")
    print(f"LAYER_HEIGHT_METERS: {LAYER_HEIGHT_METERS}")
    print(f"WIND_TYPE: {WIND_TYPE}")
    print(f"IGNITION_METHOD: {IGNITION_METHOD}")
    print(f"FUEL_LOAD_METHOD: {FUEL_LOAD_METHOD}")
    print(f"VISUALIZATION_MODE: {VISUALIZATION_MODE}")
    print(f"USE_MEMORY_OPTIMIZATIONS: {USE_MEMORY_OPTIMIZATIONS}")
    
    if USE_MEMORY_OPTIMIZATIONS:
        print(f"MEMORY_OPTIMIZATION_LEVEL: {MEMORY_OPTIMIZATION_LEVEL}")
        print(f"USE_DISK_STORAGE: {USE_DISK_STORAGE}")
        print(f"USE_MULTI_RESOLUTION: {USE_MULTI_RESOLUTION}")
    
    # Print file paths and saving settings
    print(f"\nLiDAR base directory: {LIDAR_RASTER_BASE_DIR}")
            print("\n==== USING MEMORY-OPTIMIZED FOREST MODEL ====")
            print(f"Memory optimization level: {MEMORY_OPTIMIZATION_LEVEL}")
            print(f"Disk storage: {'Enabled' if USE_DISK_STORAGE else 'Disabled'}")
            print(f"Multi-resolution grid: {'Enabled' if USE_MULTI_RESOLUTION else 'Disabled'}")
            
            forest_model = MemoryOptimizedForestModel(
                grid_size=GRID_SIZE, 
                num_layers=NUM_LAYERS,
                layer_height_meters=LAYER_HEIGHT_METERS,
                memory_optimization_level=MEMORY_OPTIMIZATION_LEVEL,
                use_disk_storage=USE_DISK_STORAGE,
                disk_storage_dir=DISK_STORAGE_DIR,
                cache_size_mb=CACHE_SIZE_MB,
                use_multi_resolution=USE_MULTI_RESOLUTION,
                max_resolution_levels=MAX_RESOLUTION_LEVELS
            )
            
        # Initialize with the specified method
        initialize_fuel_load(forest_model)
    
    # Load terrain data if we're using terrain-integrated wind
    if WIND_TYPE == 'terrain_integrated':
        # Load terrain data
        print("\nLoading terrain data for terrain-integrated wind...")
        
        # For the tiled approach with multiple datasets, there are several options for dem.tif:
        terrain_file = None
        
        # Option 1: Look for a general dem.tif in the base directory
        base_dem_path = os.path.join(LIDAR_RASTER_BASE_DIR, 'dem.tif')
        if os.path.exists(base_dem_path):
            terrain_file = base_dem_path
            print(f"Using DEM from base directory: {terrain_file}")
        
        # Option 2: If LIDAR_AREA_NAME is set, try to find dem.tif in that specific dataset
        elif LIDAR_AREA_NAME:
            dataset_dem_path = os.path.join(LIDAR_RASTER_BASE_DIR, LIDAR_AREA_NAME, 'dem.tif')
            if os.path.exists(dataset_dem_path):
                terrain_file = dataset_dem_path
                print(f"Using DEM from specific dataset: {terrain_file}")
            
            # Also check in the rasters subfolder
            else:
                rasters_dem_path = os.path.join(LIDAR_RASTER_BASE_DIR, LIDAR_AREA_NAME, 'rasters', 'dem.tif')
                if os.path.exists(rasters_dem_path):
                    terrain_file = rasters_dem_path
                    print(f"Using DEM from rasters subfolder: {terrain_file}")
        
        # Option 3: Look for dem.tif in any dataset's directory
        if terrain_file is None:
            # Find all potential dataset directories
            dataset_dirs = [d for d in os.listdir(LIDAR_RASTER_BASE_DIR) 
                           if os.path.isdir(os.path.join(LIDAR_RASTER_BASE_DIR, d))]
            
            # Search each dataset directory for dem.tif
            for dataset in dataset_dirs:
                dem_path = os.path.join(LIDAR_RASTER_BASE_DIR, dataset, 'dem.tif')
                if os.path.exists(dem_path):
                    terrain_file = dem_path
                    print(f"Using DEM from dataset {dataset}: {terrain_file}")
                    break
                
                # Also check in rasters subfolder
                rasters_dem_path = os.path.join(LIDAR_RASTER_BASE_DIR, dataset, 'rasters', 'dem.tif')
                if os.path.exists(rasters_dem_path):
                    terrain_file = rasters_dem_path
                    print(f"Using DEM from dataset {dataset} rasters subfolder: {terrain_file}")
                    break
                    
        # Load DEM if found
        if terrain_file and os.path.exists(terrain_file):
            forest_model.load_terrain_data(
                terrain_file_path=terrain_file,
                no_data_value=-9999
            )
        else:
            print(f"Warning: No terrain file (dem.tif) found in any dataset directory!")
            print("Falling back to uniform wind...")
            WIND_TYPE = 'uniform'
    
    # Initialize wind settings
    print("\nInitializing wind...")
    if WIND_TYPE == 'uniform':
        forest_model.initialize_wind(TRADE_WIND_DIRECTION, TRADE_WIND_STRENGTH)
    elif WIND_TYPE == 'terrain_integrated':
        # We've already loaded terrain data, now calculate terrain-influenced wind
        forest_model.initialize_terrain_wind(
            trade_wind_direction=TRADE_WIND_DIRECTION,
            trade_wind_strength=TRADE_WIND_STRENGTH,
            terrain_effect_strength=TERRAIN_WIND_EFFECT,
            barranco_threshold=BARRANCO_THRESHOLD,
            barranco_amplification=BARRANCO_AMPLIFICATION
        )
        
        # Visualize terrain and wind field before simulation
        if VISUALIZATION_MODE != 'none':
            visualize_terrain_and_wind(forest_model)
    
    # Set initial ignition based on specified method
    print("\nSetting initial ignition...")
    if IGNITION_METHOD == 'center':
        # Single ignition point at center of the grid, bottom layer
        center = forest_model.grid_size // 2
        forest_model.set_ignition(center, center, 0)
    elif IGNITION_METHOD == 'random':
        # Random ignition points across the bottom layer
        for _ in range(NUM_IGNITION_POINTS):
            x = random.randint(0, forest_model.grid_size - 1)
            y = random.randint(0, forest_model.grid_size - 1)
            z = 0  # Bottom layer
            forest_model.set_ignition(x, y, z)
    elif IGNITION_METHOD == 'edge':
        # Ignition points along one edge of the grid
        edge_cells = []
        
        # Choose a random edge (0=top, 1=right, 2=bottom, 3=left, None=random)
        edge = IGNITION_EDGE if IGNITION_EDGE is not None else random.randint(0, 3)
        
        if edge == 0:  # Top edge
            edge_cells = [(0, y, 0) for y in range(forest_model.grid_size)]
        elif edge == 1:  # Right edge
            edge_cells = [(x, forest_model.grid_size-1, 0) for x in range(forest_model.grid_size)]
        elif edge == 2:  # Bottom edge
            edge_cells = [(forest_model.grid_size-1, y, 0) for y in range(forest_model.grid_size)]
        else:  # Left edge
            edge_cells = [(x, 0, 0) for x in range(forest_model.grid_size)]
        
        # Sample from these edge cells
        sampled_cells = random.sample(edge_cells, min(NUM_IGNITION_POINTS, len(edge_cells)))
        for x, y, z in sampled_cells:
            forest_model.set_ignition(x, y, z)
    
    # Run the simulation
    print("\nRunning simulation...")
    if isinstance(forest_model, MemoryOptimizedForestModel):
        # Use parallel processing for memory-optimized model
        forest_model.run_simulation(
            max_steps=NUM_STEPS, 
            stop_when_fire_extinguished=STOP_WHEN_FIRE_EXTINGUISHED,
            use_parallel=USE_PARALLEL_PROCESSING,
            num_workers=NUM_PARALLEL_WORKERS
        )
    else:
        # Standard model doesn't support parallel processing
        forest_model.run_simulation(
            NUM_STEPS, 
            store_full_states=STORE_FULL_STATES
        )
    
    # Analyze the results
    fire_area, burn_pattern = analyze_fire_spread(forest_model)
    print(f"\nFire spread analysis complete.")
    print(f"Total burn area: {fire_area:.2f} sq. m ({fire_area/10000:.2f} hectares)")
    print(f"Burn pattern: {burn_pattern}")
    
    # Visualize the results
    if VISUALIZATION_MODE != 'none':
        print("\nVisualizing results...")
        if VISUALIZATION_MODE == 'static_2d':
            visualize_fire_spread_2d(forest_model)
        elif VISUALIZATION_MODE == 'static_3d':
            visualize_fire_spread_3d(forest_model)
        elif VISUALIZATION_MODE == 'animation':
            visualize_fire_spread_animation(
                forest_model,
                frame_interval_ms=ANIMATION_FRAME_INTERVAL_MS,
                display_layer=ANIMATION_DISPLAY_LAYER,
                show_stats=ANIMATION_SHOW_STATS,
                optimize_storage=ANIMATION_OPTIMIZE_STORAGE
            )
        elif VISUALIZATION_MODE == 'animation_3d':
            visualize_fire_spread_animation_3d(
                forest_model,
                frame_interval_ms=ANIMATION_FRAME_INTERVAL_MS,
                show_stats=ANIMATION_SHOW_STATS,
                elevation_factor=ANIMATION_3D_ELEVATION_FACTOR,
                view_angle=ANIMATION_3D_VIEW_ANGLE
            )
        elif VISUALIZATION_MODE == 'interactive':
            visualize_fire_spread_interactive(forest_model)
        else:
            print(f"Warning: Unknown visualization mode {VISUALIZATION_MODE}")
    
    # Save the results if enabled
    if SAVE_RESULTS:
        print("\nSaving results...")
        
        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(RESULTS_DIR, f"sim_{timestamp}")
        
        # Use the comprehensive save_results method
        output_dir = forest_model.save_results(output_dir)
        
        # Save final state visualization if available
        if VISUALIZATION_MODE != 'none' and plt.get_fignums():
            vis_dir = os.path.join(output_dir, "visualizations")
            os.makedirs(vis_dir, exist_ok=True)
            plt.savefig(os.path.join(vis_dir, "final_state.png"), dpi=300)
            print(f"Final state visualization saved to: {vis_dir}")
    
    print("\nSimulation complete!")
    return forest_model
        
def visualize_fire_spread_animation_3d(forest_model, frame_interval_ms=300, show_stats=True, elevation_factor=1.5, view_angle=None, downsample_factor=1, alpha_unburned=0.1):
    """
    Create a presentation-ready 3D animation of fire spread across all forest layers.
    
    Args:
        forest_model (ForestModel): The forest model after simulation
        frame_interval_ms (int): Milliseconds between animation frames
        show_stats (bool): Whether to display statistics on the animation
        elevation_factor (float): Factor to increase vertical spacing for better visualization
        view_angle (tuple): Initial view angle as (elevation, azimuth) in degrees or None for default
        downsample_factor (int): Factor to downsample large grids for better performance (1 = no downsampling)
        alpha_unburned (float): Transparency for unburned cells (0-1), lower values make fire more visible
        
    Returns:
        animation.FuncAnimation: Animation object
    """
    # Check if we have history data
    if not forest_model.history:
        print("No history data available for animation")
        return None
    
    # Check if full states were stored
    has_full_states = forest_model.store_full_states and 'grid_states' in forest_model.history[0]
    if not has_full_states:
        print("WARNING: Full states were not stored during simulation.")
        print("The 3D animation will use statistical approximation which may not be spatially accurate.")
        print("Consider rerunning with STORE_FULL_STATES = True for best presentation quality.")
    
    # Calculate downsampling factor automatically if grid is large and no downsampling specified
    if downsample_factor == 1 and forest_model.grid_size > 200:
        downsample_factor = max(1, forest_model.grid_size // 150)
        print(f"Large grid detected: Automatically setting downsample_factor to {downsample_factor}")
    
    # Calculate grid size after downsampling
    display_grid_size = forest_model.grid_size
    if downsample_factor > 1:
        display_grid_size = forest_model.grid_size // downsample_factor
        print(f"Downsampling grid from {forest_model.grid_size}x{forest_model.grid_size} to {display_grid_size}x{display_grid_size} for performance")
    
    # Create figure with improved layout for presentations
    fig = plt.figure(figsize=(18, 10), facecolor='white')
    
    # Add metadata for presentations
    metadata = {
        'Title': 'Forest Fire Cellular Automata Model',
        'Author': 'UvA Thesis Project',
        'Date': datetime.now().strftime("%Y-%m-%d"),
        'Resolution': f"{forest_model.model_resolution}m × {forest_model.model_resolution}m",
        'Grid Size': f"{forest_model.grid_size}×{forest_model.grid_size} cells",
        'Layers': f"{forest_model.num_layers} ({forest_model.layer_height_meters}m each)"
    }
    
    # Set up the layout with or without statistics panel
    if show_stats:
        # Create grid layout for main plot and stats panels
        gs = gridspec.GridSpec(3, 4, figure=fig, height_ratios=[3, 1, 1], width_ratios=[3, 1, 1, 1])
        
        # Main 3D plot - larger area now
        ax = fig.add_subplot(gs[0:3, 0:2], projection='3d')
        
        # Stats panel at top right
        stats_ax = fig.add_subplot(gs[0, 2:4])
        stats_ax.axis('off')  # Hide axis for stats panel
        
        # Layer breakdown chart in middle right
        layer_ax = fig.add_subplot(gs[1, 2:4])
        layer_ax.set_title("Fire Spread by Layer", fontsize=10, fontweight='bold')
        layer_ax.set_ylabel("% Affected")
        layer_ax.set_xlabel("Layer (height in meters)")
        
        # Fire spread over time chart in bottom right
        time_ax = fig.add_subplot(gs[2, 2:4])
        time_ax.set_title("Fire Spread Over Time", fontsize=10, fontweight='bold')
        time_ax.set_ylabel("Area (hectares)")
        time_ax.set_xlabel("Time Step")
    else:
        # Just a larger 3D visualization without stats
        ax = fig.add_subplot(111, projection='3d')
    
    # Apply better styling for presentations
    plt.style.use('default')  # Reset to default style
    for axis in [ax] + ([layer_ax, time_ax] if show_stats else []):
        axis.grid(alpha=0.3)
        for spine in axis.spines.values():
            spine.set_edgecolor('gray')
    
    # Set initial view angle for better visualization
    if view_angle:
        ax.view_init(elev=view_angle[0], azim=view_angle[1])
    else:
        # Default view angle optimized for forest fire visualization
        ax.view_init(elev=35, azim=45)
    
    # Define colors for each state with enhanced colors for presentations
    colors_map = {
        CellState.UNBURNED.value: (0.0, 0.5, 0.0, alpha_unburned),    # Dark green with transparency
        CellState.BURNING.value: (1.0, 0.3, 0.0, 0.9),                # Bright orange-red
        CellState.BURNED.value: (0.15, 0.15, 0.15, 0.7)               # Very dark gray, slightly transparent
    }
    
    # Create meshgrid for coordinates
    if downsample_factor > 1:
        # Create downsampled grid
        x = np.linspace(0, forest_model.grid_size-1, display_grid_size)
        y = np.linspace(0, forest_model.grid_size-1, display_grid_size)
    else:
        x = np.arange(forest_model.grid_size)
        y = np.arange(forest_model.grid_size)
    xx, yy = np.meshgrid(x, y)
    
    # Calculate layer height spacing
    layer_height = elevation_factor * forest_model.layer_height_meters / forest_model.model_resolution
    
    # Initialize scatter plots for each layer and state
    scatter_plots = {}
    for z in range(forest_model.num_layers):
        scatter_plots[z] = {}
        for state in [CellState.UNBURNED.value, CellState.BURNING.value, CellState.BURNED.value]:
            # Use larger markers for better visibility in presentations
            marker_size = 15 if state == CellState.BURNING.value else 10
            scatter_plots[z][state] = ax.scatter([], [], [], 
                                             c=[colors_map[state]], 
                                             marker='s' if state != CellState.BURNING.value else 'o',
                                             s=marker_size,
                                             alpha=colors_map[state][3],
                                             label=f"Layer {z} {CellState(state).name}")
    
    # Add enhanced legend with one entry per state
    legend_elements = [
        Line2D([0], [0], marker='s', color='w', markerfacecolor=(0.0, 0.5, 0.0), markersize=10, label='Unburned Vegetation'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=(1.0, 0.3, 0.0), markersize=10, label='Active Fire'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor=(0.15, 0.15, 0.15), markersize=10, label='Burned Area')
    ]
    ax.legend(handles=legend_elements, loc='upper right', framealpha=0.8, fontsize=9)
    
    # Set labels and title with proper formatting for presentations
    ax.set_xlabel('X Coordinate', fontsize=10, labelpad=10)
    ax.set_ylabel('Y Coordinate', fontsize=10, labelpad=10)
    ax.set_zlabel('Height (m)', fontsize=10, labelpad=10)
    title = ax.set_title(f"3D Forest Fire Simulation - Step 0", fontsize=14, fontweight='bold', y=1.02)
    
    # Set axis limits
    ax.set_xlim(0, forest_model.grid_size-1)
    ax.set_ylim(0, forest_model.grid_size-1)
    ax.set_zlim(0, (forest_model.num_layers-1) * layer_height * 1.1)  # Add some margin above
    
    # Add vertical scale with improved labels
    zticklabels = []
    zticks = []
    for z in range(forest_model.num_layers):
        min_height = z * forest_model.layer_height_meters
        max_height = (z + 1) * forest_model.layer_height_meters
        zticklabels.append(f"{min_height:.0f}-{max_height:.0f}m")
        zticks.append(z * layer_height)
    
    ax.set_zticks(zticks)
    ax.set_zticklabels(zticklabels)
    
    # Add terrain grid for better depth perception
    # This creates a clearer representation of the 3D space
    for z in range(forest_model.num_layers):
        z_height = z * layer_height
        # Create more subtle but visible grid plane
        xx_plane, yy_plane = np.meshgrid([0, forest_model.grid_size-1], [0, forest_model.grid_size-1])
        zz_plane = np.full_like(xx_plane, z_height)
        ax.plot_surface(xx_plane, yy_plane, zz_plane, alpha=0.08, color='gray', shade=False)
        
        # Add height label directly in 3D space for clarity
        ax.text(0, forest_model.grid_size-1, z_height, 
                f"{int(z*forest_model.layer_height_meters)}m", 
                fontsize=8, color='gray', ha='left', va='bottom')
    
    # Initialize enhanced statistics displays
    if show_stats:
        # Create formatted stats text box with better styling
        stats_text = stats_ax.text(0.5, 0.5, "", ha='center', va='center', fontsize=10, 
                                 linespacing=1.3,
                                 bbox=dict(boxstyle='round,pad=1', facecolor='white', 
                                           alpha=0.9, edgecolor='lightgray'),
                                 transform=stats_ax.transAxes)
        
        # Initialize layer breakdown with gradient colors based on height
        # Using color gradient from green (low) to yellow to red (high)
        layer_colors = []
        for z in range(forest_model.num_layers):
            # Create color gradient based on height (red at top, green at bottom)
            r = min(1.0, z / (forest_model.num_layers - 1) * 0.8 + 0.2)
            g = min(1.0, 0.8 - z / forest_model.num_layers * 0.5)
            b = 0.0
            layer_colors.append((r, g, b))
        
        # Create bar chart with improved height labels
        height_labels = [f"{int(z*forest_model.layer_height_meters)}-{int((z+1)*forest_model.layer_height_meters)}m" 
                         for z in range(forest_model.num_layers)]
        
        layer_bars = layer_ax.bar(
            range(forest_model.num_layers),
            [0] * forest_model.num_layers,
            color=layer_colors
        )
        layer_ax.set_xticks(range(forest_model.num_layers))
        layer_ax.set_xticklabels(height_labels, rotation=45, ha='right', fontsize=8)
        layer_ax.set_ylim(0, 100)  # 0-100%
        
        # Add grid to bar chart for better readability
        layer_ax.grid(axis='y', alpha=0.3)
        
        # Initialize time series for fire spread
        time_steps = list(range(len(forest_model.history)))
        burned_areas = [0] * len(forest_model.history)
        burning_areas = [0] * len(forest_model.history)
        
        # Create more visually striking time series plot
        time_burned_line, = time_ax.plot([], [], '-', color='#303030', linewidth=2, label='Burned')
        time_burning_line, = time_ax.plot([], [], '-', color='#FF5500', linewidth=2, label='Burning')
        
        # Fill area under curves for better visual impact
        time_ax.fill_between([], [], color='#303030', alpha=0.2)
        time_ax.fill_between([], [], color='#FF5500', alpha=0.2)
        
        time_ax.legend(loc='upper left', framealpha=0.7)
        time_ax.set_xlim(0, max(10, len(forest_model.history)-1))
        
        # Add grid to time series for better readability
        time_ax.grid(alpha=0.3)
        
        # Precompute max area for y-axis limit
        max_area = 0
        for step in range(len(forest_model.history)):
            stats = forest_model.history[step]
            area = (stats['total_burned_area'] + stats['total_burning_area']) / 10000
            if area > max_area:
                max_area = area
        
        # Set y-axis limit with proper margins
        time_ax.set_ylim(0, max_area * 1.1)  # Add 10% margin
        
        # Add current time marker with more visibility
        time_marker, = time_ax.plot([0], [0], 'o', color='black', ms=8, zorder=5)
        
        # Initialize stats values with initial frame
        stats = forest_model.history[0]
        stats_info = get_formatted_stats(stats, forest_model)
        stats_text.set_text(stats_info)
        
        # Initialize layer breakdown with initial frame
        layer_percentages = []
        for z in range(forest_model.num_layers):
            layer_burning = stats['burning_count'][z]
            layer_burned = stats['burned_count'][z]
            layer_total = layer_burning + layer_burned + stats['unburned_count'][z]
            layer_percent = (layer_burning + layer_burned) / layer_total * 100 if layer_total > 0 else 0
            layer_percentages.append(layer_percent)
        
        for bar, percentage in zip(layer_bars, layer_percentages):
            bar.set_height(percentage)
        
        # Prepare time series data
        for step in range(len(forest_model.history)):
            stats = forest_model.history[step]
            burned_areas[step] = stats['total_burned_area'] / 10000  # Convert to hectares
            burning_areas[step] = stats['total_burning_area'] / 10000  # Convert to hectares
        
        # Create filled areas for more dramatic visualization
        time_ax.fill_between(time_steps, 0, burned_areas, color='#303030', alpha=0.2)
        time_ax.fill_between(time_steps, 0, burning_areas, color='#FF5500', alpha=0.2)
        
        # Update time series plot with initial data
        time_burned_line.set_data(time_steps[:1], burned_areas[:1])
        time_burning_line.set_data(time_steps[:1], burning_areas[:1])
        
        # Add a second y-axis showing percentage of total area
        total_area = forest_model.grid_size * forest_model.grid_size * forest_model.model_resolution**2 / 10000
        ax2 = time_ax.twinx()
        ax2.set_ylim(0, max_area * 100 / total_area * 1.1)
        ax2.set_ylabel('% of Total Area')
    
    # Helper function to get layer state matrix
    def get_layer_state(layer_idx, frame):
        """Get the state matrix for a specific layer and frame"""
        stats = forest_model.history[frame]
        
        if has_full_states:
            return stats['grid_states'][layer_idx]
        else:
            # Create improved approximation based on burning/burned counts
            layer = np.zeros((forest_model.grid_size, forest_model.grid_size), dtype=np.int8)
            burning_count = stats['burning_count'][layer_idx]
            burned_count = stats['burned_count'][layer_idx]
            
            # Create a more realistic pattern that takes into account previous frames
            # This avoids the simplistic circular pattern
            if frame > 0:
                # Base approximation on previous frame's pattern
                prev_frame = max(0, frame - 1)
                prev_layer = get_layer_state(layer_idx, prev_frame)
                
                # Start with previous burns
                layer[prev_layer == CellState.BURNED.value] = CellState.BURNED.value
                
                # Create burning front around burned cells
                from scipy.ndimage import binary_dilation
                burned_mask = (prev_layer == CellState.BURNED.value)
                burning_border = binary_dilation(burned_mask, iterations=1) & ~burned_mask
                
                # Apply probabilistic expansion
                if np.sum(burning_border) > 0:
                    # Scale to match current burning count
                    layer[burning_border] = CellState.BURNING.value
                    
                    # If we need more burning cells, add them randomly near existing ones
                    current_burning = np.sum(layer == CellState.BURNING.value)
                    if current_burning < burning_count:
                        wider_border = binary_dilation(burned_mask, iterations=2) & ~burned_mask & ~burning_border
                        # Randomly select additional cells
                        if np.any(wider_border):
                            prob_mask = np.random.random(wider_border.shape) * wider_border
                            # Get coordinates of potential cells
                            potential_cells = np.where(prob_mask > 0)
                            # Sort by probability value
                            sorted_indices = np.argsort(prob_mask[potential_cells])[::-1]
                            # Select top n cells needed
                            needed = min(burning_count - current_burning, len(sorted_indices))
                            if needed > 0:
                                for i in range(needed):
                                    idx = sorted_indices[i]
                                    y, x = potential_cells[0][idx], potential_cells[1][idx]
                                    layer[y, x] = CellState.BURNING.value
                return layer
            else:
                # For first frame, use simplified approach with ignition point
                # Try to detect ignition method from configuration
                # Default to center ignition
                center_x, center_y = forest_model.grid_size // 2, forest_model.grid_size // 2
                radius = np.sqrt(burning_count / np.pi)  # Approximate radius based on burning count
                
                y, x = np.ogrid[:forest_model.grid_size, :forest_model.grid_size]
                dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                
                # Create burning mask
                burning_mask = (dist_from_center <= radius)
                
                # Apply mask, but ensure we don't exceed the count
                if np.sum(burning_mask) > 0:
                    if np.sum(burning_mask) > burning_count and burning_count > 0:
                        # Randomly select subset
                        prob_mask = np.random.random(burning_mask.shape) * burning_mask
                        sorted_indices = np.argsort(prob_mask.flat)[::-1]
                        burning_mask.flat[sorted_indices[burning_count:]] = False
                    
                    layer[burning_mask] = CellState.BURNING.value
                
                return layer
    
    # Helper function to format statistics with enhanced presentation
    def get_formatted_stats(stats, model):
        """Format statistics for display with improved presentation"""
        # Calculate percentages and areas
        total_cells = sum(stats['unburned_count']) + sum(stats['burning_count']) + sum(stats['burned_count'])
        burned_percent = (stats['total_burned'] + stats['total_burning']) / total_cells * 100 if total_cells > 0 else 0
        burned_area = (stats['total_burned_area'] + stats['total_burning_area']) / 10000  # Convert to hectares
        active_area = stats['total_burning_area'] / 10000  # Convert to hectares
        total_area = model.grid_size * model.grid_size * model.model_resolution**2 / 10000  # Total area in hectares
        
        # Format time elapsed (assuming each step is approximately constant time)
        minutes_per_step = 5  # Estimate: each step is approximately 5 minutes in simulation time
        elapsed_time = stats['time_step'] * minutes_per_step
        hours = elapsed_time // 60
        minutes = elapsed_time % 60
        
        # Create more informative, better formatted stats display
        stats_lines = [
            "FIRE PROGRESSION STATISTICS",
            "═════════════════════════════",
            f"🕒 Simulation Time: Step {stats['time_step']} ({hours}h {minutes:02d}m)",
            f"🔥 Fire Spread: {burned_percent:.1f}% of study area",
            f"📏 Affected Area: {burned_area:.2f} ha of {total_area:.1f} ha total",
            f"🌋 Active Fire Front: {active_area:.2f} ha ({stats['total_burning']:,} cells)",
            "═════════════════════════════",
            "BURN STATS BY VEGETATION LAYER:",
            " ".join([f"L{z}: {stats['burned_count'][z]/sum(stats['unburned_count'][z] + stats['burning_count'][z] + stats['burned_count'][z])*100:.0f}%" 
                     for z in range(min(4, len(stats['burned_count'])))]),
            "═════════════════════════════",
            f"Resolution: {model.model_resolution}m/cell · Grid: {model.grid_size}×{model.grid_size}"
        ]
        
        return "\n".join(stats_lines)
    
    # Function to downsample a layer matrix more efficiently
    def downsample_layer(layer_matrix, factor):
        """Downsample layer matrix with priority to fire states"""
        if factor <= 1:
            return layer_matrix
        
        # Use a more efficient approach for large matrices
        h, w = layer_matrix.shape
        new_h, new_w = h // factor, w // factor
        downsampled = np.zeros((new_h, new_w), dtype=layer_matrix.dtype)
        
        # Create binary masks for each state
        burning_mask = (layer_matrix == CellState.BURNING.value)
        burned_mask = (layer_matrix == CellState.BURNED.value)
        
        # Reshape and compute max values
        # This is much faster than the loop approach for large grids
        for i in range(new_h):
            for j in range(new_w):
                # Extract block
                block = layer_matrix[i*factor:(i+1)*factor, j*factor:(j+1)*factor]
                # Priority: BURNING > BURNED > UNBURNED
                if np.any(block == CellState.BURNING.value):
                    downsampled[i, j] = CellState.BURNING.value
                elif np.any(block == CellState.BURNED.value):
                    downsampled[i, j] = CellState.BURNED.value
                else:
                    downsampled[i, j] = CellState.UNBURNED.value
        
        return downsampled
    
    # Animation update function with optimizations for presentations
    def update(frame):
        # Update the title
        title.set_text(f"3D Forest Fire Simulation - Step {frame}")
        updated_plots = [title]
        
        # Process each layer
        for z in range(forest_model.num_layers):
            # Get the layer state matrix
            layer = get_layer_state(z, frame)
            
            # Downsample if needed
            if downsample_factor > 1:
                layer = downsample_layer(layer, downsample_factor)
            
            # Calculate height for this layer
            z_height = z * layer_height
            
            # Update scatter plots for each state
            for state in [CellState.UNBURNED.value, CellState.BURNING.value, CellState.BURNED.value]:
                mask = (layer == state)
                
                # Only process if this state has cells or if it's not unburned (always show burning/burned)
                if np.any(mask) or state != CellState.UNBURNED.value:
                    if np.any(mask):
                        # For more efficient rendering
                        if state == CellState.UNBURNED.value:
                            # For unburned, show a sparse subset to reduce point count but maintain forest feel
                            if downsample_factor <= 1:  # Only do this if not already downsampling
                                sample_rate = 0.05  # Show only 5% of unburned cells for better performance
                                rnd_mask = np.random.random(mask.shape) < sample_rate
                                mask = mask & rnd_mask
                        
                        # Extract coordinates
                        y_coords, x_coords = np.where(mask)
                        
                        if downsample_factor > 1:
                            # Scale coordinates to match original grid
                            x_coords = x_coords * downsample_factor + downsample_factor//2
                            y_coords = y_coords * downsample_factor + downsample_factor//2
                        
                        # Create z-coordinates with slight jitter for more natural forest look
                        if state == CellState.UNBURNED.value:
                            # Add small random height variation to unburned cells for more natural forest look
                            z_coords = np.full_like(x_coords, z_height)
                            z_coords = z_coords + np.random.uniform(-0.05, 0.05, size=len(z_coords))
                        else:
                            z_coords = np.full_like(x_coords, z_height)
                        
                        # Update scatter plot
                        scatter_plots[z][state]._offsets3d = (x_coords, y_coords, z_coords)
                    else:
                        # Clear scatter plot if no cells
                        scatter_plots[z][state]._offsets3d = ([], [], [])
                
                # Add to updated plots list
                updated_plots.append(scatter_plots[z][state])
        
        # Update statistics displays if showing stats
        if show_stats:
            stats = forest_model.history[frame]
            
            # Update text statistics
            stats_info = get_formatted_stats(stats, forest_model)
            stats_text.set_text(stats_info)
            updated_plots.append(stats_text)
            
            # Update layer breakdown chart
            layer_percentages = []
            for z in range(forest_model.num_layers):
                layer_burning = stats['burning_count'][z]
                layer_burned = stats['burned_count'][z]
                layer_total = layer_burning + layer_burned + stats['unburned_count'][z]
                layer_percent = (layer_burning + layer_burned) / layer_total * 100 if layer_total > 0 else 0
                layer_percentages.append(layer_percent)
            
            for bar, percentage in zip(layer_bars, layer_percentages):
                bar.set_height(percentage)
                updated_plots.append(bar)
            
            # Update time series showing progression
            time_burned_line.set_data(time_steps[:frame+1], burned_areas[:frame+1])
            time_burning_line.set_data(time_steps[:frame+1], burning_areas[:frame+1])
            time_marker.set_data([frame], [burned_areas[frame] + burning_areas[frame]])
            
            # Update the filled areas
            time_ax.collections.clear()  # Clear previous fills
            time_ax.fill_between(time_steps[:frame+1], 0, burned_areas[:frame+1], color='#303030', alpha=0.2)
            time_ax.fill_between(time_steps[:frame+1], 0, burning_areas[:frame+1], color='#FF5500', alpha=0.2)
            
            updated_plots.extend([time_burned_line, time_burning_line, time_marker])
        
        return updated_plots
    
    # Create animation with blitting for performance
    ani = animation.FuncAnimation(fig, update, frames=len(forest_model.history),
                                 interval=frame_interval_ms, blit=True)
    
    # Add rotation functionality
    def rotate(event):
        # Smooth rotation of the 3D plot
        elev, azim = ax.elev, ax.azim
        ax.view_init(elev=elev, azim=(azim + 1) % 360)
        fig.canvas.draw_idle()
    
    # Create enhanced toolbar with presentation controls
    rotation_toggle = False
    
    def toggle_rotation(event):
        nonlocal rotation_toggle
        rotation_toggle = not rotation_toggle
        if rotation_toggle:
            # Start rotation
            timer = fig.canvas.new_timer(interval=100)
            timer.add_callback(rotate, None)
            timer.start()
            rotation_button.label.set_text('Stop Rotation')
        else:
            # Stop all timers
            for timer in fig.canvas.timer_callbacks:
                if timer.callback == rotate:
                    timer.stop()
            rotation_button.label.set_text('Start Rotation')
        fig.canvas.draw_idle()
    
    # Add reset view button
    def reset_view(event):
        # Reset to default view
        if view_angle:
            ax.view_init(elev=view_angle[0], azim=view_angle[1])
        else:
            ax.view_init(elev=35, azim=45)
        fig.canvas.draw_idle()
    
    # Add export to MP4 functionality with progress feedback
    def save_animation(event):
        from matplotlib.animation import FFMpegWriter
        
        # Create default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"forest_fire_3d_{timestamp}.mp4"
        
        try:
            # Save animation with progress updates
            save_button.label.set_text('Saving...')
            fig.canvas.draw_idle()
            
            # Create writer with higher quality settings for presentations
            writer = FFMpegWriter(fps=1000//frame_interval_ms, metadata=metadata, 
                                 bitrate=5000, codec='h264')
            
            ani.save(filename, writer=writer)
            
            save_button.label.set_text('Saved!')
            print(f"Animation saved to: {filename}")
        except Exception as e:
            save_button.label.set_text('Save Failed')
            print(f"Error saving animation: {str(e)}")
        
        # Reset button after delay
        timer = fig.canvas.new_timer(interval=2000)
        timer.add_callback(lambda: save_button.label.set_text('Save MP4'))
        timer.single_shot = True
        timer.start()
    
    # Add better styled buttons with improved layout
    button_props = dict(color='0.85', hovercolor='0.95')
    
    # Control panel area
    button_area = fig.add_axes([0.01, 0.01, 0.98, 0.05])
    button_area.axis('off')
    
    # Add buttons in different positions
    rotation_ax = fig.add_axes([0.05, 0.01, 0.15, 0.04])
    rotation_button = Button(rotation_ax, 'Start Rotation', color='lightblue')
    rotation_button.on_clicked(toggle_rotation)
    
    reset_ax = fig.add_axes([0.25, 0.01, 0.15, 0.04])
    reset_button = Button(reset_ax, 'Reset View', color='lightgray')
    reset_button.on_clicked(reset_view)
    
    save_ax = fig.add_axes([0.8, 0.01, 0.15, 0.04])
    save_button = Button(save_ax, 'Save MP4', color='lightgreen')
    save_button.on_clicked(save_animation)
    
    # Add title to the figure for presentation context
    fig.suptitle("Forest Fire Cellular Automata Simulation", fontsize=16, fontweight='bold')
    
    # Show the animation
    plt.tight_layout(rect=[0, 0.06, 1, 0.95])  # Leave room for title and buttons
    plt.show()
    
    return ani

# Standard Python entry point
if __name__ == "__main__":
    print("Calling main() function...")
    main()

# ==============================================================================
# MEMORY-OPTIMIZED FOREST MODEL CLASS
# ==============================================================================

class MemoryOptimizedForestModel(ForestModel):
    """
    Memory-optimized version of the forest fire model that extends 
    the standard ForestModel with advanced memory management features.
    
    Key features:
    - Multi-resolution grid support for optimized spatial representation
    - Disk-based storage for large simulations
    - Tiered history storage to minimize memory usage
    - Integration with TileManager for large-area processing
    
    This model can handle significantly larger simulation areas while
    using less memory than the standard ForestModel.
    """
    
    def __init__(self, grid_size=100, num_layers=10, layer_height_meters=LAYER_HEIGHT_METERS,
                 memory_optimization_level=2, use_tiling=False, tile_size=500, tile_overlap=50,
                 use_disk_storage=False, disk_storage_dir="./simulation_data", cache_size_mb=1024,
                 use_multi_resolution=False, max_resolution_levels=3):
        """
        Initialize a memory-optimized forest model.
        
        Args:
            grid_size: Size of the grid as (width, height) or single value for square grid
            num_layers: Number of vertical layers to model
            layer_height_meters: Height of each layer in meters
            memory_optimization_level: Level of memory optimization (0-3)
                0: No optimization (full memory usage)
                1: Basic optimization (30% reduction)
                2: Medium optimization (60% reduction)
                3: Maximum optimization (80-90% reduction)
            use_tiling: Whether to use tile-based processing
            tile_size: Size of each tile in grid cells
            tile_overlap: Overlap between adjacent tiles
            use_disk_storage: Whether to use disk-based storage for history
            disk_storage_dir: Directory for disk storage
            cache_size_mb: Memory cache size when using disk storage (MB)
            use_multi_resolution: Whether to use multi-resolution grid
            max_resolution_levels: Number of resolution levels for multi-res grid
        """
        # Load the base module for advanced features
        try:
            from core_simulation_framework import DiskStorageManager, MultiResolutionGrid, ModelConfig
            self.has_advanced_features = True
        except ImportError:
            logger.warning("Could not import advanced memory management features from core_simulation_framework")
            self.has_advanced_features = False
        
        # Initialize basic model settings
        super().__init__(grid_size, num_layers, layer_height_meters)
        
        # Store memory optimization settings
        self.memory_optimization_level = memory_optimization_level
        self.use_tiling = use_tiling
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap
        self.use_disk_storage = use_disk_storage
        self.disk_storage_dir = disk_storage_dir
        self.cache_size_mb = cache_size_mb
        self.use_multi_resolution = use_multi_resolution
        self.max_resolution_levels = max_resolution_levels
        
        # Initialize memory management components if advanced features are available
        if self.has_advanced_features:
            self._initialize_advanced_features()
        
        # Create optimized history storage based on optimization level
        self.history = {}
        self.history_compression_ratio = 1.0
        
        # Set up tiered history storage based on optimization level
        self._setup_tiered_history()
        
        logger.info(f"Initialized memory-optimized forest model with:")
        logger.info(f"  Grid size: {self.grid_size_x}x{self.grid_size_y}x{num_layers}")
        logger.info(f"  Optimization level: {memory_optimization_level}")
        logger.info(f"  Disk storage: {'Enabled' if use_disk_storage else 'Disabled'}")
        logger.info(f"  Multi-resolution: {'Enabled' if use_multi_resolution else 'Disabled'}")
        logger.info(f"  Tiling: {'Enabled' if use_tiling else 'Disabled'}")
    
    def _initialize_advanced_features(self):
        """Initialize advanced memory management features from core_simulation_framework."""
        from core_simulation_framework import DiskStorageManager, MultiResolutionGrid
        
        # Initialize disk storage if enabled
        if self.use_disk_storage:
            import os
            os.makedirs(self.disk_storage_dir, exist_ok=True)
            self.disk_manager = DiskStorageManager(
                base_dir=self.disk_storage_dir,
                cache_size_mb=self.cache_size_mb,
                compression_level=1
            )
            logger.info(f"Initialized disk storage at {self.disk_storage_dir}")
        else:
            self.disk_manager = None
        
        # Initialize multi-resolution grid if enabled
        if self.use_multi_resolution:
            self.multi_res_grid = MultiResolutionGrid(
                base_width=self.grid_size_x,
                base_height=self.grid_size_y,
                base_resolution=MODEL_RESOLUTION,
                num_layers=self.num_layers,
                max_resolution_levels=self.max_resolution_levels
            )
            logger.info(f"Initialized multi-resolution grid with {self.max_resolution_levels} levels")
        else:
            self.multi_res_grid = None
    
    def _setup_tiered_history(self):
        """
        Set up tiered history storage based on optimization level.
        
        Level 0: Store full grid states for all steps (no optimization)
        Level 1: Store full grid states for key frames, track changes for others
        Level 2: Store active cells only, with spatial indexing
        Level 3: Store highly compressed state with minimal information
        """
        self.history_compression_ratio = 1.0
        
        if self.memory_optimization_level == 0:
            # No optimization - standard history storage
            self.store_full_states = True
            self.history_keyframe_interval = 1
        
        elif self.memory_optimization_level == 1:
            # Basic optimization - keyframe approach
            self.store_full_states = True
            self.history_keyframe_interval = 5
            self.history_compression_ratio = 0.7  # ~30% reduction
            
        elif self.memory_optimization_level == 2:
            # Medium optimization - active cell tracking
            self.store_full_states = False
            self.history_keyframe_interval = 10
            self.history_compression_ratio = 0.4  # ~60% reduction
            
        elif self.memory_optimization_level == 3:
            # Maximum optimization - minimal state tracking
            self.store_full_states = False
            self.history_keyframe_interval = 20
            self.history_compression_ratio = 0.2  # ~80% reduction
            
        logger.info(f"Set up tiered history storage at optimization level {self.memory_optimization_level}")
        logger.info(f"  History compression ratio: {self.history_compression_ratio:.2f}")
        logger.info(f"  Keyframe interval: {self.history_keyframe_interval}")
    
    def record_state(self):
        """
        Record the current state into history using the optimized storage approach.
        This overrides the base ForestModel.record_state method.
        """
        current_step = len(self.history)
        
        # If disk storage is enabled and available, delegate to disk manager
        if self.use_disk_storage and self.disk_manager:
            # Store current state to disk
            state_key = f"state_{current_step}"
            self.disk_manager.store(state_key, self.state.copy())
            
            # Only track that we have this step in history
            self.history[current_step] = {
                'disk_key': state_key,
                'on_disk': True,
                'burning_cells': np.sum(self.state == CellState.BURNING.value),
                'burned_cells': np.sum(self.state == CellState.BURNED.value),
                'active_bounds': self._calculate_active_bounds()
            }
            return
        
        # Check if this should be a keyframe
        is_keyframe = (current_step % self.history_keyframe_interval == 0)
        
        if is_keyframe or self.memory_optimization_level <= 1:
            # For keyframes or low optimization, store full or near-full state
            if self.store_full_states:
                # Store complete grid state
                self.history[current_step] = {
                    'state': self.state.copy(),
                    'burning_cells': np.sum(self.state == CellState.BURNING.value),
                    'burned_cells': np.sum(self.state == CellState.BURNED.value)
                }
            else:
                # Store active regions only
                self.history[current_step] = {
                    'active_state': self._extract_active_regions(),
                    'burning_cells': np.sum(self.state == CellState.BURNING.value),
                    'burned_cells': np.sum(self.state == CellState.BURNED.value),
                    'active_bounds': self._calculate_active_bounds()
                }
        else:
            # For non-keyframes at higher optimization levels, store minimal information
            if self.memory_optimization_level == 2:
                # Store sparse representation (only active cells)
                burning_cells = np.argwhere(self.state == CellState.BURNING.value)
                burned_cells = np.argwhere(self.state == CellState.BURNED.value)
                
                self.history[current_step] = {
                    'burning_coords': burning_cells,
                    'burned_coords': burned_cells,
                    'burning_cells': len(burning_cells),
                    'burned_cells': len(burned_cells),
                    'prev_step': current_step - 1
                }
            elif self.memory_optimization_level == 3:
                # Store only summary statistics and changes from previous state
                if current_step > 0:
                    prev_state = self.get_state_at_step(current_step - 1)
                    if prev_state is not None:
                        # Calculate differences from previous state
                        state_diff = self.state - prev_state
                        # Only record coordinates where state changed
                        changed_coords = np.argwhere(state_diff != 0)
                        changed_values = np.array([self.state[tuple(coord)] for coord in changed_coords])
                        
                        self.history[current_step] = {
                            'changed_coords': changed_coords,
                            'changed_values': changed_values,
                            'burning_cells': np.sum(self.state == CellState.BURNING.value),
                            'burned_cells': np.sum(self.state == CellState.BURNED.value),
                            'prev_step': current_step - 1
                        }
                    else:
                        # Fallback - store active regions
                        self.history[current_step] = {
                            'active_state': self._extract_active_regions(),
                            'burning_cells': np.sum(self.state == CellState.BURNING.value),
                            'burned_cells': np.sum(self.state == CellState.BURNED.value),
                            'active_bounds': self._calculate_active_bounds()
                        }
                else:
                    # For first step, store active regions
                    self.history[current_step] = {
                        'active_state': self._extract_active_regions(),
                        'burning_cells': np.sum(self.state == CellState.BURNING.value),
                        'burned_cells': np.sum(self.state == CellState.BURNED.value),
                        'active_bounds': self._calculate_active_bounds()
                    }
    
    def _extract_active_regions(self):
        """Extract only the active regions of the grid to save memory."""
        # Find bounds of active (burning or burned) areas
        active_cells = (self.state == CellState.BURNING.value) | (self.state == CellState.BURNED.value)
        if not np.any(active_cells):
            return None
            
        # Calculate bounding box with padding
        active_indices = np.argwhere(active_cells)
        min_x, min_y, min_z = np.min(active_indices, axis=0)
        max_x, max_y, max_z = np.max(active_indices, axis=0)
        
        # Add padding
        padding = 5
        min_x = max(0, min_x - padding)
        min_y = max(0, min_y - padding)
        min_z = max(0, min_z - padding)
        max_x = min(self.grid_size_x - 1, max_x + padding)
        max_y = min(self.grid_size_y - 1, max_y + padding)
        max_z = min(self.num_layers - 1, max_z + padding)
        
        # Extract region and store with coordinates
        region = self.state[min_x:max_x+1, min_y:max_y+1, min_z:max_z+1].copy()
        
        return {
            'region': region,
            'bounds': (min_x, min_y, min_z, max_x, max_y, max_z)
        }
    
    def _calculate_active_bounds(self):
        """Calculate the bounding box of active (burning or burned) areas."""
        active_cells = (self.state == CellState.BURNING.value) | (self.state == CellState.BURNED.value)
        if not np.any(active_cells):
            return (0, 0, 0, 0, 0, 0)
            
        active_indices = np.argwhere(active_cells)
        min_x, min_y, min_z = np.min(active_indices, axis=0)
        max_x, max_y, max_z = np.max(active_indices, axis=0)
        
        # Add padding
        padding = 5
        min_x = max(0, min_x - padding)
        min_y = max(0, min_y - padding)
        min_z = max(0, min_z - padding)
        max_x = min(self.grid_size_x - 1, max_x + padding)
        max_y = min(self.grid_size_y - 1, max_y + padding)
        max_z = min(self.num_layers - 1, max_z + padding)
        
        return (min_x, min_y, min_z, max_x, max_y, max_z)
    
    def _process_tile_parallel(self, tile):
        """
        Process a single tile for fire spread simulation.
        
        This method is designed to be called by parallel workers and handles
        the complete simulation for a specific tile, including horizontal 
        and vertical fire spread and ember transport.
        
        Args:
            tile: Dictionary containing tile information including:
                 - bounds: (min_x, min_y, min_z, max_x, max_y, max_z)
                 - state: Current state of the tile
                 - wind_u, wind_v: Wind vector components
                 - fuel_load: Fuel load for the tile
                 - fuel_moisture: Fuel moisture for the tile
                 
        Returns:
            Dictionary with updated tile state and fire spread statistics
        """
        # Extract tile data
        min_x, min_y, min_z, max_x, max_y, max_z = tile['bounds']
        state = tile['state'].copy()
        
        # Track if any burning occurred in this tile
        any_burning = False
        
        # Create a copy of the state to avoid order effects during updates
        new_state = state.copy()
        
        # Process each layer
        for z in range(min_z, max_z + 1):
            layer_z = z - min_z  # Local layer index within the tile
            
            # Skip layers with no burning cells
            if not np.any(state[layer_z] == CellState.BURNING.value):
                continue
                
            # Process horizontal spread within this layer
            for y in range(1, state.shape[1] - 1):
                for x in range(1, state.shape[2] - 1):
                    # Skip cells that are not burning
                    if state[layer_z, y, x] != CellState.BURNING.value:
                        continue
                        
                    # Consume fuel
                    tile['fuel_load'][layer_z, y, x] -= tile['fuel_consumption_rates'][z]
                    
                    # If fuel is depleted, mark as burned
                    if tile['fuel_load'][layer_z, y, x] <= 0:
                        new_state[layer_z, y, x] = CellState.BURNED.value
                        tile['fuel_load'][layer_z, y, x] = 0
                        continue
                    
                    # Check neighbors for potential ignition
                    neighbors = [
                        (y-1, x),    # North
                        (y+1, x),    # South
                        (y, x-1),    # West
                        (y, x+1),    # East
                        (y-1, x-1),  # Northwest
                        (y-1, x+1),  # Northeast
                        (y+1, x-1),  # Southwest
                        (y+1, x+1)   # Southeast
                    ]
                    
                    # Get local wind vector
                    if 'wind_u' in tile and 'wind_v' in tile:
                        wind_u = tile['wind_u'][y, x]
                        wind_v = tile['wind_v'][y, x]
                    else:
                        wind_u, wind_v = 0, 0
                    
                    # Count burning neighbors for each unburned cell in the neighborhood
                    for ny, nx in neighbors:
                        # Skip if out of bounds
                        if (ny < 0 or ny >= state.shape[1] or 
                            nx < 0 or nx >= state.shape[2]):
                            continue
                            
                        # Skip if neighbor is not unburned
                        if state[layer_z, ny, nx] != CellState.UNBURNED.value:
                            continue
                            
                        # Skip if neighbor has no fuel
                        if tile['fuel_load'][layer_z, ny, nx] <= 0:
                            continue
                        
                        # Count burning neighbors for this unburned cell
                        n_burning = 0
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                if dy == 0 and dx == 0:
                                    continue  # Skip self
                                
                                neighbor_y, neighbor_x = ny + dy, nx + dx
                                
                                # Check if within bounds
                                if (0 <= neighbor_y < state.shape[1] and 
                                    0 <= neighbor_x < state.shape[2]):
                                    if state[layer_z, neighbor_y, neighbor_x] == CellState.BURNING.value:
                                        n_burning += 1
                        
                        # Calculate direction vector to neighbor
                        dx = nx - x
                        dy = y - ny  # Invert y-axis to match wind direction convention
                        
                        # Normalize the direction vector
                        dist = np.sqrt(dx*dx + dy*dy)
                        if dist > 0:
                            dx /= dist
                            dy /= dist
                        
                        # Calculate wind effect (dot product of wind and direction vectors)
                        wind_effect = wind_u * dx + wind_v * dy
                        
                        # Adjust wind effect to be in range [0, WIND_EFFECT_MAX]
                        wind_effect = max(0, wind_effect) * WIND_EFFECT_MAX
                        
                        # Calculate base ignition probability using sigmoid function
                        base_prob = sigmoid_ignition_neighbors(
                            n_burning,
                            tile['fire_params']['k'],
                            tile['fire_params']['threshold']
                        )
                        
                        # Apply fuel load effect (more fuel = higher probability)
                        fuel_effect = tile['fuel_load'][layer_z, ny, nx]
                        
                        # Apply wind effect
                        ignition_prob = base_prob * fuel_effect * (1 + wind_effect)
                        
                        # Apply fuel moisture penalty
                        ignition_prob *= (1 - tile['fuel_moisture'])
                        
                        # Apply distance penalty for diagonal neighbors
                        if abs(nx - x) + abs(ny - y) > 1:  # Diagonal neighbor
                            ignition_prob *= DIAGONAL_PENALTY
                        
                        # Check if ignition occurs (probabilistic)
                        if (ignition_prob > tile['fire_params']['spread_threshold'] and 
                            random.random() < ignition_prob):
                            new_state[layer_z, ny, nx] = CellState.BURNING.value
                            any_burning = True
            
            # Process vertical spread to the layer above
            if z < max_z:
                next_layer_z = layer_z + 1
                
                # Get burning cells in current layer
                burning_cells = np.where(state[layer_z] == CellState.BURNING.value)
                
                # Process each burning cell for vertical spread
                for y, x in zip(*burning_cells):
                    # Skip if the cell above is not unburned or has no fuel
                    if (state[next_layer_z, y, x] != CellState.UNBURNED.value or
                        tile['fuel_load'][next_layer_z, y, x] <= 0):
                        continue
                    
                    # Calculate upward spread probability
                    upward_prob = tile.get('vertical_connectivity', [1.0])[z] * (
                        1.0 - tile['fuel_moisture']) * tile['fuel_load'][next_layer_z, y, x]
                    
                    # Adjust for crown fire effects if applicable
                    if hasattr(self, 'CANOPY_START_LAYER') and z >= self.CANOPY_START_LAYER:
                        upward_prob *= CROWN_FIRE_MULTIPLIER
                        
                    # Apply probabilistic ignition
                    if random.random() < upward_prob:
                        new_state[next_layer_z, y, x] = CellState.BURNING.value
                        any_burning = True
            
            # Process vertical spread to the layer below
            if z > min_z:
                prev_layer_z = layer_z - 1
                
                # Get burning cells in current layer
                burning_cells = np.where(state[layer_z] == CellState.BURNING.value)
                
                # Process each burning cell for downward spread
                for y, x in zip(*burning_cells):
                    # Skip if the cell below is not unburned or has no fuel
                    if (state[prev_layer_z, y, x] != CellState.UNBURNED.value or
                        tile['fuel_load'][prev_layer_z, y, x] <= 0):
                        continue
                    
                    # Calculate downward spread probability
                    downward_prob = DOWNWARD_SPREAD_PROBABILITY * tile['fuel_load'][prev_layer_z, y, x]
                    
                    # Apply probabilistic ignition
                    if random.random() < downward_prob:
                        new_state[prev_layer_z, y, x] = CellState.BURNING.value
                        any_burning = True
        
        # Update state in the tile with the new state
        tile['state'] = new_state
        tile['any_burning'] = any_burning
        
        # Calculate statistics for this tile
        burning_count = np.sum(new_state == CellState.BURNING.value)
        burned_count = np.sum(new_state == CellState.BURNED.value)
        
        tile['stats'] = {
            'burning_count': burning_count,
            'burned_count': burned_count,
            'any_burning': any_burning
        }
        
        return tile
    
    def get_state_at_step(self, step):
        """
        Get the full state matrix at a specific simulation step.
        This handles reconstruction from various storage formats.
        
        Args:
            step: Simulation step to retrieve
            
        Returns:
            NumPy array with full state at the requested step
        """
        if step not in self.history:
            return None
        
        # If state is on disk, retrieve it
        if self.use_disk_storage and self.disk_manager and 'on_disk' in self.history[step]:
            disk_key = self.history[step]['disk_key']
            return self.disk_manager.retrieve(disk_key)
        
        # If full state is stored directly
        if 'state' in self.history[step]:
            return self.history[step]['state']
        
        # If active region is stored
        if 'active_state' in self.history[step] and self.history[step]['active_state'] is not None:
            # Reconstruct full state from active region
            full_state = np.zeros((self.grid_size_x, self.grid_size_y, self.num_layers), dtype=np.int8)
            region_data = self.history[step]['active_state']
            region = region_data['region']
            min_x, min_y, min_z, max_x, max_y, max_z = region_data['bounds']
            full_state[min_x:max_x+1, min_y:max_y+1, min_z:max_z+1] = region
            return full_state
        
        # If coordinates of burning/burned cells are stored
        if 'burning_coords' in self.history[step] and 'burned_coords' in self.history[step]:
            full_state = np.zeros((self.grid_size_x, self.grid_size_y, self.num_layers), dtype=np.int8)
            
            # Set burning cells
            for coord in self.history[step]['burning_coords']:
                full_state[tuple(coord)] = CellState.BURNING.value
                
            # Set burned cells
            for coord in self.history[step]['burned_coords']:
                full_state[tuple(coord)] = CellState.BURNED.value
                
            return full_state
            
        # If differences from previous state are stored
        if 'changed_coords' in self.history[step] and 'prev_step' in self.history[step]:
            prev_step = self.history[step]['prev_step']
            prev_state = self.get_state_at_step(prev_step)
            
            if prev_state is not None:
                # Start with previous state
                full_state = prev_state.copy()
                
                # Apply changes
                changed_coords = self.history[step]['changed_coords']
                changed_values = self.history[step]['changed_values']
                
                for i, coord in enumerate(changed_coords):
                    full_state[tuple(coord)] = changed_values[i]
                
                return full_state
        
        # If we couldn't reconstruct the state
        logger.warning(f"Could not reconstruct state for step {step}")
        return None
    
    def estimate_memory_usage(self):
        """
        Estimate memory requirements for the simulation.
        
        Returns:
            Dictionary with memory usage estimates in MB
        """
        # Calculate base memory requirements
        cell_count = self.grid_size_x * self.grid_size_y * self.num_layers
        base_memory_mb = (cell_count * 5 * 8) / (1024 * 1024)  # 5 arrays * 8 bytes per cell
        
        # Estimate history memory
        if self.use_disk_storage:
            history_memory_mb = 10  # Minimal overhead for disk-based storage
        else:
            # Apply compression ratio based on optimization level
            history_memory_mb = (cell_count * 8 * MAX_STEPS) / (1024 * 1024) * self.history_compression_ratio
        
        # Calculate total estimated memory
        total_memory_mb = base_memory_mb + history_memory_mb
        
        # Generate detailed report
        memory_report = {
            "base_model_mb": base_memory_mb,
            "history_mb": history_memory_mb,
            "total_mb": total_memory_mb,
            "optimization_level": self.memory_optimization_level,
            "compression_ratio": self.history_compression_ratio,
            "disk_storage": self.use_disk_storage,
            "multi_resolution": self.use_multi_resolution
        }
        
        # Add multi-resolution details if applicable
        if self.use_multi_resolution and self.multi_res_grid:
            memory_report["multi_res_factor"] = self.multi_res_grid.get_memory_reduction_factor()
            memory_report["total_mb"] *= (1.0 - memory_report["multi_res_factor"])
        
        # Add disk storage details if applicable
        if self.use_disk_storage and self.disk_manager:
            disk_info = self.disk_manager.get_storage_info()
            memory_report["disk_usage_mb"] = disk_info["disk_used_mb"]
            memory_report["cache_size_mb"] = disk_info["cache_size_mb"]
            memory_report["cache_used_mb"] = disk_info["cache_used_mb"]
        
        return memory_report
    
    def run_simulation(self, max_steps=MAX_STEPS, stop_when_fire_extinguished=STOP_WHEN_FIRE_EXTINGUISHED, use_parallel=True, num_workers=None):
        """
        Run the simulation with memory optimization.
        This overrides the base ForestModel.run_simulation method.
        
        Args:
            max_steps: Maximum number of simulation steps
            stop_when_fire_extinguished: Whether to stop when fire is out
            use_parallel: Whether to use parallel processing for tile-level operations
            num_workers: Number of parallel workers to use (None = use all available cores)
            
        Returns:
            Dictionary with simulation results
        """
        start_time = time.time()
        print(f"Starting simulation with {'parallel' if use_parallel else 'sequential'} processing")
        
        # For multi-resolution grid, update active fire coordinates each step
        if self.use_multi_resolution and self.multi_res_grid:
            # Start with high resolution everywhere (for first few steps)
            fire_cells = np.argwhere(self.state == CellState.BURNING.value)
            self.multi_res_grid.update_resolution_map(fire_cells)
        
        # Add memory usage tracking
        initial_memory = self.estimate_memory_usage()
        
        # Run simulation with progress tracking
        progress_bar = get_progress_iterator(range(max_steps), desc="Running simulation")
        for step in progress_bar:
            # Record state at this step
            self.record_state()
            
            # Update fire spread using parallel or sequential processing
            if use_parallel:
                # Use parallel tile processing
                any_burning = self.update_horizontal_spread_parallel(num_workers=num_workers)
            else:
                # Use original sequential processing
            any_burning = self.update_horizontal_spread()
            
            # Update vertical fire spread
            any_burning_vertical = self.update_vertical_spread()
            
            # Combined result
            any_burning = any_burning or any_burning_vertical
            
            # Update ember transport
            if EMBER_GENERATION_PROBABILITY > 0:
                self.update_ember_transport()
            
            # For multi-resolution grid, update active fire coordinates
            if self.use_multi_resolution and self.multi_res_grid and any_burning:
                fire_cells = np.argwhere(self.state == CellState.BURNING.value)
                self.multi_res_grid.update_resolution_map(fire_cells)
            
            # Stop condition: if fire is extinguished and option is enabled
            if stop_when_fire_extinguished and not any_burning:
                logger.info(f"Fire extinguished at step {step}")
                break
        
        # Final state recording
        self.record_state()
        
        # Calculate results
        final_burning = np.sum(self.state == CellState.BURNING.value)
        final_burned = np.sum(self.state == CellState.BURNED.value)
        max_extent = len(self.history)
        
        # Calculate final memory usage
        final_memory = self.estimate_memory_usage()
        
        # If using disk storage, ensure all data is persisted
        if self.use_disk_storage and self.disk_manager:
            self.disk_manager.persist_all()
            
        return {
            "steps": max_extent,
            "burning_cells": final_burning,
            "burned_cells": final_burned,
            "initial_memory_mb": initial_memory["total_mb"],
            "final_memory_mb": final_memory["total_mb"],
            "memory_savings_pct": 100 * (1 - final_memory["total_mb"] / initial_memory["total_mb"]) if initial_memory["total_mb"] > 0 else 0
        }
    
    def clean_up(self):
        """Clean up resources, especially important for disk-based storage."""
        if self.use_disk_storage and self.disk_manager:
            self.disk_manager.clear_cache()
            logger.info("Cleaned up disk-based resources")
    
    def update_horizontal_spread_parallel(self, num_workers=None):
        """
        Update fire spread using parallel processing across independent tiles.
        
        This method divides the forest grid into tiles and processes each tile
        in parallel using multiple CPU cores. This significantly improves
        performance on multi-core systems without changing the simulation results.
        
        Args:
            num_workers (int): Number of parallel workers to use. If None,
                              defaults to the number of CPU cores.
                              
        Returns:
            bool: True if any cells are still burning after the update
        """
        # Determine number of worker processes
        if num_workers is None:
            num_workers = multiprocessing.cpu_count()
        
        # Log parallelization info
        print(f"Running parallel fire spread simulation with {num_workers} workers")
        
        # Define tile size based on grid dimensions and number of workers
        # Calculate optimal tile dimensions
        grid_size_x, grid_size_y = self.grid_size_x, self.grid_size_y
        tiles_per_dim = max(1, int(math.sqrt(num_workers * 4)))  # Create more tiles than workers for better load balancing
        
        tile_width = math.ceil(grid_size_x / tiles_per_dim)
        tile_height = math.ceil(grid_size_y / tiles_per_dim)
        
        # Create overlap to handle fire spread across tile boundaries
        overlap = 2  # Cells of overlap between adjacent tiles
        
        # Generate tiles with appropriate bounds
        tiles = []
        for y in range(0, grid_size_y, tile_height - overlap):
            for x in range(0, grid_size_x, tile_width - overlap):
                # Calculate tile bounds with overlap
                min_x = max(0, x - overlap)
                min_y = max(0, y - overlap)
                max_x = min(grid_size_x, x + tile_width + overlap)
                max_y = min(grid_size_y, y + tile_height + overlap)
                
                # Define z bounds (all layers)
                min_z = 0
                max_z = self.num_layers - 1
                
                # Extract tile state and data
                tile_state = np.zeros((max_z - min_z + 1, max_y - min_y, max_x - min_x), dtype=np.int8)
                tile_fuel_load = np.zeros((max_z - min_z + 1, max_y - min_y, max_x - min_x), dtype=np.float32)
                
                # Fill tile data from the global state
                for z in range(min_z, max_z + 1):
                    z_local = z - min_z
                    tile_state[z_local] = self.layers[z][min_y:max_y, min_x:max_x]
                    tile_fuel_load[z_local] = self.fuel_load[z, min_y:max_y, min_x:max_x]
                
                # Extract wind data for this tile if available
                tile_wind_u = None
                tile_wind_v = None
                if hasattr(self, 'wind_u') and hasattr(self, 'wind_v'):
                    tile_wind_u = self.wind_u[min_y:max_y, min_x:max_x]
                    tile_wind_v = self.wind_v[min_y:max_y, min_x:max_x]
                
                # Create a tile dictionary with all necessary data
                tile = {
                    'bounds': (min_x, min_y, min_z, max_x, max_y, max_z),
                    'state': tile_state,
                    'fuel_load': tile_fuel_load,
                    'wind_u': tile_wind_u,
                    'wind_v': tile_wind_v,
                    'fuel_moisture': self.fuel_moisture,
                    'fuel_consumption_rates': self.fuel_consumption_rates,
                    'fire_params': self.fire_params
                }
                
                # Add vertical connectivity if available
                if hasattr(self, 'vertical_connectivity'):
                    tile['vertical_connectivity'] = self.vertical_connectivity
                
                tiles.append(tile)
        
        # Process tiles in parallel
        processed_tiles = []
        any_burning = False
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tiles for processing
            future_to_tile = {
                executor.submit(self._process_tile_parallel, tile): i 
                for i, tile in enumerate(tiles)
            }
            
            # Process completed futures as they finish
            for future in as_completed(future_to_tile):
                tile_idx = future_to_tile[future]
                try:
                    processed_tile = future.result()
                    processed_tiles.append(processed_tile)
                    
                    # Check if any burning occurred in this tile
                    if processed_tile['any_burning']:
                        any_burning = True
                        
                except Exception as e:
                    print(f"Error processing tile {tile_idx}: {e}")
                    traceback.print_exc()
        
        # Merge results back to the main grid, giving priority to burning cells
        # Create a new set of layers to avoid conflicts
        new_layers = [layer.copy() for layer in self.layers]
        
        # Process each tile's results
        for tile in processed_tiles:
            min_x, min_y, min_z, max_x, max_y, max_z = tile['bounds']
            tile_state = tile['state']
            
            # For overlapping regions, we need to handle conflicts
            # Priority: BURNING > BURNED > UNBURNED
            for z in range(min_z, max_z + 1):
                z_local = z - min_z
                layer = new_layers[z][min_y:max_y, min_x:max_x]
                tile_layer = tile_state[z_local]
                
                # Burning cells always take precedence
                burning_mask = (tile_layer == CellState.BURNING.value)
                if np.any(burning_mask):
                    layer[burning_mask] = CellState.BURNING.value
                
                # Burned cells take precedence over unburned cells
                burned_mask = (tile_layer == CellState.BURNED.value) & (layer == CellState.UNBURNED.value)
                if np.any(burned_mask):
                    layer[burned_mask] = CellState.BURNED.value
                
                # Also update fuel load
                self.fuel_load[z, min_y:max_y, min_x:max_x] = tile['fuel_load'][z_local]
        
        # Update the model's layers
        self.layers = new_layers
        
        return any_burning

# Add after the imports section, around line 95
import psutil  # For system memory monitoring

# Add just before class MemoryOptimizedForestModel definition (around line 3644)
class AdaptiveRAMManager:
    """
    Monitors system memory and dynamically adjusts simulation parameters.
    """
    def __init__(self, model, target_ram_fraction=0.8):
        self.model = model
        self.target_ram_fraction = target_ram_fraction
        self.adjustment_history = []
        self.initial_assessment = self.assess_memory()
        print(f"Adaptive RAM Manager initialized - Available RAM: {self.initial_assessment['available_ram_gb']:.2f} GB")
    
    def assess_memory(self):
        """Assess current system memory status"""
        try:
            vm = psutil.virtual_memory()
            total_ram_gb = vm.total / (1024**3)
            available_ram_gb = vm.available / (1024**3)
            used_percent = vm.percent / 100.0
            current_usage_gb = psutil.Process().memory_info().rss / (1024**3)
            
            # Calculate memory pressure (0 = none, 1 = critical)
            memory_pressure = max(0.0, min(1.0, used_percent))
            
            return {
                'total_ram_gb': total_ram_gb,
                'available_ram_gb': available_ram_gb,
                'used_percent': used_percent * 100,  # Convert to percentage
                'current_usage_gb': current_usage_gb,
                'memory_pressure': memory_pressure,
                'timestamp': time.time()
            }
        except Exception as e:
            print(f"Warning: Could not assess memory properly: {e}")
            return {
                'total_ram_gb': 16.0,  # Assume 16GB as default
                'available_ram_gb': 8.0,  # Assume 8GB available
                'memory_pressure': 0.5,
                'timestamp': time.time(),
                'error': str(e)
            }
    
    def adjust_parameters(self):
        """Adjust model parameters based on memory assessment"""
        try:
            assessment = self.assess_memory()
            changes = {}
            
            # Optimization level strategy
            if assessment['memory_pressure'] < 0.3:
                # Low pressure - optimize for speed
                if self.model.memory_optimization_level != 1:
                    self.model.memory_optimization_level = 1
                    self.model._setup_tiered_history()
                    changes['memory_optimization_level'] = 1
                    
            elif assessment['memory_pressure'] < 0.6:
                # Medium pressure - balanced approach
                if self.model.memory_optimization_level != 2:
                    self.model.memory_optimization_level = 2
                    self.model._setup_tiered_history()
                    changes['memory_optimization_level'] = 2
                    
            else:
                # High pressure - optimize for memory
                if self.model.memory_optimization_level != 3:
                    self.model.memory_optimization_level = 3
                    self.model._setup_tiered_history()
                    changes['memory_optimization_level'] = 3
                    
            # Disk storage strategy
            if assessment['memory_pressure'] > 0.7 and not self.model.use_disk_storage:
                self.model.use_disk_storage = True
                changes['use_disk_storage'] = True
                if hasattr(self.model, '_initialize_advanced_features'):
                    self.model._initialize_advanced_features()
            
            # Cache size adjustment - critical for disk storage performance
            if self.model.use_disk_storage:
                # Calculate appropriate cache size based on available RAM
                available_gb = assessment['available_ram_gb']
                
                if assessment['memory_pressure'] > 0.8:
                    # Very high pressure - minimal cache
                    new_cache_size = int(available_gb * 0.3 * 1024)  # 30% of available RAM
                elif assessment['memory_pressure'] > 0.6:
                    # High pressure - reduced cache
                    new_cache_size = int(available_gb * 0.5 * 1024)  # 50% of available RAM
                else:
                    # Normal pressure - balanced cache
                    new_cache_size = int(available_gb * 0.7 * 1024)  # 70% of available RAM
                
                # Ensure minimum and maximum cache sizes
                new_cache_size = max(256, min(new_cache_size, 8192))  # 256MB to 8GB
                
                if hasattr(self.model, 'cache_size_mb') and self.model.cache_size_mb != new_cache_size:
                    self.model.cache_size_mb = new_cache_size
                    changes['cache_size_mb'] = new_cache_size
                    
                    # Update disk manager if it exists
                    if hasattr(self.model, 'disk_manager') and self.model.disk_manager:
                        try:
                            self.model.disk_manager.set_cache_size(new_cache_size)
                        except Exception as e:
                            print(f"Warning: Could not update disk cache size: {e}")
            
            # Tile size strategy - adjust based on memory pressure
            if assessment['memory_pressure'] > 0.8:
                # Very high pressure - use small tiles
                new_tile_size = min(100, self.model.grid_size_x // 4)
                if self.model.tile_size != new_tile_size:
                    self.model.tile_size = new_tile_size
                    changes['tile_size'] = new_tile_size
                    
            elif assessment['memory_pressure'] > 0.5:
                # High pressure - use medium tiles
                new_tile_size = min(200, self.model.grid_size_x // 2)
                if self.model.tile_size != new_tile_size:
                    self.model.tile_size = new_tile_size
                    changes['tile_size'] = new_tile_size
            
            # Record adjustments if any were made
            if changes:
                self.adjustment_history.append({
                    'timestamp': time.time(),
                    'assessment': assessment,
                    'changes': changes
                })
                print(f"Memory parameters adjusted - pressure: {assessment['memory_pressure']:.2f}")
                for key, value in changes.items():
                    print(f"  {key}: {value}")
            
            return changes
            
        except Exception as e:
            print(f"Warning: Error in adjust_parameters: {e}")
            return {}
    
    def emergency_reduction(self):
        """Apply emergency memory reduction measures"""
        assessment = self.assess_memory()
        
        if assessment['memory_pressure'] > 0.9:
            print("CRITICAL MEMORY PRESSURE - Applying emergency measures")
            
            # Force maximum optimization
            self.model.memory_optimization_level = 3
            self.model._setup_tiered_history()
            
            # Force disk storage
            self.model.use_disk_storage = True
            
            # Minimum tile size
            self.model.tile_size = max(50, self.model.grid_size_x // 10)
            
            # Force garbage collection
            import gc
            gc.collect()
            
            return True
        
        return False
    
    def get_status_report(self):
        """Generate a status report about memory usage and adjustments made"""
        current = self.assess_memory()
        
        report = {
            'current_memory': current,
            'adjustments_made': len(self.adjustment_history),
            'optimization_level': self.model.memory_optimization_level,
            'using_disk_storage': self.model.use_disk_storage,
            'tile_size': self.model.tile_size
        }
        
        if self.adjustment_history:
            report['last_adjustment'] = self.adjustment_history[-1]
            
        return report

# Modify the MemoryOptimizedForestModel class __init__ method to include the adaptive RAM manager
def __init__(self, grid_size=100, num_layers=10, layer_height_meters=LAYER_HEIGHT_METERS,
             memory_optimization_level=2, use_tiling=False, tile_size=500, tile_overlap=50,
             use_disk_storage=False, disk_storage_dir="./simulation_data", cache_size_mb=1024,
             use_multi_resolution=False, max_resolution_levels=3,
             use_adaptive_ram=True, target_ram_fraction=0.8):
    """
    Initialize a memory-optimized forest model.
    """
    # Initialize basic model settings
    super().__init__(grid_size, num_layers, layer_height_meters)
    
    # Store memory optimization settings
    self.memory_optimization_level = memory_optimization_level
    self.use_tiling = use_tiling
    self.tile_size = tile_size
    self.tile_overlap = tile_overlap
    self.use_disk_storage = use_disk_storage
    self.disk_storage_dir = disk_storage_dir
    self.cache_size_mb = cache_size_mb
    self.use_multi_resolution = use_multi_resolution
    self.max_resolution_levels = max_resolution_levels
    
    # Initialize memory management components if advanced features are available
    try:
        from core_simulation_framework import DiskStorageManager, MultiResolutionGrid
        self.has_advanced_features = True
        if use_disk_storage or use_multi_resolution:
            self._initialize_advanced_features()
    except ImportError:
        print("Advanced memory management features not available, using basic optimization only")
        self.has_advanced_features = False
    
    # Create optimized history storage based on optimization level
    self.history = {}
    self.history_compression_ratio = 1.0
    
    # Set up tiered history storage based on optimization level
    self._setup_tiered_history()
    
    # Initialize adaptive RAM manager if enabled
    self.use_adaptive_ram = use_adaptive_ram
    if use_adaptive_ram:
        try:
            import psutil
            self.ram_manager = AdaptiveRAMManager(self, target_ram_fraction)
        except ImportError:
            print("Warning: psutil module not available. Adaptive RAM management disabled.")
            self.use_adaptive_ram = False
            self.ram_manager = None
    else:
        self.ram_manager = None
    
    print(f"Initialized memory-optimized forest model with:")
    print(f"  Grid size: {self.grid_size_x}x{self.grid_size_y}x{num_layers}")
    print(f"  Optimization level: {memory_optimization_level}")
    print(f"  Disk storage: {'Enabled' if use_disk_storage else 'Disabled'}")
    print(f"  Adaptive RAM: {'Enabled' if self.use_adaptive_ram else 'Disabled'}")

# Add this method to the MemoryOptimizedForestModel class
def run_simulation(self, max_steps=MAX_STEPS, stop_when_fire_extinguished=STOP_WHEN_FIRE_EXTINGUISHED, 
                   use_parallel=True, num_workers=None):
    """
    Run the simulation with memory optimization and adaptive RAM management.
    """
    start_time = time.time()
    print(f"Starting simulation with {'parallel' if use_parallel else 'sequential'} processing")
    
    # Add memory usage tracking
    initial_memory = self.estimate_memory_usage()
    
    # Monitoring interval for adaptive RAM manager
    monitor_interval = max(1, min(5, max_steps // 20))  # Check up to 20 times during simulation
    
    # Run simulation with progress tracking
    try:
        progress_bar = get_progress_iterator(range(max_steps), desc="Running simulation")
        for step in progress_bar:
            # Check memory status periodically using adaptive RAM manager
            if self.use_adaptive_ram and self.ram_manager and step % monitor_interval == 0:
                self.ram_manager.adjust_parameters()
            
            # Record state at this step
            self.record_state()
            
            # Detect grid size and use appropriate processing method
            grid_size = max(self.grid_size_x, self.grid_size_y)
            
            # Use supertile processing for very large grids
            if grid_size >= 1000 and use_parallel:
                # Generate supertiles if not already generated
                if not hasattr(self, 'supertiles') or self.supertiles is None:
                    supertile_size = self.tile_size * 4  # Much larger than regular tiles
                    overlap = self.tile_overlap * 2
                    self.supertiles = self.generate_supertiles(supertile_size, overlap)
                
                # Process supertiles in parallel
                supertile_results = self.process_supertiles_parallel(self.supertiles, num_workers)
                
                # Update the model state from supertile results
                self.update_from_supertiles(supertile_results)
                
                # Check if any burning cells remain
                any_burning = any(supertile['any_burning'] for supertile in supertile_results)
                
            else:
                # Use parallel tile processing for medium-sized grids
                if use_parallel:
                    any_burning = self.update_horizontal_spread_parallel(num_workers=num_workers)
                else:
                    # Use original sequential processing for small grids
                    any_burning = self.update_horizontal_spread()
            
            # Update vertical fire spread
            any_burning_vertical = self.update_vertical_spread()
            
            # Combined result
            any_burning = any_burning or any_burning_vertical
            
            # Check for critical memory pressure every few steps
            if self.use_adaptive_ram and self.ram_manager and step % 5 == 0:
                vm = psutil.virtual_memory()
                if vm.percent > 95:  # Critical memory pressure
                    self.ram_manager.emergency_reduction()
            
            # Stop condition: if fire is extinguished and option is enabled
            if stop_when_fire_extinguished and not any_burning:
                print(f"Fire extinguished at step {step}")
                break
    
    except MemoryError:
        # Handle out of memory error
        print("MEMORY ERROR: Simulation ran out of memory")
        
        if self.use_adaptive_ram and self.ram_manager:
            # Apply emergency measures
            print("Applying emergency memory reduction measures")
            self.ram_manager.emergency_reduction()
            
            # Try to save current state
            print("Attempting to save current progress")
            self.record_state()
    
    # Final state recording
    self.record_state()
    
    # Calculate results
    final_burning = sum(np.sum(layer == CellState.BURNING.value) for layer in self.layers)
    final_burned = sum(np.sum(layer == CellState.BURNED.value) for layer in self.layers)
    max_extent = len(self.history)
    
    # Calculate final memory usage
    final_memory = self.estimate_memory_usage()
            
    return {
        "steps": max_extent,
        "burning_cells": final_burning,
        "burned_cells": final_burned,
        "initial_memory_mb": initial_memory["total_mb"],
        "final_memory_mb": final_memory["total_mb"],
        "memory_savings_pct": 100 * (1 - final_memory["total_mb"] / initial_memory["total_mb"]) if initial_memory["total_mb"] > 0 else 0,
        "adjustments": len(self.ram_manager.adjustment_history) if (self.use_adaptive_ram and self.ram_manager) else 0,
        "simulation_time_seconds": time.time() - start_time
    }
