# Forest Fire Simulation - Parameter Summary for Calibration Framework

## Status: ✅ COMPLETE
**All critical parameters for the calibration framework have been successfully added to the ModelConfig class.**

## Recently Added Parameters
- **`ignition_threshold`**: Added to ModelConfig with default value 0.5

## Complete Parameter Inventory

### **A. LITERATURE-INITIALIZED PARAMETERS (Well-established with strong theoretical foundation)**

#### Fire Behavior Parameters
- ✅ `spread_probability` (0.4) - Base probability of fire spreading between adjacent cells
- ✅ `fuel_moisture_baseline` (0.3) - Baseline moisture content for moderate drought conditions  
- ✅ `ember_probability` (0.1) - Probability of ember generation per burning cell
- ✅ `ember_ignition` (0.3) - Probability that landing ember successfully ignites fuel
- ✅ `extinction_coefficient` (0.5) - Light extinction coefficient for canopy calculations

#### Environmental Parameters
- ✅ `wind_speed` (5.0) - Base wind speed in m/s
- ✅ `wind_direction` (0.0) - Base wind direction in degrees
- ✅ `temperature` (25.0) - Ambient temperature in Celsius
- ✅ `humidity` (30.0) - Relative humidity percentage
- ✅ `reference_wind_speed` (10.0) - Reference wind speed for scaling calculations

### **B. CALIBRATION-REQUIRED PARAMETERS (Model-specific requiring optimization)**

#### Core Fire Mechanics (Tier 1 - Critical)
- ✅ `fuel_consumption_rate` (1.0) - Rate of fuel consumption during burning
- ✅ `ignition_threshold` (0.5) - **NEWLY ADDED** - Threshold for ignition probability
- ✅ `min_fuel_value` (0.1) - Minimum fuel value for combustion
- ✅ `max_fuel_value` (10.0) - Maximum fuel value for normalization

#### Environmental Interactions (Tier 2 - Moderate Sensitivity)
- ✅ `slope_influence` (0.3) - Influence of terrain slope on fire spread
- ✅ `wind_influence_on_spread` (0.5) - Wind effect on fire spread probability
- ✅ `terrain_effect_strength` (0.6) - Overall terrain modification strength

#### Ember Transport (Tier 3 - Specialized)
- ✅ `ember_distance` (5) - Maximum ember travel distance in grid cells
- ✅ `ember_height_factor` (0.2) - Height influence on ember generation
- ✅ `ember_rise` (2) - Maximum ember rise in layers
- ✅ `ember_wind_factor` (0.4) - Wind influence on ember direction

#### Terrain-Specific (Tier 4 - Local Effects)
- ✅ `barranco_threshold` (30.0) - Slope threshold for barranco detection (degrees)
- ✅ `barranco_amplification` (2.0) - Wind amplification factor in barrancos
- ✅ `barranco_direction_weight` (0.8) - Barranco direction influence weight
- ✅ `min_depression_depth` (5.0) - Minimum depression depth for detection (meters)
- ✅ `min_depression_area` (4) - Minimum depression area for detection (cells)

### **C. FIXED TECHNICAL PARAMETERS (Determined by data constraints)**

#### Spatial Resolution
- ✅ `model_resolution` (5.0) - Physical resolution in meters per cell
- ✅ `grid_size` (100) - Grid dimensions in cells
- ✅ `num_layers` (10) - Number of vertical layers
- ✅ `layer_height` (2.0) - Height of each layer in meters

#### Temporal Resolution
- ✅ `max_steps` (20) - Maximum simulation timesteps

### **D. ENVIRONMENTAL INPUT PARAMETERS (From external sources)**

#### Geographic Data
- ✅ `geo_bounds` (None) - Geographic boundaries for the simulation area
- ✅ `crs` ("EPSG:32628") - Coordinate reference system
- ✅ `dem_file` - Digital elevation model file path

#### LiDAR Integration
- ✅ `lidar_data_dir` (None) - Directory containing LiDAR-derived data
- ✅ `auto_size_from_lidar` (False) - Whether to auto-size grid from LiDAR extent

### **E. SIMULATION CONTROL PARAMETERS**

#### Execution Control
- ✅ `random_seed` (42) - Random seed for reproducibility
- ✅ `debug` (False) - Debug mode flag
- ✅ `stop_when_fire_extinguished` (True) - Stop simulation when no active cells

#### Memory Management
- ✅ `memory_optimization_level` (0) - Level of memory optimization (0-2)
- ✅ `use_disk_storage` (False) - Whether to use disk storage for states
- ✅ `bytes_per_cell` (10) - Memory usage per cell

## Parameter Validation Status

### ✅ All Parameters Present
All 13 calibration-required parameters identified in the methodology are now present in the ModelConfig class.

### ✅ Default Values Set
All parameters have scientifically reasonable default values based on literature review.

### ✅ Type Annotations
All parameters have proper type annotations for validation.

### ✅ Documentation
All parameters include descriptive comments explaining their purpose.

## Next Steps for Calibration Framework

1. **Parameter Bounds**: Define physically meaningful ranges for each calibration parameter
2. **Sensitivity Analysis**: Implement systematic sensitivity testing using the defined parameter tiers
3. **Optimization**: Set up multi-objective optimization targeting Jaccard Index and DICE coefficient
4. **Validation**: Cross-validate against 2023 EMSR fire delineation data

## Implementation Notes

- The `ignition_threshold` parameter is used in `fire_simulation_engine.py` line 564
- All other parameters are consistently accessed throughout the codebase via `getattr(self.config, parameter_name, default_value)`
- Parameter validation is handled by the `ModelConfig.__post_init__()` method
- Configuration can be saved/loaded via `save_config()` and `load_config()` functions

## Calibration Framework Compatibility

The parameter structure is fully compatible with the proposed calibration methodology:
- **Tier-based optimization** can proceed as planned
- **Literature initialization** values are set as defaults
- **Sequential calibration** protocol can target parameters by tier
- **Monte Carlo validation** can use the `random_seed` parameter for reproducibility 