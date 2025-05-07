#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Forest Fire Simulation Runner with Tiled LiDAR Integration

This script provides a complete workflow for running a forest fire simulation using LiDAR data
with optimal memory management through tiling strategies.
"""

import os
import sys
import logging
import numpy as np
import matplotlib.pyplot as plt
import time
import math
import multiprocessing
from pathlib import Path
import json
import psutil
from datetime import datetime

# Import the standardized logging
from logging_utils import get_logger, configure_logging

# Optional imports
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    
# Set up logging
# Replace the existing logging configuration with the standardized version
logger = get_logger("run_tiled_simulation")

# Import required modules
try:
    from vegetation_data_integration import TiledLiDARIntegration
    from fire_simulation_engine import ForestModel
    from core_simulation_framework import BaseForestModel, ModelConfig, TileManager, TiledSimulationWithStorage, DiskStorageManager
    from config_tools import create_config, optimize_config, ConfigurationManager, estimate_memory, load_config
    HAS_CONFIG_TOOLS = True
except ImportError as e:
    logger.warning(f"Could not import all necessary modules: {e}")
    logger.warning("Using default parameters")
    HAS_CONFIG_TOOLS = False
    try:
        from vegetation_data_integration import TiledLiDARIntegration, MODEL_RESOLUTION, LAYER_HEIGHT_METERS
    except ImportError:
        logger.error("Could not import TiledLiDARIntegration - simulation not possible")
        MODEL_RESOLUTION = 5.0
        LAYER_HEIGHT_METERS = 2.0

class TiledSimulationRunner:
    """
    Advanced memory-optimized simulation runner that uses the TileManager
    to efficiently process large areas with limited memory.
    """
    
    def __init__(
        self, 
        config=None, 
        base_dir=None, 
        dem_path=None,
        fuel_moisture_path=None
    ):
        """
        Initialize the tiled simulation runner.
        
        Args:
            config: ModelConfig instance with simulation parameters
            base_dir: Directory containing PAD data
            dem_path: Path to DEM for terrain effects
            fuel_moisture_path: Path to fuel moisture data
        """
        # Setup component-specific logger
        self.logger = get_logger("run_tiled_simulation.TiledSimulationRunner")
        
        self.base_dir = base_dir
        self.dem_path = dem_path
        self.fuel_moisture_path = fuel_moisture_path
        
        # Use provided configuration or create default
        if config is None and HAS_CONFIG_TOOLS:
            self.config = create_config()
            self.logger.info("Created default configuration")
        else:
            self.config = config
            
        # Initialize attributes
        self.tile_manager = None
        self.model = None
        self.raster_bounds = None
        self.grid_size = None
        self.physical_size = (0, 0)  # width, height in meters
        self.results = None
        
        # Initialize tile integration
        self.tile_integration = None
    
    def setup(self):
        """
        Set up the simulation environment.
        This includes determining area bounds, creating the tile manager,
        and initializing the forest model.
        
        Returns:
            Self for method chaining
        """
        start_time = time.time()
        self.logger.info("Setting up tiled simulation environment")
        
        # Step 1: Get the geographic extent from data sources
        self._determine_geographic_extent()
        
        # Step 2: Optimize configuration if needed
        self._optimize_configuration()
        
        # Step 3: Create the tile manager
        self._create_tile_manager()
        
        # Step 4: Initialize the forest model
        self._initialize_forest_model()
        
        # Step 5: Set up environmental conditions
        self._setup_environment()
        
        setup_time = time.time() - start_time
        self.logger.info(f"Simulation setup completed in {setup_time:.1f} seconds")
        return self
    
    def _determine_geographic_extent(self):
        """Determine the geographic bounds of the simulation area."""
        # Use DEM if available, otherwise use a PAD file
        if self.dem_path:
            self.logger.info(f"Using DEM file for bounds: {self.dem_path}")
            self.raster_bounds = TiledLiDARIntegration._get_raster_bounds(self.dem_path)
        else:
            # Find a sample raster file in the base directory
            pad_files = list(Path(self.base_dir).glob("*.tif"))
            if not pad_files:
                raise ValueError(f"No raster files found in {self.base_dir}")
            self.logger.info(f"Using PAD file for bounds: {pad_files[0]}")
            self.raster_bounds = TiledLiDARIntegration._get_raster_bounds(str(pad_files[0]))
        
        self.logger.info(f"Raster bounds: {self.raster_bounds}")
        
        # Calculate grid size and physical dimensions
        self.grid_size = TiledLiDARIntegration._calculate_grid_size_from_bounds(
            self.raster_bounds, self.config.MODEL_RESOLUTION)
        
        self.physical_size = (
            self.raster_bounds[2] - self.raster_bounds[0],  # width in meters
            self.raster_bounds[3] - self.raster_bounds[1]   # height in meters
        )
        
        self.logger.info(f"Physical size: {self.physical_size[0]:.1f}m x {self.physical_size[1]:.1f}m")
        self.logger.info(f"Grid size: {self.grid_size}")
    
    def _optimize_configuration(self):
        """Optimize the configuration for the determined area size."""
        if HAS_CONFIG_TOOLS:
            self.logger.info("Optimizing configuration for the area dimensions")
            
            # Optimize configuration based on area size
            self.config = optimize_config(
                self.config,
                width_m=self.physical_size[0],
                height_m=self.physical_size[1],
                max_memory_mb=self.config.MEMORY_LIMIT_MB
            )
            
            self.logger.info(f"Optimized resolution: {self.config.MODEL_RESOLUTION}m")
            self.logger.info(f"Optimized layers: {self.config.DEFAULT_NUM_LAYERS}")
            self.logger.info(f"Optimized tile size: {self.config.DEFAULT_TILE_SIZE}")
            
            # Recalculate grid size with new resolution
            self.grid_size = TiledLiDARIntegration._calculate_grid_size_from_bounds(
                self.raster_bounds, self.config.MODEL_RESOLUTION)
            
            self.logger.info(f"Updated grid size: {self.grid_size}")
    
    def _create_tile_manager(self):
        """Create the tile manager for the simulation."""
        self.logger.info("Creating tile manager")
        
        self.tile_manager = TileManager(
            grid_width=self.grid_size[0],
            grid_height=self.grid_size[1],
            tile_size=self.config.DEFAULT_TILE_SIZE,
            overlap=self.config.DEFAULT_TILE_OVERLAP,
            memory_limit_mb=self.config.MEMORY_LIMIT_MB,
            num_layers=self.config.DEFAULT_NUM_LAYERS
        )
        
        self.logger.info(f"Created tile manager with {self.tile_manager.total_tiles} tiles "
                   f"({self.tile_manager.tiles_x}x{self.tile_manager.tiles_y})")
    
    def _initialize_forest_model(self):
        """Initialize the forest model using TiledLiDARIntegration."""
        self.logger.info("Creating forest model with tiled LiDAR integration")
        
        # Create model using TiledLiDARIntegration
        self.tile_integration = TiledLiDARIntegration.create_model_from_rasters(
            base_dir=self.base_dir,
            target_resolution=self.config.MODEL_RESOLUTION,
            num_layers=self.config.DEFAULT_NUM_LAYERS,
            tile_size=self.config.DEFAULT_TILE_SIZE,
            overlap=self.config.DEFAULT_TILE_OVERLAP,
            debug=True
        )
        
        # Get the forest model from the integration
        self.model = self.tile_integration.forest_model
        
        # Apply configuration settings to the model
        if hasattr(self.model, 'config'):
            self.model.config = self.config
        
        # Set optimization parameters
        if hasattr(self.model, 'store_full_states'):
            self.model.store_full_states = self.config.STORE_FULL_STATES
        if hasattr(self.model, 'use_differential_history'):
            self.model.use_differential_history = self.config.USE_DIFFERENTIAL_HISTORY
        if hasattr(self.model, 'history_save_interval'):
            self.model.history_save_interval = self.config.HISTORY_SAVE_INTERVAL
        if hasattr(self.model, 'storage_optimization_level'):
            self.model.storage_optimization_level = self.config.STORAGE_OPTIMIZATION_LEVEL
    
    def _setup_environment(self):
        """Set up environmental conditions for the simulation."""
        self.logger.info("Setting up environmental conditions")
        
        # Load terrain data if available
        if self.dem_path:
            self.logger.info(f"Loading terrain data from {self.dem_path}")
            self.model.load_terrain_data(self.dem_path)
        
        # Load fuel moisture data if available
        if self.fuel_moisture_path and hasattr(self.model, 'load_fuel_moisture'):
            self.logger.info(f"Loading fuel moisture data from {self.fuel_moisture_path}")
            self.model.load_fuel_moisture(self.fuel_moisture_path)
        
        # Set wind conditions
        if hasattr(self.model, 'initialize_terrain_wind'):
            self.logger.info(f"Initializing terrain-influenced wind: "
                       f"{self.config.WIND_DIRECTION}°, {self.config.WIND_INFLUENCE}m/s")
            self.model.initialize_terrain_wind(
                self.config.WIND_DIRECTION,
                self.config.WIND_INFLUENCE,
                terrain_effect_strength=self.config.SLOPE_INFLUENCE
            )
        else:
            self.logger.info(f"Initializing uniform wind")
            self.model.initialize_wind(
                self.config.WIND_DIRECTION,
                self.config.WIND_INFLUENCE
            )
        
        # Set ignition point (default to center of grid)
        center_x = self.grid_size[0] // 2
        center_y = self.grid_size[1] // 2
        self.logger.info(f"Setting ignition point at ({center_x}, {center_y})")
        self.model.set_ignition(center_x, center_y)
    
    def run(self):
        """
        Run the forest fire simulation.
        
        Returns:
            Dict with simulation results
        """
        self.logger.info(f"Running simulation for up to {self.config.MAX_STEPS} steps")
        start_time = time.time()
        
        # Set random seed if provided for reproducible results
        if hasattr(self.config, 'RANDOM_SEED') and self.config.RANDOM_SEED is not None:
            np.random.seed(self.config.RANDOM_SEED)
            self.logger.info(f"Using random seed: {self.config.RANDOM_SEED}")
        
        # Track memory usage before simulation
        memory_before = None
        if HAS_PSUTIL:
            try:
                process = psutil.Process(os.getpid())
                memory_before = process.memory_info().rss / (1024 * 1024)  # MB
                self.logger.info(f"Memory usage before simulation: {memory_before:.2f} MB")
            except Exception as e:
                self.logger.warning(f"Error tracking memory: {e}")
            
        # Enable optimizations if available
        self._enable_optimizations()
        
        # Run the simulation with optimized parameters
        self.results = self.model.run_simulation(
            max_steps=self.config.MAX_STEPS,
            stop_when_fire_extinguished=getattr(self.config, 'STOP_WHEN_FIRE_EXTINGUISHED', True)
        )
        
        # Track memory usage after simulation
        if HAS_PSUTIL and memory_before is not None:
            try:
                process = psutil.Process(os.getpid())
                memory_after = process.memory_info().rss / (1024 * 1024)  # MB
                memory_diff = memory_after - memory_before
                self.logger.info(f"Memory usage after simulation: {memory_after:.2f} MB (Δ: {memory_diff:+.2f} MB)")
                # Add memory info to results
                self.results['memory_before_mb'] = memory_before
                self.results['memory_after_mb'] = memory_after
                self.results['memory_diff_mb'] = memory_diff
            except Exception as e:
                self.logger.warning(f"Error tracking memory: {e}")
        
        # Report results
        end_time = time.time()
        simulation_time = end_time - start_time
        
        # Calculate burn percentage
        total_cells = (self.grid_size[0] * self.grid_size[1] * 
                      self.config.DEFAULT_NUM_LAYERS)
        burn_pct = self.results['burned_cells'] / total_cells * 100
        
        # Calculate burn rate (cells per second)
        burn_rate = self.results['burned_cells'] / simulation_time if simulation_time > 0 else 0
        
        # Add performance metrics to results
        self.results['simulation_time'] = simulation_time
        self.results['burn_percentage'] = burn_pct
        self.results['burn_rate_cells_per_second'] = burn_rate
        
        self.logger.info(f"Simulation completed in {simulation_time:.1f} seconds")
        self.logger.info(f"Steps executed: {self.results['steps']}")
        self.logger.info(f"Cells burned: {self.results['burned_cells']} ({burn_pct:.2f}% of total)")
        self.logger.info(f"Burn rate: {burn_rate:.1f} cells/second")
        
        if 'fire_extinguished' in self.results:
            self.logger.info(f"Fire extinguished: {self.results['fire_extinguished']}")
        
        return self.results
    
    def _enable_optimizations(self):
        """Enable performance optimizations for the simulation."""
        # If numba is available, ensure JIT compilation is used
        try:
            if hasattr(self.model, 'enable_jit') and callable(self.model.enable_jit):
                self.model.enable_jit(True)
                self.logger.info("JIT compilation enabled for simulation")
            
            # Check if we can set thread optimization
            if hasattr(self.model, 'set_num_threads') and callable(self.model.set_num_threads):
                # Use half of available cores by default, or as specified in config
                num_threads = getattr(self.config, 'NUM_THREADS', 
                                      max(1, multiprocessing.cpu_count() // 2))
                self.model.set_num_threads(num_threads)
                self.logger.info(f"Using {num_threads} threads for simulation")
        except Exception as e:
            self.logger.warning(f"Error enabling optimizations: {e}")
    
    def visualize(self, output_dir=None):
        """
        Visualize the simulation results.
        
        Args:
            output_dir: Directory to save visualization results
        """
        if self.results is None:
            self.logger.warning("No simulation results to visualize")
            return
        
        # Use provided output_dir or default from config
        if output_dir is None:
            output_dir = getattr(self.config, 'OUTPUT_DIR', "results")
        
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        self.logger.info(f"Visualizing results to {output_dir}")
        visualize_results(self.model, output_dir)

def run_tiled_simulation(base_dir, dem_path=None, fuel_moisture_path=None, 
                        target_resolution=5.0, num_layers=8, 
                        target_memory_mb=4000, max_steps=200, config=None):
    """
    Run a forest fire simulation using LiDAR data with optimal memory management.
    
    Args:
        base_dir: Directory containing LiDAR PAD rasters
        dem_path: Optional path to DEM raster for terrain effects
        fuel_moisture_path: Optional path to fuel moisture raster
        target_resolution: Target spatial resolution in meters per cell
        num_layers: Number of vertical layers
        target_memory_mb: Target memory usage in MB per tile
        max_steps: Maximum number of simulation steps
        config: Optional ModelConfig instance from config_tools
        
    Returns:
        The simulation model with results
    """
    # Create configuration if not provided
    if config is None and HAS_CONFIG_TOOLS:
        config = create_config(
            model_resolution=target_resolution,
            num_layers=num_layers,
            memory_limit_mb=target_memory_mb,
            max_steps=max_steps
        )
    
    # Create and run the tiled simulation
    runner = TiledSimulationRunner(
        config=config,
        base_dir=base_dir,
        dem_path=dem_path,
        fuel_moisture_path=fuel_moisture_path
    )
    
    # Setup, run, and return the model
    runner.setup()
    runner.run()
    return runner.model

def visualize_results(model, output_dir=None):
    """
    Visualize the results of the forest fire simulation.
    
    Args:
        model: The forest model with simulation results
        output_dir: Directory to save visualization results (defaults to model's output_dir if available)
    """
    # Use model's output_dir if available and no output_dir specified
    if output_dir is None:
        output_dir = getattr(model, 'output_dir', "results")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Plot the progression of burning and burned cells
    if hasattr(model, 'history') and len(model.history) > 0:
        # Extract data for plotting
        steps = list(range(len(model.history)))
        burning_cells = []
        burned_cells = []
        
        for state in model.history:
            burning_cells.append(sum(state['burning_count']))
            burned_cells.append(sum(state['burned_count']))
        
        # Create figure for fire progression
        plt.figure(figsize=(10, 6))
        plt.plot(steps, burning_cells, 'r-', label='Burning Cells')
        plt.plot(steps, burned_cells, 'k-', label='Burned Cells')
        plt.xlabel('Time Step')
        plt.ylabel('Cell Count')
        plt.title('Fire Progression')
        plt.legend()
        plt.grid(True)
        
        # Save the figure
        progression_file = os.path.join(output_dir, 'fire_progression.png')
        plt.savefig(progression_file, dpi=100)
        plt.close()
        
        # Plot burned area (cumulative)
        area_per_cell = model.cell_area_meters if hasattr(model, 'cell_area_meters') else 25
        burned_area = [cells * area_per_cell / 10000 for cells in burned_cells]  # Convert to hectares
        
        plt.figure(figsize=(10, 6))
        plt.plot(steps, burned_area, 'k-', linewidth=2)
        plt.xlabel('Time Step')
        plt.ylabel('Burned Area (hectares)')
        plt.title('Cumulative Burned Area')
        plt.grid(True)
        
        # Save the figure
        area_file = os.path.join(output_dir, 'burned_area.png')
        plt.savefig(area_file, dpi=100)
        plt.close()
        
        # Create a top-down view of the final fire state
        plt.figure(figsize=(10, 10))
        
        # Try to get a composite view or the last layer
        final_state = model.history[-1]
        if 'composite' in final_state:
            # Use pre-computed composite view
            fire_state = final_state['composite']
        elif hasattr(model, 'get_state_at_step'):
            # Use the state reconstruction method
            reconstructed = model.get_state_at_step(len(model.history) - 1)
            if reconstructed is not None:
                # Create a composite view (maximum across layers)
                fire_state = np.max(reconstructed, axis=2)
            else:
                # Fall back to bottom layer if available
                fire_state = model.layers[0] if hasattr(model, 'layers') else None
        else:
            # Fall back to bottom layer if available
            fire_state = model.layers[0] if hasattr(model, 'layers') else None
        
        if fire_state is not None:
            plt.imshow(fire_state.T, origin='lower', cmap='hot',
                      vmin=0, vmax=2)
            plt.colorbar(label='Fire State (0=Unburned, 1=Burning, 2=Burned)')
            plt.title('Final Fire State')
            
            # Save the figure
            final_state_file = os.path.join(output_dir, 'final_fire_state.png')
            plt.savefig(final_state_file, dpi=100)
            plt.close()
            
            logger.info(f"Visualization results saved to {output_dir}")
            return {
                'progression': progression_file,
                'area': area_file,
                'final_state': final_state_file
            }
        else:
            logger.warning("Could not create final state visualization (no state data available)")
            plt.close()
    else:
        logger.warning("No history data available for visualization")
    
    return None

# Add this function to demonstrate how to use the DiskStorageManager with TiledSimulationWithStorage

def run_large_scale_simulation_with_disk_storage(config_file=None, config_dict=None, 
                                                output_dir="large_simulation_results",
                                                storage_dir="simulation_storage",
                                                cache_size_mb=512):
    """
    Run a large-scale simulation using disk-based storage for memory optimization.
    
    This function demonstrates how to use the DiskStorageManager and TiledSimulationWithStorage
    classes together to handle extremely large simulations that wouldn't fit in memory.
    
    Args:
        config_file: Path to a configuration file
        config_dict: Dictionary with configuration parameters
        output_dir: Directory to save simulation results
        storage_dir: Directory for temporary disk storage
        cache_size_mb: Size of the memory cache in MB
        
    Returns:
        Dictionary with simulation results summary
    """
    import os
    import time
    import json
    from datetime import datetime
    import numpy as np
    
    from core_simulation_framework import ModelConfig, TiledSimulationWithStorage, DiskStorageManager
    from config_tools import load_config, estimate_memory
    
    print(f"Setting up large-scale simulation with disk storage")
    
    # Load configuration
    if config_dict is not None:
        if isinstance(config_dict, dict):
            # Convert dict to ModelConfig
            config = ModelConfig()
            for key, value in config_dict.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        else:
            # Already a ModelConfig object
            config = config_dict
    elif config_file is not None:
        config = load_config(config_file)
    else:
        # Create default configuration
        config = ModelConfig()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract grid dimensions
    grid_size = (
        getattr(config, 'grid_width', 1000),
        getattr(config, 'grid_height', 1000)
    )
    
    # Estimate memory requirements using the current estimate_memory function
    memory_estimate = estimate_memory(
        config, 
        width_cells=grid_size[0],
        height_cells=grid_size[1]
    )
    
    # Use total_mb consistently
    print(f"Estimated memory for full simulation: {memory_estimate['total_mb']:.1f} MB")
    print(f"Setting up tiled simulation with disk storage (cache: {cache_size_mb} MB)")
    
    # Create storage manager
    storage_manager = DiskStorageManager(
        storage_dir=storage_dir,
        max_memory_mb=cache_size_mb
    )
    
    # Create the simulation
    simulation = TiledSimulationWithStorage(
        config=config,
        storage_manager=storage_manager
    )
    
    # Set environment parameters
    if hasattr(simulation, 'set_environmental_parameters'):
        simulation.set_environmental_parameters(
            wind_speed=getattr(config, 'wind_speed', 5.0),
            wind_direction=getattr(config, 'wind_direction', 0.0),
            moisture_content=getattr(config, 'moisture_content', 0.3)
        )
    
    # Load environmental data if available
    if hasattr(simulation, 'load_environmental_data'):
        print("Loading environmental data...")
        simulation.load_environmental_data(
            terrain_data=getattr(config, 'terrain_data', None),
            fuel_data=getattr(config, 'fuel_data', None),
            moisture_data=getattr(config, 'moisture_data', None),
            wind_data=getattr(config, 'wind_data', None)
        )
    
    # Set ignition points
    ignition_points = getattr(config, 'ignition_points', [(grid_size[0]//2, grid_size[1]//2, 0)])
    if not any(len(point) > 2 for point in ignition_points):
        # Add height coordinate if missing
        ignition_points = [(x, y, 0) for x, y in ignition_points]
    simulation.set_ignition_points(ignition_points)
    
    # Prepare for simulation
    max_steps = getattr(config, 'max_steps', 100)
    save_interval = getattr(config, 'save_interval', 10)
    
    # Time tracking
    start_time = time.time()
    
    # Run simulation
    print(f"Starting simulation run for {max_steps} steps")
    results_history = []
    
    for step in range(max_steps):
        # Run simulation step
        step_result = simulation.run_simulation_step()
        
        # Check if simulation has completed (no more active fire)
        if not step_result.get('active_fire', True):
            print(f"Simulation completed at step {step} - no active fire")
            break
            
        # Get statistics
        if step % 10 == 0:
            stats = step_result.get('statistics', {})
            active_tiles = step_result.get('active_tiles', 0)
            memory_used = step_result.get('memory_used_mb', 0)
            
            print(f"Step {step}: Active fire cells: {stats.get('active_fire_cells', 0)}, "
                  f"Active tiles: {active_tiles}, "
                  f"Memory usage: {memory_used:.1f} MB")
        
        # Save state at intervals
        if step % save_interval == 0:
            results_history.append({
                'step': step,
                'active_fire_cells': step_result.get('statistics', {}).get('active_fire_cells', 0),
                'burned_area_ha': step_result.get('statistics', {}).get('burned_area_ha', 0),
                'memory_used_mb': step_result.get('memory_used_mb', 0)
            })
    
    # Calculate execution time
    execution_time = time.time() - start_time
    
    # Export results
    print(f"Exporting simulation results to {output_dir}")
    if hasattr(simulation, 'export_results'):
        export_result = simulation.export_results(output_dir)
    
    # Create summary
    summary = {
        'execution_time_seconds': execution_time,
        'total_steps': len(results_history),
        'final_burned_area_ha': results_history[-1]['burned_area_ha'] if results_history else 0,
        'peak_memory_usage_mb': max([r['memory_used_mb'] for r in results_history]) if results_history else 0,
        'grid_size': grid_size,
        'cache_size_mb': cache_size_mb,
        'timestamp': datetime.now().isoformat(),
        'results_path': os.path.abspath(output_dir)
    }
    
    # Save summary to file
    with open(os.path.join(output_dir, 'simulation_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Cleanup
    if hasattr(simulation, 'cleanup'):
        simulation.cleanup()
    
    print(f"Simulation completed in {execution_time:.1f} seconds")
    print(f"Results saved to {os.path.abspath(output_dir)}")
    
    return summary

def benchmark_simulation(
    grid_size=(1000, 1000),
    num_layers=3,
    output_dir="benchmark_results",
    repetitions=3,
    include_profiling=True,
    config_file=None,
    custom_params=None
):
    """
    Run benchmark tests on the forest fire simulation with different configurations.
    
    Parameters:
    -----------
    grid_size : tuple
        Size of the simulation grid as (width, height)
    num_layers : int
        Number of vertical layers in the simulation
    output_dir : str
        Directory to save benchmark results
    repetitions : int
        Number of times to repeat each test for more reliable results
    include_profiling : bool
        Whether to include detailed profiling information
    config_file : str, optional
        Path to configuration file to use (if None, uses default settings)
    custom_params : dict, optional
        Custom parameters to override in the configuration
        
    Returns:
    --------
    dict
        Dictionary containing benchmark results
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize results dictionary
    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "grid_size": grid_size,
        "num_layers": num_layers,
        "repetitions": repetitions,
        "configurations": [],
        "system_info": {
            "processor": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "platform": psutil.Process().cpu_affinity() if hasattr(psutil.Process(), 'cpu_affinity') else None
        }
    }
    
    # Load configuration
    if config_file:
        config = ModelConfig.from_file(config_file)
    else:
        config = ModelConfig()
    
    # Apply custom parameters if provided
    if custom_params:
        for key, value in custom_params.items():
            setattr(config, key, value)
    
    # Set grid size and layers
    config.grid_size = grid_size
    config.num_vertical_layers = num_layers
    
    # Get memory estimate
    memory_estimate = estimate_memory(
        config,
        width_cells=grid_size[0],
        height_cells=grid_size[1]
    )
    results["memory_estimate_mb"] = memory_estimate["total_mb"]
    
    # Define configurations to test
    configurations = [
        {"name": "Baseline", "tiling": False, "multi_resolution": False, "disk_storage": False},
        {"name": "With Tiling", "tiling": True, "multi_resolution": False, "disk_storage": False, 
         "tile_size": 128, "max_active_tiles": 16},
        {"name": "With Multi-resolution", "tiling": False, "multi_resolution": True, "disk_storage": False,
         "low_res_factor": 4, "high_res_radius": 200},
        {"name": "With Disk Storage", "tiling": True, "multi_resolution": False, "disk_storage": True,
         "tile_size": 128, "max_active_tiles": 16, "disk_cache_size_mb": 512},
        {"name": "Full Optimization", "tiling": True, "multi_resolution": True, "disk_storage": True,
         "tile_size": 128, "max_active_tiles": 16, "low_res_factor": 4, "high_res_radius": 200, 
         "disk_cache_size_mb": 512}
    ]
    
    # Run benchmarks for each configuration
    for config_params in configurations:
        config_name = config_params.pop("name")
        print(f"Running benchmark for configuration: {config_name}")
        
        # Create test configuration by copying and updating the base config
        test_config = ModelConfig()
        for attr, value in vars(config).items():
            setattr(test_config, attr, value)
        
        # Apply configuration specific parameters
        for param, value in config_params.items():
            setattr(test_config, param, value)
        
        # Initialize result data for this configuration
        config_results = {
            "name": config_name,
            "settings": config_params,
            "runs": []
        }
        
        # Run the test multiple times
        for i in range(repetitions):
            run_result = _run_single_benchmark(test_config, output_dir, include_profiling)
            config_results["runs"].append(run_result)
            print(f"  Run {i+1}/{repetitions} completed: {run_result['execution_time']:.2f}s, "
                  f"{run_result['peak_memory_mb']:.1f}MB")
        
        # Calculate averages
        config_results["avg_execution_time"] = np.mean([r["execution_time"] for r in config_results["runs"]])
        config_results["avg_peak_memory_mb"] = np.mean([r["peak_memory_mb"] for r in config_results["runs"]])
        config_results["avg_cells_per_second"] = np.mean([r["cells_per_second"] for r in config_results["runs"]])
        
        # Add to results
        results["configurations"].append(config_results)
    
    # Calculate relative performance metrics
    baseline = next((c for c in results["configurations"] if c["name"] == "Baseline"), None)
    if baseline:
        baseline_time = baseline["avg_execution_time"]
        baseline_memory = baseline["avg_peak_memory_mb"]
        baseline_cells = baseline["avg_cells_per_second"]
        
        for config in results["configurations"]:
            config["relative_time"] = (config["avg_execution_time"] / baseline_time) * 100
            config["relative_memory"] = (config["avg_peak_memory_mb"] / baseline_memory) * 100
            config["relative_cells"] = (config["avg_cells_per_second"] / baseline_cells) * 100
    
    # Save results to file
    result_file = os.path.join(output_dir, f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(result_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Benchmark completed. Results saved to {result_file}")
    return results

def _run_single_benchmark(config, output_dir, include_profiling):
    """Run a single benchmark test with the given configuration"""
    # Create a unique output directory for this run
    run_dir = os.path.join(output_dir, f"run_{int(time.time())}")
    os.makedirs(run_dir, exist_ok=True)
    
    # Track memory and time
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
    peak_memory = initial_memory
    
    # Setup simulation
    start_setup = time.time()
    
    # Initialize disk storage if needed
    storage_manager = None
    if getattr(config, "disk_storage", False):
        storage_dir = os.path.join(run_dir, "storage")
        os.makedirs(storage_dir, exist_ok=True)
        storage_manager = DiskStorageManager(
            storage_dir=storage_dir,
            max_memory_mb=getattr(config, "disk_cache_size_mb", 512)
        )
    
    # Setup simulation
    simulation = TiledSimulationWithStorage(
        config=config,
        storage_manager=storage_manager
    )
    
    # Generate random forest data for testing
    grid_size = config.grid_size
    num_layers = config.num_vertical_layers
    
    # Generate simple random forest data
    for layer in range(num_layers):
        # Create a random forest with some patterns
        forest_data = np.random.random(grid_size) * 0.5
        # Add some dense patches
        for _ in range(5):
            x, y = np.random.randint(0, grid_size[0]), np.random.randint(0, grid_size[1])
            radius = np.random.randint(20, 100)
            y_grid, x_grid = np.ogrid[-y:grid_size[1]-y, -x:grid_size[0]-x]
            mask = x_grid*x_grid + y_grid*y_grid <= radius*radius
            forest_data[mask] += np.random.random() * 0.5
        
        # Clip values to [0, 1]
        forest_data = np.clip(forest_data, 0, 1)
        
        # Add to simulation
        simulation.set_layer_data(layer, forest_data)
    
    # Set ignition points
    center_x, center_y = grid_size[0] // 2, grid_size[1] // 2
    simulation.set_ignition_points([(center_x, center_y, 0)])
    
    setup_time = time.time() - start_setup
    current_memory = process.memory_info().rss / (1024 * 1024)
    peak_memory = max(peak_memory, current_memory)
    
    # Run simulation
    start_sim = time.time()
    stats = {"active_cells": [], "memory_usage": []}
    
    for step in range(200):  # Run for a fixed number of steps
        simulation.step()
        
        # Collect statistics every 10 steps
        if step % 10 == 0:
            current_memory = process.memory_info().rss / (1024 * 1024)
            peak_memory = max(peak_memory, current_memory)
            stats["active_cells"].append(simulation.count_active_cells())
            stats["memory_usage"].append(current_memory)
    
    sim_time = time.time() - start_sim
    current_memory = process.memory_info().rss / (1024 * 1024)
    peak_memory = max(peak_memory, current_memory)
    
    # Generate output
    start_output = time.time()
    output_file = os.path.join(run_dir, "simulation_result.npy")
    simulation.save_state(output_file)
    output_time = time.time() - start_output
    
    # Final memory check
    final_memory = process.memory_info().rss / (1024 * 1024)
    peak_memory = max(peak_memory, final_memory)
    
    # Calculate cells processed per second
    total_cells = grid_size[0] * grid_size[1] * num_layers
    cells_per_second = total_cells / sim_time if sim_time > 0 else 0
    
    # Prepare result
    result = {
        "execution_time": setup_time + sim_time + output_time,
        "setup_time": setup_time,
        "simulation_time": sim_time,
        "output_time": output_time,
        "initial_memory_mb": initial_memory,
        "peak_memory_mb": peak_memory,
        "final_memory_mb": final_memory,
        "memory_difference_mb": final_memory - initial_memory,
        "cells_per_second": cells_per_second,
        "total_cells": total_cells,
        "burned_cells": simulation.count_burned_cells(),
        "active_cell_stats": stats["active_cells"],
    }
    
    # Add profiling data if requested
    if include_profiling and storage_manager:
        result["storage_stats"] = {
            "cache_hits": storage_manager.get_cache_hits(),
            "cache_misses": storage_manager.get_cache_misses(),
            "disk_reads": storage_manager.get_disk_reads(),
            "disk_writes": storage_manager.get_disk_writes()
        }
    
    return result

# Add this function to bridge between the two naming conventions
def estimate_memory_requirements(grid_width, grid_height, num_layers=3, 
                                store_history=True, history_frequency=10):
    """
    Wrapper function for estimate_memory from config_tools to maintain 
    backward compatibility.
    
    Args:
        grid_width (int): Width of the grid in cells
        grid_height (int): Height of the grid in cells
        num_layers (int): Number of vertical layers
        store_history (bool): Whether to store simulation history
        history_frequency (int): Frequency of history recording
        
    Returns:
        Dict with memory requirement estimates
    """
    # Import estimate_memory at function call time to avoid circular imports
    from config_tools import estimate_memory, ModelConfig
    
    # Create a temporary config with the right parameters
    config = ModelConfig()
    
    # Set essential parameters that affect memory estimation
    config.num_layers = num_layers
    
    # Set history parameters if the ModelConfig supports them
    if hasattr(config, 'store_full_states'):
        config.store_full_states = store_history
    if hasattr(config, 'history_save_interval'):
        config.history_save_interval = history_frequency
    
    # Call the standard estimate_memory function
    memory_estimates = estimate_memory(config, grid_width, grid_height)
    
    # Ensure backward compatibility with any code expecting the old format
    # Add any legacy fields that might be expected
    if 'total_mb' not in memory_estimates and 'total_memory_mb' in memory_estimates:
        memory_estimates['total_mb'] = memory_estimates['total_memory_mb']
    
    return memory_estimates

def _setup_logging(log_dir=None, log_level=None, track_memory=False):
    """
    Set up logging for the simulation.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        track_memory: Whether to track memory usage in logs
    """
    # Define the logging configuration
    log_config = {
        "log_levels": {
            "run_tiled_simulation": log_level or "INFO",
            "core_simulation_framework": log_level or "INFO",
            "fire_simulation_engine": log_level or "INFO",
        },
        "console_format": "simple",
        "file_format": "detailed",
        "separate_component_logs": True,
    }
    
    # Configure the logging system
    configure_logging(
        config=log_config,
        log_dir=log_dir or "simulation_logs",
        default_level=getattr(logging, (log_level or "INFO").upper(), logging.INFO),
        console=True
    )
    
    # Get the main logger
    logger = get_logger(
        "run_tiled_simulation",
        log_format="memory" if track_memory else "simple",
        track_memory=track_memory
    )
    
    return logger

if __name__ == "__main__":
    # Configure logging
    _setup_logging(
        log_dir="simulation_logs",
        log_level="INFO",
        track_memory=True
    )
    
    # Command-line interface
    import argparse
    
    parser = argparse.ArgumentParser(description='Run forest fire simulation with memory optimization')
    
    # Create subparsers for different modes
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')
    
    # Simulation mode
    sim_parser = subparsers.add_parser('simulate', help='Run a simulation')
    sim_parser.add_argument('--base_dir', type=str, required=True, help='Directory containing PAD rasters')
    sim_parser.add_argument('--dem', type=str, help='Path to DEM raster for terrain effects')
    sim_parser.add_argument('--moisture', type=str, help='Path to fuel moisture raster')
    sim_parser.add_argument('--resolution', type=float, default=5.0, help='Target resolution in meters')
    sim_parser.add_argument('--layers', type=int, default=8, help='Number of vertical layers')
    sim_parser.add_argument('--memory', type=int, default=4000, help='Target memory usage in MB')
    sim_parser.add_argument('--steps', type=int, default=200, help='Maximum simulation steps')
    sim_parser.add_argument('--output', type=str, default='results', help='Output directory')
    sim_parser.add_argument('--config', type=str, help='Path to configuration file')
    sim_parser.add_argument('--log_level', type=str, default='INFO', 
                           choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                           help='Logging level')
    sim_parser.add_argument('--log_dir', type=str, default='simulation_logs', help='Log directory')
    sim_parser.add_argument('--track_memory', action='store_true', help='Track memory usage in logs')
    
    # Benchmark mode
    bench_parser = subparsers.add_parser('benchmark', help='Run benchmarks')
    bench_parser.add_argument('--size', type=int, nargs=2, default=[1000, 1000], help='Grid size (width, height)')
    bench_parser.add_argument('--layers', type=int, default=3, help='Number of vertical layers')
    bench_parser.add_argument('--output', type=str, default='benchmark_results', help='Output directory')
    bench_parser.add_argument('--repetitions', type=int, default=3, help='Number of test repetitions')
    bench_parser.add_argument('--config', type=str, help='Configuration file')
    bench_parser.add_argument('--profile', action='store_true', help='Include detailed profiling')
    bench_parser.add_argument('--log_level', type=str, default='INFO',
                           choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                           help='Logging level')
    bench_parser.add_argument('--log_dir', type=str, default='benchmark_logs', help='Log directory')
    bench_parser.add_argument('--track_memory', action='store_true', help='Track memory usage in logs')
    
    # Large-scale mode
    large_parser = subparsers.add_parser('large', help='Run large-scale simulation with disk storage')
    large_parser.add_argument('--config', type=str, help='Path to configuration file')
    large_parser.add_argument('--output', type=str, default='large_simulation_results', help='Output directory')
    large_parser.add_argument('--storage', type=str, default='simulation_storage', help='Disk storage directory')
    large_parser.add_argument('--cache', type=int, default=512, help='Memory cache size in MB')
    large_parser.add_argument('--log_level', type=str, default='INFO',
                            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                            help='Logging level')
    large_parser.add_argument('--log_dir', type=str, default='large_simulation_logs', help='Log directory')
    large_parser.add_argument('--track_memory', action='store_true', help='Track memory usage in logs')
    
    args = parser.parse_args()
    
    # Configure logging based on command-line arguments
    if hasattr(args, 'log_level') and hasattr(args, 'log_dir'):
        _setup_logging(
            log_dir=args.log_dir,
            log_level=args.log_level,
            track_memory=getattr(args, 'track_memory', False)
        )
    
    # Handle operation modes
    if args.mode == 'simulate' or args.mode is None:  # Default to simulate
        # Log the start of simulation
        logger.info(f"Starting simulation with target resolution {args.resolution}m, {args.layers} layers")
        
        # Load configuration if provided
        config = None
        if hasattr(args, 'config') and args.config:
            try:
                config = load_config(args.config)
                logger.info(f"Loaded configuration from {args.config}")
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
                logger.warning("Using default parameters")
        
        # Run the simulation
        model = run_tiled_simulation(
            base_dir=args.base_dir if hasattr(args, 'base_dir') else None,
            dem_path=args.dem if hasattr(args, 'dem') else None,
            fuel_moisture_path=args.moisture if hasattr(args, 'moisture') else None,
            target_resolution=args.resolution if hasattr(args, 'resolution') else 5.0,
            num_layers=args.layers if hasattr(args, 'layers') else 8,
            target_memory_mb=args.memory if hasattr(args, 'memory') else 4000,
            max_steps=args.steps if hasattr(args, 'steps') else 200,
            config=config
        )
        
        # Visualize results
        if hasattr(args, 'output'):
            logger.info(f"Saving visualization to {args.output}")
            visualize_results(model, args.output)
        
        logger.info("Simulation completed successfully")
    
    elif args.mode == 'benchmark':
        # Log the start of benchmarking
        logger.info(f"Starting benchmark with grid size {args.size}, {args.layers} layers, {args.repetitions} repetitions")
        
        # Run benchmarks
        results = benchmark_simulation(
            grid_size=tuple(args.size),
            num_layers=args.layers,
            output_dir=args.output,
            repetitions=args.repetitions,
            include_profiling=args.profile,
            config_file=args.config
        )
        
        # Print summary
        logger.info("Benchmark complete. Summary of results:")
        for config in results["configurations"]:
            relative_info = ""
            if "relative_time" in config:
                relative_info = f", {config['relative_time']:.1f}% time, {config['relative_memory']:.1f}% memory"
            
            logger.info(f"{config['name']}: {config['avg_execution_time']:.2f}s, "
                       f"{config['avg_peak_memory_mb']:.1f}MB, "
                       f"{config['avg_cells_per_second']:.0f} cells/s{relative_info}")
            
        logger.info(f"Full results saved to: {os.path.join(args.output, 'benchmark_results_*.json')}")
    
    elif args.mode == 'large':
        # Log the start of large-scale simulation
        logger.info(f"Starting large-scale simulation with disk storage, cache size: {args.cache}MB")
        
        # Run large-scale simulation
        summary = run_large_scale_simulation_with_disk_storage(
            config_file=args.config,
            output_dir=args.output,
            storage_dir=args.storage,
            cache_size_mb=args.cache
        )
        
        # Log summary information
        logger.info(f"Large-scale simulation completed in {summary['execution_time_seconds']:.1f} seconds")
        logger.info(f"Total steps: {summary['total_steps']}")
        logger.info(f"Final burned area: {summary['final_burned_area_ha']:.2f} hectares")
        logger.info(f"Peak memory usage: {summary['peak_memory_usage_mb']:.1f} MB")
        logger.info(f"Results saved to: {summary['results_path']}")
    else:
        parser.print_help() 