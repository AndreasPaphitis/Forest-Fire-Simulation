# LiDAR Calibration Framework Guide

This guide shows how to use the forest fire simulation calibration framework with your existing LiDAR data and geographic bounds.

## Quick Start with Production Configuration

The easiest way to get started is to use your existing production configuration file:

```python
from src.core.calibration import create_calibration_from_production_config

# Create calibration config from your production settings
config = create_calibration_from_production_config(
    production_config_path="hpc_deployment/Forest_Fire_Simulation_production_test.json",
    experiment_name="tenerife_fire_calibration",
    calibration_parameters=['spread_probability', 'fuel_consumption_rate', 'ignition_threshold']
)

print(config.summary())
# This automatically uses the same:
# - Geographic bounds (geo_bounds)
# - Resolution (model_resolution)  
# - LiDAR data directory (lidar_data_dir)
# - CRS (coordinate reference system)
# - Terrain data (dem_file)
# - Processing settings (tile_size, memory optimization, etc.)
```

## Manual Configuration

You can also create the configuration manually if you need more control:

```python
from src.core.calibration import CalibrationConfig, CalibrationMethod

config = CalibrationConfig(
    experiment_name="custom_lidar_calibration",
    method=CalibrationMethod.GRID_SEARCH,
    
    # Your calibration parameters (choose 3-6 for efficient calibration)
    calibration_parameters=[
        'spread_probability',
        'fuel_consumption_rate', 
        'ignition_threshold',
        'min_fuel_value',
        'slope_influence'
    ],
    
    # === GEOGRAPHIC CONFIGURATION ===
    # Tenerife bounds (adjust for your study area)
    geo_bounds=(273500, 3094350, 323500, 3144350),  # [min_x, min_y, max_x, max_y]
    crs="EPSG:25828",  # UTM Zone 28N for Tenerife
    model_resolution=5.0,  # 5 meters per grid cell
    
    # === LIDAR DATA CONFIGURATION ===
    use_lidar_data=True,
    lidar_data_dir="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/PAD Results/",
    auto_size_from_lidar=False,  # Use explicit geo_bounds
    extinction_coefficient=0.5,
    pad_bin_size=2.0,
    exclude_ground_layer=True,
    max_vegetation_height_m=50.0,
    
    # === TERRAIN DATA CONFIGURATION ===
    use_terrain=True,
    dem_file="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/DTM/Merged_DTM.tif",
    
    # === PROCESSING SETTINGS ===
    tile_size=200,
    tile_overlap_ratio=0.1,
    memory_optimization_level=1,
    max_parallel_tiles=10,
    
    # === CALIBRATION SETTINGS ===
    grid_search_points=5,  # 5^5 = 3,125 parameter combinations
    results_dir="calibration_results/lidar_calibration",
    max_workers=8,  # Adjust based on your HPC resources
    verbose=True
)
```

## Complete Calibration Workflow

Here's a complete example showing the full calibration process:

```python
import time
from src.core.calibration import (
    create_calibration_from_production_config,
    get_default_calibration_bounds,
    create_default_spatial_objective,
    GridSearchCalibrator,
    create_progress_callback,
    save_calibration_results
)

# Step 1: Create configuration
config = create_calibration_from_production_config(
    production_config_path="hpc_deployment/Forest_Fire_Simulation_production_test.json",
    experiment_name="tenerife_calibration"
)

# Step 2: Load your historical fire data
# For real usage, replace with your actual fire perimeter data
target_data = {
    'fire_perimeter': fire_perimeter_array,  # Your fire data as 2D numpy array
    'burned_cells': np.sum(fire_perimeter_array > 0),
    'geo_bounds': config.geo_bounds,
    'crs': config.crs,
    'resolution': config.model_resolution
}

# Step 3: Set up calibration components
parameter_bounds = get_default_calibration_bounds()
objective_function = create_default_spatial_objective()

# Step 4: Create and run calibrator
calibrator = GridSearchCalibrator(
    calibration_config=config,
    parameter_bounds=parameter_bounds,
    objective_function=objective_function
)

# Show estimation
estimation = calibrator.get_estimation_info()
print(f"Estimated calibration time: {estimation['estimated_time_seconds']/3600:.1f} hours")
print(f"Total parameter combinations: {estimation['total_combinations']}")

# Step 5: Run calibration with progress tracking
progress_callback = create_progress_callback(verbose=True)

start_time = time.time()
results = calibrator.run_calibration(
    target_data=target_data,
    progress_callback=progress_callback
)
runtime = time.time() - start_time

# Step 6: Analyze results
print(f"Calibration completed in {runtime/3600:.2f} hours")
print(f"Best objective value: {results.get_best_objective_value():.4f}")
print("Best parameters:")
for param, value in results.get_best_parameters().items():
    print(f"  {param}: {value:.4f}")

# Step 7: Save results
save_calibration_results(results, config.results_dir, "lidar_calibration")
```

## Key Configuration Parameters

### Geographic Parameters
- **`geo_bounds`**: `[min_x, min_y, max_x, max_y]` - Define your study area in CRS units
- **`crs`**: Coordinate reference system (e.g., `"EPSG:25828"` for Tenerife)
- **`model_resolution`**: Meters per grid cell (typically 5.0 for 5m resolution)

### LiDAR Parameters
- **`use_lidar_data`**: Set to `True` to enable LiDAR vegetation data
- **`lidar_data_dir`**: Path to your PAD results directory
- **`auto_size_from_lidar`**: Set to `False` to use explicit `geo_bounds`
- **`tile_size`**: Size of processing tiles (200-500 typical)
- **`memory_optimization_level`**: 0=speed, 1=balanced, 2=memory

### Terrain Parameters  
- **`use_terrain`**: Set to `True` to enable terrain effects
- **`dem_file`**: Path to your Digital Elevation Model file

## Performance Optimization for HPC

For HPC deployment, consider these settings:

```python
config = CalibrationConfig(
    # Use focused parameter set (3-5 parameters for efficiency)
    calibration_parameters=['spread_probability', 'fuel_consumption_rate', 'ignition_threshold'],
    
    # Conservative grid search for initial calibration
    grid_search_points=5,  # 5^3 = 125 combinations
    
    # HPC resource allocation
    max_workers=16,  # Adjust based on allocated CPUs
    memory_limit_gb=64.0,  # Adjust based on allocated memory
    simulation_timeout_minutes=60.0,
    
    # Processing optimization
    tile_size=200,  # Smaller tiles for memory efficiency
    memory_optimization_level=1,
    max_parallel_tiles=8
)
```

## Tips for Effective Calibration

1. **Start Small**: Begin with a subset of your study area and fewer parameters
2. **Use Sensitivity Analysis**: Run sensitivity analysis first to identify important parameters
3. **Progressive Refinement**: Start with coarse grid (3 points), then refine with more points
4. **Memory Management**: Monitor memory usage, especially with large LiDAR datasets
5. **Validation**: Always validate results against independent fire data

## Example: Tenerife Fire Calibration

For a typical Tenerife fire calibration:

```python
# Typical Tenerife configuration
config = CalibrationConfig(
    geo_bounds=(270000, 3090000, 330000, 3150000),  # Covers major fire-prone areas
    crs="EPSG:25828",  # UTM Zone 28N
    model_resolution=5.0,  # 5m resolution
    
    use_lidar_data=True,
    lidar_data_dir="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/PAD Results/",
    
    use_terrain=True,
    dem_file="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/DTM/Merged_DTM.tif",
    
    calibration_parameters=[
        'spread_probability',      # Critical for fire spread
        'fuel_consumption_rate',   # Critical for fire intensity
        'ignition_threshold',      # Critical for fire ignition
        'slope_influence',         # Important in mountainous terrain
        'wind_influence_on_spread' # Important for wind-driven fires
    ],
    
    grid_search_points=5,  # 5^5 = 3,125 combinations
    max_workers=16
)
```

This provides a good balance of comprehensiveness and computational efficiency for forest fire calibration in Tenerife's complex terrain and vegetation patterns. 