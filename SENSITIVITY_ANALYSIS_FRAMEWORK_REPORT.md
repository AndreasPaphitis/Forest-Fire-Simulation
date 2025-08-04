# Sensitivity Analysis Framework - Current State Report

## Executive Summary

The sensitivity analysis framework implements **comprehensive parameter coverage** with **13 calibration parameters** organized into two groups for systematic analysis. This provides thorough coverage of all core fire simulation mechanisms including fire spread, fuel dynamics, wind effects, terrain interactions, and ember generation.

## Current Parameter Configuration

### ✅ **Complete Parameter Set (13 Total)**

The framework analyzes 13 parameters organized into two groups:

#### **Group 1: Full Range Parameters (7 parameters)**
Parameters tested across their complete theoretical ranges:
1. `wind_influence_on_spread` - Wind effect on fire spread probability [0.0, 1.0]
2. `fuel_consumption_rate` - Rate of fuel consumption [0.1, 5.0]
3. `terrain_effect_strength` - Overall terrain effect strength [0.0, 1.0]
4. `barranco_amplification` - Wind speed amplification in ravines [1.0, 3.0]
5. `barranco_direction_weight` - Wind direction alignment weight in ravines [0.0, 1.0]
6. `slope_influence` - Terrain slope effect on fire spread [0.0, 1.0]
7. `ember_height_factor` - Height factor for ember generation [0.5, 2.0]

#### **Group 2: Constrained Range Parameters (6 parameters)**
Parameters tested within realistic operational ranges:
8. `wind_speed` - Base wind speed affecting fire spread [5.0, 15.0]
9. `wind_direction` - Wind direction in degrees [0.0, 360.0]
10. `ember_distance` - Ember travel distance [5.0, 50.0]
11. `ember_probability` - Ember generation probability [0.01, 0.3]
12. `spread_probability` - Base fire spread probability [0.1, 0.8]
13. `ember_ignition` - Ember ignition probability [0.1, 0.6]

## Framework Implementation Status

### ✅ **All 13 Parameters Are Consistently Defined**

**Parameter Distribution by Category:**
- **Fire Spread Parameters (2):** `spread_probability`, `wind_influence_on_spread`
- **Fuel Parameters (1):** `fuel_consumption_rate`
- **Wind Parameters (2):** `wind_speed`, `wind_direction`
- **Terrain Parameters (3):** `terrain_effect_strength`, `barranco_amplification`, `slope_influence`
- **Ember Parameters (4):** `ember_probability`, `ember_ignition`, `ember_distance`, `ember_height_factor`
- **Barranco Parameters (1):** `barranco_direction_weight`

## Framework Components Status

### ✅ **Core Components Fully Implemented**
1. **Parameter Bounds** (`src/core/calibration/parameter_bounds.py`)
   - Defines all 13 calibration parameters with appropriate bounds
   - Comprehensive validation and type checking
   - Literature-based range definitions

2. **Sensitivity Analysis Runner** (`scripts/sensitivity_analysis_runner.py`)
   - Implements 13-parameter analysis in two groups
   - HPC-optimized parallel processing (28 workers)
   - Comprehensive validation and error handling

3. **Calibration Configuration** (`src/core/calibration/calibration_config.py`)
   - Default parameter list includes all 13 parameters
   - Maintains group organization for systematic analysis
   - Fully consistent with bounds and runner

4. **Sensitivity Objective Function** (`src/core/calibration/sensitivity_objective.py`)
   - Custom objective function for intrinsic fire behavior analysis
   - Measures burned area, spread rate, persistence, and spatial dispersion
   - No external target data required

### ✅ **Validation Tests Passed**
- Parameter bounds loading: ✅ 13 parameters loaded successfully
- Parameter validation: ✅ All parameters have valid bounds and types
- Import tests: ✅ No import errors
- Objective function: ✅ Correctly measures fire behavior metrics
- Parallel processing: ✅ Consistent results across workers

## Expected Performance and Efficiency

### **Comprehensive Analysis Scope**
- **Current**: 13 parameters × 9 evaluations = 117 simulations
- **Parallel Workers**: 28 (HPC optimized)
- **Estimated Runtime**: 2-4 hours (depending on grid size and optimization level)
- **Memory Usage**: Up to 28GB (HPC configured)

### **Analysis Coverage**
- **Complete fire behavior**: All core mechanisms analyzed
- **Terrain interactions**: Slope, barranco, and terrain strength effects
- **Wind dynamics**: Speed, direction, and influence on spread
- **Ember generation**: Probability, ignition, distance, and height factors
- **Fuel dynamics**: Consumption rates and effects

### **Calibration Strategy Options**
- **Quick Analysis**: 7 parameters (Group 1) × 9 points = 63 evaluations (1-2 hours)
- **Full Analysis**: 13 parameters × 9 points = 117 evaluations (2-4 hours)
- **Extended Analysis**: 13 parameters × additional test points (4-8 hours)

## Rationale for Current Parameter Set

### **Why These 13 Parameters?**

**Core Fire Mechanisms (5 parameters):**
1. **`spread_probability`**: Base fire spread probability - fundamental fire behavior
2. **`fuel_consumption_rate`**: Fuel depletion rate - controls fire intensity and duration
3. **`wind_speed`**: Environmental wind speed - major driver of fire behavior
4. **`wind_influence_on_spread`**: Wind effect modifier - controls wind impact
5. **`ember_probability`**: Ember generation rate - enables long-range fire spread

**Terrain and Environmental Effects (4 parameters):**
6. **`terrain_effect_strength`**: Overall terrain influence - modulates topographic effects
7. **`slope_influence`**: Slope impact on fire spread - critical for mountainous terrain
8. **`barranco_amplification`**: Wind amplification in ravines - terrain-wind interaction
9. **`barranco_direction_weight`**: Wind alignment in channels - directional effects

**Ember Dynamics (3 parameters):**
10. **`ember_ignition`**: Ember ignition success rate - spot fire initiation
11. **`ember_distance`**: Maximum ember travel distance - long-range spread
12. **`ember_height_factor`**: Vertical ember generation - height-dependent processes

**Environmental Variability (1 parameter):**
13. **`wind_direction`**: Wind direction - directional fire spread patterns

## Technical Implementation Status

### ✅ **Critical Fixes Completed**
1. **Sequential/Parallel Consistency**: Fixed function signature mismatches
2. **Objective Function**: Implemented sensitivity-specific metrics (no target data)
3. **Performance Optimization**: Eliminated unnecessary target data processing
4. **Mathematical Robustness**: Using median-based sensitivity index calculations
5. **HPC Configuration**: Optimized for 28-worker parallel execution

### ✅ **Framework Validation**
- **Import Tests**: All modules import correctly
- **Parameter Consistency**: All 13 parameters defined consistently across files
- **Bounds Validation**: All parameters have valid, literature-based ranges
- **Objective Function**: Measures intrinsic fire behavior without external dependencies
- **Parallel Processing**: Consistent objective function configuration across workers

## Recommendations for Next Steps

### **Immediate Actions (Production Ready)**
1. **Run comprehensive sensitivity analysis** with full 13-parameter set
2. **Monitor performance**: Expect 2-4 hour runtime on HPC system
3. **Validate results**: Ensure meaningful sensitivity indices across all parameters
4. **Consider quick mode**: Use 7-parameter subset for faster initial analysis
### **Future Enhancements**
1. **Advanced Analysis Methods**:
   - Implement global sensitivity analysis (Sobol indices) for parameter interactions
   - Add variance-based sensitivity analysis for more robust rankings
   - Include uncertainty quantification for parameter bounds

2. **Expanded Objective Functions**:
   - Add fire intensity distribution metrics
   - Include spatial pattern analysis (fire shape, connectivity)
   - Incorporate temporal fire progression metrics

3. **Methodological Improvements**:
   - Parameter interaction analysis (two-way sensitivity)
   - Multi-objective sensitivity analysis
   - Adaptive parameter sampling for efficient exploration

## Risk Assessment

### **Low Risk ✅**
- **Parameter Consistency**: All 13 parameters defined consistently across all files
- **Implementation Robustness**: Comprehensive error handling and validation
- **Computational Efficiency**: Optimized parallel processing for HPC environment
- **Mathematical Soundness**: Robust median-based sensitivity calculations

### **Medium Risk ⚠️**  
- **Runtime Management**: 2-4 hour analysis requires proper scheduling and monitoring
- **Resource Usage**: High memory usage (28GB) needs system resource planning
- **Result Interpretation**: Large parameter set requires careful analysis of results

### **High Risk ❌**
- **None Identified**: Framework is technically sound and production-ready

## Conclusion

The sensitivity analysis framework implements **comprehensive parameter coverage** with **13 calibration parameters** providing thorough analysis of all fire simulation mechanisms. Key achievements:

- **✅ Technical Excellence**: All critical implementation issues resolved
- **✅ Comprehensive Coverage**: Fire spread, fuel dynamics, wind effects, terrain interactions, and ember generation
- **✅ HPC Optimization**: 28-worker parallel processing with robust error handling  
- **✅ Mathematical Rigor**: Proper sensitivity index calculations and objective functions
- **✅ Production Ready**: Validated implementation ready for immediate deployment

The framework provides **industry-standard sensitivity analysis** capabilities and should deliver **meaningful, actionable insights** for forest fire simulation parameter understanding and calibration.

**Next recommended action**: Execute the comprehensive 13-parameter sensitivity analysis on HPC system to obtain complete parameter rankings across all fire behavior mechanisms. 