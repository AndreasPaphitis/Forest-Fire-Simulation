# Forest Fire Simulation: Configuration Tools User Guide

This guide explains how to use the `config_tools.py` module to create, manage, and optimize configurations for forest fire simulations.

> **Important Note**: The `config_tools.py` module and the `ModelConfig` class only cover simulation parameters, not preprocessing parameters. The preprocessing scripts (`height_normalisation_all.py`, `NRD_calculation.py`, and `PAD_calculation.py`) have their own separate configuration systems with command-line arguments and hard-coded defaults. Refer to the documentation in those scripts for preprocessing configuration options.

## Quick Start

```python
# Import the configuration tools
from config_tools import create_config, save_config, load_config

# Create a basic configuration
config = create_config(
    model_resolution=5.0,       # 5 meters per cell
    num_layers=10,              # 10 vertical layers
    wind_speed=6.0,             # Wind speed in m/s
    wind_direction=90           # East wind (degrees)
)

# Save the configuration for later use
save_config(config, "configs/my_first_config.json")

# Load a previously saved configuration
config = load_config("configs/my_first_config.json")
```

## Configuration Parameters

The configuration system is organized into several parameter categories:

### Spatial Parameters
These control the spatial resolution and structure of the simulation:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resolution` | Resolution in meters per cell (lower = more detail) | 5.0 |
| `num_layers` | Number of vertical layers | 10 |
| `layer_height` | Height of each layer in meters | 2.0 |

### Fire Spread Parameters
These control how fire spreads through the simulation:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `spread_probability` | Base probability of fire spreading horizontally (0-1) | 0.3 |
| `vertical_spread` | Probability of fire spreading upward (0-1) | 0.2 |
| `downward_spread` | Probability of fire spreading downward (0-1) | 0.1 |
| `diagonal_factor` | Factor to reduce spread probability for diagonal neighbors | 0.707 |
| `moisture_effect` | How strongly moisture reduces spread probability (0-1) | 0.5 |
| `ember_probability` | Probability of generating embers (0-1) | 0.05 |
| `ember_distance_mean` | Mean distance that embers travel in cells | 15.0 |
| `ember_distance_std` | Standard deviation of ember travel distance | 7.5 |
| `ember_ignition_probability` | Probability of ember causing ignition on landing (0-1) | 0.3 |

### Environmental Parameters
These simulate environmental conditions:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `wind_speed` | Wind speed in meters per second | 5.0 |
| `wind_direction` | Wind direction in degrees (0=N, 90=E, 180=S, 270=W) | 45 |
| `ambient_temp` | Ambient temperature in Celsius | 25 |
| `ignition_temp` | Temperature required for ignition in Celsius | 300 |
| `slope_influence` | How strongly terrain slope affects fire spread (0-1) | 0.3 |
| `terrain_threshold` | Threshold for significant terrain features in degrees | 5.0 |

### Memory Management Parameters
These control how large areas are handled:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `tile_size` | Size of processing tiles in cells | 150 |
| `tile_overlap` | Overlap between adjacent tiles in cells | 15 |
| `memory_limit_mb` | Memory limit in MB for optimization | 4000 |

### Simulation Control Parameters
These control the simulation execution:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `max_steps` | Maximum number of simulation steps | 100 |
| `store_full_states` | Whether to store full grid states (memory intensive) | False |

## Environmental Configuration

### Terrain Integration

You can configure terrain effects using the following parameters:

```python
config = create_config(
    # Terrain influence parameters
    slope_influence=0.4,        # How strongly terrain affects fire spread
    barranco_threshold=5.0,     # Slope threshold for ravine detection (degrees)
    barranco_amplification=1.5, # Wind amplification in ravines
)
```

These parameters control how terrain affects fire spread and wind patterns:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `slope_influence` | How strongly slope affects fire spread (0-1) | 0.3 |
| `barranco_threshold` | Slope threshold for identifying ravines (degrees) | 5.0 |
| `barranco_amplification` | Factor to amplify wind in ravines | 1.5 |

To use these settings with terrain data:

```python
from run_tiled_simulation import TiledSimulationRunner

# Create configuration
config = create_config(
    slope_influence=0.5,
    wind_direction=90,    # East wind
    wind_speed=6.0        # 6 m/s
)

# Create simulation runner with DEM path
runner = TiledSimulationRunner(
    config=config,
    base_dir="path/to/pad_data",
    dem_path="path/to/dem.tif"  # Digital Elevation Model
)

# Setup and run
results = runner.setup().run()
```

### Fuel Moisture Configuration

Fuel moisture significantly affects fire spread probability. Configure it using:

```python
config = create_config(
    # Moisture parameters
    fuel_moisture_baseline=0.3,  # Default fuel moisture (0-1)
    moisture_influence=0.6       # How strongly moisture affects spread (0-1)
)
```

These parameters control fuel moisture effects:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `fuel_moisture_baseline` | Default moisture when no spatial data is available (0-1) | 0.3 |
| `moisture_influence` | Scaling factor for moisture effects on fire spread | 0.6 |

To use spatially-explicit moisture data:

```python
from run_tiled_simulation import TiledSimulationRunner

# Create configuration with moisture settings
config = create_config(
    moisture_influence=0.7
)

# Create simulation runner with moisture data
runner = TiledSimulationRunner(
    config=config,
    base_dir="path/to/pad_data",
    fuel_moisture_path="path/to/moisture.tif"  # Spatial moisture data
)

# Setup and run
results = runner.setup().run()
```

## Large-Scale Simulation Configuration

### Tiled Simulation Runner

For very large areas, the `TiledSimulationRunner` provides advanced memory-optimized simulation capabilities:

```python
from run_tiled_simulation import TiledSimulationRunner

# Create runner with configuration
runner = TiledSimulationRunner(
    config=config,
    base_dir="path/to/pad_data"
)

# Setup and run
results = runner.setup().run()
```

The runner automatically determines geographic extent, optimizes configuration, and sets up the environment. Key configuration parameters affecting its behavior:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `tile_size` | Size of processing tiles in grid cells | 200 |
| `tile_overlap` | Overlap between adjacent tiles | 20 |
| `memory_limit_mb` | Memory limit for optimization | 4000 |
| `model_resolution` | Spatial resolution in meters | 5.0 |

The runner will automatically adjust these parameters when needed based on the area size and available memory:

```python
# Create configuration
config = create_config(
    # Specify base parameters - these may be optimized automatically
    model_resolution=5.0,
    tile_size=200,
    tile_overlap=20,
    memory_limit_mb=4000,
    
    # These parameters won't be automatically adjusted
    wind_speed=6.0,
    wind_direction=90
)

# Create runner
runner = TiledSimulationRunner(config=config, base_dir="path/to/pad_data")

# Setup (includes configuration optimization)
runner.setup()

# Check the optimized configuration
print(f"Optimized resolution: {runner.config.model_resolution}m")
print(f"Optimized tile size: {runner.config.tile_size} cells")
```

### Processing Large Geographic Areas

When working with very large areas (e.g., entire islands or regions), specialized functions are available:

```python
from vegetation_data_integration import process_tenerife_at_5m

# Process entire island at 5m resolution
processed_data = process_tenerife_at_5m(
    base_dir="path/to/pad_rasters",
    output_dir="path/to/output",
    num_layers=80,           # 80 vertical layers
    layer_group_size=10      # Process in groups of 10 layers
)
```

This specialized function ensures the resolution is never compromised, maintaining exactly 5m resolution throughout, while optimizing memory usage through tiling and layer grouping.

## Common Tasks

### Creating Configurations

Creating a custom configuration with specific parameters:

```python
config = create_config(
    # Spatial parameters
    resolution=2.5,       # Higher resolution (2.5m per cell)
    num_layers=15,        # More vertical layers
    layer_height=1.5,     # Layer height in meters
    
    # Fire behavior
    spread_probability=0.35,
    vertical_spread=0.25,
    downward_spread=0.12,
    diagonal_factor=0.7,
    moisture_effect=0.4,
    
    # Ember parameters
    ember_probability=0.1,
    ember_distance_mean=20.0,
    ember_distance_std=10.0,
    ember_ignition_probability=0.35,
    
    # Environmental conditions
    wind_speed=8.0,
    wind_direction=180,   # South wind
    ambient_temp=30,
    ignition_temp=280,
    slope_influence=0.35,
    terrain_threshold=4.5,
    
    # Memory management
    tile_size=100,
    tile_overlap=10,
    memory_limit_mb=3000,
    
    # Simulation control
    max_steps=150,
    store_full_states=True
)
```

### Using Presets with ConfigurationManager

Create configurations from predefined presets:

```python
from config_tools import ConfigurationManager

# Initialize the manager
manager = ConfigurationManager()

# Create configuration from a preset
config = manager.create_config(preset="high_resolution")

# Create with a preset and override some values
config = manager.create_config(
    preset="large_area", 
    wind_speed=10.0, 
    ember_probability=0.15
)

# Available presets: "high_resolution", "large_area", 
# "memory_optimized", "ember_focused"
```

### Saving and Loading Configurations

Save a configuration to reuse later:

```python
# Save configuration
save_config("high_wind_config", config)

# List all saved configurations
available_configs = list_configs()
print("Available configurations:", available_configs)

# Load a configuration
config = load_config("high_wind_config")
```

### Validating Configurations

Check if a configuration is valid:

```python
is_valid, issues = validate_config(config)

if not is_valid:
    print("Configuration has issues:")
    for issue in issues:
        print(f"- {issue}")
else:
    print("Configuration is valid")
```

### Memory Estimation

Estimate memory requirements before running a simulation:

```python
# Estimate for area with 1000×1000 cells
memory = estimate_memory(config, width_cells=1000, height_cells=1000)

print(f"Total memory required: {memory['total_mb']:.1f} MB")
print(f"Number of tiles: {memory.get('num_tiles', 1)}")
print(f"Memory per tile: {memory.get('per_tile_mb', memory['total_mb']):.1f} MB")
print(f"State grid: {memory['state_grid_mb']:.1f} MB")
print(f"Fuel grid: {memory['fuel_grid_mb']:.1f} MB")
print(f"Temperature grid: {memory['temperature_grid_mb']:.1f} MB")
print(f"2D grids (DEM, moisture): {memory['2d_grids_mb']:.1f} MB")
```

### Area-Based Optimization

Automatically optimize a configuration for a specific geographic area:

```python
# Optimize for a 5km × 3km area with 4GB memory limit
# First create a base configuration
base_config = create_config(
    model_resolution=5.0,
    num_layers=10,
    wind_speed=7.5,
    memory_limit_mb=4000
)

# Then optimize it for the specific area
optimized_config = optimize_config(
    base_config,               # Base configuration to optimize
    width_m=5000,              # 5 kilometers width
    height_m=3000,              # 3 kilometers height
    max_memory_mb=4000         # 4GB memory limit
)

print(f"Optimized resolution: {optimized_config.model_resolution} meters per cell")
print(f"Number of layers: {optimized_config.num_layers}")
print(f"Tile size: {optimized_config.tile_size} cells")
```

### Visualizing Configurations

Visualize a configuration to understand its settings:

```python
# You can print out the configuration details
print(f"Model resolution: {config.model_resolution}m")
print(f"Number of layers: {config.num_layers}")
print(f"Wind speed: {config.wind_speed}m/s at {config.wind_direction}°")
print(f"Fire spread probability: {config.spread_probability}")
```

## Using with Simulation Runner

To use your configuration with the simulation runner:

```python
from config_tools import create_config
from run_tiled_simulation import run_tiled_simulation, visualize_results

# Create configuration
config = create_config(
    model_resolution=2.5,
    num_layers=15,
    wind_speed=8.0,
    wind_direction=90,
    wind_influence=0.6,
    slope_influence=0.4,
    ember_probability=0.08,
    ember_distance=8,
    ember_ignition=0.35,
    max_steps=200
)

# Run simulation with the configuration
model = run_tiled_simulation(
    base_dir="path/to/pad_data",
    dem_path="path/to/dem.tif",
    fuel_moisture_path="path/to/fuel_moisture.tif",
    config=config
)

# Visualize the results
visualize_results(model)
```

## Configuration Relationships and Impacts

Understanding how parameters interact is essential for effective simulations:

### Resolution Impact
- Higher resolution (lower value) = More detailed simulation but higher memory usage
- Lower resolution (higher value) = Less detailed simulation but can cover larger areas

### Fire Spread Parameters
- Higher `spread_probability` = Faster fire spread across flat terrain 
- Higher `vertical_spread`/`downward_spread` = More vertical fire progression
- Higher `ember_probability` = More long-distance spotting behavior
- Higher `moisture_effect` = More pronounced dampening of fire in moist areas

### Environmental Parameters
- Higher `wind_speed` = Stronger directional influence on fire
- Higher `slope_influence` = Terrain has stronger effect on fire behavior
- Lower `ignition_temp` = Easier ignition of new cells

### Memory Management
- Larger `tile_size` = Fewer tiles but higher per-tile memory usage
- Higher `tile_overlap` = Better continuity between tiles but more redundant computation

## Tips for Effective Configuration

1. **Start with a low-resolution test**: Begin with coarse resolution (e.g., 10m) for quick testing before running detailed simulations.

2. **Monitor memory usage**: High-resolution simulations with many layers can require significant memory.

3. **Balance resolution and area size**: Larger areas typically require coarser resolution to remain feasible.

4. **Use the optimization tool**: For large areas, let the system automatically determine the best parameters.

5. **Save working configurations**: When you find settings that work well, save them for future use.

6. **Understand parameter tradeoffs**: For example, increasing resolution by 2x increases memory requirements by 4x.

7. **Adjust ember parameters for wind**: Higher wind speeds typically warrant higher ember distances.

8. **Layer count affects vertical behavior**: More layers give more detailed vertical fire progression but increase memory usage. 