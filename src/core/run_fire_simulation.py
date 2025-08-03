#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Forest Fire Simulation Runner

A user-friendly interface for running forest fire simulations.

Examples:
    # Run with default configuration
    python run_fire_simulation.py
    
    # Run with custom configuration file
    python run_fire_simulation.py --config my_config.json
    
    # Run with interactive parameter selection
    python run_fire_simulation.py --interactive
    
    # Validate configuration without running
    python run_fire_simulation.py --config mountain_fire.json --validate-only
"""

import sys
import os
import argparse
import logging
import time
import json
import traceback
from pathlib import Path
from datetime import datetime
import numpy as np
from typing import Dict, Any, Optional, Union, List, Tuple
import pickle

# Import paths and setup module first to ensure correct path handling
from utils.project_paths import (
    setup_python_path, PROJECT_ROOT, get_results_dir, get_config_file_path
)
setup_python_path()

# Try importing psutil, but provide a fallback
try:
    import psutil
except ImportError:
    psutil = None
    print("Warning: psutil module not found. Memory usage tracking will be disabled.")

# Set up logging using the centralized system
from utils.logging_utils import setup_global_logging, get_simulation_logger

# Initialize the global logging system
setup_global_logging(
    log_dir=Path(PROJECT_ROOT) / "logs",
    default_level=logging.INFO,
    log_format="detailed",
    console=True,
    track_memory=True if psutil else False
)

# Get a logger for this module
logger = get_simulation_logger("fire_simulation")
logger.info("Fire simulation runner initializing with centralized logging")

# Import configuration tools - simplify with a single import approach
CONFIG_TOOLS_IMPORTED = False
try:
    from config.config_tools import (
        ModelConfig, create_config, load_config, validate_config, 
        optimize_config
    )
    from core.forest_model import ForestModel, MemoryOptimizedForestModel, create_forest_model
    from core.fire_simulation_engine import FireSimulationEngine
    logger.info("Successfully imported from regular imports")
    CONFIG_TOOLS_IMPORTED = True
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

# Import parameter validator
PARAMETER_VALIDATION_ENABLED = False
try:
    from config.parameter_validator import validator, ValidationContext
    PARAMETER_VALIDATION_ENABLED = True
    logger.info("Successfully imported parameter_validator.")
except ImportError:
    # Create a simple dummy so it doesn't crash if validator is used
    class DummyValidator:
        def register_parameter(self, *args, **kwargs): pass
        def register_parameters(self, *args, **kwargs): pass
        def track_usage(self, *args, **kwargs): pass
        def create_tracked_parameter(self, *args, **kwargs): 
            return args[1] if args[1] is not None else args[2]
        def save_report(self, *args, **kwargs): pass
        def print_summary(self, *args, **kwargs): pass
    validator = DummyValidator()
    class ValidationContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def register_parameter(self, *args, **kwargs): return self
        def validate_parameter(self, *args, **kwargs): return True
    logger.warning("Parameter validation will use a basic dummy (parameter_validator module not found).")

class SimulationRunner:
    """
    Runner class for forest fire simulations.
    
    This class handles the complete lifecycle of a simulation:
    - Loading or creating configuration
    - Initializing the forest model
    - Running the simulation
    - Saving results and generating visualizations
    """
    
    def __init__(self, config=None, output_dir=None, interactive=False):
        """
        Initialize the simulation runner.
        
        Args:
            config: Configuration object or path to config file
            output_dir: Directory to save results. If 'auto' or None, a timestamped dir in 'results/' is created.
            interactive: Whether to allow interactive parameter adjustment
        """
        # Generate timestamp for unique identification
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save config file path if provided as string
        self.config_path = None
        if isinstance(config, str):
            self.config_path = config
            self.config = self._load_config(self.config_path)
            logger.info(f"Loaded configuration from file: {self.config_path}")
        elif isinstance(config, ModelConfig):
            self.config = config
            logger.info("Using provided ModelConfig object.")
        else:
            # This case should ideally not be reached if main() prepares the config properly.
            logger.warning("No valid configuration path or ModelConfig object provided to SimulationRunner. Creating a default ModelConfig.")
            self.config = ModelConfig() # Default fallback
        
        # Handle output directory configuration
        if output_dir is not None and str(output_dir).lower() != "auto":
            # Override config output_dir with provided parameter
            self.config.output_dir = str(output_dir)
        elif output_dir is None or str(output_dir).lower() == "auto":
            # Use timestamped directory if none specified or auto requested
            if not hasattr(self.config, 'output_dir') or not self.config.output_dir:
                self.config.output_dir = f"results/sim_{timestamp}"
        
        # Use config method to get resolved output directory
        if hasattr(self.config, 'get_output_dir'):
            self.output_dir = self.config.get_output_dir()
        else:
            # Fallback for older configs
            self.output_dir = Path(self.config.output_dir).expanduser().resolve()
        
        # Create the output directory
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        self.interactive = interactive
        self.forest_model = None
        self.start_time = None
        self.end_time = None
        
        # Track parameter values that were actually used
        if PARAMETER_VALIDATION_ENABLED:
            validator.track_usage("output_dir", str(self.output_dir), "SimulationRunner.__init__")
            validator.track_usage("interactive", self.interactive, "SimulationRunner.__init__")
            
        # Log the configuration source and key parameters
        self._log_config_details()
        
        # Apply reasonable constraints to configuration parameters without overriding valid user settings
        self._adjust_configuration()
        
        # Allow interactive parameter adjustment if requested
        if interactive:
            self._interactive_config_adjustment()
            
        # Save a copy of the configuration to the output directory
        self._save_config_copy()
    
    def _log_config_details(self):
        """Log details about the configuration to help with debugging."""
        logger.info("Configuration details:")
        
        # Log the configuration type
        config_type = type(self.config).__name__
        config_module = type(self.config).__module__
        logger.info(f"Configuration type: {config_module}.{config_type}")
        
        # Log key parameters
        try:
            # Log grid parameters
            grid_size = getattr(self.config, 'grid_size', 'Not set')
            logger.info(f"  grid_size: {grid_size}")
            
            # Log resolution
            resolution = getattr(self.config, 'model_resolution', 'Not set')
            logger.info(f"  model_resolution: {resolution}")
            
            # Log layer parameters
            num_layers = getattr(self.config, 'num_layers', 'Not set')
            logger.info(f"  num_layers: {num_layers}")
            
            layer_height = getattr(self.config, 'layer_height', 'Not set')
            logger.info(f"  layer_height: {layer_height}")
            
            # Log auto-sizing parameters
            auto_size = getattr(self.config, 'auto_size_from_lidar', 'Not set')
            logger.info(f"  auto_size_from_lidar: {auto_size}")
            
            lidar_dir = getattr(self.config, 'lidar_data_dir', 'Not set')
            logger.info(f"  lidar_data_dir: {lidar_dir}")
            
            # Log memory optimization parameters
            memory_level = getattr(self.config, 'memory_optimization_level', 'Not set')
            logger.info(f"  memory_optimization_level: {memory_level}")
            
            use_tiling = getattr(self.config, 'use_tiling', 'Not set')
            logger.info(f"  use_tiling: {use_tiling}")
        except Exception as e:
            logger.warning(f"Error logging configuration details: {e}")
    
    def _adjust_configuration(self):
        """Apply reasonable constraints to configuration parameters without overriding valid user settings."""
        # Check number of layers
        if self.config.num_layers < 1:
            logger.warning(f"Number of layers {self.config.num_layers} must be at least 1, setting to 5")
            self.config.num_layers = 5
        
        # Ensure layer_height is valid
        if not hasattr(self.config, 'layer_height') or self.config.layer_height <= 0:
            logger.warning(f"Invalid layer_height value, defaulting to 2.0 meters")
            self.config.layer_height = 2.0
        
        # Ensure max_steps is valid
        if not hasattr(self.config, 'max_steps') or self.config.max_steps < 1:
            logger.warning(f"Invalid max_steps value, defaulting to 100")
            self.config.max_steps = 100
            
        self._configure_memory_optimization()
    
    def _configure_memory_optimization(self):
        """Configure memory optimization based on grid size"""
        # Calculate grid cells for memory estimation
        if isinstance(self.config.grid_size, int):
            grid_cells = self.config.grid_size * self.config.grid_size
        elif isinstance(self.config.grid_size, tuple) and len(self.config.grid_size) == 2:
            grid_cells = self.config.grid_size[0] * self.config.grid_size[1]
        else:
            grid_cells = 0
            
        # Enable memory optimization for very large grids
        if grid_cells > 500000 and not hasattr(self.config, 'memory_optimization_level'):
            logger.info(f"Large grid detected ({grid_cells} cells). Setting memory_optimization_level=1")
            self.config.memory_optimization_level = 1
        
        # For extremely large grids, increase optimization level
        if grid_cells > 2000000 and getattr(self.config, 'memory_optimization_level', 0) < 2:
            logger.info(f"Very large grid detected ({grid_cells} cells). Setting memory_optimization_level=2")
            self.config.memory_optimization_level = 2
            
            # Enable tiling for extremely large grids
            if not hasattr(self.config, 'use_tiling') or not self.config.use_tiling:
                logger.info("Enabling tiling for memory efficiency")
                self.config.use_tiling = True
                
                # Set tile size if not already specified
                if not hasattr(self.config, 'tile_size') or self.config.tile_size <= 0:
                    logger.info("Setting default tile_size to 200")
                    self.config.tile_size = 200
    
    def _load_config(self, config_path):
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to the configuration file
        
        Returns:
            ModelConfig: Loaded configuration
        """
        try:
            logger.info(f"Loading configuration from: {config_path}")
            config = load_config(config_path)
            logger.info(f"Successfully loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
            logger.warning("Creating default configuration instead")
            return create_config()
    
    def _save_config_copy(self):
        """Save a copy of the current configuration to the output directory."""
        config_file = self.output_dir / "config" / "simulation_config.json"
        config_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(config_file, 'w') as f:
                # Convert dataclass to dict and save as JSON
                json.dump(self.config.to_dict(), f, indent=2)
            logger.info(f"Saved configuration to {config_file}")
        except Exception as e:
            logger.warning(f"Could not save configuration copy: {e}")
    
    def _interactive_config_adjustment(self):
        """Interactively adjust configuration parameters."""
        # Only import if needed to avoid dependencies for non-interactive mode
        try:
            print("\n===== Interactive Configuration =====")
            print("Adjust key simulation parameters (press Enter to keep current value):")
            
            # Grid size
            current = self.config.grid_size
            user_input = input(f"Grid size ({current}): ")
            if user_input.strip():
                self.config.grid_size = int(user_input)
            
            # Number of layers
            current = self.config.num_layers
            user_input = input(f"Number of layers ({current}): ")
            if user_input.strip():
                self.config.num_layers = int(user_input)
            
            # Wind speed
            current = self.config.wind_speed
            user_input = input(f"Wind speed in m/s ({current}): ")
            if user_input.strip():
                self.config.wind_speed = float(user_input)
            
            # Wind direction
            current = self.config.wind_direction
            user_input = input(f"Wind direction in degrees ({current}): ")
            if user_input.strip():
                self.config.wind_direction = float(user_input)
            
            # Maximum steps
            current = self.config.max_steps
            user_input = input(f"Maximum simulation steps ({current}): ")
            if user_input.strip():
                self.config.max_steps = int(user_input)
            
            # Memory optimization level
            current = self.config.memory_optimization_level
            user_input = input(f"Memory optimization level (0-2) ({current}): ")
            if user_input.strip():
                self.config.memory_optimization_level = int(user_input)
                
            # Ask about ignition points
            print("\nCurrent ignition points:")
            for i, (x, y, z) in enumerate(self.config.ignition_points):
                print(f"  {i+1}: ({x}, {y}, {z})")
                
            if input("Add new ignition point? (y/n): ").lower() == 'y':
                try:
                    x = int(input("X coordinate: "))
                    y = int(input("Y coordinate: "))
                    z = int(input("Z coordinate (layer): "))
                    self.config.ignition_points.append((x, y, z))
                except ValueError as e:
                    print(f"Invalid input: {e}")
            
            print("Configuration updated.")
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"Error updating parameters: {e}")
            print("Continuing with original configuration.")
    
    def validate(self, strict=False):
        """Validate the configuration and report any issues."""
        logger.info("Validating configuration...")

        if PARAMETER_VALIDATION_ENABLED:
            validator.track_usage("strict", strict, "SimulationRunner.validate")

        try:
            is_valid = validate_config(self.config, strict=strict)
            
            if is_valid:
                logger.info("Configuration is valid.")
                print("Configuration is valid.")
                
                if PARAMETER_VALIDATION_ENABLED:
                    validator.track_usage("validation_result", "valid", "SimulationRunner.validate")
                
                return True
            else:
                logger.warning("Configuration has warnings.")
                print("Configuration has warnings but may still work.")
                
                if PARAMETER_VALIDATION_ENABLED:
                    validator.track_usage("validation_result", "warnings", "SimulationRunner.validate")
                
                return not strict
        except Exception as e:
            logger.error(f"Configuration is invalid: {e}")
            print(f"Configuration is invalid: {e}")
            
            if PARAMETER_VALIDATION_ENABLED:
                validator.track_usage("validation_result", f"error: {str(e)}", "SimulationRunner.validate")
            
            return False
    
    def _prepare_forest_model(self):
        """Creates and initializes the ForestModel based on the configuration."""
        logger.info(f"Preparing ForestModel using configuration: {self.config.config_name}")

        # Create the base ForestModel instance using the factory
        # create_forest_model will use self.config.simulation_type and other relevant config fields
        forest_model = create_forest_model(config=self.config)
        logger.info(f"Created ForestModel of type: {type(forest_model).__name__}")

        # If LiDAR data is the chosen fuel load method, integrate it now
        if hasattr(self.config, 'fuel_load_method') and self.config.fuel_load_method == 'tiled_lidar':
            logger.info("Initializing ForestModel with LiDAR data using TiledLiDARIntegration.")
            if not self.config.lidar_data_dir:
                logger.error("lidar_data_dir is not set in config, but fuel_load_method is 'tiled_lidar'. Cannot proceed with LiDAR integration.")
                # Depending on desired strictness, could raise an error or allow model to proceed with no/default fuel
            else:
                try:
                    from src.core.vegetation_data_integration import TiledLiDARIntegration
                    
                    integrator = TiledLiDARIntegration(
                        config=self.config, # Pass the already resolved config
                        forest_model=forest_model # Pass the created model instance
                    )
                    # This will populate the forest_model instance in-place
                    integrator.initialize_forest_model() 
                    logger.info("ForestModel populated with LiDAR data.")
                except ImportError as e:
                    logger.error(f"Failed to import TiledLiDARIntegration: {e}. LiDAR data will not be loaded.")
                except Exception as e:
                    logger.error(f"Error during TiledLiDARIntegration: {e}")
                    logger.error(traceback.format_exc())
                    # Model proceeds but might not have fuel data from LiDAR
        else:
            logger.info(f"Skipping TiledLiDARIntegration, fuel_load_method is '{self.config.fuel_load_method}'. ForestModel will use its default fuel initialization.")
            # The created forest_model should handle its own default fuel initialization if not using LiDAR.
            # Ensure ForestModel.initialize_fuel_load() or similar is called if needed, or handled by its __init__.
            if hasattr(forest_model, 'initialize_fuel_load') and not (hasattr(self.config, 'fuel_load_method') and self.config.fuel_load_method == 'tiled_lidar'):
                 logger.info("Calling forest_model.initialize_fuel_load() for non-LiDAR setup.")
                 forest_model.initialize_fuel_load()


        return forest_model

    def _initialize_model(self, model_to_initialize): # Renamed 'model' to 'model_to_initialize' for clarity
        """Initialize the model with configuration settings."""
        print("\n===== INITIALIZING SIMULATION MODEL =====")
        init_start_time = time.time()
        
        # Load terrain if specified
        dem_file = getattr(self.config, 'dem_file', None)
        if dem_file and os.path.exists(dem_file):
            print(f"Loading terrain data from {os.path.basename(dem_file)}...")
            terrain_start = time.time()
            model_to_initialize.load_terrain_data(dem_file)
            terrain_time = time.time() - terrain_start
            print(f"Terrain data loaded successfully ({terrain_time:.2f}s)")
            logger.info(f"Loaded terrain data from {dem_file} in {terrain_time:.2f}s")
            
            # Initialize terrain-influenced wind
            print(f"Initializing terrain-influenced wind field...")
            wind_start = time.time()
            model_to_initialize.initialize_terrain_wind(
                    self.config.wind_direction,
                    self.config.wind_speed,
                    terrain_effect_strength=self.config.terrain_effect_strength
            )
            wind_time = time.time() - wind_start
            print(f"Terrain-influenced wind field initialized ({wind_time:.2f}s)")
            logger.info(f"Initialized terrain-influenced wind in {wind_time:.2f}s")
        else:
            # Set up regular wind conditions
            print(f"Setting up uniform wind field: {self.config.wind_speed}m/s at {self.config.wind_direction}°...")
            wind_start = time.time()
            model_to_initialize.initialize_wind(self.config.wind_direction, self.config.wind_speed)
            wind_time = time.time() - wind_start
            print(f"Uniform wind field initialized ({wind_time:.2f}s)")
            logger.info(f"Initialized uniform wind field in {wind_time:.2f}s")
        
        # Set fire behavior parameters
        if hasattr(model_to_initialize, "set_fire_parameters"):
            print(f"Configuring fire behavior parameters...")
            param_start = time.time()
            
            # Prepare required parameters
            fire_params = {
                'spread_probability': self.config.spread_probability,
                'ember_probability': self.config.ember_probability,
                'ember_distance': self.config.ember_distance,
                'wind_influence': self.config.wind_influence_on_spread,
                'slope_influence': self.config.slope_influence
            }
            
            # Add optional parameters if available
            for param in [
                'ember_rise', 'ember_ignition', 
                'ember_wind_factor', 'ember_height_factor', 'moisture_influence'
            ]:
                if hasattr(self.config, param):
                    fire_params[param] = getattr(self.config, param)
            
            # Set parameters
            model_to_initialize.set_fire_parameters(**fire_params)
            param_time = time.time() - param_start
            print(f"Fire behavior parameters configured ({param_time:.2f}s)")
            logger.info(f"Set fire parameters in {param_time:.2f}s")
        
        # Initialize fuel loading
        print(f"Initializing fuel load distribution...")
        fuel_start = time.time()
        
        # Set fuel load method for the model if the attribute exists
        fuel_load_method = getattr(self.config, 'fuel_load_method', 'random')
        if hasattr(model_to_initialize, 'fuel_load_method'):
            model_to_initialize.fuel_load_method = fuel_load_method
        
        # Try to initialize fuel load with one of several methods
        fuel_initialized = False
        
        # Method 1: Use model's initialize_fuel_load method if available
        # This is now the primary way for non-LiDAR fuel setup, called in _prepare_forest_model if applicable.
        # We can check if it was successful or if fuel_load exists and seems populated.
        if hasattr(model_to_initialize, 'fuel_load') and model_to_initialize.fuel_load is not None:
            # A basic check, e.g., if it's a numpy array and not empty or all zeros. More robust checks could be added.
            if isinstance(model_to_initialize.fuel_load, np.ndarray) and model_to_initialize.fuel_load.size > 0: 
                logger.info("Fuel load appears to be initialized in ForestModel.")
                fuel_initialized = True
            elif isinstance(model_to_initialize.fuel_load, list) and len(model_to_initialize.fuel_load) > 0:
                logger.info("Fuel load (list) appears to be initialized in ForestModel.")
                fuel_initialized = True

        # Method 2: Try to import and use the standalone initialize_fuel_load function (legacy/fallback)
        if not fuel_initialized:
            logger.info("Attempting legacy/standalone initialize_fuel_load function.")
            import_paths = [
                "from src.core.fire_simulation_engine import initialize_fuel_load",
                "from core.fire_simulation_engine import initialize_fuel_load",
                "from fire_simulation_engine import initialize_fuel_load"
            ]
            
            for import_path in import_paths:
                try:
                    namespace = {}
                    exec(import_path, globals(), namespace)
                    if 'initialize_fuel_load' in namespace:
                        namespace['initialize_fuel_load'](model_to_initialize)
                        fuel_initialized = True
                        logger.info(f"Fuel initialized using standalone function from: {import_path}")
                        break
                except Exception as e:
                    logger.warning(f"Failed to initialize fuel with standalone function from {import_path}: {e}")
        
        if not fuel_initialized:
            logger.error("Fuel load could not be initialized by standard methods. Model may not run correctly.")
            # The extensive fallback block that was here has been removed.
            # ForestModel instances should be responsible for their own default fuel state.
        
        fuel_time = time.time() - fuel_start
        print(f"Fuel load initialized using '{fuel_load_method}' method ({fuel_time:.2f}s)")
        logger.info(f"Initialized fuel load in {fuel_time:.2f}s")
            
        # Ensure at least one valid ignition point is set
        print(f"Setting ignition points...")
        ignition_points = getattr(self.config, 'ignition_points', [(50, 50, 0)])
        
        # Validate that ignition points are within the grid boundaries
        valid_ignition_points = []
        for point in ignition_points:
            x, y, z = point
            # Check if coordinates are within bounds
            if (0 <= x < model_to_initialize.grid_size_x and 
                0 <= y < model_to_initialize.grid_size_y and
                0 <= z < model_to_initialize.num_layers):
                valid_ignition_points.append(point)
            else:
                print(f"Ignition point ({x}, {y}, {z}) is outside grid bounds. Adjusting...")
                # Adjust to valid coordinates
                valid_x = min(max(0, x), model_to_initialize.grid_size_x - 1)
                valid_y = min(max(0, y), model_to_initialize.grid_size_y - 1)
                valid_z = min(max(0, z), model_to_initialize.num_layers - 1)
                valid_ignition_points.append((valid_x, valid_y, valid_z))
                print(f"  -> Adjusted to ({valid_x}, {valid_y}, {valid_z})")
        
        # If no valid ignition points, set one at the center
        if not valid_ignition_points:
            center_x = model_to_initialize.grid_size_x // 2
            center_y = model_to_initialize.grid_size_y // 2
            valid_ignition_points.append((center_x, center_y, 0))
            print(f"No valid ignition points found. Setting default at center: ({center_x}, {center_y}, 0)")
        
        # Set each valid ignition point
        for x, y, z in valid_ignition_points:
            print(f"Setting ignition at position ({x}, {y}, {z})")
            model_to_initialize.set_ignition(x, y, z)
        
        print(f"{len(valid_ignition_points)} ignition point(s) set")
        logger.info(f"Set {len(valid_ignition_points)} ignition points")
        
        # Report initialization completion
        init_time = time.time() - init_start_time
        print(f"Model initialization completed in {init_time:.2f}s")
        print("="*40)
        
        return model_to_initialize
    
    def _get_system_memory_mb(self):
        """Get the total system memory in MB."""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 * 1024)
        except ImportError:
            # Fallback if psutil is not available
            logger.warning("psutil not available, using default system memory estimate")
            return 16384  # Assume 16GB
    
    def _get_memory_usage(self):
        """Get current memory usage in MB."""
        if psutil is None:
            # Return a default value if psutil is not available
            logger.warning("psutil not available, cannot track memory usage")
            return 0
        
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert to MB
        except Exception as e:
            logger.warning(f"Error getting memory usage: {e}")
            return 0
    
    def run(self):
        """Run the simulation."""
        try:
            # Record overall start time
            total_start_time = time.time()
            
            # Initialize memory tracking
            self.memory_usage_history = []
            self.memory_usage_steps = []
            initial_memory = self._get_memory_usage()
            self.memory_usage_history.append(initial_memory)
            self.memory_usage_steps.append(0)

            print("\n" + "="*50)
            print("     FOREST FIRE SIMULATION - EXECUTION STARTED")
            print("="*50)
            print(f"Initial memory usage: {initial_memory:.1f}MB")

            print("\n===== PHASE 1: PREPARATION =====")
            prep_start_time = time.time()

            # Memory estimation can be done via self.config if needed for logging,
            # but model creation itself relies on config values.
            if hasattr(self.config, 'calculate_memory_requirements'):
                memory_estimate = self.config.calculate_memory_requirements()
                logger.info(f"Estimated memory via config: {memory_estimate.get('total_estimated_in_memory_mb', 'N/A')} MB")
                print(f"Estimated memory required (from config): {memory_estimate.get('total_estimated_in_memory_mb', 'N/A')}MB")
            else:
                logger.warning("Config object does not have calculate_memory_requirements method.")

            # The _prepare_forest_model will use create_forest_model which considers 
            # memory_optimization_level from the config.
            logger.info("===== Preparing Forest Model =====")
            self.forest_model = self._prepare_forest_model()

            # Calculate grid dimensions
            if not self.forest_model:
                logger.error("Forest model preparation failed. self.forest_model is None.")
                raise RuntimeError("Forest model could not be initialized.")

            grid_size_x = self.forest_model.grid_size_x
            grid_size_y = self.forest_model.grid_size_y
            num_layers = self.forest_model.num_layers
            total_cells = grid_size_x * grid_size_y * num_layers
            model_resolution = getattr(self.config, 'model_resolution', 1.0)
            physical_width = grid_size_x * model_resolution
            physical_height = grid_size_y * model_resolution
            physical_depth = num_layers * getattr(self.config, 'layer_height', 1.0)
            
            print(f"Grid dimensions: {grid_size_x}x{grid_size_y}x{num_layers} " +
                  f"({total_cells} total cells)")
            print(f"Physical dimensions: {physical_width:.1f}m x {physical_height:.1f}m x {physical_depth:.1f}m")
            
            # Update config with actual grid dimensions to ensure consistency
            if self.config.grid_size != grid_size_x or self.config.grid_size != grid_size_y:
                if isinstance(self.config.grid_size, int):
                    logger.info(f"Updating config.grid_size from {self.config.grid_size} to ({grid_size_x}, {grid_size_y})")
                    self.config.grid_size = (grid_size_x, grid_size_y)
            
            # Track actual model properties
            if PARAMETER_VALIDATION_ENABLED:
                validator.track_usage("actual_grid_size_x", self.forest_model.grid_size_x, "SimulationRunner.run")
                validator.track_usage("actual_grid_size_y", self.forest_model.grid_size_y, "SimulationRunner.run")
                validator.track_usage("actual_num_layers", self.forest_model.num_layers, "SimulationRunner.run")
                
                # Check if the expected grid size matches the actual
                if self.config.grid_size != self.forest_model.grid_size_x or self.config.grid_size != self.forest_model.grid_size_y:
                    validator.track_usage(
                        "grid_size", 
                        (self.forest_model.grid_size_x, self.forest_model.grid_size_y), 
                        "SimulationRunner.run",
                        is_fallback=True, 
                        notes=f"Expected {self.config.grid_size}, actual differs"
                    )
                
                # Validate geographical extents if available
                if hasattr(self.forest_model, 'geo_bounds') and hasattr(self.config, 'geo_bounds'):
                    from src.config.parameter_validator import verify_extents
                    verify_extents(
                        "SimulationRunner.run",
                        "geo_bounds",
                        self.config.geo_bounds,
                        self.forest_model.geo_bounds
                    )
            
            # PHASE 2: INITIALIZATION
            # Initialize the model (this already has detailed reporting from previous enhancement)
            self._initialize_model(self.forest_model)
            
            # Complete preparation phase
            prep_time = time.time() - prep_start_time
            print(f"Preparation and initialization completed in {prep_time:.2f}s")
            
            # PHASE 3: SIMULATION
            sim_start_time = time.time()
            print(f"\n===== PHASE 3: RUNNING SIMULATION =====")
            print(f"Running for up to {self.config.max_steps} steps...")
            
            # Initialize step tracking variables
            self._last_update_time = time.time()
            self._last_step = 0
            self._steps_per_second = []
            
            # Define step callback for progress notification
            def step_callback(step, stats):
                # Get statistics
                active = stats.get("active_cells", 0)
                burned = stats.get("burned_cells", 0)
                total_cells = self.forest_model.grid_size_x * self.forest_model.grid_size_y * self.forest_model.num_layers
                
                # Calculate percentages
                percent_complete = (step / self.config.max_steps) * 100
                percent_burned = (burned / total_cells) * 100
                percent_active = (active / total_cells) * 100
                
                # Calculate elapsed time and rate statistics
                current_time = time.time()
                elapsed = current_time - sim_start_time
                if step > self._last_step:  # Only update if we've made progress
                    steps_since_last = step - self._last_step
                    time_since_last = current_time - self._last_update_time
                    
                    if time_since_last > 0:  # Avoid division by zero
                        current_rate = steps_since_last / time_since_last
                        self._steps_per_second.append(current_rate)
                        # Keep only the last 5 rate measurements
                        if len(self._steps_per_second) > 5:
                            self._steps_per_second.pop(0)
                    
                    self._last_step = step
                    self._last_update_time = current_time
                
                # Calculate average rate and ETA
                if self._steps_per_second:
                    avg_rate = sum(self._steps_per_second) / len(self._steps_per_second)
                    if avg_rate > 0:  # Avoid division by zero
                        steps_remaining = self.config.max_steps - step
                        eta_seconds = steps_remaining / avg_rate
                        eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                    else:
                        eta_str = "unknown"
                else:
                    avg_rate = 0
                    eta_str = "calculating..."
                
                # Create progress bar (20 characters wide)
                bar_width = 20
                filled_length = int(percent_complete / 100 * bar_width)
                # Use ASCII characters for progress bar to avoid UnicodeEncodeError on Windows
                bar = '=' * filled_length + '-' * (bar_width - filled_length)
                
                # Track memory usage every 10 steps
                memory_message = ""
                if step % 10 == 0 or step == 1:
                    current_memory = self._get_memory_usage()
                    self.memory_usage_history.append(current_memory)
                    self.memory_usage_steps.append(step)
                    memory_delta = current_memory - self.memory_usage_history[0]
                    memory_message = f" | Memory: {current_memory:.1f}MB ({memory_delta:+.1f}MB)"
                    
                    # Log significant memory changes (>5% increase from last check)
                    if len(self.memory_usage_history) >= 2:
                        prev_memory = self.memory_usage_history[-2]
                        percent_change = ((current_memory - prev_memory) / prev_memory) * 100
                        if percent_change > 5:
                            logger.warning(f"Memory usage increased by {percent_change:.1f}% at step {step}: " +
                                          f"{prev_memory:.1f}MB -> {current_memory:.1f}MB")
                
                # Print progress information
                print(f"\rStep {step}/{self.config.max_steps} [{bar}] {percent_complete:.1f}% " + 
                      f"| Active: {active} ({percent_active:.2f}%) | Burned: {burned} ({percent_burned:.2f}%) " +
                      f"| {avg_rate:.2f} steps/s | ETA: {eta_str}{memory_message}", end="")
                
                # Periodically log more detailed information (every 10 steps or if active cells changed significantly)
                if step % 10 == 0 or step == 1:
                    logger.info(f"Step {step}/{self.config.max_steps} ({percent_complete:.1f}%) - " +
                                f"Active: {active}, Burned: {burned}, Rate: {avg_rate:.2f} steps/s")
                
                # Track parameter usage if validation is enabled
                if PARAMETER_VALIDATION_ENABLED:
                    validator.track_usage(
                        f"step_{step}_stats",
                        stats,
                        "SimulationRunner.run_step"
                    )
                
                return True  # Continue simulation
            
            # Run the simulation with step callback
            logger.info("===== Initializing Fire Simulation Engine =====")
            # Pass the prepared and initialized forest_model to the engine
            engine = FireSimulationEngine(
                config=self.config, 
                forest_model=self.forest_model # Pass self.forest_model
            )
            logger.info("FireSimulationEngine initialized.")
            
            simulation_results = engine.run_simulation(
                max_steps=self.config.max_steps,
                stop_when_fire_extinguished=self.config.stop_when_fire_extinguished,
                step_callback=step_callback
            )
            
            # Add a newline after the progress indicators
            print()
            
            # Complete simulation phase
            sim_time = time.time() - sim_start_time
            print(f"Simulation completed in {sim_time:.2f}s")
            
            # PHASE 4: RESULTS PROCESSING
            print(f"\n===== PHASE 4: PROCESSING RESULTS =====")
            results_start_time = time.time()
            
            # Report results using the data from simulation_results
            print("Generating simulation summary...")
            self._report_results(sim_time, simulation_results)
            
            # Save outputs using data from simulation_results
            print("Saving simulation results...")
            save_start = time.time()
            self._save_results(simulation_results)
            save_time = time.time() - save_start
            print(f"Results saved successfully ({save_time:.2f}s)")
            
            # Generate validation report if enabled
            if PARAMETER_VALIDATION_ENABLED:
                print("Generating parameter validation report...")
                report_start = time.time()
                report_path = os.path.join(str(self.output_dir), "parameter_validation.json")
                validator.save_report(report_path)
                validator.print_summary()
                report_time = time.time() - report_start
                print(f"Parameter validation report saved to: {report_path} ({report_time:.2f}s)")
            
            # Complete results phase
            results_time = time.time() - results_start_time
            print(f"Results processing completed in {results_time:.2f}s")
            
            # Memory usage report
            final_memory = self._get_memory_usage()
            peak_memory = max(self.memory_usage_history)
            initial_memory = self.memory_usage_history[0]
            memory_change = final_memory - initial_memory
            
            print(f"\n===== MEMORY USAGE REPORT =====")
            print(f"Initial memory usage: {initial_memory:.1f}MB")
            print(f"Peak memory usage:    {peak_memory:.1f}MB")
            print(f"Final memory usage:   {final_memory:.1f}MB")
            print(f"Memory change:        {memory_change:+.1f}MB ({memory_change/initial_memory*100:+.1f}%)")
            
            # Save memory usage data
            try:
                memory_data = {
                    "steps": self.memory_usage_steps,
                    "memory_mb": self.memory_usage_history,
                    "peak_mb": peak_memory,
                    "initial_mb": initial_memory,
                    "final_mb": final_memory
                }
                
                with open(self.output_dir / "memory_usage.json", "w") as f:
                    json.dump(memory_data, f, indent=2)
                logger.info(f"Memory usage data saved to {self.output_dir}/memory_usage.json")
            except Exception as e:
                logger.warning(f"Could not save memory usage data: {e}")
            
            # Final summary
            total_elapsed_time = time.time() - total_start_time
            print(f"\nTotal simulation runtime: {total_elapsed_time:.2f} seconds.")
            print("="*50)
            print(f"Results saved to: {self.output_dir}")
            
            return self.forest_model
            
        except Exception as e:
            logger.error(f"Error during simulation: {e}", exc_info=True)
            print(f"Simulation failed: {e}")
            # Potentially save partial results or logs here
            # For now, just re-raise to indicate failure in tests or main script
            raise
    
    def _report_results(self, runtime, simulation_results):
        """Report the simulation results to console and log."""
        stats = simulation_results.get('stats', {})
        final_active_cells_stat = stats.get("final_active_cells", 0) # Use this for final active cells
        total_burned_cells_stat = stats.get("total_burned_cells", 0) # Use this for total burned

        # engine_current_step should be 'steps' from the stats dict which is total steps run
        engine_current_step = stats.get("steps", "N/A")

        # peak_active_cells is usually part of stats if calculated by the engine
        peak_active_cells_stat = stats.get("max_active_cells", final_active_cells_stat) # Fallback to final if not present

        total_cells = 0
        if self.forest_model: # Corrected: was self.model
            total_cells = self.forest_model.width * self.forest_model.height * self.forest_model.num_layers
        percent_burned = (total_burned_cells_stat / total_cells) * 100 if total_cells > 0 else 0

        total_steps_config_val = "N/A"
        if self.config:
            total_steps_config_val = self.config.max_steps # Corrected from simulation_steps

        print("\n===== SIMULATION REPORT =====")
        logger.info("===== SIMULATION REPORT =====")
        print(f"Simulation completed in {runtime:.2f}s after {engine_current_step} steps (Configured for {total_steps_config_val} steps).")
        logger.info(f"Simulation completed in {runtime:.2f}s after {engine_current_step} steps (Configured for {total_steps_config_val} steps).")
        
        can_compare_steps = isinstance(engine_current_step, int) and isinstance(total_steps_config_val, int)
        stop_when_extinguished_config = getattr(self.config, 'stop_when_fire_extinguished', True)

        if stop_when_extinguished_config and \
           final_active_cells_stat == 0 and \
           can_compare_steps and \
           engine_current_step < total_steps_config_val:
            print(f"Fire extinguished at step {engine_current_step}.")
            logger.info(f"Fire extinguished at step {engine_current_step}.")

        print(f"Final active cells: {final_active_cells_stat}")
        logger.info(f"Final active cells: {final_active_cells_stat}")
        print(f"Total burned cells: {total_burned_cells_stat}")
        logger.info(f"Total burned cells: {total_burned_cells_stat}")
        print(f"Peak active cells during simulation: {peak_active_cells_stat}") # Added peak active cells
        logger.info(f"Peak active cells during simulation: {peak_active_cells_stat}")
        print("=============================")
        logger.info("=============================")
    
    def _save_results(self, simulation_results):
        """Save simulation results and visualizations."""
        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info(f"Created output directory: {self.output_dir}")

        # 1. Save simulation statistics
        stats_file = os.path.join(self.output_dir, "results.json")
        stats_to_save = simulation_results.get('stats', {})
        try:
            with open(stats_file, 'w') as f:
                json.dump(stats_to_save, f, indent=4, default=lambda o: '<not serializable>')
            logger.info(f"Simulation statistics saved to {stats_file}")
        except Exception as e:
            logger.error(f"Failed to save simulation statistics: {e}")

        # 2. Save the final forest model state
        final_model_state_file = os.path.join(self.output_dir, "final_forest_model_state.pkl") # Or other format
        final_forest_model = simulation_results.get('forest_model')
        if final_forest_model and hasattr(final_forest_model, 'save_state_to_file'):
            try:
                final_forest_model.save_state_to_file(final_model_state_file)
                logger.info(f"Final forest model state saved to {final_model_state_file}")
            except Exception as e:
                logger.error(f"Failed to save final forest model state: {e}")
        elif final_forest_model:
            logger.warning("Final forest model does not have a 'save_state_to_file' method.")
        else:
            logger.warning("No final forest model found in simulation results to save.")
            
        # 3. Save simulation history if available
        history_data = simulation_results.get('history')
        if history_data:
            history_file = os.path.join(self.output_dir, "simulation_history.pkl")
            try:
                with open(history_file, 'wb') as f:
                    pickle.dump(history_data, f)
                logger.info(f"Simulation history saved to {history_file}")
            except Exception as e:
                logger.error(f"Failed to save simulation history: {e}")
        else:
            logger.info("No simulation history to save (or history was not stored).")

        # Keep visualizations and summary generation
        if getattr(self.config, 'save_visualizations', True):
            print("Generating visualizations...")
            vis_start = time.time()
            self._generate_visualizations(simulation_results) # Pass results if needed
            vis_time = time.time() - vis_start
            print(f"Visualizations generated in {vis_time:.2f}s")
            
        # Always generate summary file, or add a separate explicit config flag later if needed.
        # For now, decoupling from save_visualizations to ensure test assertions pass.
        print("Generating summary file...")
        summary_start = time.time()
        self._generate_summary(simulation_results) # Pass results if needed
        summary_time = time.time() - summary_start
        print(f"Summary file generated in {summary_time:.2f}s")
        logger.info(f"Summary file generated in {summary_time:.2f}s")
            
        self.end_time = time.time()

    def _generate_visualizations(self, simulation_results):
        """Generate visualizations of simulation results."""
        viz_dir = self.output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        logger.info("Generating visualizations")
        
        # Use the centralized visualization module
        try:
            # Import the visualization module
            from utils.visualization import ForestFireVisualizer, generate_standard_visualizations
            
            # Generate all standard visualizations at once
            frame_interval_ms = getattr(self.config, 'viz_frame_interval_ms', 200) if self.config else 200
            
            saved_files = generate_standard_visualizations(
                forest_model=self.forest_model,
                output_dir=self.output_dir,
                include_animation=True
            )
            
            logger.info(f"Generated {len(saved_files)} visualizations successfully")
            
            # If specific custom visualizations are needed, use the visualizer directly:
            # visualizer = ForestFireVisualizer(self.forest_model)
            # visualizer.visualize_custom_view(...)
            
        except ImportError as e:
            logger.warning(f"Could not import visualization module: {e}")
            logger.warning("Falling back to basic visualizations")
            
            # Basic fallback visualization if the visualization module is not available
            try:
                import matplotlib.pyplot as plt
                
                # Simple 2D visualization as fallback
                if hasattr(self.forest_model, 'visualize_fire_state'):
                    plt.figure(figsize=(10, 8))
                    self.forest_model.visualize_fire_state(title="Final Fire State")
                    plt.savefig(viz_dir / "final_state_2d.png")
                    plt.close()
                    logger.info("Generated basic 2D visualization as fallback")
            except Exception as e:
                logger.warning(f"Could not generate fallback visualizations: {e}")
        
        except Exception as e:
            logger.warning(f"Error during visualization generation: {e}")
    
    def _generate_summary(self, simulation_results):
        """Generate a summary text file of the simulation."""
        stats = simulation_results.get('stats', {})
        
        current_step = stats.get('steps', 0) # Get steps from stats, default to 0
        total_steps_config = self.config.max_steps if self.config else "N/A"
        
        final_active_cells = stats.get('final_active_cells', 'N/A')
        total_burned_cells = stats.get('total_burned_cells', 'N/A')
        max_active_cells = stats.get('max_active_cells', 'N/A')
        runtime = stats.get('runtime_seconds', 0.0)

        summary_content = [
            "===== SIMULATION SUMMARY =====",
            f"Simulation Duration: {runtime:.2f} seconds",
            f"Completed Steps: {current_step} (Configured: {total_steps_config})",
            f"Final Active Cells: {final_active_cells}",
            f"Total Burned Cells: {total_burned_cells}",
            f"Peak Active Cells: {max_active_cells}",
            "============================",
            "\nDetailed Configuration:",
            str(self.config), # Assuming config has a __str__ method
            "\nSimulation Statistics:",
            json.dumps(stats, indent=4, default=str) # Serialize stats, handling non-serializable
        ]

        summary_file = os.path.join(self.output_dir, "simulation_summary.txt")
        with open(summary_file, 'w') as f:
            f.write("\n".join(summary_content))
        
        logger.info(f"Simulation summary saved to {summary_file}")

def main():
    # Initial memory usage tracking (memory usage will be tracked within SimulationRunner)
    
    parser = argparse.ArgumentParser(description="Run a forest fire simulation.")
    parser.add_argument("--config", type=str, help="Path to configuration JSON file.")
    parser.add_argument("--output", type=str, help="Directory to save simulation results.")
    parser.add_argument("--interactive", action="store_true", help="Enable interactive parameter adjustment.")
    parser.add_argument("--validate-only", action="store_true", help="Validate configuration and exit.")
    parser.add_argument("--no-viz", action="store_true", help="Disable visualization generation.")
    # Add more arguments as needed (e.g., for specific overrides)
    args = parser.parse_args()

    if not CONFIG_TOOLS_IMPORTED:
        logger.critical("Config tools failed to import. Cannot proceed with simulation runner.")
        sys.exit(1)
        
    config = None
    config_file_path_for_runner = None

    if args.config:
        config = load_config(args.config)
        config_file_path_for_runner = args.config
        if not config:
            logger.error(f"Failed to load config from {args.config}. Exiting.")
            sys.exit(1)
    else:
        logger.info("No config file provided, attempting to load default or create new.")
        # Try to load a default config if none specified, or create a new one
        default_config_path = "configs/default_config.json"
        if Path(default_config_path).exists():
            config = load_config(default_config_path)
            config_file_path_for_runner = default_config_path
            logger.info(f"Loaded default configuration from {default_config_path}")
        else:
            config = ModelConfig() # Create a new default ModelConfig
            logger.info("Created a new default ModelConfig.")

    if args.validate_only:
        if config:
            is_valid, errors = validate_config(config)
            if is_valid:
                logger.info("Configuration is valid.")
            else:
                logger.error(f"Configuration errors: {errors}")
            sys.exit(0 if is_valid else 1)
        else:
            logger.error("No configuration loaded to validate.")
            sys.exit(1)
            
    # Apply command-line argument overrides to the config object
    if args.no_viz:
        if config:
            if hasattr(config, 'save_visualizations'):
                config.save_visualizations = False
                logger.info("Visualization disabled via --no-viz argument.")
            else:
                # If ModelConfig doesn't have this attribute directly,
                # we might need to store it in a way the runner or visualization module checks.
                # For now, assume ModelConfig is expected to have/handle 'save_visualizations'.
                logger.warning("--no-viz specified, but config object does not have 'save_visualizations' attribute.")
        else:
            logger.warning("--no-viz specified, but no config object was loaded or created to modify.")

    # Determine output directory
    # Priority: command-line arg, then config file, then default
    output_dir_from_config = None
    if config:
        # Attempt 1: Direct attribute (if 'output_dir' is a defined field or dynamically added)
        output_dir_from_config = getattr(config, 'output_dir', None)
        
        # Attempt 2: If ModelConfig uses to_dict() or has a dictionary of parameters
        if output_dir_from_config is None and hasattr(config, 'to_dict') and callable(config.to_dict):
            try:
                config_data = config.to_dict()
                if isinstance(config_data, dict):
                    output_dir_from_config = config_data.get('output_dir')
            except Exception as e:
                logger.debug(f"Error calling config.to_dict() or getting 'output_dir': {e}")
        # Attempt 3: If ModelConfig has a 'get' method for parameters
        elif output_dir_from_config is None and hasattr(config, 'get') and callable(config.get):
            try:
                output_dir_from_config = config.get('output_dir')
            except Exception as e:
                logger.debug(f"Error calling config.get('output_dir'): {e}")
                
    output_dir_arg = args.output if args.output else output_dir_from_config
    
    # Pass the original config file path (if any) or the config object to SimulationRunner
    runner_config_input = config_file_path_for_runner if config_file_path_for_runner and Path(config_file_path_for_runner).exists() else config

    runner = SimulationRunner(config=runner_config_input, output_dir=output_dir_arg, interactive=args.interactive)
    
    # Validate configuration
    is_valid = runner.validate(strict=args.validate_only)
    
    # Exit if validation-only mode or validation failed
    if args.validate_only:
        print("Validation complete.")
        
        # Generate validation report if requested
        if PARAMETER_VALIDATION_ENABLED:
            if runner.output_dir:
                report_path = os.path.join(str(runner.output_dir), "parameter_validation.json")
            else:
                report_path = "parameter_validation.json"
            validator.save_report(report_path)
            validator.print_summary()
            print(f"Parameter validation report saved to: {report_path}")
            
        sys.exit(0 if is_valid else 1)
    elif not is_valid:
        print("Validation failed. Exiting.")
        sys.exit(1)
    
    # Run the simulation
    runner.run()
    
    # Print final path to results
    print(f"Results saved to: {runner.output_dir}")
    
if __name__ == "__main__":
    main() 