# 🎯 Complete Calibration Workflow Guide

This guide explains the complete calibration workflow that integrates terrain resampling with the fire simulation calibration system.

## 📋 Overview

The calibration workflow consists of three main phases:

1. **🏔️ Terrain Resampling**: Subset and resample terrain data for faster calibration
2. **🔍 Validation**: Verify that the resampled terrain is suitable for calibration
3. **🎯 Calibration**: Run the actual parameter optimization

## 🚀 Quick Start

### Option 1: Automated Workflow (Recommended)
```bash
# Run the complete workflow automatically
python run_complete_calibration_workflow.py

# Or run with options
python run_complete_calibration_workflow.py --dry-run  # See what would be done
python run_complete_calibration_workflow.py --validate-only  # Only validate, skip calibration
```

### Option 2: Step-by-Step
```bash
# Step 1: Resample terrain
python preprocessed_resampling.py

# Step 2: Validate terrain
python validate_calibration_terrain.py

# Step 3: Run calibration
python scripts/run_tenerife_calibration_custom.py
```

## 📁 File Structure

```
├── preprocessed_resampling.py          # Terrain resampling script
├── validate_calibration_terrain.py     # Terrain validation script
├── run_complete_calibration_workflow.py # Automated workflow
├── test_calibration_workflow.py        # Component testing
├── preprocessed_terrain/               # Original 5m terrain data
│   ├── elevation.npy
│   ├── slope.npy
│   ├── aspect.npy
│   └── metadata.json
├── calibration_terrain/                # Resampled 20m terrain data (created)
│   ├── elevation.npy
│   ├── slope.npy
│   ├── aspect.npy
│   └── metadata.json
└── EMSR Delineations/                  # Fire perimeter data
    ├── Day 1 (18_08_23)/
    ├── Day 2 (21_08_23)/
    ├── Day 3 (24_08_23)/
    └── Day 4 (26_08_23)/
```

## 🔧 Detailed Workflow

### Phase 1: Terrain Resampling (`preprocessed_resampling.py`)

**Purpose**: Create a smaller, faster terrain dataset for calibration

**Process**:
1. **Fire Area Detection**: Automatically finds Day 4 EMSR fire perimeter data
2. **Coordinate Conversion**: Converts from WGS84 to UTM (EPSG:25828)
3. **Subsetting**: Extracts terrain area around fire with 10% buffer
4. **Resampling**: Reduces resolution from 5m to 20m (4x reduction)
5. **Validation**: Checks coordinate systems and grid bounds

**Output**: `calibration_terrain/` directory with resampled terrain files

**Performance Impact**:
- **Memory**: ~99.9% reduction (from 15,121×24,741 to ~609×609 cells)
- **Speed**: ~16x faster simulations
- **Storage**: ~16x smaller files

### Phase 2: Validation (`validate_calibration_terrain.py`)

**Purpose**: Ensure the resampled terrain is suitable for calibration

**Checks**:
- ✅ File integrity and completeness
- ✅ Metadata validation
- ✅ Resolution verification (20m)
- ✅ Grid size suitability
- ✅ Data quality (NaN, infinite values)
- ✅ Coordinate system alignment
- ✅ Memory usage estimation
- ✅ Calibration framework compatibility

**Output**: Detailed validation report with warnings and recommendations

### Phase 3: Calibration (`run_tenerife_calibration_custom.py`)

**Purpose**: Optimize fire simulation parameters against observed data

**Configuration**:
- **Resolution**: 20m (resampled terrain)
- **Grid Size**: Dynamic based on fire area
- **Parameters**: 4 key parameters (spread_probability, fuel_consumption_rate, ignition_threshold, ember_probability)
- **Grid Search**: 3 points per parameter (81 total combinations)
- **Optimizations**: Sparse storage, tiling, parallel processing

**Output**: Calibration results with best parameters and objective values

## 🧪 Testing

### Test Individual Components
```bash
# Test all workflow components
python test_calibration_workflow.py
```

### Test Specific Components
```python
# Test terrain resampling
from preprocessed_resampling import get_fire_area_bounds
fire_bounds = get_fire_area_bounds()
print(f"Fire area: {fire_bounds}")

# Test validation
from validate_calibration_terrain import validate_calibration_terrain
is_valid = validate_calibration_terrain()
print(f"Terrain valid: {is_valid}")
```

## ⚙️ Configuration Options

### Terrain Resampling Options
```python
# In preprocessed_resampling.py
buffer_factor = 1.1        # 10% buffer around fire area
target_resolution = 20.0   # Target resolution in meters
zoom_factor = 0.25         # 5m → 20m (4x reduction)
```

### Calibration Options
```python
# In scripts/run_tenerife_calibration_custom.py
OPTIMIZED_CONFIG = {
    'model_resolution': 20.0,
    'max_steps': 100,
    'grid_search_points': 3,
    'parameters': ['spread_probability', 'fuel_consumption_rate', 'ignition_threshold', 'ember_probability'],
    'use_calibration_terrain': True,
    'calibration_terrain_dir': 'calibration_terrain'
}
```

## 📊 Performance Estimates

### Memory Usage
- **Original Terrain**: ~75GB (15,121×24,741×25 cells)
- **Resampled Terrain**: ~4.7GB (609×609×25 cells)
- **Per Simulation**: ~50MB (with optimizations)

### Time Estimates
- **Terrain Resampling**: ~5-10 minutes
- **Validation**: ~1-2 minutes
- **Calibration**: ~2-3 hours (81 combinations, 32 workers)

### Storage Requirements
- **Original Terrain**: ~75GB
- **Resampled Terrain**: ~4.7GB
- **Calibration Results**: ~1-2GB

## 🚨 Troubleshooting

### Common Issues

#### 1. "Fire area is very small" Warning
**Cause**: The fire area from EMSR data is too small for meaningful calibration
**Solution**: 
```python
# Increase buffer factor in preprocessed_resampling.py
buffer_factor = 2.0  # 100% buffer instead of 10%
```

#### 2. "Grid coordinates out of bounds" Error
**Cause**: Fire area extends outside terrain bounds
**Solution**: Check coordinate system alignment and fire area location

#### 3. "Missing required files" Error
**Cause**: Terrain files not found
**Solution**: Run terrain preprocessing first:
```bash
python scripts/preprocess_terrain.py
```

#### 4. "Import error" Issues
**Cause**: Missing Python dependencies
**Solution**: Install required packages:
```bash
pip install numpy geopandas scipy rasterio
```

### Validation Failures

#### Terrain Validation Fails
1. Check that `calibration_terrain/` directory exists
2. Verify all required files are present
3. Check file sizes (should be ~1-10MB each)
4. Review validation output for specific issues

#### Calibration Integration Fails
1. Check Python path includes project root
2. Verify calibration framework is properly installed
3. Test with smaller grid sizes first
4. Check memory availability

## 🎯 Best Practices

### 1. Always Validate First
```bash
# Run validation before calibration
python validate_calibration_terrain.py
```

### 2. Use Dry Run Mode
```bash
# See what would be done without running
python run_complete_calibration_workflow.py --dry-run
```

### 3. Monitor Resources
- Check available memory before running
- Monitor CPU usage during calibration
- Ensure sufficient disk space

### 4. Start Small
```bash
# Test with validation only first
python run_complete_calibration_workflow.py --validate-only
```

### 5. Backup Results
```bash
# Backup calibration terrain
cp -r calibration_terrain calibration_terrain_backup
```

## 📈 Expected Results

### Successful Calibration Output
```
✅ CALIBRATION COMPLETED SUCCESSFULLY!
📊 Best objective value: 0.8234
🎯 Best parameters:
   - spread_probability: 0.65
   - fuel_consumption_rate: 0.45
   - ignition_threshold: 0.12
   - ember_probability: 0.35
📁 Results saved to: calibration_results/
```

### Performance Metrics
- **Memory Reduction**: 99.9% (75GB → 4.7GB)
- **Speed Improvement**: 16x faster
- **Accuracy**: Maintained within acceptable bounds
- **Calibration Quality**: Comparable to full-resolution runs

## 🔄 Workflow Integration

### With HPC Systems
```bash
# Update HPC configuration
python hpc_deployment/run_hpc_calibration.py
```

### With Existing Scripts
```python
# Use in custom scripts
from preprocessed_resampling import preprocess_terrain_for_calibration
from validate_calibration_terrain import validate_calibration_terrain

# Resample terrain
success = preprocess_terrain_for_calibration()

# Validate terrain
if success:
    is_valid = validate_calibration_terrain()
```

## 📞 Support

If you encounter issues:

1. **Check the troubleshooting section above**
2. **Run the test script**: `python test_calibration_workflow.py`
3. **Review validation output** for specific error messages
4. **Check system resources** (memory, disk space, CPU)
5. **Verify file paths** and coordinate systems

## 🎉 Success Criteria

Your calibration workflow is working correctly when:

- ✅ Terrain resampling completes without errors
- ✅ Validation passes all checks
- ✅ Calibration runs successfully
- ✅ Results show reasonable parameter values
- ✅ Performance meets expectations (memory, speed)

---

**Author**: Forest Fire Simulation Team  
**Date**: 2025  
**Version**: 1.0
