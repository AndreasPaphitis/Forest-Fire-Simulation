# Forest Fire Simulation

A comprehensive 3D forest fire simulation framework using cellular automata and LiDAR data integration, with specialized calibration for Tenerife fire perimeter analysis.

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Tenerife Fire Calibration](#tenerife-fire-calibration)
- [Configuration Management for HPC](#configuration-management-for-hpc)
- [Usage](#usage)
- [Documentation](#documentation)

## Overview

This project implements a sophisticated forest fire simulation system that combines:
- 3D cellular automata fire spread modeling
- LiDAR data integration for realistic vegetation structure
- Memory-optimized processing for large-scale simulations
- HPC-compatible configuration management
- Comprehensive visualization capabilities
- **Specialized Tenerife fire perimeter calibration** using EMSR delineation data

## Installation

[Installation instructions remain the same...]

## Quick Start

[Quick start instructions remain the same...]

## Tenerife Fire Calibration

The framework includes a specialized calibration system for the Tenerife fire using EMSR delineation data:

### 🎯 **Day 4 Fire Area Calibration**

**Grid Configuration**:
- **Dynamic sizing**: Based on Day 4 fire perimeter + 10% buffer + 10% northern expansion
- **Typical size**: ~500 × 500 × 25 cells = **6.25M cells**
- **Resolution**: 5m per cell
- **Area**: ~6.25 km² (focused on fire-affected region)
- **Performance**: 99.93% smaller than full Tenerife domain

### ⏱️ **Accurate Time Estimates**

**With 45 workers**:
- **Per simulation**: 3.0 minutes
- **Total combinations**: 243 (3^5 parameters)
- **Expected completion**: 20-30 minutes
- **Memory usage**: ~65 GB

### 🚀 **Quick Start Commands**

```bash
# Optimal configuration (50GB system)
python scripts/run_tenerife_calibration.py --memory 50 --workers 45

# High performance (64GB system)
python scripts/run_tenerife_calibration.py --memory 64 --workers 60

# Conservative approach
python scripts/run_tenerife_calibration.py --memory 50 --workers 32

# Dry run to validate setup
python scripts/run_tenerife_calibration.py --memory 50 --workers 45 --dry-run
```

### 📊 **Key Advantages**

- **99.93% fewer cells** than full Tenerife domain
- **20-30 minute completion** vs weeks for full domain
- **Manageable memory requirements** (50GB vs 500GB+)
- **Focused calibration** on actual fire-affected region
- **Real fire perimeter data** from EMSR delineations

For detailed calibration documentation, see [docs/TENERIFE_CALIBRATION_GUIDE.md](docs/TENERIFE_CALIBRATION_GUIDE.md).

## Configuration Management for HPC

The simulation framework includes powerful configuration management tools specifically designed for High-Performance Computing (HPC) environments. These tools allow you to easily generate, modify, and deploy multiple simulation configurations without modifying code.

### Basic Configuration Export

Export the default configuration to a JSON file:

```bash
# Export default configuration
python src/config/config_tools.py export --output my_config.json

# Export with custom parameters
python src/config/config_tools.py export \
    --output custom_config.json \
    --resolution 2.0 \
    --layers 15 \
    --wind-speed 10 \
    --wind-direction 90 \
    --max-steps 500 \
    --memory-optimization 2 \
    --use-tiling \
    --tile-size 150
```

### Batch Configuration Generation for Parameter Sweeps

Generate multiple configuration files for parameter sensitivity analysis:

```bash
# Generate configurations for wind speed and direction sweep
python src/config/config_tools.py batch \
    --output-dir ./hpc_configs \
    --wind-speeds "5,10,15,20" \
    --wind-directions "0,45,90,135,180,225,270,315" \
    --prefix "wind_study_"

# Generate configurations for resolution and memory optimization study
python src/config/config_tools.py batch \
    --output-dir ./resolution_study \
    --resolutions "1.0,2.0,5.0,10.0" \
    --memory-levels "0,1,2" \
    --max-steps-list "200,500,1000" \
    --prefix "res_mem_"

# Use existing config as base for modifications
python src/config/config_tools.py batch \
    --base-config my_custom_config.json \
    --output-dir ./parameter_sweep \
    --spread-probs "0.2,0.25,0.3,0.35,0.4" \
    --wind-speeds "5,10,15"
```

### HPC Job Script Generation

Automatically generate SLURM job scripts for all your configurations:

```bash
# Generate job scripts for all configurations in a directory
python src/config/config_tools.py hpc \
    --config-dir ./hpc_configs \
    --output-dir ./hpc_jobs \
    --time-limit "04:00:00" \
    --memory "16G" \
    --partition "compute"

# Use custom job template
python src/config/config_tools.py hpc \
    --config-dir ./hpc_configs \
    --output-dir ./hpc_jobs \
    --job-template my_slurm_template.sh \
```

### Complete HPC Workflow Example

Here's a complete workflow for running parameter sweeps on HPC:

```bash
# 1. Generate base configuration
python src/config/config_tools.py export \
    --output base_config.json \
    --resolution 5.0 \
    --layers 10 \
    --memory-optimization 2 \
    --use-tiling

# 2. Generate parameter sweep configurations
python src/config/config_tools.py batch \
    --base-config base_config.json \
    --output-dir ./sweep_configs \
    --wind-speeds "5,10,15,20,25" \
    --wind-directions "0,90,180,270" \
    --spread-probs "0.25,0.3,0.35" \
    --prefix "sweep_"

# 3. Generate HPC job scripts
python src/config/config_tools.py hpc \
    --config-dir ./sweep_configs \
    --output-dir ./hpc_jobs \
    --time-limit "02:00:00" \
    --memory "8G" \
    --partition "compute" \
    --python-script "src/core/run_fire_simulation.py"

# 4. Submit all jobs to SLURM
cd hpc_jobs
./submit_all.sh

# 5. Monitor job progress
squeue -u $USER

# 6. Collect results when jobs complete
# Results will be in separate directories for each configuration
```

### Running Individual Simulations with Configuration Files

Once you have configuration files, run simulations directly:

```bash
# Run simulation with a specific configuration
python src/core/run_fire_simulation.py --config my_config.json

# Run with custom output directory
python src/core/run_fire_simulation.py \
    --config my_config.json \
    --output /path/to/results

# Validate configuration without running
python src/core/run_fire_simulation.py \
    --config my_config.json \
    --validate-only

# Run without generating visualizations (faster for large sweeps)
python src/core/run_fire_simulation.py \
    --config my_config.json \
    --no-viz
```

### Configuration File Structure

Configuration files are JSON format with all simulation parameters:

```json
{
  "model_resolution": 5.0,
  "grid_size": [1000, 1000],
  "num_layers": 10,
  "layer_height": 2.0,
  "spread_probability": 0.3,
  "vertical_spread": 0.2,
  "wind_speed": 10.0,
  "wind_direction": 90.0,
  "max_steps": 500,
  "memory_optimization_level": 2,
  "use_tiling": true,
  "tile_size": 200,
  "save_visualizations": true,
  "output_dir": "results",
  ...
}
```

### Advanced Configuration Management

```bash
# Optimize configuration for specific area and memory constraints
python src/config/config_tools.py optimize \
    --input my_config.json \
    --output optimized_config.json \
    --width 5000 \
    --height 5000 \
    --memory 4000

# Validate any configuration file
python src/config/config_tools.py validate --input my_config.json

# Get help for any command
python src/config/config_tools.py export --help
python src/config/config_tools.py batch --help
python src/config/config_tools.py hpc --help
```

This approach provides several advantages for HPC workflows:

1. **Version Control**: Configuration files can be version controlled separately from code
2. **Reproducibility**: Exact simulation parameters are preserved in JSON files
3. **Scalability**: Easy to generate hundreds of configurations for large parameter sweeps
4. **Flexibility**: No need to modify and recompile code for different simulations
5. **Automation**: Automatic generation of job scripts reduces manual setup time
6. **Standardization**: Consistent configuration format across all simulations

## Usage

[Rest of usage documentation...]

## Documentation

[Documentation section...] 