# HPC-Optimized Sensitivity Analysis Guide

## Overview

This guide explains how to run the forest fire simulation sensitivity analysis on HPC systems with **32 CPU cores and 32 GB RAM**. The HPC-optimized version provides massive performance improvements over the standard implementation.

## Performance Comparison

| Configuration | Cores | Memory | Analysis Time | Speedup |
|---------------|-------|--------|---------------|---------|
| Sequential    | 1     | 4 GB   | ~5.6 hours    | 1x      |
| Standard      | 16    | 16 GB  | ~25 minutes   | 13x     |
| **HPC Mode**  | **28**| **28 GB** | **~20 minutes** | **17x** |
| **Production Scale** | **28** | **28 GB** | **~45 minutes** | **7x** |

*Analysis time for 117 evaluations (13 parameters × 9 test points)*

## Quick Start (HPC)

### Option 1: SLURM Job Submission (Recommended)

```bash
# Submit the pre-configured SLURM job
sbatch hpc_deployment/submit_sensitivity_analysis.slurm

# Monitor job status
squeue -u $USER
watch squeue -u $USER

# Check results when complete
ls hpc_sensitivity_results_*/
```

### Option 2: Interactive Session

```bash
# Request interactive node
salloc --ntasks=1 --cpus-per-task=32 --mem=32G --time=2:00:00

# Run analysis with full HPC optimization
python sensitivity_analysis_runner.py --hpc-mode

# For production-scale analysis (larger grids)
python sensitivity_analysis_runner.py --production-scale --hpc-mode
```

## HPC Modes Explained

### 1. Standard Mode (Default)
```bash
python sensitivity_analysis_runner.py
```
- **Workers**: 16 (conservative)
- **Memory**: 24 GB limit
- **Grid**: 100×100×6
- **Time**: ~35 minutes
- **Use case**: Testing, shared nodes

### 2. HPC Mode (Recommended)
```bash
python sensitivity_analysis_runner.py --hpc-mode
```
- **Workers**: 28 (leaves 4 cores for system)
- **Memory**: 28 GB limit  
- **Grid**: 120×120×8
- **Time**: ~20 minutes
- **Use case**: Dedicated 32-core node

### 3. Production Scale
```bash
python sensitivity_analysis_runner.py --production-scale --hpc-mode
```
- **Workers**: 28
- **Memory**: 28 GB limit
- **Grid**: 200×200×10 
- **Time**: ~45 minutes
- **Use case**: High-resolution analysis

## Command Line Options

### Core HPC Options
```bash
--hpc-mode                    # Enable full HPC optimization
--production-scale            # Very large grids (200×200×10)
--workers N                   # Custom worker count (default: auto)
--memory-level {1,2,3}        # Memory optimization (default: 3)
```

### Analysis Options
```bash
--quick                       # Analyze only top 7 parameters
--config FILE                 # Use production config file
--output DIR                  # Custom output directory
--name EXPERIMENT             # Custom experiment name
```

### Data Options
```bash
--dem-file PATH               # Custom DEM file path
--lidar-dir PATH              # Custom LiDAR data directory
--force-synthetic             # Force synthetic data (testing)
```

## Example Commands

### Basic HPC Analysis
```bash
# Full HPC optimization with auto-detection
python sensitivity_analysis_runner.py --hpc-mode

# Custom output location
python sensitivity_analysis_runner.py --hpc-mode \
    --output "tenerife_sensitivity_$(date +%Y%m%d)" \
    --name "tenerife_hpc_analysis"
```

### Production Analysis with Real Data
```bash
# Using your production configuration
python sensitivity_analysis_runner.py --hpc-mode \
    --config "hpc_deployment/Forest_Fire_Simulation_production_test.json" \
    --dem-file "/path/to/Merged_DTM.tif" \
    --lidar-dir "/path/to/PAD_Results/" \
    --output "production_sensitivity_results"
```

### Quick Parameter Screening
```bash
# Analyze only top 7 critical parameters (faster)
python sensitivity_analysis_runner.py --hpc-mode --quick
```

### Conservative Mode for Shared Nodes
```bash
# Use fewer resources if node is shared
python sensitivity_analysis_runner.py \
    --workers 16 \
    --memory-level 2
```

## SLURM Configuration

### Basic SLURM Script

```bash
#!/bin/bash
#SBATCH --job-name=fire_sensitivity
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=sensitivity_%j.out
#SBATCH --error=sensitivity_%j.err

# Load modules (adjust for your system)
module load Python/3.9.6-GCCcore-11.2.0
module load GDAL/3.3.2-foss-2021b

# Run analysis
cd Forest-Fire-Simulation
python sensitivity_analysis_runner.py --hpc-mode
```

### Advanced SLURM Script with Array Jobs

```bash
#!/bin/bash
#SBATCH --job-name=fire_sensitivity_array
#SBATCH --array=1-3
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --time=02:00:00

# Define different configurations for array jobs
case $SLURM_ARRAY_TASK_ID in
    1) MODE="--hpc-mode" ;;
    2) MODE="--production-scale --hpc-mode" ;;
    3) MODE="--quick --hpc-mode" ;;
esac

cd Forest-Fire-Simulation
python sensitivity_analysis_runner.py $MODE --name "array_job_${SLURM_ARRAY_TASK_ID}"
```

## Resource Optimization

### CPU Allocation Strategy

| Cores | Workers | System Reserve | Efficiency |
|-------|---------|----------------|------------|
| 32    | 28      | 4 cores        | 95%        |
| 32    | 24      | 8 cores        | 88%        |
| 32    | 16      | 16 cores       | 75%        |

**Recommended**: 28 workers (leaves 4 cores for system overhead)

### Memory Usage Patterns

| Grid Size | Layers | Peak Memory | Memory/Core |
|-----------|--------|-------------|-------------|
| 100×100×6 | 6      | ~12 GB      | ~430 MB     |
| 120×120×8 | 8      | ~18 GB      | ~640 MB     |
| 200×200×10| 10     | ~28 GB      | ~1000 MB    |

### Performance Tuning

#### For Maximum Speed
```bash
python sensitivity_analysis_runner.py \
    --hpc-mode \
    --workers 28 \
    --memory-level 3
```

#### For Memory Efficiency
```bash
python sensitivity_analysis_runner.py \
    --workers 24 \
    --memory-level 3
```

#### For Shared Nodes
```bash
python sensitivity_analysis_runner.py \
    --workers 16 \
    --memory-level 2
```

## Monitoring and Debugging

### Check Job Status
```bash
# Monitor SLURM job
squeue -u $USER
sacct -j JOBID --format=JobID,JobName,State,Elapsed,MaxRSS

# Monitor real-time resource usage
ssh node_name
htop
```

### Common Performance Issues

#### Issue: Low CPU Utilization
```bash
# Solution: Increase workers
python sensitivity_analysis_runner.py --workers 28
```

#### Issue: Memory Exhaustion
```bash
# Solution: Reduce workers or memory level
python sensitivity_analysis_runner.py --workers 24 --memory-level 2
```

#### Issue: Slow Analysis
```bash
# Solution: Enable HPC mode and check system
python sensitivity_analysis_runner.py --hpc-mode
htop  # Check for other processes
```

## Output Analysis

### Expected Output Structure
```
hpc_sensitivity_results_20250101_120000/
├── sensitivity_results.json           # Complete results
├── sensitivity_summary.txt           # Human-readable summary
├── calibration_recommendations.md    # Next steps guide
├── parameter_rankings.csv           # Parameter importance ranking
└── analysis_metadata.json          # Technical details
```

### Key Metrics to Check

1. **Parameter Rankings**: Which parameters are most sensitive?
2. **Analysis Time**: Did HPC optimization work?
3. **Memory Usage**: Was system memory sufficient?
4. **Worker Efficiency**: Were all cores utilized?

### Performance Validation

```bash
# Check if HPC mode was actually used
grep "HPC MODE" hpc_sensitivity_results_*/analysis_metadata.json

# Verify worker count
grep "max_workers" hpc_sensitivity_results_*/analysis_metadata.json

# Check analysis time
grep "total_time" hpc_sensitivity_results_*/analysis_metadata.json
```

## Next Steps After Analysis

### 1. Review Results
```bash
# Read the recommendations
cat hpc_sensitivity_results_*/calibration_recommendations.md

# Check parameter rankings
head -10 hpc_sensitivity_results_*/parameter_rankings.csv
```

### 2. Run Focused Calibration
Use the sensitivity results to run focused grid search calibration:

```bash
# Use top 5 parameters for calibration
python run_calibration.py \
    --method grid_search \
    --parameters spread_probability,fuel_consumption_rate,ignition_threshold,min_fuel_value,max_fuel_value \
    --grid-points 7 \
    --hpc-mode
```

### 3. Validate Results
Test the calibrated parameters on independent fire data.

## Troubleshooting

### Common SLURM Issues

#### Job Won't Start
```bash
# Check queue status
sinfo
squeue

# Check resource availability
sinfo -N -l
```

#### Out of Memory Errors
```bash
# Reduce memory requirements
python sensitivity_analysis_runner.py --workers 20 --memory-level 2
```

#### Python Module Errors
```bash
# Load required modules
module load Python/3.9.6-GCCcore-11.2.0
module load GDAL/3.3.2-foss-2021b

# Check Python path
which python
python -c "import src.core.calibration; print('OK')"
```

### Performance Issues

#### Slower Than Expected
1. Check if other jobs are running on the node
2. Verify all cores are being used: `htop`
3. Check memory usage isn't maxed out
4. Ensure HPC mode is actually enabled

#### Memory Errors
1. Reduce worker count: `--workers 20`
2. Lower memory optimization: `--memory-level 2`
3. Use smaller grids: avoid `--production-scale`

## Best Practices

### 1. Always Use HPC Mode on 32-Core Systems
```bash
python sensitivity_analysis_runner.py --hpc-mode
```

### 2. Monitor Resource Usage
```bash
# In another terminal during analysis
watch -n 5 'ps aux | grep python'
watch -n 5 'free -h'
```

### 3. Use Appropriate Queue/Partition
```bash
#SBATCH --partition=compute     # For compute-intensive tasks
#SBATCH --qos=normal           # Standard priority
```

### 4. Plan for Data Transfer
Large result files may need special handling:
```bash
# Compress results for transfer
tar -czf sensitivity_results.tar.gz hpc_sensitivity_results_*/
```

### 5. Save Configurations
Keep track of successful configurations:
```bash
# Save working command for future use
echo "python sensitivity_analysis_runner.py --hpc-mode --workers 28" > run_sensitivity.sh
chmod +x run_sensitivity.sh
```

## Expected Performance on Your 32-Core System

### Standard Analysis (117 evaluations)
- **Sequential**: 5.6 hours
- **HPC Optimized**: ~20 minutes  
- **Speedup**: ~17x

### Production Scale (117 evaluations, large grids)
- **Sequential**: ~12 hours
- **HPC Optimized**: ~45 minutes
- **Speedup**: ~16x

### Extended Analysis (1,350 evaluations)
- **Sequential**: ~56 hours
- **HPC Optimized**: ~3.5 hours
- **Speedup**: ~16x

This represents a massive improvement in analysis capability, allowing you to run comprehensive sensitivity analyses that would otherwise be impractical. 