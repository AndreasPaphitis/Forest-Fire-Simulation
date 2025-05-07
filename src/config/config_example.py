#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Forest Fire Simulation Configuration Examples and Integration Tests

This comprehensive script demonstrates how to use the config_tools module:
1. Creating, validating, saving and loading configurations
2. Estimating memory requirements and optimizing for specific areas
3. Using the ConfigurationManager to manage presets
4. Integrating configurations with the forest fire simulation system

The script contains both standalone examples and integration tests with
the simulation system (if available).
"""

import os
import logging
import numpy as np
from pathlib import Path
import time

# Import configuration tools
from config_tools import (
    create_config, validate_config, save_config, load_config, 
    estimate_memory, optimize_config, ConfigurationManager
)

# Try to import simulation modules (optional)
try:
    from core_simulation_framework import BaseForestModel
    from fire_simulation_engine import ForestModel
    from run_tiled_simulation import run_tiled_simulation, visualize_results
    # Optional import for tiled functionality
    from vegetation_data_integration import TiledLiDARIntegration
    SIMULATION_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Note: Some simulation modules couldn't be imported: {e}")
    print("Simulation integration examples will be skipped.")
    SIMULATION_IMPORTS_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("config_example")

# ====================================================================
# PART 1: BASIC CONFIGURATION EXAMPLES
# ====================================================================

def create_basic_config_example():
    """Create a basic configuration with essential parameters."""
    print("\n=== Creating a Basic Configuration ===")
    
    # Create a basic configuration with a few key parameters
    config = create_config(
        model_resolution=5.0,       # 5 meters per cell
        num_layers=10,              # 10 vertical layers
        wind_speed=7.5,             # Wind speed in m/s
        wind_direction=45.0         # Wind direction in degrees (NE)
    )
    
    print(f"Created configuration with:")
    print(f"  - Resolution: {config.model_resolution}m")
    print(f"  - Layers: {config.num_layers}")
    print(f"  - Wind: {config.wind_speed}m/s at {config.wind_direction}°")
    
    return config

def create_detailed_config_example():
    """Create a more detailed configuration with many parameters."""
    print("\n=== Creating a Detailed Configuration ===")
    
    # Create a detailed configuration with many parameters
    config = create_config(
        # Spatial parameters
        model_resolution=2.5,        # 2.5 meters per cell
        num_layers=15,               # 15 vertical layers
        layer_height=1.5,            # 1.5 meters per layer
        
        # Fire behavior parameters
        spread_probability=0.35,     # Base probability for fire spread
        vertical_spread=0.25,        # Upward spread probability
        downward_spread=0.15,        # Downward spread probability
        diagonal_factor=0.65,        # Diagonal spread probability factor
        
        # Ember parameters
        ember_probability=0.08,      # Probability of ember generation
        ember_distance=7,            # Mean ember travel distance (cells)
        ember_rise=2,                # Number of layers embers rise
        ember_ignition=0.35,         # Probability of ember causing ignition
        
        # Environmental conditions
        wind_speed=12.5,             # Wind speed in m/s
        wind_direction=225.0,        # Wind direction in degrees (SW)
        wind_influence=0.6,          # Scaling factor for wind effects
        slope_influence=0.4,         # Influence of slope on fire spread
        fuel_moisture_baseline=0.25, # Default fuel moisture content
        moisture_influence=0.7,      # Scaling factor for moisture effects
        
        # Fuel parameters
        min_fuel_value=0.1,          # Minimum fuel value to be combustible
        max_fuel_value=8.0,          # Maximum fuel value for normalization
        fuel_consumption_rate=0.25,  # Rate of fuel consumption per step
        
        # Memory management parameters
        tile_size=120,               # Size of each tile in cells
        tile_overlap=12,             # Overlap between tiles in cells
        memory_limit_mb=4000,        # Maximum memory usage in MB
        bytes_per_cell=15,           # Memory usage per cell in bytes
        
        # Simulation control parameters
        max_steps=500,               # Maximum number of simulation steps
        save_interval=20,            # Interval between saving states
        random_seed=42,              # Seed for random number generation
        stop_when_fire_extinguished=True, # Auto-stop when fire is out
        
        # Output configuration
        output_dir="results/high_detail",  # Output directory
        save_visualizations=True,    # Whether to save visualizations
        
        # Visualization parameters
        viz_frame_interval_ms=100,   # Milliseconds between animation frames
        viz_elevation_factor=1.8,    # Vertical exaggeration for 3D viz
        
        # PAD parameters
        extinction_coefficient=0.5,  # Extinction coefficient for PAD calculation
        pad_bin_size=1.5             # Vertical bin size for PAD in meters
    )
    
    print(f"Created detailed configuration with {config.num_layers} layers")
    print(f"Resolution: {config.model_resolution}m, Total height: {config.num_layers * config.layer_height}m")
    print(f"Wind: {config.wind_speed}m/s at {config.wind_direction}° (SW)")
    
    return config

def validate_config_example(config):
    """Validate a configuration for issues."""
    print("\n=== Validating Configuration ===")
    
    # Create an intentionally invalid configuration
    invalid_config = create_config(
        spread_probability=1.5,      # Invalid: must be between 0-1
        wind_direction=400.0,        # Invalid: should be 0-359
        tile_overlap=50,             # Will be invalid if tile_size < 100
        tile_size=40                 # Makes tile_overlap invalid
    )
    
    # Validate the valid configuration
    original_is_valid = validate_config(config)
    print(f"Original config valid: {original_is_valid}")
    
    # Validate the invalid configuration
    invalid_is_valid = validate_config(invalid_config)
    print(f"Invalid config valid: {invalid_is_valid}")
    
    # Test strict validation (should raise exception)
    try:
        validate_config(invalid_config, strict=True)
        print("Expected exception for strict validation, but none occurred!")
    except ValueError as e:
        error_message = str(e).split('\n')[0]
        print(f"Strict validation correctly raised exception:\n  {error_message}...")
    
    return invalid_config

def save_load_config_example(config):
    """Save and load a configuration to/from JSON file."""
    print("\n=== Saving and Loading Configuration ===")
    
    # Create directory if it doesn't exist
    os.makedirs("configs", exist_ok=True)
    
    # Save the configuration
    save_config(config, "configs/example_config.json")
    print(f"Configuration saved to: configs/example_config.json")
    
    # Load the configuration
    loaded_config = load_config("configs/example_config.json")
    print(f"Configuration loaded with resolution: {loaded_config.model_resolution}m")
    print(f"Wind settings: {loaded_config.wind_speed}m/s at {loaded_config.wind_direction}°")
    
    return loaded_config

def estimate_memory_example(config):
    """Estimate memory requirements for a configuration."""
    print("\n=== Estimating Memory Requirements ===")
    
    # Define area dimensions
    width_cells = 1000  # 1000 cells
    height_cells = 800  # 800 cells
    
    # Calculate area in meters
    width_meters = width_cells * config.model_resolution
    height_meters = height_cells * config.model_resolution
    print(f"Area dimensions: {width_meters}m x {height_meters}m")
    
    # Estimate memory requirements
    memory = estimate_memory(config, width_cells, height_cells)
    
    # Display memory requirements
    print(f"Total memory required: {memory['total_mb']:.2f} MB")
    
    # Check if tiling is required
    if memory.get("tiling_required", False):
        print(f"\nTiling required: {memory['num_tiles']} tiles ({memory['tiles_x']}x{memory['tiles_y']})")
        print(f"Tile size: {memory['tile_side']} cells")
        print(f"Memory per tile: {memory['memory_per_tile_mb']:.2f} MB")
    else:
        print("\nTiling not required - area fits in memory")
    
    return memory

def optimize_config_example():
    """Optimize a configuration for a specific area."""
    print("\n=== Optimizing Configuration for Area ===")
    
    # Define area dimensions and memory constraint
    width_meters = 5000.0  # 5 km
    height_meters = 4000.0  # 4 km
    target_memory_mb = 4000  # 4 GB
    
    print(f"Area dimensions: {width_meters}m x {height_meters}m")
    print(f"Memory constraint: {target_memory_mb} MB")
    
    # Create a base configuration
    base_config = create_config(
        model_resolution=5.0,
        num_layers=10,
        layer_height=2.0,
        memory_limit_mb=target_memory_mb
    )
    
    # Optimize configuration
    optimized_config = optimize_config(
        base_config,
        width_m=width_meters,
        height_m=height_meters,
        max_memory_mb=target_memory_mb
    )
    
    # Display optimized configuration
    print(f"Optimized resolution: {optimized_config.model_resolution}m")
    print(f"Optimized layers: {optimized_config.num_layers}")
    print(f"Optimized tile size: {optimized_config.tile_size} cells")
    print(f"Optimized tile overlap: {optimized_config.tile_overlap} cells")
    
    # Display grid dimensions with optimized resolution
    width_cells = int(width_meters / optimized_config.model_resolution)
    height_cells = int(height_meters / optimized_config.model_resolution)
    print(f"Grid dimensions: {width_cells} x {height_cells} cells")
    
    # Verify memory requirements
    memory = estimate_memory(optimized_config, width_cells, height_cells)
    print(f"Memory requirement with optimized config: {memory['total_mb']:.2f} MB")
    
    return optimized_config

def use_config_manager_example():
    """Demonstrate the use of the ConfigurationManager."""
    print("\n=== Using the Configuration Manager ===")
    
    # Create a configuration manager
    manager = ConfigurationManager()
    
    # Get available presets
    presets = list(manager.presets.keys())
    print(f"Available presets: {', '.join(presets)}")
    
    # Create configurations from different presets
    configs = {}
    
    # Default configuration
    configs["default"] = manager.create_config("default")
    print(f"Default preset: {configs['default'].model_resolution}m resolution, {configs['default'].wind_speed}m/s wind")
    
    # High-resolution configuration
    configs["high_res"] = manager.create_config("high_resolution")
    print(f"High resolution preset: {configs['high_res'].model_resolution}m resolution, {configs['high_res'].num_layers} layers")
    
    # Large-area configuration
    configs["large_area"] = manager.create_config("large_area")
    print(f"Large area preset: {configs['large_area'].model_resolution}m resolution, {configs['large_area'].tile_size} tile size")
    
    # Windy conditions with overrides
    configs["windy"] = manager.create_config("windy_conditions", model_resolution=3.0, num_layers=12)
    print(f"Windy conditions with overrides: {configs['windy'].model_resolution}m resolution, wind speed {configs['windy'].wind_speed}m/s")
    
    # Add a custom preset
    custom_preset = {
        "model_resolution": 3.5,
        "num_layers": 12,
        "ember_probability": 0.1,
        "ember_distance": 10,
        "ember_rise": 3,
        "ember_ignition": 0.4,
        "wind_speed": 8.0,
        "wind_direction": 180.0,  # South
        "wind_influence": 0.7,
        "slope_influence": 0.5
    }
    manager.add_preset("custom_forest", custom_preset)
    
    # Create a configuration from the custom preset
    configs["custom"] = manager.create_config("custom_forest")
    print(f"Custom preset: {configs['custom'].model_resolution}m resolution, " 
          f"wind {configs['custom'].wind_speed}m/s from South, "
          f"ember_probability {configs['custom'].ember_probability}")
    
    return manager, configs

# ====================================================================
# PART 2: SIMULATION INTEGRATION EXAMPLES
# ====================================================================

def test_direct_simulation():
    """
    Test running a simple simulation directly using configurations 
    from config_tools.
    """
    print("\n=== Testing Direct Simulation Integration ===")
    
    if not SIMULATION_IMPORTS_AVAILABLE:
        print("Skipping direct simulation test (simulation modules not available)")
        return None, None
    
    # Create a basic configuration for the simulation
    config = create_config(
        model_resolution=5.0,
        num_layers=8,
        layer_height=1.0,
        spread_probability=0.3,
        vertical_spread=0.2,
        downward_spread=0.15,
        wind_speed=5.0,
        wind_direction=90.0,
        wind_influence=0.5,
        slope_influence=0.3,
        fuel_moisture_baseline=0.3,
        max_steps=50,
        random_seed=42
    )
    
    print(f"Created simulation config with resolution: {config.model_resolution}m")
    
    # Create simulation data directories if they don't exist
    data_dir = Path("test_data")
    results_dir = Path("test_results")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    # Create a simple simulation space
    # In a real scenario, this would come from LiDAR or other data sources
    grid_size = (100, 100)
    forest_model = ForestModel(grid_size, config.num_layers)
    forest_model.config = config
    
    # Set up simple terrain
    terrain = np.zeros(grid_size)
    # Add a simple hill in the center
    x, y = np.meshgrid(np.linspace(-3, 3, grid_size[0]), np.linspace(-3, 3, grid_size[1]))
    r = np.sqrt(x**2 + y**2)
    terrain = 30 * np.exp(-0.5 * r**2)
    forest_model.load_terrain_data(terrain=terrain)
    
    # Set up simple fuel data (random forest density)
    np.random.seed(42)  # For reproducibility
    fuel_data = np.random.random((*grid_size, config.num_layers)) * 0.6 + 0.2
    forest_model.fuel_load = fuel_data
    
    # Set ignition point
    ignition_point = (20, 50)
    forest_model.set_ignition(ignition_point[0], ignition_point[1])
    
    print(f"Initialized forest model with grid size: {grid_size}")
    print(f"Ignition point set at: {ignition_point}")
    
    # Run the simulation
    print(f"Running simulation for {config.max_steps} steps...")
    start_time = time.time()
    result = forest_model.run_simulation(
        max_steps=config.max_steps,
        stop_when_fire_extinguished=True
    )
    
    # Show simulation results
    elapsed_time = time.time() - start_time
    print(f"Simulation completed in {elapsed_time:.2f} seconds")
    print(f"Steps executed: {result['steps']}")
    print(f"Cells burned: {result['burned_cells']}")
    
    return forest_model, result

def test_tiled_simulation():
    """
    Test running a tiled simulation using the run_tiled_simulation function
    with configurations from config_tools.
    """
    print("\n=== Testing Tiled Simulation Integration ===")
    
    if not SIMULATION_IMPORTS_AVAILABLE:
        print("Skipping tiled simulation test (simulation modules not available)")
        return None, None
    
    # Create a configuration for a larger area that requires tiling
    config = create_config(
        model_resolution=2.5,
        num_layers=10,
        layer_height=1.0,
        spread_probability=0.35,
        vertical_spread=0.25,
        downward_spread=0.15,
        ember_probability=0.07,
        ember_distance=8,
        ember_rise=2,
        ember_ignition=0.3,
        wind_speed=8.0,
        wind_direction=45.0,
        wind_influence=0.6,
        slope_influence=0.4,
        fuel_moisture_baseline=0.25,
        moisture_influence=0.7,
        tile_size=100,
        tile_overlap=10,
        memory_limit_mb=2000,
        max_steps=100,
        stop_when_fire_extinguished=True,
        output_dir="test_results/tiled_simulation"
    )
    
    # Define paths to data (these would be real paths in actual usage)
    base_dir = Path("test_data")
    dem_path = base_dir / "test_dem.tif"
    fuel_moisture_path = base_dir / "test_fuel_moisture.tif"
    
    # Test memory estimation for a large area
    width_m = 5000  # 5 km
    height_m = 4000  # 4 km
    width_cells = int(width_m / config.model_resolution)
    height_cells = int(height_m / config.model_resolution)
    
    memory = estimate_memory(config, width_cells, height_cells)
    
    print(f"Configuration for tiled simulation:")
    print(f"  - Resolution: {config.model_resolution}m")
    print(f"  - Layers: {config.num_layers} (height: {config.layer_height}m each)")
    print(f"  - Tile size: {config.tile_size} cells ({config.tile_size * config.model_resolution}m)")
    print(f"  - Memory limit: {config.memory_limit_mb} MB")
    
    print(f"\nFor an area of {width_m}m x {height_m}m:")
    print(f"  - Grid size: {width_cells} x {height_cells} cells")
    print(f"  - Total memory: {memory['total_mb']:.2f} MB")
    if memory.get('tiling_required', False):
        print(f"  - Tiling required: {memory['num_tiles']} tiles")
        print(f"  - Tile size: {memory['tile_side']} cells")
    
    # In a real scenario, we would call run_tiled_simulation() here
    print("\nTo run an actual tiled simulation with real data, use:")
    print("""
    model = run_tiled_simulation(
        base_dir="path/to/pad_data",
        dem_path="path/to/dem.tif",
        fuel_moisture_path="path/to/fuel_moisture.tif",
        config=config
    )
    """)
    
    return config, memory

def test_config_manager_integration():
    """
    Test using the ConfigurationManager to manage and apply simulation presets.
    """
    print("\n=== Testing Configuration Manager Integration ===")
    
    # Create a configuration manager
    manager = ConfigurationManager()
    
    # Create configurations for different scenarios
    configs = {
        "small_forest": manager.create_config("default"),
        "large_forest": manager.create_config("large_area"),
        "extreme_wind": manager.create_config("windy_conditions"),
        "high_detail": manager.create_config("high_resolution")
    }
    
    # Add a custom preset for a specific study area
    study_area_preset = {
        "model_resolution": 3.0,
        "num_layers": 12,
        "layer_height": 1.5,
        "spread_probability": 0.32,
        "vertical_spread": 0.22,
        "downward_spread": 0.12,
        "ember_probability": 0.07,
        "ember_distance": 8,
        "ember_rise": 2,
        "ember_ignition": 0.35,
        "wind_speed": 6.5,
        "wind_direction": 135.0,
        "wind_influence": 0.6,
        "slope_influence": 0.35,
        "fuel_moisture_baseline": 0.25,
        "moisture_influence": 0.7,
        "tile_size": 120,
        "max_steps": 300
    }
    manager.add_preset("study_area_2023", study_area_preset)
    configs["study_area"] = manager.create_config("study_area_2023")
    
    # Compare memory requirements for different presets
    print("Memory requirements for different configurations (1km² area):")
    
    for name, config in configs.items():
        # Adjust grid cells to match the resolution of each config
        w_cells = int(1000 / config.model_resolution)
        h_cells = int(1000 / config.model_resolution)
        
        memory = estimate_memory(config, w_cells, h_cells)
        tiling = f"({memory.get('num_tiles', 1)} tiles)" if memory.get('tiling_required', True) else "(no tiling)"
        
        print(f"  - {name.ljust(12)}: {memory['total_mb']:.1f} MB {tiling}")
        print(f"      Resolution: {config.model_resolution}m, Layers: {config.num_layers}")
    
    # Demonstrate how to select the best configuration based on area characteristics
    def select_best_config(area_width, area_height, forest_density, wind_speed, memory_limit):
        """Select the best configuration based on area characteristics."""
        
        # Choose resolution based on area size
        if area_width > 3000 or area_height > 3000:
            base_preset = "large_area"
        else:
            base_preset = "default"
        
        # Adjust for wind conditions
        if wind_speed > 7.0:
            base_preset = "windy_conditions"
        
        # Create the base configuration
        config = manager.create_config(base_preset)
        
        # Customize based on forest density
        if forest_density > 0.7:  # Dense forest
            config.num_layers += 2
            config.vertical_spread += 0.05
        
        # Optimize for the specific area
        width_cells = int(area_width / config.model_resolution)
        height_cells = int(area_height / config.model_resolution)
        memory = estimate_memory(config, width_cells, height_cells)
        
        # If memory exceeds limit, optimize configuration
        if memory['total_mb'] > memory_limit:
            base_config = config  # Save original config
            config = optimize_config(
                config, 
                width_m=area_width, 
                height_m=area_height, 
                max_memory_mb=memory_limit
            )
            logger.info(f"Optimized resolution from {base_config.model_resolution}m to {config.model_resolution}m")
        
        return config
    
    # Example usage of the selection function
    test_area = {
        "width": 2500,  # meters
        "height": 2000,  # meters
        "forest_density": 0.8,  # high density
        "wind_speed": 8.5,  # m/s
        "memory_limit": 3000  # MB
    }
    
    print("\nSelecting optimal configuration for test area:")
    print(f"  - Area: {test_area['width']}m x {test_area['height']}m")
    print(f"  - Forest density: {test_area['forest_density']}")
    print(f"  - Wind speed: {test_area['wind_speed']} m/s")
    print(f"  - Memory limit: {test_area['memory_limit']} MB")
    
    best_config = select_best_config(
        test_area["width"], 
        test_area["height"],
        test_area["forest_density"],
        test_area["wind_speed"],
        test_area["memory_limit"]
    )
    
    print("Selected configuration:")
    print(f"  - Resolution: {best_config.model_resolution}m")
    print(f"  - Layers: {best_config.num_layers}")
    print(f"  - Tile size: {best_config.tile_size} cells")
    print(f"  - Wind parameters: {best_config.wind_speed}m/s at {best_config.wind_direction}°")
    
    return manager, best_config

def main():
    """Run all configuration examples."""
    print("Forest Fire Simulation Configuration Examples and Integration Tests")
    print("=================================================================")
    
    # Part 1: Basic Configuration Examples
    print("\n--- PART 1: BASIC CONFIGURATION EXAMPLES ---")
    
    basic_config = create_basic_config_example()
    detailed_config = create_detailed_config_example()
    invalid_config = validate_config_example(detailed_config)
    loaded_config = save_load_config_example(detailed_config)
    memory_estimate = estimate_memory_example(detailed_config)
    optimized_config = optimize_config_example()
    manager, configs = use_config_manager_example()
    
    # Part 2: Simulation Integration Examples
    print("\n--- PART 2: SIMULATION INTEGRATION EXAMPLES ---")
    
    # Only run these if simulation modules are available
    if SIMULATION_IMPORTS_AVAILABLE:
        forest_model, direct_sim_result = test_direct_simulation()
        tiled_config, tiled_memory = test_tiled_simulation()
    else:
        print("\nSimulation modules not available. Skipping direct simulation tests.")
        print("To run these examples, ensure the following modules are installed:")
        print("  - core_simulation_framework")
        print("  - fire_simulation_engine")
        print("  - run_tiled_simulation")
        print("  - vegetation_data_integration")
    
    # Configuration Manager Integration (doesn't require simulation modules)
    manager, best_config = test_config_manager_integration()
    
    print("\nAll examples completed successfully.")
    print("Refer to CONFIG_TOOLS_USER_GUIDE.md for more detailed documentation.")

if __name__ == "__main__":
    main() 