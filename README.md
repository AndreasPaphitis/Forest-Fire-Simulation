# LiDAR-Integrated Cellular Automata Wildfire Model

## Overview
This repository contains the complete research dataset and codebase for wildfire simulation modeling using LiDAR-derived vegetation structure data integrated with cellular automata framework, applied to the 2023 Tenerife wildfire case study.

## Repository Structure

```
project_root/
├── src/                    # Core library code
│   ├── core/              # Fire simulation engine and models
│   ├── config/            # Configuration management
│   ├── utils/             # Utility functions and helpers
│   └── LiDAR_preprocessing/  # LiDAR data processing
├── scripts/               # Executable workflow scripts
│   ├── preprocessing/     # Data preprocessing
│   ├── calibration/       # Model calibration
│   ├── validation/        # Model validation
│   ├── hpc/              # HPC deployment scripts
│   └── analysis/         # Analysis and visualization
├── figures/              # Chart and visualization generation
│   ├── methodology/      # Methodology section figures
│   ├── results/          # Results section figures
│   └── supplementary/    # Animations and supplementary
├── tests/                # Unit and integration tests
│   └── integration/      # Integration tests
├── diagnostics/          # Diagnostic and debugging scripts
├── docs/                 # Documentation
│   ├── guides/           # User guides and tutorials
│   ├── fixes/            # Technical fix documentation
│   └── summaries/        # Workflow and status summaries
├── data/                 # Data files
│   ├── raw/             # Original unprocessed data
│   ├── processed/       # Processed analysis-ready data
│   └── emsr_delineations/  # EMSR fire perimeter data
├── results/             # Analysis outputs
│   ├── calibration/     # Calibration results
│   ├── validation/      # Validation results
│   ├── sensitivity/     # Sensitivity analysis results
│   ├── figures/         # Generated figures
│   └── simulation_states/  # Simulation state files
└── archive/             # Historical code and documentation
    ├── old_numbered_structure/  # Original folder structure
    ├── backup_files/    # Backup copies of replaced files
    └── historical_docs/ # Historical documentation
```

## Quick Start

### 1. Environment Setup
```bash
pip install -r requirements.txt
```

### 2. Data Preprocessing
```bash
# Preprocess LiDAR data
python scripts/preprocessing/preprocess_lidar.py

# Preprocess terrain data
python scripts/preprocessing/preprocess_terrain.py
```

### 3. Model Calibration
```bash
python scripts/calibration/run_tenerife_calibration_clean.py
```

### 4. Model Validation
```bash
python scripts/validation/run_tenerife_validation_optimized.py
```

### 5. Generate Figures
```bash
python figures/results/create_all_thesis_charts_master.py
```

## Data Description

### Input Data
- **LiDAR**: High-resolution point cloud (0.5 pts/m²) from PNOA-IGN
  - Location: `data/raw/lidar/`
  - Processed output: `data/processed/lidar/`
- **Terrain**: Digital Terrain Model (5m resolution) from IGN
  - Location: `data/raw/terrain/`
  - Processed output: `data/processed/terrain/`
- **Fire Perimeters**: EMSR-665 Copernicus emergency mapping
  - Location: `data/emsr_delineations/`
  - Binary masks: `data/processed/fire_targets/`

### Output Data
- **Calibration Results**: `results/calibration/`
- **Validation Results**: `results/validation/`
- **Sensitivity Analysis**: `results/sensitivity/`
- **Figures**: `results/figures/thesis/`
- **Simulation States**: `results/simulation_states/`

## Methodology

### 1. LiDAR Processing
Height normalization → Vegetation classification → PAD derivation → Resampling

See: `docs/guides/` for detailed guides

### 2. Terrain Analysis
Slope/aspect calculation → Barranco detection → Wind modeling

### 3. Model Development
3D cellular automata with horizontal/vertical/ember spread

Core implementation: `src/core/forest_model.py`

### 4. Calibration
Sensitivity analysis → Grid search optimization

Scripts: `scripts/calibration/` and `scripts/analysis/run_sensitivity_analysis.py`

### 5. Validation
Independent testing on withheld fire progression data

Scripts: `scripts/validation/`

## HPC Deployment

For running on Snellius HPC cluster:

```bash
# Submit calibration job
sbatch scripts/hpc/tenerife_production.slurm

# Submit sensitivity analysis
sbatch scripts/hpc/submit_sensitivity_analysis.slurm
```

See `scripts/hpc/OUTPUT_PATH_CONFIGURATION.md` for configuration details.

## Documentation

- **User Guides**: `docs/guides/`
  - Calibration guide
  - Production deployment guide
  - Sensitivity analysis guide
  - Chart generation guide
  
- **Technical Documentation**: `docs/fixes/`
  - Bug fixes and optimizations
  - Memory management
  - Performance improvements

- **Workflow Documentation**: `docs/summaries/`
  - Comprehensive workflow
  - Parameter summaries
  - Memory audits

## Testing

Run tests to verify system integrity:

```bash
# Run import tests
python tests/test_gdal_import.py

# Run integration tests
python tests/integration/test_corrected_calibration.py
```

## Project Organization

This repository was reorganized in October 2025 to improve navigability and maintainability. The old numbered folder structure (01-06) has been archived in `archive/old_numbered_structure/` for reference.

### Key Changes
- Consolidated data into `data/` directory
- Organized scripts by workflow stage in `scripts/`
- Separated figure generation into `figures/`
- Centralized documentation in `docs/`
- Archived historical files in `archive/`

See `archive/README.md` for details on archived materials.

## Citation

If you use this dataset or code, please cite:

```bibtex
@software{paphitis2025lidar,
  author = {Paphitis, Andreas},
  title = {LiDAR-Integrated Cellular Automata Wildfire Model},
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/yourusername/wildfire-model}
}
```

See `CITATION.cff` for complete citation information.

## Requirements

- Python 3.8+
- GDAL
- NumPy, SciPy
- Rasterio, GeoPandas
- Matplotlib, Seaborn
- PDAL (for LiDAR processing)

See `requirements.txt` for complete list.

## License

[Add license information]

## Contact

[Add contact information]

## Acknowledgments

- LiDAR data: PNOA-IGN (Instituto Geográfico Nacional)
- Fire perimeter data: Copernicus Emergency Management Service (EMSR-665)
- Terrain data: Instituto Geográfico Nacional
- HPC resources: Snellius supercomputer (SURF)
