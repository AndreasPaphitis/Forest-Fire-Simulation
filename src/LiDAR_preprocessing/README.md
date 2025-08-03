# LiDAR Preprocessing Framework

This directory contains the preprocessing framework for LiDAR data in the Forest-Fire-Simulation project. The framework processes raw LiDAR data to extract vegetation structure information for forest fire modeling.

## Preprocessing Pipeline

The preprocessing workflow consists of three main stages:

1. **Height Normalization** (`height_normalisation_all.py`) - Normalizes point heights relative to the ground surface
2. **Normalized Return Density (NRD) Calculation** (`NRD_calculation.py`) - Calculates proportion of LiDAR returns at each height
3. **Plant Area Density (PAD) Calculation** (`PAD_calculation.py`) - Converts NRD to physical vegetation density metrics

## Recent Improvements

The preprocessing framework has been improved in several key areas:

### 1. Dependency Management

- Added robust import handling with proper fallbacks
- Implemented system path manipulation to ensure correct module imports
- Removed hard-coded file paths and replaced with proper path handling

### 2. Code Duplication Reduction

- Created shared utilities in `preprocessing_utils.py`
- Consolidated common functions across modules
- Standardized error handling and logging

### 3. Configuration Handling

- Implemented unified configuration system (`preprocessing_config.py`)
- Added validation for configuration parameters
- Supported multiple configuration sources (files, command-line)

### 4. Error Handling Standardization

- Added consistent error handling across all preprocessing modules
- Implemented appropriate exception catching and logging
- Created test modules for preprocessing utilities

### 5. Testing

- Added unit tests for preprocessing utilities
- Implemented systematic test coverage for critical functions
- Created fixtures for testing with synthetic data

### 6. Progress Reporting

- Added `ProgressTracker` for consistent progress reporting
- Implemented central logging configuration
- Created detailed processing reports and metadata

### 7. Memory Management

- Added memory monitoring and reporting
- Implemented chunked processing for large datasets
- Added memory requirement estimation and validation

## Usage

To run the entire preprocessing pipeline:

```bash
python run_preprocessing.py --input_dir /path/to/raw/data --output_dir /path/to/output --config config.json
```

To run individual steps:

```bash
# Height normalization only
python run_preprocessing.py --height_norm_only --input_dir /path/to/raw/data --output_dir /path/to/output

# NRD calculation only
python run_preprocessing.py --nrd_only --nrd_input /path/to/normalized/data --nrd_output /path/to/nrd/output

# PAD calculation only
python run_preprocessing.py --pad_only --pad_input /path/to/nrd/data --pad_output /path/to/pad/output --extinction_coefficient 0.5
```

## Configuration

Use preprocessing_config.py to generate a default configuration:

```bash
python preprocessing_config.py --output my_config.json
```

Then edit the configuration file as needed and pass it to the preprocessing runner:

```bash
python run_preprocessing.py --config my_config.json
```

## Memory Optimization

For very large datasets, you can control memory usage using these techniques:

1. Adjust the number of workers (`--workers`) to control parallel processing
2. Use the memory monitoring utilities to profile memory usage
3. Configure chunking parameters in `memory_utils.py`
4. Consider pre-tiling large areas and processing each tile separately 