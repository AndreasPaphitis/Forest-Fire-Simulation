# Forest Fire Simulation - Requirements Guide

This document explains the different requirements files and installation options for the Forest Fire Simulation Framework.

## Overview

The project provides multiple requirements files to support different use cases:

- **`requirements.txt`** - Complete dependencies for full functionality
- **`requirements-minimal.txt`** - Essential dependencies for basic simulation
- **`requirements-dev.txt`** - Development tools and testing frameworks

## Requirements Files

### 📋 `requirements.txt` - Full Installation

**Use this for:** Production deployments, research applications, complete functionality

**Includes:**
- Core scientific computing (NumPy, SciPy)
- Geospatial processing (GDAL, GeoPandas, Rasterio)
- Visualization and animation (Matplotlib, ImageIO)
- System monitoring (psutil)
- Optional performance enhancements (Numba)

```bash
pip install -r requirements.txt
```

### ⚡ `requirements-minimal.txt` - Minimal Installation

**Use this for:** Quick testing, resource-constrained environments, basic functionality

**Includes only essential packages:**
- NumPy, SciPy (scientific computing)
- GDAL (geospatial data)
- scikit-image (image processing)
- Matplotlib (basic visualization)
- psutil (memory monitoring)
- tqdm (progress bars)

```bash
pip install -r requirements-minimal.txt
```

### 🔧 `requirements-dev.txt` - Development Installation

**Use this for:** Contributing to the project, development, testing

**Includes everything from requirements.txt plus:**
- Testing frameworks (pytest, coverage)
- Code quality tools (black, flake8, mypy)
- Documentation tools (Sphinx, Jupyter)
- Advanced debugging and profiling tools
- Build and packaging utilities

```bash
pip install -r requirements-dev.txt
```

## Installation Instructions

### Quick Start (Minimal)

For basic functionality and quick testing:

```bash
# Create virtual environment
python -m venv fire-sim-env
source fire-sim-env/bin/activate  # On Windows: fire-sim-env\Scripts\activate

# Install minimal dependencies
pip install -r requirements-minimal.txt
```

### Recommended Installation (Conda)

For the best experience, especially with GDAL:

```bash
# Create conda environment
conda create -n fire-sim python=3.9
conda activate fire-sim

# Install GDAL through conda (recommended)
conda install -c conda-forge gdal>=3.4.0

# Install remaining dependencies
pip install -r requirements.txt
```

### Development Setup

For contributors and developers:

```bash
# Clone repository
git clone <repository-url>
cd forest-fire-simulation

# Create development environment
conda create -n fire-sim-dev python=3.9
conda activate fire-sim-dev

# Install GDAL
conda install -c conda-forge gdal>=3.4.0

# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install
```

### HPC Installation (Snellius/SURF)

For HPC cluster deployment:

```bash
# Load required modules
module load Python/3.9.6-GCCcore-11.2.0
module load GDAL/3.5.0-foss-2022a

# Install user packages
pip install --user -r requirements.txt
```

## Critical Dependencies

### GDAL (Geospatial Data Abstraction Library)

**⚠️ Most important dependency** - Required for all LiDAR data processing

**Installation challenges:**
- **Linux:** `sudo apt-get install gdal-bin libgdal-dev`
- **macOS:** `brew install gdal`
- **Windows:** Use conda: `conda install -c conda-forge gdal`
- **HPC:** Load system module: `module load GDAL`

**Common issues:**
- Python GDAL bindings must match system GDAL version
- Install system GDAL before pip installing other packages
- Use conda for most reliable GDAL installation

### NumPy & SciPy

Essential for all mathematical operations and array processing.

### Matplotlib

Required for fire visualization and animation export.

### psutil

Critical for memory monitoring and system resource management.

## Optional Dependencies

### Performance Enhancement

- **numba** - Just-in-time compilation for speed improvements
- **dask** - Distributed computing for very large simulations

### Advanced Features

- **pydantic** - Advanced configuration validation
- **scikit-learn** - Machine learning for fire behavior modeling
- **h5py/netcdf4** - Scientific data format support

### Development Tools

- **pytest** - Testing framework
- **black** - Code formatting
- **sphinx** - Documentation generation
- **jupyter** - Interactive development

## Troubleshooting

### GDAL Installation Issues

```bash
# Check GDAL installation
python -c "from osgeo import gdal; print(gdal.__version__)"

# If import fails:
# 1. Reinstall GDAL through conda
conda install -c conda-forge gdal --force-reinstall

# 2. Or check system GDAL version matches Python bindings
gdal-config --version
```

### Memory Issues

```bash
# For large simulations, enable memory optimization
# In your simulation configuration:
memory_optimization_level = 2
use_disk_storage = True
```

### Import Errors

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Verify virtual environment
which python
pip list
```

## Version Compatibility

- **Python:** 3.9+ (tested with 3.9.21)
- **GDAL:** 3.4.0+ (critical for geospatial operations)
- **NumPy:** 1.21.0+ (core mathematical operations)
- **SciPy:** 1.7.0+ (sparse matrices, image processing)

## System Requirements

### Minimum System Requirements

- **Memory:** 8GB RAM (for grids up to 1000x1000)
- **Storage:** 5GB free space
- **CPU:** Multi-core recommended for parallel processing

### Recommended System Requirements

- **Memory:** 16GB+ RAM (for large simulations)
- **Storage:** 50GB+ for data and results
- **CPU:** 8+ cores for optimal performance
- **GPU:** Not required but may benefit visualization

### HPC Requirements

- **Memory:** 32GB+ per node
- **Storage:** Parallel filesystem recommended
- **Network:** High-bandwidth for distributed computing

## Platform-Specific Notes

### Windows

- Use conda for GDAL installation
- May require Visual C++ build tools for some packages
- Consider WSL for better GDAL compatibility

### macOS

- Use Homebrew for system dependencies
- Xcode command line tools may be required
- M1/M2 Macs: use conda-forge for best compatibility

### Linux

- Most straightforward installation
- Package manager installation for system dependencies
- Preferred platform for HPC deployment

## Support

For installation issues:

1. Check this guide first
2. Review error messages carefully
3. Search existing issues in the repository
4. Create a new issue with:
   - Operating system and version
   - Python version
   - Complete error message
   - Steps to reproduce

## Contributing

When contributing to the project:

1. Use `requirements-dev.txt` for development setup
2. Run tests before submitting: `pytest tests/`
3. Format code: `black src/ tests/`
4. Check code quality: `flake8 src/ tests/`
5. Update requirements if adding new dependencies 