# Scripts Directory

This directory contains executable workflow scripts for running the fire simulation system.

## Structure

### preprocessing/
Data preprocessing scripts:
- `preprocess_lidar.py` - LiDAR data preprocessing pipeline
- `preprocess_terrain.py` - Terrain data preprocessing
- `verify_preprocessed_lidar.py` - Verify LiDAR preprocessing outputs
- Terrain preprocessing utilities

### calibration/
Model calibration scripts:
- `run_tenerife_calibration_clean.py` - Main calibration script for Tenerife case study

### validation/
Model validation scripts:
- `run_tenerife_validation_optimized.py` - Optimized validation script
- `validate_fine_resolution.py` - Fine resolution validation

### hpc/
HPC deployment scripts for Snellius cluster:
- `run_hpc_calibration.py` - HPC calibration execution
- `run_production_sim.py` - Production simulation runner
- `submit_job.sh` - Job submission script
- `submit_sensitivity_analysis.slurm` - Sensitivity analysis SLURM script
- `tenerife_production.slurm` - Tenerife production SLURM script
- `validate_hpc_setup.py` - Validate HPC environment
- `OUTPUT_PATH_CONFIGURATION.md` - HPC path configuration guide

### analysis/
Analysis and visualization scripts:
- `run_sensitivity_analysis.py` - Sensitivity analysis execution
- `comprehensive_validation_analysis.py` - Comprehensive validation analysis
- `run_visualization.py` - Visualization runner
- `visualize_terrain_data.py` - Terrain data visualization

## Workflow

### 1. Preprocessing
```bash
python scripts/preprocessing/preprocess_lidar.py
python scripts/preprocessing/preprocess_terrain.py
```

### 2. Calibration
```bash
python scripts/calibration/run_tenerife_calibration_clean.py
```

### 3. Validation
```bash
python scripts/validation/run_tenerife_validation_optimized.py
```

### 4. Analysis
```bash
python scripts/analysis/run_sensitivity_analysis.py
python scripts/analysis/comprehensive_validation_analysis.py
```

## HPC Usage

For HPC deployment on Snellius:
```bash
sbatch scripts/hpc/tenerife_production.slurm
sbatch scripts/hpc/submit_sensitivity_analysis.slurm
```

See `scripts/hpc/OUTPUT_PATH_CONFIGURATION.md` for configuration details.


