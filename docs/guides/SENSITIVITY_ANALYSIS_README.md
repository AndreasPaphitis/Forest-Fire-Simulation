# Grid-Based Sensitivity Analysis Runner

This directory contains a ready-to-run sensitivity analysis tool for the forest fire simulation model. The analysis uses a **grid-based approach with 10% perturbations** across the full parameter range to identify which parameters have the most impact on fire behavior.

## What This Analysis Does

The sensitivity analysis:
- **Tests all 13 calibration parameters** systematically
- **Uses 10% increments** (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9) across each parameter's valid range
- **Requires NO baseline values** - samples across the entire parameter space
- **Ranks parameters by sensitivity** to guide efficient calibration
- **Generates comprehensive reports** with calibration recommendations

## Quick Start

### Option 1: Simple Run (Default Settings)
```bash
cd Forest-Fire-Simulation
python run_sensitivity_analysis.py
```

### Option 2: With Your Production Configuration
```bash
cd Forest-Fire-Simulation
python run_sensitivity_analysis.py --config hpc_deployment/Forest_Fire_Simulation_production_test.json
```

### Option 3: Custom Output Directory
```bash
cd Forest-Fire-Simulation
python run_sensitivity_analysis.py --output my_sensitivity_results
```

### Option 4: Quick Analysis (Fewer Parameters)
```bash
cd Forest-Fire-Simulation
python run_sensitivity_analysis.py --quick
```

## Expected Runtime

- **Total simulations**: 13 parameters × 9 perturbations = **117 simulations**
- **Estimated time**: 10-20 minutes (depends on your hardware)
- **Memory usage**: Moderate (optimized for speed over memory)
- **Parallel execution**: Yes (4 workers by default)

## What You'll Get

### 1. Parameter Rankings
The analysis will rank all 13 parameters by sensitivity, showing which ones matter most:

```
Rank | Parameter                 | Sensitivity | Recommendation
-----|---------------------------|-------------|---------------
   1 | spread_probability        |     0.1234  | CALIBRATE FIRST
   2 | fuel_consumption_rate     |     0.0987  | CALIBRATE FIRST
   3 | ignition_threshold        |     0.0765  | CALIBRATE FIRST
   ...
```

### 2. Calibration Recommendations
- **Top 3 parameters**: Recommended for focused calibration (1-2 hours)
- **Top 4 parameters**: For comprehensive calibration (2-4 hours) 
- **All 5 parameters**: Complete analysis (computationally efficient)

### 3. Output Files
All results are saved to the output directory:

```
sensitivity_results/
├── grid_sensitivity_YYYYMMDD_HHMMSS_detailed_results.json    # Complete data
├── grid_sensitivity_YYYYMMDD_HHMMSS_summary.json            # Summary statistics  
├── grid_sensitivity_YYYYMMDD_HHMMSS_calibration_recommendations.txt  # Action plan
└── calibration_report_YYYYMMDD_HHMMSS.html                  # Visual report
```

## Understanding the Results

### Sensitivity Index
- **Higher values** = parameter has more impact on fire behavior
- **Lower values** = parameter has minimal impact
- **Scale**: Typically 0.001 to 0.200

### Parameter Tiers
The 5 parameters are organized into sensitivity tiers:

**Tier 1: Critical Parameters** (Expected high sensitivity)
- `spread_probability` - Base fire spread probability
- `fuel_consumption_rate` - Rate of fuel consumption  
- `wind_speed` - Base wind speed affecting fire spread
- `wind_influence_on_spread` - Wind effect on spread probability

**Tier 3: Low Sensitivity**
- `ember_probability` - Ember generation probability

## Using the Results for Calibration

### Step 1: Review Rankings
Look at the parameter sensitivity rankings in the results files.

### Step 2: Choose Strategy
Based on computational resources:

**Focused Calibration (Recommended)**
- Use top 3 most sensitive parameters
- Grid search with 5 points per parameter = 5^3 = 125 combinations
- Estimated time: 1-2 hours

**Comprehensive Calibration**
- Use top 4 most sensitive parameters  
- Grid search with 3 points per parameter = 3^4 = 81 combinations
- Estimated time: 2-4 hours

### Step 3: Run Calibration
Use the identified sensitive parameters in your grid search calibration:

```python
from src.core.calibration import CalibrationConfig, CalibrationMethod

# Use the top 5 parameters from sensitivity analysis
top_params = ['spread_probability', 'fuel_consumption_rate', 'ignition_threshold', ...]

config = CalibrationConfig(
    method=CalibrationMethod.GRID_SEARCH,
    calibration_parameters=top_params,
    grid_search_points=5
)
```

## Command Line Options

```bash
python run_sensitivity_analysis.py [OPTIONS]

Options:
  --config PATH     Path to production configuration JSON file
  --output PATH     Output directory for results (default: sensitivity_results)
  --name NAME       Experiment name (default: auto-generated with timestamp)
  --quick           Quick analysis with top 8 parameters only
  --help           Show help message
```

## Technical Details

### Grid Method Benefits
1. **No baseline required**: Samples across full parameter range
2. **Systematic coverage**: 10% increments ensure even sampling
3. **Robust ranking**: Less sensitive to starting values
4. **Reproducible**: Same results every time

### 10% Perturbation Strategy
- **Parameter range**: [min_value, max_value] from parameter bounds
- **Sample points**: 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9 of range
- **Example**: For spread_probability [0.1, 0.8]:
  - 0.1 = 0.1 + 0.1×(0.8-0.1) = 0.17
  - 0.2 = 0.1 + 0.2×(0.8-0.1) = 0.24
  - ...
  - 0.9 = 0.1 + 0.9×(0.8-0.1) = 0.73

### Sensitivity Calculation
For grid method, sensitivity uses **coefficient of variation**:
- `sensitivity = std(objective_values) / mean(objective_values)`
- Higher variation across parameter range = higher sensitivity

## Integration with Production

### Using Production Configuration
If you have an existing production configuration file:

```bash
python run_sensitivity_analysis.py --config hpc_deployment/Forest_Fire_Simulation_production_test.json
```

This will:
- Use the same geographic bounds, resolution, and data sources
- Apply the same LiDAR and terrain settings
- Maintain consistency with production simulations

### Geographic Configuration
The analysis supports the same geographic features as production:
- **Geographic bounds**: Tenerife coordinates `(273500, 3094350, 323500, 3144350)`
- **CRS**: `"EPSG:25828"` (UTM Zone 28N)
- **Resolution**: 5m per grid cell
- **LiDAR data**: Your existing PAD results directory
- **Terrain data**: Your existing DEM files

## Troubleshooting

### Common Issues

**Error: "Could not import sensitivity analysis runner"**
- Solution: Make sure you're in the `Forest-Fire-Simulation` directory

**Error: "Configuration validation failed"**
- Solution: Check that all required modules are installed and paths are valid

**Error: "All simulations fail"**
- Solution: Test with a smaller grid size or fewer layers in the configuration

**Long runtime**
- Solution: Use `--quick` option for faster analysis with fewer parameters

### Performance Optimization

**For faster analysis:**
- Use smaller grid size (60×60 instead of 100×100)
- Reduce number of layers (3-5 instead of 10+)
- Shorter max_steps (30-40 instead of 50+)
- Disable full state storage

**For comprehensive analysis:**
- Use larger grid size
- More layers for vertical detail
- Longer simulations for complete fire behavior

## Next Steps

1. **Run the analysis**: `python run_sensitivity_analysis.py`
2. **Review results**: Check the calibration recommendations file
3. **Plan calibration**: Choose focused or comprehensive strategy
4. **Set up calibration**: Use identified sensitive parameters
5. **Validate results**: Test optimized parameters on independent data

## Support

For questions about the sensitivity analysis:
1. Check this README
2. Review the output files and error messages
3. Examine the generated calibration recommendations
4. Contact the development team with specific issues

The sensitivity analysis is designed to be **self-contained and robust** - it should run successfully with minimal setup and provide clear guidance for your calibration efforts. 