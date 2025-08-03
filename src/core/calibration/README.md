# Forest Fire Simulation Calibration Framework

A comprehensive calibration system for optimizing forest fire simulation parameters against historical fire data or specific objectives.



## Key Features

- **Focused Calibration Methods**: Grid search for systematic parameter exploration and sensitivity analysis for parameter ranking
- **Flexible Objective Functions**: Spatial similarity metrics and fire behavior objectives
- **Parameter Management**: Physically-constrained parameter bounds with tier-based prioritization
- **Parallel Execution**: Multi-threaded/multi-process calibration for faster results
- **Comprehensive Analysis**: Sensitivity analysis, parameter ranking, and detailed reporting
- **Easy Integration**: Works seamlessly with existing forest fire simulation system
- **Production-Ready**: Only includes tested, working calibration methods

## Quick Start

```python
from src.core.calibration import (
    CalibrationConfig, CalibrationMethod,
    get_default_calibration_bounds,
    create_default_spatial_objective,
    GridSearchCalibrator
)

# 1. Create calibration configuration
config = CalibrationConfig(
    experiment_name="my_calibration",
    method=CalibrationMethod.GRID_SEARCH,
    objective=CalibrationObjective.SPATIAL_SIMILARITY,
    calibration_parameters=['spread_probability', 'fuel_consumption_rate'],
    grid_search_points=5
)

# 2. Set up calibration components
bounds = get_default_calibration_bounds()
objective = create_default_spatial_objective()

# 3. Run calibration
calibrator = GridSearchCalibrator(config, bounds, objective)
results = calibrator.run_calibration(target_data=my_target_data)

# 4. Get best parameters
best_params = results.get_best_parameters()
print(f"Best objective: {results.get_best_objective_value():.4f}")
```

## Framework Components

### 1. Configuration Management (`calibration_config.py`)

- **CalibrationConfig**: Main configuration class with all calibration settings
- **CalibrationMethod**: Enumeration of available calibration methods
- **CalibrationObjective**: Enumeration of objective function types

### 2. Parameter Management (`parameter_bounds.py`)

- **ParameterBounds**: Defines valid ranges and constraints for parameters
- **CalibrationParameter**: Wrapper for parameters with metadata
- **Tier-based prioritization**: Critical, moderate, and low sensitivity parameters

### 3. Objective Functions (`objective_functions.py`)

- **SpatialSimilarityObjective**: Jaccard, Dice, and Sørensen coefficients
- **FireBehaviorObjective**: Burned area and spread rate metrics

### 4. Calibration Algorithms

#### Grid Search (`grid_search.py`)
- **Purpose**: Systematic exploration of parameter space using a grid of points
- **Strengths**: Comprehensive coverage, deterministic results, parallel execution
- **Best for**: Parameter optimization when you need to explore the full space
- **Configurable**: Grid resolution per parameter, parallel workers, timeout handling
- **Sensitivity Analysis**: Includes basic correlation-based sensitivity analysis (use dedicated SensitivityAnalyzer for comprehensive analysis)

#### Sensitivity Analysis (`sensitivity_analysis.py`)
- **Purpose**: One-at-a-time parameter perturbation to identify important parameters
- **Strengths**: Fast execution, clear parameter ranking, guides optimization focus
- **Best for**: Understanding which parameters matter most before running expensive calibration
- **Output**: Parameter sensitivity ranking and importance scores
- **Method**: Range-based sensitivity analysis with standardized sensitivity indices
- **Coverage**: Handles all 5 calibration parameters with configurable test points

### 5. Utilities (`calibration_utils.py`)

- **Data Loading**: Support for GeoTIFF, shapefile, numpy, and JSON formats
- **Result Saving**: Multiple output formats (JSON, pickle, CSV)
- **Report Generation**: HTML reports with analysis and visualizations
- **Configuration Validation**: Comprehensive config checking

## Parameter Tiers

Parameters are organized into sensitivity-based tiers:

### Tier 1: Critical Parameters (High Sensitivity)
- `spread_probability`: Base fire spread probability
- `fuel_consumption_rate`: Rate of fuel consumption
- `wind_speed`: Base wind speed affecting fire spread
- `wind_influence_on_spread`: Wind effect on spread probability

### Tier 3: Low Sensitivity
- `ember_probability`: Ember generation probability

## Usage Examples

### 1. Basic Grid Search Calibration

```python
from src.core.calibration import *

# Create configuration
config = CalibrationConfig(
    experiment_name="basic_calibration",
    method=CalibrationMethod.GRID_SEARCH,
    calibration_parameters=['spread_probability', 'fuel_consumption_rate'],
    grid_search_points=5,  # 5x5 = 25 combinations
    results_dir="results/basic"
)

# Load target data
target_data = load_historical_fire_data("path/to/fire_perimeter.tif")

# Run calibration
bounds = get_default_calibration_bounds()
objective = create_default_spatial_objective()
calibrator = GridSearchCalibrator(config, bounds, objective)
results = calibrator.run_calibration(target_data=target_data)

# Save results
save_calibration_results(results, config.results_dir)
```

### 2. Sensitivity Analysis

```python
# Analyze parameter sensitivity
analyzer = SensitivityAnalyzer(
    calibration_config=config,
    parameter_bounds=bounds,
    objective_function=objective,
    perturbation_method="percentage",
    perturbation_values=[-0.2, -0.1, 0.1, 0.2]  # ±20%, ±10%
)

results = analyzer.run_sensitivity_analysis(target_data=target_data)

# Get most sensitive parameters
top_params = results.get_most_sensitive_parameters(5)
print("Most sensitive parameters:")
for param, sensitivity in top_params:
    print(f"  {param}: {sensitivity:.4f}")
```

### 3. Fire Behavior Calibration

```python
# Focus on fire behavior metrics
config = CalibrationConfig(
    objective=CalibrationObjective.FIRE_BEHAVIOR,
    calibration_parameters=['spread_probability', 'fuel_consumption_rate']
)

from src.core.calibration.objective_functions import FireBehaviorObjective
objective = FireBehaviorObjective(
    target_burned_area=250,
    target_spread_rate=6.25
)
# ... run calibration as before
```

### 4. Focused Calibration

```python
# Use sensitivity results to focus calibration
sensitive_params = [param for param, _ in sensitivity_results.get_most_sensitive_parameters(3)]

focused_config = CalibrationConfig(
    calibration_parameters=sensitive_params,
    grid_search_points=7  # Higher resolution for fewer parameters
)
# ... continue with focused calibration
```

### 5. LiDAR-Based Calibration

```python
# Create calibration config from production configuration file
from src.core.calibration import create_calibration_from_production_config

config = create_calibration_from_production_config(
    production_config_path="hpc_deployment/Forest_Fire_Simulation_production_test.json",
    experiment_name="tenerife_calibration",
    calibration_parameters=['spread_probability', 'fuel_consumption_rate']
)

# Or create manually with geographic parameters
config = CalibrationConfig(
    experiment_name="lidar_calibration",
    method=CalibrationMethod.GRID_SEARCH,
    
    # Geographic configuration
    geo_bounds=(273500, 3094350, 323500, 3144350),  # Tenerife bounds
    crs="EPSG:25828",
    model_resolution=5.0,
    
    # LiDAR configuration
    use_lidar_data=True,
    lidar_data_dir="/path/to/PAD_Results/",
    auto_size_from_lidar=False,
    
    # Terrain configuration
    use_terrain=True,
    dem_file="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/DTM/Merged_DTM.tif",
    
    # Processing settings
    tile_size=200,
    memory_optimization_level=1
)
```

## Geographic and LiDAR Data Integration

The calibration framework is designed to work seamlessly with the same geographic bounds, resolution, and LiDAR data sources used in your production simulations.

### Geographic Configuration

```python
config = CalibrationConfig(
    # Geographic bounds [min_x, min_y, max_x, max_y] in CRS units
    geo_bounds=(273500, 3094350, 323500, 3144350),
    
    # Coordinate reference system (e.g., "EPSG:25828" for Tenerife)
    crs="EPSG:25828",
    
    # Model resolution in meters per grid cell
    model_resolution=5.0,
    
    # Enable LiDAR vegetation data
    use_lidar_data=True,
    lidar_data_dir="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/PAD Results/",
    
    # Enable terrain effects
    use_terrain=True,
    dem_file="/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/Data/DTM/Merged_DTM.tif"
)
```

### Using Production Configuration Files

The easiest way to ensure consistency is to create calibration configs from your existing production configuration:

```python
from src.core.calibration import create_calibration_from_production_config

# Creates calibration config with same geographic/LiDAR settings as production
config = create_calibration_from_production_config(
    production_config_path="hpc_deployment/Forest_Fire_Simulation_production_test.json",
    experiment_name="my_calibration",
    calibration_parameters=['spread_probability', 'fuel_consumption_rate']
)
```

## Data Formats

### Target Fire Data

The framework supports multiple formats for historical fire data:

#### GeoTIFF Format
```python
target_data = load_historical_fire_data("fire_perimeter.tif", "geotiff")
```

#### Shapefile Format
```python
target_data = load_historical_fire_data("fire_perimeter.shp", "shapefile")
```

#### NumPy Array Format
```python
target_data = load_historical_fire_data("fire_perimeter.npy", "numpy")
```

#### JSON Format
```python
# JSON structure: {"fire_perimeter": [[0,1,0], [1,1,1], [0,1,0]]}
target_data = load_historical_fire_data("fire_perimeter.json", "json")
```

## Output Formats

### Results Storage
- **JSON**: Human-readable results with metadata
- **Pickle**: Complete Python objects for post-processing
- **CSV**: Tabular data for analysis in external tools

### Reports
- **HTML Reports**: Interactive reports with analysis and visualizations
- **Parameter Rankings**: Sensitivity-based parameter importance
- **Convergence Analysis**: Algorithm performance metrics

## Best Practices

### 1. Start with Sensitivity Analysis
```python
# Always start with sensitivity analysis to understand parameter importance
analyzer = SensitivityAnalyzer(config, bounds, objective)
sensitivity_results = analyzer.run_sensitivity_analysis(target_data)

# Use results to focus calibration on important parameters
important_params = [p for p, _ in sensitivity_results.get_most_sensitive_parameters(4)]
```

### 2. Use Tier-Based Calibration
```python
# Start with critical parameters (Tier 1)
from src.core.calibration.parameter_bounds import CalibrationTier, get_calibration_parameters_by_tier

tier1_params = get_calibration_parameters_by_tier(CalibrationTier.CRITICAL)
config.calibration_parameters = tier1_params
```

### 3. Progressive Grid Refinement
```python
# Start with coarse grid, then refine
coarse_config = CalibrationConfig(grid_search_points=3)  # 3^n combinations
# ... run calibration, analyze results

# Refine around best region
fine_config = CalibrationConfig(grid_search_points=5)  # 5^n combinations
# ... focus on promising parameter ranges
```

### 4. Validate Configurations
```python
# Always validate before running
is_valid, errors = validate_calibration_config(config)
if not is_valid:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
```

## Performance Considerations

### Memory Usage
- Use smaller grid sizes for initial exploration
- Consider using `store_full_states=False` to reduce memory
- Monitor memory usage with large parameter spaces

### Computation Time
- Grid search scales as `points^parameters`
- Use parallel execution for faster results
- Start with fewer parameters and smaller grids
- Consider sensitivity analysis to reduce parameter space

### Recommended Limits
- **Parameters**: 3-5 for initial calibration, up to 8 for comprehensive
- **Grid Points**: 3-5 per parameter for exploration, 7-10 for refinement
- **Grid Size**: Start with 50x50, increase based on computational resources

## Error Handling

The framework includes comprehensive error handling:

```python
try:
    results = calibrator.run_calibration(target_data)
    if results.successful_evaluations == 0:
        print("All evaluations failed - check configuration")
except Exception as e:
    logger.error(f"Calibration failed: {e}")
```

## Integration with Existing System

The calibration framework integrates seamlessly with the existing forest fire simulation:

```python
# Use calibrated parameters in regular simulation
best_params = results.get_best_parameters()
config = ModelConfig(**best_params)

# Run simulation with optimized parameters
forest_model = create_forest_model(config=config)
engine = FireSimulationEngine(forest_model=forest_model, config=config)
simulation_result = engine.run_simulation()
```

## Extending the Framework

### Adding New Calibration Methods

1. Create new method in `CalibrationMethod` enum
2. Implement calibrator class following `GridSearchCalibrator` pattern
3. Add to factory functions

### Adding New Objective Functions

1. Inherit from `ObjectiveFunction` base class
2. Implement `evaluate()` method
3. Add to objective creation functions

### Adding New Parameter Types

1. Extend `ParameterType` enum
2. Add validation logic in `ParameterBounds`
3. Update bounds generation functions

## Troubleshooting

### Common Issues

**Issue**: "No valid parameter combinations found"
**Solution**: Check parameter bounds and ensure they're not too restrictive

**Issue**: "All simulations fail"
**Solution**: Verify base configuration works with a manual simulation first

**Issue**: "Calibration takes too long"
**Solution**: Reduce grid_search_points or number of parameters

**Issue**: "Poor calibration results"
**Solution**: Try different objective functions or check target data quality

### Debug Mode

Enable debug logging for detailed information:

```python
config = CalibrationConfig(verbose=True, debug=True)
```

## Example Scripts

Complete working examples are provided in:
- `example_calibration.py`: Comprehensive examples of all calibration methods
- Run with: `python src/core/calibration/example_calibration.py`

## Dependencies

Required packages:
- numpy
- scipy (optional, for advanced metrics)
- pandas (optional, for CSV export)
- geopandas (optional, for shapefile support)
- rasterio (optional, for GeoTIFF support)
- gdal (optional, for geographic data)

## Future Enhancements

Potential future additions (when justified by clear need):
- **Cross-validation support**: For robust parameter estimation across multiple fire events
- **Interactive visualization tools**: Web-based interface for exploring calibration results
- **Automated parameter selection**: AI-guided selection of parameters to calibrate based on data availability
- **Advanced grid search**: Adaptive grid refinement around promising regions
- **Ensemble calibration**: Calibration across multiple fire scenarios simultaneously

**Note**: The framework previously included multi-objective functionality but this has been removed to focus on simpler, more reliable single-objective approaches. Additional optimization methods (Bayesian, genetic algorithms) will only be added if they demonstrate clear advantages over the current methods for fire modeling use cases.

## Support

For questions and issues:
1. Check this documentation
2. Review example scripts
3. Examine error messages and logs
4. Contact the development team

## License

Part of the Forest Fire Simulation project - see main project license. 